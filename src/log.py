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


def add_betterstack_handler(source_token: str, ingesting_host: str) -> bool:
    """Attach the Better Stack Logtail handler to the logger.
    Returns True if added, False if skipped (no token)."""
    if not source_token:
        return False

    try:
        from logtail import LogtailHandler
    except ImportError:
        logging.getLogger("booking-alert").warning(
            "logtail-python not installed \u2014 run: pip install logtail-python"
        )
        return False

    logger = logging.getLogger("booking-alert")
    handler = LogtailHandler(
        source_token=source_token,
        host=f"https://{ingesting_host}",
    )
    handler.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.info("Better Stack logging enabled")
    return True
