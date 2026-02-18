# Audio File Utility

A tool to normalize album art (600 x 600 pixels) and rename audio files based on metadata.

## Setup

```powershell
pip install -r requirements.txt
```

## Usage

Run the interactive menu:

```powershell
python main.py
```

The menu offers 4 options:
1. **Embed cover art only** - Normalize album art (resize, convert to JPEG)
2. **Rename files only** - Rename based on track number and title
3. **Embed + Rename** - Do both operations
4. **Rename folders** - Rename folders by album metadata

## Supported Formats

MP3, M4A/MP4, FLAC, OGG/Opus

## Notes

- Test on one album first before processing your entire collection
- Backup option available in the menu 