from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class MergeLLMExtractedWithSource:
    """
    Merge chunk-level llm_extracted_normalized*.json files by reg_id
    and keep provenance in a 'source' field for each merged REG object.
    """

    def __init__(self, input_root: str | Path, filename_pattern: str = "llm_extracted_normalized*.json") -> None:
        self.input_root = Path(input_root).expanduser().resolve()
        self.filename_pattern = filename_pattern

    @staticmethod
    def _chunk_sort_key(path: Path) -> tuple[int, int, str]:
        name = path.name.strip().lower()
        digits = "".join(ch for ch in name if ch.isdigit())
        if digits:
            return (0, int(digits), name)
        return (1, 10**9, name)

    def _find_chunk_files(self) -> list[Path]:
        if not self.input_root.exists() or not self.input_root.is_dir():
            raise FileNotFoundError(f"Input root not found: {self.input_root}")

        files = sorted(self.input_root.glob(f"chunk*/{self.filename_pattern}"), key=self._chunk_sort_key)
        if not files:
            raise FileNotFoundError(
                f"No files matching chunk*/{self.filename_pattern} found under: {self.input_root}"
            )
        return files

    @staticmethod
    def _read_rows(path: Path) -> list[dict[str, Any]]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError(f"Expected a JSON list in {path}")
        return [row for row in payload if isinstance(row, dict)]

    @staticmethod
    def _row_id(row: dict[str, Any]) -> str:
        return str(row.get("reg_id", "")).strip()

    @staticmethod
    def _row_deviation_found(row: dict[str, Any]) -> bool:
        deviations = row.get("deviations", [])
        if isinstance(deviations, list) and any(isinstance(item, dict) for item in deviations):
            return True
        return bool(row.get("deviation_found", False))

    @staticmethod
    def _merge_unique_refs(existing: list[Any], incoming: list[Any]) -> list[Any]:
        seen = set(existing)
        for ref in incoming:
            if ref not in seen:
                existing.append(ref)
                seen.add(ref)
        return existing

    @staticmethod
    def _merge_unique_deviations(existing: list[dict[str, Any]], incoming: list[Any]) -> list[dict[str, Any]]:
        seen = {json.dumps(item, ensure_ascii=False, sort_keys=True) for item in existing if isinstance(item, dict)}
        for item in incoming:
            if not isinstance(item, dict):
                continue
            key = json.dumps(item, ensure_ascii=False, sort_keys=True)
            if key not in seen:
                existing.append(item)
                seen.add(key)
        return existing

    def merge(self) -> list[dict[str, Any]]:
        chunk_files = self._find_chunk_files()
        merged: dict[str, dict[str, Any]] = {}

        for file_path in chunk_files:
            rows = self._read_rows(file_path)
            source_ref = str(file_path)

            for row in rows:
                reg_id = self._row_id(row)
                if not reg_id:
                    continue

                clause = str(row.get("clause", "")).strip()
                refs = row.get("considered_references", [])
                refs = refs if isinstance(refs, list) else []
                deviations = row.get("deviations", [])
                deviations = deviations if isinstance(deviations, list) else []
                deviation_found = self._row_deviation_found(row)

                if reg_id not in merged:
                    merged[reg_id] = {
                        "reg_id": reg_id,
                        "clause": clause,
                        "considered_references": list(refs),
                        "deviation_found": bool(deviation_found),
                        "deviations": [item for item in deviations if isinstance(item, dict)],
                        # Requested provenance field:
                        "source": [source_ref],
                    }
                else:
                    current = merged[reg_id]
                    if not current.get("clause") and clause:
                        current["clause"] = clause

                    current["considered_references"] = self._merge_unique_refs(
                        list(current.get("considered_references", [])),
                        refs,
                    )
                    current["deviations"] = self._merge_unique_deviations(
                        list(current.get("deviations", [])),
                        deviations,
                    )
                    current["deviation_found"] = bool(current.get("deviation_found", False) or deviation_found)

                    srcs = current.get("source", [])
                    if not isinstance(srcs, list):
                        srcs = [str(srcs)]
                    if source_ref not in srcs:
                        srcs.append(source_ref)
                    current["source"] = srcs

        # Stable order by REG numeric suffix if available.
        def sort_key(item: dict[str, Any]) -> tuple[int, str]:
            reg_id = str(item.get("reg_id", ""))
            try:
                n = int(reg_id.split("-")[-1])
                return (n, reg_id)
            except Exception:
                return (10**9, reg_id)

        return sorted(merged.values(), key=sort_key)

    def save(self, output_file: str | Path) -> Path:
        output_path = Path(output_file).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = self.merge()
        output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return output_path


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]

    # Input folder: contains chunk*/llm_extracted_normalized*.json
    input_root = project_root / "intermediate_outputs" / "artifact_03_rea_case3_injections"

    # Output merged file with source provenance per REG.
    output_file = input_root / "merged_llm_extracted_normalized_with_source.json"

    merger = MergeLLMExtractedWithSource(input_root=input_root)
    saved = merger.save(output_file=output_file)
    print(f"Saved merged file: {saved}")


if __name__ == "__main__":
    main()
