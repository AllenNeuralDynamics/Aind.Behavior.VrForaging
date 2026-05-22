import logging
import os
import typing as t
from functools import partial
from pathlib import Path

import contraqctor
import semver

from aind_behavior_vr_foraging import __semver__

logger = logging.getLogger(__name__)


def _dataset_lookup_helper(version: str) -> t.Callable[[Path], contraqctor.contract.Dataset]:
    parsed_version = semver.Version.parse(version)
    # Ignore release candidate suffix for version comparison
    parsed_version = semver.Version(parsed_version.major, parsed_version.minor, parsed_version.patch)
    if semver.Version.parse("0.4.0") <= parsed_version < semver.Version.parse("0.5.0"):
        from .v0_4_0 import dataset as _dataset
    elif semver.Version.parse("0.5.0") <= parsed_version < semver.Version.parse("0.6.0"):
        from .v0_5_0 import dataset as _dataset
    elif semver.Version.parse("0.6.0") <= parsed_version < semver.Version.parse("0.7.0"):
        from .v0_6_0 import dataset as _dataset
    elif parsed_version.major == 1:
        if parsed_version.prerelease is not None:
            logger.warning(
                "Version %s is a pre-release version. This will be considered a best-effort attempt to load the dataset.",
                version,
            )
        from .v1 import dataset as _dataset
    else:
        raise ValueError(f"Unsupported version: {version}")
    return partial(_dataset, version=version)


def _infer_dataset_version(path: os.PathLike) -> t.Optional[str]:
    """Infers the dataset version from the given path.

    Args:
        path (os.PathLike): The path to infer the dataset version from.

    Returns:
        str: The inferred dataset version.
    """
    task_logic = Path(path) / "behavior/Logs/tasklogic_output.json"
    version: t.Optional[str] = None
    if task_logic.exists():
        import json

        with open(task_logic, "r", encoding="utf-8") as f:
            data = json.load(f)
            version = data.get("version", None)
    return version


def dataset(path: os.PathLike, version: t.Optional[str] = None) -> contraqctor.contract.Dataset:
    """
    Loads the dataset for the Aind VR Foraging project from a specified version.

    Args:
        path (os.PathLike): The path to the dataset root directory.
        version (str, optional): The version of the dataset to load. If not provided, it will be inferred from the dataset or default to the package version.

    Returns:
        contraqctor.contract.Dataset: The loaded dataset.
    """
    if version is None:
        version = _infer_dataset_version(path)
        if version is None:
            logger.warning(
                "Could not infer dataset version from path: %s. Defaulting to package version: %s",
                path,
                __semver__,
            )
    dataset_constructor = _dataset_lookup_helper(version if version is not None else __semver__)
    return dataset_constructor(Path(path))


def render_dataset(version: str = __semver__) -> str:
    """Renders the dataset as a tree-like structure for visualization."""
    from contraqctor.contract.utils import print_data_stream_tree_html

    dataset_constructor = _dataset_lookup_helper(version)
    return print_data_stream_tree_html(
        dataset_constructor(Path("<RootPath>")), show_missing_indicator=False, show_type=True
    )
