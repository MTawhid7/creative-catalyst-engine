"""
Configures a centralized, structured logger for the application.
This logger is designed for deep observability, writing JSON logs that
include rich contextual information for easier debugging and monitoring.
"""

import logging
import logging.config
import sys
import uuid
import threading

from pythonjsonlogger import jsonlogger
from .. import settings

# --- Thread-safe context for storing the run_id ---
# This is the professional way to handle request-specific context.
log_context = threading.local()


class ContextFilter(logging.Filter):
    """A filter to add a unique run_id from the thread-local context to every log record."""

    def filter(self, record):
        # Get the run_id from our thread-safe context, with a fallback.
        record.run_id = getattr(log_context, "run_id", "no-run-id")
        return True


# --- Structured Logging Configuration ---
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "context_filter": {
            "()": ContextFilter,
        },
    },
    "formatters": {
        "json_formatter": {
            "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s %(funcName)s %(lineno)d %(run_id)s %(message)s",
        },
        "console_formatter": {
            "format": "%(asctime)s - %(levelname)s - [%(name)s:%(lineno)d] (%(run_id)s) - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
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
            "maxBytes": 1024 * 1024 * 5,  # 5 MB
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

# Apply the configuration
logging.config.dictConfig(LOGGING_CONFIG)


def get_logger(name: str) -> logging.Logger:
    """Returns a configured logger instance."""
    return logging.getLogger(name)


def setup_logging_run_id():
    """Generates and sets a unique run_id for the current application run."""
    # Generate a short, unique ID for this run.
    run_id = str(uuid.uuid4()).split("-")[0]
    # Set the run_id on our thread-safe context.
    log_context.run_id = run_id
    return run_id


# --- START OF CHANGE ---
def get_run_id() -> str:
    """
    Safely retrieves the current run_id from the thread-local context.
    Provides a fallback if the run_id is not set.
    """
    return getattr(log_context, "run_id", "no-run-id")


# --- END OF CHANGE ---

# A central logger instance for general use if needed, though get_logger is preferred
logger = get_logger(__name__)
