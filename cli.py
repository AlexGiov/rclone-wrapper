"""Command-line interface for rclone wrapper."""

import argparse
import sys
import logging
from pathlib import Path

from rclone_wrapper import (
    __version__,
    BackupManager,
    SyncManager,
    BisyncManager,
    load_backup_config,
    load_sync_config,
    load_bisync_config,
    RcloneError,
)
from rclone_wrapper.utils import setup_logging
from rclone_wrapper.core import ensure_rclone


DEFAULT_CONFIG_DIR = Path('config')


def create_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        description="Professional Python wrapper for rclone operations",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {__version__}'
    )
    
    parser.add_argument(
        '--config-dir',
        type=Path,
        default=DEFAULT_CONFIG_DIR,
        help='Configuration directory path (default: config/)'
    )
    
    parser.add_argument(
        '--rclone',
        type=Path,
        help='Path to rclone executable (default: auto-detect)'
    )
    
    parser.add_argument(
        '--log-file',
        type=Path,
        help='Log file path (default: logs/rclone_wrapper.log)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose console output'
    )
    
    parser.add_argument(
        '--dry-run', '-n',
        action='store_true',
        help='Perform a trial run with no changes made'
    )
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Backup command
    backup_parser = subparsers.add_parser('backup', help='Backup folders to remote')
    backup_parser.add_argument(
        '--no-cleanup',
        action='store_true',
        help='Skip cleanup of old backups'
    )
    backup_parser.add_argument(
        'folders',
        nargs='*',
        help='Folders to backup (overrides config)'
    )
    
    # Sync command
    sync_parser = subparsers.add_parser('sync', help='One-way sync to remote')
    sync_parser.add_argument(
        '--source',
        help='Local source folder'
    )
    sync_parser.add_argument(
        '--dest',
        help='Remote destination'
    )
    
    # Bisync command
    bisync_parser = subparsers.add_parser('bisync', help='Bidirectional sync')
    bisync_parser.add_argument(
        '--resync',
        action='store_true',
        help='Force resync operation'
    )
    bisync_parser.add_argument(
        '--no-auto-resync',
        action='store_true',
        help='Disable automatic resync on critical errors'
    )
    bisync_parser.add_argument(
        '--path1',
        help='First sync path (local)'
    )
    bisync_parser.add_argument(
        '--path2',
        help='Second sync path (remote)'
    )
    
    # Version info
    info_parser = subparsers.add_parser('info', help='Show version information')
    
    return parser


def cmd_backup(args: argparse.Namespace, logger: logging.Logger) -> int:
    """Execute backup command."""
    try:
        # Load backup configuration
        common_config, backup_config = load_backup_config(args.config_dir)
        
        # Override dry-run from CLI
        if args.dry_run:
            common_config.dry_run = True
        
        manager = BackupManager(common_config, backup_config, args.rclone, logger)
        
        folders = args.folders if args.folders else None
        cleanup = not args.no_cleanup
        
        manager.backup_folders(folders, cleanup)
        
        logger.info("Backup completed successfully")
        return 0
    
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        return 1


def cmd_sync(args: argparse.Namespace, logger: logging.Logger) -> int:
    """Execute sync command."""
    try:
        # Load sync configuration
        common_config, sync_config = load_sync_config(args.config_dir)
        
        if args.dry_run:
            common_config.dry_run = True
        
        manager = SyncManager(common_config, sync_config, args.rclone, logger)
        
        if args.source and args.dest:
            # Single sync
            manager.sync_folder(args.source, args.dest)
        else:
            # Sync all configured folders
            manager.sync_folders()
        
        logger.info("Sync completed successfully")
        return 0
    
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        return 1


def cmd_bisync(args: argparse.Namespace, logger: logging.Logger) -> int:
    """Execute bisync command."""
    try:
        # Load bisync configuration
        common_config, bisync_config = load_bisync_config(args.config_dir)
        
        if args.dry_run:
            common_config.dry_run = True
        
        manager = BisyncManager(common_config, bisync_config, args.rclone, logger)
        
        if args.path1 and args.path2:
            # Single bisync
            if args.resync:
                manager.resync(args.path1, args.path2, force=True)
            else:
                auto_resync = not args.no_auto_resync
                manager.sync(args.path1, args.path2, auto_resync)
        else:
            # Bisync all configured folders
            manager.sync_all()
        
        logger.info("Bisync completed successfully")
        return 0
    
    except Exception as e:
        logger.error(f"Bisync failed: {e}")
        return 1


def cmd_info(args: argparse.Namespace, logger: logging.Logger) -> int:
    """Show version information."""
    try:
        rclone = ensure_rclone(args.rclone)
        
        from rclone_wrapper.core import RcloneCommand
        from rclone_wrapper.config import CommonConfig
        
        # Minimal config for version check
        config = CommonConfig(remote="test")
        cmd = RcloneCommand(config, args.rclone, logger)
        
        print(f"rclone_wrapper version: {__version__}")
        print(f"rclone executable: {rclone}")
        print(f"rclone version: {cmd.version()}")
        
        return 0
    
    except Exception as e:
        logger.error(f"Failed to get version info: {e}")
        return 1


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Setup logging
    console_level = logging.INFO if args.verbose else logging.WARNING
    
    if args.log_file:
        log_file = args.log_file
    else:
        log_file = Path('logs') / 'rclone_wrapper.log'
    
    logger = setup_logging(
        log_file=log_file,
        console_level=console_level
    )
    
    # Show help if no command
    if not args.command:
        parser.print_help()
        return 0
    
    # Info command doesn't need config
    if args.command == 'info':
        return cmd_info(args, logger)
    
    # Execute command
    try:
        if args.command == 'backup':
            return cmd_backup(args, logger)
        
        elif args.command == 'sync':
            return cmd_sync(args, logger)
        
        elif args.command == 'bisync':
            return cmd_bisync(args, logger)
        
        else:
            parser.print_help()
            return 0
    
    except RcloneError as e:
        logger.error(f"Rclone error: {e}")
        return 1
    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
        return 130
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
