from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def _normalize_text(value: Any) -> str:
    return " ".join(str(value).split()).strip()


def _flatten_goldstandard_rows(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        raise ValueError("Goldstandard JSON must be a list of objects.")

    rows: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue

        reg_id = _normalize_text(item.get("reg_id", ""))
        clause = _normalize_text(item.get("clause", ""))
        considered_refs = item.get("considered_references", [])
        if not isinstance(considered_refs, list):
            considered_refs = []
        considered_refs_text = ", ".join(_normalize_text(x) for x in considered_refs if _normalize_text(x))

        deviation_found = bool(item.get("deviation_found", False))
        top_analysis = _normalize_text(item.get("analysis", ""))
        deviations = item.get("deviations", [])
        if not isinstance(deviations, list):
            deviations = []

        if not deviations:
            rows.append(
                {
                    "reg_id": reg_id,
                    "clause": clause,
                    "considered_references": considered_refs_text,
                    "deviation_found": deviation_found,
                    "deviation_index": "",
                    "deviation_type": "",
                    "deviation_analysis": "",
                    "top_level_analysis": top_analysis,
                }
            )
            continue

        idx = 0
        for deviation in deviations:
            if not isinstance(deviation, dict):
                continue
            idx += 1
            rows.append(
                {
                    "reg_id": reg_id,
                    "clause": clause,
                    "considered_references": considered_refs_text,
                    "deviation_found": True,
                    "deviation_index": idx,
                    "deviation_type": _normalize_text(deviation.get("deviation_type", "")),
                    "deviation_analysis": _normalize_text(deviation.get("analysis", "")),
                    "top_level_analysis": top_analysis,
                }
            )

        if idx == 0:
            rows.append(
                {
                    "reg_id": reg_id,
                    "clause": clause,
                    "considered_references": considered_refs_text,
                    "deviation_found": deviation_found,
                    "deviation_index": "",
                    "deviation_type": "",
                    "deviation_analysis": "",
                    "top_level_analysis": top_analysis,
                }
            )

    return rows


def convert_file(input_json: Path, output_csv: Path) -> Path:
    payload = json.loads(input_json.read_text(encoding="utf-8"))
    rows = _flatten_goldstandard_rows(payload)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "reg_id",
        "clause",
        "considered_references",
        "deviation_found",
        "deviation_index",
        "deviation_type",
        "deviation_analysis",
        "top_level_analysis",
    ]
    with output_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    return output_csv


def convert_folder(input_dir: Path, output_dir: Path) -> list[Path]:
    saved_paths: list[Path] = []
    for json_file in sorted(input_dir.rglob("*.json")):
        rel = json_file.relative_to(input_dir)
        target = output_dir / rel.with_suffix(".csv")
        saved_paths.append(convert_file(json_file, target))
    return saved_paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert goldstandard JSON to CSV.")
    parser.add_argument("--input-json", type=str, default="", help="Path to a single goldstandard JSON file.")
    parser.add_argument("--output-csv", type=str, default="", help="Path to output CSV file for single-file mode.")
    parser.add_argument("--input-dir", type=str, default="", help="Path to folder containing goldstandard JSON files.")
    parser.add_argument("--output-dir", type=str, default="", help="Path to output folder for folder mode.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.input_json:
        input_json = Path(args.input_json).expanduser().resolve()
        if not input_json.exists():
            raise FileNotFoundError(f"Input JSON not found: {input_json}")

        output_csv = Path(args.output_csv).expanduser().resolve() if args.output_csv else input_json.with_suffix(".csv")
        saved = convert_file(input_json, output_csv)
        print(f"Saved CSV: {saved}")
        return

    if args.input_dir:
        input_dir = Path(args.input_dir).expanduser().resolve()
        if not input_dir.exists() or not input_dir.is_dir():
            raise FileNotFoundError(f"Input directory not found: {input_dir}")
        output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else input_dir
        saved_paths = convert_folder(input_dir, output_dir)
        print(f"Converted {len(saved_paths)} file(s).")
        for path in saved_paths:
            print(f"Saved CSV: {path}")
        return

    raise ValueError("Provide either --input-json (single file) or --input-dir (folder mode).")


if __name__ == "__main__":
    main()

