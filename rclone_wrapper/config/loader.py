"""
Configuration loader - Factory for loading configurations.

Provides a clean API for loading all configuration types from JSON files.
Uses dependency injection and proper error handling.
"""

import json
import logging
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from ..exceptions import RcloneConfigError
from .models import (
    BackupConfig,
    BackupExtendedConfig,
    BisyncConfig,
    CommonConfig,
    CompareConfig,
    SyncConfig,
)

__all__ = ["ConfigLoader", "DEFAULT_CONFIG_DIR"]

logger = logging.getLogger(__name__)

# Type variable for generic config loading
T = TypeVar("T", bound=BaseModel)

# Default config directory
DEFAULT_CONFIG_DIR = Path("config")


class ConfigLoader:
    """
    Factory for loading configurations from JSON files.

    Provides a clean, testable API for configuration loading with
    proper error handling and validation.

    Example:
        >>> loader = ConfigLoader()
        >>> common, sync = loader.load_sync()
        >>> # OR
        >>> loader = ConfigLoader(config_dir=Path("custom/config"))
        >>> common, bisync = loader.load_bisync()
    """

    def __init__(self, config_dir: Path = DEFAULT_CONFIG_DIR) -> None:
        """
        Initialize config loader.

        Args:
            config_dir: Directory containing config files
        """
        self.config_dir = config_dir

        if not self.config_dir.exists():
            logger.warning(f"Config directory does not exist: {self.config_dir}")

    def load_common(self) -> CommonConfig:
        """
        Load common configuration.

        Returns:
            CommonConfig instance

        Raises:
            RcloneConfigError: If config file not found or invalid
        """
        return self._load_config("common.json", CommonConfig)

    def load_sync(self) -> tuple[CommonConfig, SyncConfig]:
        """
        Load sync configuration (common + sync).

        Returns:
            Tuple of (CommonConfig, SyncConfig)

        Raises:
            RcloneConfigError: If config files not found or invalid
        """
        common = self.load_common()
        sync = self._load_config("sync.json", SyncConfig)
        return common, sync

    def load_bisync(self) -> tuple[CommonConfig, BisyncConfig]:
        """
        Load bisync configuration (common + bisync).

        Returns:
            Tuple of (CommonConfig, BisyncConfig)

        Raises:
            RcloneConfigError: If config files not found or invalid
        """
        common = self.load_common()
        bisync = self._load_config("bisync.json", BisyncConfig)
        return common, bisync

    def load_compare(self) -> tuple[CommonConfig, CompareConfig]:
        """
        Load compare configuration (common + compare).

        Returns:
            Tuple of (CommonConfig, CompareConfig)

        Raises:
            RcloneConfigError: If config files not found or invalid
        """
        common = self.load_common()
        compare = self._load_config("compare.json", CompareConfig)
        return common, compare

    def load_backup(self) -> tuple[CommonConfig, BackupConfig]:
        """
        Load backup configuration (common + backup).

        Returns:
            Tuple of (CommonConfig, BackupConfig)

        Raises:
            RcloneConfigError: If config files not found or invalid
        """
        common = self.load_common()
        backup = self._load_config("backup.json", BackupConfig)
        return common, backup

    def load_backup_extended(self) -> tuple[CommonConfig, BackupExtendedConfig]:
        """
        Load extended backup configuration (common + backup_extended).

        Returns:
            Tuple of (CommonConfig, BackupExtendedConfig)

        Raises:
            RcloneConfigError: If config files not found or invalid
        """
        common = self.load_common()
        backup_ext = self._load_config("backup_extended.json", BackupExtendedConfig)
        return common, backup_ext

    def _load_config(self, filename: str, config_class: type[T]) -> T:
        """
        Load a configuration file.

        Args:
            filename: Name of config file
            config_class: Pydantic model class

        Returns:
            Instance of config_class

        Raises:
            RcloneConfigError: If file not found or invalid
        """
        config_file = self.config_dir / filename

        if not config_file.exists():
            raise RcloneConfigError(f"Config file not found: {config_file}")

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Validate and create config instance
            config = config_class(**data)
            logger.info(f"Loaded config from {config_file}")
            return config

        except json.JSONDecodeError as e:
            raise RcloneConfigError(f"Invalid JSON in {filename}: {e}") from e
        except ValidationError as e:
            raise RcloneConfigError(f"Validation error in {filename}: {e}") from e
        except Exception as e:
            raise RcloneConfigError(f"Error loading {filename}: {e}") from e

    def config_exists(self, filename: str) -> bool:
        """
        Check if a config file exists.

        Args:
            filename: Name of config file

        Returns:
            True if file exists
        """
        return (self.config_dir / filename).exists()

    def list_configs(self) -> list[str]:
        """
        List all JSON config files in config directory.

        Returns:
            List of config filenames
        """
        if not self.config_dir.exists():
            return []

        return [f.name for f in self.config_dir.glob("*.json") if f.is_file()]
