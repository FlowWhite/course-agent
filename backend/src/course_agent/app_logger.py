import logging

from .paths import LOG_DIR

LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_PATH = LOG_DIR / "agent.log"


def create_logger() -> logging.Logger:
    logger = logging.getLogger("course_agent")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if logger.handlers:
        return logger

    handler = logging.FileHandler(
        LOG_PATH,
        encoding="utf-8",
    )

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


logger = create_logger()
