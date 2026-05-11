from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _normalize(value: Any) -> str:
    return " ".join(str(value).split()).strip()


def _render_chunk_markdown(rows: list[dict[str, Any]], title: str) -> str:
    lines: list[str] = [f"# {title}", ""]

    if not rows:
        lines.append("No rows found.")
        lines.append("")
        return "\n".join(lines)

    for row in rows:
        if not isinstance(row, dict):
            continue

        reg_id = _normalize(row.get("reg_id", "")) or "UNKNOWN"
        clause = _normalize(row.get("clause", ""))
        considered_refs = row.get("considered_references", [])
        if not isinstance(considered_refs, list):
            considered_refs = []
        refs_text = ", ".join(_normalize(ref) for ref in considered_refs if _normalize(ref)) or "None"

        deviation_found = bool(row.get("deviation_found", False))
        deviations = row.get("deviations", [])
        if not isinstance(deviations, list):
            deviations = []
        top_analysis = _normalize(row.get("analysis", ""))

        lines.append(f"## {reg_id}")
        if clause:
            lines.append(f"- Clause: {clause}")
        lines.append(f"- Considered References: {refs_text}")
        lines.append(f"- Deviation Found: {deviation_found}")
        lines.append("")

        if deviations:
            lines.append("### Deviations")
            lines.append("")
            for index, deviation in enumerate(deviations, start=1):
                if not isinstance(deviation, dict):
                    continue
                deviation_type = _normalize(deviation.get("deviation_type", "")) or "N/A"
                analysis = _normalize(deviation.get("analysis", "")) or "N/A"
                lines.append(f"{index}. Type: {deviation_type}")
                lines.append(f"   Analysis: {analysis}")
            lines.append("")
        else:
            lines.append("### Deviations")
            lines.append("")
            lines.append("None")
            lines.append("")

        if top_analysis:
            lines.append("### Top-Level Analysis")
            lines.append("")
            lines.append(top_analysis)
            lines.append("")

    return "\n".join(lines).strip() + "\n"


def convert_json_to_md(input_json: Path, output_md: Path) -> Path:
    payload = json.loads(input_json.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"Expected JSON list in {input_json}")

    title = f"Expected Output - {input_json.parent.name}"
    markdown = _render_chunk_markdown(payload, title=title)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(markdown, encoding="utf-8")
    return output_md


def convert_goldstandard_root(goldstandard_root: Path, output_filename: str) -> list[Path]:
    saved: list[Path] = []
    chunk_dirs = sorted(path for path in goldstandard_root.iterdir() if path.is_dir())
    for chunk_dir in chunk_dirs:
        json_files = sorted(chunk_dir.glob("*.json"))
        if not json_files:
            continue
        # Prefer canonical "output.json", then fallback to first json.
        preferred = chunk_dir / "output.json"
        input_json = preferred if preferred.exists() else json_files[0]
        output_md = chunk_dir / output_filename
        saved.append(convert_json_to_md(input_json, output_md))
    return saved


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert goldstandard chunk JSON files to Markdown.")
    parser.add_argument(
        "--goldstandard-root",
        type=str,
        default="/Users/my/Documents/projects/detectionDeviation/goldstandard",
        help="Root folder containing chunk subfolders with JSON files.",
    )
    parser.add_argument(
        "--output-filename",
        type=str,
        default="output.md",
        help="Output markdown filename to write in each chunk folder.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(args.goldstandard_root).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(f"Goldstandard root not found: {root}")

    saved = convert_goldstandard_root(root, output_filename=args.output_filename)
    print(f"Converted {len(saved)} chunk file(s).")
    for path in saved:
        print(f"Saved Markdown: {path}")


if __name__ == "__main__":
    main()
