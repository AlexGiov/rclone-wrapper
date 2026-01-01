"""
Domain layer - Pure business models and value objects.

This package contains immutable domain models that represent
the core business concepts of the rclone wrapper.

Following Domain-Driven Design principles:
- Value objects are immutable (frozen dataclasses)
- No dependencies on infrastructure
- Pure Python objects with validation logic
"""

from .enums import (
    ConflictLoser,
    ConflictResolve,
    ExitCode,
    FileAction,
    LogLevel,
    OperationStatus,
    ParseStatus,
    ResyncMode,
)
from .models import (
    ErrorInfo,
    FileInfo,
    FileOperation,
    FileState,
    OperationLog,
    ParsedData,
    Summary,
    TransferStats,
    UnifiedOperationLog,
)
from .value_objects import FolderPairResult, OperationTiming, RemotePath

__all__ = [
    # Enums
    "ExitCode",
    "LogLevel",
    "ConflictResolve",
    "ConflictLoser",
    "ResyncMode",
    "FileAction",
    "OperationStatus",
    "ParseStatus",
    # Models
    "FileInfo",
    "FileState",
    "FileOperation",
    "ErrorInfo",
    "TransferStats",
    "ParsedData",
    "UnifiedOperationLog",
    "Summary",
    "OperationLog",
    # Value Objects
    "OperationTiming",
    "RemotePath",
    "FolderPairResult",
]
