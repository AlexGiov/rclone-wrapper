"""
Protocols for command system - PEP 544 structural subtyping.

Protocols define interfaces using structural typing (duck typing with type checking).
This allows for flexible implementations while maintaining type safety.

Following PEP 544 best practices:
- @runtime_checkable for isinstance() checks
- Protocol instead of ABC for structural typing
- Clear, minimal interface definitions
"""

from typing import Protocol, runtime_checkable

from ...domain import ParsedData

__all__ = [
    "CommandBuilderProtocol",
    "CommandExecutorProtocol",
]


@runtime_checkable
class CommandBuilderProtocol(Protocol):
    """
    Protocol for rclone command builders.

    Implementations must provide methods to build rclone commands
    with various options using a fluent interface.
    """

    def build(self) -> list[str]:
        """
        Build and return the complete command as list of strings.

        Returns:
            Complete command arguments list
        """
        ...


@runtime_checkable
class CommandExecutorProtocol(Protocol):
    """
    Protocol for command executors.

    Implementations must be able to execute commands and return results.
    """

    def execute(
        self,
        cmd: list[str],
        timeout: int | None = None,
    ) -> "CommandResult":
        """
        Execute a command.

        Args:
            cmd: Command arguments list
            timeout: Optional timeout in seconds

        Returns:
            Command execution result

        Raises:
            RcloneError: If command execution fails
        """
        ...


# Supporting dataclass for command results
from dataclasses import dataclass


@dataclass
class CommandResult:
    """
    Result of command execution.

    Attributes:
        returncode: Process exit code
        stdout: Standard output
        stderr: Standard error
        success: Whether command succeeded (returncode == 0)
        parsed_data: Optional parsed data from output
    """

    returncode: int
    stdout: str
    stderr: str
    success: bool
    parsed_data: ParsedData | None = None
