"""
Domain models - Core business entities.

These models represent the core business concepts and data structures
used throughout the application. They are primarily dataclasses for
clean, typed data containers.

Following best practices:
- Dataclasses for clean syntax
- Type hints for all fields
- Validation in __post_init__ where needed
- Helper methods for common operations
- JSON serialization support
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from .enums import FileAction, ParseStatus, OperationStatus
from .value_objects import FolderPairResult

__all__ = [
    "FileInfo",
    "ErrorInfo",
    "TransferStats",
    "ParsedData",
    "FileState",
    "FileOperation",
    "UnifiedOperationLog",
    "Summary",
    "OperationLog",
]


# ==============================================================================
# PARSED DATA MODELS
# ==============================================================================


@dataclass
class FileInfo:
    """
    Information about a file operation.

    Attributes:
        path: File path
        size: File size in bytes
        modtime: Modification timestamp
        action: Action performed on file
        source: Source location (for bisync: 'Path1' or 'Path2')
        destination: Destination location
        error: Error message if operation failed
        metadata: Additional metadata
    """

    path: str
    size: int = 0
    modtime: Optional[datetime] = None
    action: FileAction = FileAction.COPIED
    source: Optional[str] = None
    destination: Optional[str] = None
    error: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ErrorInfo:
    """
    Information about an error during operation.

    Attributes:
        path: File path where error occurred (if applicable)
        message: Error message
        level: Error level (ERROR, WARNING, etc.)
        timestamp: When error occurred
    """

    path: Optional[str]
    message: str
    level: str = "ERROR"
    timestamp: Optional[datetime] = None


@dataclass
class TransferStats:
    """
    Statistics about a transfer operation.

    Contains comprehensive statistics for all operation types.
    """

    # General stats
    total_files: int = 0
    copied_files: int = 0
    deleted_files: int = 0
    updated_files: int = 0
    renamed_files: int = 0
    error_files: int = 0
    total_size: int = 0
    transferred_size: int = 0
    elapsed_time: float = 0.0

    # Bisync-specific
    path1_to_path2: int = 0
    path2_to_path1: int = 0

    # Compare-specific
    matches: int = 0
    missing_in_dest: int = 0
    missing_in_source: int = 0
    different: int = 0


@dataclass
class ParsedData:
    """
    Unified parsed data structure from rclone output.

    This is the canonical representation of parsed rclone command output,
    regardless of the parsing strategy used.
    """

    status: ParseStatus
    stats: TransferStats
    files_copied: list[FileInfo] = field(default_factory=list)
    files_deleted: list[FileInfo] = field(default_factory=list)
    files_updated: list[FileInfo] = field(default_factory=list)
    files_renamed: list[FileInfo] = field(default_factory=list)
    errors: list[ErrorInfo] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    # Compare-specific (for check command)
    missing_in_dest: list[str] = field(default_factory=list)
    missing_in_source: list[str] = field(default_factory=list)
    different_files: list[str] = field(default_factory=list)

    def get_all_files(self) -> list[FileInfo]:
        """Get all files regardless of action."""
        return (
            self.files_copied
            + self.files_deleted
            + self.files_updated
            + self.files_renamed
        )


# ==============================================================================
# UNIFIED OPERATION LOG MODELS
# ==============================================================================


@dataclass
class FileState:
    """
    State of a file at a specific location.

    Represents the state of a file (or lack thereof) at either
    source or destination during an operation.

    Attributes:
        exists: Whether file exists at this location
        size: File size in bytes (if exists)
        modtime: Modification time ISO string (if exists)
        hash: File hash/checksum (if available)
    """

    exists: bool
    size: Optional[int] = None
    modtime: Optional[str] = None  # ISO format string
    hash: Optional[str] = None  # MD5 hash if available

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict, omitting None values for cleaner JSON."""
        result: dict[str, Any] = {"exists": self.exists}
        if self.exists:
            if self.size is not None:
                result["size"] = self.size
            if self.modtime is not None:
                result["modtime"] = self.modtime
            if self.hash is not None:
                result["hash"] = self.hash
        return result


@dataclass
class FileOperation:
    """
    Single file operation in unified format.

    Represents a file operation (copy, delete, update, etc.) with
    complete information about source and destination states.

    Attributes:
        path: File path
        source: State at source
        destination: State at destination
        action: Operation performed (copy, delete, update, conflict, error)
        direction: Direction of operation (source_to_dest, dest_to_source, None)
        status: Operation status (success, failed, conflict)
        error: Error message if failed
        timestamp: When operation occurred (ISO format)
        
        # NEW: Direct JSON fields from rclone --use-json-log
        json_object: Object name from JSON log (file/folder name)
        json_msg: Message from JSON log (e.g., "Copied (new)")
        json_level: Log level from JSON (info, error, notice)
        json_size: File size in bytes from JSON
        json_objectType: Object type from JSON (*local.Object, *drive.Directory)
        json_time: Precise ISO8601 timestamp from JSON
        json_source: Source file in rclone code from JSON
    """

    path: str
    source: FileState
    destination: FileState
    action: str
    direction: Optional[str] = None
    status: str = "success"
    error: Optional[str] = None
    timestamp: Optional[str] = None
    
    # NEW: JSON fields from rclone --use-json-log
    json_object: Optional[str] = None
    json_msg: Optional[str] = None
    json_level: Optional[str] = None
    json_size: Optional[int] = None
    json_objectType: Optional[str] = None
    json_time: Optional[str] = None
    json_source: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        # NEW: Prefer JSON fields if available (from --use-json-log)
        if self.json_object is not None:
            # Use JSON format matching report_template.json
            result: dict[str, Any] = {
                "object": self.json_object,
                "msg": self.json_msg,
                "level": self.json_level,
                "size": self.json_size,
                "objectType": self.json_objectType,
                "time": self.json_time,
                "source": self.json_source,
            }
        else:
            # DEPRECATED: Fallback to old format (text parsing)
            result: dict[str, Any] = {
                "path": self.path,
                "source": self.source.to_dict(),
                "destination": self.destination.to_dict(),
                "action": self.action,
                "status": self.status,
            }
            if self.direction is not None:
                result["direction"] = self.direction
            if self.error is not None:
                result["error"] = self.error
            if self.timestamp is not None:
                result["timestamp"] = self.timestamp
        return result


@dataclass
class UnifiedOperationLog:
    """
    Unified log structure for all operation types.

    This is the canonical format for operation logs, used by all
    operation types (sync, bisync, compare, backup) for consistency.

    Supports both individual operations and batch operations through
    the metadata field.
    """

    operation_type: str
    timestamp_start: str
    timestamp_end: Optional[str] = None
    duration_seconds: Optional[float] = None
    source_path: str = ""
    destination_path: str = ""
    mode: str = "one-way"
    comparison_method: str = "size+modtime"

    # Summary
    total_operations: int = 0
    source_modified: int = 0
    destination_modified: int = 0
    conflicts: int = 0
    errors: int = 0

    # Operations (legacy format - kept for backward compatibility)
    operations: list[FileOperation] = field(default_factory=list)

    # File operations grouped by action (Opzione B+)
    file_operations: dict[str, list[dict[str, Any]]] = field(default_factory=dict)

    # Metadata for batch operations and other custom data
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dict for JSON serialization.

        Handles both individual and batch operations with specialized
        formatting for batch operations.
        """
        # Check if this is a batch operation with folder_pairs metadata
        if self.operation_type.endswith("_batch") and "folder_pairs" in self.metadata:
            # Specialized JSON structure for batch operations
            result: dict[str, Any] = {
                "batch_info": {
                    "operation_type": self.operation_type,
                    "timestamp_start": self.timestamp_start,
                    "total_pairs": len(self.metadata["folder_pairs"]),
                },
                "folder_pairs": self.metadata["folder_pairs"],
                "summary": {
                    "total_operations": self.total_operations,
                    "total_errors": self.errors,
                    "total_conflicts": self.conflicts,
                },
            }

            if self.timestamp_end is not None:
                result["batch_info"]["timestamp_end"] = self.timestamp_end
            if self.duration_seconds is not None:
                result["batch_info"]["duration_seconds"] = self.duration_seconds

            # Include aggregated file_operations if present (Opzione B+)
            if self.file_operations:
                result["file_operations"] = self.file_operations

            return result

        # Standard individual operation format
        result = {
            "operation_type": self.operation_type,
            "timestamp_start": self.timestamp_start,
            "source_path": self.source_path,
            "destination_path": self.destination_path,
            "mode": self.mode,
            "comparison_method": self.comparison_method,
            "summary": {
                "total_operations": self.total_operations,
                "source_modified": self.source_modified,
                "destination_modified": self.destination_modified,
                "conflicts": self.conflicts,
                "errors": self.errors,
            },
            "operations": [op.to_dict() for op in self.operations],
        }

        # Add file_operations if present (Opzione B+ grouped format)
        if self.file_operations:
            result["file_operations"] = self.file_operations

        if self.timestamp_end is not None:
            result["timestamp_end"] = self.timestamp_end
        if self.duration_seconds is not None:
            result["duration_seconds"] = self.duration_seconds

        # Add any additional metadata
        if self.metadata:
            result["metadata"] = self.metadata

        return result


# ==============================================================================
# STREAM-BASED ARCHITECTURE MODELS (NEW)
# ==============================================================================


@dataclass
class Summary:
    """
    Aggregated summary statistics across all folder pairs.
    
    Mutable during accumulation, then frozen when operation completes.
    Used in the new stream-based architecture.
    """
    
    total_operations: int = 0
    total_copied: int = 0
    total_deleted: int = 0
    total_updated: int = 0
    total_renamed: int = 0
    total_errors: int = 0
    total_conflicts: int = 0
    duration_seconds: float = 0.0
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "total_operations": self.total_operations,
            "copied": self.total_copied,
            "deleted": self.total_deleted,
            "updated": self.total_updated,
            "renamed": self.total_renamed,
            "errors": self.total_errors,
            "conflicts": self.total_conflicts,
            "duration_seconds": round(self.duration_seconds, 2),
        }


@dataclass
class OperationLog:
    """
    Log risultante dall'elaborazione di N coppie di cartelle (N≥1).
    
    KEY INSIGHT: Non c'è distinzione batch/single - è SEMPRE N coppie.
    - N=1: operazione singola
    - N>1: operazione batch
    
    Questa è l'unica struttura di log, eliminando la dicotomia batch/single.
    Uniform representation per TUTTE le operazioni (sync, bisync, compare).
    """
    
    timestamp_start: datetime
    timestamp_end: datetime
    folder_pairs: list[FolderPairResult]  # SEMPRE lista (anche se N=1)
    file_operations: dict[str, list[FileOperation]]  # Grouped by action
    summary: Summary
    metadata: dict[str, Any]  # Contiene operation_type, mode, etc.
    
    @property
    def duration_seconds(self) -> float:
        """Calculate total duration."""
        return (self.timestamp_end - self.timestamp_start).total_seconds()
    
    @property
    def pairs_count(self) -> int:
        """Number of folder pairs processed."""
        return len(self.folder_pairs)
    
    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.
        
        Single, uniform representation for ALL cases (N≥1).
        No conditional logic based on operation_type or batch/single.
        """
        return {
            "timestamp_start": self.timestamp_start.isoformat(),
            "timestamp_end": self.timestamp_end.isoformat(),
            "duration_seconds": round(self.duration_seconds, 2),
            "folder_pairs": [pair.to_dict() for pair in self.folder_pairs],
            "file_operations": {
                action: [op.to_dict() for op in operations]
                for action, operations in self.file_operations.items()
            },
            "summary": self.summary.to_dict(),
            "metadata": self.metadata,
        }
