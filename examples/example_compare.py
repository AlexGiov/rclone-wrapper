"""
Compare script using new architecture.

Loads configuration, creates compare manager, and compares all configured
folder pairs.

Uses RcloneOutputAnalyzer for automatic report generation.

Exit codes:
    0: Compare completed (check report for details)
    1: Critical error occurred
"""

import json
import logging
import sys
from pathlib import Path

# Add parent directory to path for rclone_wrapper import
sys.path.insert(0, str(Path(__file__).parent.parent))

from rclone_wrapper.config import ConfigLoader
from rclone_wrapper.core.command import CommandExecutor
from rclone_wrapper.operations import OperationFactory, PathValidator

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def main() -> int:
    """
    Run compare workflow.

    Returns:
        Exit code (0 = all match, 1 = differences found)
    """
    logger.info("=" * 70)
    logger.info("FOLDER COMPARISON - Production Run")
    logger.info("=" * 70)

    try:
        # Load configuration
        loader = ConfigLoader(config_dir=Path("config_examples"))
        common_config, compare_config = loader.load_compare()

        logger.info(f"Remote: {common_config.remote}")
        logger.info(f"Folder pairs: {len(compare_config.folders)}")
        logger.info(f"One-way mode: {compare_config.one_way}")
        logger.info(f"Download mode: {compare_config.download}")
        logger.info(f"Log directory: {common_config.log_dir}")

        if common_config.dry_run:
            logger.warning("⚠️  DRY-RUN MODE - No actual changes will be made")

        # Validate all folder pairs before starting comparison
        logger.info("")
        logger.info("="*70)
        logger.info("Validating folder pairs...")
        logger.info("="*70)

        executor = CommandExecutor()
        validator = PathValidator(executor)

        validation_failed = False
        for i, folder_pair in enumerate(compare_config.folders, 1):
            logger.info(f"\nValidating pair {i}/{len(compare_config.folders)}:")
            logger.info(f"  {folder_pair.source} <-> {folder_pair.destination}")

            result = validator.validate_folder_pair(
                folder_pair,
                create_missing=False,  # Don't auto-create
                allow_empty=False,  # Safety check enabled
                interactive=True,  # Ask user for decisions
            )

            # Show actions taken
            for action in result.actions_taken:
                logger.info(f"  ✓ {action}")

            # Show warnings
            for warning in result.warnings:
                logger.warning(f"  ⚠️  {warning}")

            # Show issues
            if not result.is_valid:
                validation_failed = True
                for issue in result.issues:
                    logger.error(f"  ❌ {issue}")

        if validation_failed:
            logger.error("")
            logger.error("="*70)
            logger.error("❌ VALIDATION FAILED")
            logger.error("="*70)
            logger.error("Fix the issues above before running comparison.")
            return 1

        logger.info("")
        logger.info("✅ All folder pairs validated successfully")

        # Create operation manager
        factory = OperationFactory(rclone_path=Path(common_config.rclone_path))
        compare_manager = factory.create_compare_manager(common_config, compare_config)

        # Compare all folders (report auto-generated)
        logger.info("")
        logger.info("=" * 70)
        logger.info("Comparing all configured folder pairs...")
        logger.info("=" * 70)
        logger.info("")

        compare_manager.compare_all()

        logger.info("")
        logger.info("=" * 70)
        logger.info("COMPARISON COMPLETED")
        logger.info("=" * 70)
        
        # Read latest analysis report
        log_dir = Path(common_config.log_dir)
        analysis_files = sorted(log_dir.glob("*_compare_batch_analysis.json"))
        
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
            for cmd in report['commands']:
                cmd_num = cmd['command_info']['command_number']
                cmd_ops = cmd['summary']['total_operations']
                if cmd_ops > 0:
                    logger.info(f"  Command #{cmd_num}: {cmd_ops} operations")
            
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
