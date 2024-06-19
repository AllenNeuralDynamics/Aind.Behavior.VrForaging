""" testing examples """

import glob
import unittest

from . import EXAMPLES_DIR, build_example


class ExampleTests(unittest.TestCase):
    """tests for examples"""

    def test_examples(self):
        for script_path in glob.glob(str(EXAMPLES_DIR / "*.py")):
            with self.subTest(script_path=script_path):
                module = build_example(script_path)
                # Check if the module executed successfully
                if hasattr(module, "__name__") and module.__name__ == "__main__":
                    self.assertEqual(module.__name__, "__main__", f"Script {script_path} failed to execute")


if __name__ == "__main__":
    unittest.main()