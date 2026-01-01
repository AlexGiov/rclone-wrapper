# Rclone Wrapper

**Professional Python wrapper for rclone with focus on backup, sync, and bidirectional sync operations**

Type-safe, robust wrapper for rclone with comprehensive error handling, retry logic, JSON log parsing, and advanced features for bisync, backup, and sync operations.

## ✨ Features

- **Type-Safe**: Full type hints with Pydantic validation
- **Robust Error Handling**: Comprehensive exception hierarchy with exit code mapping
- **Retry Logic**: Automatic retry with exponential backoff for transient errors
- **Bisync Support**: Full bidirectional sync with conflict detection and auto-resync
- **JSON Logging**: Structured log parsing with raw JSON log preservation
- **Backup Management**: ZIP archiving with retention policy
- **Flexible Logging**: Multi-level logging with file rotation
- **CLI Interface**: Complete command-line interface for all operations
- **Well-Tested**: Comprehensive test suite with 80%+ coverage

## 📋 Requirements

- **Python**: 3.11+
- **rclone**: 1.60.0+ ([download](https://rclone.org/downloads/))

## 🚀 Installation

```bash
# Clone repository
git clone https://github.com/yourusername/rclone-wrapper.git
cd rclone-wrapper

# Install dependencies
pip install -r requirements.txt

# Or install as package
pip install -e .
```

## 🎯 Quick Start

### Configuration

Create `config/backup.json`:

```json
{
  "remote": "gdrive",
  "dest_base": "Backup",
  "folders": ["D:/Documents", "D:/Photos"],
  "retention_days": 30,
  "log_level": "INFO"
}
```

### Basic Operations

```bash
# Backup folders to remote
python cli.py backup --config config/backup.json

# Sync folder to remote
python cli.py sync --local "D:/Projects" --remote "gdrive:Projects"

# Bidirectional sync (bisync)
python cli.py bisync --path1 "D:/Work" --path2 "gdrive:Work"

# Compare directories
python cli.py compare --local "D:/folder" --remote "gdrive:folder"
```

## 📖 Detailed Usage

### Backup Operation

Archive local folders and upload to remote with retention:

```bash
python cli.py backup \
    --config config/backup.json \
    --dry-run  # Preview only
```

**Features:**
- Creates ZIP archives locally
- Uploads to remote
- Maintains retention policy (deletes old backups)
- Preserves JSON logs for audit

### Sync Operation

One-way sync from local to remote:

```bash
python cli.py sync \
    --local "D:/Documents" \
    --remote "gdrive:Documents" \
    --delete  # Delete files on remote not present locally
```

**Features:**
- One-way synchronization
- Optional delete on destination
- Handles large file transfers
- Retry on transient errors

### Bisync Operation

Bidirectional sync with conflict detection:

```bash
# First run (creates baseline)
python cli.py bisync \
    --path1 "D:/Work" \
    --path2 "gdrive:Work" \
    --resync  # Force resync (first time or after changes)

# Subsequent runs (incremental sync)
python cli.py bisync \
    --path1 "D:/Work" \
    --path2 "gdrive:Work"
```

**Features:**
- Two-way synchronization
- Conflict detection and resolution
- Auto-resync on critical errors
- Preserves bisync state
- Backup of listing files

**Conflict Resolution:**
- Creates `.conflict` copies
- Preserves both versions
- Logs conflicts for review

### Compare Operation

Compare local and remote directories:

```bash
python cli.py compare \
    --local "D:/Documents" \
    --remote "gdrive:Documents" \
    --output comparison.json
```

**Output:**
```json
{
  "only_in_local": ["file1.txt", "folder/"],
  "only_in_remote": ["file2.txt"],
  "different": [
    {
      "path": "report.pdf",
      "local_size": 12345,
      "remote_size": 12340,
      "local_time": "2026-01-01T10:00:00",
      "remote_time": "2026-01-01T09:55:00"
    }
  ]
}
```

## 🔧 Advanced Usage

### Python API

```python
from rclone_wrapper.operations import BisyncOperation
from rclone_wrapper.config import Config

# Create config
config = Config(
    remote="gdrive",
    log_level="DEBUG",
    retry_max_attempts=3
)

# Run bisync
bisync = BisyncOperation(config)
result = bisync.execute(
    path1="D:/Work",
    path2="gdrive:Work",
    resync=False
)

if result.success:
    print(f"Synced successfully: {result.files_transferred} files")
else:
    print(f"Error: {result.error_message}")
```

### Error Handling

```python
from rclone_wrapper.exceptions import (
    RcloneException,
    BisyncConflictError,
    RetryableError
)

try:
    result = bisync.execute(path1="...", path2="...")
except BisyncConflictError as e:
    print(f"Conflicts detected: {e.conflicts}")
    # Handle conflicts
except RetryableError as e:
    print(f"Transient error (will retry): {e}")
except RcloneException as e:
    print(f"Fatal error: {e}")
```

### JSON Log Parsing

```python
from rclone_wrapper.logging import JSONLogParser

# Parse rclone JSON log
parser = JSONLogParser()
entries = parser.parse_file("logs/rclone_20260101.log")

# Analyze
errors = [e for e in entries if e.level == "error"]
transfers = [e for e in entries if e.stats]
```

## 📊 Configuration Reference

Full config example (`config/backup.json`):

```json
{
  "remote": "gdrive",
  "dest_base": "Backup",
  "folders": [
    "D:/Documents",
    "D:/Photos"
  ],
  "sync_folders": [
    {"local": "D:/Projects", "remote": "Projects"}
  ],
  "retention_days": 30,
  "log_level": "INFO",
  "rclone_path": "rclone",
  "retry_max_attempts": 3,
  "retry_initial_delay": 1.0,
  "retry_max_delay": 60.0,
  "retry_backoff_factor": 2.0
}
```

See [config_examples/](config_examples/) for more examples.

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=rclone_wrapper --cov-report=html

# Specific test
pytest tests/test_bisync.py -v
```

## 📁 Project Structure

```
rclone-wrapper/
├── rclone_wrapper/          # Main package
│   ├── core/               # Core executor and builder
│   ├── domain/             # Domain models and exceptions
│   ├── logging/            # JSON log parser
│   ├── operations/         # Bisync, sync, backup, compare
│   ├── config/             # Configuration management
│   └── utils.py
├── cli.py                  # Command-line interface
├── config_examples/        # Example configurations
├── tests/                  # Test suite
└── examples/               # Usage examples
```

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Ensure all tests pass
5. Submit Pull Request

## 📝 License

MIT License - see [LICENSE](LICENSE) file

## 🙏 Acknowledgments

- Built on top of excellent [rclone](https://rclone.org/) tool
- Inspired by real-world backup and sync requirements
- Follows Python best practices and SOLID principles

## 📧 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/rclone-wrapper/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/rclone-wrapper/discussions)
- **Documentation**: [Full docs](docs/)

---

**Made with ❤️ for reliable cloud backup and sync**
