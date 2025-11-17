import re
from importlib.metadata import PackageNotFoundError, version


def pep440_to_semver(ver: str) -> str:
    """
    Convert a PEP 440 version to a SemVer-compatible string.

    Examples:
        1.2.3rc2   -> 1.2.3-rc2
        1.2.3a1    -> 1.2.3-a1
        1.2.3b1    -> 1.2.3-b1
        1.2.3.dev4 -> 1.2.3-dev4
        1.2.3.post1 -> 1.2.3+post1
    """
    # pre-release: a, b, rc -> -aN, -bN, -rcN
    ver = re.sub(r"(?<=\d)(a|b|rc)(\d+)", r"-\1\2", ver)
    # dev release: .devN -> -devN
    ver = re.sub(r"\.dev(\d+)", r"-dev\1", ver)
    # post release: .postN -> +postN
    ver = re.sub(r"\.post(\d+)", r"+post\1", ver)
    return ver


try:
    __version__ = version(__name__)
except PackageNotFoundError:
    __version__ = "0.0.0"

__semver__ = pep440_to_semver(__version__)
