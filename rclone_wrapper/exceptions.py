"""Custom exceptions for rclone wrapper."""

from typing import Optional


class RcloneError(Exception):
    """Base exception for all rclone operations."""
    
    def __init__(
        self,
        message: str,
        exit_code: Optional[int] = None,
        stderr: Optional[str] = None
    ):
        """
        Initialize RcloneError.
        
        Args:
            message: Error message
            exit_code: Rclone exit code (if available)
            stderr: Stderr output from rclone (if available)
        """
        super().__init__(message)
        self.exit_code = exit_code
        self.stderr = stderr
    
    def __str__(self) -> str:
        """Return formatted error message."""
        msg = super().__str__()
        if self.exit_code is not None:
            msg += f" (exit code: {self.exit_code})"
        if self.stderr:
            msg += f"\nStderr: {self.stderr}"
        return msg


class RcloneRetryableError(RcloneError):
    """
    Error that can be automatically retried.
    
    These errors typically indicate temporary issues like:
    - Network connectivity problems
    - Rate limiting
    - Temporary service unavailability
    """
    pass


class RcloneCriticalError(RcloneError):
    """
    Critical error that requires manual intervention.
    
    These errors typically indicate:
    - Bisync requires --resync
    - Configuration errors
    - Permission denied
    - Data corruption
    """
    pass


class RcloneTimeoutError(RcloneError):
    """Timeout occurred during rclone operation."""
    
    def __init__(self, message: str, timeout: Optional[float] = None):
        """
        Initialize RcloneTimeoutError.
        
        Args:
            message: Error message
            timeout: Timeout value in seconds
        """
        super().__init__(message)
        self.timeout = timeout


class RcloneConfigError(RcloneError):
    """Configuration validation or loading error."""
    pass


class RcloneLockError(RcloneError):
    """Lock file already exists - another operation is running."""
    pass


class RcloneParseError(RcloneError):
    """Error parsing rclone output."""
    pass
