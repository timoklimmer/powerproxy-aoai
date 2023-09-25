from helpers.config import get_config
from typing import List
import logging


LOGGERS: List[logging.Logger] = []

LOGGING_SYS_LEVEL = get_config(
    "sys_level", sections=["monitoring", "logging"], validate=str, default="WARN"
)
logging.basicConfig(level=LOGGING_SYS_LEVEL)
LOGGING_APP_LEVEL = get_config(
    "app_level", sections=["monitoring", "logging"], validate=str, default="INFO"
)


def build_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel("DEBUG")
    LOGGERS.append(logger)
    return logger
