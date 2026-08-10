"""Make the track_a package and gwbench importable from any cwd.

The gwbench editable install resolves through the root pyproject's pytest
pythonpath, which plain `python` invocations never see, so ../src goes on the
path here too (read-only import, per the session rules).
"""

import sys
from pathlib import Path

TRACK_A = Path(__file__).resolve().parent.parent
for path in (TRACK_A, TRACK_A.parent / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
