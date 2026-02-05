"""
Colored logging utilities for enhanced terminal output.

Provides colored terminal output with Windows support via colorama.
Color scheme:
- RED: Errors and critical issues
- YELLOW: Warnings
- GREEN: Success messages and working features
- BLUE: General information
- WHITE: Trivial/debug text
- CYAN: Highlights and important values
"""

import logging
import sys
from typing import Optional


try:
    from colorama import Fore, Style
    from colorama import init as colorama_init

    # Initialize colorama for Windows support
    colorama_init(autoreset=True)
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False

    # Fallback: no colors
    class _DummyColor:
        def __getattr__(self, name):
            return ""

    Fore = Style = _DummyColor()


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors to log messages based on level."""

    # Color mapping for log levels
    COLORS = {
        logging.DEBUG: Fore.WHITE,  # Trivial text in white
        logging.INFO: Fore.BLUE,  # General information in blue
        logging.WARNING: Fore.YELLOW,  # Warnings in yellow
        logging.ERROR: Fore.RED,  # Errors in red
        logging.CRITICAL: Fore.RED + Style.BRIGHT,  # Critical errors in bright red
    }

    # Success level (custom)
    SUCCESS = 25  # Between INFO (20) and WARNING (30)
    logging.addLevelName(SUCCESS, "SUCCESS")

    def __init__(self, fmt: Optional[str] = None, datefmt: Optional[str] = None):
        """Initialize the colored formatter.

        Args:
            fmt: Log message format string
            datefmt: Date format string
        """
        if fmt is None:
            fmt = "%(asctime)s - %(levelname)s - %(message)s"
        if datefmt is None:
            datefmt = "%H:%M:%S"
        super().__init__(fmt, datefmt)

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record with colors.

        Args:
            record: The log record to format

        Returns:
            Formatted and colored log message
        """
        # Get the color for this log level
        if record.levelno == self.SUCCESS:
            color = Fore.GREEN
        else:
            color = self.COLORS.get(record.levelno, Fore.WHITE)

        # Save the original level name
        original_levelname = record.levelname

        # Add color to the level name
        if COLORAMA_AVAILABLE:
            record.levelname = f"{color}{record.levelname}{Style.RESET_ALL}"

        # Format the message
        formatted = super().format(record)

        # Restore the original level name
        record.levelname = original_levelname

        # Add color to the entire message if it's an error or warning
        if COLORAMA_AVAILABLE and record.levelno >= logging.WARNING:
            formatted = f"{color}{formatted}{Style.RESET_ALL}"

        return formatted


class ColoredLogger(logging.Logger):
    """Custom logger with colored output and success() method."""

    def __init__(self, name: str, level: int = logging.NOTSET):
        """Initialize the colored logger.

        Args:
            name: Logger name
            level: Logging level
        """
        super().__init__(name, level)

    def success(self, message: str, *args, **kwargs):
        """Log a success message in green.

        Args:
            message: The success message
            *args: Additional positional arguments for formatting
            **kwargs: Additional keyword arguments
        """
        if self.isEnabledFor(ColoredFormatter.SUCCESS):
            self._log(ColoredFormatter.SUCCESS, message, args, **kwargs)


def get_colored_logger(name: str, level: int = logging.INFO, add_handler: bool = True) -> ColoredLogger:
    """Get a colored logger instance.

    Args:
        name: Logger name
        level: Logging level (default: INFO)
        add_handler: Whether to add a colored stream handler (default: True)

    Returns:
        ColoredLogger instance with colored output
    """
    # Set the custom logger class
    logging.setLoggerClass(ColoredLogger)
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Add colored handler if requested and not already present
    if add_handler and not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        handler.setFormatter(ColoredFormatter())
        logger.addHandler(handler)

    return logger


def setup_colored_logging(level: int = logging.INFO):
    """Configure colored logging for the entire application.

    Args:
        level: The logging level to use (default: INFO)
    """
    # Set the custom logger class globally
    logging.setLoggerClass(ColoredLogger)

    # Configure root logger
    root = logging.getLogger()
    root.setLevel(level)

    # Remove existing handlers
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    # Add colored handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(ColoredFormatter())
    root.addHandler(handler)


class LogFilter(logging.Filter):
    """Filter to exclude specific log messages."""

    def __init__(self, exclude_patterns: list[str] = None):
        """Initialize the log filter.

        Args:
            exclude_patterns: List of substrings to filter out
        """
        super().__init__()
        self.exclude_patterns = exclude_patterns or []

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter log records.

        Args:
            record: The log record to filter

        Returns:
            False if the record should be filtered out, True otherwise
        """
        message = record.getMessage().lower()
        return not any(pattern.lower() in message for pattern in self.exclude_patterns)


def create_filtered_logger(name: str, exclude_patterns: list[str] = None, level: int = logging.INFO) -> ColoredLogger:
    """Create a colored logger with message filtering.

    Args:
        name: Logger name
        exclude_patterns: List of patterns to exclude from logs
        level: Logging level

    Returns:
        Filtered colored logger instance
    """
    logger = get_colored_logger(name, level)

    # Add filter to all handlers
    log_filter = LogFilter(exclude_patterns)
    for handler in logger.handlers:
        handler.addFilter(log_filter)

    return logger


# Convenience functions for colored output
def print_error(message: str):
    """Print an error message in red."""
    if COLORAMA_AVAILABLE:
        print(f"{Fore.RED}{message}{Style.RESET_ALL}")
    else:
        print(f"ERROR: {message}")


def print_warning(message: str):
    """Print a warning message in yellow."""
    if COLORAMA_AVAILABLE:
        print(f"{Fore.YELLOW}{message}{Style.RESET_ALL}")
    else:
        print(f"WARNING: {message}")


def print_success(message: str):
    """Print a success message in green."""
    if COLORAMA_AVAILABLE:
        print(f"{Fore.GREEN}{message}{Style.RESET_ALL}")
    else:
        print(f"SUCCESS: {message}")


def print_info(message: str):
    """Print an info message in blue."""
    if COLORAMA_AVAILABLE:
        print(f"{Fore.BLUE}{message}{Style.RESET_ALL}")
    else:
        print(f"INFO: {message}")


def print_debug(message: str):
    """Print a debug message in white."""
    if COLORAMA_AVAILABLE:
        print(f"{Fore.WHITE}{message}{Style.RESET_ALL}")
    else:
        print(message)


def print_highlight(message: str):
    """Print a highlighted message in cyan."""
    if COLORAMA_AVAILABLE:
        print(f"{Fore.CYAN}{Style.BRIGHT}{message}{Style.RESET_ALL}")
    else:
        print(f"*** {message} ***")
