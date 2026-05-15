from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


TITLE_PATTERN = re.compile(r"^\s*Title\s*:\s*(.+)\s*$", flags=re.IGNORECASE)
REA_PATTERN = re.compile(r"^\s*(REA-\d+)\s*:\s*(.*)$", flags=re.IGNORECASE)
CHUNK_NUMBER_PATTERN = re.compile(r"^chunk(\d+)$", flags=re.IGNORECASE)


class ReaRequirementsExtractor:
    def __init__(self, input_txt_path: str | Path):
        self.input_txt_path = Path(input_txt_path).expanduser().resolve()

    @staticmethod
    def _normalize_spaces(value: str) -> str:
        return re.sub(r"\s+", " ", value).strip()

    def _fallback_rea_id_from_filename(self) -> str:
        """
        Derive REA ID from chunk filename:
        chunk1 -> REA-01
        chunk10 -> REA-10
        """
        stem = self.input_txt_path.stem.strip()
        match = CHUNK_NUMBER_PATTERN.match(stem)
        if match:
            return f"REA-{int(match.group(1)):02d}"
        # Conservative fallback if naming assumption is violated.
        return "REA-01"

    def extract(self) -> list[dict[str, Any]]:
        lines = self.input_txt_path.read_text(encoding="utf-8", errors="ignore").splitlines()

        rows: list[dict[str, Any]] = []
        current_title = ""
        current_item: dict[str, Any] | None = None
        found_rea_marker = False
        non_title_lines: list[str] = []

        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                continue

            title_match = TITLE_PATTERN.match(line)
            if title_match:
                current_title = self._normalize_spaces(title_match.group(1))
                continue

            rea_match = REA_PATTERN.match(line)
            if rea_match:
                found_rea_marker = True
                if current_item is not None:
                    current_item["text"] = self._normalize_spaces(str(current_item.get("text", "")))
                    rows.append(current_item)

                rea_id, text_part = rea_match.groups()
                current_item = {
                    "title": current_title,
                    "rea_id": rea_id.upper(),
                    "text": self._normalize_spaces(text_part),
                }
                continue

            non_title_lines.append(line)

            # Continuation line: belongs to current REA block.
            if current_item is not None:
                existing = str(current_item.get("text", "")).strip()
                continuation = self._normalize_spaces(line)
                if existing:
                    current_item["text"] = f"{existing} {continuation}"
                else:
                    current_item["text"] = continuation

        if current_item is not None:
            current_item["text"] = self._normalize_spaces(str(current_item.get("text", "")))
            rows.append(current_item)

        # Fallback mode: no REA markers in file -> one requirement row for whole chunk text.
        if not found_rea_marker:
            full_text = self._normalize_spaces(" ".join(non_title_lines))
            if full_text:
                rows = [
                    {
                        "title": current_title,
                        "rea_id": self._fallback_rea_id_from_filename(),
                        "text": full_text,
                    }
                ]
            else:
                rows = []

        return rows

    def save_json(self, output_json_path: str | Path) -> Path:
        output_path = Path(output_json_path).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(self.extract(), indent=2, ensure_ascii=False), encoding="utf-8")
        return output_path

    @staticmethod
    def process_folder(input_folder: str | Path, output_root_folder: str | Path) -> list[Path]:
        """
        Process all .txt files in input_folder.
        For each file <xy>.txt, output:
        <output_root_folder>/<xy>/<xy>_requirements.json
        """
        input_dir = Path(input_folder).expanduser().resolve()
        output_root = Path(output_root_folder).expanduser().resolve()
        if not input_dir.exists() or not input_dir.is_dir():
            raise FileNotFoundError(f"Input folder not found: {input_dir}")

        saved_paths: list[Path] = []
        for txt_file in sorted(input_dir.glob("*.txt")):
            stem = txt_file.stem
            output_json = output_root / stem / f"{stem}_requirements.json"
            extractor = ReaRequirementsExtractor(txt_file)
            saved_paths.append(extractor.save_json(output_json))
        return saved_paths


def main() -> None:
    project_root = Path("/Users/my/Documents/projects/detectionDeviation").expanduser().resolve()
    rea_input_name = "rea_with_injections"
    input_folder = project_root / "input" / rea_input_name / "chunked_texts"
    output_root = (
        project_root
        / "intermediate_results"
        / "01_preprocessing"
        / "reaPrep"
        / "01_extracting"
        / "rearequirementsextractor"
        / rea_input_name
    )

    saved_paths = ReaRequirementsExtractor.process_folder(input_folder, output_root)
    print(f"Processed {len(saved_paths)} REA chunk file(s).")
    for path in saved_paths:
        print(f"Saved REA requirements JSON: {path}")


if __name__ == "__main__":
    main()
