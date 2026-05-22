import pathlib

import pytest

ASSETS_DIR = pathlib.Path(__file__).parent / "assets"


@pytest.fixture
def assets_dir() -> pathlib.Path:
    return ASSETS_DIR
