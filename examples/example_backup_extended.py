"""
Extended backup script using new architecture.

Loads configuration, creates backup extended manager, and performs
multi-archive backup with ZIP compression, upload, and retention.

Uses RcloneOutputAnalyzer for automatic report generation.

Exit codes:
    0: Backup completed (check report for details)
    1: Critical error occurred
"""

import json
import logging
import sys
from pathlib import Path

# Add parent directory to path for rclone_wrapper import
sys.path.insert(0, str(Path(__file__).parent.parent))

from rclone_wrapper.backup_extended import BackupExtendedManager
from rclone_wrapper.config import ConfigLoader
from rclone_wrapper.core.command import CommandExecutor

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def validate_source_folders(backup_extended_config) -> tuple[bool, list[str]]:
    """
    Validate that source folders exist (non-blocking).
    
    Args:
        backup_extended_config: Backup extended configuration
        
    Returns:
        Tuple of (all_valid, warnings_list)
    """
    warnings = []
    all_valid = True
    
    for archive in backup_extended_config.archives:
        if not archive.enabled:
            continue
            
        for folder in archive.source:
            folder_path = Path(folder)
            if not folder_path.exists():
                warnings.append(f"Source folder not found: {folder}")
                all_valid = False
            elif not folder_path.is_dir():
                warnings.append(f"Source path is not a directory: {folder}")
                all_valid = False
    
    return all_valid, warnings


def main() -> int:
    """
    Run extended backup workflow.

    Returns:
        Exit code (0 = success, 1 = failure)
    """
    logger.info("=" * 70)
    logger.info("EXTENDED BACKUP - Multi-Archive with Retention")
    logger.info("=" * 70)

    try:
        # Load configuration
        loader = ConfigLoader(config_dir=Path("config_examples"))
        common_config, backup_extended_config = loader.load_backup_extended()

        logger.info(f"Remote: {common_config.remote}")
        logger.info(f"Destination base: {backup_extended_config.dest_base}")
        logger.info(f"Archives configured: {len(backup_extended_config.archives)}")
        logger.info(f"Max retention: {backup_extended_config.max_retention_days} days")
        logger.info(f"Log directory: {common_config.log_dir}")

        if common_config.dry_run:
            logger.warning("⚠️  DRY-RUN MODE - No actual changes will be made")

        # Display archives summary
        logger.info("")
        logger.info("=" * 70)
        logger.info("Archives to process:")
        logger.info("=" * 70)
        
        enabled_count = 0
        for i, archive in enumerate(backup_extended_config.archives, 1):
            status = "✓ ENABLED" if archive.enabled else "✗ DISABLED"
            logger.info(f"\n[{i}] {archive.destination} ({status})")
            if archive.description:
                logger.info(f"    Description: {archive.description}")
            logger.info(f"    Sources: {len(archive.source)} folder(s)")
            for src in archive.source:
                logger.info(f"      - {src}")
            logger.info(f"    Merge ZIP: {archive.merge_zip}")
            logger.info(f"    Compression: Level {archive.compression_level}")
            logger.info(f"    Retention: {archive.retention_days} days")
            if archive.enabled:
                enabled_count += 1
        
        logger.info("")
        logger.info(f"Total enabled archives: {enabled_count}")

        if enabled_count == 0:
            logger.warning("No enabled archives to process")
            return 0

        # Validate source folders (non-blocking warnings)
        logger.info("")
        logger.info("=" * 70)
        logger.info("Validating source folders...")
        logger.info("=" * 70)
        
        all_valid, warnings = validate_source_folders(backup_extended_config)
        
        if warnings:
            logger.warning(f"\n⚠️  Found {len(warnings)} issue(s):")
            for warning in warnings:
                logger.warning(f"  • {warning}")
            logger.warning("\n⚠️  Backup will proceed, but these folders will be skipped")
        else:
            logger.info("✅ All source folders validated successfully")

        # Create operation manager
        logger.info("")
        logger.info("=" * 70)
        logger.info("Starting backup process...")
        logger.info("=" * 70)
        logger.info("")

        executor = CommandExecutor()
        backup_manager = BackupExtendedManager(
            common_config=common_config,
            backup_extended_config=backup_extended_config,
            executor=executor,
            rclone_path=Path(common_config.rclone_path),
        )

        # Execute backup (report auto-generated)
        backup_manager.backup_all(cleanup=True, verify=False)

        logger.info("")
        logger.info("=" * 70)
        logger.info("BACKUP COMPLETED")
        logger.info("=" * 70)
        
        # Read latest analysis report
        log_dir = Path(common_config.log_dir)
        analysis_files = sorted(log_dir.glob("*_backup_batch_analysis.json"))
        
        if analysis_files:
            latest_report = analysis_files[-1]
            with open(latest_report, 'r') as f:
                report = json.load(f)
            
            # Calculate total operations across all commands
            total_ops = sum(cmd['summary']['total_operations'] for cmd in report['commands'])
            
            logger.info(f"  Session: {report['session_info']['session_name']}")
            logger.info(f"  Duration: {report['session_info']['duration_seconds']:.2f}s")
            logger.info(f"  Commands executed: {report['session_info']['commands_executed']}")
            logger.info(f"  Total operations: {total_ops}")
            logger.info("")
            
            # Show per-command summary
            upload_count = 0
            cleanup_count = 0
            for cmd in report['commands']:
                cmd_info = cmd['command_info']
                if cmd_info.get('command') == 'copy':
                    upload_count += 1
                elif cmd_info.get('command') in ['delete', 'deletefile']:
                    cleanup_count += 1
            
            logger.info(f"  Uploads: {upload_count}")
            logger.info(f"  Cleanups: {cleanup_count}")
            logger.info("")
            logger.info(f"📊 Detailed report: {latest_report.name}")
        else:
            logger.warning("  No analysis report found")
        
        logger.info("=" * 70)
        logger.info("✅ Check logs directory for complete analysis")
        logger.info("=" * 70)
        
        return 0

    except Exception as e:
        logger.error(f"❌ CRITICAL ERROR: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
