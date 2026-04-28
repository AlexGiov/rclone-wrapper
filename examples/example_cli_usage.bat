@echo off
REM ============================================================================
REM Example CLI Usage - rclone-wrapper
REM
REM This script demonstrates all available command-line interface commands.
REM Modify the --config-dir path and remote names according to your setup.
REM
REM NOTE: Global options (--dry-run, --verbose, --log-file, --rclone) MUST be
REM       placed BEFORE the subcommand name.
REM       Correct:   python ..\rclone-wrapper.py --dry-run sync --config-dir ...
REM       Incorrect: python ..\rclone-wrapper.py sync --config-dir ... --dry-run
REM ============================================================================

echo.
echo ============================================================================
echo rclone-wrapper CLI Examples
echo ============================================================================
echo.

REM Set config directory (change this to your actual config path)
set CONFIG_DIR=config_examples

echo ============================================================================
echo [1] Version information
echo ============================================================================
echo.
echo [1a] Show wrapper + rclone version (subcommand - queries rclone binary):
echo   python ..\rclone-wrapper.py info
echo.
python ..\rclone-wrapper.py info
echo.
echo [1b] Show wrapper version only (argparse built-in flag, does not call rclone):
echo   python ..\rclone-wrapper.py --version
echo.
python ..\rclone-wrapper.py --version
echo.
pause

echo.
echo ============================================================================
echo [2] Backup - Create ZIP archives and upload to remote
echo ============================================================================
echo.
echo Reads config from: %CONFIG_DIR%\backup_extended.json + %CONFIG_DIR%\common.json
echo.
echo [2a] Run backup (cleanup enabled by default):
echo   python ..\rclone-wrapper.py backup --config-dir %CONFIG_DIR%
echo.
REM Uncomment to run:
REM python ..\rclone-wrapper.py backup --config-dir %CONFIG_DIR%
echo.
echo [2b] Run backup skipping deletion of old archives:
echo   python ..\rclone-wrapper.py backup --config-dir %CONFIG_DIR% --no-cleanup
echo.
REM python ..\rclone-wrapper.py backup --config-dir %CONFIG_DIR% --no-cleanup
echo.
echo [2c] Dry run (no changes made, global flag BEFORE subcommand):
echo   python ..\rclone-wrapper.py --dry-run backup --config-dir %CONFIG_DIR%
echo.
REM python ..\rclone-wrapper.py --dry-run backup --config-dir %CONFIG_DIR%
echo (Remove REM from the desired line to execute)
echo.
pause

echo.
echo ============================================================================
echo [3] Sync - One-way sync to remote
echo ============================================================================
echo.
echo Reads config from: %CONFIG_DIR%\sync.json + %CONFIG_DIR%\common.json
echo.
echo [3a] Sync all pairs defined in sync.json:
echo   python ..\rclone-wrapper.py sync --config-dir %CONFIG_DIR%
echo.
REM python ..\rclone-wrapper.py sync --config-dir %CONFIG_DIR%
echo.
echo [3b] Override source/destination from command line (ignores sync.json pairs):
echo   python ..\rclone-wrapper.py sync --config-dir %CONFIG_DIR% --source "C:\local\folder" --dest "remote:bucket/path"
echo.
REM python ..\rclone-wrapper.py sync --config-dir %CONFIG_DIR% --source "C:\local\folder" --dest "remote:bucket/path"
echo.
echo [3c] Dry run:
echo   python ..\rclone-wrapper.py --dry-run sync --config-dir %CONFIG_DIR%
echo.
REM python ..\rclone-wrapper.py --dry-run sync --config-dir %CONFIG_DIR%
echo (Remove REM from the desired line to execute)
echo.
pause

echo.
echo ============================================================================
echo [4] Bisync - Bidirectional sync
echo ============================================================================
echo.
echo Reads config from: %CONFIG_DIR%\bisync.json + %CONFIG_DIR%\common.json
echo.
echo [4a] Run bisync for all pairs defined in bisync.json:
echo   python ..\rclone-wrapper.py bisync --config-dir %CONFIG_DIR%
echo.
REM python ..\rclone-wrapper.py bisync --config-dir %CONFIG_DIR%
echo.
echo [4b] First-time setup or force resync (rebuilds state):
echo   python ..\rclone-wrapper.py bisync --config-dir %CONFIG_DIR% --resync
echo.
REM python ..\rclone-wrapper.py bisync --config-dir %CONFIG_DIR% --resync
echo.
echo [4c] Override path1/path2 from command line (ignores bisync.json pairs):
echo   python ..\rclone-wrapper.py bisync --config-dir %CONFIG_DIR% --path1 "C:\local\folder" --path2 "remote:bucket/path"
echo.
REM python ..\rclone-wrapper.py bisync --config-dir %CONFIG_DIR% --path1 "C:\local\folder" --path2 "remote:bucket/path"
echo.
echo [4d] Dry run:
echo   python ..\rclone-wrapper.py --dry-run bisync --config-dir %CONFIG_DIR%
echo.
REM python ..\rclone-wrapper.py --dry-run bisync --config-dir %CONFIG_DIR%
echo (Remove REM from the desired line to execute)
echo.
pause

echo.
echo ============================================================================
echo [5] Compare - Compare local and remote directories
echo ============================================================================
echo.
echo Reads config from: %CONFIG_DIR%\compare.json + %CONFIG_DIR%\common.json
echo.
echo [5a] Compare all pairs defined in compare.json:
echo   python ..\rclone-wrapper.py compare --config-dir %CONFIG_DIR%
echo.
REM python ..\rclone-wrapper.py compare --config-dir %CONFIG_DIR%
echo.
echo [5b] Override local/remote from command line (ignores compare.json pairs):
echo   python ..\rclone-wrapper.py compare --config-dir %CONFIG_DIR% --local "C:\local\folder" --remote "remote:bucket/path"
echo.
REM python ..\rclone-wrapper.py compare --config-dir %CONFIG_DIR% --local "C:\local\folder" --remote "remote:bucket/path"
echo (Remove REM from the desired line to execute)
echo.
pause

echo.
echo ============================================================================
echo [6] Using as Python module (alternative syntax)
echo ============================================================================
echo.
echo You can also run commands using: python -m rclone_wrapper
echo The same global/subcommand option rules apply.
echo.
echo   python -m rclone_wrapper info
echo   python -m rclone_wrapper backup --config-dir %CONFIG_DIR%
echo   python -m rclone_wrapper backup --config-dir %CONFIG_DIR% --no-cleanup
echo   python -m rclone_wrapper --dry-run sync --config-dir %CONFIG_DIR%
echo   python -m rclone_wrapper bisync --config-dir %CONFIG_DIR% --resync
echo   python -m rclone_wrapper --verbose compare --config-dir %CONFIG_DIR%
echo.
pause

echo.
echo ============================================================================
echo [7] Global Options Reference
echo ============================================================================
echo.
echo Global options MUST come BEFORE the subcommand:
echo   python ..\rclone-wrapper.py [GLOBAL OPTIONS] ^<subcommand^> [SUBCOMMAND OPTIONS]
echo.
echo Global options:
echo   --config-dir PATH    Config directory (default: config_examples)
echo   --rclone PATH        Path to rclone executable (default: auto-detect)
echo   --dry-run, -n        Test run - no changes made
echo   --verbose, -v        Enable verbose console output
echo   --log-file PATH      Custom log file path (default: logs/rclone_wrapper.log)
echo   --version            Show wrapper version and exit (does NOT call rclone)
echo   --help, -h           Show help message
echo.
echo Subcommand-specific options:
echo   backup   : --no-cleanup
echo   sync     : --source LOCAL, --dest REMOTE
echo   bisync   : --resync, --path1 LOCAL, --path2 REMOTE
echo   compare  : --local FOLDER, --remote FOLDER
echo.
echo Examples:
echo   python ..\rclone-wrapper.py --dry-run --verbose backup --config-dir %CONFIG_DIR% --no-cleanup
echo   python ..\rclone-wrapper.py --log-file logs\sync.log sync --config-dir %CONFIG_DIR%
echo   python ..\rclone-wrapper.py --rclone "C:\tools\rclone.exe" bisync --config-dir %CONFIG_DIR% --resync
echo.
pause

echo.
echo ============================================================================
echo For detailed documentation, see:
echo   - examples/README.md (Python API usage)
echo   - README.md (Project overview)
echo   - config_examples/ (Configuration examples)
echo ============================================================================
echo.
pause
