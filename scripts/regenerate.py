"""Cross-platform script to regenerate all schemas in this repository.

This script runs the following steps in order:
  1. ``uv run vr-foraging regenerate`` — regenerates the JSON/C# schemas for
     the core VR Foraging task logic and rig models.
  2. Runs ``_schema.py`` from the curricula package — serialises every known
     curriculum to a JSON file under the curricula ``schema/`` directory.

Usage (from the repository root)::

    python scripts/regenerate.py
    # or, using uv:
    uv run scripts/regenerate.py
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent


def main() -> int:
    commands = [
        ["uv", "run", "vr-foraging", "regenerate"],
        [
            "uv",
            "run",
            str(
                ROOT
                / "src"
                / "packages"
                / "aind_behavior_vr_foraging_curricula"
                / "src"
                / "aind_behavior_vr_foraging_curricula"
                / "_schema.py"
            ),
        ],
    ]
    for cmd in commands:
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=ROOT)
        if result.returncode != 0:
            return result.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
