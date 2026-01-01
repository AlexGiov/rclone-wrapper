"""Backup operations using rclone."""

import logging
import zipfile
import tempfile
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from .core import RcloneCommand
from .config import CommonConfig, BackupConfig
from .utils import format_size, ensure_path_exists


class BackupManager(RcloneCommand):
    """Manager for backup operations with ZIP and retention."""
    
    def __init__(
        self,
        common_config: CommonConfig,
        backup_config: BackupConfig,
        rclone_path: Optional[Path] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize BackupManager.
        
        Args:
            common_config: Common rclone configuration
            backup_config: Backup-specific configuration
            rclone_path: Optional path to rclone executable
            logger: Optional logger instance
        """
        super().__init__(common_config, rclone_path, logger)
        self.backup_config = backup_config
    
    def create_archive(
        self,
        folders: List[str],
        output_path: Optional[Path] = None,
        compression: int = zipfile.ZIP_DEFLATED
    ) -> Path:
        """
        Create ZIP archive of specified folders.
        
        Args:
            folders: List of folder paths to archive
            output_path: Optional output path for archive
            compression: ZIP compression method
        
        Returns:
            Path to created archive
        """
        if not folders:
            raise ValueError("No folders specified for archiving")
        
        # Generate archive name
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if output_path is None:
            output_path = Path(f"{self.backup_config.zip_prefix}{timestamp}.zip")
        
        self.logger.info(f"Creating archive: {output_path}")
        
        # Create archive
        with zipfile.ZipFile(output_path, 'w', compression) as zipf:
            for folder in folders:
                folder_path = Path(folder)
                if not folder_path.exists():
                    self.logger.warning(f"Folder not found, skipping: {folder}")
                    continue
                
                self.logger.info(f"Archiving: {folder_path}")
                for file_path in folder_path.rglob('*'):
                    if file_path.is_file():
                        arcname = file_path.relative_to(folder_path.parent)
                        zipf.write(file_path, arcname)
        
        size = output_path.stat().st_size
        self.logger.info(
            f"Archive created: {output_path} ({format_size(size)})"
        )
        
        return output_path
    
    def upload(
        self,
        local_path: Path,
        remote_path: Optional[str] = None,
        delete_after: bool = False
    ) -> None:
        """
        Upload file to remote.
        
        Args:
            local_path: Local file to upload
            remote_path: Remote destination (defaults to backup_config.dest_base)
            delete_after: Delete local file after successful upload
        """
        if not local_path.exists():
            raise FileNotFoundError(f"File not found: {local_path}")
        
        if remote_path is None:
            remote_path = self.backup_config.dest_base
        
        dest = f"{self.config.remote}:{remote_path}"
        
        self.logger.info(f"Uploading {local_path} to {dest}")
        
        cmd = self._build_cmd('copy', str(local_path), dest, progress=True)
        self._run(cmd)
        
        self.logger.info("Upload completed successfully")
        
        if delete_after:
            local_path.unlink()
            self.logger.info(f"Deleted local file: {local_path}")
    
    def cleanup_old_backups(
        self,
        remote_path: Optional[str] = None,
        retention_days: Optional[int] = None,
        pattern: str = "*.zip"
    ) -> None:
        """
        Clean up old backups based on retention policy.
        
        Args:
            remote_path: Remote path to clean (defaults to config.dest_base)
            retention_days: Retention period (defaults to config.retention_days)
            pattern: File pattern to match
        """
        if remote_path is None:
            remote_path = self.backup_config.dest_base
        if retention_days is None:
            retention_days = self.backup_config.retention_days
        
        dest = f"{self.config.remote}:{remote_path}"
        
        self.logger.info(
            f"Cleaning up backups older than {retention_days} days in {dest}"
        )
        
        # Delete old files
        cmd = self._build_cmd(
            'delete',
            dest,
            f'--min-age={retention_days}d',
            f'--include={pattern}'
        )
        self._run(cmd)
        
        # Remove empty directories
        cmd = self._build_cmd('rmdirs', dest)
        try:
            self._run(cmd)
        except Exception as e:
            self.logger.warning(f"Could not remove empty dirs: {e}")
        
        self.logger.info("Cleanup completed")
    
    def backup_folders(
        self,
        folders: Optional[List[str]] = None,
        cleanup: bool = True
    ) -> None:
        """
        Complete backup workflow: archive, upload, cleanup.
        
        Args:
            folders: Folders to backup (defaults to config.folders)
            cleanup: Whether to run cleanup after upload
        """
        if folders is None:
            folders = self.backup_config.folders
        
        if not folders:
            self.logger.warning("No folders configured for backup")
            return
        
        # Create archive
        archive = self.create_archive(folders)
        
        try:
            # Upload
            self.upload(archive, delete_after=True)
            
            # Cleanup old backups
            if cleanup:
                self.cleanup_old_backups()
        
        except Exception as e:
            self.logger.error(f"Backup failed: {e}")
            # Keep local archive on failure
            if archive.exists():
                self.logger.info(f"Local archive preserved: {archive}")
            raise
