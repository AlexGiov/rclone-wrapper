"""
Sync operation manager - One-way sync operations.

Implements sync operations using the new architecture with
dependency injection and proper separation of concerns.
"""

import logging
from datetime import datetime
from pathlib import Path

from ..config import CommonConfig, FolderPair, SyncConfig
from ..core.command import CommandBuilder, CommandExecutor
from ..logging.output_analyzer import RcloneOutputAnalyzer
from .base import BaseOperationManager

from ..exceptions import RcloneError

__all__ = ["SyncOperationManager"]

logger = logging.getLogger(__name__)


class SyncOperationManager(BaseOperationManager):
    """Manager for one-way sync operations.
    
    ARCHITECTURE: Uses RcloneOutputAnalyzer for all parsing and logging.
    
    Key features:
    - All parsing delegated to RcloneOutputAnalyzer (SRP compliant)
    - Batch operations with aggregated reporting
    - Direct command building without factory pattern overhead
    
    Workflow:
    1. Build command with CommandBuilder + --use-json-log
    2. Execute within RcloneOutputAnalyzer context
    3. Analyzer handles all parsing, counting, and report generation
    
    Example:
        >>> executor = CommandExecutor()
        >>> manager = SyncOperationManager(
        ...     common_config=common,
        ...     sync_config=sync,
        ...     executor=executor,
        ... )
        >>> manager.sync_all()
    """

    def __init__(
        self,
        common_config: CommonConfig,
        sync_config: SyncConfig,
        executor: CommandExecutor,
        rclone_path: Path | None = None,
        log_dir: Path | None = None,
    ) -> None:
        """Initialize sync operation manager.
        
        Args:
            common_config: Common configuration
            sync_config: Sync-specific configuration
            executor: Command executor
            rclone_path: Optional path to rclone executable
            log_dir: Directory for log files (defaults to common_config.log_dir)
        """
        super().__init__(
            common_config=common_config,
            executor=executor,
            rclone_path=rclone_path,
            log_dir=log_dir or common_config.log_dir,
        )
        self.sync_config = sync_config

    def _build_command(
        self,
        builder: CommandBuilder,
        source: str,
        destination: str | None,
        **kwargs,
    ) -> CommandBuilder:
        """
        Build sync-specific command.
        
        Args:
            builder: Command builder
            source: Source path
            destination: Destination path
            **kwargs: Additional parameters (checksum, size_only, etc.)
            
        Returns:
            Builder with sync settings
        """
        # Sync subcommand
        builder.subcommand("sync")
        builder.arguments(source, destination)
        
        # Comparison method
        checksum = kwargs.get("checksum", self.sync_config.checksum)
        size_only = kwargs.get("size_only", self.sync_config.size_only)
        
        if checksum:
            builder.arguments("--checksum")
        elif size_only:
            builder.arguments("--size-only")
        # else: default modtime + size
        
        # Enable JSON logging for robust parsing
        builder.json_log()
        
        return builder

    def sync_all(self) -> None:
        """
        Sync all configured folder pairs.
        
        Uses RcloneOutputAnalyzer to execute commands and generate aggregated report.
        All parsing and logging is delegated to the analyzer (SRP compliant).
        """
        if not self.sync_config.folders:
            logger.warning("No folder pairs configured for sync")
            return
        
        logger.info(f"Starting batch sync: {len(self.sync_config.folders)} folder pairs")

        failed_pairs: list[str] = []

        # RcloneOutputAnalyzer handles ALL logging and parsing
        with RcloneOutputAnalyzer(self.log_dir, session_name="sync_batch") as analyzer:
            for folder_pair in self.sync_config.folders:
                start_time = datetime.now()
                try:
                    logger.info(f"Syncing: {folder_pair.source} -> {folder_pair.destination}")
                    
                    # Build command
                    builder = CommandBuilder(self.rclone_path)
                    builder = self._apply_common_settings(builder, self._merge_filters(
                        self.sync_config.filters, folder_pair.filters
                    ))
                    builder = self._build_command(
                        builder,
                        source=folder_pair.source,
                        destination=folder_pair.destination,
                        checksum=folder_pair.checksum if folder_pair.checksum is not None else self.sync_config.checksum,
                        size_only=folder_pair.size_only if folder_pair.size_only is not None else self.sync_config.size_only,
                    )
                    cmd = builder.build()
                    
                    # Execute and aggregate output
                    result = self.executor.execute(cmd)
                    analyzer.add_output(
                        result.stderr,
                        command_info={
                            "command": "sync",
                            "source": folder_pair.source,
                            "destination": folder_pair.destination,
                            "timestamp": start_time.isoformat(),
                            "returncode": result.returncode,
                        }
                    )
                    
                    # Simple success/error logging
                    if result.returncode == 0:
                        logger.info(f"✓ Sync completed: {folder_pair.source} -> {folder_pair.destination}")
                    else:
                        logger.error(f"✗ Sync failed: {folder_pair.source} -> {folder_pair.destination}")
                        
                except Exception as e:
                    failed_pairs.append(folder_pair.source)
                    logger.error(f"Error syncing {folder_pair.source}: {e}")
                    
                    # Add error to analyzer
                    analyzer.add_output(
                        f'{{"level":"error","msg":"Sync failed: {str(e)}","source":"sync_all"}}',
                        command_info={
                            "command": "sync",
                            "source": folder_pair.source,
                            "destination": folder_pair.destination,
                            "error": str(e),
                            "timestamp": start_time.isoformat(),
                        }
                    )
        
        # Report generated automatically by analyzer on context exit
        logger.info("Batch sync completed - analysis report generated")

        if failed_pairs:
            total = len(self.sync_config.folders)
            raise RcloneError(
                f"Batch sync failed: {len(failed_pairs)}/{total} pairs failed: "
                + ", ".join(failed_pairs)
            )
