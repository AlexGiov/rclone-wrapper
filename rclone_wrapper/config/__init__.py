"""
Configuration layer - Configuration models and loading.

This package provides Pydantic-based configuration models
and utilities for loading and validating configuration files.
"""

from .loader import DEFAULT_CONFIG_DIR, ConfigLoader
from .models import (
    ArchiveConfig,
    BackupConfig,
    BackupExtendedConfig,
    BisyncConfig,
    CommonConfig,
    CompareConfig,
    FilterConfig,
    FolderPair,
    SyncConfig,
)

__all__ = [
    # Models
    "CommonConfig",
    "FilterConfig",
    "FolderPair",
    "SyncConfig",
    "BisyncConfig",
    "CompareConfig",
    "BackupConfig",
    "ArchiveConfig",
    "BackupExtendedConfig",
    # Loader
    "ConfigLoader",
    "DEFAULT_CONFIG_DIR",
]
