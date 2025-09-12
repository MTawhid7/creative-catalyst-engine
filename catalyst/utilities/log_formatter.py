# catalyst/utilities/log_formatter.py

"""
This module contains the custom ColoredFormatter class for the application's
human-readable console logging.
"""

import logging


class ColoredFormatter(logging.Formatter):
    """A custom formatter to add color to log levels for readability."""

    GREY = "\x1b[38;20m"
    YELLOW = "\x1b[33;20m"
    RED = "\x1b[31;20m"
    BOLD_RED = "\x1b[31;1m"
    GREEN = "\x1b[32;20m"
    RESET = "\x1b[0m"

    def __init__(self, fmt, datefmt=None):
        super().__init__(fmt, datefmt)
        base_fmt = self._fmt or ""
        self.FORMATS = {
            logging.DEBUG: self.GREY + base_fmt + self.RESET,
            logging.INFO: self.GREEN + base_fmt + self.RESET,
            logging.WARNING: self.YELLOW + base_fmt + self.RESET,
            logging.ERROR: self.RED + base_fmt + self.RESET,
            logging.CRITICAL: self.BOLD_RED + base_fmt + self.RESET,
        }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, self.datefmt)
        return formatter.format(record)
