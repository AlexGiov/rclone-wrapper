"""Command-line interface for rclone wrapper."""

import argparse
import sys
import logging
from pathlib import Path

from rclone_wrapper import (
    __version__,
    ConfigLoader,
    RcloneError,
)
from rclone_wrapper.core.command import CommandExecutor
from rclone_wrapper.operations import (
    SyncOperationManager,
    BisyncOperationManager,
    CompareOperationManager,
)
from rclone_wrapper.backup_extended import BackupExtendedManager

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

DEFAULT_CONFIG_DIR = Path('config_examples')


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
    backup_parser = subparsers.add_parser('backup', help='Backup folders with ZIP archiving')
    backup_parser.add_argument(
        '--config-dir',
        type=Path,
        default=argparse.SUPPRESS,
        help='Configuration directory path (overrides global --config-dir)'
    )
    backup_parser.add_argument(
        '--no-cleanup',
        action='store_true',
        help='Skip cleanup of old backups'
    )

    # Sync command
    sync_parser = subparsers.add_parser('sync', help='One-way sync to remote')
    sync_parser.add_argument(
        '--config-dir',
        type=Path,
        default=argparse.SUPPRESS,
        help='Configuration directory path (overrides global --config-dir)'
    )
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
        '--config-dir',
        type=Path,
        default=argparse.SUPPRESS,
        help='Configuration directory path (overrides global --config-dir)'
    )
    bisync_parser.add_argument(
        '--resync',
        action='store_true',
        help='Force resync operation'
    )
    bisync_parser.add_argument(
        '--path1',
        help='First sync path (local)'
    )
    bisync_parser.add_argument(
        '--path2',
        help='Second sync path (remote)'
    )

    # Compare command
    compare_parser = subparsers.add_parser('compare', help='Compare directories')
    compare_parser.add_argument(
        '--config-dir',
        type=Path,
        default=argparse.SUPPRESS,
        help='Configuration directory path (overrides global --config-dir)'
    )
    compare_parser.add_argument(
        '--local',
        help='Local folder'
    )
    compare_parser.add_argument(
        '--remote',
        help='Remote folder'
    )

    # Version info
    info_parser = subparsers.add_parser('info', help='Show version information')
    
    return parser


def cmd_backup(args: argparse.Namespace, logger: logging.Logger) -> int:
    """Execute backup command."""
    try:
        loader = ConfigLoader(args.config_dir)
        common_config, backup_extended_config = loader.load_backup_extended()
        
        if args.dry_run:
            common_config.dry_run = True
        
        executor = CommandExecutor()
        manager = BackupExtendedManager(
            common_config=common_config,
            backup_extended_config=backup_extended_config,
            executor=executor,
            rclone_path=Path(args.rclone) if args.rclone else None,
        )
        
        cleanup = not args.no_cleanup
        manager.backup_all(cleanup=cleanup)
        
        logger.info("✅ Backup completed successfully")
        return 0
    
    except Exception as e:
        logger.error(f"❌ Backup failed: {e}")
        return 1


def cmd_sync(args: argparse.Namespace, logger: logging.Logger) -> int:
    """Execute sync command."""
    try:
        loader = ConfigLoader(args.config_dir)
        common_config, sync_config = loader.load_sync()
        
        if args.dry_run:
            common_config.dry_run = True
        
        executor = CommandExecutor()
        manager = SyncOperationManager(
            common_config=common_config,
            sync_config=sync_config,
            executor=executor,
            rclone_path=Path(args.rclone) if args.rclone else None,
        )
        
        manager.sync_all()
        
        logger.info("✅ Sync completed successfully")
        return 0
    
    except Exception as e:
        logger.error(f"❌ Sync failed: {e}")
        return 1


def cmd_bisync(args: argparse.Namespace, logger: logging.Logger) -> int:
    """Execute bisync command."""
    try:
        loader = ConfigLoader(args.config_dir)
        common_config, bisync_config = loader.load_bisync()
        
        if args.dry_run:
            common_config.dry_run = True
        
        executor = CommandExecutor()
        manager = BisyncOperationManager(
            common_config=common_config,
            bisync_config=bisync_config,
            executor=executor,
            rclone_path=Path(args.rclone) if args.rclone else None,
        )
        
        if args.resync:
            manager.resync_all()
        else:
            manager.bisync_all_stream()
        
        logger.info("✅ Bisync completed successfully")
        return 0
    
    except Exception as e:
        logger.error(f"❌ Bisync failed: {e}")
        return 1


def cmd_compare(args: argparse.Namespace, logger: logging.Logger) -> int:
    """Execute compare command."""
    try:
        loader = ConfigLoader(args.config_dir)
        common_config, compare_config = loader.load_compare()
        
        if args.dry_run:
            common_config.dry_run = True
        
        executor = CommandExecutor()
        manager = CompareOperationManager(
            common_config=common_config,
            compare_config=compare_config,
            executor=executor,
            rclone_path=Path(args.rclone) if args.rclone else None,
        )
        
        manager.compare_all()
        
        logger.info("✅ Compare completed successfully")
        return 0
    
    except Exception as e:
        logger.error(f"❌ Compare failed: {e}")
        return 1


def cmd_info(args: argparse.Namespace, logger: logging.Logger) -> int:
    """Show version information."""
    try:
        import shutil
        import subprocess
        
        rclone_path = args.rclone if args.rclone else "rclone"
        resolved = shutil.which(str(rclone_path)) or str(rclone_path)
        
        result = subprocess.run(
            [str(rclone_path), "version"],
            capture_output=True,
            text=True,
            check=True
        )
        
        print(f"rclone_wrapper version: {__version__}")
        print(f"rclone path: {resolved}")
        print(f"rclone version:\n{result.stdout}")
        
        return 0
    
    except Exception as e:
        logger.error(f"Failed to get version info: {e}")
        return 1


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    logger = logging.getLogger(__name__)
    
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
        
        elif args.command == 'compare':
            return cmd_compare(args, logger)
        
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
