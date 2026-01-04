"""
Entry point for running rclone-wrapper as a module.

Usage:
    python -m rclone_wrapper backup
    python -m rclone_wrapper sync
    python -m rclone_wrapper bisync
    python -m rclone_wrapper compare
    python -m rclone_wrapper info
"""

import sys
from pathlib import Path

# Add parent directory to path to import rclone-wrapper.py
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

# Import main function from rclone-wrapper.py
import importlib.util
spec = importlib.util.spec_from_file_location("rclone_wrapper_cli", parent_dir / "rclone-wrapper.py")
cli_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli_module)

if __name__ == "__main__":
    sys.exit(cli_module.main())
