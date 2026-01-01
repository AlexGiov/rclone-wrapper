"""
Parser strategy base - ABC for parsing strategies.

Defines the interface for different parsing strategies (JSON, text, etc.)
following the Strategy Pattern.
"""

from abc import ABC, abstractmethod

from ...domain import ParsedData

__all__ = ["ParserStrategy"]


class ParserStrategy(ABC):
    """
    Abstract base class for parsing strategies.
    
    Different parsers (JSON, text) implement this interface to provide
    consistent parsing of rclone output.
    
    Following Strategy Pattern from Gang of Four.
    """

    @abstractmethod
    def parse(
        self,
        stdout: str,
        stderr: str,
        returncode: int,
        command: str,
    ) -> ParsedData:
        """
        Parse rclone command output.
        
        Args:
            stdout: Standard output from rclone
            stderr: Standard error from rclone
            returncode: Exit code
            command: Command that was executed (sync, bisync, check, etc.)
            
        Returns:
            ParsedData with extracted information
            
        Raises:
            RcloneParseError: If parsing fails
        """
        ...

    @abstractmethod
    def can_parse(self, stdout: str, stderr: str) -> bool:
        """
        Check if this parser can handle the output.
        
        Args:
            stdout: Standard output
            stderr: Standard error
            
        Returns:
            True if this parser can parse the output
        """
        ...
