"""Constants for rclone wrapper."""

from enum import IntEnum, Enum


class ExitCode(IntEnum):
    """Rclone exit codes."""
    SUCCESS = 0
    ERROR = 1              # Non-critical error (retryable)
    SYNTAX_ERROR = 2       # Command line syntax error
    CRITICAL = 7           # Critical error (bisync requires --resync)
    TRANSFER_EXCEEDED = 8  # --max-transfer limit reached
    NO_TRANSFER = 9        # No files transferred (with --error-on-no-transfer)


class LogLevel(str, Enum):
    """Rclone log levels."""
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
    NUM = "num"           # Auto-number conflicts
    PATHNAME = "pathname" # Rename with path name
    DELETE = "delete"     # Delete loser


class ResyncMode(str, Enum):
    """Bisync resync modes."""
    NONE = "none"
    PATH1 = "path1"
    PATH2 = "path2"
    NEWER = "newer"
    OLDER = "older"
    LARGER = "larger"
    SMALLER = "smaller"


# Default values
DEFAULT_TIMEOUT = 3600  # 1 hour
DEFAULT_CHECKERS = 8
DEFAULT_TRANSFERS = 4
DEFAULT_RETENTION_DAYS = 30
DEFAULT_MAX_LOCK = "2m"
DEFAULT_RETRIES = 3
DEFAULT_RETRY_SLEEP = 10  # seconds

# Paths
RCLONE_CACHE_DIR = ".cache/rclone"
BISYNC_WORKDIR = "bisync"
