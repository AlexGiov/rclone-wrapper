"""
Base operation manager - ABC for all operation managers.

Defines the common interface and shared functionality for all
operation types (sync, bisync, compare).

ARCHITECTURE:
- All operations use RcloneOutputAnalyzer for parsing and logging (SRP compliant)
- Direct command building without factory pattern overhead

Following Template Method Pattern and Strategy Pattern.
"""

from abc import ABC, abstractmethod
from pathlib import Path

from ..config import CommonConfig, FilterConfig
from ..core.command import CommandBuilder, CommandExecutor
from ..core.filters import FilterBuilder

__all__ = ["BaseOperationManager"]


class BaseOperationManager(ABC):
    """
    Abstract base class for operation managers.
    
    Provides common functionality for all operation types while
    requiring subclasses to implement operation-specific logic.
    
    Following Template Method Pattern - defines the skeleton of
    the algorithm while letting subclasses override specific steps.
    
    Example:
        >>> class CustomOperation(BaseOperationManager):
        ...     def _build_command(self, ...):
        ...         # Custom command building logic
        ...         pass
    """

    def __init__(
        self,
        common_config: CommonConfig,
        executor: CommandExecutor,
        rclone_path: Path | None = None,
        log_dir: Path | None = None,
    ) -> None:
        """Initialize base operation manager.
        
        Args:
            common_config: Common configuration
            executor: Command executor
            rclone_path: Optional path to rclone executable
            log_dir: Directory for log files
        """
        self.common_config = common_config
        self.executor = executor
        self.rclone_path = rclone_path or Path(common_config.rclone_path)
        self.log_dir = log_dir or Path("logs")

    def _apply_common_settings(
        self,
        builder: CommandBuilder,
        filters: FilterConfig | None = None,
    ) -> CommandBuilder:
        """
        Apply common settings to command builder.
        
        Args:
            builder: Command builder
            filters: Optional filters to apply
            
        Returns:
            Builder with common settings applied
        """
        # Log level
        builder.log_level(self.common_config.log_level)
        
        # Transfers and checkers
        builder.transfers(self.common_config.transfers)
        builder.checkers(self.common_config.checkers)
        
        # Bandwidth limit
        if self.common_config.bwlimit:
            builder.arguments("--bwlimit", self.common_config.bwlimit)
        
        # Dry run
        if self.common_config.dry_run:
            builder.dry_run()
        
        # Filters
        if filters:
            filter_builder = FilterBuilder(filters)
            filter_args = filter_builder.build_args()
            for arg in filter_args:
                if "=" in arg:
                    key, value = arg.split("=", 1)
                    builder.arguments(key, value)
                else:
                    builder.arguments(arg)
        
        # Extra flags
        for flag in self.common_config.extra_flags:
            builder.arguments(flag)
        
        return builder

    def _merge_filters(
        self,
        global_filters: FilterConfig,
        local_filters: FilterConfig | None,
    ) -> FilterConfig:
        """
        Merge global and local filters.
        
        Args:
            global_filters: Global filters
            local_filters: Local filters (override global)
            
        Returns:
            Merged filters
        """
        if not local_filters:
            return global_filters
        
        return FilterBuilder.merge_filters(global_filters, local_filters)

    @abstractmethod
    def _build_command(
        self,
        builder: CommandBuilder,
        source: str,
        destination: str | None,
        **kwargs,
    ) -> CommandBuilder:
        """
        Build operation-specific command.
        
        Subclasses must implement this to add operation-specific
        arguments and options.
        
        Args:
            builder: Command builder
            source: Source path
            destination: Destination path (None for single-path ops)
            **kwargs: Additional operation-specific parameters
            
        Returns:
            Builder with operation-specific settings
        """
        ...
