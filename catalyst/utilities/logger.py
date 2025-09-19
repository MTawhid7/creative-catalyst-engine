# catalyst/utilities/logger.py

"""
Configures a centralized, structured logger for the application.
This version provides a dual-format logging setup:
1.  Human-Readable, Color-Coded Console Logs.
2.  Machine-Readable JSON File Logs.
"""

import logging
import logging.config
import sys
import threading
from .. import settings

# Thread-safe context for storing the run_id.
log_context = threading.local()


class ContextFilter(logging.Filter):
    """A filter to add a unique run_id from the thread-local context."""

    def filter(self, record):
        record.run_id = getattr(log_context, "run_id", "init")
        return True


# --- START: DEFINITIVE LOGGING REFACTOR ---
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "context_filter": {"()": ContextFilter},
    },
    "formatters": {
        "json_formatter": {
            "class": "pythonjsonlogger.json.JsonFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s %(funcName)s %(lineno)d %(run_id)s %(message)s",
        },
        # The console formatter now points to the class in its new, separate file.
        # This breaks the circular import.
        "console_formatter": {
            "()": "catalyst.utilities.log_formatter.ColoredFormatter",
            "format": "%(asctime)s | %(levelname)-8s | [%(run_id)s] %(name)s:%(lineno)d - %(message)s",
            "datefmt": "%H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "stream": sys.stdout,
            "formatter": "console_formatter",
            "filters": ["context_filter"],
        },
        "file_json": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": settings.LOG_FILE_PATH,
            "maxBytes": 1024 * 1024 * 5,
            "backupCount": 5,
            "formatter": "json_formatter",
            "filters": ["context_filter"],
        },
    },
    "root": {
        "level": "INFO",
        "handlers": ["console", "file_json"],
    },
}
# --- END: DEFINITIVE LOGGING REFACTOR ---


def setup_logging_run_id(run_id: str):
    """Sets the unique run_id for the current application run."""
    log_context.run_id = run_id


def get_run_id() -> str:
    """Safely retrieves the current run_id from the thread-local context."""
    return getattr(log_context, "run_id", "no-id-set")


# Apply the configuration
logging.config.dictConfig(LOGGING_CONFIG)


def get_logger(name: str) -> logging.Logger:
    """Returns a configured logger instance."""
    return logging.getLogger(name)
