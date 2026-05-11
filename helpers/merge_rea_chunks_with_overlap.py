from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


CHUNK_FILE_PATTERN = re.compile(r"^chunk(\d+)\.txt$", re.IGNORECASE)


@dataclass(frozen=True)
class ChunkFile:
    number: int
    path: Path


def _discover_chunks(input_dir: Path) -> List[ChunkFile]:
    chunks: List[ChunkFile] = []
    for path in sorted(input_dir.iterdir()):
        if not path.is_file():
            continue
        match = CHUNK_FILE_PATTERN.match(path.name)
        if not match:
            continue
        chunks.append(ChunkFile(number=int(match.group(1)), path=path))
    return sorted(chunks, key=lambda item: item.number)


def _load_chunk_texts(chunks: List[ChunkFile]) -> Dict[int, str]:
    result: Dict[int, str] = {}
    for chunk in chunks:
        result[chunk.number] = chunk.path.read_text(encoding="utf-8").strip()
    return result


def merge_adjacent_chunks_with_overlap(
    input_dir: Path,
    output_dir: Path,
    overlap: int = 1,
    add_chunk_markers: bool = True,
) -> dict:
    """
    Build anchor-based overlapping chunk windows.

    Example with overlap=1:
      chunk2 output = chunk1 + chunk2 + chunk3

    Output files keep anchor naming (chunkN.txt), so evaluation against
    per-chunk goldstandard remains compatible.
    """
    if overlap < 0:
        raise ValueError("overlap must be >= 0")

    chunks = _discover_chunks(input_dir)
    if not chunks:
        raise FileNotFoundError(f"No files matching chunk*.txt in: {input_dir}")

    chunk_numbers = [chunk.number for chunk in chunks]
    min_idx = min(chunk_numbers)
    max_idx = max(chunk_numbers)
    texts = _load_chunk_texts(chunks)

    output_dir.mkdir(parents=True, exist_ok=True)
    written_files: List[str] = []

    for anchor in chunk_numbers:
        start = max(min_idx, anchor - overlap)
        end = min(max_idx, anchor + overlap)

        merged_parts: List[str] = []
        for idx in range(start, end + 1):
            text = texts.get(idx, "").strip()
            if not text:
                continue
            if add_chunk_markers:
                merged_parts.append(f"[chunk{idx}]\n{text}")
            else:
                merged_parts.append(text)

        merged_text = "\n\n".join(merged_parts).strip()
        out_file = output_dir / f"chunk{anchor}.txt"
        out_file.write_text(merged_text + "\n", encoding="utf-8")
        written_files.append(str(out_file))

    return {
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "overlap": overlap,
        "add_chunk_markers": add_chunk_markers,
        "files_written": len(written_files),
        "written_files": written_files,
    }


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    input_dir = root / "input" / "rea"
    output_dir = root / "input" / "rea_windowed_overlap1"

    result = merge_adjacent_chunks_with_overlap(
        input_dir=input_dir,
        output_dir=output_dir,
        overlap=1,
        add_chunk_markers=False,
    )
    print(result)


if __name__ == "__main__":
    main()
