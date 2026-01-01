"""
Command builder - Fluent interface for building rclone commands.

This module implements the Builder Pattern for constructing rclone
commands in a readable, type-safe way.

Example:
    >>> from pathlib import Path
    >>> builder = CommandBuilder(Path('/usr/bin/rclone'))
    >>> cmd = (builder
    ...     .subcommand('sync')
    ...     .arguments('source/', 'dest/')
    ...     .log_level('INFO')
    ...     .dry_run()
    ...     .build())
    >>> cmd
    ['/usr/bin/rclone', 'sync', 'source/', 'dest/', '--log-level=INFO', '-n', '--dry-run']
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...domain import LogLevel

__all__ = ["CommandBuilder"]


@dataclass
class CommandBuilder:
    """
    Builder for rclone commands using fluent interface.

    Follows the Builder Pattern from Gang of Four design patterns.
    Provides a clean, readable way to construct complex rclone commands.

    Attributes:
        rclone_path: Path to rclone executable

    Example:
        >>> builder = CommandBuilder(Path('/usr/bin/rclone'))
        >>> cmd = (builder
        ...     .subcommand('sync')
        ...     .arguments('/data', 'remote:/backup')
        ...     .transfers(8)
        ...     .build())
    """

    rclone_path: Path
    _parts: list[str] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize with rclone executable path."""
        self._parts = [str(self.rclone_path)]

    def subcommand(self, cmd: str) -> CommandBuilder:
        """
        Add rclone subcommand.

        Args:
            cmd: Subcommand (sync, bisync, check, copy, etc.)

        Returns:
            Self for method chaining
        """
        self._parts.append(cmd)
        return self

    def arguments(self, *args: str) -> CommandBuilder:
        """
        Add positional arguments.

        Args:
            *args: Arguments (paths, etc.)

        Returns:
            Self for method chaining
        """
        self._parts.extend(args)
        return self

    def log_level(self, level: str | LogLevel) -> CommandBuilder:
        """
        Set log level.

        Args:
            level: Log level (DEBUG, INFO, NOTICE, ERROR) or LogLevel enum

        Returns:
            Self for method chaining
        """
        from ...domain import LogLevel

        if isinstance(level, LogLevel):
            level = level.value
        self._parts.append(f"--log-level={level}")
        return self

    def checkers(self, count: int) -> CommandBuilder:
        """
        Set number of file checkers.

        Args:
            count: Number of checkers (1-32)

        Returns:
            Self for method chaining
        """
        self._parts.append(f"--checkers={count}")
        return self

    def transfers(self, count: int) -> CommandBuilder:
        """
        Set number of parallel transfers.

        Args:
            count: Number of transfers (1-32)

        Returns:
            Self for method chaining
        """
        self._parts.append(f"--transfers={count}")
        return self

    def bandwidth_limit(self, limit: str | None) -> CommandBuilder:
        """
        Set bandwidth limit.

        Args:
            limit: Bandwidth limit (e.g., '10M', '1G') or None

        Returns:
            Self for method chaining
        """
        if limit:
            self._parts.append(f"--bwlimit={limit}")
        return self

    def timeout(self, seconds: int) -> CommandBuilder:
        """
        Set operation timeout.

        Args:
            seconds: Timeout in seconds

        Returns:
            Self for method chaining
        """
        self._parts.append(f"--timeout={seconds}s")
        return self

    def dry_run(self, enabled: bool = True) -> CommandBuilder:
        """
        Enable dry-run mode.

        Args:
            enabled: Whether to enable dry-run

        Returns:
            Self for method chaining
        """
        if enabled:
            self._parts.extend(["-n", "--dry-run"])
        return self

    def verbose(self, enabled: bool = True) -> CommandBuilder:
        """
        Enable verbose output.

        Args:
            enabled: Whether to enable verbose mode

        Returns:
            Self for method chaining
        """
        if enabled:
            self._parts.append("-v")
        return self

    def progress(self, enabled: bool = True) -> CommandBuilder:
        """
        Enable progress output.

        Args:
            enabled: Whether to show progress

        Returns:
            Self for method chaining
        """
        if enabled:
            self._parts.append("-P")
        return self

    def json_log(self, enabled: bool = True) -> CommandBuilder:
        """
        Enable JSON logging.

        Args:
            enabled: Whether to use JSON log format

        Returns:
            Self for method chaining
        """
        if enabled:
            self._parts.append("--use-json-log")
        return self

    def checksum(self, enabled: bool = True) -> CommandBuilder:
        """
        Enable checksum comparison.

        Args:
            enabled: Whether to use checksum

        Returns:
            Self for method chaining
        """
        if enabled:
            self._parts.append("--checksum")
        return self

    def size_only(self, enabled: bool = True) -> CommandBuilder:
        """
        Use size-only comparison.

        Args:
            enabled: Whether to use size-only comparison

        Returns:
            Self for method chaining
        """
        if enabled:
            self._parts.append("--size-only")
        return self

    def one_way(self, enabled: bool = True) -> CommandBuilder:
        """
        Enable one-way check mode.

        Args:
            enabled: Whether to use one-way mode

        Returns:
            Self for method chaining
        """
        if enabled:
            self._parts.append("--one-way")
        return self

    def download(self, enabled: bool = True) -> CommandBuilder:
        """
        Enable download mode for comparison.

        Args:
            enabled: Whether to download for comparison

        Returns:
            Self for method chaining
        """
        if enabled:
            self._parts.append("--download")
        return self

    def filters(self, filter_args: list[str]) -> CommandBuilder:
        """
        Add filter arguments.

        Args:
            filter_args: List of filter arguments

        Returns:
            Self for method chaining
        """
        self._parts.extend(filter_args)
        return self

    def extra_flags(self, flags: list[str]) -> CommandBuilder:
        """
        Add extra custom flags.

        Args:
            flags: List of additional flags

        Returns:
            Self for method chaining
        """
        self._parts.extend(flags)
        return self

    def flag(self, name: str, value: str | None = None) -> CommandBuilder:
        """
        Add a single flag with optional value.

        Args:
            name: Flag name (without --)
            value: Optional flag value

        Returns:
            Self for method chaining

        Example:
            >>> builder.flag('max-depth', '5')
            >>> builder.flag('delete-excluded')
        """
        if value is not None:
            self._parts.append(f"--{name}={value}")
        else:
            self._parts.append(f"--{name}")
        return self

    def build(self) -> list[str]:
        """
        Build and return the complete command.

        Returns:
            List of command arguments ready for subprocess
        """
        return self._parts.copy()

    def __str__(self) -> str:
        """Return command as a single string for logging."""
        return " ".join(self._parts)
