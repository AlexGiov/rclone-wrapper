"""
Logging protocols - PEP 544 structural typing for logging system.

Defines interfaces for log writers using Protocol pattern,
allowing for flexible implementations while maintaining type safety.
"""

from pathlib import Path
from typing import Protocol, runtime_checkable

from ..domain import UnifiedOperationLog

__all__ = ["LogWriterProtocol"]


@runtime_checkable
class LogWriterProtocol(Protocol):
    """
    Protocol for log writers.
    
    Implementations must be able to write both individual operation logs
    and batch operation logs to persistent storage.
    
    Example:
        >>> class FileLogWriter:
        ...     def write_operation_log(self, log: UnifiedOperationLog) -> Path:
        ...         # Write individual operation log
        ...         pass
        ...
        ...     def write_batch_log(self, log: UnifiedOperationLog) -> Path:
        ...         # Write batch operation log
        ...         pass
    """

    def write_operation_log(self, log: UnifiedOperationLog) -> Path:
        """
        Write an individual operation log.
        
        Args:
            log: Unified operation log to write
            
        Returns:
            Path to written log file
        """
        ...

    def write_batch_log(self, log: UnifiedOperationLog) -> Path:
        """
        Write a batch operation log.
        
        Args:
            log: Batch unified operation log
            
        Returns:
            Path to written batch log file
        """
        ...
