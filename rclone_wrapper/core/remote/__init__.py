"""
Remote utilities exports.

This module exports remote-related utilities.
"""

from .capabilities import (
    RemoteCapabilities,
    ensure_rclone,
    is_remote_path,
    parse_remote_path,
)

__all__ = [
    "RemoteCapabilities",
    "is_remote_path",
    "parse_remote_path",
    "ensure_rclone",
]
