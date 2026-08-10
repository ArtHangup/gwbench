"""Make the track_a package importable when pytest runs from anywhere.

gwbench itself is an editable install in the repo venv, so `import gwbench`
already works; only `conflict` needs the path help.
"""

import sys
from pathlib import Path

TRACK_A = Path(__file__).resolve().parent.parent
if str(TRACK_A) not in sys.path:
    sys.path.insert(0, str(TRACK_A))
