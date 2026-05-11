from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any


class ExtractLLMOutput:
    """
    Extract structured evaluation rows from an LLM response JSON and export to table format.
    """

    def __init__(
        self,
        llm_response_json_path: str | Path,
        reg_metadata_json_path: str | Path = "/Users/my/Documents/projects/detectionDeviation/intermediate_results/reg/gdpr_requirements_with_additional_references.json",
    ):
        self.llm_response_json_path = Path(llm_response_json_path).expanduser().resolve()
        self.reg_metadata_json_path = Path(reg_metadata_json_path).expanduser().resolve()
        self.reg_to_article = self._load_reg_to_article_map()

    @staticmethod
    def _build_article_label(article: Any, paragraph: Any) -> str:
        article_str = str(article).strip().replace("Art", "")
        paragraph_str = str(paragraph).strip()
        if not article_str:
            return ""
        if paragraph_str:
            return f"Art{article_str}({paragraph_str})"
        return f"Art{article_str}"

    def _load_reg_to_article_map(self) -> dict[str, str]:
        if not self.reg_metadata_json_path.exists():
            return {}
        payload = json.loads(self.reg_metadata_json_path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            return {}

        mapping: dict[str, str] = {}
        for row in payload:
            if not isinstance(row, dict):
                continue
            reg_id = str(row.get("ID", "")).strip().upper()
            if not reg_id:
                continue
            article_label = self._build_article_label(row.get("Article", ""), row.get("Paragraph", ""))
            if article_label:
                mapping[reg_id] = article_label
        return mapping

    def _map_reference_to_article(self, value: Any) -> str:
        ref = str(value).strip()
        reg_id = ref.upper()
        if re.fullmatch(r"REG-\d+", reg_id):
            return self.reg_to_article.get(reg_id, ref)
        return ref

    def _normalize_policy_rows(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            row_copy = dict(row)
            considered_refs = row_copy.get("considered_references", [])
            if isinstance(considered_refs, list):
                row_copy["considered_references"] = [
                    self._map_reference_to_article(ref) for ref in considered_refs if str(ref).strip()
                ]
            normalized.append(row_copy)
        return normalized

    @staticmethod
    def _extract_content_from_response(payload: dict[str, Any]) -> str:
        """
        Read assistant content from OpenAI chat completion payload.
        Supports both string content and list-form content parts.
        """
        choices = payload.get("choices", [])
        if not isinstance(choices, list) or not choices:
            raise ValueError("Invalid LLM response: missing choices[0].")

        first_choice = choices[0] if isinstance(choices[0], dict) else {}
        message = first_choice.get("message", {})
        if not isinstance(message, dict):
            raise ValueError("Invalid LLM response: missing message object.")

        content = message.get("content", "")
        if isinstance(content, str):
            return content

        # Newer payload variants may return content as a list of blocks.
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str) and text.strip():
                        parts.append(text)
            if parts:
                return "\n".join(parts)

        raise ValueError("Invalid LLM response: assistant content is empty or unsupported.")

    @staticmethod
    def _extract_json_string(content: str) -> str:
        """
        Extract JSON from:
        1) fenced ```json blocks
        2) or first JSON-like array/object fallback.
        """
        fenced = re.search(r"```json\s*(.*?)\s*```", content, flags=re.IGNORECASE | re.DOTALL)
        if fenced:
            return fenced.group(1).strip()

        # Fallback: take first top-level JSON-looking array/object span.
        array_match = re.search(r"(\[\s*[\s\S]*\])", content)
        if array_match:
            return array_match.group(1).strip()

        object_match = re.search(r"(\{\s*[\s\S]*\})", content)
        if object_match:
            return object_match.group(1).strip()

        raise ValueError("No JSON content found in assistant response.")

    @staticmethod
    def _to_rows(parsed_json: Any) -> list[dict[str, Any]]:
        """
        Normalize parsed JSON into list[dict].
        """
        if isinstance(parsed_json, dict):
            return [parsed_json]

        if isinstance(parsed_json, list):
            rows: list[dict[str, Any]] = []
            for item in parsed_json:
                if isinstance(item, dict):
                    rows.append(item)
            if rows:
                return rows

        raise ValueError("Parsed JSON is not a valid row object/list for tabular export.")

    @staticmethod
    def _flatten_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Flatten policy-level outputs to a tabular row shape.

        Supports:
        1) Current schema:
           {
             "reg_id": "...",
             "clause": "...",
             "considered_references": [...],
             "deviation_found": bool,
             "deviations": [{...}, ...]
           }
        2) Previous schema:
           {
             "policy_id": "...",
             "deviations": [{...}, ...]
           }
        3) Old flat schema where each object already contains deviation fields.
        """
        flattened: list[dict[str, Any]] = []

        for row in rows:
            reg_id = str(row.get("reg_id", "")).strip()
            clause = str(row.get("clause", "")).strip()
            considered_refs = row.get("considered_references", [])
            deviation_found_value = row.get("deviation_found")
            policy_id = str(row.get("policy_id", "")).strip()
            deviations = row.get("deviations")

            # Current/previous nested schema path
            if isinstance(deviations, list):
                base = {
                    "reg_id": reg_id,
                    "policy_id": policy_id,
                    "clause": clause,
                    "considered_references": considered_refs if isinstance(considered_refs, list) else [],
                }
                # Keep deviation_found deterministic from the actual deviations payload.
                # If payload explicitly sets deviation_found, we still prioritize structural consistency.
                computed_deviation_found = bool(deviations)

                if not deviations:
                    row_out = dict(base)
                    row_out.update(
                        {
                            "deviation_index": "",
                            "deviation_found": False if deviation_found_value is None else bool(computed_deviation_found),
                            "article": "",
                            "gdpr_requirement": "",
                            "policy_realization": "",
                            "deviation_type": "",
                            "analysis": "",
                        }
                    )
                    flattened.append(row_out)
                    continue

                index = 0
                for deviation in deviations:
                    if not isinstance(deviation, dict):
                        continue
                    index += 1
                    row_out = dict(base)
                    row_out.update(
                        {
                            "deviation_index": index,
                            "article": str(deviation.get("article", "")).strip(),
                            "gdpr_requirement": str(deviation.get("gdpr_requirement", "")).strip(),
                            "policy_realization": str(deviation.get("policy_realization", "")).strip(),
                            "deviation_type": str(deviation.get("deviation_type", "")).strip(),
                            "gdpr_quote": str(deviation.get("gdpr_quote", "")).strip(),
                            "policy_quote": str(deviation.get("policy_quote", "")).strip(),
                            "mismatch": str(deviation.get("mismatch", "")).strip(),
                            "analysis": str(deviation.get("analysis", "")).strip(),
                            "deviation_found": True if deviation_found_value is None else bool(computed_deviation_found),
                        }
                    )
                    flattened.append(row_out)
                if index == 0:
                    row_out = dict(base)
                    row_out.update(
                        {
                            "deviation_index": "",
                            "deviation_found": bool(deviation_found_value) if deviation_found_value is not None else False,
                            "article": "",
                            "gdpr_requirement": "",
                            "policy_realization": "",
                            "deviation_type": "",
                            "gdpr_quote": "",
                            "policy_quote": "",
                            "mismatch": "",
                            "analysis": "",
                        }
                    )
                    flattened.append(row_out)
                continue

            # Old schema path (keep compatibility with previous outputs)
            old_row = dict(row)
            if "deviation_found" not in old_row:
                old_row["deviation_found"] = bool(old_row.get("deviation_type"))
            flattened.append(old_row)

        return flattened

    @staticmethod
    def _column_order(rows: list[dict[str, Any]]) -> list[str]:
        """
        Preserve useful stable order for known fields first, then append unknown fields.
        """
        preferred = [
            "reg_id",
            "clause",
            "considered_references",
            "policy_id",
            "deviation_index",
            "deviation_found",
            "article",
            "gdpr_requirement",
            "policy_realization",
            "deviation_type",
            "gdpr_quote",
            "policy_quote",
            "mismatch",
            # Backward-compatible legacy columns:
            "is_compliant",
            "analysis",
        ]
        seen: set[str] = set()
        ordered: list[str] = []

        for col in preferred:
            for row in rows:
                if col in row and col not in seen:
                    ordered.append(col)
                    seen.add(col)
                    break

        for row in rows:
            for key in row.keys():
                if key not in seen:
                    ordered.append(key)
                    seen.add(key)

        return ordered

    def extract_rows(self) -> list[dict[str, Any]]:
        payload = json.loads(self.llm_response_json_path.read_text(encoding="utf-8"))
        content = self._extract_content_from_response(payload)
        json_string = self._extract_json_string(content)
        parsed = json.loads(json_string)
        rows = self._normalize_policy_rows(self._to_rows(parsed))
        return self._flatten_rows(rows)

    def _extract_policy_objects(self) -> list[dict[str, Any]]:
        """
        Return policy-level objects from the parsed assistant JSON.
        This keeps structure needed for readable reporting.
        """
        payload = json.loads(self.llm_response_json_path.read_text(encoding="utf-8"))
        content = self._extract_content_from_response(payload)
        json_string = self._extract_json_string(content)
        parsed = json.loads(json_string)
        rows = self._normalize_policy_rows(self._to_rows(parsed))
        policies: list[dict[str, Any]] = []
        for row in rows:
            if isinstance(row, dict):
                policies.append(row)
        return policies

    def save_normalized_json(self, output_json_path: str | Path) -> Path:
        """
        Save normalized policy-level JSON with considered_references mapped to article labels.
        """
        payload = json.loads(self.llm_response_json_path.read_text(encoding="utf-8"))
        content = self._extract_content_from_response(payload)
        json_string = self._extract_json_string(content)
        parsed = json.loads(json_string)
        rows = self._normalize_policy_rows(self._to_rows(parsed))

        output_path = Path(output_json_path).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
        return output_path

    def save_table_csv(self, output_csv_path: str | Path) -> Path:
        rows = self.extract_rows()
        output_path = Path(output_csv_path).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        columns = self._column_order(rows)
        with output_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            for row in rows:
                normalized = {
                    key: (json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value)
                    for key, value in row.items()
                }
                writer.writerow(normalized)

        return output_path

    def save_readable_report(self, output_md_path: str | Path) -> Path:
        """
        Generate a more readable markdown view of LLM output.
        Grouped by reg_id/policy_id with per-deviation details.
        """
        policies = self._extract_policy_objects()
        output_path = Path(output_md_path).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        lines: list[str] = []
        lines.append("# LLM Deviation Review")
        lines.append("")

        if not policies:
            lines.append("No policy evaluations were found.")
        else:
            for row in policies:
                reg_id = str(row.get("reg_id", "")).strip()
                policy_id = str(row.get("policy_id", "")).strip()
                row_id = reg_id or policy_id or "UNKNOWN"
                clause = str(row.get("clause", "")).strip()
                considered_refs = row.get("considered_references", [])
                deviations = row.get("deviations")

                lines.append(f"## {row_id}")
                if clause:
                    lines.append(f"- Clause: {clause}")
                if isinstance(considered_refs, list):
                    refs_text = ", ".join(str(x).strip() for x in considered_refs if str(x).strip())
                    lines.append(f"- Considered References: {refs_text or 'None'}")
                lines.append("")

                # New schema
                if isinstance(deviations, list):
                    if not deviations:
                        lines.append("- No deviations found (non-deviation).")
                        lines.append("")
                        continue

                    lines.append(f"- Deviation Count: {len([d for d in deviations if isinstance(d, dict)])}")
                    lines.append("")
                    for index, deviation in enumerate(deviations, start=1):
                        if not isinstance(deviation, dict):
                            continue
                        deviation_type = str(deviation.get("deviation_type", "")).strip()
                        gdpr_quote = str(deviation.get("gdpr_quote", "")).strip()
                        policy_quote = str(deviation.get("policy_quote", "")).strip()
                        mismatch = str(deviation.get("mismatch", "")).strip()

                        lines.append(f"- Deviation {index}")
                        analysis = str(deviation.get("analysis", "")).strip()
                        lines.append(f"  - Type: {deviation_type or 'N/A'}")
                        lines.append(f"  - GDPR Quote: {gdpr_quote or 'N/A'}")
                        lines.append(f"  - Policy Quote: {policy_quote or 'N/A'}")
                        lines.append(f"  - Mismatch: {mismatch or 'N/A'}")
                        lines.append(f"  - Analysis: {analysis or 'N/A'}")
                    lines.append("")
                    continue

                # Backward-compatible schema
                deviation_found = row.get("deviation_found")
                deviation_type = str(row.get("deviation_type", "")).strip()
                analysis = str(row.get("analysis", "")).strip()
                lines.append(f"- Deviation Found: {deviation_found}")
                lines.append(f"- Deviation Type: {deviation_type or 'N/A'}")
                lines.append(f"- Analysis: {analysis or 'N/A'}")
                lines.append("")

        output_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
        return output_path

    @classmethod
    def _with_suffix_before_ext(cls, filename: str, suffix: str) -> str:
        path = Path(filename)
        if not suffix:
            return filename
        return f"{path.stem}_{suffix}{path.suffix}"

    @classmethod
    def _iter_response_files(
        cls,
        chunk_dir: Path,
        response_filename: str,
    ) -> list[tuple[Path, str]]:
        """
        Resolve response files to process in one chunk.

        Returns list of tuples:
        - response file path
        - output suffix ('' for llm_response.json, otherwise e.g. '01')
        """
        # Backward compatibility: if caller gives a non-default name, process exactly that file.
        if response_filename != "llm_response.json":
            explicit = chunk_dir / response_filename
            if not explicit.exists():
                return []
            return [(explicit, "")]

        # New behavior: process all llm_response*.json files.
        files = sorted(chunk_dir.glob("llm_response*.json"))
        results: list[tuple[Path, str]] = []
        for file_path in files:
            name = file_path.name
            if name == "llm_response.json":
                results.append((file_path, ""))
                continue
            match = re.match(r"^llm_response_(.+)\.json$", name, flags=re.IGNORECASE)
            suffix = match.group(1) if match else ""
            results.append((file_path, suffix))
        return results

    @classmethod
    def process_chunk_dir(
        cls,
        chunk_dir: str | Path,
        response_filename: str = "llm_response.json",
        output_json_filename: str = "llm_extracted_normalized.json",
        output_csv_filename: str = "llm_extracted_table.csv",
        output_md_filename: str = "llm_extracted_readable.md",
    ) -> dict[str, str]:
        """
        Process one artifact_03 chunk directory.
        """
        chunk_path = Path(chunk_dir).expanduser().resolve()
        if not chunk_path.exists() or not chunk_path.is_dir():
            raise FileNotFoundError(f"Chunk directory not found: {chunk_path}")

        response_path = chunk_path / response_filename
        if not response_path.exists():
            raise FileNotFoundError(f"LLM response file not found: {response_path}")

        extractor = cls(response_path)
        json_path = chunk_path / output_json_filename
        csv_path = chunk_path / output_csv_filename
        md_path = chunk_path / output_md_filename
        saved_json = extractor.save_normalized_json(json_path)
        saved_csv = extractor.save_table_csv(csv_path)
        saved_md = extractor.save_readable_report(md_path)
        return {
            "chunk_dir": str(chunk_path),
            "response_file": str(response_path),
            "normalized_json_file": str(saved_json),
            "csv_file": str(saved_csv),
            "readable_file": str(saved_md),
        }

    @classmethod
    def process_artifact_root(
        cls,
        artifact_03_root: str | Path,
        response_filename: str = "llm_response.json",
        output_json_filename: str = "llm_extracted_normalized.json",
        output_csv_filename: str = "llm_extracted_table.csv",
        output_md_filename: str = "llm_extracted_readable.md",
    ) -> dict[str, Any]:
        """
        Process every chunk folder under artifact_03 root.
        """
        root = Path(artifact_03_root).expanduser().resolve()
        if not root.exists() or not root.is_dir():
            raise FileNotFoundError(f"artifact_03 root not found: {root}")

        processed: list[dict[str, str]] = []
        skipped: list[dict[str, str]] = []
        for chunk_dir in sorted(path for path in root.iterdir() if path.is_dir()):
            response_files = cls._iter_response_files(chunk_dir, response_filename)
            if not response_files:
                if response_filename == "llm_response.json":
                    skipped.append({"chunk": chunk_dir.name, "reason": "missing llm_response*.json"})
                else:
                    skipped.append({"chunk": chunk_dir.name, "reason": f"missing {response_filename}"})
                continue

            for response_path, suffix in response_files:
                json_name = cls._with_suffix_before_ext(output_json_filename, suffix)
                csv_name = cls._with_suffix_before_ext(output_csv_filename, suffix)
                md_name = cls._with_suffix_before_ext(output_md_filename, suffix)

                result = cls.process_chunk_dir(
                    chunk_dir=chunk_dir,
                    response_filename=response_path.name,
                    output_json_filename=json_name,
                    output_csv_filename=csv_name,
                    output_md_filename=md_name,
                )
                processed.append(result)

        return {
            "artifact_03_root": str(root),
            "processed_count": len(processed),
            "skipped_count": len(skipped),
            "processed": processed,
            "skipped": skipped,
        }


def main() -> None:
    artifact_03_root = "/Users/my/Documents/projects/detectionDeviation/intermediate_outputs/artifact_03_reranked_100"
    result = ExtractLLMOutput.process_artifact_root(artifact_03_root)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
