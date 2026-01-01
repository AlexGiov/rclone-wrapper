"""
RcloneOutputAnalyzer - Context manager for analyzing rclone command outputs.

Provides a session-based approach to collecting and analyzing rclone outputs.
Completely independent from operation types (sync, bisync, compare).

Usage:
    with RcloneOutputAnalyzer(log_dir, session_name="my_session") as analyzer:
        # Execute rclone commands
        result1 = subprocess.run(['rclone', 'sync', ...], capture_output=True)
        analyzer.add_output(result1.stderr.decode())
        
        result2 = subprocess.run(['rclone', 'check', ...], capture_output=True)
        analyzer.add_output(result2.stderr.decode())
        
        # On exit, automatically:
        # 1. Closes raw file
        # 2. Parses offline
        # 3. Generates JSON report

Example:
    >>> from pathlib import Path
    >>> with RcloneOutputAnalyzer(Path('logs')) as analyzer:
    ...     analyzer.add_output('{"level":"info","msg":"Copied file.txt",...}')
    ...     analyzer.add_output('{"level":"info","msg":"Deleted old.txt",...}')
    >>> # Report generated at logs/20251229_143022_rclone_session_analysis.json
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, TextIO, List, Dict, Any

from .offline_parser import RcloneOfflineParser, CommandSession


logger = logging.getLogger(__name__)


class RcloneOutputAnalyzer:
    """
    Context manager for analyzing rclone command outputs.
    
    Aggregates outputs from multiple rclone commands into a single session,
    performs offline parsing, and generates unified analysis report.
    
    This component is completely independent from operations (sync, bisync, etc.)
    and can be used with ANY rclone command.
    
    Attributes:
        output_dir: Directory for raw output and analysis report
        session_name: Optional session name (default: timestamp)
    """
    
    def __init__(
        self,
        output_dir: Path,
        session_name: Optional[str] = None
    ):
        """
        Initialize analyzer.
        
        Args:
            output_dir: Directory for raw output and analysis report
            session_name: Optional session name (default: "rclone_session")
        """
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        
        self._session_name = session_name or "rclone_session"
        self._raw_file: Optional[Path] = None
        self._file_handle: Optional[TextIO] = None
        self._start_time: Optional[datetime] = None
        self._command_count = 0
    
    def __enter__(self) -> 'RcloneOutputAnalyzer':
        """
        Enter context - open raw output file.
        
        Returns:
            Self for use in with statement
        """
        self._start_time = datetime.now()
        timestamp = self._start_time.strftime("%Y%m%d_%H%M%S")
        
        filename = f"{timestamp}_{self._session_name}_raw.jsonl"
        self._raw_file = self._output_dir / filename
        self._file_handle = self._raw_file.open('w', encoding='utf-8')
        
        logger.info(f"📊 RcloneOutputAnalyzer session started: {self._raw_file}")
        return self
    
    def add_output(
        self,
        rclone_output: str,
        command_info: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add output from a rclone command execution.
        
        Args:
            rclone_output: Raw stderr/stdout from rclone (JSON lines format)
            command_info: Optional metadata about the command (for debugging)
        
        Raises:
            RuntimeError: If called outside context manager
        
        Example:
            >>> analyzer.add_output(
            ...     result.stderr.decode(),
            ...     command_info={
            ...         "command": "sync",
            ...         "source": "local/path",
            ...         "destination": "remote:path"
            ...     }
            ... )
        """
        if self._file_handle is None:
            raise RuntimeError(
                "Analyzer not initialized - use within 'with' statement"
            )
        
        self._command_count += 1
        
        # Optional: Add separator/metadata between commands
        if command_info:
            separator = {
                "analyzer_meta": True,
                "command_number": self._command_count,
                "timestamp": datetime.now().isoformat(),
                **command_info
            }
            self._file_handle.write(json.dumps(separator) + '\n')
        
        # Write raw rclone output
        self._file_handle.write(rclone_output)
        if not rclone_output.endswith('\n'):
            self._file_handle.write('\n')
        
        self._file_handle.flush()  # Ensure written to disk
        logger.debug(f"Added output from rclone command #{self._command_count}")
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit context - close file, parse offline, generate report.
        
        Args:
            exc_type: Exception type (if any)
            exc_val: Exception value (if any)
            exc_tb: Exception traceback (if any)
        
        Returns:
            False to propagate exceptions
        """
        # Always close file handle
        if self._file_handle:
            self._file_handle.close()
            logger.debug(f"Raw file closed: {self._raw_file}")
        
        # Only generate report if no exception occurred
        if exc_type is None and self._raw_file and self._raw_file.exists():
            try:
                self._generate_analysis_report()
            except Exception as e:
                logger.error(
                    f"Failed to generate analysis report: {e}",
                    exc_info=True
                )
        elif exc_type is not None:
            logger.warning(
                f"Session ended with exception, skipping analysis: "
                f"{exc_type.__name__}"
            )
        
        return False  # Don't suppress exceptions
    
    def _generate_analysis_report(self) -> Path:
        """
        Parse raw file offline and generate unified analysis report.
        
        Returns:
            Path to generated report JSON
        """
        logger.info(f"🔍 Parsing session raw file: {self._raw_file}")
        
        # Use offline parser (completely independent!)
        parser = RcloneOfflineParser(self._raw_file)
        sessions = parser.parse()  # Returns List[CommandSession]
        
        total_ops = sum(len(s.operations) for s in sessions)
        logger.info(
            f"Identified {total_ops} logical operations in session"
        )
        
        # Generate unified report
        report = self._create_report(sessions)
        
        # Save report
        timestamp = self._start_time.strftime("%Y%m%d_%H%M%S")
        report_filename = f"{timestamp}_{self._session_name}_analysis.json"
        report_path = self._output_dir / report_filename
        
        report_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
        
        logger.info(f"✅ Analysis report generated: {report_path}")
        return report_path
    
    def _create_report(self, sessions: List) -> Dict[str, Any]:
        """
        Create unified analysis report from parsed command sessions.
        
        This report is INDEPENDENT of operation type (sync/bisync/compare).
        It reports operations grouped by command execution.
        
        Args:
            sessions: List of CommandSession objects
        
        Returns:
            Report dictionary
        """
        end_time = datetime.now()
        duration = (end_time - self._start_time).total_seconds()
        
        # Build commands array
        commands = []
        for session in sessions:
            # Aggregate by operation type for this command
            ops_by_type = {}
            for op in session.operations:
                ops_by_type[op.type] = ops_by_type.get(op.type, 0) + 1
            
            # Aggregate by object type
            ops_by_object_type = {}
            for op in session.operations:
                obj_type = op.objectType or "unknown"
                ops_by_object_type[obj_type] = ops_by_object_type.get(obj_type, 0) + 1
            
            # Aggregate by direction
            ops_by_direction = {}
            for op in session.operations:
                if op.direction:
                    ops_by_direction[op.direction] = ops_by_direction.get(op.direction, 0) + 1
            
            commands.append({
                "command_info": {
                    "command_number": session.metadata.get("command_number"),
                    "timestamp": session.metadata.get("timestamp"),
                    "command": session.metadata.get("command"),
                    "source": session.metadata.get("source"),
                    "destination": session.metadata.get("destination"),
                    "resync": session.metadata.get("resync"),
                    "returncode": session.metadata.get("returncode"),
                },
                "summary": {
                    "total_operations": len(session.operations),
                    "operations_by_type": ops_by_type,
                    "operations_by_object_type": ops_by_object_type,
                    "operations_by_direction": ops_by_direction,
                },
                "operations": [
                    {
                        "type": op.type,
                        "object": op.object,
                        "size": op.size,
                        "timestamp": op.timestamp,
                        "msg": op.msg,
                        "objectType": op.objectType,
                        "direction": op.direction,
                        # Conflict-specific fields
                        **({"error": op.error} if op.error else {}),
                        **({"winner": op.winner} if op.winner else {}),
                        # Update-specific fields
                        **({"old_size": op.old_size} if op.old_size else {}),
                        **({"new_size": op.new_size} if op.new_size else {}),
                    }
                    for op in session.operations
                ],
            })
        
        return {
            "session_info": {
                "start_time": self._start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_seconds": round(duration, 2),
                "commands_executed": self._command_count,
                "session_name": self._session_name,
            },
            "commands": commands,
        }
