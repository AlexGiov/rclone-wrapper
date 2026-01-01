"""
Compare operation manager - Compare operations between paths.

Implements compare/check operations using the new architecture with
dependency injection and proper separation of concerns.
"""

import logging
from datetime import datetime
from pathlib import Path

from ..config import CommonConfig, CompareConfig, FolderPair
from ..core.command import CommandBuilder, CommandExecutor
from ..logging.output_analyzer import RcloneOutputAnalyzer
from .base import BaseOperationManager

__all__ = ["CompareOperationManager"]

logger = logging.getLogger(__name__)


class CompareOperationManager(BaseOperationManager):
    """Manager for compare/check operations.
    
    ARCHITECTURE: Uses RcloneOutputAnalyzer for all parsing and logging.
    
    Key features:
    - All parsing delegated to RcloneOutputAnalyzer (SRP compliant)
    - Batch operations with aggregated difference reporting
    - Direct command building without factory pattern overhead
    
    Workflow:
    1. Build command with CommandBuilder (rclone check --combined)
    2. Execute within RcloneOutputAnalyzer context
    3. Analyzer handles all parsing, counting, and report generation
    
    Example:
        >>> executor = CommandExecutor()
        >>> manager = CompareOperationManager(
        ...     common_config=common,
        ...     compare_config=compare,
        ...     executor=executor,
        ... )
        >>> manager.compare_all()
    """

    def __init__(
        self,
        common_config: CommonConfig,
        compare_config: CompareConfig,
        executor: CommandExecutor,
        rclone_path: Path | None = None,
        log_dir: Path | None = None,
    ) -> None:
        """Initialize compare operation manager.
        
        Args:
            common_config: Common configuration
            compare_config: Compare-specific configuration
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
        self.compare_config = compare_config

    def _build_command(
        self,
        builder: CommandBuilder,
        source: str,
        destination: str | None,
        **kwargs,
    ) -> CommandBuilder:
        """
        Build compare-specific command.
        
        Args:
            builder: Command builder
            source: Source path
            destination: Destination path
            **kwargs: Additional parameters (checksum, size_only, etc.)
            
        Returns:
            Builder with compare settings
        """
        # Check subcommand
        builder.subcommand("check")
        builder.arguments(source, destination)
        
        # Comparison method
        checksum = kwargs.get("checksum", self.compare_config.checksum)
        size_only = kwargs.get("size_only", self.compare_config.size_only)
        download = kwargs.get("download", self.compare_config.download)
        
        if checksum:
            builder.arguments("--checksum")
        elif size_only:
            builder.arguments("--size-only")
        # else: default modtime + size
        
        # Download option
        if download:
            builder.arguments("--download")
        
        # One-way check
        one_way = kwargs.get("one_way", self.compare_config.one_way)
        if one_way:
            builder.arguments("--one-way")
        
        # Combined output (show missing, differ, and extra)
        builder.arguments("--combined", "-")
        
        # Enable JSON logging for robust parsing
        builder.json_log()
        
        return builder

    def compare_all(self) -> None:
        """
        Compare all configured folder pairs.
        
        Uses RcloneOutputAnalyzer to execute commands and generate aggregated report.
        All parsing and logging is delegated to the analyzer (SRP compliant).
        """
        if not self.compare_config.folders:
            logger.warning("No folder pairs configured for compare")
            return
        
        logger.info(f"Starting batch compare: {len(self.compare_config.folders)} folder pairs")
        
        # RcloneOutputAnalyzer handles ALL logging and parsing
        with RcloneOutputAnalyzer(self.log_dir, session_name="compare_batch") as analyzer:
            for folder_pair in self.compare_config.folders:
                start_time = datetime.now()
                try:
                    logger.info(f"Comparing: {folder_pair.source} <-> {folder_pair.destination}")
                    
                    # Build command
                    builder = CommandBuilder(self.rclone_path)
                    filters = self._merge_filters(
                        self.compare_config.filters,
                        folder_pair.filters,
                    )
                    builder = self._apply_common_settings(builder, filters)
                    
                    # Get comparison method overrides
                    checksum = folder_pair.checksum if folder_pair.checksum is not None else self.compare_config.checksum
                    size_only = folder_pair.size_only if folder_pair.size_only is not None else self.compare_config.size_only
                    one_way = folder_pair.one_way if folder_pair.one_way is not None else self.compare_config.one_way
                    download = folder_pair.download if folder_pair.download is not None else self.compare_config.download
                    
                    builder = self._build_command(
                        builder,
                        source=folder_pair.source,
                        destination=folder_pair.destination,
                        checksum=checksum,
                        size_only=size_only,
                        one_way=one_way,
                        download=download,
                    )
                    
                    cmd = builder.build()
                    
                    # Execute and aggregate output
                    result = self.executor.execute(cmd)
                    analyzer.add_output(
                        result.stderr,
                        command_info={
                            "command": "compare",
                            "source": folder_pair.source,
                            "destination": folder_pair.destination,
                            "timestamp": start_time.isoformat(),
                            "returncode": result.returncode,
                        }
                    )
                    
                    # Simple success/error logging
                    if result.returncode == 0:
                        logger.info(f"✓ Compare completed: {folder_pair.source} <-> {folder_pair.destination}")
                    else:
                        logger.error(f"✗ Compare failed: {folder_pair.source} <-> {folder_pair.destination}")
                        
                except Exception as e:
                    logger.error(f"Error comparing {folder_pair.source}: {e}")
                    
                    # Add error to analyzer
                    analyzer.add_output(
                        f'{{"level":"error","msg":"Compare failed: {str(e)}","source":"compare_all"}}',
                        command_info={
                            "command": "compare",
                            "source": folder_pair.source,
                            "destination": folder_pair.destination,
                            "error": str(e),
                            "timestamp": start_time.isoformat(),
                        }
                    )
        
        # Report generated automatically by analyzer on context exit
        logger.info("Batch compare completed - analysis report generated")
