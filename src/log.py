import logging
import sys


def setup_logging() -> logging.Logger:
    logger = logging.getLogger("booking-alert")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)

        fmt = logging.Formatter(
            "[%(asctime)s] %(levelname)s \u2014 %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(fmt)
        logger.addHandler(handler)

    return logger
