import random
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
RANDOM_SEED = 42


def main() -> int:
    cmd = ["uv", "run", "vr-foraging", "regenerate"]
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        return result.returncode

    print(f"Running curricula schema generation (seed={RANDOM_SEED})")
    random.seed(RANDOM_SEED)
    from aind_behavior_vr_foraging_curricula._schema import main as curricula_main  # noqa: PLC0415

    curricula_main()
    return 0


if __name__ == "__main__":
    sys.exit(main())
