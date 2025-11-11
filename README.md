# Project Usage

## Background
This project is originally created because the limitation of my DAP (Digital Audio Player / F.Audio FA4) to display album art of some music files. This project aim to normalize music files by embedding the album art so it could be displayed in those DAP. Furthermore, I tried to have a renaming function base on the track number and track name.

## Purpose
Normalize embedded album art inside music files and optionally rename files base on their metadata. 

## Requirements
```powershell
pip install -r requirements.txt
```

## Arguments
- `--dir`, `-d` PATH
	- Target directory to scan (default: current directory).

- `--dry-run`
	- Do not write changes; print what the tool would do.

- `--backup`
	- Create a `_backup` copy of each original audio file before modifying it.

- `--rename`
	- When enabled (and not using `--rename-only`), allow renaming files after embedding.

- `--embed-only`
	- Only embed cover art; do not rename files.

- `--rename-only`
	- Only rename files; do not embed cover art.

- `--workers`, `-w` N
	- Number of worker threads for parallel processing (default: 4).

- `--verbose`, `-v`
	- Show detailed output while processing.

## Examples (PowerShell)
- Embed only (do not rename):

```powershell
python3 .\main.py --dir "C:\path\to\music" --embed-only 
```

- Rename only (do not embed):

```powershell
python3 .\main.py --dir "C:\path\to\music" --rename-only 
```

- Embed + rename, without backups:

```powershell
python3 .\main.py --dir "C:\path\to\music" --rename
```

- Embed + rename, with backups:

```powershell
python3 .\main.py --dir "C:\path\to\music" --rename --backup
```

Notes
-----
- Supported formats: MP3, M4A/MP4, FLAC, OGG/Opus. Other formats may still work via a best-effort fallback.
- Recommended `--workers`:
	On a 4-core / 8-thread CPU start with `--workers 4`; increase to `8` if you want to test hyperthreading speedups.
- Please test the usage within one folder/album to check if it's working before fully embedding whole your collection. 