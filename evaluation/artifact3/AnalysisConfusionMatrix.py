from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


class AnalysisConfusionMatrix:
    """
    Build confusion-matrix-style analysis per chunk:
    compares Gold Standard vs System Output at REG-ID level for deviation detection.
    """

    def __init__(self, gold_root: str | Path, system_root: str | Path):
        self.gold_root = Path(gold_root).expanduser().resolve()
        self.system_root = Path(system_root).expanduser().resolve()

    @staticmethod
    def _normalize_chunk_name(name: str) -> str:
        return re.sub(r"[^a-z0-9]", "", name.strip().lower())

    @staticmethod
    def _chunk_sort_key(path: Path) -> tuple[int, int, str]:
        """
        Natural chunk ordering:
        chunk1, chunk2, ... chunk10
        Also handles names like 'chunk_1' or 'chunk 4'.
        """
        name = path.name.strip().lower()
        match = re.search(r"chunk\D*(\d+)", name)
        if match:
            return (0, int(match.group(1)), name)
        return (1, 10**9, name)

    @staticmethod
    def _safe_div(n: float, d: float) -> float:
        return float(n / d) if d else 0.0

    @classmethod
    def _prf(cls, tp: int, fp: int, fn: int) -> dict[str, float | int]:
        precision = cls._safe_div(tp, tp + fp)
        recall = cls._safe_div(tp, tp + fn)
        f1 = cls._safe_div(2 * precision * recall, precision + recall) if (precision + recall) else 0.0
        return {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": round(precision, 6),
            "recall": round(recall, 6),
            "f1": round(f1, 6),
        }

    @staticmethod
    def _extract_json_from_llm_response_payload(payload: dict[str, Any]) -> Any:
        choices = payload.get("choices", [])
        if not isinstance(choices, list) or not choices:
            raise ValueError("Invalid LLM response payload: missing choices.")
        first = choices[0] if isinstance(choices[0], dict) else {}
        message = first.get("message", {})
        if not isinstance(message, dict):
            raise ValueError("Invalid LLM response payload: missing message.")
        content = message.get("content", "")
        if not isinstance(content, str):
            raise ValueError("Invalid LLM response payload: content is not a string.")
        fenced = re.search(r"```json\s*(.*?)\s*```", content, flags=re.IGNORECASE | re.DOTALL)
        json_text = fenced.group(1).strip() if fenced else content.strip()
        return json.loads(json_text)

    @classmethod
    def _load_rows(cls, path: Path) -> list[dict[str, Any]]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        data: Any = payload
        if isinstance(payload, dict) and "choices" in payload:
            data = cls._extract_json_from_llm_response_payload(payload)
        if isinstance(data, dict):
            data = [data]
        if not isinstance(data, list):
            raise ValueError(f"Expected list-like data in {path}")
        return [row for row in data if isinstance(row, dict)]

    @staticmethod
    def _row_id(row: dict[str, Any]) -> str:
        reg_id = str(row.get("reg_id", "")).strip()
        if reg_id:
            return reg_id
        return str(row.get("policy_id", "")).strip()

    @staticmethod
    def _row_clause(row: dict[str, Any]) -> str:
        return str(row.get("clause", "")).strip()

    @staticmethod
    def _normalize_clause_key(value: str) -> str:
        # Keep alphanumerics and parentheses for GDPR clause specificity.
        return re.sub(r"[^a-z0-9()]+", "", str(value).strip().lower())

    @staticmethod
    def _article_root_from_key(key: str) -> str | None:
        """
        Extract article root from normalized keys:
        - art21 -> art21
        - art21(2) -> art21
        Returns None for non-standard combined keys like art33andart34.
        """
        match = re.match(r"^(art\d+)(?:\([^)]*\))?$", str(key).strip().lower())
        if not match:
            return None
        return match.group(1)

    @staticmethod
    def _row_deviation_found(row: dict[str, Any]) -> bool:
        deviations = row.get("deviations", [])
        if isinstance(deviations, list):
            if any(isinstance(item, dict) for item in deviations):
                return True
            if "deviation_found" in row:
                return bool(row.get("deviation_found"))
            return False
        return bool(row.get("deviation_found", False))

    @staticmethod
    def _row_deviation_count(row: dict[str, Any]) -> int:
        deviations = row.get("deviations", [])
        if isinstance(deviations, list):
            count = sum(1 for item in deviations if isinstance(item, dict))
            if count > 0:
                return count
        return 1 if bool(row.get("deviation_found", False)) else 0

    @classmethod
    def _build_map(cls, rows: list[dict[str, Any]]) -> dict[str, bool]:
        out: dict[str, bool] = {}
        for row in rows:
            reg_id = cls._row_id(row)
            if not reg_id:
                continue
            out[reg_id] = cls._row_deviation_found(row)
        return out

    @classmethod
    def _build_map_by_clause_or_id(cls, rows: list[dict[str, Any]]) -> dict[str, bool]:
        """
        Build map keyed by clause when present, otherwise by id.
        Useful when gold/system use different REG-ID namespaces.
        """
        out: dict[str, bool] = {}
        for row in rows:
            clause = cls._row_clause(row)
            key = cls._normalize_clause_key(clause) if clause else ""
            if not key:
                key = cls._row_id(row)
            if not key:
                continue
            deviation = cls._row_deviation_found(row)
            # OR-merge duplicates (if any duplicate has deviation, keep True).
            out[key] = bool(out.get(key, False) or deviation)
        return out

    @classmethod
    def _build_count_map(cls, rows: list[dict[str, Any]]) -> dict[str, int]:
        out: dict[str, int] = {}
        for row in rows:
            reg_id = cls._row_id(row)
            if not reg_id:
                continue
            out[reg_id] = out.get(reg_id, 0) + cls._row_deviation_count(row)
        return out

    @classmethod
    def _build_count_map_by_clause_or_id(cls, rows: list[dict[str, Any]]) -> dict[str, int]:
        out: dict[str, int] = {}
        for row in rows:
            clause = cls._row_clause(row)
            key = cls._normalize_clause_key(clause) if clause else ""
            if not key:
                key = cls._row_id(row)
            if not key:
                continue
            out[key] = out.get(key, 0) + cls._row_deviation_count(row)
        return out

    @staticmethod
    def _status_label(value: bool) -> str:
        return "Deviation (True)" if value else "Non-Deviation (False)"

    @staticmethod
    def _result_label(gold_value: bool, system_value: bool) -> str:
        if gold_value and system_value:
            return "True Positive (Hit)"
        if gold_value and (not system_value):
            return "False Negative (Miss)"
        if (not gold_value) and system_value:
            return "False Positive (Alarm)"
        return "True Negative"

    @classmethod
    def compare_chunk(cls, gold_file: Path, system_files: list[Path]) -> dict[str, Any]:
        gold_rows = cls._load_rows(gold_file)
        system_rows: list[dict[str, Any]] = []
        for system_file in system_files:
            system_rows.extend(cls._load_rows(system_file))
        gold_map = cls._build_map(gold_rows)
        system_map = cls._build_map(system_rows)
        gold_count_map = cls._build_count_map(gold_rows)
        system_count_map = cls._build_count_map(system_rows)

        all_ids = sorted(set(gold_map.keys()) | set(system_map.keys()))
        tp = fp = fn = tn = 0

        table_rows: list[dict[str, Any]] = []
        tn_ids: list[str] = []
        for reg_id in all_ids:
            g = bool(gold_map.get(reg_id, False))
            s = bool(system_map.get(reg_id, False))
            result = cls._result_label(g, s)
            if result == "True Positive (Hit)":
                tp += 1
                table_rows.append(
                    {
                        "ID": reg_id,
                        "Gold Standard": cls._status_label(g),
                        "System Output": cls._status_label(s),
                        "Result": result,
                    }
                )
            elif result == "False Negative (Miss)":
                fn += 1
                table_rows.append(
                    {
                        "ID": reg_id,
                        "Gold Standard": cls._status_label(g),
                        "System Output": cls._status_label(s),
                        "Result": result,
                    }
                )
            elif result == "False Positive (Alarm)":
                fp += 1
                table_rows.append(
                    {
                        "ID": reg_id,
                        "Gold Standard": cls._status_label(g),
                        "System Output": cls._status_label(s),
                        "Result": result,
                    }
                )
            else:
                tn += 1
                tn_ids.append(reg_id)

        if tn > 0:
            table_rows.append(
                {
                    "ID": f"Others ({tn})",
                    "Gold Standard": "Non-Deviation (False)",
                    "System Output": "Non-Deviation (False)",
                    "Result": "True Negatives",
                    "tn_reg_ids": tn_ids,
                }
            )

        all_count_ids = sorted(set(gold_count_map.keys()) | set(system_count_map.keys()))
        count_hit_total = count_miss_total = count_alarm_total = 0
        count_table: list[dict[str, Any]] = []
        for reg_id in all_count_ids:
            gold_count = int(gold_count_map.get(reg_id, 0))
            system_count = int(system_count_map.get(reg_id, 0))
            if gold_count == 0 and system_count == 0:
                continue
            hit = min(gold_count, system_count)
            miss = max(gold_count - hit, 0)
            alarm = max(system_count - hit, 0)
            count_hit_total += hit
            count_miss_total += miss
            count_alarm_total += alarm
            count_table.append(
                {
                    "ID": reg_id,
                    "Gold Deviations": gold_count,
                    "System Deviations": system_count,
                    "Hit": hit,
                    "Miss": miss,
                    "Alarm": alarm,
                }
            )

        return {
            "expected_file": str(gold_file),
            "actual_file": str(system_files[0]) if system_files else "",
            "actual_files": [str(path) for path in system_files],
            "table": table_rows,
            "calculation_matrix": {
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "tn": tn,
                **cls._prf(tp, fp, fn),
            },
            "deviation_count_matrix": {
                "hit": count_hit_total,
                "miss": count_miss_total,
                "alarm": count_alarm_total,
                "gold_total": count_hit_total + count_miss_total,
                "system_total": count_hit_total + count_alarm_total,
                "count_recall": round(cls._safe_div(count_hit_total, count_hit_total + count_miss_total), 6),
                "count_precision": round(cls._safe_div(count_hit_total, count_hit_total + count_alarm_total), 6),
            },
            "deviation_count_table": count_table,
        }

    @staticmethod
    def _find_gold_output_json(chunk_dir: Path) -> Path | None:
        preferred = chunk_dir / "output.json"
        if preferred.exists():
            return preferred
        typo = chunk_dir / "ouput.json"
        if typo.exists():
            return typo
        candidates = sorted(chunk_dir.glob("*.json"))
        return candidates[0] if candidates else None

    @staticmethod
    def _find_system_output_jsons(chunk_dir: Path) -> list[Path]:
        # Preferred: all normalized extraction files (single and multi-response variants)
        # e.g., llm_extracted_normalized.json, llm_extracted_normalized_01.json, ...
        normalized_files = sorted(chunk_dir.glob("llm_extracted_normalized*.json"))
        if normalized_files:
            return normalized_files
        # Fallback: raw LLM responses if normalized files are not present.
        raw_files = sorted(chunk_dir.glob("llm_response*.json"))
        if raw_files:
            return raw_files
        return []

    def analyze_all_chunks(self) -> dict[str, Any]:
        if not self.gold_root.exists() or not self.gold_root.is_dir():
            raise FileNotFoundError(f"Gold root not found: {self.gold_root}")
        if not self.system_root.exists() or not self.system_root.is_dir():
            raise FileNotFoundError(f"System root not found: {self.system_root}")

        system_chunks = sorted(
            (path for path in self.system_root.iterdir() if path.is_dir()),
            key=self._chunk_sort_key,
        )
        system_by_exact: dict[str, Path] = {path.name: path for path in system_chunks}
        system_by_norm: dict[str, list[Path]] = {}
        for system_chunk in system_chunks:
            norm_key = self._normalize_chunk_name(system_chunk.name)
            system_by_norm.setdefault(norm_key, []).append(system_chunk)

        chunk_reports: list[dict[str, Any]] = []
        skipped: list[dict[str, str]] = []
        total_tp = total_fp = total_fn = total_tn = 0

        for gold_chunk in sorted(
            (path for path in self.gold_root.iterdir() if path.is_dir()),
            key=self._chunk_sort_key,
        ):
            # 1) Prefer exact directory-name match (e.g. chunk1 -> chunk1).
            # 2) Fallback to normalized match (e.g. chunk1 -> chunk_1).
            system_chunk = system_by_exact.get(gold_chunk.name)
            if system_chunk is None:
                norm = self._normalize_chunk_name(gold_chunk.name)
                candidates = system_by_norm.get(norm, [])
                system_chunk = candidates[0] if candidates else None
            if system_chunk is None:
                skipped.append({"chunk": gold_chunk.name, "reason": "matching system chunk not found"})
                continue

            gold_file = self._find_gold_output_json(gold_chunk)
            system_files = self._find_system_output_jsons(system_chunk)
            if gold_file is None:
                skipped.append({"chunk": gold_chunk.name, "reason": "gold output json missing"})
                continue
            if not system_files:
                skipped.append({"chunk": gold_chunk.name, "reason": "system output json missing"})
                continue

            report = self.compare_chunk(gold_file, system_files)
            report["chunk"] = gold_chunk.name
            chunk_reports.append(report)

            calc = report["calculation_matrix"]
            total_tp += int(calc["tp"])
            total_fp += int(calc["fp"])
            total_fn += int(calc["fn"])
            total_tn += int(calc["tn"])

        overall_calc = {
            "tp": total_tp,
            "fp": total_fp,
            "fn": total_fn,
            "tn": total_tn,
            **self._prf(total_tp, total_fp, total_fn),
            "accuracy": round(self._safe_div(total_tp + total_tn, total_tp + total_fp + total_fn + total_tn), 6),
        }

        return {
            "gold_root": str(self.gold_root),
            "system_root": str(self.system_root),
            "evaluated_chunks": len(chunk_reports),
            "skipped_chunks": len(skipped),
            "overall_calculation_matrix": overall_calc,
            "chunks": chunk_reports,
            "skipped": skipped,
        }

    @staticmethod
    def _render_chunk_table_md(rows: list[dict[str, Any]]) -> list[str]:
        lines = [
            "| ID | Gold Standard | System Output | Result |",
            "|---|---|---|---|",
        ]
        for row in rows:
            lines.append(
                f"| {row.get('ID','')} | {row.get('Gold Standard','')} | {row.get('System Output','')} | {row.get('Result','')} |"
            )
        return lines

    @staticmethod
    def _render_deviation_count_table_md(rows: list[dict[str, Any]]) -> list[str]:
        lines = [
            "| ID | Gold Deviations | System Deviations | Hit | Miss | Alarm |",
            "|---|---:|---:|---:|---:|---:|",
        ]
        for row in rows:
            lines.append(
                f"| {row.get('ID','')} | {row.get('Gold Deviations',0)} | {row.get('System Deviations',0)} | {row.get('Hit',0)} | {row.get('Miss',0)} | {row.get('Alarm',0)} |"
            )
        return lines

    def save_json(self, output_json: str | Path) -> Path:
        result = self.analyze_all_chunks()
        output_path = Path(output_json).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        return output_path

    def save_markdown(self, output_md: str | Path) -> Path:
        result = self.analyze_all_chunks()
        output_path = Path(output_md).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        lines: list[str] = ["# Analysis Confusion Matrix", ""]
        lines.append(f"- Evaluated chunks: {result.get('evaluated_chunks', 0)}")
        lines.append(f"- Skipped chunks: {result.get('skipped_chunks', 0)}")
        lines.append("")
        overall = result.get("overall_calculation_matrix", {})
        lines.append("## Overall Calculation Matrix")
        lines.append("")
        lines.append(f"- TP: {overall.get('tp', 0)}")
        lines.append(f"- FP: {overall.get('fp', 0)}")
        lines.append(f"- FN: {overall.get('fn', 0)}")
        lines.append(f"- TN: {overall.get('tn', 0)}")
        lines.append(f"- Precision: {overall.get('precision', 0.0)}")
        lines.append(f"- Recall: {overall.get('recall', 0.0)}")
        lines.append(f"- F1: {overall.get('f1', 0.0)}")
        lines.append(f"- Accuracy: {overall.get('accuracy', 0.0)}")
        lines.append("")

        for chunk in result.get("chunks", []):
            if not isinstance(chunk, dict):
                continue
            lines.append(f"## Chunk: {chunk.get('chunk', 'UNKNOWN')}")
            lines.append("")
            lines.append(f"### Expected: `{chunk.get('expected_file', '')}`")
            lines.append(f"### Actual: `{chunk.get('actual_file', '')}`")
            actual_files = chunk.get("actual_files", [])
            if isinstance(actual_files, list) and len(actual_files) > 1:
                lines.append(f"### Actual Files Count: `{len(actual_files)}`")
            lines.append("")
            lines.extend(self._render_chunk_table_md(chunk.get("table", [])))
            lines.append("")
            calc = chunk.get("calculation_matrix", {})
            lines.append("### Calculation Matrix")
            lines.append("")
            lines.append(f"- TP: {calc.get('tp', 0)}")
            lines.append(f"- FP: {calc.get('fp', 0)}")
            lines.append(f"- FN: {calc.get('fn', 0)}")
            lines.append(f"- TN: {calc.get('tn', 0)}")
            lines.append(f"- Precision: {calc.get('precision', 0.0)}")
            lines.append(f"- Recall: {calc.get('recall', 0.0)}")
            lines.append(f"- F1: {calc.get('f1', 0.0)}")
            lines.append("")
            count_calc = chunk.get("deviation_count_matrix", {})
            lines.append("### Deviation Count Matrix")
            lines.append("")
            lines.append(f"- Hit: {count_calc.get('hit', 0)}")
            lines.append(f"- Miss: {count_calc.get('miss', 0)}")
            lines.append(f"- Alarm: {count_calc.get('alarm', 0)}")
            lines.append(f"- Gold Total: {count_calc.get('gold_total', 0)}")
            lines.append(f"- System Total: {count_calc.get('system_total', 0)}")
            lines.append(f"- Count Precision: {count_calc.get('count_precision', 0.0)}")
            lines.append(f"- Count Recall: {count_calc.get('count_recall', 0.0)}")
            lines.append("")
            lines.extend(self._render_deviation_count_table_md(chunk.get("deviation_count_table", [])))
            lines.append("")

        if result.get("skipped"):
            lines.append("## Skipped")
            lines.append("")
            for item in result.get("skipped", []):
                if isinstance(item, dict):
                    lines.append(f"- {item.get('chunk', 'UNKNOWN')}: {item.get('reason', 'n/a')}")
            lines.append("")

        output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        return output_path

    def build_merged_system_output(self, output_json: str | Path) -> Path:
        """
        Merge all chunk-level system outputs into one deduplicated JSON.
        Preferred key: normalized clause; fallback key: id.
        """
        if not self.system_root.exists() or not self.system_root.is_dir():
            raise FileNotFoundError(f"System root not found: {self.system_root}")

        merged: dict[str, dict[str, Any]] = {}
        for chunk_dir in sorted((path for path in self.system_root.iterdir() if path.is_dir()), key=self._chunk_sort_key):
            system_files = self._find_system_output_jsons(chunk_dir)
            if not system_files:
                continue
            for system_file in system_files:
                rows = self._load_rows(system_file)
                for row in rows:
                    if not isinstance(row, dict):
                        continue
                    clause = self._row_clause(row)
                    key = self._normalize_clause_key(clause) if clause else ""
                    if not key:
                        key = self._row_id(row)
                    if not key:
                        continue
                    deviation = self._row_deviation_found(row)
                    if key not in merged:
                        merged[key] = {
                            "reg_id": self._row_id(row),
                            "clause": clause,
                            "deviation_found": bool(deviation),
                            "sources": [str(system_file)],
                        }
                    else:
                        merged[key]["deviation_found"] = bool(merged[key].get("deviation_found", False) or deviation)
                        srcs = merged[key].get("sources", [])
                        src = str(system_file)
                        if isinstance(srcs, list) and src not in srcs:
                            srcs.append(src)
                            merged[key]["sources"] = srcs

        output_path = Path(output_json).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_payload = list(merged.values())
        output_path.write_text(json.dumps(output_payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return output_path

    @classmethod
    def compare_merged_files(cls, gold_file: Path, merged_system_file: Path) -> dict[str, Any]:
        gold_rows = cls._load_rows(gold_file)
        system_rows = cls._load_rows(merged_system_file)
        gold_map = cls._build_map_by_clause_or_id(gold_rows)
        system_map = cls._build_map_by_clause_or_id(system_rows)
        gold_count_map = cls._build_count_map_by_clause_or_id(gold_rows)
        system_count_map = cls._build_count_map_by_clause_or_id(system_rows)

        # Gold-driven scope normalization:
        # If gold contains article-level key (e.g., art21), collapse system paragraph keys
        # for that same article (art21(2), art21(3), ...) into article-level key.
        gold_article_level_roots: set[str] = set()
        for key in gold_map.keys():
            if "(" in key:
                continue
            root = cls._article_root_from_key(key)
            if root:
                gold_article_level_roots.add(root)

        collapsed_system: dict[str, bool] = {}
        for key, value in system_map.items():
            root = cls._article_root_from_key(key)
            if root and root in gold_article_level_roots:
                target = root
            else:
                target = key
            collapsed_system[target] = bool(collapsed_system.get(target, False) or value)
        system_map = collapsed_system

        collapsed_system_count: dict[str, int] = {}
        for key, value in system_count_map.items():
            root = cls._article_root_from_key(key)
            if root and root in gold_article_level_roots:
                target = root
            else:
                target = key
            collapsed_system_count[target] = collapsed_system_count.get(target, 0) + int(value)
        system_count_map = collapsed_system_count

        collapsed_gold_count: dict[str, int] = {}
        for key, value in gold_count_map.items():
            root = cls._article_root_from_key(key)
            if root and root in gold_article_level_roots:
                target = root
            else:
                target = key
            collapsed_gold_count[target] = collapsed_gold_count.get(target, 0) + int(value)
        gold_count_map = collapsed_gold_count

        all_ids = sorted(set(gold_map.keys()) | set(system_map.keys()))
        tp = fp = fn = tn = 0
        table_rows: list[dict[str, Any]] = []
        tn_ids: list[str] = []

        for key in all_ids:
            g = bool(gold_map.get(key, False))
            s = bool(system_map.get(key, False))
            result = cls._result_label(g, s)
            if result == "True Positive (Hit)":
                tp += 1
                table_rows.append({"ID": key, "Gold Standard": cls._status_label(g), "System Output": cls._status_label(s), "Result": result})
            elif result == "False Negative (Miss)":
                fn += 1
                table_rows.append({"ID": key, "Gold Standard": cls._status_label(g), "System Output": cls._status_label(s), "Result": result})
            elif result == "False Positive (Alarm)":
                fp += 1
                table_rows.append({"ID": key, "Gold Standard": cls._status_label(g), "System Output": cls._status_label(s), "Result": result})
            else:
                tn += 1
                tn_ids.append(key)

        if tn > 0:
            table_rows.append(
                {
                    "ID": f"Others ({tn})",
                    "Gold Standard": "Non-Deviation (False)",
                    "System Output": "Non-Deviation (False)",
                    "Result": "True Negatives",
                    "tn_keys": tn_ids,
                }
            )

        all_count_ids = sorted(set(gold_count_map.keys()) | set(system_count_map.keys()))
        count_hit_total = count_miss_total = count_alarm_total = 0
        count_table: list[dict[str, Any]] = []
        for key in all_count_ids:
            gold_count = int(gold_count_map.get(key, 0))
            system_count = int(system_count_map.get(key, 0))
            if gold_count == 0 and system_count == 0:
                continue
            hit = min(gold_count, system_count)
            miss = max(gold_count - hit, 0)
            alarm = max(system_count - hit, 0)
            count_hit_total += hit
            count_miss_total += miss
            count_alarm_total += alarm
            count_table.append(
                {
                    "ID": key,
                    "Gold Deviations": gold_count,
                    "System Deviations": system_count,
                    "Hit": hit,
                    "Miss": miss,
                    "Alarm": alarm,
                }
            )

        return {
            "mode": "merged_injection_analysis",
            "expected_file": str(gold_file),
            "actual_file": str(merged_system_file),
            "table": table_rows,
            "calculation_matrix": {
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "tn": tn,
                **cls._prf(tp, fp, fn),
                "accuracy": round(cls._safe_div(tp + tn, tp + fp + fn + tn), 6),
            },
            "deviation_count_matrix": {
                "hit": count_hit_total,
                "miss": count_miss_total,
                "alarm": count_alarm_total,
                "gold_total": count_hit_total + count_miss_total,
                "system_total": count_hit_total + count_alarm_total,
                "count_recall": round(cls._safe_div(count_hit_total, count_hit_total + count_miss_total), 6),
                "count_precision": round(cls._safe_div(count_hit_total, count_hit_total + count_alarm_total), 6),
            },
            "deviation_count_table": count_table,
        }

    def save_merged_injection_json(
        self,
        gold_json_file: str | Path,
        merged_system_json_file: str | Path,
        output_json: str | Path,
    ) -> Path:
        result = self.compare_merged_files(
            gold_file=Path(gold_json_file).expanduser().resolve(),
            merged_system_file=Path(merged_system_json_file).expanduser().resolve(),
        )
        output_path = Path(output_json).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        return output_path

    def save_merged_injection_markdown(
        self,
        gold_json_file: str | Path,
        merged_system_json_file: str | Path,
        output_md: str | Path,
    ) -> Path:
        result = self.compare_merged_files(
            gold_file=Path(gold_json_file).expanduser().resolve(),
            merged_system_file=Path(merged_system_json_file).expanduser().resolve(),
        )
        output_path = Path(output_md).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        lines: list[str] = ["# Analysis Confusion Matrix (Merged Injections)", ""]
        lines.append(f"- Expected: `{result.get('expected_file', '')}`")
        lines.append(f"- Actual: `{result.get('actual_file', '')}`")
        lines.append("")
        calc = result.get("calculation_matrix", {})
        lines.append(f"- TP: {calc.get('tp', 0)}")
        lines.append(f"- FP: {calc.get('fp', 0)}")
        lines.append(f"- FN: {calc.get('fn', 0)}")
        lines.append(f"- TN: {calc.get('tn', 0)}")
        lines.append(f"- Precision: {calc.get('precision', 0.0)}")
        lines.append(f"- Recall: {calc.get('recall', 0.0)}")
        lines.append(f"- F1: {calc.get('f1', 0.0)}")
        lines.append(f"- Accuracy: {calc.get('accuracy', 0.0)}")
        lines.append("")
        count_calc = result.get("deviation_count_matrix", {})
        lines.append("## Deviation Count Matrix")
        lines.append("")
        lines.append(f"- Hit: {count_calc.get('hit', 0)}")
        lines.append(f"- Miss: {count_calc.get('miss', 0)}")
        lines.append(f"- Alarm: {count_calc.get('alarm', 0)}")
        lines.append(f"- Gold Total: {count_calc.get('gold_total', 0)}")
        lines.append(f"- System Total: {count_calc.get('system_total', 0)}")
        lines.append(f"- Count Precision: {count_calc.get('count_precision', 0.0)}")
        lines.append(f"- Count Recall: {count_calc.get('count_recall', 0.0)}")
        lines.append("")
        lines.extend(self._render_deviation_count_table_md(result.get("deviation_count_table", [])))
        lines.append("")
        lines.extend(self._render_chunk_table_md(result.get("table", [])))
        lines.append("")
        output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        return output_path


def main() -> None:
    project_root = Path("/Users/my/Documents/projects/detectionDeviation")
    gold_root = project_root / "goldstandard"

    system_root = project_root / "intermediate_outputs" / "artifact_03_reranked_overlapwindows"
    out_json = project_root / "evaluation" / "artifact3" / "artifact_03_reranked_overlapwindows"/"analysis_confusion_matrix.json"
    out_md = project_root / "evaluation" / "artifact3" / "artifact_03_reranked_overlapwindows"/ "analysis_confusion_matrix.md"

    # system_root = project_root / "intermediate_outputs" / "artifact_01"
    # out_json = project_root / "evaluation" / "artifact3" / "without_reranker" /"analysis_confusion_matrix.json"
    # out_md = project_root / "evaluation" / "artifact3" / "without_reranker"/ "analysis_confusion_matrix.md"

    evaluator = AnalysisConfusionMatrix(gold_root=gold_root, system_root=system_root)
    saved_json = evaluator.save_json(out_json)
    saved_md = evaluator.save_markdown(out_md)

    gold_injection_json = project_root / "goldstandard" / "rea_with_injections.json"
    merged_system_json = project_root / "evaluation" / "artifact3" / "artifact_03_reranked_overlapwindows" / "merged_llm_extracted_normalized.json"
    merged_eval_json = project_root / "evaluation" / "artifact3" / "artifact_03_reranked_overlapwindows" / "analysis_confusion_matrix_merged_injections.json"
    merged_eval_md = project_root / "evaluation" / "artifact3" / "artifact_03_reranked_overlapwindows" / "analysis_confusion_matrix_merged_injections.md"

    merged_saved = evaluator.build_merged_system_output(merged_system_json)
    merged_json_saved = evaluator.save_merged_injection_json(gold_injection_json, merged_saved, merged_eval_json)
    merged_md_saved = evaluator.save_merged_injection_markdown(gold_injection_json, merged_saved, merged_eval_md)

    print(f"Saved JSON: {saved_json}")
    print(f"Saved Markdown: {saved_md}")
    print(f"Saved merged system JSON: {merged_saved}")
    print(f"Saved merged injection eval JSON: {merged_json_saved}")
    print(f"Saved merged injection eval Markdown: {merged_md_saved}")


if __name__ == "__main__":
    main()
