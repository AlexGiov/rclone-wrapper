"""
Value objects - Immutable domain values.

Value objects represent concepts that are defined by their values,
not by identity. They are immutable and can be freely copied.

Following Domain-Driven Design principles:
- Immutable (frozen=True)
- Defined by values, not identity
- Self-validating
- No side effects
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

__all__ = ["OperationTiming", "RemotePath", "FolderPairResult"]


@dataclass(frozen=True)
class OperationTiming:
    """
    Immutable value object representing operation timing information.

    Attributes:
        start: Operation start timestamp
        end: Operation end timestamp

    Example:
        >>> timing = OperationTiming(
        ...     start=datetime(2025, 1, 1, 10, 0, 0),
        ...     end=datetime(2025, 1, 1, 10, 5, 30)
        ... )
        >>> timing.duration_seconds
        330.0
    """

    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        """Validate timing values."""
        if self.end < self.start:
            raise ValueError(
                f"End time ({self.end}) cannot be before start time ({self.start})"
            )

    @property
    def duration_seconds(self) -> float:
        """Calculate duration in seconds."""
        return (self.end - self.start).total_seconds()
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "duration_seconds": round(self.duration_seconds, 2),
        }

    @classmethod
    def now(cls) -> "OperationTiming":
        """Create timing with current timestamp for both start and end."""
        now = datetime.now()
        return cls(start=now, end=now)

    def with_end(self, end: datetime) -> "OperationTiming":
        """Create new timing with updated end time."""
        return OperationTiming(start=self.start, end=end)


@dataclass(frozen=True)
class RemotePath:
    """
    Immutable value object representing a remote path.

    Remote paths have the format: remote_name:path/to/folder

    Attributes:
        remote_name: Name of the rclone remote (e.g., 'gdrive')
        path: Path on the remote (e.g., 'documents/work')

    Example:
        >>> path = RemotePath('gdrive', 'documents/work')
        >>> str(path)
        'gdrive:documents/work'
        >>> path.full_path
        'gdrive:documents/work'
    """

    remote_name: str
    path: str

    def __post_init__(self) -> None:
        """Validate remote path values."""
        if not self.remote_name:
            raise ValueError("Remote name cannot be empty")

        if ":" in self.remote_name:
            raise ValueError(
                f"Remote name cannot contain ':' character: {self.remote_name}"
            )

    def __str__(self) -> str:
        """Return string representation in rclone format."""
        return self.full_path

    @property
    def full_path(self) -> str:
        """Return full remote path in rclone format (remote:path)."""
        return f"{self.remote_name}:{self.path}"

    @classmethod
    def parse(cls, path: str) -> Optional["RemotePath"]:
        """
        Parse a string into RemotePath.

        Args:
            path: Path string in format 'remote:path' or local path

        Returns:
            RemotePath if path is remote, None if local

        Example:
            >>> RemotePath.parse('gdrive:/documents')
            RemotePath(remote_name='gdrive', path='/documents')
            >>> RemotePath.parse('C:\\Users\\data')
            None
        """
        if ":" not in path:
            return None

        # Check for Windows drive (C:, D:, etc.)
        if len(path) >= 2 and path[1] == ":" and path[0].isalpha():
            return None

        # Split remote:path
        parts = path.split(":", 1)
        if len(parts) != 2:
            return None

        remote_name, remote_path = parts
        if not remote_name:
            return None

        return cls(remote_name=remote_name, path=remote_path)

    def join(self, *parts: str) -> "RemotePath":
        """
        Join path parts to create new RemotePath.

        Example:
            >>> base = RemotePath('gdrive', 'documents')
            >>> base.join('work', 'projects')
            RemotePath(remote_name='gdrive', path='documents/work/projects')
        """
        import posixpath

        new_path = posixpath.join(self.path, *parts)
        return RemotePath(remote_name=self.remote_name, path=new_path)


@dataclass(frozen=True)
class FolderPairResult:
    """
    Value object representing the result of processing a single folder pair.
    
    Immutable summary of what happened to ONE pair of folders.
    Used to aggregate results in batch operations.
    
    Attributes:
        source_path: Source folder path
        destination_path: Destination folder path
        operations_count: Number of file operations performed
        errors_count: Number of errors encountered
        duration_seconds: Duration of the operation in seconds
        timestamp: When the operation started
    
    Example:
        >>> result = FolderPairResult(
        ...     source_path="./data",
        ...     destination_path="remote:backup/data",
        ...     operations_count=42,
        ...     errors_count=0,
        ...     duration_seconds=12.5,
        ...     timestamp=datetime.now()
        ... )
        >>> result.to_dict()
        {'source': './data', 'destination': 'remote:backup/data', ...}
    """
    
    source_path: str
    destination_path: str
    operations_count: int
    errors_count: int
    duration_seconds: float
    timestamp: datetime
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "source": self.source_path,
            "destination": self.destination_path,
            "operations": self.operations_count,
            "errors": self.errors_count,
            "duration": round(self.duration_seconds, 2),
            "timestamp": self.timestamp.isoformat(),
        }

