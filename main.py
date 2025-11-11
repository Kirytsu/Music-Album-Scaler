#!/usr/bin/env python3
"""Orchestrator for embedding cover art and renaming audio files.

This script delegates utility work to utils.py so the helpers are reusable and
unit-testable. The CLI supports running embedding and renaming separately or
together. Backups are off by default; pass --backup to create a `_backup` file
before modifying audio files.
"""
from __future__ import annotations

import argparse
import concurrent.futures
from typing import Optional

from utils import find_audio_files, process_path, DEFAULT_EXTENSIONS


def main() -> None:
	parser = argparse.ArgumentParser(description="Normalize embedded cover art and optionally rename files")
	parser.add_argument("--dir", "-d", default=".", help="Target directory (default: current directory)")
	parser.add_argument("--dry-run", action="store_true", help="Do not write changes, only report")
	parser.add_argument("--backup", action="store_true", help="Create a backup copy of the original audio file before modifying (default: off)")
	parser.add_argument("--rename", action="store_true", help="Rename files to 'XX_name.ext' using track number metadata (when enabled)")
	parser.add_argument("--workers", "-w", type=int, default=4, help="Number of worker threads to process files in parallel (default: 4)")
	parser.add_argument("--embed-only", action="store_true", help="Only embed cover art; do not rename files")
	parser.add_argument("--rename-only", action="store_true", help="Only rename files; do not embed cover art")
	parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
	args = parser.parse_args()

	# Always use the default extensions set
	exts = DEFAULT_EXTENSIONS

	# Determine operations
	if args.embed_only:
		args.do_embed = True
		args.do_rename = False
	elif args.rename_only:
		args.do_embed = False
		args.do_rename = True
	else:
		args.do_embed = True
		args.do_rename = bool(args.rename)

	files = list(find_audio_files(args.dir, exts))
	total = len(files)
	processed = 0
	skipped = 0
	errors = 0

	if args.workers and args.workers > 1:
		if args.verbose:
			print(f"Processing {total} files with {args.workers} workers...")
		with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
			futs = {ex.submit(process_path, fpath, args): fpath for fpath in files}
			for fut in concurrent.futures.as_completed(futs):
				status, p, msg = fut.result()
				if status == "processed":
					processed += 1
					if args.verbose:
						print(f"Processed: {p}")
				elif status == "skipped":
					skipped += 1
					if args.verbose:
						print(f"Skipped: {p} ({msg})")
				else:
					errors += 1
					print(f"Error processing {p}: {msg}")
	else:
		for fpath in files:
			if args.verbose:
				print(f"Checking: {fpath}")
			status, p, msg = process_path(fpath, args)
			if status == "processed":
				processed += 1
				if args.verbose:
					print(f"Processed: {p}")
			elif status == "skipped":
				skipped += 1
				if args.verbose:
					print(f"Skipped: {p} ({msg})")
			else:
				errors += 1
				print(f"Error processing {p}: {msg}")

	print(f"Done. total: {total}, processed: {processed}, skipped: {skipped}, errors: {errors}")


if __name__ == "__main__":
	main()

