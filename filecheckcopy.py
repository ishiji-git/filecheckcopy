#!/usr/bin/env python3

"""
filecheckcopy.py - Incremental file copy utility with content comparison

Copyright (c) 2026 ishiji-git. All rights reserved.
SPDX-License-Identifier: MIT
"""

import argparse
import ctypes
import fnmatch
import hashlib
import os
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="Copy only changed files between directories.")
    parser.add_argument("source", help="Source file or directory")
    parser.add_argument("target", help="Target file or directory")
    parser.add_argument("--exclude-dir", action="append", default=[], help="Directory name or pattern to exclude")
    parser.add_argument("--exclude-file", action="append", default=[], help="File name or pattern to exclude")
    parser.add_argument("--skip-same-mtime", action="store_true", help="Skip copy when size and timestamp are the same")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be copied without writing files")
    parser.add_argument("--verbose", action="store_true", help="Print verbose output")
    parser.add_argument("--progress", action="store_true", help="Display progress while copying files")
    parser.add_argument("--log-file", default=None, help="Write copy operations to a log file")
    parser.add_argument("--parallel", type=int, default=1, help="Number of worker threads to use for file copy processing")
    return parser.parse_args()


def normalize_excludes(items):
    return {item.strip().lower() for item in items if item and item.strip()}


def should_exclude_path(path, exclude_dirs, exclude_files):
    name = os.path.basename(path).lower()
    dir_name = os.path.basename(os.path.dirname(path)).lower()

    if name in exclude_dirs or dir_name in exclude_dirs:
        return True
    if name in exclude_files:
        return True

    for pattern in exclude_dirs:
        if fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(dir_name, pattern):
            return True
    for pattern in exclude_files:
        if fnmatch.fnmatch(name, pattern):
            return True
    return False


def compute_file_hash(path):
    digest = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def same_mtime(src_stat, dst_stat):
    return src_stat.st_mtime_ns == dst_stat.st_mtime_ns


def restore_windows_attributes(src_path, dst_path):
    if os.name != "nt":
        return

    kernel32 = ctypes.windll.kernel32
    INVALID_FILE_ATTRIBUTES = -1

    def get_attrs(path):
        attrs = kernel32.GetFileAttributesW(path)
        if attrs == INVALID_FILE_ATTRIBUTES:
            return 0
        return attrs

    src_attrs = get_attrs(str(src_path))
    if src_attrs == 0:
        return

    kernel32.SetFileAttributesW(str(dst_path), src_attrs)


def set_file_timestamps(src_path, dst_path):
    src_stat = os.stat(src_path)
    try:
        os.utime(dst_path, (src_stat.st_atime, src_stat.st_mtime), follow_symlinks=False)
    except (TypeError, NotImplementedError, OSError):
        os.utime(dst_path, (src_stat.st_atime, src_stat.st_mtime))


def should_copy_file(src_path, dst_path, skip_same_mtime):
    if not os.path.exists(dst_path):
        return True

    src_stat = os.stat(src_path)
    dst_stat = os.stat(dst_path)

    if src_stat.st_size != dst_stat.st_size:
        return True

    if skip_same_mtime and same_mtime(src_stat, dst_stat):
        return False

    return compute_file_hash(src_path) != compute_file_hash(dst_path)


def log_message(message, log_file=None, verbose=False):
    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        with open(log_file, "a", encoding="utf-8") as fh:
            fh.write(message + "\n")
    if verbose:
        print(message)


def copy_file(src_path, dst_path, skip_same_mtime=False, dry_run=False, verbose=False, log_file=None):
    if not should_copy_file(src_path, dst_path, skip_same_mtime):
        if verbose or log_file:
            log_message(f"Skipped (unchanged): {src_path}", log_file, verbose)
        return False

    if verbose or log_file:
        log_message(f"Copying: {src_path} -> {dst_path}", log_file, verbose)

    if dry_run:
        return True

    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    shutil.copy2(src_path, dst_path)
    set_file_timestamps(src_path, dst_path)
    restore_windows_attributes(src_path, dst_path)
    return True


def format_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def copy_tree(source_dir, target_dir, exclude_dirs=None, exclude_files=None, skip_same_mtime=False, dry_run=False, verbose=False, log_file=None, parallel=1, progress=False):
    ex_dirs = normalize_excludes(set(exclude_dirs or []))
    ex_files = normalize_excludes(set(exclude_files or []))

    source_root = Path(source_dir)
    target_root = Path(target_dir)
    copied_count = 0
    skipped_count = 0
    start_time = time.perf_counter()

    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        with open(log_file, "a", encoding="utf-8") as fh:
            fh.write(f"Operation started: [{format_timestamp()}] {source_root} -> {target_root}\n")

    if source_root.is_file():
        relative_name = source_root.name
        target_path = target_root if target_root.suffix else target_root / relative_name
        if target_root.exists() and target_root.is_dir():
            target_path = target_root / source_root.name
        if not dry_run and not target_root.parent.exists():
            target_root.parent.mkdir(parents=True, exist_ok=True)
        if should_exclude_path(str(source_root), ex_dirs, ex_files):
            return 0, 0
        copied = copy_file(str(source_root), str(target_path), skip_same_mtime, dry_run, verbose, log_file)
        return (1, 0) if copied else (0, 1)

    file_jobs = []
    for root, dirs, files in os.walk(source_root, topdown=True):
        dirs[:] = [d for d in dirs if not should_exclude_path(os.path.join(root, d), ex_dirs, ex_files)]
        for d in dirs:
            dst_dir = Path(root).relative_to(source_root)
            target_dir_path = target_root / dst_dir / d
            if dry_run:
                if verbose:
                    log_message(f"Create directory: {target_dir_path}", log_file)
                continue
            target_dir_path.mkdir(parents=True, exist_ok=True)

        for file_name in files:
            src_path = Path(root) / file_name
            if should_exclude_path(str(src_path), ex_dirs, ex_files):
                continue

            rel_path = src_path.relative_to(source_root)
            dst_path = target_root / rel_path
            file_jobs.append((str(src_path), str(dst_path), skip_same_mtime, dry_run, verbose, log_file))

    total_files = len(file_jobs)
    if progress and total_files:
        print(f"Total files: {total_files}")

    worker_count = max(1, int(parallel))
    if worker_count == 1:
        for index, (src_path, dst_path, skip_flag, dry_flag, verbose_flag, log_path) in enumerate(file_jobs, start=1):
            if progress and total_files:
                print(f"Progress: {index}/{total_files}")
            result = copy_file(src_path, dst_path, skip_flag, dry_flag, verbose_flag, log_path)
            if progress and total_files:
                status = "COPY" if result else "SKIP"
                print(f"{status}: {src_path}")
            if result:
                copied_count += 1
            else:
                skipped_count += 1
    else:
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = [
                executor.submit(copy_file, src_path, dst_path, skip_same_mtime, dry_run, verbose, log_file)
                for src_path, dst_path, skip_same_mtime, dry_run, verbose, log_file in file_jobs
            ]
            for index, future in enumerate(futures, start=1):
                if progress and total_files:
                    print(f"Progress: {index}/{total_files}")
                result = future.result()
                if progress and total_files:
                    status = "COPY" if result else "SKIP"
                    print(f"{status}: {file_jobs[index - 1][0]}")
                if result:
                    copied_count += 1
                else:
                    skipped_count += 1

    elapsed_seconds = time.perf_counter() - start_time
    if log_file:
        with open(log_file, "a", encoding="utf-8") as fh:
            fh.write(f"Operation completed: [{format_timestamp()}] Elapsed: {elapsed_seconds:.3f}s\n")
            fh.write(f"Result: copied={copied_count}, skipped={skipped_count}\n")

    return copied_count, skipped_count


def main():
    args = parse_args()
    source_path = Path(args.source)
    target_path = Path(args.target)

    if not source_path.exists():
        print(f"Source does not exist: {source_path}", file=sys.stderr)
        return 1

    if source_path.is_file() and target_path.exists() and target_path.is_dir():
        target_path = target_path / source_path.name

    if source_path.is_dir() and not target_path.exists():
        target_path.mkdir(parents=True, exist_ok=True)

    exclude_dirs = normalize_excludes(set(args.exclude_dir))
    exclude_files = normalize_excludes(set(args.exclude_file))

    copied, skipped = copy_tree(
        str(source_path),
        str(target_path),
        exclude_dirs=exclude_dirs,
        exclude_files=exclude_files,
        skip_same_mtime=args.skip_same_mtime,
        dry_run=args.dry_run,
        verbose=args.verbose,
        log_file=args.log_file,
        parallel=args.parallel,
        progress=args.progress,
    )

    if args.verbose:
        print(f"Files copied: {copied}")
        print(f"Files skipped: {skipped}")
    if args.log_file:
        with open(args.log_file, "a", encoding="utf-8") as fh:
            fh.write(f"Files copied: {copied}\n")
            fh.write(f"Files skipped: {skipped}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
