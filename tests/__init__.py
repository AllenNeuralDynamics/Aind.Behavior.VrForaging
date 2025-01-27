import glob
import importlib.util
import logging
from pathlib import Path
from types import ModuleType

EXAMPLES_DIR = Path(__file__).parents[1] / "examples"
JSON_ROOT = Path("./local").resolve()

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())
logging.disable(logging.CRITICAL)


def build_example(script_path: str) -> ModuleType:
    module_name = Path(script_path).stem
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    if spec is None:
        raise ImportError(f"Can't find {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_examples(examples_dir: Path = EXAMPLES_DIR):
    for script_path in glob.glob(str(examples_dir / "*.py")):
        _ = build_example(script_path)
