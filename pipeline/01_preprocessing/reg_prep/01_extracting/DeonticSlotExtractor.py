from __future__ import annotations

from pathlib import Path
from typing import Any

from .DeonticSlotExtractorLegacy import DeonticSlotExtractorLegacy
from .deontic.io import DeonticIO
from .deontic.llm_client import DeonticLLMClient
from .deontic.modal_detection import DeonticModalDetection
from .deontic.splitting import DeonticSplitting
from .deontic.stage1_3 import DeonticStage13
from .deontic.stage4_slots import DeonticStage4Slots
from .deontic.text_normalization import DeonticTextNormalization


class DeonticSlotExtractor:
    """
    Thin facade for deontic extraction orchestration.

    Core logic is delegated into:
    - deontic/io.py
    - deontic/text_normalization.py
    - deontic/modal_detection.py
    - deontic/splitting.py
    - deontic/stage1_3.py
    - deontic/stage4_slots.py
    - deontic/llm_client.py

    Backward compatibility:
    unknown attributes/methods are forwarded to the legacy implementation.
    """

    SYSTEM_PROMPT = DeonticSlotExtractorLegacy.SYSTEM_PROMPT
    PASSIVE_TO_ACTIVE_SYSTEM_PROMPT_TEMPLATE = DeonticSlotExtractorLegacy.PASSIVE_TO_ACTIVE_SYSTEM_PROMPT_TEMPLATE
    ANAPHORA_MISSING_ACTOR_SYSTEM_PROMPT = DeonticSlotExtractorLegacy.ANAPHORA_MISSING_ACTOR_SYSTEM_PROMPT
    REQUIRED_FIELDS = DeonticSlotExtractorLegacy.REQUIRED_FIELDS
    INVENTED_WORD_CHECK_FIELDS = DeonticSlotExtractorLegacy.INVENTED_WORD_CHECK_FIELDS

    def __init__(
        self,
        endpoint_url: str = "http://localhost:11434/api/chat",
        model_name: str = "llama3",
        timeout_seconds: int = 180,
        max_retries: int = 3,
        temperature: float = 0.1,
    ) -> None:
        self._legacy = DeonticSlotExtractorLegacy(
            endpoint_url=endpoint_url,
            model_name=model_name,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            temperature=temperature,
        )

        self.io = DeonticIO(self._legacy)
        self.text_normalization = DeonticTextNormalization(self._legacy)
        self.modal_detection = DeonticModalDetection(self._legacy)
        self.splitting = DeonticSplitting(self._legacy)
        self.stage1_3 = DeonticStage13(self._legacy)
        self.stage4_slots = DeonticStage4Slots(self._legacy)
        self.llm_client = DeonticLLMClient(self._legacy)

    def __getattr__(self, name: str) -> Any:
        """
        Backward-compatible passthrough for existing helper-method calls.
        """
        return getattr(self._legacy, name)

    # Orchestration methods
    def resolve_anaphora_and_missing_actor(self, nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return self.stage1_3.resolve_anaphora_and_missing_actor(nodes)

    def make_passive_to_active(self, nodes: list[dict[str, Any]]) -> list[dict[str, str]]:
        return self.stage1_3.make_passive_to_active(nodes)

    def make_passive_to_active_two_calls(self, nodes: list[dict[str, Any]]) -> list[dict[str, str]]:
        return self.stage1_3.make_passive_to_active_two_calls(nodes)

    def run_passive_active_pipeline_on_file(self, input_json: str | Path, output_json: str | Path) -> Path:
        return self.stage1_3.run_passive_active_pipeline_on_file(input_json=input_json, output_json=output_json)

    def extract_slots_for_group(self, group: dict[str, Any]) -> list[dict[str, Any]]:
        return self.stage4_slots.extract_slots_for_group(group)

    def run(self, input_json: str | Path, output_json: str | Path) -> Path:
        return self.stage4_slots.run(input_json=input_json, output_json=output_json)

    def test_passive_to_active(self, output_json: str | Path | None = None) -> dict[str, Any]:
        return self.stage1_3.test_passive_to_active(output_json=output_json)


def main() -> None:
    from .DeonticSlotExtractorLegacy import main as legacy_main

    legacy_main()


if __name__ == "__main__":
    main()
