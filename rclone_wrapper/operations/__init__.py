"""
Operations layer - Business logic for rclone operations.

This package contains operation managers that coordinate
command building, execution, and logging for different
types of rclone operations.

All managers inherit from BaseOperationManager and use
dependency injection for testability.
"""

from .base import BaseOperationManager
from .bisync import BisyncOperationManager
from .compare import CompareOperationManager
from .factory import OperationFactory
from .sync import SyncOperationManager
from .validators import PathValidator, ValidationResult

__all__ = [
    # Base
    "BaseOperationManager",
    # Managers
    "SyncOperationManager",
    "BisyncOperationManager",
    "CompareOperationManager",
    # Factory
    "OperationFactory",
    # Validators
    "PathValidator",
    "ValidationResult",
]
