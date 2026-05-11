from __future__ import annotations

import json
import re
from pathlib import Path


class RecursivePolicyChunker:
    """
    Deterministic text chunker using recursive character splitting.

    It prioritizes natural boundaries:
    1) paragraph breaks ("\n\n")
    2) line breaks ("\n")
    3) spaces (" ")
    and falls back to hard character slicing only when needed.
    """

    def __init__(
        self,
        chunk_size: int = 1400,
        chunk_overlap: int = 0,
        separators: list[str] | None = None,
    ) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be > 0")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap must be >= 0")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", " "]

    @staticmethod
    def _load_text(input_file: Path) -> str:
        return input_file.read_text(encoding="utf-8")

    @staticmethod
    def _normalize_whitespace(text: str) -> str:
        # Keep line structure, trim trailing spaces.
        lines = [line.rstrip() for line in text.splitlines()]
        return "\n".join(lines).strip()

    @staticmethod
    def _looks_like_heading(line: str) -> bool:
        """
        Heuristic heading detector to keep heading context with the first rule.
        """
        text = line.strip()
        if not text:
            return False

        if text.endswith(":") and len(text.split()) <= 14:
            return True

        # Short line with no sentence punctuation is usually a heading.
        if all(p not in text for p in (".", "?", "!")) and len(text.split()) <= 8:
            return True

        return False

    @staticmethod
    def _looks_like_bullet(line: str) -> bool:
        """
        Detect legal list items: '-', '•', '(a)', '(1)', 'a)', '1.' ...
        """
        text = line.strip()
        if not text:
            return False

        bullet_patterns = [
            r"^[-*•]\s+",
            r"^\([a-zA-Z]\)\s+",
            r"^\(\d+\)\s+",
            r"^[a-zA-Z]\)\s+",
            r"^\d+\.\s+",
        ]
        return any(re.match(pattern, text) for pattern in bullet_patterns)

    @staticmethod
    def _starts_with_connector(line: str) -> bool:
        text = line.strip().lower()
        connectors = (
            "however",
            "unless",
            "therefore",
            "thus",
            "moreover",
            "furthermore",
            "and ",
            "or ",
            "but ",
            "insofar as",
            "provided that",
            "whereas",
            "if ",
        )
        return text.startswith(connectors)

    def _should_attach_to_previous(self, previous: str, current: str) -> bool:
        current_stripped = current.strip()
        if not current_stripped:
            return False

        # Lowercase starts are usually continuation fragments.
        if current_stripped[0].islower():
            return True

        if self._starts_with_connector(current_stripped):
            return True

        prev_trim = previous.rstrip()
        if prev_trim.endswith((",", ";", ":", "(")):
            return True

        # If previous does not end with sentence punctuation, keep flowing.
        if not re.search(r"[.!?]$", prev_trim):
            return True

        return False

    def _repair_structure_before_chunking(self, text: str) -> str:
        """
        Pre-chunk repair to reduce orphan sentences:
        - carry heading context into first following rule line
        - attach bullet lines to their governing previous line
        - merge connector/lowercase continuation lines to previous line
        """
        lines = [line.strip() for line in text.splitlines()]
        blocks: list[str] = []
        pending_heading = ""

        for line in lines:
            if not line:
                continue

            if self._looks_like_heading(line):
                pending_heading = f"{pending_heading} {line}".strip() if pending_heading else line
                continue

            current = line
            if pending_heading:
                current = f"{pending_heading}: {current}"
                pending_heading = ""

            if self._looks_like_bullet(current):
                if blocks:
                    blocks[-1] = f"{blocks[-1].rstrip()} {current}"
                else:
                    blocks.append(current)
                continue

            if blocks and self._should_attach_to_previous(blocks[-1], current):
                blocks[-1] = f"{blocks[-1].rstrip()} {current}"
            else:
                blocks.append(current)

        # Keep trailing heading if file ends with one.
        if pending_heading:
            blocks.append(pending_heading)

        return "\n\n".join(block.strip() for block in blocks if block.strip())

    def _split_hard(self, text: str) -> list[str]:
        """
        Last-resort splitter when no separator-based split can keep chunk bounds.
        """
        text = text.strip()
        if not text:
            return []

        chunks: list[str] = []
        start = 0
        step = self.chunk_size - self.chunk_overlap
        while start < len(text):
            end = min(len(text), start + self.chunk_size)
            piece = text[start:end].strip()
            if piece:
                chunks.append(piece)
            if end >= len(text):
                break
            start += step
        return chunks

    def _merge_with_limit(self, pieces: list[str], separator: str) -> list[str]:
        """
        Greedily merge split pieces up to chunk_size to reduce tiny fragments.
        """
        merged: list[str] = []
        current = ""
        for piece in pieces:
            part = piece.strip()
            if not part:
                continue
            candidate = f"{current}{separator}{part}" if current else part
            if len(candidate) <= self.chunk_size:
                current = candidate
            else:
                if current:
                    merged.append(current.strip())
                current = part
        if current:
            merged.append(current.strip())
        return merged

    def _recursive_split(self, text: str, separators: list[str]) -> list[str]:
        text = text.strip()
        if not text:
            return []
        if len(text) <= self.chunk_size:
            return [text]
        if not separators:
            return self._split_hard(text)

        sep = separators[0]
        parts = text.split(sep)

        # If separator is not present or useless, move to next separator.
        if len(parts) == 1:
            return self._recursive_split(text, separators[1:])

        candidate_chunks = self._merge_with_limit(parts, sep)
        out: list[str] = []
        for chunk in candidate_chunks:
            if len(chunk) <= self.chunk_size:
                out.append(chunk)
            else:
                out.extend(self._recursive_split(chunk, separators[1:]))
        return out

    def _apply_overlap(self, chunks: list[str]) -> list[str]:
        """
        Add overlap by prefixing each chunk (except first) with tail text
        from the previous chunk.
        """
        if not chunks or self.chunk_overlap == 0:
            return chunks

        out: list[str] = [chunks[0]]
        for idx in range(1, len(chunks)):
            prev_tail = chunks[idx - 1][-self.chunk_overlap :].strip()
            cur = chunks[idx].strip()
            if prev_tail and not cur.startswith(prev_tail):
                out.append(f"{prev_tail}\n{cur}")
            else:
                out.append(cur)
        return out

    @staticmethod
    def _merge_chunks_starting_lowercase(chunks: list[str]) -> list[str]:
        """
        Enforce rule: a chunk must not start with a lowercase letter.
        If it does, merge it into the previous chunk.
        """
        if not chunks:
            return chunks

        merged: list[str] = [chunks[0]]
        for chunk in chunks[1:]:
            current = chunk.strip()
            if not current:
                continue

            if current[0].islower() and merged:
                merged[-1] = f"{merged[-1].rstrip()} {current}"
            else:
                merged.append(current)
        return merged

    def chunk_text(self, text: str) -> list[str]:
        cleaned = self._normalize_whitespace(text)
        repaired = self._repair_structure_before_chunking(cleaned)
        chunks = self._recursive_split(repaired, self.separators)
        chunks = self._apply_overlap(chunks)
        chunks = self._merge_chunks_starting_lowercase(chunks)

        # Final cleanup + deterministic ordering.
        normalized: list[str] = []
        for chunk in chunks:
            c = re.sub(r"\n{3,}", "\n\n", chunk).strip()
            if c:
                normalized.append(c)
        return normalized

    @staticmethod
    def _write_chunk_text_files(output_dir: Path, chunks: list[str]) -> list[Path]:
        output_dir.mkdir(parents=True, exist_ok=True)

        # Remove stale chunk files first.
        for existing in output_dir.glob("chunk*.txt"):
            if re.fullmatch(r"chunk\d+\.txt", existing.name, flags=re.IGNORECASE):
                existing.unlink(missing_ok=True)

        written: list[Path] = []
        for index, chunk_text in enumerate(chunks, start=1):
            path = output_dir / f"chunk{index}.txt"
            path.write_text(chunk_text.strip() + "\n", encoding="utf-8")
            written.append(path)
        return written

    def chunk_policy(self, input_file: Path, output_file: Path) -> Path:
        text = self._load_text(input_file)
        chunks = self.chunk_text(text)
        payload = {"chunks": chunks}

        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        self._write_chunk_text_files(output_file.parent, chunks)
        return output_file


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]

    input_file = project_root / "input" / "rea_no_injections" / "rea_full_text.txt.txt"
    output_file = project_root / "input" / "rea_no_injections" / "chunked_texts"/ "chunked_policy_recursive.json"

    # Recommended default for legal policy chunks:
    # chunk_size=1400 chars, overlap=0 chars.
    chunker = RecursivePolicyChunker(
        chunk_size=500,
        chunk_overlap=0,
    )
    saved = chunker.chunk_policy(input_file=input_file, output_file=output_file)
    print(f"Saved chunked output: {saved}")


if __name__ == "__main__":
    main()
