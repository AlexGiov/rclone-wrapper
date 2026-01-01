"""Utility functions for rclone wrapper."""

import time
import random
import logging
import sys
from pathlib import Path
from typing import Callable, TypeVar, Optional
from logging.handlers import RotatingFileHandler

from .exceptions import RcloneRetryableError

T = TypeVar('T')


def exponential_backoff(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 60.0
) -> float:
    """
    Calculate delay with exponential backoff and jitter.
    
    Args:
        attempt: Current attempt number (0-indexed)
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
    
    Returns:
        Calculated delay in seconds
    """
    delay = min(base_delay * (2 ** attempt), max_delay)
    jitter = random.uniform(0, delay * 0.1)  # 10% jitter
    return delay + jitter


def retry_on_error(
    func: Callable[..., T],
    retries: int = 3,
    retryable_errors: tuple = (RcloneRetryableError,),
    logger: Optional[logging.Logger] = None
) -> T:
    """
    Retry function on retryable errors with exponential backoff.
    
    Args:
        func: Function to execute
        retries: Number of retry attempts
        retryable_errors: Tuple of exception types to retry
        logger: Logger instance for logging retry attempts
    
    Returns:
        Result of the function
    
    Raises:
        Last exception if all retries fail
    """
    if logger is None:
        logger = logging.getLogger(__name__)
    
    last_exception = None
    
    for attempt in range(retries):
        try:
            return func()
        except retryable_errors as e:
            last_exception = e
            if attempt < retries - 1:
                delay = exponential_backoff(attempt)
                logger.warning(
                    f"Attempt {attempt + 1}/{retries} failed: {e}. "
                    f"Retrying in {delay:.2f}s..."
                )
                time.sleep(delay)
            else:
                logger.error(f"All {retries} attempts failed: {e}")
                raise
    
    # This should never be reached, but just in case
    if last_exception:
        raise last_exception
    raise RuntimeError("Unexpected state in retry_on_error")


def setup_logging(
    name: str = "rclone_wrapper",
    log_file: Optional[Path] = None,
    console_level: int = logging.WARNING,
    file_level: int = logging.DEBUG,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Configure logging with console and file handlers.
    
    Args:
        name: Logger name
        log_file: Path to log file (optional)
        console_level: Minimum level for console output
        file_level: Minimum level for file output
        max_bytes: Maximum log file size before rotation
        backup_count: Number of backup files to keep
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.handlers = []  # Clear any existing handlers
    
    # Detailed formatter
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - '
        '%(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Simple formatter for console
    simple_formatter = logging.Formatter(
        '%(levelname)s: %(message)s'
    )
    
    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(console_level)
    console.setFormatter(simple_formatter)
    logger.addHandler(console)
    
    # File handler (if log_file specified)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(file_level)
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)
    
    return logger


def format_size(size_bytes: int) -> str:
    """
    Format byte size to human-readable string.
    
    Args:
        size_bytes: Size in bytes
    
    Returns:
        Formatted size string (e.g., "1.5 GB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def ensure_path_exists(path: Path, create: bool = True) -> Path:
    """
    Ensure a path exists, optionally creating it.
    
    Args:
        path: Path to check/create
        create: Whether to create the path if it doesn't exist
    
    Returns:
        The path (possibly created)
    
    Raises:
        FileNotFoundError: If path doesn't exist and create=False
    """
    if not path.exists():
        if create:
            path.mkdir(parents=True, exist_ok=True)
        else:
            raise FileNotFoundError(f"Path does not exist: {path}")
    return path
