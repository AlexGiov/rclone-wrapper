"""
Batch log formatter - Aggregates multiple operation logs.

Provides functionality to combine multiple individual operation logs
into a single batch summary log.
"""

import logging
from datetime import datetime

from ...domain import (
    FileOperation,
    FileState,
    OperationTiming,
    TransferStats,
    UnifiedOperationLog,
)

__all__ = ["BatchLogFormatter"]

logger = logging.getLogger(__name__)


class BatchLogFormatter:
    """
    Formatter for batch operation logs.
    
    Aggregates multiple individual operation logs into a single
    summary log with combined statistics.
    
    Example:
        >>> formatter = BatchLogFormatter()
        >>> batch_log = formatter.aggregate_logs(
        ...     operation_type='batch_sync',
        ...     logs=[log1, log2, log3],
        ...     start_time=start,
        ...     end_time=end
        ... )
    """

    def aggregate_logs(
        self,
        operation_type: str,
        logs: list[UnifiedOperationLog],
        start_time: datetime,
        end_time: datetime,
        extra_params: dict | None = None,
    ) -> UnifiedOperationLog:
        """
        Aggregate multiple logs into a batch summary.
        
        Args:
            operation_type: Type of batch operation
            logs: Individual operation logs
            start_time: Batch start time
            end_time: Batch end time
            extra_params: Extra parameters
            
        Returns:
            Aggregated UnifiedOperationLog
        """
        # Calculate duration
        duration = (end_time - start_time).total_seconds()
        
        if not logs:
            # Empty batch - return minimal log
            return UnifiedOperationLog(
                operation_type=operation_type,
                timestamp_start=start_time.isoformat(),
                timestamp_end=end_time.isoformat(),
                duration_seconds=duration,
                source_path="batch",
                destination_path="",
                total_operations=0,
                errors=0,
                metadata=extra_params or {},
            )
        
        # Aggregate statistics from individual logs
        total_operations = sum(log.total_operations for log in logs)
        total_source_modified = sum(log.source_modified for log in logs)
        total_dest_modified = sum(log.destination_modified for log in logs)
        total_conflicts = sum(log.conflicts for log in logs)
        total_errors = sum(log.errors for log in logs)
        
        # Collect all operations from individual logs
        all_operations: list[FileOperation] = []
        for log in logs:
            all_operations.extend(log.operations)
        
        # Aggregate file_operations from individual logs (Opzione B+)
        aggregated_file_operations = {
            "copied": [],
            "deleted": [],
            "updated": [],
            "renamed": [],
            "errors": []
        }
        
        for log in logs:
            if not log.file_operations:
                continue
            
            # Merge each category
            for category in ["copied", "deleted", "updated", "renamed", "errors"]:
                if category in log.file_operations:
                    aggregated_file_operations[category].extend(
                        log.file_operations[category]
                    )
        
        # Remove empty categories
        aggregated_file_operations = {
            k: v for k, v in aggregated_file_operations.items() if v
        }
        
        # Build folder_pairs metadata for batch operations
        folder_pairs = []
        for log in logs:
            pair_info = {
                "source": log.source_path,
                "destination": log.destination_path,
                "operations": log.total_operations,
                "errors": log.errors,
            }
            if log.duration_seconds:
                pair_info["duration"] = log.duration_seconds
            folder_pairs.append(pair_info)
        
        # Merge extra_params with folder_pairs
        metadata = extra_params or {}
        metadata["folder_pairs"] = folder_pairs
        
        return UnifiedOperationLog(
            operation_type=operation_type,
            timestamp_start=start_time.isoformat(),
            timestamp_end=end_time.isoformat(),
            duration_seconds=duration,
            source_path="batch",
            destination_path="",
            total_operations=total_operations,
            source_modified=total_source_modified,
            destination_modified=total_dest_modified,
            conflicts=total_conflicts,
            errors=total_errors,
            operations=all_operations if len(all_operations) < 1000 else [],  # Limit operations in batch
            file_operations=aggregated_file_operations,  # Include aggregated file operations
            metadata=metadata,
        )

