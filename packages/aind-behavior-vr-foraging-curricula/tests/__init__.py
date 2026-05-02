import contextlib
import io
import logging
import sys


@contextlib.contextmanager
def suppress_stdout():
    original_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        yield
    finally:
        sys.stdout = original_stdout


@contextlib.contextmanager
def suppress_all_logging():
    root_logger = logging.getLogger()
    previous_levels = {root_logger: root_logger.level}
    previous_levels.update(
        {
            logger: logger.level
            for logger in logging.Logger.manager.loggerDict.values()
            if isinstance(logger, logging.Logger)
        }
    )

    try:
        logging.disable(logging.CRITICAL + 1)
        yield
    finally:
        logging.disable(logging.NOTSET)
        for logger, level in previous_levels.items():
            logger.setLevel(level)
