"""
Raw input capture for debugging and testing.

Saves raw rclone output to .raw files before parsing, enabling:
1. Debug without re-running rclone
2. Regression testing with real data
3. Parser development and validation
4. Audit trail
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class RawCaptureConfig:
    """Configuration for raw input capture."""
    
    enabled: bool = True
    base_dir: Path = Path("logs/raw")
    keep_days: Optional[int] = 30  # Auto-cleanup after N days (None = keep forever)
    compress: bool = False  # Future: compress old .raw files


class RawInputCapture:
    """
    Captures and saves raw rclone output for debugging and testing.
    
    File naming: YYYYMMDD_HHMMSS_<operation>_<pair_index>.raw
    
    Example:
        >>> capture = RawInputCapture(base_dir=Path("logs/raw"))
        >>> capture.save_raw_output(
        ...     output="rclone json output...",
        ...     operation="bisync",
        ...     source="path1",
        ...     dest="path2",
        ...     timestamp=datetime.now()
        ... )
        Path("logs/raw/20251228_143022_bisync_0.raw")
    """
    
    def __init__(self, config: Optional[RawCaptureConfig] = None):
        """
        Initialize raw input capture.
        
        Args:
            config: Configuration for capture behavior
        """
        self.config = config or RawCaptureConfig()
        
        if self.config.enabled:
            self.config.base_dir.mkdir(parents=True, exist_ok=True)
    
    def save_raw_output(
        self,
        output: str,
        operation: str,
        timestamp: datetime,
        source: str = "",
        dest: str = "",
        pair_index: int = 0,
    ) -> Optional[Path]:
        """
        Save raw rclone output to .raw file.
        
        Args:
            output: Raw output from rclone (stdout+stderr)
            operation: Operation type (sync, bisync, compare)
            timestamp: Operation timestamp
            source: Source path (optional)
            dest: Destination path (optional)
            pair_index: Index of folder pair (for batch operations)
        
        Returns:
            Path to saved .raw file, or None if capture disabled
        """
        if not self.config.enabled:
            return None
        
        # Generate filename: YYYYMMDD_HHMMSS_<operation>_<pair_index>.raw
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp_str}_{operation}_{pair_index}.raw"
        raw_file = self.config.base_dir / filename
        
        # Create metadata header (JSON Lines format)
        metadata = {
            "timestamp": timestamp.isoformat(),
            "operation": operation,
            "source": source,
            "destination": dest,
            "pair_index": pair_index,
        }
        
        # Write metadata + raw output
        with raw_file.open("w", encoding="utf-8") as f:
            # First line: metadata (JSON)
            f.write(json.dumps(metadata) + "\n")
            # Separator
            f.write("--- RAW OUTPUT ---\n")
            # Raw output (può essere NDJSON da rclone)
            f.write(output)
        
        return raw_file
    
    def load_raw_output(self, raw_file: Path) -> tuple[dict, str]:
        """
        Load raw output from .raw file.
        
        Args:
            raw_file: Path to .raw file
        
        Returns:
            Tuple of (metadata dict, raw output string)
        
        Example:
            >>> capture = RawInputCapture()
            >>> metadata, output = capture.load_raw_output(
            ...     Path("logs/raw/20251228_143022_bisync_0.raw")
            ... )
            >>> metadata["operation"]
            'bisync'
        """
        with raw_file.open("r", encoding="utf-8") as f:
            lines = f.readlines()
        
        # First line: metadata JSON
        metadata = json.loads(lines[0])
        
        # Skip separator line (--- RAW OUTPUT ---)
        # Rest: raw output
        raw_output = "".join(lines[2:])
        
        return metadata, raw_output
    
    def list_raw_files(
        self,
        operation: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> list[Path]:
        """
        List all .raw files matching criteria.
        
        Args:
            operation: Filter by operation type (sync, bisync, etc.)
            start_date: Filter files after this date
            end_date: Filter files before this date
        
        Returns:
            List of matching .raw file paths
        """
        if not self.config.enabled:
            return []
        
        all_files = sorted(self.config.base_dir.glob("*.raw"))
        
        # Filter by operation
        if operation:
            all_files = [f for f in all_files if f"_{operation}_" in f.name]
        
        # Filter by date (parse from filename)
        if start_date or end_date:
            filtered = []
            for file in all_files:
                # Extract timestamp from filename: YYYYMMDD_HHMMSS_...
                try:
                    date_str = file.stem.split("_")[0] + file.stem.split("_")[1]
                    file_date = datetime.strptime(date_str, "%Y%m%d%H%M%S")
                    
                    if start_date and file_date < start_date:
                        continue
                    if end_date and file_date > end_date:
                        continue
                    
                    filtered.append(file)
                except (ValueError, IndexError):
                    continue  # Skip malformed filenames
            
            all_files = filtered
        
        return all_files
    
    def cleanup_old_files(self) -> int:
        """
        Delete .raw files older than keep_days.
        
        Returns:
            Number of files deleted
        """
        if not self.config.enabled or self.config.keep_days is None:
            return 0
        
        cutoff_date = datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        cutoff_date = cutoff_date.replace(day=cutoff_date.day - self.config.keep_days)
        
        old_files = self.list_raw_files(end_date=cutoff_date)
        
        for file in old_files:
            file.unlink()
        
        return len(old_files)
