# Examples

Complete usage examples demonstrating the rclone-wrapper API and CLI for different operations.

## 🚀 Quick Start

### Command-Line Interface (CLI)

For quick demonstrations of CLI usage:

**Windows:**
```bash
examples\example_cli_usage.bat
```

**Linux/macOS:**
```bash
chmod +x examples/example_cli_usage.sh
./examples/example_cli_usage.sh
```

### Python API Examples

For programmatic usage and advanced customization, see the Python scripts below.

---

## 📋 Available Examples

### 1. **example_sync.py** - One-Way Synchronization

One-way sync from local to remote with optional deletion of files not present at source.

**Use Case:**
- Backup local folders to cloud storage
- Mirror local directory to remote
- Keep remote in sync with local changes

**Configuration:** `config_examples/sync.json`

```bash
python examples/example_sync.py
```

**Features:**
- Syncs all configured folder pairs
- Automatic JSON log parsing and reporting
- Exit code handling for automation

---

### 2. **example_bisync.py** - Bidirectional Synchronization

Bidirectional sync keeping both local and remote in sync with conflict detection.

**Use Case:**
- Sync work folders across multiple machines
- Keep local and cloud storage synchronized
- Collaborative folder synchronization

**Configuration:** `config_examples/bisync.json`

```bash
python examples/example_bisync.py
```

**Features:**
- Two-way synchronization
- Automatic conflict resolution
- Path validation before sync
- Critical error detection (resync needed)

---

### 3. **example_bisync_resync_selective.py** - Selective Resync

Initialize or force-resync specific folder pairs without affecting others.

**Use Case:**
- First-time setup of bisync for specific folders
- Recovery from bisync critical errors on specific pairs
- Reinitialize after manual changes outside bisync

**Configuration:** `config_examples/bisync.json`

```bash
python examples/example_bisync_resync_selective.py
```

**Features:**
- Interactive selection of folder pairs to resync
- Non-interactive mode for automation
- Safety warnings and confirmations
- Granular control over which pairs to initialize

⚠️ **WARNING:** Resync copies files bidirectionally, which means:
- Deleted files will reappear
- Renamed files will be duplicated
- All differences will be resolved by copying

---

### 4. **example_compare.py** - Directory Comparison

Compare local and remote directories to detect differences without making changes.

**Use Case:**
- Audit differences before syncing
- Verify backup integrity
- Detect missing or modified files

**Configuration:** `config_examples/compare.json`

```bash
python examples/example_compare.py
```

**Features:**
- Detects missing files (in both directions)
- Identifies modified files
- Dry-run analysis without changes
- Detailed comparison report

---

### 5. **example_backup_extended.py** - Multi-Archive Backup with Retention

Advanced backup solution with ZIP compression, multiple archives, and retention policies.

**Use Case:**
- Backup multiple folder sets with different retention
- Create compressed archives before upload
- Automatic cleanup of old backups
- Enterprise backup workflows

**Configuration:** `config_examples/backup_extended.json`

```bash
python examples/example_backup_extended.py
```

**Features:**
- ZIP compression (configurable levels 0-9)
- Multiple independent archives
- Individual retention policies per archive
- Merge multiple folders into single ZIP or separate ZIPs
- Automatic old backup cleanup
- Global and per-archive filters

⚠️ **Note:** Archives are created locally, then uploaded and deleted after successful transfer.

---

## 🚀 Getting Started

### Prerequisites

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Install rclone:**
   - Download from [rclone.org](https://rclone.org/downloads/)
   - Ensure `rclone` is in your PATH or configure path in config files

3. **Configure rclone remote:**
   ```bash
   rclone config
   ```
   Create a remote (e.g., `gdrive`, `onedrive`, `s3`)

### Configuration

Copy and customize configuration files from `config_examples/`:

```bash
# Create your own config directory
mkdir config

# Copy example configs
cp config_examples/sync.json config/sync.json
cp config_examples/bisync.json config/bisync.json
cp config_examples/compare.json config/compare.json
```

Edit configuration files to match your setup:
- Update `remote` with your rclone remote name
- Set correct local paths in `folder_pairs`
- Adjust `log_level`, `transfers`, and other settings

### Running Examples

Each example script expects configuration in the default `config/` directory:

```bash
# Sync example
python examples/example_sync.py

# Bisync example
python examples/example_bisync.py

# Compare example
python examples/example_compare.py

# Selective resync
python examples/example_bisync_resync_selective.py
```

---

## 📊 Output and Logs

All examples generate:

1. **Console output**: Real-time operation progress
2. **JSON logs**: Structured logs in `logs/` directory
3. **Analysis reports**: Detailed JSON reports with statistics

### Log Files

```
logs/
├── 20260103_143022_sync_session_raw.jsonl       # Raw rclone output
├── 20260103_143022_sync_session_analysis.json   # Parsed report
└── rclone_wrapper.log                           # Application logs
```

### Report Structure

```json
{
  "session_name": "sync_session",
  "timestamp": "2026-01-03T14:30:22",
  "commands": [...],
  "summary": {
    "total_files": 150,
    "copied_files": 12,
    "deleted_files": 3,
    "total_size": 524288000,
    "elapsed_time": 45.2
  },
  "errors": [...]
}
```

---

## 🔧 Exit Codes

All examples use consistent exit codes for automation:

| Code | Meaning |
|------|---------|
| `0` | Success (check report for details) |
| `1` | Critical error occurred |
| `2` | Configuration error |
| `3` | Bisync requires resync |

Use in scripts:

```bash
python examples/example_sync.py
if [ $? -eq 0 ]; then
    echo "Sync completed successfully"
else
    echo "Sync failed"
fi
```

---

## 💡 Best Practices

### Sync Operations
- Test with `dry_run: true` first
- Review logs after first run
- Use `delete_mode: "during"` for large syncs

### Bisync Operations
- **Always run resync on first use** for each folder pair
- Run bisync regularly (daily/hourly) to minimize conflicts
- Monitor logs for conflict warnings
- Use `resilient: true` for unreliable connections

### Compare Operations
- Use before major sync operations
- Verify backups periodically
- Audit changes before syncing

### General
- Keep configurations in version control (exclude sensitive data)
- Monitor log directories for disk usage
- Use log rotation for long-running deployments
- Test configurations with dry-run mode

---

## 🐛 Troubleshooting

### "Bisync critical error: prior run failed"
Run selective resync for affected folder pair:
```bash
python examples/example_bisync_resync_selective.py
```

### "Remote not found"
Check rclone configuration:
```bash
rclone listremotes
rclone config show <remote_name>
```

### "Permission denied"
Verify:
- Local folder permissions
- Remote authentication
- Rclone remote configuration

### High memory usage
Reduce parallel operations in config:
```json
{
  "transfers": 4,
  "checkers": 4
}
```

---

## 📚 Related Documentation

- [Configuration Reference](../config_examples/CONFIG_REFERENCE.md)
- [Main README](../README.md)
- [rclone Documentation](https://rclone.org/docs/)

---

## 🤝 Contributing

Found an issue or have an improvement? Examples are meant to demonstrate best practices. If you find a better approach, please submit a PR!
