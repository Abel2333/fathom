"""Logging configuration for the Fathom project."""

import logging
import sys
from pathlib import Path
from typing import Optional

from fathom.config.loader import ConfigLoader


class LoggerSetup:
    """Centralized logging configuration for Fathom."""

    _initialized = False

    @classmethod
    def setup_logging(cls, config: Optional[ConfigLoader] = None) -> None:
        """
        Configure logging for the application.

        Args:
            config: Optional ConfigLoader instance. If not provided, creates a new one.
        """
        if cls._initialized:
            return

        if config is None:
            config = ConfigLoader()

        # Get logging configuration
        log_config = config.config.get("logging", {})
        log_level = log_config.get("level", "INFO").upper()
        log_format = log_config.get(
            "format",
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        log_to_file = log_config.get("log_to_file", False)
        log_file_path = log_config.get("log_file", "logs/fathom.log")

        # Create formatter
        formatter = logging.Formatter(log_format)

        # Get root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, log_level))

        # Remove existing handlers to avoid duplicates
        root_logger.handlers.clear()

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level))
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        # File handler (optional)
        if log_to_file:
            log_path = Path(log_file_path)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.FileHandler(log_path)
            file_handler.setLevel(getattr(logging, log_level))
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)

        cls._initialized = True

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        Get a logger instance with the given name.

        Args:
            name: Name for the logger (typically __name__)

        Returns:
            Configured logger instance
        """
        if not cls._initialized:
            cls.setup_logging()

        return logging.getLogger(name)


def get_logger(name: str) -> logging.Logger:
    """
    Convenience function to get a logger instance.

    Args:
        name: Name for the logger (typically __name__)

    Returns:
        Configured logger instance
    """
    return LoggerSetup.get_logger(name)
