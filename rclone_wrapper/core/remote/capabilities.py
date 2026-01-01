"""
Remote capabilities and path utilities.

This module handles remote-related operations:
- Checking remote capabilities (checksum support, features)
- Parsing and validating remote paths
- Caching remote information

Extracted from core.py to follow Single Responsibility Principle.
"""

import json
import logging
import subprocess
from pathlib import Path
from typing import Optional

from ...domain import RemotePath
from ...exceptions import RcloneError

__all__ = [
    "RemoteCapabilities",
    "is_remote_path",
    "parse_remote_path",
    "ensure_rclone",
]

logger = logging.getLogger(__name__)


def is_remote_path(path: str) -> bool:
    """
    Determine if a path is remote (rclone) or local.

    A remote rclone path has the format: remote_name:path/to/folder
    A local path can be:
    - Windows drive: C:\\path, D:\\path
    - UNC path: \\\\server\\share
    - Relative path: .\\folder, ../folder
    - Unix path: /mnt/folder

    Args:
        path: Path to check

    Returns:
        True if remote path (format remote:path), False if local

    Examples:
        >>> is_remote_path("agdrive:/documents")
        True
        >>> is_remote_path("C:\\Users\\data")
        False
        >>> is_remote_path("\\\\192.168.1.1\\share")
        False
    """
    path = path.strip()

    if ":" in path:
        # Check for Windows drive (single letter followed by :)
        if len(path) >= 2 and path[1] == ":" and path[0].isalpha():
            return False  # Windows drive (C:, D:, etc.)
        else:
            return True  # rclone remote:path format

    return False  # All other cases are local


def parse_remote_path(path: str) -> RemotePath | None:
    """
    Parse a string into RemotePath.

    Args:
        path: Path string in format 'remote:path' or local path

    Returns:
        RemotePath if path is remote, None if local

    Example:
        >>> parse_remote_path('gdrive:/documents')
        RemotePath(remote_name='gdrive', path='/documents')
        >>> parse_remote_path('C:\\Users\\data')
        None
    """
    return RemotePath.parse(path)


def ensure_rclone(rclone_path: Path | None = None) -> Path:
    """
    Ensure rclone executable is available.

    Args:
        rclone_path: Optional explicit path to rclone executable

    Returns:
        Path to rclone executable

    Raises:
        RcloneError: If rclone is not found
    """
    import shutil

    if rclone_path and rclone_path.exists():
        return rclone_path

    # Search in PATH
    rclone_exe = shutil.which("rclone")
    if rclone_exe:
        return Path(rclone_exe)

    # Common installation paths
    common_paths = [
        Path("C:/rclone/rclone.exe"),
        Path("C:/Program Files/rclone/rclone.exe"),
        Path("/usr/bin/rclone"),
        Path("/usr/local/bin/rclone"),
    ]

    for path in common_paths:
        if path.exists():
            return path

    raise RcloneError(
        "rclone executable not found. Please install rclone or specify path."
    )


class RemoteCapabilities:
    """
    Manages remote capabilities checking and caching.

    Queries rclone backends for features like checksum support,
    with caching to avoid repeated queries.

    Attributes:
        rclone_path: Path to rclone executable

    Example:
        >>> caps = RemoteCapabilities(Path('/usr/bin/rclone'))
        >>> if caps.supports_checksum('gdrive'):
        ...     print("Google Drive supports checksums")
    """

    def __init__(self, rclone_path: Path):
        """
        Initialize capabilities manager.

        Args:
            rclone_path: Path to rclone executable
        """
        self.rclone_path = rclone_path
        self._cache: dict[str, dict[str, any]] = {}

    def supports_checksum(self, remote_name: str) -> bool:
        """
        Check if a remote supports hash/checksum.

        Args:
            remote_name: Name of the remote (e.g., "agdrive")

        Returns:
            True if remote supports at least one hash type

        Raises:
            RcloneError: If unable to query remote capabilities

        Example:
            >>> caps = RemoteCapabilities(Path('/usr/bin/rclone'))
            >>> caps.supports_checksum('gdrive')
            True
        """
        # Check cache first
        if remote_name in self._cache:
            return self._cache[remote_name].get("has_hash", False)

        try:
            # Query remote features using rclone backend
            cmd = [str(self.rclone_path), "backend", "features", f"{remote_name}:"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )

            if result.returncode != 0:
                logger.warning(
                    f"Unable to query capabilities for remote '{remote_name}': "
                    f"{result.stderr}"
                )
                # Assume no hash support if query fails
                self._cache[remote_name] = {"has_hash": False}
                return False

            # Parse JSON output for hash support
            try:
                features = json.loads(result.stdout)
                hashes = features.get("Hashes", [])
                has_hash = bool(hashes)

                self._cache[remote_name] = {"has_hash": has_hash, "hashes": hashes}

                if has_hash:
                    logger.debug(
                        f"Remote '{remote_name}' supports hashes: {', '.join(hashes)}"
                    )
                else:
                    logger.debug(f"Remote '{remote_name}' does not support hashes")

                return has_hash

            except json.JSONDecodeError as e:
                logger.warning(
                    f"Failed to parse capabilities JSON for remote '{remote_name}': {e}"
                )
                self._cache[remote_name] = {"has_hash": False}
                return False

        except subprocess.TimeoutExpired:
            logger.warning(f"Timeout querying capabilities for remote '{remote_name}'")
            self._cache[remote_name] = {"has_hash": False}
            return False

        except Exception as e:
            logger.warning(
                f"Error querying capabilities for remote '{remote_name}': {e}"
            )
            self._cache[remote_name] = {"has_hash": False}
            return False

    def verify_checksum_support(
        self,
        path: str,
        operation_name: str = "operation",
    ) -> None:
        """
        Verify that a path's remote supports checksum.

        Raises error if checksum is not supported.

        Args:
            path: Path to check (must be remote path)
            operation_name: Name of operation for error message

        Raises:
            RcloneError: If path is remote but doesn't support checksum

        Example:
            >>> caps = RemoteCapabilities(Path('/usr/bin/rclone'))
            >>> caps.verify_checksum_support('gdrive:/docs', 'sync')
        """
        remote_path = parse_remote_path(path)

        if remote_path and not self.supports_checksum(remote_path.remote_name):
            raise RcloneError(
                f"Remote '{remote_path.remote_name}' does not support checksum/hash. "
                f"Cannot perform {operation_name} with checksum verification. "
                f"Either use a remote that supports hashing, or disable checksum option, "
                f"or enable 'download' option to calculate checksums locally."
            )

    def get_features(self, remote_name: str) -> dict[str, any]:
        """
        Get all features for a remote.

        Args:
            remote_name: Name of the remote

        Returns:
            Dictionary of remote features

        Example:
            >>> caps = RemoteCapabilities(Path('/usr/bin/rclone'))
            >>> features = caps.get_features('gdrive')
            >>> print(features.get('Hashes', []))
        """
        if remote_name not in self._cache:
            # Trigger capability check to populate cache
            self.supports_checksum(remote_name)

        return self._cache.get(remote_name, {})

    def clear_cache(self, remote_name: str | None = None) -> None:
        """
        Clear capability cache.

        Args:
            remote_name: Specific remote to clear, or None to clear all

        Example:
            >>> caps = RemoteCapabilities(Path('/usr/bin/rclone'))
            >>> caps.clear_cache('gdrive')  # Clear specific remote
            >>> caps.clear_cache()  # Clear all
        """
        if remote_name:
            self._cache.pop(remote_name, None)
        else:
            self._cache.clear()
