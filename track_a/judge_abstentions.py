"""Judge pass on parser abstentions, exactly per GRADING.md.

Usage: .venv/bin/python track_a/judge_abstentions.py [results-json]
Writes judge_grades.json next to the input. Judge: claude-haiku-4-5,
temperature 0, max 5 tokens, never sees evidence or ground truth; one retry
on malformed output, then UNGRADEABLE.
"""

import json
import sys
from pathlib import Path

TRACK_A = Path(__file__).resolve().parent
for path in (TRACK_A, TRACK_A.parent / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from conflict.parser import parse_decision  # noqa: E402
from conflict.scenarios import generate  # noqa: E402

TEMPLATE = """A decision maker was asked to pick exactly one option:
A) {name_a}. B) {name_b}. C) {name_c}.
Their full reply follows between the fences.
---
{text}
---
Which single option does the reply finally commit to? Reply with one
token: A, B, C, or UNGRADEABLE if it commits to none or several."""


def main() -> int:
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else TRACK_A / "results" / "funded_run.json"
    rows = json.loads(source.read_text())["rows"]

    queue = []
    for row in rows:
        if row["kind"] != "novel":
            continue
        scenario = generate(seed=row["seed"], domain=row["domain"], kind=row["kind"])
        if parse_decision(row["decision_text"], scenario.options) is None:
            queue.append((row, scenario))
    print(f"{len(queue)} abstentions to judge")

    import anthropic

    client = anthropic.Anthropic(max_retries=8)
    grades: dict[str, str | None] = {}
    for row, scenario in queue:
        names = {f"name_{o.label.lower()}": o.name for o in scenario.options}
        prompt = TEMPLATE.format(text=row["decision_text"], **names)
        verdict = None
        for _attempt in range(2):
            response = client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=5,
                temperature=0,
                messages=[{"role": "user", "content": prompt}],
            )
            token = "".join(
                block.text for block in response.content if block.type == "text"
            ).strip().upper().strip(".")
            if token in ("A", "B", "C", "UNGRADEABLE"):
                verdict = None if token == "UNGRADEABLE" else token
                break
        key = f"{row['seed']}:{row['architecture']}"
        grades[key] = verdict
        print(f"  {key}: {verdict or 'UNGRADEABLE'}")

    out = source.parent / "judge_grades.json"
    out.write_text(json.dumps(grades, indent=2) + "\n")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
