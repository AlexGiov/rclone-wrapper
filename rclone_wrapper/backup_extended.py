"""
Backup extended operation manager - Multi-archive backup operations.

Implements backup operations with ZIP archiving, upload, and retention
using the new architecture with dependency injection and proper separation of concerns.

ARCHITECTURE:
- Uses RcloneOutputAnalyzer for all parsing and logging (SRP compliant)
- Batch operations with aggregated reporting
- CommandBuilder for all rclone commands
- Local ZIP creation separate from rclone operations

WORKFLOW:
1. Create ZIP archives locally (multiple folders -> single or multiple ZIPs)
2. Upload ZIPs to remote using rclone copy with --use-json-log
3. Execute within RcloneOutputAnalyzer context
4. Cleanup old backups based on retention policy
5. Analyzer handles all parsing, counting, and report generation
"""

import json
import logging
import re
import zipfile
from datetime import datetime
from pathlib import Path

from .config import ArchiveConfig, BackupExtendedConfig, CommonConfig, FilterConfig
from .core.command import CommandBuilder, CommandExecutor
from .logging.output_analyzer import RcloneOutputAnalyzer
from .operations.base import BaseOperationManager

__all__ = ["BackupExtendedManager"]

logger = logging.getLogger(__name__)


class BackupExtendedManager(BaseOperationManager):
    """
    Manager for extended backup operations with multiple archives.
    
    ARCHITECTURE: Uses RcloneOutputAnalyzer for all parsing and logging.
    
    Key features:
    - ZIP archiving with compression and filtering
    - Multiple archives with individual retention policies
    - All parsing delegated to RcloneOutputAnalyzer (SRP compliant)
    - Batch operations with aggregated reporting
    - Direct command building without factory pattern overhead
    
    Example:
        >>> executor = CommandExecutor()
        >>> manager = BackupExtendedManager(
        ...     common_config=common,
        ...     backup_extended_config=backup_ext,
        ...     executor=executor,
        ... )
        >>> manager.backup_all()
    """
    
    def __init__(
        self,
        common_config: CommonConfig,
        backup_extended_config: BackupExtendedConfig,
        executor: CommandExecutor,
        rclone_path: Path | None = None,
        log_dir: Path | None = None,
    ) -> None:
        """
        Initialize backup extended operation manager.
        
        Args:
            common_config: Common configuration
            backup_extended_config: Backup extended configuration
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
        self.backup_extended_config = backup_extended_config
    
    def _build_command(
        self,
        builder: CommandBuilder,
        source: str,
        destination: str | None,
        **kwargs,
    ) -> CommandBuilder:
        """
        Build backup-specific command (copy or delete).
        
        Args:
            builder: Command builder
            source: Source path (local ZIP file for upload)
            destination: Destination path (remote)
            **kwargs: Additional parameters (operation, retention_days, pattern, etc.)
            
        Returns:
            Builder with backup settings
        """
        operation = kwargs.get("operation", "copy")
        
        if operation == "copy":
            # Upload command
            builder.subcommand("copy")
            builder.arguments(source, destination)
            builder.json_log()
            
        elif operation == "delete":
            # Cleanup command
            builder.subcommand("delete")
            builder.arguments(destination)
            
            # Retention filter
            retention_days = kwargs.get("retention_days")
            if retention_days is not None and retention_days > 0:
                builder.arguments(f"--min-age={retention_days}d")
            
            # Pattern filter - use --filter to avoid rclone warning about
            # mixing --include and --exclude (order is indeterminate)
            pattern = kwargs.get("pattern")
            if pattern:
                builder.arguments(f"--filter=+ {pattern}")
                builder.arguments("--filter=- *")
            
            builder.json_log()
        
        elif operation == "lsjson":
            # List files (for keep-latest cleanup)
            builder.subcommand("lsjson")
            builder.arguments(destination)
            builder.json_log()
            
        elif operation == "deletefile":
            # Delete specific file
            builder.subcommand("deletefile")
            builder.arguments(destination)
            builder.json_log()
        
        return builder
    
    # =========================================================================
    # HELPER METHODS (Local operations, not rclone)
    # =========================================================================
    
    def _sanitize_name(self, name: str) -> str:
        """
        Sanitize folder name for use in ZIP filename.
        
        Args:
            name: Original folder name
        
        Returns:
            Sanitized name (spaces to underscores, special chars removed)
        """
        # Get last component if it's a path
        name = Path(name).name
        # Replace spaces with underscores
        name = name.replace(' ', '_')
        # Remove special characters except underscore and hyphen
        name = re.sub(r'[^\w\-]', '', name)
        return name
    
    def _get_effective_retention(self, archive: ArchiveConfig) -> int:
        """
        Get effective retention days (clipped to max_retention_days).
        
        Args:
            archive: Archive configuration
        
        Returns:
            Effective retention days
        """
        retention = archive.retention_days
        max_retention = self.backup_extended_config.max_retention_days
        
        if retention > max_retention:
            logger.warning(
                f"Archive '{archive.destination}' retention ({retention}d) exceeds "
                f"max_retention_days ({max_retention}d), clipping to {max_retention}d"
            )
            return max_retention
        
        return retention
    
    def _format_size(self, size_bytes: int) -> str:
        """Format size in bytes to human-readable string."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"
    
    def _create_single_zip(
        self,
        folders: list[str],
        output_path: Path,
        compression_level: int,
        filters: FilterConfig | None = None
    ) -> Path | None:
        """
        Create a single ZIP archive from multiple folders.
        
        Args:
            folders: List of local folder paths
            output_path: Path for output ZIP file
            compression_level: ZIP compression level (0-9)
            filters: Optional filter configuration
        
        Returns:
            Path to created archive, or None if all folders failed
        """
        logger.info(f"Creating archive: {output_path}")
        
        # Map compression level to zipfile constant
        compression = zipfile.ZIP_DEFLATED if compression_level > 0 else zipfile.ZIP_STORED
        
        files_added = 0
        
        with zipfile.ZipFile(output_path, 'w', compression, compresslevel=compression_level) as zipf:
            for folder in folders:
                folder_path = Path(folder)
                if not folder_path.exists():
                    logger.warning(f"Folder not found, skipping: {folder}")
                    continue
                
                if not folder_path.is_dir():
                    logger.warning(f"Not a directory, skipping: {folder}")
                    continue
                
                logger.info(f"Archiving: {folder_path}")
                
                # Add all files from this folder
                for file_path in folder_path.rglob('*'):
                    if file_path.is_file():
                        # Preserve folder structure: folder_name/subpath/file
                        arcname = Path(folder_path.name) / file_path.relative_to(folder_path)
                        zipf.write(file_path, arcname)
                        files_added += 1
        
        if files_added == 0:
            logger.error(f"No files added to archive, removing empty ZIP: {output_path}")
            output_path.unlink()
            return None
        
        size = output_path.stat().st_size
        logger.info(
            f"Archive created: {output_path} ({self._format_size(size)}, {files_added} files)"
        )
        
        return output_path
    
    def _create_archive(
        self,
        archive: ArchiveConfig,
        timestamp: str
    ) -> list[Path]:
        """
        Create single ZIP archive for an archive configuration.
        
        Each archive creates ONE ZIP file containing all source folders.
        
        Args:
            archive: Archive configuration
            timestamp: Timestamp string for archive naming
        
        Returns:
            List containing single created archive path (or empty if disabled/failed)
        """
        if not archive.enabled:
            logger.info(f"Archive '{archive.destination}' is disabled, skipping")
            return []
        
        # Merge filters: global + archive-specific
        merged_filters = self._merge_filters(
            self.backup_extended_config.filters,
            archive.filters
        )
        
        # Always create single ZIP for all folders in this archive
        # Name format: <source_folder>_backup_<timestamp>.zip
        source_folder = self._sanitize_name(archive.source[0])
        local_name = f"{source_folder}_backup"
        zip_name = f"{local_name}_{timestamp}.zip"
        output_path = Path(zip_name)
        
        result = self._create_single_zip(
            archive.source,
            output_path,
            archive.compression_level,
            merged_filters
        )
        
        return [result] if result else []
    
    # =========================================================================
    # MAIN OPERATIONS
    # =========================================================================
    
    def _upload_archive(
        self,
        local_path: Path,
        archive: ArchiveConfig,
        analyzer: RcloneOutputAnalyzer
    ) -> bool:
        """
        Upload a single archive to remote.
        
        Args:
            local_path: Local ZIP file path
            archive: Archive configuration
            analyzer: Output analyzer for logging
        
        Returns:
            True if upload successful, False otherwise
        """
        # Build destination path: dest_base/destination/
        # Normalize destination separators for remote path (always use /)
        remote_dest = archive.destination.replace("\\", "/")
        remote_path = f"{self.backup_extended_config.dest_base}/{remote_dest}"
        dest = f"{self.common_config.remote}:{remote_path}"
        
        logger.info(f"Uploading: {local_path.name} -> {dest}")
        
        start_time = datetime.now()
        
        try:
            # Build upload command
            builder = CommandBuilder(self.rclone_path)
            builder = self._apply_common_settings(builder, None)
            builder = self._build_command(
                builder,
                source=str(local_path),
                destination=dest,
                operation="copy"
            )
            
            cmd = builder.build()
            
            # Execute and log
            result = self.executor.execute(cmd)
            analyzer.add_output(
                result.stderr,
                command_info={
                    "command": "copy",
                    "source": str(local_path),
                    "destination": dest,
                    "timestamp": start_time.isoformat(),
                    "returncode": result.returncode,
                }
            )
            
            if result.returncode == 0:
                logger.info(f"✓ Upload completed: {local_path.name}")
                # Delete local file after successful upload
                local_path.unlink()
                logger.info(f"Deleted local file: {local_path}")
                return True
            else:
                logger.error(f"✗ Upload failed: {local_path.name}")
                return False
                
        except Exception as e:
            logger.error(f"Error uploading {local_path}: {e}")
            analyzer.add_output(
                f'{{"level":"error","msg":"Upload failed: {str(e)}","source":"upload_archive"}}',
                command_info={
                    "command": "copy",
                    "source": str(local_path),
                    "destination": dest,
                    "error": str(e),
                    "timestamp": start_time.isoformat(),
                }
            )
            return False
    
    def _cleanup_old_backups(
        self,
        archive: ArchiveConfig,
        analyzer: RcloneOutputAnalyzer
    ) -> None:
        """
        Clean up old backups based on retention policy.
        
        Args:
            archive: Archive configuration
            analyzer: Output analyzer for logging
        """
        retention_days = self._get_effective_retention(archive)
        
        # Build remote path
        # Normalize destination separators for remote path (always use /)
        remote_dest = archive.destination.replace("\\", "/")
        remote_path = f"{self.backup_extended_config.dest_base}/{remote_dest}"
        dest = f"{self.common_config.remote}:{remote_path}"
        
        # Handle retention_days = 0 (keep only latest)
        if retention_days == 0:
            logger.info(f"Archive '{archive.destination}' has retention_days=0, keeping only latest")
            self._cleanup_keep_latest(archive, dest, analyzer)
            return
        
        # Normal retention cleanup
        # Pattern must match the filename used during upload: <source_folder>_backup_*.zip
        source_folder = self._sanitize_name(archive.source[0])
        local_name = f"{source_folder}_backup"
        pattern = f"{local_name}_*.zip"
        
        logger.info(
            f"Cleaning up '{archive.destination}' backups older than {retention_days} days"
        )
        
        start_time = datetime.now()
        
        try:
            # Build delete command
            builder = CommandBuilder(self.rclone_path)
            builder = self._apply_common_settings(builder, None)
            builder = self._build_command(
                builder,
                source="",  # Not used for delete
                destination=dest,
                operation="delete",
                retention_days=retention_days,
                pattern=pattern
            )
            
            cmd = builder.build()
            
            # Execute and log
            result = self.executor.execute(cmd)
            analyzer.add_output(
                result.stderr,
                command_info={
                    "command": "delete",
                    "destination": dest,
                    "retention_days": retention_days,
                    "pattern": pattern,
                    "timestamp": start_time.isoformat(),
                    "returncode": result.returncode,
                }
            )
            
            if result.returncode == 0:
                logger.info(f"✓ Cleanup completed for '{archive.destination}'")
            else:
                logger.warning(f"✗ Cleanup failed for '{archive.destination}'")
                
        except Exception as e:
            logger.warning(f"Cleanup error for '{archive.destination}': {e}")
            analyzer.add_output(
                f'{{"level":"error","msg":"Cleanup failed: {str(e)}","source":"cleanup_old_backups"}}',
                command_info={
                    "command": "delete",
                    "destination": dest,
                    "error": str(e),
                    "timestamp": start_time.isoformat(),
                }
            )
    
    def _cleanup_keep_latest(
        self,
        archive: ArchiveConfig,
        dest: str,
        analyzer: RcloneOutputAnalyzer
    ) -> None:
        """
        Keep only the latest backup (retention_days = 0).
        
        Args:
            archive: Archive configuration
            dest: Remote destination path
            analyzer: Output analyzer for logging
        """
        start_time = datetime.now()
        
        try:
            # List files
            builder = CommandBuilder(self.rclone_path)
            builder = self._apply_common_settings(builder, None)
            builder = self._build_command(
                builder,
                source="",
                destination=dest,
                operation="lsjson"
            )
            
            cmd = builder.build()
            result = self.executor.execute(cmd)
            
            if result.returncode != 0:
                logger.warning(f"Could not list files in '{archive.destination}'")
                return
            
            files = json.loads(result.stdout)
            
            if not files:
                logger.info(f"No files found in '{archive.destination}'")
                return
            
            # Filter ZIP files and sort by ModTime (newest first)
            zip_files = [f for f in files if f['Name'].endswith('.zip')]
            zip_files.sort(key=lambda x: x['ModTime'], reverse=True)
            
            if len(zip_files) <= 1:
                logger.info(f"Only {len(zip_files)} backup(s) found, nothing to clean")
                return
            
            # Keep the first (newest), delete the rest
            for old_file in zip_files[1:]:
                file_path = f"{dest}/{old_file['Name']}"
                logger.info(f"Deleting old backup: {old_file['Name']}")
                
                # Build deletefile command
                del_builder = CommandBuilder(self.rclone_path)
                del_builder = self._apply_common_settings(del_builder, None)
                del_builder = self._build_command(
                    del_builder,
                    source="",
                    destination=file_path,
                    operation="deletefile"
                )
                
                del_cmd = del_builder.build()
                del_result = self.executor.execute(del_cmd)
                
                analyzer.add_output(
                    del_result.stderr,
                    command_info={
                        "command": "deletefile",
                        "destination": file_path,
                        "timestamp": start_time.isoformat(),
                        "returncode": del_result.returncode,
                    }
                )
            
            logger.info(
                f"Kept latest backup, deleted {len(zip_files) - 1} old backup(s)"
            )
            
        except Exception as e:
            logger.warning(f"Could not cleanup old backups: {e}")
            analyzer.add_output(
                f'{{"level":"error","msg":"Keep-latest cleanup failed: {str(e)}","source":"cleanup_keep_latest"}}',
                command_info={
                    "command": "cleanup_keep_latest",
                    "destination": dest,
                    "error": str(e),
                    "timestamp": start_time.isoformat(),
                }
            )
    
    def backup_all(
        self,
        cleanup: bool = True,
        verify: bool = False
    ) -> None:
        """
        Complete backup workflow for all enabled archives.
        
        Uses RcloneOutputAnalyzer to execute commands and generate aggregated report.
        All parsing and logging is delegated to the analyzer (SRP compliant).
        
        Args:
            cleanup: Whether to run cleanup after upload
            verify: Reserved for future verification implementation
        """
        # Filter enabled archives
        archives = [a for a in self.backup_extended_config.archives if a.enabled]
        
        if not archives:
            logger.warning("No enabled archives to backup")
            return
        
        logger.info(f"Starting backup of {len(archives)} archive(s)")
        
        # Use same timestamp for all archives in this run
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # RcloneOutputAnalyzer handles ALL rclone logging and parsing
        with RcloneOutputAnalyzer(self.log_dir, session_name="backup_batch") as analyzer:
            for archive in archives:
                logger.info(f"Processing archive: '{archive.destination}'")
                if archive.description:
                    logger.info(f"  Description: {archive.description}")
                
                try:
                    # 1. Create ZIP archives (local operation)
                    created_files = self._create_archive(archive, timestamp)
                    
                    if not created_files:
                        logger.warning(f"No archives created for '{archive.destination}'")
                        continue
                    
                    # 2. Upload archives
                    upload_success = True
                    for zip_path in created_files:
                        if not self._upload_archive(zip_path, archive, analyzer):
                            upload_success = False
                    
                    if not upload_success:
                        logger.error(f"Some uploads failed for '{archive.destination}'")
                        # Preserve local files on failure
                        for zip_path in created_files:
                            if zip_path.exists():
                                logger.info(f"Local archive preserved: {zip_path}")
                        continue
                    
                    # 3. Cleanup old backups
                    if cleanup:
                        self._cleanup_old_backups(archive, analyzer)
                    
                    logger.info(f"✅ Archive '{archive.destination}' completed successfully")
                
                except Exception as e:
                    logger.error(f"❌ Archive '{archive.destination}' failed: {e}")
                    # Continue with next archive (best-effort)
                    continue
        
        # Report generated automatically by analyzer on context exit
        logger.info("Backup workflow completed - analysis report generated")
