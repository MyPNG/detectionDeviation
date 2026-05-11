from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class MainRequirementsSlotFilter:
    def _load_json(self, path: Path) -> Any:
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _normalize_id(value: Any) -> str:
        return str(value or "").strip()

    def build_main_slots(
        self,
        main_requirements_json: str | Path,
        extended_slots_json: str | Path,
        output_json: str | Path,
    ) -> Path:
        main_path = Path(main_requirements_json)
        slots_path = Path(extended_slots_json)
        output_path = Path(output_json)

        main_payload = self._load_json(main_path)
        if not isinstance(main_payload, list):
            raise ValueError(f"Expected list in {main_path}")

        slot_payload = self._load_json(slots_path)
        if not isinstance(slot_payload, dict):
            raise ValueError(f"Expected object in {slots_path}")

        slot_rows = slot_payload.get("results", [])
        if not isinstance(slot_rows, list):
            raise ValueError(f"Expected 'results' list in {slots_path}")

        main_ids = {
            self._normalize_id(row.get("ID"))
            for row in main_payload
            if isinstance(row, dict) and self._normalize_id(row.get("ID"))
        }

        matched_rows = [
            row
            for row in slot_rows
            if isinstance(row, dict) and self._normalize_id(row.get("id")) in main_ids
        ]

        output_payload = {
            "main_requirements_file": str(main_path),
            "extended_slots_file": str(slots_path),
            "main_requirement_count": len(main_ids),
            "matched_slot_count": len(matched_rows),
            "results": matched_rows,
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(output_payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return output_path


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    reg_input_name = "reg_for_injectiontest"  # change if needed
    reg_root = project_root / "intermediate_results" / reg_input_name

    main_requirements_json = reg_root / f"{reg_input_name}_requirements.json"
    extended_slots_json = reg_root / f"{reg_input_name}_requirements_extended_slots_llama3.json"
    output_json = reg_root / f"{reg_input_name}_requirements_slots_main.json"

    builder = MainRequirementsSlotFilter()
    saved = builder.build_main_slots(
        main_requirements_json=main_requirements_json,
        extended_slots_json=extended_slots_json,
        output_json=output_json,
    )
    print(f"Saved main slots JSON to: {saved}")


if __name__ == "__main__":
    main()
