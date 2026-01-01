"""
Domain enums - Consolidated from constants.py and log_parser.py.

All enums used throughout the application are defined here
following PEP 435 (Enum) best practices.
"""

from enum import Enum, IntEnum

__all__ = [
    "ExitCode",
    "LogLevel",
    "ConflictResolve",
    "ConflictLoser",
    "ResyncMode",
    "FileAction",
    "OperationStatus",
    "ParseStatus",
]


class ExitCode(IntEnum):
    """
    Rclone exit codes.

    Reference: https://rclone.org/docs/#exit-code
    """

    SUCCESS = 0
    ERROR = 1  # Non-critical error (retryable)
    SYNTAX_ERROR = 2  # Command line syntax error
    CRITICAL = 7  # Critical error (bisync requires --resync)
    TRANSFER_EXCEEDED = 8  # --max-transfer limit reached
    NO_TRANSFER = 9  # No files transferred (with --error-on-no-transfer)


class LogLevel(str, Enum):
    """
    Rclone log levels.

    Using str as mixin for JSON serialization compatibility.
    """

    DEBUG = "DEBUG"
    INFO = "INFO"
    NOTICE = "NOTICE"
    ERROR = "ERROR"


class ConflictResolve(str, Enum):
    """Bisync conflict resolution strategies."""

    NONE = "none"
    PATH1 = "path1"
    PATH2 = "path2"
    NEWER = "newer"
    OLDER = "older"
    LARGER = "larger"
    SMALLER = "smaller"


class ConflictLoser(str, Enum):
    """Bisync conflict loser handling."""

    NUM = "num"  # Auto-number conflicts
    PATHNAME = "pathname"  # Rename with path name
    DELETE = "delete"  # Delete loser


class ResyncMode(str, Enum):
    """Bisync resync modes."""

    NONE = "none"
    PATH1 = "path1"
    PATH2 = "path2"
    NEWER = "newer"
    OLDER = "older"
    LARGER = "larger"
    SMALLER = "smaller"


class FileAction(str, Enum):
    """
    Actions performed on files during operations.
    
    Unified across all operation types (sync, bisync, compare).
    """

    COPIED = "copied"
    COPY = "copy"  # Alias for COPIED
    DELETED = "deleted"
    DELETE = "delete"  # Alias for DELETED
    UPDATED = "updated"
    UPDATE = "update"  # Alias for UPDATED
    RENAMED = "renamed"
    RENAME = "rename"  # Alias for RENAMED
    ERROR = "error"
    MISSING = "missing"
    MISSING_IN_DEST = "missing_in_dest"  # Compare-specific
    MISSING_IN_SOURCE = "missing_in_source"  # Compare-specific
    DIFFERENT = "different"


class OperationStatus(str, Enum):
    """
    Status of a file operation.
    
    Uniform across all operation types.
    """
    
    SUCCESS = "success"
    FAILED = "failed"
    DETECTED = "detected"  # Compare operations - not executed
    SKIPPED = "skipped"  # Filtered, dry-run, etc.
    IN_PROGRESS = "in_progress"  # For streaming updates


class ParseStatus(str, Enum):
    """Status of parsing operation."""

    SUCCESS = "success"
    NO_DATA = "no_data"
    PARTIAL = "partial"
    FAILED = "failed"
