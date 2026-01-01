"""
Operation factory - Creates operation managers with dependency injection.

Provides a clean API for creating operation managers with all
required dependencies properly injected.

Following Factory Method Pattern and Builder Pattern.
"""

import logging
from pathlib import Path

from ..config import BisyncConfig, CommonConfig, CompareConfig, SyncConfig
from ..core.command import CommandExecutor
from .bisync import BisyncOperationManager
from .compare import CompareOperationManager
from .sync import SyncOperationManager

__all__ = ["OperationFactory"]

logger = logging.getLogger(__name__)


class OperationFactory:
    """
    Factory for creating operation managers.
    
    Handles dependency injection and proper initialization
    of all operation manager types.
    
    Example:
        >>> factory = OperationFactory()
        >>> sync_manager = factory.create_sync_manager(common, sync)
        >>> bisync_manager = factory.create_bisync_manager(common, bisync)
        >>> compare_manager = factory.create_compare_manager(common, compare)
    """

    def __init__(
        self,
        rclone_path: Path | None = None,
        executor: CommandExecutor | None = None,
    ) -> None:
        """Initialize operation factory.
        
        Args:
            rclone_path: Optional path to rclone executable
            executor: Optional command executor (creates default if None)
        """
        self.rclone_path = rclone_path
        self._executor = executor

    @property
    def executor(self) -> CommandExecutor:
        """Get or create command executor."""
        if self._executor is None:
            self._executor = CommandExecutor()
        return self._executor

    def create_sync_manager(
        self,
        common_config: CommonConfig,
        sync_config: SyncConfig,
    ) -> SyncOperationManager:
        """Create sync operation manager.
        
        Args:
            common_config: Common configuration
            sync_config: Sync configuration
            
        Returns:
            SyncOperationManager instance
        """
        return SyncOperationManager(
            common_config=common_config,
            sync_config=sync_config,
            executor=self.executor,
            rclone_path=self.rclone_path,
        )

    def create_bisync_manager(
        self,
        common_config: CommonConfig,
        bisync_config: BisyncConfig,
    ) -> BisyncOperationManager:
        """Create bisync operation manager.
        
        Args:
            common_config: Common configuration
            bisync_config: Bisync configuration
            
        Returns:
            BisyncOperationManager instance
        """
        return BisyncOperationManager(
            common_config=common_config,
            bisync_config=bisync_config,
            executor=self.executor,
            rclone_path=self.rclone_path,
        )

    def create_compare_manager(
        self,
        common_config: CommonConfig,
        compare_config: CompareConfig,
    ) -> CompareOperationManager:
        """Create compare operation manager.
        
        Args:
            common_config: Common configuration
            compare_config: Compare configuration
            
        Returns:
            CompareOperationManager instance
        """
        return CompareOperationManager(
            common_config=common_config,
            compare_config=compare_config,
            executor=self.executor,
            rclone_path=self.rclone_path,
        )
