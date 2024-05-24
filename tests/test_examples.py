""" testing examples """

import glob
import unittest
from pathlib import Path

EXAMPLES_DIR = Path(__file__).parents[1] / "examples"


class ExampleTests(unittest.TestCase):
    """tests for examples"""

    def test_examples(self):
        import importlib.util

        for script_path in glob.glob(str(EXAMPLES_DIR / "*.py")):
            with self.subTest(script_path=script_path):
                module_name = Path(script_path).stem
                spec = importlib.util.spec_from_file_location(module_name, script_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Check if the module executed successfully
                if hasattr(module, "__name__") and module.__name__ == "__main__":
                    self.assertEqual(module.__name__, "__main__", f"Script {script_path} failed to execute")


if __name__ == "__main__":
    unittest.main()
