import logging.handlers
import socket
import urllib.parse
from pathlib import Path
from typing import Any, Dict, Optional

from mllo_web.app.services.config import MlloAppConfig
from mllo_web.app.services.config.config_default import get_config

try:
    import syslog

    SYSLOG_AVAILABLE = True
except ImportError:
    SYSLOG_AVAILABLE = False


# module level functions
def debug(msg: str, *args: str, **kwargs: Any) -> None:  # noqa D103
    MlloLogger.get_logger().debug(msg, *args, **kwargs)


def info(msg: str, *args: str, **kwargs: Any) -> None:  # noqa D103
    MlloLogger.get_logger().info(msg, *args, **kwargs)


def warning(msg: str, *args: str, **kwargs: Any) -> None:  # noqa D103
    MlloLogger.get_logger().warning(msg, *args, **kwargs)


def error(msg: str, *args: str, **kwargs: Any) -> None:  # noqa D103
    MlloLogger.get_logger().error(msg, *args, **kwargs)


def critical(msg: str, *args: str, **kwargs: Any) -> None:  # noqa D103
    MlloLogger.get_logger().critical(msg, *args, **kwargs)


def log(level: int, msg: str, *args: str, **kwargs: Any) -> None:  # noqa D103
    MlloLogger.get_logger().log(level, msg, *args, **kwargs)


def disable(level: int = logging.CRITICAL) -> None:  # noqa D103
    logging.disable(level)


def basicConfig(**kwargs: Any) -> None:  # noqa D103
    logging.basicConfig(**kwargs)


_FACILITY_MAP = (
    {
        "LOG_KERN": syslog.LOG_KERN,
        "LOG_USER": syslog.LOG_USER,
        "LOG_MAIL": syslog.LOG_MAIL,
        "LOG_DAEMON": syslog.LOG_DAEMON,
        "LOG_AUTH": syslog.LOG_AUTH,
        "LOG_LPR": syslog.LOG_LPR,
        "LOG_NEWS": syslog.LOG_NEWS,
        "LOG_UUCP": syslog.LOG_UUCP,
        "LOG_CRON": syslog.LOG_CRON,
        "LOG_SYSLOG": syslog.LOG_SYSLOG,
        "LOG_LOCAL0": syslog.LOG_LOCAL0,
        "LOG_LOCAL1": syslog.LOG_LOCAL1,
        "LOG_LOCAL2": syslog.LOG_LOCAL2,
        "LOG_LOCAL3": syslog.LOG_LOCAL3,
        "LOG_LOCAL4": syslog.LOG_LOCAL4,
        "LOG_LOCAL5": syslog.LOG_LOCAL5,
        "LOG_LOCAL6": syslog.LOG_LOCAL6,
        "LOG_LOCAL7": syslog.LOG_LOCAL7,
    }
    if SYSLOG_AVAILABLE
    else {}
)

_SOCK_MAP = {
    "SOCK_STREAM": socket.SOCK_STREAM,
    "SOCK_DGRAM": socket.SOCK_DGRAM,
}


class MlloFormatter(logging.Formatter):
    """Base class for logging formatter."""

    def format(self, record: logging.LogRecord) -> str:  # noqa D102
        formatter = logging.Formatter(self.log_fmt(record.levelno))
        return formatter.format(record)

    def log_fmt(self, levelno: int) -> str:  # noqa D102
        return "[%(asctime)s]::[%(name)s]::%(levelname)s --> %(message)s"


class MlloSyslogFormatter(MlloFormatter):
    """Formatting for syslog."""

    def log_fmt(self, levelno: int) -> str:  # noqa D102
        return "%(name)s [%(process)d] <%(levelname)s> %(message)s"


class MlloLegacyLogFormatter(MlloFormatter):  # noqa D102
    """Formatting for the Mllo Logger (legacy version)."""

    FORMATS = {
        logging.DEBUG: "   | %(message)s",
        logging.INFO: ">> %(message)s",
        logging.WARNING: "** %(message)s",
        logging.ERROR: "*** %(message)s",
        logging.CRITICAL: "### %(message)s",
    }

    def log_fmt(self, levelno: int) -> str:  # noqa D102
        format = self.FORMATS.get(levelno)
        assert format is not None
        return format


class MlloPlainLogFormatter(MlloFormatter):
    """Custom Formatting for the Mllo Logger (plain version)."""

    def log_fmt(self, levelno: int) -> str:  # noqa D102
        return "[%(asctime)s]::[%(name)s]::%(levelname)s --> %(message)s"


class MlloColorLogFormatter(MlloFormatter):
    """Custom Formatting for the Mllo Logger."""

    # Color Codes
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    cyan = "\x1b[36;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"

    # Log Format
    log_format = "[%(asctime)s]::[%(name)s]::%(levelname)s --> %(message)s"
    ## More Formatting Options: %(pathname)s, %(filename)s, %(module)s, %(lineno)d

    # Format Map
    FORMATS = {
        logging.DEBUG: cyan + log_format + reset,
        logging.INFO: grey + log_format + reset,
        logging.WARNING: yellow + log_format + reset,
        logging.ERROR: red + log_format + reset,
        logging.CRITICAL: bold_red + log_format + reset,
    }

    def log_fmt(self, levelno: int) -> str:  # noqa D102
        format = self.FORMATS.get(levelno)
        assert format is not None
        return format


LOG_FORMATTERS = {
    "plain": MlloPlainLogFormatter,
    "color": MlloColorLogFormatter,
    "syslog": MlloSyslogFormatter,
    "legacy": MlloLegacyLogFormatter,
}


class MlloLogger(object):  # noqa D102
    loggers: Dict[str, logging.Logger] = {}

    @classmethod
    def get_logger(cls, name: str = "MLLO", config: Optional[MlloAppConfig] = None) -> logging.Logger:  # noqa D102
        config = config or get_config()
        if name in cls.loggers:
            return cls.loggers[name]

        logger = logging.getLogger(name)
        logger.setLevel(config.log_level.upper())  # yes, strings work here
        for ch in cls.get_loggers(config):
            logger.addHandler(ch)
        cls.loggers[name] = logger
        return cls.loggers[name]

    @classmethod
    def get_loggers(cls, config: MlloAppConfig) -> list[logging.Handler]:  # noqa D102
        handler_strs = config.log_handlers
        handlers = []
        for handler in handler_strs:
            handler_name, *args = handler.split("=", 2)
            arg = args[0] if len(args) > 0 else None

            # console and file get the fancy formatter.
            # syslog gets a simple one
            # http gets no custom formatter
            formatter = LOG_FORMATTERS[config.log_format]
            if handler_name == "console":
                ch: logging.Handler = logging.StreamHandler()
                ch.setFormatter(formatter())
                handlers.append(ch)

            elif handler_name == "syslog":
                ch = cls._parse_syslog_args(arg)
                handlers.append(ch)

            elif handler_name == "file":
                ch = cls._parse_file_args(arg)
                ch.setFormatter(formatter())
                handlers.append(ch)

            elif handler_name == "http":
                ch = cls._parse_http_args(arg)
                handlers.append(ch)
        return handlers

    @staticmethod
    def _parse_syslog_args(args: Optional[str] = None) -> logging.Handler:
        if not SYSLOG_AVAILABLE:
            raise ValueError("syslog is not available on this system")
        if not args:
            args = "/dev/log" if Path("/dev/log").exists() else "address:localhost:514"
        syslog_args: Dict[str, Any] = {}
        try:
            for a in args.split(","):
                arg_name, *arg_value = a.split(":", 2)
                if arg_name == "address":
                    host, *port_list = arg_value
                    port = 514 if not port_list else int(port_list[0])
                    syslog_args["address"] = (host, port)
                elif arg_name == "facility":
                    syslog_args["facility"] = _FACILITY_MAP[arg_value[0]]
                elif arg_name == "socktype":
                    syslog_args["socktype"] = _SOCK_MAP[arg_value[0]]
                else:
                    syslog_args["address"] = arg_name
        except Exception:
            raise ValueError(f"{args} is not a value argument list for syslog logging")
        return logging.handlers.SysLogHandler(**syslog_args)

    @staticmethod
    def _parse_file_args(args: Optional[str] = None) -> logging.Handler:  # noqa D102
        if not args:
            raise ValueError("please provide filename for file logging using format 'file=/path/to/logfile.txt'")
        return logging.FileHandler(args)

    @staticmethod
    def _parse_http_args(args: Optional[str] = None) -> logging.Handler:  # noqa D102
        if not args:
            raise ValueError("please provide destination for http logging using format 'http=url'")
        arg_list = args.split(",")
        url = urllib.parse.urlparse(arg_list.pop(0))
        if url.scheme != "http":
            raise ValueError(f"the http logging module can only log to HTTP URLs, but {url.scheme} was specified")
        host = url.hostname
        path = url.path
        port = url.port or 80

        syslog_args: Dict[str, Any] = {}
        for a in arg_list:
            arg_name, *arg_value = a.split(":", 2)
            if arg_name == "method":
                method = arg_value[0] if len(arg_value) > 0 else "GET"
                syslog_args[arg_name] = method
            else:  # TODO: Provide support for SSL context and credentials
                pass
        return logging.handlers.HTTPHandler(f"{host}:{port}", path, **syslog_args)
