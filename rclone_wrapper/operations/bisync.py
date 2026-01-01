"""
Bisync operation manager - Bidirectional sync operations.

Implements bisync operations using RcloneOutputAnalyzer architecture.

ARCHITECTURE:
- RcloneOutputAnalyzer for all parsing and logging (SRP compliant)
- Batch operations with aggregated reporting
- Direct command building without factory pattern overhead

WORKFLOW:
1. Build bisync command with --use-json-log
2. Execute within RcloneOutputAnalyzer context
3. Analyzer handles all parsing, counting, and report generation

KEY IMPROVEMENTS:
- All parsing delegated to RcloneOutputAnalyzer
- Zero code duplication
- Clean separation of concerns
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Iterator

from ..config import BisyncConfig, CommonConfig, FolderPair
from ..core.command import CommandBuilder, CommandExecutor
from ..logging.output_analyzer import RcloneOutputAnalyzer
from .base import BaseOperationManager

__all__ = ["BisyncOperationManager"]

logger = logging.getLogger(__name__)


class BisyncOperationManager(BaseOperationManager):
    """
    Manager for bidirectional sync (bisync) operations.

    Handles bisync operations with conflict resolution,
    state management, and backup options.

    Example:
        >>> executor = CommandExecutor()
        >>> manager = BisyncOperationManager(
        ...     common_config=common,
        ...     bisync_config=bisync,
        ...     executor=executor,
        ... )
        >>> manager.bisync_all_stream()
    """

    def __init__(
        self,
        common_config: CommonConfig,
        bisync_config: BisyncConfig,
        executor: CommandExecutor,
        rclone_path: Path | None = None,
        log_dir: Path | None = None,
    ) -> None:
        """Initialize bisync operation manager.

        Args:
            common_config: Common configuration
            bisync_config: Bisync-specific configuration
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
        self.bisync_config = bisync_config

    def _build_command(
        self,
        builder: CommandBuilder,
        source: str,
        destination: str | None,
        **kwargs,
    ) -> CommandBuilder:
        """
        Build bisync-specific command.

        Args:
            builder: Command builder
            source: Path1 for bisync
            destination: Path2 for bisync
            **kwargs: Additional parameters (resync, force, etc.)

        Returns:
            Builder with bisync settings
        """
        # Bisync subcommand
        builder.subcommand("bisync")
        builder.arguments(source, destination)

        # Checksum
        if self.bisync_config.checksum or kwargs.get("checksum"):
            builder.arguments("--checksum")

        # Resilient mode
        if self.bisync_config.resilient:
            builder.arguments("--resilient")

        # Recover mode
        if self.bisync_config.recover:
            builder.arguments("--recover")

        # Force
        if self.bisync_config.force or kwargs.get("force"):
            builder.arguments("--force")

        # Max lock
        builder.arguments("--max-lock", self.bisync_config.max_lock)

        # Conflict resolution
        if self.bisync_config.conflict_resolve != "none":
            builder.arguments("--conflict-resolve", self.bisync_config.conflict_resolve)

        if self.bisync_config.conflict_loser != "num":
            builder.arguments("--conflict-loser", self.bisync_config.conflict_loser)

        builder.arguments("--conflict-suffix", self.bisync_config.conflict_suffix)

        # Resync mode
        # Support both boolean resync and specific resync_mode
        if kwargs.get("resync") is True:
            # Simple --resync flag (path1 mode)
            builder.arguments("--resync")
        elif self.bisync_config.resync_mode != "none":
            # Configured resync mode
            resync_mode = self.bisync_config.resync_mode
            if resync_mode == "path1":
                builder.arguments("--resync")
            elif resync_mode == "path2":
                builder.arguments("--resync-mode", "path2")

        # Compare methods
        for method in self.bisync_config.compare:
            builder.arguments("--compare", method)

        # Create empty source dirs
        if self.bisync_config.create_empty_src_dirs:
            builder.arguments("--create-empty-src-dirs")

        # Backup directories
        # backup-dir1 must be on same remote as path1 (source)
        # backup-dir2 must be on same remote as path2 (destination)

        # Path1 backup (local)
        builder.arguments("--backup-dir1", str(self.bisync_config.backup_dir / "path1"))

        # Path2 backup (must be on destination remote if destination is remote)
        if destination and ":" in destination:
            # Remote destination - extract remote name and build remote backup path
            remote_name = destination.split(":", 1)[0]
            backup_dir2 = f"{remote_name}:{self.bisync_config.backup_dir.name}/path2"
        else:
            # Local destination - use local backup path
            backup_dir2 = str(self.bisync_config.backup_dir / "path2")

        builder.arguments("--backup-dir2", backup_dir2)

        # State directory (using workdir)
        state_dir = self.bisync_config.state_dir
        builder.arguments("--workdir", str(state_dir))

        # Enable JSON logging for robust parsing
        builder.json_log()

        return builder

    def bisync_all_stream(
        self,
        resync: bool = False,
    ) -> None:
        """Bisync all configured folder pairs.
        
        Uses RcloneOutputAnalyzer for all parsing and logging.
        
        Args:
            resync: Whether to resync all pairs
        """
        if not self.bisync_config.folders:
            logger.warning("No folder pairs configured for bisync")
            return

        logger.info(f"🌊 Stream-based bisync: {len(self.bisync_config.folders)} folder pairs")
        
        # RcloneOutputAnalyzer handles ALL logging and parsing
        with RcloneOutputAnalyzer(self.log_dir, session_name="bisync_batch") as analyzer:
            # Process each pair
            for i, folder_pair in enumerate(self.bisync_config.folders, 1):
                logger.info(f"\n[{i}/{len(self.bisync_config.folders)}] Processing {folder_pair.source} <-> {folder_pair.destination}")
                
                start_time = datetime.now()
                try:
                    # Build command
                    builder = CommandBuilder(self.rclone_path)
                    builder = self._apply_common_settings(builder, self._merge_filters(
                        self.bisync_config.filters, folder_pair.filters
                    ))
                    builder = self._build_command(
                        builder,
                        source=folder_pair.source,
                        destination=folder_pair.destination,
                        resync=resync,
                        force=False,
                        checksum=folder_pair.checksum if folder_pair.checksum is not None else self.bisync_config.checksum,
                    )
                    cmd = builder.build()
                    
                    # Execute and aggregate output
                    result = self.executor.execute(cmd)
                    complete_output = result.stdout + "\n" + result.stderr
                    analyzer.add_output(
                        complete_output,
                        command_info={
                            "command": "bisync",
                            "source": folder_pair.source,
                            "destination": folder_pair.destination,
                            "resync": resync,
                            "timestamp": start_time.isoformat(),
                            "returncode": result.returncode,
                        }
                    )
                    
                    # Simple success/error logging
                    if result.returncode == 0:
                        logger.info(f"✅ Bisync completed: {folder_pair.source} <-> {folder_pair.destination}")
                    else:
                        logger.error(f"✗ Bisync failed: {folder_pair.source} <-> {folder_pair.destination}")
                        
                except Exception as e:
                    logger.error(f"❌ Error in bisync {folder_pair.source}: {e}")
                    
                    # Add error to analyzer
                    analyzer.add_output(
                        f'{{"level":"error","msg":"Bisync failed: {str(e)}","source":"bisync_all_stream"}}',
                        command_info={
                            "command": "bisync",
                            "source": folder_pair.source,
                            "destination": folder_pair.destination,
                            "error": str(e),
                            "timestamp": start_time.isoformat(),
                        }
                    )
                    
                    # Check if this is a "first run" error
                    error_str = str(e).lower()
                    if "empty prior" in error_str and "listing" in error_str:
                        logger.error("")
                        logger.error("💡 This appears to be the first bisync run for this folder pair.")
                        logger.error("   Run with --resync flag to initialize:")
                        logger.error(f"   python main_bisync_resync.py")
                        logger.error("")
        
        # Report generated automatically by analyzer on context exit
        logger.info("Batch bisync completed - analysis report generated")

    def resync_all(self) -> None:
        """
        Resync all configured folder pairs.

        Warning:
            --resync will copy (not sync) files between paths.
            This means:
            - Deleted files may reappear
            - Renamed files will be duplicated
            - Use only when necessary (first run, filter changes, recovery)
        """
        logger.warning("=" * 70)
        logger.warning("⚠️  RESYNC MODE - Important Information")
        logger.warning("=" * 70)
        logger.warning(
            "--resync will copy files between paths (NOT true bidirectional sync)"
        )
        logger.warning("This means:")
        logger.warning("  • Deleted files will reappear from the other side")
        logger.warning("  • Renamed files will result in duplicates")
        logger.warning("  • Use only for: first run, filter changes, or recovery")
        logger.warning("")
        logger.warning("For robust recovery from interruptions, use --resilient")
        logger.warning("and --recover flags instead (enabled by default).")
        logger.warning("=" * 70)

        self.bisync_all_stream(resync=True)

    def check_bisync_status(self) -> dict[str, bool]:
        """
        Check bisync configuration status and best practices.

        Returns:
            Dict with configuration status
        """
        status = {
            "resilient_enabled": self.bisync_config.resilient,
            "recover_enabled": self.bisync_config.recover,
            "max_lock_set": self.bisync_config.max_lock != "0s",
            "conflict_resolution_set": self.bisync_config.conflict_resolve != "none",
            "backup_dirs_configured": bool(self.bisync_config.backup_dir),
        }

        # Log status
        logger.info("=" * 70)
        logger.info("Bisync Configuration Status")
        logger.info("=" * 70)
        logger.info(
            f"  Resilient mode: {'✓ Enabled' if status['resilient_enabled'] else '✗ Disabled'}"
        )
        logger.info(
            f"  Recover mode: {'✓ Enabled' if status['recover_enabled'] else '✗ Disabled'}"
        )
        logger.info(f"  Max lock: {self.bisync_config.max_lock}")
        logger.info(f"  Conflict resolve: {self.bisync_config.conflict_resolve}")
        logger.info(f"  Conflict loser: {self.bisync_config.conflict_loser}")
        logger.info(f"  Backup dir: {self.bisync_config.backup_dir}")
        logger.info("=" * 70)

        # Check best practices
        all_good = all(status.values())
        if all_good:
            logger.info("✓ Configuration follows rclone bisync best practices!")
        else:
            logger.warning(
                "⚠️  Consider enabling all recommended flags for robust operation:"
            )
            if not status["resilient_enabled"]:
                logger.warning(
                    "  • Set resilient: true (auto-retry after non-critical errors)"
                )
            if not status["recover_enabled"]:
                logger.warning(
                    "  • Set recover: true (auto-recover from interruptions)"
                )
            if not status["max_lock_set"]:
                logger.warning("  • Set max_lock: '2m' (auto-expire stale locks)")
            if not status["conflict_resolution_set"]:
                logger.warning(
                    "  • Set conflict_resolve: 'newer' (auto-resolve conflicts)"
                )

        logger.info("=" * 70)
        return status
