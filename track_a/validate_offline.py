"""Run the offline validation battery and write the report artifacts.

Usage (from the repo root):

    .venv/bin/python track_a/validate_offline.py [n_per_cell]

Zero API calls: every module is a scripted oracle. Writes
track_a/validation_results.json and track_a/VALIDATION.md, and exits nonzero
if any architecture signature check fails.
"""

import json
import sys
from pathlib import Path

TRACK_A = Path(__file__).resolve().parent
for path in (TRACK_A, TRACK_A.parent / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from conflict.validation import render_markdown, run_validation  # noqa: E402


def main() -> int:
    n_per_cell = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    report = run_validation(n_per_cell=n_per_cell)

    (TRACK_A / "validation_results.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    (TRACK_A / "VALIDATION.md").write_text(render_markdown(report))

    failures = [name for name, ok in report["checks"].items() if not ok]
    for name, ok in report["checks"].items():
        print(f"{'PASS' if ok else 'FAIL'} {name}")
    print(f"{report['n_trials']} trials, {len(failures)} failing checks")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
