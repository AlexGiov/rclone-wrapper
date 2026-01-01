"""
Configuration models - Pydantic models for all configurations.

Consolidated from old config.py with modern Python 3.10+ features.
Uses Pydantic 2.0+ with strict validation.
"""

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..constants import (
    DEFAULT_CHECKERS,
    DEFAULT_MAX_LOCK,
    DEFAULT_RETENTION_DAYS,
    DEFAULT_TIMEOUT,
    DEFAULT_TRANSFERS,
)
from ..domain import ConflictLoser, ConflictResolve, LogLevel, ResyncMode

__all__ = [
    "FilterConfig",
    "CommonConfig",
    "FolderPair",
    "SyncConfig",
    "BisyncConfig",
    "CompareConfig",
    "BackupConfig",
    "ArchiveConfig",
    "BackupExtendedConfig",
]


class FilterConfig(BaseModel):
    """
    Filtering options for rclone operations.

    Attributes:
        exclude: Patterns to exclude
        include: Patterns to include
        exclude_dirs: Directory names to exclude
        exclude_if_present: Exclude dir if this file is present
        min_size: Minimum file size (e.g. '100M')
        max_size: Maximum file size (e.g. '1G')
        min_age: Minimum file age (e.g. '7d')
        max_age: Maximum file age (e.g. '30d')
        filter_from: Read filters from file
        ignore_case: Make filter patterns case-insensitive
    """

    exclude: list[str] = Field(default_factory=list)
    include: list[str] = Field(default_factory=list)
    exclude_dirs: list[str] = Field(default_factory=list)
    exclude_if_present: str | None = None
    min_size: str | None = None
    max_size: str | None = None
    min_age: str | None = None
    max_age: str | None = None
    filter_from: Path | None = None
    ignore_case: bool = False

    model_config = ConfigDict(validate_assignment=True)


class CommonConfig(BaseModel):
    """
    Common configuration shared across all operations.

    Attributes:
        remote: Rclone remote name
        rclone_path: Path to rclone executable (defaults to 'rclone' in PATH)
        log_dir: Log directory
        log_level: Logging level
        bwlimit: Bandwidth limit (e.g. '10M')
        transfers: Number of parallel transfers
        timeout: Timeout in seconds for rclone operations
        checkers: Number of parallel checkers
        dry_run: Dry run mode
        extra_flags: Extra flags for rclone
        filters: Filter options
    """

    remote: str = Field(..., min_length=1)
    rclone_path: str = Field(default="rclone")
    log_dir: Path = Field(default=Path("logs"))
    log_level: LogLevel = Field(default=LogLevel.INFO)
    bwlimit: str | None = None
    transfers: int = Field(default=DEFAULT_TRANSFERS, ge=1, le=32)
    timeout: int = Field(default=DEFAULT_TIMEOUT, ge=60)
    checkers: int = Field(default=DEFAULT_CHECKERS, ge=1, le=32)
    dry_run: bool = False
    extra_flags: list[str] = Field(default_factory=list)
    filters: FilterConfig = Field(default_factory=FilterConfig)

    model_config = ConfigDict(validate_assignment=True, use_enum_values=True)

    @field_validator("log_dir")
    @classmethod
    def create_log_dir(cls, v: Path) -> Path:
        """Create log directory if it doesn't exist."""
        v.mkdir(parents=True, exist_ok=True)
        return v

    @field_validator("bwlimit")
    @classmethod
    def validate_bwlimit(cls, v: str | None) -> str | None:
        """Validate bandwidth limit format."""
        if v is None:
            return v
        # Basic validation - rclone will do full validation
        if not any(v.endswith(unit) for unit in ["k", "K", "m", "M", "g", "G"]):
            if not v.isdigit():
                raise ValueError(f"Invalid bwlimit format: {v}")
        return v


class FolderPair(BaseModel):
    """
    Single folder pair configuration with optional overrides.

    Attributes:
        source: Source path (local or remote:path)
        destination: Destination path (relative to dest_base)
        filters: Override filters for this pair
        checksum: Override checksum setting
        size_only: Override size_only setting
        one_way: Override one_way setting (compare only)
        download: Override download setting (compare only)
    """

    source: str = Field(..., min_length=1)
    destination: str = Field(..., min_length=1)

    # Optional per-pair overrides
    filters: FilterConfig | None = None
    checksum: bool | None = None
    size_only: bool | None = None
    one_way: bool | None = None
    download: bool | None = None
    allow_empty: bool = False  # Allow empty directories (skip safety check)

    model_config = ConfigDict(validate_assignment=True)


class SyncConfig(BaseModel):
    """
    Configuration for one-way sync operations.

    Attributes:
        remote: Remote name for validation
        size_only: Compare by size only (ignores modtime)
        modtime_and_size: Compare by size and modtime (rclone default)
        checksum: Compare by checksum/hash (slowest but most accurate)
        filters: Global filters (merged with common)
        folders: List of folder pairs to sync
    """

    remote: str = Field(..., min_length=1)

    # Global defaults for all folder pairs
    size_only: bool = False
    modtime_and_size: bool = True
    checksum: bool = False
    filters: FilterConfig = Field(default_factory=FilterConfig)

    # Folder pairs (can override global settings)
    folders: list[FolderPair] = Field(default_factory=list)

    model_config = ConfigDict(validate_assignment=True)

    @field_validator("folders")
    @classmethod
    def validate_folders_destinations(
        cls, v: list[FolderPair], info
    ) -> list[FolderPair]:
        """Validate that all destination paths are explicit remote paths."""
        remote = info.data.get("remote") if hasattr(info, "data") else None
        for i, folder in enumerate(v):
            if ":" not in folder.destination:
                raise ValueError(
                    f"Folder pair {i}: destination must be explicit remote path "
                    f"(format 'remote:path'), got: {folder.destination}"
                )
            if remote:
                dest_remote = folder.destination.split(":", 1)[0]
                if dest_remote != remote:
                    raise ValueError(
                        f"Folder pair {i}: destination remote '{dest_remote}' "
                        f"does not match configured remote '{remote}'"
                    )
        return v


class BisyncConfig(BaseModel):
    """
    Configuration for bidirectional sync operations.

    Attributes:
        remote: Remote name for validation
        state_dir: Directory for bisync state files
        backup_dir: Directory for bisync backups
        filters: Global filters (merged with common)
        checksum: Use checksum for comparison
        folders: List of folder pairs for bidirectional sync
        resilient: Enable resilient mode
        recover: Enable recover mode
        force: Force sync even when many files have changed
        max_lock: Maximum lock duration
        conflict_resolve: Conflict resolution strategy
        conflict_loser: Which side loses in conflict
        conflict_suffix: Suffix for conflict files
        resync_mode: Resync mode
        compare: Comparison methods
        create_empty_src_dirs: Create empty source directories
    """

    remote: str = Field(..., min_length=1)
    state_dir: Path = Field(default=Path("bisync_state"))
    backup_dir: Path = Field(default=Path("bisync_backups"))

    # Global defaults for all folder pairs
    filters: FilterConfig = Field(default_factory=FilterConfig)
    checksum: bool = False

    # Folder pairs
    folders: list[FolderPair] = Field(default_factory=list)

    # Bisync options
    resilient: bool = True
    recover: bool = True
    force: bool = False
    max_lock: str = Field(default=DEFAULT_MAX_LOCK)
    conflict_resolve: ConflictResolve = Field(default=ConflictResolve.NONE)
    conflict_loser: ConflictLoser = Field(default=ConflictLoser.NUM)
    conflict_suffix: str = "conflict"
    resync_mode: ResyncMode = Field(default=ResyncMode.NONE)

    # Comparison options
    compare: list[str] = Field(default_factory=lambda: ["size", "modtime"])
    create_empty_src_dirs: bool = True

    model_config = ConfigDict(validate_assignment=True, use_enum_values=True)

    @field_validator("state_dir", "backup_dir")
    @classmethod
    def create_directories(cls, v: Path) -> Path:
        """Create directories if they don't exist."""
        v.mkdir(parents=True, exist_ok=True)
        return v

    @field_validator("max_lock")
    @classmethod
    def validate_max_lock(cls, v: str) -> str:
        """Validate max_lock format."""
        if v[-1] not in ["s", "m", "h"]:
            raise ValueError(f"max_lock must end with s, m, or h: {v}")
        try:
            int(v[:-1])
        except ValueError:
            raise ValueError(f"Invalid max_lock format: {v}")
        return v

    @field_validator("folders")
    @classmethod
    def validate_folders_destinations(
        cls, v: list[FolderPair], info
    ) -> list[FolderPair]:
        """Validate that all destination paths are explicit remote paths."""
        remote = info.data.get("remote") if hasattr(info, "data") else None
        for i, folder in enumerate(v):
            if ":" not in folder.destination:
                raise ValueError(
                    f"Folder pair {i}: destination must be explicit remote path "
                    f"(format 'remote:path'), got: {folder.destination}"
                )
            if remote:
                dest_remote = folder.destination.split(":", 1)[0]
                if dest_remote != remote:
                    raise ValueError(
                        f"Folder pair {i}: destination remote '{dest_remote}' "
                        f"does not match configured remote '{remote}'"
                    )
        return v


class CompareConfig(BaseModel):
    """
    Configuration for compare operations.

    Attributes:
        remote: Remote name for validation
        one_way: Only check source -> dest (ignore extra files in dest)
        download: Download files for comparison (slower but more thorough)
        checksum: Compare by checksum/hash
        size_only: Compare by size only
        filters: Global filters (merged with common)
        folders: List of folder pairs to compare
    """

    remote: str = Field(..., min_length=1)

    # Global defaults for all folder pairs
    one_way: bool = True
    download: bool = False
    checksum: bool = False
    size_only: bool = False
    filters: FilterConfig = Field(default_factory=FilterConfig)

    # Folder pairs
    folders: list[FolderPair] = Field(default_factory=list)

    model_config = ConfigDict(validate_assignment=True)

    @field_validator("folders")
    @classmethod
    def validate_folders_destinations(
        cls, v: list[FolderPair], info
    ) -> list[FolderPair]:
        """Validate that all destination paths are explicit remote paths."""
        remote = info.data.get("remote") if hasattr(info, "data") else None
        for i, folder in enumerate(v):
            if ":" not in folder.destination:
                raise ValueError(
                    f"Folder pair {i}: destination must be explicit remote path "
                    f"(format 'remote:path'), got: {folder.destination}"
                )
            if remote:
                dest_remote = folder.destination.split(":", 1)[0]
                if dest_remote != remote:
                    raise ValueError(
                        f"Folder pair {i}: destination remote '{dest_remote}' "
                        f"does not match configured remote '{remote}'"
                    )
        return v


class BackupConfig(BaseModel):
    """
    Configuration for backup operations.

    Attributes:
        dest_base: Base destination path
        zip_prefix: Prefix for backup ZIP files
        retention_days: Number of days to retain backups
        folders: List of folders to backup
    """

    dest_base: str = Field(..., min_length=1)
    zip_prefix: str = Field(default="backup", min_length=1)
    retention_days: int = Field(default=DEFAULT_RETENTION_DAYS, ge=1, le=365)
    folders: list[str] = Field(default_factory=list)

    model_config = ConfigDict(validate_assignment=True)


class ArchiveConfig(BaseModel):
    """
    Configuration for a single backup archive.

    Attributes:
        source: List of source folders to include in archive
        destination: Destination folder name
        filters: Archive-specific filters
        retention_days: Number of days to retain this archive
        merge_zip: Merge all folders into single zip
        compression_level: ZIP compression level
        enabled: Enable/disable this archive
        description: Optional description
    """

    source: list[str] = Field(..., min_length=1)
    destination: str = Field(..., min_length=1)
    filters: FilterConfig | None = None
    retention_days: int = Field(default=DEFAULT_RETENTION_DAYS, ge=0, le=365)
    merge_zip: bool = True
    compression_level: int = Field(default=6, ge=0, le=9)
    enabled: bool = True
    description: str | None = None

    model_config = ConfigDict(validate_assignment=True)

    @field_validator("source")
    @classmethod
    def validate_source_folders(cls, v: list[str]) -> list[str]:
        """Ensure at least one source folder is specified."""
        if not v:
            raise ValueError("At least one source folder must be specified")
        return v


class BackupExtendedConfig(BaseModel):
    """
    Configuration for extended backup operations with multiple archives.

    Attributes:
        dest_base: Base destination path
        filters: Global filters
        max_retention_days: Maximum retention allowed
        archives: Archive configurations
    """

    dest_base: str = Field(..., min_length=1)
    filters: FilterConfig = Field(default_factory=FilterConfig)
    max_retention_days: int = Field(default=30, ge=1, le=365)
    archives: list[ArchiveConfig] = Field(..., min_length=1)

    model_config = ConfigDict(validate_assignment=True)

    @field_validator("archives")
    @classmethod
    def validate_archives(cls, v: list[ArchiveConfig]) -> list[ArchiveConfig]:
        """Ensure at least one archive is defined."""
        if not v:
            raise ValueError("At least one archive must be defined")
        return v
