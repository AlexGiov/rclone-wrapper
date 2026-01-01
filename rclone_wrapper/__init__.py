"""
rclone_wrapper - Professional Python wrapper for rclone.

A modern, type-safe wrapper for rclone with comprehensive support for
sync, bisync, and compare operations.

Architecture:
- Domain-Driven Design with layered architecture
- Dependency Injection for testability
- Modern Python 3.10+ with PEP 585/604 type hints
- Pydantic 2.0+ for configuration validation
- Comprehensive logging with UnifiedOperationLog

Version 0.4.0 - Complete Refactoring:
- Modern architecture following SOLID principles
- Eliminated ~750 lines of code duplication
- Builder, Factory, Strategy, and Protocol patterns
- Full type coverage with mypy strict compliance
"""

__version__ = "0.4.0"
__author__ = "Alex"

# Config layer
from .config import (
    ArchiveConfig,
    BackupConfig,
    BackupExtendedConfig,
    BisyncConfig,
    CommonConfig,
    CompareConfig,
    ConfigLoader,
    FilterConfig,
    FolderPair,
    SyncConfig,
)

# Core layer
from .core.command import CommandBuilder, CommandExecutor, CommandResult
from .core.filters import FilterBuilder
from .core.remote import RemoteCapabilities

# Domain layer
from .domain import (
    ConflictLoser,
    ConflictResolve,
    ExitCode,
    FileAction,
    FileInfo,
    FileOperation,
    FileState,
    LogLevel,
    OperationTiming,
    ParsedData,
    ParseStatus,
    RemotePath,
    ResyncMode,
    TransferStats,
    UnifiedOperationLog,
)

# Exceptions
from .exceptions import (
    RcloneConfigError,
    RcloneCriticalError,
    RcloneError,
    RcloneLockError,
    RcloneParseError,
    RcloneRetryableError,
)

# Logging layer
from .logging import (
    BatchLogFormatter,
    ParserStrategy,
)

# Operations layer
from .operations import (
    BaseOperationManager,
    BisyncOperationManager,
    CompareOperationManager,
    OperationFactory,
    SyncOperationManager,
)

__all__ = [
    # Config
    "CommonConfig",
    "FilterConfig",
    "FolderPair",
    "SyncConfig",
    "BisyncConfig",
    "CompareConfig",
    "BackupConfig",
    "ArchiveConfig",
    "BackupExtendedConfig",
    "ConfigLoader",
    # Core
    "CommandBuilder",
    "CommandExecutor",
    "CommandResult",
    "FilterBuilder",
    "RemoteCapabilities",
    # Domain
    "ExitCode",
    "LogLevel",
    "ConflictResolve",
    "ConflictLoser",
    "ResyncMode",
    "FileAction",
    "ParseStatus",
    "RemotePath",
    "OperationTiming",
    "FileInfo",
    "FileState",
    "FileOperation",
    "TransferStats",
    "ParsedData",
    "UnifiedOperationLog",
    # Exceptions
    "RcloneError",
    "RcloneRetryableError",
    "RcloneCriticalError",
    "RcloneLockError",
    "RcloneConfigError",
    "RcloneParseError",
    # Logging
    "BatchLogFormatter",
    "ParserStrategy",
    # Operations
    "BaseOperationManager",
    "SyncOperationManager",
    "BisyncOperationManager",
    "CompareOperationManager",
    "OperationFactory",
]
