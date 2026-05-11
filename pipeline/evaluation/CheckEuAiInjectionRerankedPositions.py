from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


class EuAiInjectionRerankedChecker:
    def __init__(self, root_dir: str | Path):
        self.root_dir = Path(root_dir).expanduser().resolve()
        self.injections_json = self.root_dir / "goldstandard" / "eu_ai_injections.json"
        self.reranked_root = self.root_dir / "intermediate_outputs" / "artifact_01_case3_v3_reranked"
        self.rea_stage_root = self.root_dir / "intermediate_results" / "rea_case3_injections_deontic_stages"

    @staticmethod
    def _normalize_spaces(value: str) -> str:
        return " ".join(str(value).split()).strip()

    @classmethod
    def _clean_placeholder(cls, value: str) -> str:
        text = str(value)
        text = re.sub(r"\[\s*missing_subject\s*\]", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"\bmissing_subject\b", " ", text, flags=re.IGNORECASE)
        return cls._normalize_spaces(text)

    @classmethod
    def _normalize_realization_text(cls, value: str) -> str:
        text = cls._normalize_spaces(str(value))
        text = re.sub(r"^[A-Z]\d+(?:\.\d+)+(?:\s+|\s*\.\.\.\s*)", "", text)
        text = re.sub(r"\.\.\.", " ", text)
        text = text.replace("“", '"').replace("”", '"').replace("’", "'")
        text = cls._clean_placeholder(text)
        return text

    @classmethod
    def _canonical_text(cls, value: str) -> str:
        text = cls._normalize_realization_text(value).casefold()
        text = re.sub(r"\s+", " ", text)
        return text.strip(" .,:;")

    @staticmethod
    def _split_expected_reg_ids(value: str) -> list[str]:
        parts = [part.strip() for part in str(value).split("|")]
        return [part for part in parts if re.fullmatch(r"REG-\d+", part)]

    def _load_json(self, path: Path) -> Any:
        return json.loads(path.read_text(encoding="utf-8"))

    def _build_reranked_index(self) -> dict[str, dict[str, Any]]:
        reranked_by_id: dict[str, dict[str, Any]] = {}
        for reranked_file in sorted(self.reranked_root.rglob("*.json")):
            payload = self._load_json(reranked_file)
            rea_id = self._normalize_spaces(str(payload.get("id", "")))
            if not rea_id:
                continue
            reranked_by_id[rea_id] = {
                "path": str(reranked_file),
                "payload": payload,
            }
        return reranked_by_id

    def _build_candidate_index(self) -> list[dict[str, Any]]:
        reranked_by_id = self._build_reranked_index()
        candidates: list[dict[str, Any]] = []

        for stage_file in sorted(self.rea_stage_root.rglob("*_deontic_stages.json")):
            payload = self._load_json(stage_file)
            stage1_rows = payload.get("stage1_output", [])
            stage2_rows = payload.get("stage2_output", [])
            stage3_rows = payload.get("stage3_output", [])
            stage4_rows = payload.get("stage4_output", [])

            stage1_by_id = {self._normalize_spaces(str(row.get("ID", ""))): row for row in stage1_rows if isinstance(row, dict)}
            stage2_by_id = {self._normalize_spaces(str(row.get("ID", ""))): row for row in stage2_rows if isinstance(row, dict)}
            stage3_by_id = {self._normalize_spaces(str(row.get("ID", ""))): row for row in stage3_rows if isinstance(row, dict)}

            for row in stage4_rows:
                if not isinstance(row, dict):
                    continue
                sub_id = self._normalize_spaces(str(row.get("sub_id", row.get("id", ""))))
                if not sub_id:
                    continue
                reranked = reranked_by_id.get(sub_id)
                if reranked is None:
                    continue

                stage1_text = self._normalize_spaces(str(stage1_by_id.get(sub_id, {}).get("Text", "")))
                stage2_text = self._normalize_spaces(str(stage2_by_id.get(sub_id, {}).get("Text", "")))
                stage3_text = self._clean_placeholder(str(stage3_by_id.get(sub_id, {}).get("Active_Recovered_Text", "")))
                stage4_text = self._clean_placeholder(str(row.get("text", "")))
                search_query = self._clean_placeholder(str(reranked["payload"].get("search query", "")))

                texts = [text for text in [stage1_text, stage2_text, stage3_text, stage4_text, search_query] if text]
                canonical_texts = {self._canonical_text(text) for text in texts if self._canonical_text(text)}

                candidates.append(
                    {
                        "sub_id": sub_id,
                        "rea_id": self._normalize_spaces(str(row.get("rea_id", row.get("id", "")))),
                        "reranked_path": reranked["path"],
                        "reranked_payload": reranked["payload"],
                        "texts": texts,
                        "canonical_texts": canonical_texts,
                    }
                )
        return candidates

    @staticmethod
    def _find_reg_rank(top_matches: list[dict[str, Any]], reg_id: str) -> int | None:
        for idx, match in enumerate(top_matches, start=1):
            match_id = str(match.get("ID", "")).strip()
            if match_id == reg_id:
                rank_value = match.get("rerank rank", idx)
                try:
                    return int(rank_value)
                except Exception:
                    return idx
        return None

    def _match_realization(self, realization_text: str, candidates: list[dict[str, Any]]) -> list[tuple[str, dict[str, Any]]]:
        query = self._canonical_text(realization_text)
        if not query:
            return []

        exact_matches: list[tuple[str, dict[str, Any]]] = []
        fuzzy_matches: list[tuple[str, dict[str, Any]]] = []
        for candidate in candidates:
            texts = candidate.get("canonical_texts", set())
            if query in texts:
                exact_matches.append(("exact", candidate))
                continue
            if any(query in text or text in query for text in texts):
                fuzzy_matches.append(("fuzzy", candidate))

        return exact_matches if exact_matches else fuzzy_matches

    def build_report(self) -> dict[str, Any]:
        injections = self._load_json(self.injections_json)
        if not isinstance(injections, list):
            raise ValueError("eu_ai_injections.json must contain a list.")

        candidates = self._build_candidate_index()
        report_entries: list[dict[str, Any]] = []
        matched_realization_count = 0
        expected_reg_hit_count = 0

        for item in injections:
            if not isinstance(item, dict):
                continue
            expected_reg_ids = self._split_expected_reg_ids(item.get("reg_id", ""))
            realization_reports: list[dict[str, Any]] = []

            for realization_text in item.get("realization_texts", []):
                matched_candidates = self._match_realization(str(realization_text), candidates)
                if matched_candidates:
                    matched_realization_count += 1

                candidate_reports: list[dict[str, Any]] = []
                found_any_expected = False
                for match_type, candidate in matched_candidates:
                    payload = candidate["reranked_payload"]
                    top_matches = payload.get("top matches", [])
                    reg_hits = []
                    for reg_id in expected_reg_ids:
                        rank = self._find_reg_rank(top_matches, reg_id)
                        if rank is not None:
                            found_any_expected = True
                            expected_reg_hit_count += 1
                        reg_hits.append(
                            {
                                "reg_id": reg_id,
                                "rank": rank,
                            }
                        )

                    candidate_reports.append(
                        {
                            "match_type": match_type,
                            "rea_id": candidate["rea_id"],
                            "sub_id": candidate["sub_id"],
                            "reranked_file": candidate["reranked_path"],
                            "search_query": payload.get("search query", ""),
                            "expected_reg_hits": reg_hits,
                        }
                    )

                realization_reports.append(
                    {
                        "realization_text": realization_text,
                        "matched_reranked_entries": candidate_reports,
                        "expected_reg_found": found_any_expected,
                    }
                )

            report_entries.append(
                {
                    "reg_id": item.get("reg_id", ""),
                    "clause": item.get("clause", ""),
                    "regulatory_text": item.get("regulatory_text", ""),
                    "deviation_found": item.get("deviation_found", None),
                    "realization_checks": realization_reports,
                }
            )

        return {
            "input_file": str(self.injections_json),
            "reranked_root": str(self.reranked_root),
            "summary": {
                "unit_count": len(report_entries),
                "matched_realization_count": matched_realization_count,
                "expected_reg_hit_count": expected_reg_hit_count,
            },
            "results": report_entries,
        }

    def run(self, output_json: str | Path) -> Path:
        report = self.build_report()
        output_path = Path(output_json).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        return output_path


def main() -> None:
    project_root = Path("/Users/my/Documents/projects/detectionDeviation")
    output_json = project_root / "evaluation" / "eu_ai_injections_reranked_positions.json"
    checker = EuAiInjectionRerankedChecker(root_dir=project_root)
    saved = checker.run(output_json=output_json)
    print(f"Saved: {saved}")


if __name__ == "__main__":
    main()
