from typing import Optional, Dict

import logging
from mllo_web.app.api.config import AppConfig, get_config


class BaseFormatter(logging.Formatter):
    """Base class for logging formatter."""

    def format(self, record: logging.LogRecord) -> str:
        formatter = logging.Formatter(self.log_fmt(record.levelno))
        return formatter.format(record)

    def log_fmt(self, levelno: int) -> str:
        return "[%(asctime)s]::[%(name)s]::%(levelname)s --> %(message)s"


class Logger:
    loggers: Dict[str, logging.Logger] = {}

    @classmethod
    def get_logger(cls, name='MLLO', config: Optional[AppConfig] = None):
        config = config or get_config()
        if name in cls.loggers:
            return cls.loggers[name]

        logger = logging.getLogger(name)
        logger.setLevel(config.log_level.upper())

        ch: logging.Handler = logging.StreamHandler()
        ch.setFormatter(BaseFormatter())

        logger.addHandler(ch)
        
        cls.loggers[name] = logger
        return cls.loggers[name]
