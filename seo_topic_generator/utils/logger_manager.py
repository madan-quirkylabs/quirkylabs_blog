"""
logger_manager.py

Purpose:
    Centralized JSON-based structured logger for SEO Topic Generator.

Features:
    - Logs to both console (colored) and file (structured JSON Lines format)
    - Unicode-safe output (no \ud83c encoding issues)
    - Easy metadata attachment via extra
    - Timestamped filenames to avoid overwrites
    - Safe handler initialization (no duplicate logs)

Author: QuirkyLabs
"""

import os
import json
import logging
from datetime import datetime

class JsonFormatter(logging.Formatter):
    """
    Formatter to output logs as JSON lines (for file storage).
    """

    def __init__(self, ensure_ascii=False):
        super().__init__()
        self.ensure_ascii = ensure_ascii

    def format(self, record):
        log_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage()
        }
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            log_record.update(record.extra)
        return json.dumps(log_record, ensure_ascii=self.ensure_ascii)

class ConsoleFormatter(logging.Formatter):
    """
    Formatter for console logs with color coding.
    """

    COLORS = {
        "DEBUG": "\033[94m",     # Blue
        "INFO": "\033[92m",      # Green
        "WARNING": "\033[93m",   # Yellow
        "ERROR": "\033[91m",     # Red
        "CRITICAL": "\033[95m",  # Magenta
        "RESET": "\033[0m"       # Reset
    }

    def format(self, record):
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
        reset = self.COLORS["RESET"]
        return f"{color}[{timestamp}] {record.levelname}: {record.getMessage()}{reset}"

class LoggerManager:
    """
    Manages logging configuration for file and console outputs.
    """

    def __init__(self, log_folder_path="../outputs/logs/", log_prefix="app_log"):
        """
        Initialize the logger.

        Args:
            log_folder_path (str): Directory to store log files.
            log_prefix (str): Prefix for log filenames.
        """
        os.makedirs(log_folder_path, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"{log_prefix}_{timestamp}.jsonl"
        log_filepath = os.path.join(log_folder_path, log_filename)

        self.logger = logging.getLogger(log_prefix)
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False  # Prevents accidental log duplication in nested modules

        if not self.logger.handlers:
            self._setup_handlers(log_filepath)

    def _setup_handlers(self, log_filepath):
        # File Handler (JSON output)
        file_handler = logging.FileHandler(log_filepath, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(JsonFormatter(ensure_ascii=False))

        # Console Handler (Colorized output)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(ConsoleFormatter())

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    # Public logging methods
    def debug(self, message, extra=None):
        self.logger.debug(message, extra={"extra": extra} if extra else {})

    def info(self, message, extra=None):
        self.logger.info(message, extra={"extra": extra} if extra else {})

    def warning(self, message, extra=None):
        self.logger.warning(message, extra={"extra": extra} if extra else {})

    def error(self, message, extra=None):
        self.logger.error(message, extra={"extra": extra} if extra else {})

    def critical(self, message, extra=None):
        self.logger.critical(message, extra={"extra": extra} if extra else {})
