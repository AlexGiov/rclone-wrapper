# Rclone Wrapper

**Professional Python wrapper for rclone with focus on backup, sync, and bidirectional sync operations**

Type-safe, robust wrapper for rclone with comprehensive error handling, retry logic, JSON log parsing, and advanced features for bisync, backup, and sync operations.

## ✨ Features

### Architecture
- **Modern Python 3.11+**: PEP 585/604 type hints, dataclasses, Protocol-based design
- **Domain-Driven Design**: Layered architecture (Domain, Core, Config, Operations, Logging)
- **SOLID Principles**: Single Responsibility, Dependency Injection, Open/Closed
- **Design Patterns**: Builder, Factory, Strategy, Template Method, Context Manager

### Operations
- **Backup Extended**: Multi-archive ZIP backup with individual retention policies
- **Sync**: One-way synchronization with filtering and error recovery
- **Bisync**: Bidirectional sync with conflict detection and auto-recovery
- **Compare**: Directory comparison for audit and verification

### Developer Experience
- **Type-Safe**: Full type hints with Pydantic 2.0+ validation
- **Comprehensive Logging**: RcloneOutputAnalyzer with JSON parsing and aggregated reports
- **CLI & API**: Three usage modes (direct script, module, installed command)
- **Interactive Examples**: Batch/shell scripts demonstrating all features
- **Extensive Documentation**: Working examples for all operations

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

### Interactive CLI Demo

**Windows:**
```bash
examples\example_cli_usage.bat
```

**Linux/macOS:**
```bash
chmod +x examples/example_cli_usage.sh
./examples/example_cli_usage.sh
```

### Configuration

Example configurations are provided in `config_examples/`. Copy and customize for your use:

```bash
mkdir config
cp config_examples/sync.json config/
cp config_examples/bisync.json config/
cp config_examples/backup_extended.json config/
```

### Three Ways to Use

**1. Direct Script (Easiest):**
```bash
python rclone-wrapper.py backup --config-dir config_examples
python rclone-wrapper.py sync --config-dir config_examples
python rclone-wrapper.py bisync --config-dir config_examples
python rclone-wrapper.py compare --config-dir config_examples
```

**2. Python Module (Standard):**
```bash
python -m rclone_wrapper backup --config-dir config_examples
python -m rclone_wrapper sync --config-dir config_examples --dry-run
```

**3. Installed Command (After `pip install .`):**
```bash
rclone-wrapper backup
rclone-wrapper sync --verbose
rclone-wrapper bisync --resync
```

## 📖 Detailed Usage

### Backup Operation (Extended)

Multi-archive backup with ZIP compression and retention policies:

```bash
python rclone-wrapper.py backup --config-dir config_examples
```

**Features:**
- Multiple independent archives with different retention
- ZIP compression (configurable levels 0-9)
- Merge multiple folders into single ZIP or separate ZIPs
- Automatic cleanup of old backups based on retention policy
- Global and per-archive filters
- Unified JSON reporting

**Configuration:** `config_examples/backup_extended.json`

See [examples/example_backup_extended.py](examples/example_backup_extended.py) for Python API usage.

### Sync Operation

One-way sync from local to remote:

```bash
python rclone-wrapper.py sync --config-dir config_examples
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
python rclone-wrapper.py bisync --config-dir config_examples --resync

# Subsequent runs (incremental sync)
python rclone-wrapper.py bisync --config-dir config_examples
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
python rclone-wrapper.py compare --config-dir config_examples
```

**Features:**
- Detects missing files (in both directions)
- Identifies modified files (size/time differences)
- One-way or two-way comparison
- Comprehensive JSON reports in `logs/`

**Configuration:** `config_examples/compare.json`

See [examples/example_compare.py](examples/example_compare.py) for Python API usage.

## 🔧 Advanced Usage

### Python API

```python
from pathlib import Path
from rclone_wrapper.config import ConfigLoader
from rclone_wrapper.core.command import CommandExecutor
from rclone_wrapper.operations import BisyncOperationManager

# Load configuration
loader = ConfigLoader(Path("config_examples"))
common_config, bisync_config = loader.load_bisync()

# Create executor and manager
executor = CommandExecutor()
manager = BisyncOperationManager(
    common_config=common_config,
    bisync_config=bisync_config,
    executor=executor
)

# Run bisync for all configured pairs
manager.bisync_all_stream()

# Or resync all
manager.resync_all()
```

See [examples/](examples/) for complete working examples.

### Error Handling

```python
from rclone_wrapper.exceptions import (
    RcloneError,
    RcloneCriticalError,
    RcloneRetryableError,
)

try:
    manager.bisync_all_stream()
except RcloneCriticalError as e:
    print(f"Critical error - resync needed: {e}")
    # Run resync
except RcloneRetryableError as e:
    print(f"Transient error (will auto-retry): {e}")
except RcloneError as e:
    print(f"Rclone error: {e}")
```

### Analyzing Reports

```python
import json
from pathlib import Path

# Read generated report
report_file = max(Path("logs").glob("*_analysis.json"))
with open(report_file) as f:
    report = json.load(f)

# Extract statistics
print(f"Session: {report['session_name']}")
print(f"Duration: {report['summary']['elapsed_time']}s")
print(f"Operations: {report['summary']['total_operations']}")
print(f"Errors: {report['summary']['errors']}")

# Check specific operations
for cmd in report['commands']:
    print(f"{cmd['command']}: {cmd['source']} -> {cmd['destination']}")
```

## 📊 Configuration

All operations use JSON configuration files. Examples are provided in `config_examples/`:

- **`common.json`** - Shared settings (remote, log level, transfers, etc.)
- **`sync.json`** - One-way sync configuration
- **`bisync.json`** - Bidirectional sync with conflict resolution
- **`compare.json`** - Directory comparison settings
- **`backup_extended.json`** - Multi-archive backup with retention

See [config_examples/CONFIG_REFERENCE.md](config_examples/CONFIG_REFERENCE.md) for complete documentation.

**Quick Example** (`config/sync.json`):
```json
{
  "remote": "gdrive",
  "log_dir": "logs",
  "log_level": "INFO",
  "folders": [
    {
      "source": "D:/Documents",
      "destination": "gdrive:Backup/Documents"
    },
    {
      "source": "D:/Photos",
      "destination": "gdrive:Backup/Photos"
    }
  ]
}
```

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
├── rclone_wrapper/              # Main package
│   ├── config/                  # Configuration layer (Pydantic models)
│   ├── core/                    # Core layer (CommandBuilder, Executor)
│   ├── domain/                  # Domain layer (models, enums, value objects)
│   ├── logging/                 # Logging layer (parsers, formatters, analyzer)
│   ├── operations/              # Operations layer (managers for sync/bisync/compare)
│   ├── backup_extended.py       # Backup extended operation manager
│   ├── exceptions.py            # Exception hierarchy
│   └── __main__.py              # Module entry point
├── rclone-wrapper.py            # CLI entry point (direct execution)
├── config_examples/             # Example configurations + reference docs
├── examples/                    # Working examples (Python + CLI demos)
├── tests/                       # Test suite
└── pyproject.toml               # Project configuration
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
