from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path


CHUNK_PATTERN = re.compile(r"^chunk(\d+)\.txt$", re.IGNORECASE)
REA_PREFIX_PATTERN = re.compile(r"^\s*REA-\d+\s*:\s*", re.IGNORECASE)


@dataclass(frozen=True)
class ChunkFile:
    index: int
    path: Path


class ChunkedTextOverlapBuilder:
    """
    Build anchor-based overlapping windows from chunk*.txt files.
    """

    def __init__(self, overlap_hops: int = 1) -> None:
        if overlap_hops < 0:
            raise ValueError("overlap_hops must be >= 0")
        self.overlap_hops = overlap_hops

    @staticmethod
    def _discover_chunk_files(input_dir: Path) -> list[ChunkFile]:
        chunk_files: list[ChunkFile] = []
        for path in input_dir.iterdir():
            if not path.is_file():
                continue
            match = CHUNK_PATTERN.match(path.name)
            if not match:
                continue
            chunk_files.append(ChunkFile(index=int(match.group(1)), path=path))
        return sorted(chunk_files, key=lambda item: item.index)

    @staticmethod
    def _strip_rea_prefix(text: str) -> str:
        """
        Remove leading REA-ID prefix like 'REA-01: ' from chunk text.
        """
        return REA_PREFIX_PATTERN.sub("", text, count=1).strip()

    @staticmethod
    def _load_chunk_text_map(chunk_files: list[ChunkFile]) -> dict[int, str]:
        text_map: dict[int, str] = {}
        for item in chunk_files:
            raw_text = item.path.read_text(encoding="utf-8").strip()
            text_map[item.index] = ChunkedTextOverlapBuilder._strip_rea_prefix(raw_text)
        return text_map

    def build_overlapping_chunks(self, input_dir: str | Path, output_dir: str | Path) -> dict:
        src_dir = Path(input_dir).expanduser().resolve()
        dst_dir = Path(output_dir).expanduser().resolve()
        dst_dir.mkdir(parents=True, exist_ok=True)

        chunk_files = self._discover_chunk_files(src_dir)
        if not chunk_files:
            raise FileNotFoundError(f"No chunk*.txt files found in: {src_dir}")

        text_map = self._load_chunk_text_map(chunk_files)
        chunk_indices = [item.index for item in chunk_files]
        index_set = set(chunk_indices)
        min_index = min(chunk_indices)
        max_index = max(chunk_indices)

        # Remove previous chunk*.txt to avoid stale files.
        for existing in dst_dir.glob("chunk*.txt"):
            if CHUNK_PATTERN.match(existing.name):
                existing.unlink(missing_ok=True)

        written_files: list[str] = []
        manifest_rows: list[dict] = []

        for anchor in chunk_indices:
            neighbors: list[int] = []
            for idx in range(max(min_index, anchor - self.overlap_hops), min(max_index, anchor + self.overlap_hops) + 1):
                if idx in index_set:
                    neighbors.append(idx)

            merged_parts = [text_map[idx] for idx in neighbors if text_map.get(idx)]
            merged_text = "\n\n".join(merged_parts).strip()

            out_file = dst_dir / f"chunk{anchor}.txt"
            out_file.write_text(merged_text + "\n", encoding="utf-8")
            written_files.append(str(out_file))
            manifest_rows.append(
                {
                    "anchor_chunk": f"chunk{anchor}",
                    "merged_from_chunks": [f"chunk{idx}" for idx in neighbors],
                    "output_file": str(out_file),
                }
            )

        manifest_path = dst_dir / "overlap_manifest.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "input_dir": str(src_dir),
                    "output_dir": str(dst_dir),
                    "overlap_hops": self.overlap_hops,
                    "count": len(manifest_rows),
                    "chunks": manifest_rows,
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        return {
            "input_dir": str(src_dir),
            "output_dir": str(dst_dir),
            "overlap_hops": self.overlap_hops,
            "files_written": len(written_files),
            "manifest_file": str(manifest_path),
        }


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    input_dir = project_root / "input" / "rea_no_injections" / "chunked_texts"
    output_dir = project_root / "input" / "rea_no_injections" / "chunked_texts_overlapping_window"

    builder = ChunkedTextOverlapBuilder(overlap_hops=1)
    result = builder.build_overlapping_chunks(input_dir=input_dir, output_dir=output_dir)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
