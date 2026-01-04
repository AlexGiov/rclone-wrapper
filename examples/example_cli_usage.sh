#!/bin/bash
# ============================================================================
# Example CLI Usage - rclone-wrapper
# 
# This script demonstrates all available command-line interface commands.
# Modify the --config-dir path and remote names according to your setup.
# ============================================================================

echo ""
echo "============================================================================"
echo "rclone-wrapper CLI Examples"
echo "============================================================================"
echo ""

# Set config directory (change this to your actual config path)
CONFIG_DIR="config_examples"

echo "[1] Show version information"
echo "Command: python ../rclone-wrapper.py info"
echo ""
python ../rclone-wrapper.py info
echo ""
read -p "Press Enter to continue..."

echo ""
echo "============================================================================"
echo "[2] Backup - Create ZIP archives and upload to remote"
echo "Command: python ../rclone-wrapper.py backup --config-dir $CONFIG_DIR"
echo ""
echo "Note: Add --no-cleanup to skip old backup deletion"
echo "      Add --dry-run to test without making changes"
echo ""
# Uncomment to run:
# python ../rclone-wrapper.py backup --config-dir "$CONFIG_DIR"
echo "(Commented out - uncomment to execute)"
echo ""
read -p "Press Enter to continue..."

echo ""
echo "============================================================================"
echo "[3] Sync - One-way sync to remote"
echo "Command: python ../rclone-wrapper.py sync --config-dir $CONFIG_DIR"
echo ""
echo "Syncs all configured folder pairs from config_examples/sync.json"
echo ""
# Uncomment to run:
# python ../rclone-wrapper.py sync --config-dir "$CONFIG_DIR"
echo "(Commented out - uncomment to execute)"
echo ""
read -p "Press Enter to continue..."

echo ""
echo "============================================================================"
echo "[4] Bisync - Bidirectional sync"
echo "Command: python ../rclone-wrapper.py bisync --config-dir $CONFIG_DIR"
echo ""
echo "For first-time setup, use --resync:"
echo "python ../rclone-wrapper.py bisync --config-dir $CONFIG_DIR --resync"
echo ""
# Uncomment to run:
# python ../rclone-wrapper.py bisync --config-dir "$CONFIG_DIR"
echo "(Commented out - uncomment to execute)"
echo ""
read -p "Press Enter to continue..."

echo ""
echo "============================================================================"
echo "[5] Compare - Compare local and remote directories"
echo "Command: python ../rclone-wrapper.py compare --config-dir $CONFIG_DIR"
echo ""
echo "Shows differences between configured folder pairs"
echo ""
# Uncomment to run:
# python ../rclone-wrapper.py compare --config-dir "$CONFIG_DIR"
echo "(Commented out - uncomment to execute)"
echo ""
read -p "Press Enter to continue..."

echo ""
echo "============================================================================"
echo "[6] Using as Python module (alternative syntax)"
echo ""
echo "You can also run commands using: python -m rclone_wrapper"
echo ""
echo "Examples:"
echo "  python -m rclone_wrapper info"
echo "  python -m rclone_wrapper backup --config-dir $CONFIG_DIR"
echo "  python -m rclone_wrapper sync --config-dir $CONFIG_DIR --dry-run"
echo "  python -m rclone_wrapper bisync --config-dir $CONFIG_DIR --resync"
echo "  python -m rclone_wrapper compare --config-dir $CONFIG_DIR --verbose"
echo ""
read -p "Press Enter to continue..."

echo ""
echo "============================================================================"
echo "[7] Common Options"
echo "============================================================================"
echo ""
echo "--config-dir PATH    : Specify config directory (default: config_examples)"
echo "--rclone PATH        : Path to rclone executable (default: auto-detect)"
echo "--dry-run, -n        : Test run without making changes"
echo "--verbose, -v        : Enable verbose console output"
echo "--log-file PATH      : Custom log file path"
echo "--version            : Show version information"
echo "--help, -h           : Show help message"
echo ""
echo "Example with options:"
echo "  python ../rclone-wrapper.py sync --config-dir $CONFIG_DIR --dry-run --verbose"
echo ""
read -p "Press Enter to continue..."

echo ""
echo "============================================================================"
echo "For detailed documentation, see:"
echo "  - examples/README.md (Python API usage)"
echo "  - README.md (Project overview)"
echo "  - config_examples/ (Configuration examples)"
echo "============================================================================"
echo ""
