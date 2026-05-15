from __future__ import annotations

from typing import Any


class DeonticLLMClient:
    """
    LLM prompt/call utilities:
    - prompt building
    - retries/timeouts
    - JSON response parsing
    """

    def __init__(self, legacy: Any) -> None:
        """Store legacy implementation for behavior-preserving delegation."""
        self.legacy = legacy

    def build_user_prompt_for_group(self, group: dict[str, Any]) -> str:
        """Build user prompt text for one grouped requirement set."""
        return self.legacy._build_user_prompt_for_group(group)

    def call_ollama(self, user_prompt: str) -> str:
        """Send a user-only prompt to Ollama-compatible endpoint."""
        return self.legacy._call_ollama(user_prompt)

    def call_ollama_with_system(self, system_prompt: str, user_prompt: str) -> str:
        """Send system+user prompt pair to Ollama-compatible endpoint."""
        return self.legacy._call_ollama_with_system(system_prompt, user_prompt)

    def extract_json_array_from_text(self, text: str) -> list[dict[str, Any]]:
        """Extract JSON-array rows from free-form LLM text output."""
        return self.legacy._extract_json_array_from_text(text)
