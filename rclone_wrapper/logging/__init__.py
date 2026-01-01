"""
Logging layer - Structured logging and parsing.

This package provides a unified logging architecture that:
- Parses rclone output (JSON and text)
- Creates unified operation logs
- Manages log files and batch operations
- Provides extensible parsing strategies
"""

from .capture import RawInputCapture
from .formatters import BatchLogFormatter
from .offline_parser import CommandSession, LogicalOperation, RcloneOfflineParser
from .output_analyzer import RcloneOutputAnalyzer
from .parsers import ParserStrategy
from .protocol import LogWriterProtocol

__all__ = [
    # Protocols
    "LogWriterProtocol",
    # Parsers
    "ParserStrategy",
    # Offline Analysis
    "RcloneOfflineParser",
    "CommandSession",
    "LogicalOperation",
    "RcloneOutputAnalyzer",
    # Formatters
    "BatchLogFormatter",
    # Capture
    "RawInputCapture",
]
