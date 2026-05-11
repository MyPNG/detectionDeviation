from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


class Llama3PolicyChunker:
    """
    Chunk policy text with a local Llama 3 endpoint (Ollama-compatible API).
    """

    SYSTEM_PROMPT = """
You are an expert data architect building a Vector Database for a GDPR compliance audit.
Your task is to read the provided Privacy Policy and break it into distinct, logical chunks.

Rules for chunking:
1. Break the text down by individual rules, rights, or data processing activities.
2. CONTEXT INJECTION: Do not output "orphan sentences." Ensure every chunk includes the context of what section it belongs to (e.g., start a chunk with "Regarding the right to erasure...").
3. LOSSLESS REQUIREMENT (CRITICAL): Do NOT summarize, paraphrase, rewrite, or omit content. Preserve original wording for all policy statements.
4. COVERAGE REQUIREMENT (CRITICAL): Every substantive sentence from the input must appear in exactly one chunk. No dropped sentences and no duplicates.
5. BULLET REQUIREMENT (CRITICAL): Keep each bullet/right statement complete. If a bullet contains a qualifier (e.g., "However..."), keep that qualifier in the same chunk.
6. LIST ATTACHMENT RULE (CRITICAL): If there is a list of bullet points, treat that list as belonging to the immediately preceding governing sentence/section. Keep list items grouped with that parent context so no bullet becomes orphaned.
7. Output strictly as a JSON object containing a list of strings and nothing else.

Format:
{
  "chunks": [
    "chunk 1...",
    "chunk 2..."
  ]
}
""".strip()

    def __init__(
        self,
        endpoint_url: str = "http://localhost:11434/api/chat",
        model_name: str = "llama3",
        timeout_seconds: int = 300,
        max_retries: int = 3,
    ) -> None:
        self.endpoint_url = endpoint_url
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    @staticmethod
    def _load_text(input_file: Path) -> str:
        return input_file.read_text(encoding="utf-8").strip()

    @staticmethod
    def _escape_control_chars_in_json_strings(raw: str) -> str:
        """
        Escape raw control characters that appear inside JSON string literals.
        This helps recover model outputs that are "almost JSON" but contain
        unescaped newlines/tabs within quoted values.
        """
        out: list[str] = []
        in_string = False
        escaped = False

        for ch in raw:
            if in_string:
                if escaped:
                    out.append(ch)
                    escaped = False
                    continue

                if ch == "\\":
                    out.append(ch)
                    escaped = True
                    continue

                if ch == '"':
                    out.append(ch)
                    in_string = False
                    continue

                # JSON control chars must be escaped when inside strings.
                code = ord(ch)
                if code < 0x20:
                    if ch == "\n":
                        out.append("\\n")
                    elif ch == "\r":
                        out.append("\\r")
                    elif ch == "\t":
                        out.append("\\t")
                    elif ch == "\b":
                        out.append("\\b")
                    elif ch == "\f":
                        out.append("\\f")
                    else:
                        out.append(f"\\u{code:04x}")
                    continue

                out.append(ch)
                continue

            out.append(ch)
            if ch == '"':
                in_string = True

        return "".join(out)

    @classmethod
    def _parse_json_candidate(cls, candidate: str) -> dict[str, Any] | None:
        """
        Parse a candidate JSON object with strict + tolerant fallbacks.
        """
        for payload_text in (
            candidate.strip(),
            cls._escape_control_chars_in_json_strings(candidate.strip()),
        ):
            try:
                payload = json.loads(payload_text)
                if isinstance(payload, dict):
                    return payload
            except json.JSONDecodeError:
                pass

            try:
                payload = json.loads(payload_text, strict=False)
                if isinstance(payload, dict):
                    return payload
            except json.JSONDecodeError:
                pass

        return None

    @staticmethod
    def _extract_json_from_text(text: str) -> dict[str, Any]:
        """
        Try robustly to recover JSON from model text output.
        """
        cleaned = text.strip()

        # 1) Direct parse.
        payload = Llama3PolicyChunker._parse_json_candidate(cleaned)
        if payload is not None:
            return payload

        # 2) Parse from fenced code block.
        fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, flags=re.DOTALL | re.IGNORECASE)
        if fence_match:
            candidate = fence_match.group(1)
            payload = Llama3PolicyChunker._parse_json_candidate(candidate)
            if payload is not None:
                return payload

        # 3) Parse first JSON object span.
        span_match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if span_match:
            candidate = span_match.group(0)
            payload = Llama3PolicyChunker._parse_json_candidate(candidate)
            if payload is not None:
                return payload

        raise ValueError("Could not parse JSON object from Llama output.")

    @staticmethod
    def _normalize_chunk_payload(payload: dict[str, Any]) -> dict[str, list[str]]:
        chunks = payload.get("chunks", [])
        if not isinstance(chunks, list):
            raise ValueError("Llama response JSON must contain a list field named 'chunks'.")

        out: list[str] = []
        for item in chunks:
            text = str(item).strip()
            if text:
                out.append(text)
        return {"chunks": out}

    @staticmethod
    def _write_chunk_text_files(output_dir: Path, chunks: list[str]) -> list[Path]:
        """
        Write one chunk per file: chunk1.txt, chunk2.txt, ...
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        # Remove previously generated chunk text files to avoid stale leftovers.
        for existing in output_dir.glob("chunk*.txt"):
            match = re.fullmatch(r"chunk\d+\.txt", existing.name, flags=re.IGNORECASE)
            if match:
                existing.unlink(missing_ok=True)

        written: list[Path] = []
        id_width = max(2, len(str(len(chunks))))
        for index, chunk_text in enumerate(chunks, start=1):
            path = output_dir / f"chunk{index}.txt"
            rea_id = f"REA-{index:0{id_width}d}"
            text = chunk_text.strip()
            path.write_text(f"{rea_id}: {text}\n", encoding="utf-8")
            written.append(path)
        return written

    @staticmethod
    def _normalize_text_for_match(value: str) -> str:
        value = value.lower()
        value = re.sub(r"\s+", " ", value)
        value = re.sub(r"[^\w\s]", "", value)
        return value.strip()

    @staticmethod
    def _looks_like_heading(line: str) -> bool:
        stripped = line.strip()
        if not stripped:
            return True
        if stripped.lower() == "privacy policy":
            return True
        # Likely heading: no sentence punctuation and short.
        if all(p not in stripped for p in (".", "?", "!", ":")) and len(stripped.split()) <= 8:
            return True
        return False

    def _extract_source_sentences(self, policy_text: str) -> list[str]:
        """
        Extract source sentences from the policy text for coverage validation.
        """
        lines = [line.strip() for line in policy_text.splitlines() if line.strip()]
        sentences: list[str] = []

        # Sentence splitting keeps legal statements mostly intact.
        sentence_split_re = re.compile(r"(?<=[.!?])\s+(?=[A-Z“\"(])")

        for line in lines:
            if line.startswith("•"):
                item = line[1:].strip()
                if item:
                    sentences.append(item)
                continue

            if self._looks_like_heading(line):
                continue

            parts = [part.strip() for part in sentence_split_re.split(line) if part.strip()]
            if not parts:
                continue
            sentences.extend(parts)

        # Keep order, dedupe exact repeats.
        out: list[str] = []
        seen: set[str] = set()
        for sentence in sentences:
            key = sentence.strip()
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(key)
        return out

    def _validate_coverage(self, source_sentences: list[str], chunks: list[str]) -> list[str]:
        """
        Return missing source sentences not found in the combined chunk text.
        """
        normalized_chunks = [self._normalize_text_for_match(chunk) for chunk in chunks]
        missing: list[str] = []
        for sentence in source_sentences:
            normalized_sentence = self._normalize_text_for_match(sentence)
            if len(normalized_sentence) < 8:
                continue
            found = any(normalized_sentence in normalized_chunk for normalized_chunk in normalized_chunks)
            if not found:
                missing.append(sentence)
        return missing

    @staticmethod
    def _is_orphan_chunk(chunk_text: str) -> bool:
        text = chunk_text.strip()
        if not text:
            return True

        if len(text.split()) <= 7:
            return True

        if re.match(r"^(These|This|They|It|Such|However|Furthermore|Moreover)\b", text, flags=re.IGNORECASE):
            return True

        if re.match(r"^The right to\b", text, flags=re.IGNORECASE):
            return True

        return False

    def _repair_orphan_chunks(self, chunks: list[str]) -> list[str]:
        """
        Merge orphan chunks into previous chunk to improve self-contained context.
        """
        repaired: list[str] = []
        for chunk in chunks:
            current = chunk.strip()
            if not current:
                continue
            if repaired and self._is_orphan_chunk(current):
                repaired[-1] = f"{repaired[-1].rstrip()} {current}"
            else:
                repaired.append(current)
        return repaired

    def _call_local_llama(self, policy_text: str, validation_feedback: str | None = None) -> str:
        user_content = policy_text.strip()
        if validation_feedback:
            user_content += "\n\n" + validation_feedback.strip()

        request_payload = {
            "model": self.model_name,
            "stream": False,
            "messages": [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            "options": {
                "temperature": 0.1,
            },
        }

        request = urllib.request.Request(
            url=self.endpoint_url,
            data=json.dumps(request_payload).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
                payload = json.loads(raw)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Llama endpoint HTTP {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Llama endpoint connection error: {exc.reason}") from exc

        # Ollama chat format: {"message":{"role":"assistant","content":"..."}}
        message = payload.get("message", {}) if isinstance(payload, dict) else {}
        content = message.get("content", "") if isinstance(message, dict) else ""
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("Llama endpoint returned empty assistant content.")
        return content

    def chunk_policy(self, input_file: Path, output_file: Path) -> Path:
        policy_text = self._load_text(input_file)
        source_sentences = self._extract_source_sentences(policy_text)
        feedback: str | None = None
        final_payload: dict[str, list[str]] | None = None
        final_missing: list[str] = []

        for attempt in range(1, self.max_retries + 1):
            print(f"Sending text to local Llama 3 for intelligent chunking... (attempt {attempt}/{self.max_retries})")
            model_output_text = self._call_local_llama(policy_text, validation_feedback=feedback)
            parsed = self._extract_json_from_text(model_output_text)
            normalized = self._normalize_chunk_payload(parsed)
            repaired_chunks = self._repair_orphan_chunks(normalized["chunks"])
            missing = self._validate_coverage(source_sentences, repaired_chunks)

            final_payload = {"chunks": repaired_chunks}
            final_missing = missing
            if not missing:
                break

            missing_lines = "\n".join(f"- {line}" for line in missing[:50])
            feedback = (
                "VALIDATION FAILED. Your previous output omitted required input sentences.\n"
                "Regenerate the full JSON from scratch.\n"
                "Keep all prior constraints and include ALL missing lines exactly as written.\n"
                "Missing lines:\n"
                f"{missing_lines}\n"
                "Return only strict JSON in the required format."
            )

        if final_payload is None:
            raise RuntimeError("Chunking failed: no payload generated.")
        if final_missing:
            missing_preview = "\n".join(final_missing[:20])
            raise RuntimeError(
                "Chunking failed coverage validation after retries. Missing lines remain:\n"
                f"{missing_preview}"
            )

        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(json.dumps(final_payload, indent=2, ensure_ascii=False), encoding="utf-8")
        self._write_chunk_text_files(output_file.parent, final_payload["chunks"])
        return output_file


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    input_file = project_root / "input" / "rea_no_injections" / "rea_full_text.txt.txt"
    output_file = (
        project_root
        / "input"
        / "rea_no_injections"
        / "chunked_policy.json"
    )

    chunker = Llama3PolicyChunker(
        endpoint_url="http://localhost:11434/api/chat",
        model_name="llama3",
        timeout_seconds=300,
    )
    saved = chunker.chunk_policy(input_file=input_file, output_file=output_file)
    print(f"Saved chunked output: {saved}")


if __name__ == "__main__":
    main()
