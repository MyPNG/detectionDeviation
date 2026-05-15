from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ChunkSplitResult:
    """Summary of one splitter run."""

    input_txt: str
    output_dir: str
    chunk_count: int
    rea_count: int
    chunk_files: list[str]
    manifest_json: str


class ReaChunkSplitter:
    """
    Split one REA full-text .txt file into chunked .txt files.

    Output chunk format mirrors your existing `chunked_texts` style:
      REA-01: ...
      REA-02: ...
      REA-03: ...

    with approximately 3 REA entries per chunk file.
    """

    def __init__(
        self,
        input_txt_path: str | Path,
        output_chunk_dir: str | Path,
        entries_per_chunk: int = 3,
    ):
        self.input_txt_path = Path(input_txt_path).expanduser().resolve()
        self.output_chunk_dir = Path(output_chunk_dir).expanduser().resolve()
        self.entries_per_chunk = max(1, int(entries_per_chunk))

    @staticmethod
    def _normalize_spaces(text: str) -> str:
        """Collapse repeated whitespace and trim."""
        return re.sub(r"\s+", " ", text).strip()

    def _read_logical_lines(self) -> list[str]:
        """
        Read input text and keep non-empty logical lines.

        A logical line is one non-empty line from the source file.
        This keeps behavior predictable for manual policy texts.
        """
        if not self.input_txt_path.exists():
            raise FileNotFoundError(f"Input TXT not found: {self.input_txt_path}")

        raw = self.input_txt_path.read_text(encoding="utf-8", errors="ignore")
        logical_lines: list[str] = []
        for line in raw.splitlines():
            cleaned = self._normalize_spaces(line)
            if cleaned:
                logical_lines.append(cleaned)
        return logical_lines

    @staticmethod
    def _format_rea_id(index_1_based: int) -> str:
        """Format IDs as REA-01, REA-02, ..."""
        return f"REA-{index_1_based:02d}"

    @staticmethod
    def _chunk_list(values: list[Any], size: int) -> list[list[Any]]:
        """Split a list into fixed-size chunks."""
        return [values[i : i + size] for i in range(0, len(values), size)]

    def _build_rea_entries(self, logical_lines: list[str]) -> list[dict[str, str]]:
        """Convert lines into REA entries with sequential REA IDs."""
        entries: list[dict[str, str]] = []
        for idx, line in enumerate(logical_lines, start=1):
            entries.append({"rea_id": self._format_rea_id(idx), "text": line})
        return entries

    def _write_chunk_files(self, entries: list[dict[str, str]]) -> list[Path]:
        """
        Write chunk files like chunk1.txt, chunk2.txt, ...

        Each line in a chunk file is "REA-xy: <text>".
        """
        self.output_chunk_dir.mkdir(parents=True, exist_ok=True)

        saved_paths: list[Path] = []
        chunks = self._chunk_list(entries, self.entries_per_chunk)
        for chunk_idx, chunk_entries in enumerate(chunks, start=1):
            chunk_path = self.output_chunk_dir / f"chunk{chunk_idx}.txt"
            lines = [f"{item['rea_id']}: {item['text']}" for item in chunk_entries]
            chunk_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
            saved_paths.append(chunk_path)

        return saved_paths

    def split(self) -> ChunkSplitResult:
        """Run full split and write `split_manifest.json` in output directory."""
        logical_lines = self._read_logical_lines()
        entries = self._build_rea_entries(logical_lines)
        chunk_files = self._write_chunk_files(entries)

        manifest = {
            "input_txt": str(self.input_txt_path),
            "output_chunk_dir": str(self.output_chunk_dir),
            "entries_per_chunk": self.entries_per_chunk,
            "rea_count": len(entries),
            "chunk_count": len(chunk_files),
            "chunks": [str(path) for path in chunk_files],
        }

        manifest_path = self.output_chunk_dir / "split_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

        return ChunkSplitResult(
            input_txt=str(self.input_txt_path),
            output_dir=str(self.output_chunk_dir),
            chunk_count=len(chunk_files),
            rea_count=len(entries),
            chunk_files=[str(path) for path in chunk_files],
            manifest_json=str(manifest_path),
        )


# Edit these values directly if you want to run this file without terminal args.
if __name__ == "__main__":
    project_root = Path("/Users/my/Documents/projects/detectionDeviation")

    # Example input can be switched to rea_with_injections/rea_full_text.txt
    input_txt = project_root / "input" / "rea_no_injections" / "rea_full_text.txt"

    # Use a NEW output folder so existing chunked_texts stay untouched.
    output_chunks = project_root / "input" / "rea_no_injections" / "chunked_texts"

    splitter = ReaChunkSplitter(
        input_txt_path=input_txt,
        output_chunk_dir=output_chunks,
        entries_per_chunk=3,
    )
    result = splitter.split()
    print(json.dumps(result.__dict__, indent=2, ensure_ascii=False))
