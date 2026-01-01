"""Extended backup operations with multiple archives and advanced filtering."""

import logging
import zipfile
import re
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict

from .core import RcloneCommand
from .config import CommonConfig, BackupExtendedConfig, ArchiveConfig, FilterConfig
from .utils import format_size


class BackupExtendedManager(RcloneCommand):
    """Manager for extended backup operations with multiple archives."""
    
    def __init__(
        self,
        common_config: CommonConfig,
        backup_extended_config: BackupExtendedConfig,
        rclone_path: Optional[Path] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize BackupExtendedManager.
        
        Args:
            common_config: Common rclone configuration
            backup_extended_config: Extended backup configuration
            rclone_path: Optional path to rclone executable
            logger: Optional logger instance
        """
        super().__init__(common_config, rclone_path, logger)
        self.backup_extended_config = backup_extended_config
    
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
            self.logger.warning(
                f"Archive '{archive.remote}' retention ({retention}d) exceeds "
                f"max_retention_days ({max_retention}d), clipping to {max_retention}d"
            )
            return max_retention
        
        return retention
    
    def _create_single_zip(
        self,
        folders: List[str],
        output_path: Path,
        compression_level: int,
        filters: Optional[FilterConfig] = None
    ) -> Optional[Path]:
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
        self.logger.info(f"Creating archive: {output_path}")
        
        # Map compression level to zipfile constant
        compression = zipfile.ZIP_DEFLATED if compression_level > 0 else zipfile.ZIP_STORED
        
        files_added = 0
        
        with zipfile.ZipFile(output_path, 'w', compression, compresslevel=compression_level) as zipf:
            for folder in folders:
                folder_path = Path(folder)
                if not folder_path.exists():
                    self.logger.warning(f"Folder not found, skipping: {folder}")
                    continue
                
                if not folder_path.is_dir():
                    self.logger.warning(f"Not a directory, skipping: {folder}")
                    continue
                
                self.logger.info(f"Archiving: {folder_path}")
                
                # Add all files from this folder
                for file_path in folder_path.rglob('*'):
                    if file_path.is_file():
                        # Preserve folder structure: folder_name/subpath/file
                        arcname = Path(folder_path.name) / file_path.relative_to(folder_path)
                        zipf.write(file_path, arcname)
                        files_added += 1
        
        if files_added == 0:
            self.logger.error(f"No files added to archive, removing empty ZIP: {output_path}")
            output_path.unlink()
            return None
        
        size = output_path.stat().st_size
        self.logger.info(
            f"Archive created: {output_path} ({format_size(size)}, {files_added} files)"
        )
        
        return output_path
    
    def create_archive(
        self,
        archive: ArchiveConfig,
        timestamp: Optional[str] = None
    ) -> List[Path]:
        """
        Create ZIP archive(s) for a single archive configuration.
        
        Args:
            archive: Archive configuration
            timestamp: Optional timestamp string (generated if not provided)
        
        Returns:
            List of created archive paths
        """
        if not archive.enabled:
            self.logger.info(f"Archive '{archive.remote}' is disabled, skipping")
            return []
        
        if timestamp is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Merge filters: global + archive-specific
        merged_filters = self._merge_filters(
            self.backup_extended_config.filters,
            archive.filters
        )
        
        created_archives = []
        
        if archive.merge_zip:
            # Single ZIP for all folders
            zip_name = f"{archive.remote}_{timestamp}.zip"
            output_path = Path(zip_name)
            
            result = self._create_single_zip(
                archive.local,
                output_path,
                archive.compression_level,
                merged_filters
            )
            
            if result:
                created_archives.append(result)
        
        else:
            # Separate ZIP for each folder
            for folder in archive.local:
                folder_path = Path(folder)
                if not folder_path.exists():
                    self.logger.warning(f"Folder not found, skipping: {folder}")
                    continue
                
                sanitized_name = self._sanitize_name(folder_path.name)
                zip_name = f"{sanitized_name}_{timestamp}.zip"
                output_path = Path(zip_name)
                
                result = self._create_single_zip(
                    [folder],
                    output_path,
                    archive.compression_level,
                    merged_filters
                )
                
                if result:
                    created_archives.append(result)
        
        return created_archives
    
    def upload(
        self,
        local_paths: List[Path],
        remote_subfolder: str,
        delete_after: bool = False,
        verify: bool = False
    ) -> None:
        """
        Upload files to remote.
        
        Args:
            local_paths: List of local files to upload
            remote_subfolder: Remote subfolder (archive.remote)
            delete_after: Delete local files after successful upload
            verify: Verify upload with rclone check
        """
        if not local_paths:
            self.logger.warning("No files to upload")
            return
        
        # Build destination path: dest_base/remote_subfolder/
        remote_path = f"{self.backup_extended_config.dest_base}/{remote_subfolder}"
        dest = f"{self.config.remote}:{remote_path}"
        
        self.logger.info(f"Uploading {len(local_paths)} file(s) to {dest}")
        
        for local_path in local_paths:
            if not local_path.exists():
                self.logger.error(f"File not found, skipping: {local_path}")
                continue
            
            self.logger.info(f"Uploading: {local_path}")
            
            cmd = self._build_cmd('copy', str(local_path), dest, progress=True)
            self._run(cmd)
            
            self.logger.info(f"Upload completed: {local_path.name}")
            
            if verify:
                self.logger.info(f"Verifying upload: {local_path.name}")
                remote_file = f"{dest}/{local_path.name}"
                if self.check(str(local_path), remote_file):
                    self.logger.info(f"✅ Verification passed: {local_path.name}")
                else:
                    self.logger.error(f"❌ Verification failed: {local_path.name}")
                    # Don't delete if verification failed
                    continue
            
            if delete_after:
                local_path.unlink()
                self.logger.info(f"Deleted local file: {local_path}")
    
    def cleanup_old_backups(
        self,
        archive: ArchiveConfig,
        pattern: Optional[str] = None
    ) -> None:
        """
        Clean up old backups for a specific archive based on retention policy.
        
        Args:
            archive: Archive configuration
            pattern: Optional file pattern (defaults to archive.remote_*.zip or *_*.zip)
        """
        retention_days = self._get_effective_retention(archive)
        
        # Handle retention_days = 0 (keep only latest)
        if retention_days == 0:
            self.logger.info(
                f"Archive '{archive.remote}' has retention_days=0, "
                "will keep only latest backup"
            )
            # We'll implement this by listing files and deleting all but the newest
            # This requires special handling, so we'll use rclone lsjson + delete
            self._cleanup_keep_latest(archive)
            return
        
        # Normal retention cleanup
        remote_path = f"{self.backup_extended_config.dest_base}/{archive.remote}"
        dest = f"{self.config.remote}:{remote_path}"
        
        # Default pattern: match archive name or any folder name for merge_zip=false
        if pattern is None:
            if archive.merge_zip:
                pattern = f"{archive.remote}_*.zip"
            else:
                pattern = "*_*.zip"
        
        self.logger.info(
            f"Cleaning up '{archive.remote}' backups older than {retention_days} days"
        )
        
        # Delete old files
        cmd = self._build_cmd(
            'delete',
            dest,
            f'--min-age={retention_days}d',
            f'--include={pattern}'
        )
        
        try:
            self._run(cmd)
            self.logger.info(f"Cleanup completed for '{archive.remote}'")
        except Exception as e:
            self.logger.warning(f"Cleanup failed for '{archive.remote}': {e}")
    
    def _cleanup_keep_latest(self, archive: ArchiveConfig) -> None:
        """
        Keep only the latest backup (retention_days = 0).
        
        Args:
            archive: Archive configuration
        """
        remote_path = f"{self.backup_extended_config.dest_base}/{archive.remote}"
        dest = f"{self.config.remote}:{remote_path}"
        
        # List all files with timestamps
        cmd = self._build_cmd('lsjson', dest)
        
        try:
            result = self._run(cmd, capture_output=True)
            
            import json
            files = json.loads(result.stdout)
            
            if not files:
                self.logger.info(f"No files found in '{archive.remote}'")
                return
            
            # Filter ZIP files and sort by ModTime (newest first)
            zip_files = [f for f in files if f['Name'].endswith('.zip')]
            zip_files.sort(key=lambda x: x['ModTime'], reverse=True)
            
            if len(zip_files) <= 1:
                self.logger.info(f"Only {len(zip_files)} backup(s) found, nothing to clean")
                return
            
            # Keep the first (newest), delete the rest
            for old_file in zip_files[1:]:
                file_path = f"{dest}/{old_file['Name']}"
                self.logger.info(f"Deleting old backup: {old_file['Name']}")
                
                delete_cmd = self._build_cmd('deletefile', file_path)
                self._run(delete_cmd)
            
            self.logger.info(
                f"Kept latest backup, deleted {len(zip_files) - 1} old backup(s)"
            )
        
        except Exception as e:
            self.logger.warning(f"Could not cleanup old backups: {e}")
    
    def backup_archives(
        self,
        archives: Optional[List[ArchiveConfig]] = None,
        cleanup: bool = True,
        verify: bool = False
    ) -> None:
        """
        Complete backup workflow for multiple archives.
        
        Args:
            archives: List of archives to backup (defaults to all enabled in config)
            cleanup: Whether to run cleanup after upload
            verify: Verify uploads with rclone check
        """
        if archives is None:
            archives = [a for a in self.backup_extended_config.archives if a.enabled]
        
        if not archives:
            self.logger.warning("No enabled archives to backup")
            return
        
        # Use same timestamp for all archives in this run
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        self.logger.info(f"Starting backup of {len(archives)} archive(s)")
        
        for archive in archives:
            if not archive.enabled:
                continue
            
            self.logger.info(f"Processing archive: '{archive.remote}'")
            if archive.description:
                self.logger.info(f"  Description: {archive.description}")
            
            try:
                # Create archives
                created_files = self.create_archive(archive, timestamp)
                
                if not created_files:
                    self.logger.warning(f"No archives created for '{archive.remote}'")
                    continue
                
                # Upload
                self.upload(created_files, archive.remote, delete_after=True, verify=verify)
                
                # Cleanup old backups
                if cleanup:
                    self.cleanup_old_backups(archive)
                
                self.logger.info(f"✅ Archive '{archive.remote}' completed successfully")
            
            except Exception as e:
                self.logger.error(f"❌ Archive '{archive.remote}' failed: {e}")
                # Keep local files on failure
                for file_path in created_files:
                    if file_path.exists():
                        self.logger.info(f"Local archive preserved: {file_path}")
                # Continue with next archive (best-effort)
                continue
        
        self.logger.info("Backup workflow completed")
