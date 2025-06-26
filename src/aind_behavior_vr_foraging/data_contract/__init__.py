import os
import typing as t
from functools import partial
from pathlib import Path

import contraqctor
import semver

from aind_behavior_vr_foraging import __version__


def _dataset_lookup_helper(version: str) -> t.Callable[[Path], contraqctor.contract.Dataset]:
    parsed_version = semver.Version.parse(version)
    if semver.Version.parse("0.5.0") <= parsed_version < semver.Version.parse("6.0.0"):
        from .v0_5_0 import dataset as _dataset
    elif parsed_version >= semver.Version.parse("0.6.0"):
        from .v0_6_0 import dataset as _dataset
    else:
        raise ValueError(f"Unsupported version: {version}")
    return partial(_dataset, version=version)


def dataset(path: os.PathLike, version: str = __version__) -> contraqctor.contract.Dataset:
    """
    Loads the dataset for the Aind VR Foraging project from a specified version.

    Args:
        path (os.PathLike): The path to the dataset root directory.
        version (str): The version of the dataset to load. By default, it uses the package version.

    Returns:
        contraqctor.contract.Dataset: The loaded dataset.
    """
    dataset_constructor = _dataset_lookup_helper(version)
    return dataset_constructor(Path(path))


def render_dataset(version: str = __version__) -> str:
    """Renders the dataset as a tree-like structure for visualization."""
    from contraqctor.contract.utils import print_data_stream_tree

    dataset_constructor = _dataset_lookup_helper(version)
    return print_data_stream_tree(dataset_constructor(Path("<RootPath>")), show_missing_indicator=False, show_type=True)
