"""
Core layer - Infrastructure components.

This package contains core infrastructure components that interact
with external systems (rclone executable, filesystem, etc.).

Components are organized by responsibility:
- command: Building and executing rclone commands
- remote: Remote capabilities and path handling
- filters: Filter management and building
"""

from .command import CommandBuilder, CommandExecutor
from .filters import FilterBuilder
from .remote import RemoteCapabilities, is_remote_path, parse_remote_path

__all__ = [
    # Command
    "CommandBuilder",
    "CommandExecutor",
    # Filters
    "FilterBuilder",
    # Remote
    "RemoteCapabilities",
    "is_remote_path",
    "parse_remote_path",
]
