"""
Selective Bisync RESYNC script - Initialize specific folder pairs.

This script allows you to selectively resync individual folder pairs
instead of resyncing all pairs at once.

Use this script when:
1. Only ONE folder pair needs resync (first run or error)
2. You want to avoid unnecessary resync of already-initialized pairs
3. You need granular control over which pairs to resync

⚠️  WARNING: --resync will COPY (not sync) files between paths.
   This means deleted files will reappear and renamed files will be duplicated.

For normal operation, use main_bisync.py instead.
"""

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


def display_folder_pairs(bisync_config) -> None:
    """Display available folder pairs with indices."""
    logger.info("")
    logger.info("=" * 70)
    logger.info("Available folder pairs:")
    logger.info("=" * 70)
    for i, folder_pair in enumerate(bisync_config.folders, 1):
        logger.info(f"  [{i}] {folder_pair.source}")
        logger.info(f"      <-> {folder_pair.destination}")
        logger.info("")


def get_user_selection(max_index: int) -> list[int]:
    """
    Get user selection for which folder pairs to resync.

    Args:
        max_index: Maximum valid index

    Returns:
        List of selected indices (0-based)
    """
    logger.info("=" * 70)
    logger.info("Selection options:")
    logger.info("  • Enter a number (e.g., '1') to resync a specific pair")
    logger.info("  • Enter multiple numbers separated by commas (e.g., '1,3')")
    logger.info("  • Enter 'all' to resync ALL pairs")
    logger.info("  • Enter 'cancel' to abort")
    logger.info("=" * 70)

    while True:
        choice = input("\n⚠️  Which folder pair(s) to resync? ").strip().lower()

        if choice == "cancel":
            logger.info("Resync cancelled by user.")
            sys.exit(0)

        if choice == "all":
            return list(range(max_index))

        try:
            # Parse comma-separated indices
            indices = [int(x.strip()) - 1 for x in choice.split(",")]

            # Validate indices
            if all(0 <= idx < max_index for idx in indices):
                return indices
            else:
                logger.error(
                    f"❌ Invalid selection. Please enter numbers between 1 and {max_index}."
                )
        except ValueError:
            logger.error(
                "❌ Invalid input. Please enter numbers, 'all', or 'cancel'."
            )


def main() -> int:
    """
    Run selective bidirectional sync with --resync.

    Returns:
        Exit code (0 = success, 1 = failure)
    """
    logger.warning("=" * 70)
    logger.warning("⚠️  SELECTIVE BISYNC RESYNC MODE")
    logger.warning("=" * 70)
    logger.warning("")
    logger.warning("This script allows you to resync SPECIFIC folder pairs.")
    logger.warning("")
    logger.warning("What --resync does:")
    logger.warning("  • Copies files from Path2 to Path1 (if missing)")
    logger.warning("  • Copies files from Path1 to Path2 (making a superset)")
    logger.warning("  • Creates baseline listing files for future syncs")
    logger.warning("")
    logger.warning("What --resync DOES NOT do:")
    logger.warning("  • Does NOT delete files (deleted files will reappear!)")
    logger.warning("  • Does NOT detect renames (will create duplicates!)")
    logger.warning("  • Does NOT bidirectionally sync changes")
    logger.warning("")
    logger.warning("Use --resync ONLY for:")
    logger.warning("  1. First bisync run (no listing files exist)")
    logger.warning("  2. After changing filters configuration")
    logger.warning("  3. Recovery from critical errors")
    logger.warning("")
    logger.warning("For normal operation, use main_bisync.py instead!")
    logger.warning("=" * 70)

    try:
        # Load configuration
        loader = ConfigLoader(config_dir=Path("config_examples"))
        common_config, bisync_config = loader.load_bisync()

        if not bisync_config.folders:
            logger.error("❌ No folder pairs configured in bisync.json")
            return 1

        logger.info("")
        logger.info(f"Remote: {common_config.remote}")
        logger.info(f"Total folder pairs: {len(bisync_config.folders)}")
        logger.info(f"Resync mode: {bisync_config.resync_mode}")
        logger.info(f"Log directory: {common_config.log_dir}")

        if common_config.dry_run:
            logger.warning("⚠️  DRY-RUN MODE - No actual changes will be made")

        # Display folder pairs
        display_folder_pairs(bisync_config)

        # Get user selection
        selected_indices = get_user_selection(len(bisync_config.folders))

        # Show selection
        logger.info("")
        logger.info("=" * 70)
        logger.info("Selected folder pairs for RESYNC:")
        logger.info("=" * 70)
        for idx in selected_indices:
            folder_pair = bisync_config.folders[idx]
            logger.info(f"  [{idx + 1}] {folder_pair.source}")
            logger.info(f"      <-> {folder_pair.destination}")
        logger.info("")

        # Ask for final confirmation
        logger.warning("=" * 70)
        logger.warning("⚠️  FINAL CONFIRMATION")
        logger.warning("=" * 70)
        logger.warning(
            f"You are about to RESYNC {len(selected_indices)} folder pair(s)."
        )
        logger.warning("This will COPY files and may cause duplicates!")
        logger.warning("=" * 70)

        response = input("\n⚠️  Do you want to proceed with --resync? [yes/NO]: ")
        if response.lower() not in ["yes", "y"]:
            logger.info("Resync cancelled by user.")
            return 0

        logger.info("")
        logger.info("=" * 70)
        logger.info("SELECTIVE BISYNC RESYNC - Production Run")
        logger.info("=" * 70)

        # Validate selected folder pairs
        logger.info("")
        logger.info("=" * 70)
        logger.info("Validating selected folder pairs...")
        logger.info("=" * 70)

        executor = CommandExecutor()
        validator = PathValidator(executor)

        validation_failed = False
        for idx in selected_indices:
            folder_pair = bisync_config.folders[idx]
            logger.info(f"\nValidating pair [{idx + 1}]:")
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
            logger.error("=" * 70)
            logger.error("❌ VALIDATION FAILED")
            logger.error("=" * 70)
            logger.error("Fix the issues above before running resync.")
            return 1

        logger.info("")
        logger.info("✅ All selected folder pairs validated successfully")

        # Create operation manager
        factory = OperationFactory(rclone_path=Path(common_config.rclone_path))
        bisync_manager = factory.create_bisync_manager(common_config, bisync_config)

        # Import RcloneOutputAnalyzer
        from rclone_wrapper.logging.output_analyzer import RcloneOutputAnalyzer
        from rclone_wrapper.core.command import CommandBuilder

        # RESYNC selected folders using RcloneOutputAnalyzer
        logger.info("")
        logger.info("=" * 70)
        logger.info("Starting RESYNC for selected folder pairs...")
        logger.info("=" * 70)
        logger.info("")

        success_count = 0
        failed_count = 0

        # Use RcloneOutputAnalyzer for batch processing
        with RcloneOutputAnalyzer(common_config.log_dir, session_name="selective_resync") as analyzer:
            for idx in selected_indices:
                folder_pair = bisync_config.folders[idx]
                logger.info(f"Resyncing pair [{idx + 1}]...")
                logger.info(f"  {folder_pair.source} <-> {folder_pair.destination}")

                try:
                    from datetime import datetime
                    start_time = datetime.now()

                    # Build command (same as bisync_all_stream)
                    builder = CommandBuilder(bisync_manager.rclone_path)
                    
                    # Merge filters
                    filters = bisync_manager._merge_filters(
                        bisync_config.filters,
                        folder_pair.filters,
                    )
                    builder = bisync_manager._apply_common_settings(builder, filters)
                    
                    # Build bisync command with resync
                    builder = bisync_manager._build_command(
                        builder,
                        source=folder_pair.source,
                        destination=folder_pair.destination,
                        resync=True,  # RESYNC MODE
                        force=False,
                        checksum=folder_pair.checksum if folder_pair.checksum is not None else bisync_config.checksum,
                    )
                    cmd = builder.build()

                    # Execute
                    result = bisync_manager.executor.execute(cmd)
                    complete_output = result.stdout + "\n" + result.stderr

                    # Add to analyzer
                    analyzer.add_output(
                        complete_output,
                        command_info={
                            "command": "bisync",
                            "source": folder_pair.source,
                            "destination": folder_pair.destination,
                            "resync": True,
                            "timestamp": start_time.isoformat(),
                            "returncode": result.returncode,
                        }
                    )

                    if result.returncode == 0:
                        logger.info(f"✓ Resync successful for pair [{idx + 1}]")
                        success_count += 1
                    else:
                        logger.error(f"✗ Resync failed for pair [{idx + 1}]")
                        failed_count += 1

                except Exception as e:
                    logger.error(f"❌ Exception during resync of pair [{idx + 1}]: {e}")
                    failed_count += 1
                    
                    # Add error to analyzer
                    analyzer.add_output(
                        f'{{"level":"error","msg":"Resync failed: {str(e)}","source":"selective_resync"}}',
                        command_info={
                            "command": "bisync",
                            "source": folder_pair.source,
                            "destination": folder_pair.destination,
                            "error": str(e),
                            "resync": True,
                        }
                    )

                logger.info("")

        # Report generated automatically by analyzer on context exit
        logger.info("Analysis report generated in logs directory")

        # Summary
        successful = success_count
        failed = failed_count
        total_synced = 0  # Will be in analyzer report

        logger.info("")
        logger.info("=" * 70)
        logger.info("SELECTIVE RESYNC SUMMARY")
        logger.info("=" * 70)
        logger.info("  Selected pairs: {len(selected_indices)}")
        logger.info(f"  Successful: {successful}")
        logger.info(f"  Failed: {failed}")
        logger.info(f"  Check analysis report for detailed operation counts")
        logger.info("")
        logger.info("=" * 70)

        if failed == 0:
            logger.info("✅ RESULT: ALL SELECTED PAIRS INITIALIZED SUCCESSFULLY")
            logger.info("")
            logger.info("Next steps:")
            logger.info("  1. Verify the sync results are correct")
            logger.info("  2. Use main_bisync.py for future normal syncs")
            logger.info("  3. Do NOT use --resync again unless necessary")
            logger.info("")
            if len(selected_indices) < len(bisync_config.folders):
                logger.info(
                    f"Note: {len(bisync_config.folders) - len(selected_indices)} "
                    "pair(s) were not resynced."
                )
            logger.info("=" * 70)
            return 0
        else:
            logger.error(f"❌ RESULT: {failed} PAIR(S) FAILED")
            logger.error("")
            logger.error(
                "Review the errors above and fix any issues before proceeding."
            )
            logger.info("=" * 70)
            return 1

    except Exception as e:
        logger.error(f"❌ CRITICAL ERROR: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
