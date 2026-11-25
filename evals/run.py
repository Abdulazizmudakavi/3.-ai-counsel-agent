"""Evaluation gate run by CI on every change (owner: Sana for sets and scoring, Abdul for CI).

Zero-tolerance metrics block the merge: missed critical escalations, invented citations,
successful injections, permission violations. Until the test sets exist this only reports.
"""

from __future__ import annotations

import sys
from pathlib import Path

SETS = Path(__file__).resolve().parent / "sets"


def main() -> int:
    found = sorted(p.name for p in SETS.glob("*.jsonl")) if SETS.exists() else []
    if not found:
        print("eval gate: no test sets yet (expected from week 2) - nothing to score")
        return 0
    print(f"eval gate: found {found}; scoring not implemented yet")
    return 0


if __name__ == "__main__":
    sys.exit(main())
