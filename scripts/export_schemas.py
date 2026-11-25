"""Write the JSON Schemas for the three shared records to contracts/. CI fails if they drift."""

from __future__ import annotations

import json
from pathlib import Path

from counsel.contracts import RECORDS

OUT = Path(__file__).resolve().parent.parent / "contracts"


def render() -> dict[str, str]:
    return {
        f"{name}.schema.json": json.dumps(model.model_json_schema(), indent=2, ensure_ascii=False)
        + "\n"
        for name, model in RECORDS.items()
    }


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for filename, text in render().items():
        (OUT / filename).write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote contracts/{filename}")
