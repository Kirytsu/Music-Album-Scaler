#!/usr/bin/env python3
"""Orchestrator for embedding cover art and renaming audio files.

Interactive numbered menu for processing audio files:
- Embed/normalize cover art (resize, convert to JPEG)
- Rename files based on track number metadata

This script delegates utility work to utils.py so the helpers are reusable and
unit-testable.
"""
from __future__ import annotations

import concurrent.futures
import os
import shlex
from dataclasses import dataclass

from utils import find_audio_files, process_path, rename_folder_by_album, DEFAULT_EXTENSIONS


# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Config:
    """Holds all processing options."""
    directory: str = "."
    backup: bool = False
    do_embed: bool = True
    do_rename: bool = False
    do_rename_folders: bool = False
    workers: int = 4


# ─────────────────────────────────────────────────────────────────────────────
# Interactive Menu
# ─────────────────────────────────────────────────────────────────────────────

def clear_screen() -> None:
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_menu() -> None:
    """Display the main menu."""
    print()
    print("=" * 50)
    print("   AUDIO FILE COVER ART & RENAME UTILITY")
    print("=" * 50)
    print()
    print("  [1] Embed cover art only")
    print("  [2] Rename files only")
    print("  [3] Embed + Rename")
    print("  [4] Rename folders by album metadata")
    print("  [0] Exit")
    print()
    print("-" * 50)


def parse_path(raw: str) -> str:
    """
    Parse a path string, handling quoted paths with spaces.
    e.g. '"C:\\My Music\\Album"' -> 'C:\\My Music\\Album'
    """
    raw = raw.strip()
    if not raw:
        return "."
    
    # Handle quoted paths (e.g., "C:\path with spaces")
    if (raw.startswith('"') and raw.endswith('"')) or \
       (raw.startswith("'") and raw.endswith("'")):
        return raw[1:-1]
    
    # Try shlex for more complex quoting
    try:
        parts = shlex.split(raw)
        if parts:
            return parts[0]
    except ValueError:
        pass
    
    return raw


def prompt_directory() -> str:
    """Prompt user for directory path."""
    print("Enter target directory path:")
    print("  (Use quotes for paths with spaces, e.g., \"C:\\My Music\")")
    print("  (Press Enter for current directory)")
    print()
    
    while True:
        raw = input("  Path: ")
        path = parse_path(raw)
        
        if os.path.isdir(path):
            return os.path.abspath(path)
        
        print(f"  [!] Directory not found: {path}")
        print("  Please try again.\n")


def prompt_choice(prompt: str, valid: set[str]) -> str:
    """Prompt for a single choice from valid options."""
    while True:
        choice = input(prompt).strip()
        if choice in valid:
            return choice
        print(f"  [!] Invalid option. Choose from: {', '.join(sorted(valid))}")


def run_interactive() -> Config | None:
    """
    Run the interactive menu.
    Returns Config if user selects an operation, None if exit.
    """
    clear_screen()
    print_menu()
    
    choice = prompt_choice("  Select option: ", {"0", "1", "2", "3", "4"})
    
    if choice == "0":
        return None
    
    # Map choice to config
    config = Config()
    
    if choice == "1":
        config.do_embed, config.do_rename, config.do_rename_folders = True, False, False
    elif choice == "2":
        config.do_embed, config.do_rename, config.do_rename_folders = False, True, False
    elif choice == "3":
        config.do_embed, config.do_rename, config.do_rename_folders = True, True, False
    elif choice == "4":
        config.do_embed, config.do_rename, config.do_rename_folders = False, False, True
    
    print()
    config.directory = prompt_directory()
    
    # Ask for backup if embedding
    if config.do_embed:
        print()
        bk = prompt_choice("  Create backup before modifying? [y/N]: ", {"", "y", "n", "Y", "N"})
        config.backup = bk.lower() == "y"
    
    return config


def print_summary(config: Config, file_count: int) -> None:
    """Display processing summary."""
    ops = []
    if config.do_embed:
        ops.append("Embed")
    if config.do_rename:
        ops.append("Rename")
    if config.do_rename_folders:
        ops.append("Rename Folders")
    
    print()
    print("-" * 50)
    print("  SUMMARY")
    print("-" * 50)
    print(f"  Directory : {config.directory}")
    print(f"  Files     : {file_count}")
    print(f"  Operation : {' + '.join(ops)}")
    print(f"  Backup    : {'Yes' if config.backup else 'No'}")
    print("-" * 50)


def confirm_proceed() -> bool:
    """Ask user to confirm before processing."""
    choice = prompt_choice("\n  Proceed? [Y/n]: ", {"", "y", "n", "Y", "N"})
    return choice.lower() != "n"


# ─────────────────────────────────────────────────────────────────────────────
# File Processing
# ─────────────────────────────────────────────────────────────────────────────

def process_files(files: list[str], config: Config) -> tuple[int, int, int]:
    """
    Process all files with the given configuration.
    Returns (processed_count, skipped_count, error_count).
    """
    total = len(files)
    processed = 0
    skipped = 0
    errors = 0
    
    print(f"\n  Processing {total} files...\n")
    
    if config.workers > 1:
        with concurrent.futures.ThreadPoolExecutor(max_workers=config.workers) as executor:
            futures = {executor.submit(process_path, fpath, config): fpath for fpath in files}
            
            for future in concurrent.futures.as_completed(futures):
                status, path, msg = future.result()
                processed, skipped, errors = _update_counters(
                    status, path, msg, processed, skipped, errors
                )
    else:
        for fpath in files:
            status, path, msg = process_path(fpath, config)
            processed, skipped, errors = _update_counters(
                status, path, msg, processed, skipped, errors
            )
    
    return processed, skipped, errors


def _update_counters(
    status: str, path: str, msg: str,
    processed: int, skipped: int, errors: int
) -> tuple[int, int, int]:
    """Update and return counters based on processing status."""
    filename = os.path.basename(path)
    if status == "processed":
        processed += 1
    elif status == "skipped":
        skipped += 1
        print(f"  [-] Skipped: {filename} ({msg})")
    else:
        errors += 1
        print(f"  [!] Error: {filename} - {msg}")
    
    return processed, skipped, errors


def print_results(total: int, processed: int, skipped: int, errors: int) -> None:
    """Display final processing results."""
    print()
    print("=" * 50)
    print("  RESULTS")
    print("=" * 50)
    print(f"  Total     : {total}")
    print(f"  Processed : {processed}")
    print(f"  Skipped   : {skipped}")
    print(f"  Errors    : {errors}")
    print("=" * 50)


# ─────────────────────────────────────────────────────────────────────────────
# Folder Processing
# ─────────────────────────────────────────────────────────────────────────────

def get_immediate_subdirs(root: str) -> list[str]:
    """Get all immediate subdirectories in root."""
    subdirs = []
    try:
        for entry in os.scandir(root):
            if entry.is_dir():
                subdirs.append(entry.path)
    except Exception as e:
        print(f"  [!] Error scanning directory: {e}")
    return subdirs


def process_folders(root: str) -> tuple[int, int, int]:
    """
    Rename folders based on album metadata.
    Returns (processed_count, skipped_count, error_count).
    """
    folders = get_immediate_subdirs(root)
    
    if not folders:
        print("\n  No subdirectories found.")
        return 0, 0, 0
    
    processed = 0
    skipped = 0
    errors = 0
    
    print(f"\n  Processing {len(folders)} folders...\n")
    
    for folder in folders:
        status, old_path, new_path_or_msg = rename_folder_by_album(folder)
        
        folder_name = os.path.basename(old_path)
        
        if status == "processed":
            processed += 1
            new_name = os.path.basename(new_path_or_msg)
            print(f"  ✓ Renamed: {folder_name} → {new_name}")
        elif status == "skipped":
            skipped += 1
            print(f"  [-] Skipped: {folder_name} ({new_path_or_msg})")
        else:
            errors += 1
            print(f"  [!] Error: {folder_name} - {new_path_or_msg}")
    
    return processed, skipped, errors


# ─────────────────────────────────────────────────────────────────────────────
# Main Entry Point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    """Main entry point with interactive numbered menu."""
    try:
        config = run_interactive()
        
        if config is None:
            print("\n  Goodbye!")
            return
        
        # Handle folder renaming separately
        if config.do_rename_folders:
            processed, skipped, errors = process_folders(config.directory)
            print_results(len(get_immediate_subdirs(config.directory)), processed, skipped, errors)
            return
        
        # Find audio files
        files = list(find_audio_files(config.directory, DEFAULT_EXTENSIONS))
        
        # Show summary
        print_summary(config, len(files))
        
        if len(files) == 0:
            print("\n  No audio files found.")
            return
        
        # Confirm
        if not confirm_proceed():
            print("\n  Cancelled.")
            return
        
        # Process files
        processed, skipped, errors = process_files(files, config)
        
        # Show results
        print_results(len(files), processed, skipped, errors)
        
    except KeyboardInterrupt:
        print("\n\n  Cancelled by user.")


if __name__ == "__main__":
    main()

