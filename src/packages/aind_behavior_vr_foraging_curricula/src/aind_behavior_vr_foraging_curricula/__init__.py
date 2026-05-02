import logging
import re
import sys
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


log_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# Configure package logger
# Here, we will log all debug and above
curricula_logger = logging.getLogger(__name__)
curricula_logger.setLevel(logging.DEBUG)

stderr_handler = logging.StreamHandler(sys.stderr)
stderr_handler.setLevel(logging.DEBUG)
stderr_handler.setFormatter(log_formatter)

curricula_logger.addHandler(stderr_handler)
curricula_logger.propagate = False

# Configure the root logger to send logs from other packages to stderr
# Here, we will log all warnings and above
root_logger = logging.getLogger()
for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)

root_stderr_handler = logging.StreamHandler(sys.stderr)
root_stderr_handler.setLevel(logging.WARNING)
root_stderr_handler.setFormatter(log_formatter)

root_logger.addHandler(root_stderr_handler)
root_logger.setLevel(logging.WARNING)
