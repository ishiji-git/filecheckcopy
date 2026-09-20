<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ishiji-git. All rights reserved. -->

# filecheckcopy

> Initial version generated with GitHub Copilot Free.

filecheckcopy is a Windows-based Python utility that copies only changed files between directories. It compares file content and metadata, supports dry-run, logging, parallel processing, and progress output, and preserves empty folders.

## Overview

This tool copies files from a source location to a target location while skipping unchanged content. It compares file size, timestamps when requested, and file hashes to decide whether a copy is needed, making it suitable for backup and synchronization workflows where only real changes should be transferred.

Typical use cases:

- Avoid unnecessary copying during large backup operations
- Reduce write overhead on NAS or remote-mounted storage
- Update only the changed portion of an existing backup set

## Features

- Designed for Windows-based systems
- Works with Python 3
- Supports both files and directories as input
- Recursively scans directories when a folder is specified
- Preserves empty directories
- Skips copying when file contents are identical even if timestamps differ
- Uses a hash value for content comparison
- Supports `--skip-same-mtime` to skip files when size and timestamp are the same
- Supports `--dry-run` to preview actions without writing files
- Supports `--exclude-dir` and `--exclude-file` to ignore specific paths or names when explicitly configured
- No default exclusion rules are enforced; exclusions must be specified by the user
- Supports `--log-file` to record copy activity to a file, including start/end timestamps and elapsed time
- Supports `--parallel` to process files with multiple worker threads
- Supports `--progress` to show overall progress while processing files

## Usage

### 1. Basic usage

```bash
python filecheckcopy.py source_dir target_dir
```

### 2. Preview without copying

```bash
python filecheckcopy.py source_dir target_dir --dry-run --verbose
```

### 3. Skip files whose timestamps are already identical

```bash
python filecheckcopy.py source_dir target_dir --skip-same-mtime
```

### 4. Exclude specific directories or files explicitly

```bash
python filecheckcopy.py source_dir target_dir --exclude-dir .git --exclude-dir .svn --exclude-file Thumbs.db
```

This behavior is only active when the exclusion options are explicitly provided.

### 5. Save activity to a log file

```bash
python filecheckcopy.py source_dir target_dir --log-file C:\logs\filecheckcopy.log
```

The log file records the start timestamp, each copy/skip action, and the final end timestamp with elapsed time in a compact format.

Example log snippet:

```text
Operation started: [2026-09-20 12:34:56] C:\backup-src -> C:\backup-dst
Copying: C:\backup-src\a.txt -> C:\backup-dst\a.txt
Skipped (unchanged): C:\backup-src\b.txt
Operation completed: [2026-09-20 12:34:57] Elapsed: 0.123s
Result: copied=1, skipped=1
```

### 6. Use parallel copying

```bash
python filecheckcopy.py source_dir target_dir --parallel 4 --verbose
```

### 7. Show progress while copying

```bash
python filecheckcopy.py source_dir target_dir --progress --parallel 4
```

### 8. Copy a single file

```bash
python filecheckcopy.py C:\src\a.txt C:\dst\
```

## Copy decision logic

The tool decides whether to copy a file in the following order:

1. If the target file does not exist, copy it
2. If the file size differs, copy it
3. If `--skip-same-mtime` is enabled and the timestamps match, skip it
4. If the hash values differ, copy it
5. Otherwise, skip it

## Example execution

```bash
python filecheckcopy.py C:\backup-src C:\backup-dst --dry-run --verbose --log-file C:\logs\copy.log --parallel 2
```

Example output:

```text
Copying: C:\backup-src\a.txt -> C:\backup-dst\a.txt
Skipped (unchanged): C:\backup-src\b.txt
Files copied: 1
Files skipped: 1
```

The same content is also appended to the log file.

## Notes

- The tool uses `MD5` for hashing
- Hash collisions are not a major concern for this project, so speed and simplicity are prioritized
- On Windows, file attributes and timestamps are preserved as far as the platform allows
- `--parallel` performs file-level parallelism; it is especially effective in I/O-bound environments

## Development notes

The test suite is located in `tests/test_filecheckcopy.py`.

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

Covered scenarios:

- Only changed files are copied
- `--skip-same-mtime` works correctly
- `--dry-run` does not write files
- `--log-file` produces output
- `--parallel` works safely
