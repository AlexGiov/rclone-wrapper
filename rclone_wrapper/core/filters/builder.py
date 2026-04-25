"""
Filter builder - Constructs rclone filter arguments.

This module handles the construction of filter arguments for rclone
commands based on FilterConfig settings.

Extracted from core.py to follow Single Responsibility Principle.
"""

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...config import FilterConfig

__all__ = ["FilterBuilder"]


class FilterBuilder:
    """
    Builds filter arguments for rclone commands.

    Takes FilterConfig and produces list of command-line arguments
    for rclone filtering options.

    Example:
        >>> from rclone_wrapper.config import FilterConfig
        >>> filters = FilterConfig(
        ...     exclude=['*.tmp', '*.bak'],
        ...     min_size='10M',
        ...     exclude_dirs=['.git', 'node_modules']
        ... )
        >>> builder = FilterBuilder(filters)
        >>> args = builder.build_args()
        >>> print(args)
        ['--exclude', '*.tmp', '--exclude', '*.bak', '--exclude', '.git/**',
         '--exclude', 'node_modules/**', '--min-size', '10M']
    """

    def __init__(self, filters: "FilterConfig"):
        """
        Initialize filter builder.

        Args:
            filters: Filter configuration
        """
        self.filters = filters

    def build_args(self) -> list[str]:
        """
        Build filter arguments for rclone command.

        Returns:
            List of filter arguments

        Example:
            >>> builder = FilterBuilder(config.filters)
            >>> args = builder.build_args()
        """
        args: list[str] = []

        # Exclude patterns
        for pattern in self.filters.exclude:
            args.extend(["--exclude", pattern.replace("\\", "/")])

        # Include patterns
        for pattern in self.filters.include:
            args.extend(["--include", pattern.replace("\\", "/")])

        # Exclude directories (automatically add /** for recursive exclusion)
        for dir_name in self.filters.exclude_dirs:
            args.extend(["--exclude", f"{dir_name}/**"])

        # Exclude if present
        if self.filters.exclude_if_present:
            args.extend(["--exclude-if-present", self.filters.exclude_if_present])

        # Size filters
        if self.filters.min_size:
            args.extend(["--min-size", self.filters.min_size])
        if self.filters.max_size:
            args.extend(["--max-size", self.filters.max_size])

        # Age filters
        if self.filters.min_age:
            args.extend(["--min-age", self.filters.min_age])
        if self.filters.max_age:
            args.extend(["--max-age", self.filters.max_age])

        # Filter from file
        if self.filters.filter_from:
            args.extend(["--filter-from", str(self.filters.filter_from)])

        # Case sensitivity
        if self.filters.ignore_case:
            args.append("--ignore-case")

        return args

    @staticmethod
    def merge_filters(
        base: "FilterConfig",
        override: "FilterConfig | None",
    ) -> "FilterConfig":
        """
        Merge two filter configurations.

        Combines base and override filters, with override taking precedence
        for singular values and both being combined for lists.

        Args:
            base: Base filter configuration
            override: Override filter configuration (can be None)

        Returns:
            Merged FilterConfig

        Example:
            >>> base = FilterConfig(exclude=['*.tmp'])
            >>> override = FilterConfig(exclude=['*.log'], min_size='10M')
            >>> merged = FilterBuilder.merge_filters(base, override)
            >>> merged.exclude
            ['*.tmp', '*.log']
            >>> merged.min_size
            '10M'
        """
        from ...config import FilterConfig

        if override is None:
            return base

        return FilterConfig(
            exclude=base.exclude + override.exclude,
            include=base.include + override.include,
            exclude_dirs=base.exclude_dirs + override.exclude_dirs,
            exclude_if_present=override.exclude_if_present or base.exclude_if_present,
            min_size=override.min_size or base.min_size,
            max_size=override.max_size or base.max_size,
            min_age=override.min_age or base.min_age,
            max_age=override.max_age or base.max_age,
            filter_from=override.filter_from or base.filter_from,
            ignore_case=override.ignore_case or base.ignore_case,
        )
