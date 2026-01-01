"""
Command executor - Executes rclone commands with error handling.

This module handles the actual execution of rclone commands using
subprocess, with proper error handling and exit code interpretation.

Following Single Responsibility Principle - this class only executes
commands, it doesn't build them or parse results.
"""

import logging
import subprocess
from typing import Optional

from ...domain import ExitCode
from ...exceptions import (
    RcloneCriticalError,
    RcloneError,
    RcloneRetryableError,
    RcloneTimeoutError,
)
from .protocol import CommandResult

__all__ = ["CommandExecutor"]

# Module logger
logger = logging.getLogger(__name__)

# Default timeout (1 hour)
DEFAULT_TIMEOUT = 3600


class CommandExecutor:
    """
    Executes rclone commands with proper error handling.

    Implements CommandExecutorProtocol using subprocess.
    Handles exit codes and raises appropriate exceptions.

    Attributes:
        default_timeout: Default timeout for commands in seconds

    Example:
        >>> executor = CommandExecutor(default_timeout=1800)
        >>> cmd = ['rclone', 'sync', 'source', 'dest']
        >>> result = executor.execute(cmd)
        >>> if result.success:
        ...     print("Sync completed")
    """

    def __init__(self, default_timeout: int = DEFAULT_TIMEOUT):
        """
        Initialize executor.

        Args:
            default_timeout: Default timeout in seconds
        """
        self.default_timeout = default_timeout

    def execute(
        self,
        cmd: list[str],
        timeout: int | None = None,
        env: dict[str, str] | None = None,
    ) -> CommandResult:
        """
        Execute a command.

        Args:
            cmd: Command arguments list
            timeout: Optional timeout in seconds (uses default if None)
            env: Optional environment variables

        Returns:
            CommandResult with execution details

        Raises:
            RcloneTimeoutError: If command times out
            RcloneCriticalError: For critical errors (exit code 7)
            RcloneRetryableError: For retryable errors (exit code 1)
            RcloneError: For other errors

        Example:
            >>> executor = CommandExecutor()
            >>> result = executor.execute(['rclone', 'version'])
            >>> print(result.stdout)
        """
        if timeout is None:
            timeout = self.default_timeout

        # Log command (but not full env for security)
        logger.info(f"Executing: {' '.join(cmd)}")
        logger.debug(f"Timeout: {timeout}s")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",  # Replace invalid chars instead of crashing
                check=False,
                timeout=timeout,
                env=env,
            )

            # Create CommandResult
            cmd_result = CommandResult(
                returncode=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                success=result.returncode == ExitCode.SUCCESS,
            )

            # Handle exit codes
            if result.returncode == ExitCode.SUCCESS:
                logger.debug("Command completed successfully")
                return cmd_result

            elif result.returncode == ExitCode.ERROR:
                logger.warning(f"Retryable error (exit {result.returncode})")
                raise RcloneRetryableError(
                    "Rclone command failed (retryable)",
                    exit_code=result.returncode,
                    stderr=result.stderr,
                )

            elif result.returncode == ExitCode.CRITICAL:
                logger.error(f"Critical error (exit {result.returncode})")
                raise RcloneCriticalError(
                    "Critical error - bisync may require --resync",
                    exit_code=result.returncode,
                    stderr=result.stderr,
                )

            else:
                logger.error(f"Command failed with exit code {result.returncode}")
                raise RcloneError(
                    f"Rclone command failed with exit code {result.returncode}",
                    exit_code=result.returncode,
                    stderr=result.stderr,
                )

        except subprocess.TimeoutExpired as e:
            logger.error(f"Command timed out after {timeout}s")
            raise RcloneTimeoutError(
                f"Command timed out after {timeout}s",
                timeout=timeout,
            ) from e

        except (RcloneError, RcloneRetryableError, RcloneCriticalError):
            # Re-raise rclone exceptions
            raise

        except Exception as e:
            # Wrap unexpected exceptions
            logger.exception("Unexpected error executing command")
            raise RcloneError(f"Unexpected error executing command: {e}") from e

    def execute_with_retry(
        self,
        cmd: list[str],
        retries: int = 3,
        timeout: int | None = None,
        backoff_base: float = 2.0,
    ) -> CommandResult:
        """
        Execute command with automatic retry on retryable errors.

        Args:
            cmd: Command arguments list
            retries: Number of retry attempts
            timeout: Optional timeout per attempt
            backoff_base: Exponential backoff base multiplier

        Returns:
            CommandResult from successful execution

        Raises:
            Last exception if all retries fail

        Example:
            >>> executor = CommandExecutor()
            >>> result = executor.execute_with_retry(
            ...     ['rclone', 'sync', 'source', 'dest'],
            ...     retries=3
            ... )
        """
        import random
        import time

        last_exception: Exception | None = None

        for attempt in range(retries):
            try:
                return self.execute(cmd, timeout=timeout)

            except RcloneRetryableError as e:
                last_exception = e
                if attempt < retries - 1:
                    # Calculate backoff with jitter
                    base_delay = backoff_base**attempt
                    jitter = random.uniform(0, base_delay * 0.1)
                    delay = base_delay + jitter

                    logger.warning(
                        f"Attempt {attempt + 1}/{retries} failed: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"All {retries} attempts failed")

            except (RcloneCriticalError, RcloneTimeoutError, RcloneError):
                # Don't retry critical errors or timeouts
                raise

        # This should not be reached, but just in case
        if last_exception:
            raise last_exception
        raise RcloneError("Retry logic failed unexpectedly")
