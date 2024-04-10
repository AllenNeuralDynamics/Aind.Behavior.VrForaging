""" testing examples """

import glob
import unittest
from pathlib import Path
import sys

EXAMPLES_DIR = Path(__file__).parents[1] / "examples"
sys.path.append(str(EXAMPLES_DIR.parent / "scripts"))

from examples import main

class ExampleTests(unittest.TestCase):
    """tests for examples"""

    def test_examples(self):
        main()

if __name__ == "__main__":
    unittest.main()