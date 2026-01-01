"""
Path validation for bisync operations.

Validates paths before sync to prevent silent failures and provide
clear user feedback for common issues.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path

from ..config import FolderPair
from ..core.command import CommandExecutor

__all__ = ["PathValidator", "ValidationResult"]

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of path validation."""

    is_valid: bool = True
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    actions_taken: list[str] = field(default_factory=list)

    def add_issue(self, message: str) -> None:
        """Add a blocking issue."""
        self.issues.append(message)
        self.is_valid = False

    def add_warning(self, message: str) -> None:
        """Add a non-blocking warning."""
        self.warnings.append(message)

    def add_action(self, message: str) -> None:
        """Record an action taken."""
        self.actions_taken.append(message)


class PathValidator:
    """
    Validates paths before bisync operations.

    Checks for:
    - Path existence (local and remote)
    - Empty directories (potential unmounted drives)
    - Creates marker files for intentionally empty directories
    - Interactive prompts for user decisions
    """

    MARKER_FILENAME = ".rclone-keep"
    MARKER_CONTENT = """This directory is intentionally kept empty.
Created by rclone-wrapper to prevent sync errors.
Safe to delete if you add other files to this directory.
"""

    def __init__(self, executor: CommandExecutor) -> None:
        """
        Initialize path validator.

        Args:
            executor: Command executor for remote path checks
        """
        self.executor = executor

    def validate_folder_pair(
        self,
        folder_pair: FolderPair,
        create_missing: bool = False,
        allow_empty: bool = False,
        interactive: bool = True,
    ) -> ValidationResult:
        """
        Validate a folder pair before sync.

        Args:
            folder_pair: Folder pair to validate
            create_missing: Auto-create missing directories
            allow_empty: Allow empty directories without marker
            interactive: Ask user for decisions

        Returns:
            ValidationResult with status and actions
        """
        result = ValidationResult()

        # Check source path (Path1)
        self._validate_path(
            path=folder_pair.source,
            path_name="Source",
            is_remote=self._is_remote_path(folder_pair.source),
            folder_pair=folder_pair,
            create_missing=create_missing,
            allow_empty=allow_empty or folder_pair.allow_empty,
            interactive=interactive,
            result=result,
        )

        # Check destination path (Path2)
        self._validate_path(
            path=folder_pair.destination,
            path_name="Destination",
            is_remote=self._is_remote_path(folder_pair.destination),
            folder_pair=folder_pair,
            create_missing=create_missing,
            allow_empty=allow_empty or folder_pair.allow_empty,
            interactive=interactive,
            result=result,
        )

        return result

    def _validate_path(
        self,
        path: str,
        path_name: str,
        is_remote: bool,
        folder_pair: FolderPair,
        create_missing: bool,
        allow_empty: bool,
        interactive: bool,
        result: ValidationResult,
    ) -> None:
        """Validate a single path (source or destination)."""
        # Check existence
        exists = self._path_exists(path, is_remote)

        if not exists:
            if create_missing or (interactive and self._ask_create_missing(path)):
                try:
                    self._create_directory(path, is_remote)
                    result.add_action(f"Created missing directory: {path}")
                    exists = True
                except Exception as e:
                    result.add_issue(f"{path_name} creation failed for {path}: {e}")
                    return
            else:
                result.add_issue(f"{path_name} does not exist: {path}")
                return

        # Check if empty (only if exists)
        if exists:
            is_empty = self._is_empty(path, is_remote)

            if is_empty and not allow_empty:
                if interactive:
                    choice = self._ask_empty_dir_action(path)
                    if choice == "marker":
                        try:
                            self._create_marker_file(path, is_remote)
                            result.add_action(
                                f"Created marker file in empty {path_name.lower()}: {path}"
                            )
                        except Exception as e:
                            result.add_warning(
                                f"Could not create marker file in {path}: {e}"
                            )
                    elif choice == "continue":
                        result.add_warning(
                            f"{path_name} is empty but user chose to continue: {path}"
                        )
                    else:  # abort
                        result.add_issue(
                            f"{path_name} is empty (rejected by user): {path}"
                        )
                else:
                    result.add_issue(
                        f"{path_name} is empty (safety check): {path}\n"
                        f"  Possible unmounted drive or sync error.\n"
                        f"  Use --allow-empty flag or add files to proceed."
                    )

    def _is_remote_path(self, path: str) -> bool:
        """Check if path is a remote (contains ':')."""
        return ":" in path and not path.startswith("\\\\") and len(path) > 2

    def _path_exists(self, path: str, is_remote: bool) -> bool:
        """Check if path exists (local or remote)."""
        if is_remote:
            # Use rclone lsd to check remote directory
            try:
                remote, remote_path = path.split(":", 1)
                cmd = ["rclone", "lsd", path, "--max-depth", "1"]
                result = self.executor.execute(cmd)
                return result.returncode == 0
            except Exception as e:
                logger.debug(f"Remote path check failed for {path}: {e}")
                return False
        else:
            # Local path check
            return Path(path).exists()

    def _is_empty(self, path: str, is_remote: bool) -> bool:
        """Check if directory is empty."""
        if is_remote:
            # Use rclone lsf to list files
            try:
                cmd = ["rclone", "lsf", path, "--max-depth", "1"]
                result = self.executor.execute(cmd)
                # Empty if no output
                return result.returncode == 0 and not result.stdout.strip()
            except Exception as e:
                logger.debug(f"Remote empty check failed for {path}: {e}")
                return False
        else:
            # Local empty check
            local_path = Path(path)
            try:
                # Check if any files/dirs exist
                return not any(local_path.iterdir())
            except Exception as e:
                logger.debug(f"Local empty check failed for {path}: {e}")
                return False

    def _create_directory(self, path: str, is_remote: bool) -> None:
        """Create directory (local or remote)."""
        if is_remote:
            # Use rclone mkdir
            cmd = ["rclone", "mkdir", path]
            result = self.executor.execute(cmd)
            if result.returncode != 0:
                raise RuntimeError(f"Failed to create remote directory: {path}")
        else:
            # Local mkdir
            Path(path).mkdir(parents=True, exist_ok=True)

    def _create_marker_file(self, path: str, is_remote: bool) -> None:
        """Create marker file in empty directory."""
        import tempfile

        if is_remote:
            # Create temp file locally, then copy to remote
            with tempfile.NamedTemporaryFile(
                mode="w", delete=False, suffix=".txt"
            ) as f:
                f.write(self.MARKER_CONTENT)
                temp_path = f.name

            try:
                marker_remote_path = f"{path}/{self.MARKER_FILENAME}"
                cmd = ["rclone", "copyto", temp_path, marker_remote_path]
                result = self.executor.execute(cmd)
                if result.returncode != 0:
                    raise RuntimeError("rclone copyto failed")
            finally:
                Path(temp_path).unlink(missing_ok=True)
        else:
            # Local marker file
            marker_path = Path(path) / self.MARKER_FILENAME
            marker_path.write_text(self.MARKER_CONTENT, encoding="utf-8")

    def _ask_create_missing(self, path: str) -> bool:
        """Ask user if they want to create missing directory."""
        response = input(
            f"\n⚠️  Directory does not exist: {path}\n" f"   Create it now? [yes/NO]: "
        )
        return response.lower() in ["yes", "y"]

    def _ask_empty_dir_action(self, path: str) -> str:
        """Ask user what to do with empty directory."""
        print(f"\n⚠️  EMPTY DIRECTORY DETECTED: {path}")
        print("   This could indicate:")
        print("   • Unmounted network drive")
        print("   • Sync error or data loss")
        print("   • Intentionally empty directory")
        print()
        print("   Options:")
        print("   [M]arker - Create .rclone-keep file and continue")
        print("   [C]ontinue - Proceed without marker (risky)")
        print("   [A]bort - Stop validation (default)")
        print()

        response = input("   Your choice [M/C/A]: ").strip().lower()

        if response in ["m", "marker"]:
            return "marker"
        elif response in ["c", "continue"]:
            return "continue"
        else:
            return "abort"
