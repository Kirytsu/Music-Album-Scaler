#!/usr/bin/env python3
"""Utility helpers for embedding cover art and file renaming.

This module contains the image processing and tag-manipulation helpers used by
`main.py`.
"""
from __future__ import annotations

import base64
import io
import os
import re
import shutil
from typing import Optional, Tuple

from PIL import Image, ImageOps

try:
    from mutagen import File
    from mutagen.id3 import ID3, APIC, ID3NoHeaderError
    from mutagen.mp4 import MP4, MP4Cover
    from mutagen.flac import FLAC, Picture
    from mutagen.oggvorbis import OggVorbis
except Exception:
    raise SystemExit("Missing required packages. Install with: pip install -r requirements.txt")


DEFAULT_EXTENSIONS = {
    ".mp3",
    ".m4a",
    ".mp4",
    ".flac",
    ".ogg",
    ".opus",
    ".wav",
    ".aac",
    ".wma",
}


def find_audio_files(root: str, exts=DEFAULT_EXTENSIONS):
    for dirpath, dirs, files in os.walk(root):
        for name in files:
            _, ext = os.path.splitext(name)
            if ext.lower() in exts:
                yield os.path.join(dirpath, name)


def extract_cover_bytes(path: str) -> Optional[Tuple[bytes, str]]:
    """Return (image_bytes, mime) if a cover exists, otherwise None."""
    _, ext = os.path.splitext(path)
    ext = ext.lower()

    try:
        if ext == ".mp3":
            try:
                tags = ID3(path)
            except ID3NoHeaderError:
                return None
            apics = tags.getall("APIC")
            if not apics:
                return None
            data = apics[0].data
            mime = apics[0].mime
            return data, mime

        elif ext in (".m4a", ".mp4"):
            mp4 = MP4(path)
            covr = mp4.tags.get("covr")
            if not covr:
                return None
            data = bytes(covr[0])
            mime = "image/jpeg" if data[:3] == b"\xff\xd8\xff" else "image/png"
            return data, mime

        elif ext == ".flac":
            fl = FLAC(path)
            if not fl.pictures:
                return None
            pic = fl.pictures[0]
            return pic.data, pic.mime

        elif ext in (".ogg", ".opus"):
            ogg = OggVorbis(path)
            key = None
            for k in ogg.keys():
                if k.lower() == "metadata_block_picture":
                    key = k
                    break
            if not key:
                return None
            b64 = ogg.get(key)
            if not b64:
                return None
            raw = base64.b64decode(b64[0])
            p = Picture()
            try:
                p.parse(raw)
                return p.data, p.mime
            except Exception:
                start = raw.find(b"\xff\xd8\xff")
                if start != -1:
                    return raw[start:], "image/jpeg"
                start = raw.find(b"\x89PNG")
                if start != -1:
                    return raw[start:], "image/png"
                return None

        else:
            f = File(path)
            if f is None:
                return None
            if hasattr(f, "tags") and f.tags:
                try:
                    apics = f.tags.getall("APIC")
                    if apics:
                        return apics[0].data, apics[0].mime
                except Exception:
                    pass
            return None
    except Exception as e:
        print(f"Warning: failed to read tags from {path}: {e}")
        return None


def process_image_to_jpeg(img_bytes: bytes, target_width: int = 600, quality: int = 95) -> bytes:
    """Convert image bytes to a baseline JPEG.

    Behavior:
    - If image width > target_width, downscale to target_width (preserve aspect ratio).
    - If image width <= target_width, keep original dimensions (no upscaling).
    - Respect EXIF orientation, flatten alpha, preserve ICC profile when present.
    - Save as baseline (non-progressive) JPEG with given quality.
    """

    with Image.open(io.BytesIO(img_bytes)) as im:
        try:
            im = ImageOps.exif_transpose(im)
        except Exception:
            pass

        icc_profile = im.info.get("icc_profile")

        if im.mode in ("RGBA", "LA"):
            background = Image.new("RGB", im.size, (255, 255, 255))
            background.paste(im, mask=im.split()[-1])
            im = background
        else:
            im = im.convert("RGB")

        orig_w, orig_h = im.size
        if orig_w > target_width:
            target_h = int(target_width * orig_h / orig_w)
            im = im.resize((target_width, target_h), Image.LANCZOS)

        out = io.BytesIO()
        save_kwargs = {
            "format": "JPEG",
            "quality": quality,
            "optimize": True,
            "progressive": False,
            "subsampling": 0,
        }
        if icc_profile:
            save_kwargs["icc_profile"] = icc_profile
        im.save(out, **save_kwargs)
        return out.getvalue()


def get_track_number(path: str) -> Optional[int]:
    _, ext = os.path.splitext(path)
    ext = ext.lower()
    try:
        if ext == ".mp3":
            try:
                tags = ID3(path)
            except ID3NoHeaderError:
                return None
            trcks = tags.getall("TRCK")
            if trcks:
                txt = trcks[0].text[0]
                m = re.match(r"(\d+)", str(txt))
                if m:
                    return int(m.group(1))
            return None

        elif ext in (".m4a", ".mp4"):
            mp4 = MP4(path)
            trkn = mp4.tags.get("trkn")
            if trkn and len(trkn) and isinstance(trkn[0], (list, tuple)):
                return int(trkn[0][0])
            return None

        elif ext == ".flac":
            fl = FLAC(path)
            tn = fl.tags.get("tracknumber") or fl.tags.get("TRACKNUMBER")
            if tn:
                m = re.match(r"(\d+)", tn[0])
                if m:
                    return int(m.group(1))
            return None

        elif ext in (".ogg", ".opus"):
            ogg = OggVorbis(path)
            tn = ogg.get("tracknumber") or ogg.get("TRACKNUMBER")
            if tn:
                m = re.match(r"(\d+)", tn[0])
                if m:
                    return int(m.group(1))
            return None

        else:
            f = File(path)
            if f is None or not getattr(f, "tags", None):
                return None
            for key in ("tracknumber", "TRACKNUMBER", "TRCK", "trkn"):
                val = None
                try:
                    val = f.tags.get(key)
                except Exception:
                    pass
                if val:
                    if isinstance(val, (list, tuple)):
                        val = val[0]
                    m = re.match(r"(\d+)", str(val))
                    if m:
                        return int(m.group(1))
            return None
    except Exception:
        return None


def get_title(path: str) -> Optional[str]:
    _, ext = os.path.splitext(path)
    ext = ext.lower()
    try:
        if ext == ".mp3":
            try:
                tags = ID3(path)
            except ID3NoHeaderError:
                return None
            tit = tags.getall("TIT2")
            if tit:
                return str(tit[0].text[0])
            return None

        elif ext in (".m4a", ".mp4"):
            mp4 = MP4(path)
            tit = mp4.tags.get("\xa9nam")
            if tit:
                return str(tit[0])
            return None

        elif ext == ".flac":
            fl = FLAC(path)
            t = fl.tags.get("title") or fl.tags.get("TITLE")
            if t:
                return str(t[0])
            return None

        elif ext in (".ogg", ".opus"):
            ogg = OggVorbis(path)
            t = ogg.get("title") or ogg.get("TITLE")
            if t:
                return str(t[0])
            return None

        else:
            f = File(path)
            if f is None or not getattr(f, "tags", None):
                return None
            for key in ("title", "TITLE", "TIT2", "\xa9nam"):
                try:
                    val = f.tags.get(key)
                except Exception:
                    val = None
                if val:
                    if isinstance(val, (list, tuple)):
                        val = val[0]
                    return str(val)
            return None
    except Exception:
        return None


def get_album(path: str) -> Optional[str]:
    """Extract album name from audio file metadata."""
    _, ext = os.path.splitext(path)
    ext = ext.lower()
    try:
        if ext == ".mp3":
            try:
                tags = ID3(path)
            except ID3NoHeaderError:
                return None
            alb = tags.getall("TALB")
            if alb:
                return str(alb[0].text[0])
            return None

        elif ext in (".m4a", ".mp4"):
            mp4 = MP4(path)
            alb = mp4.tags.get("\xa9alb")
            if alb:
                return str(alb[0])
            return None

        elif ext == ".flac":
            fl = FLAC(path)
            a = fl.tags.get("album") or fl.tags.get("ALBUM")
            if a:
                return str(a[0])
            return None

        elif ext in (".ogg", ".opus"):
            ogg = OggVorbis(path)
            a = ogg.get("album") or ogg.get("ALBUM")
            if a:
                return str(a[0])
            return None

        else:
            f = File(path)
            if f is None or not getattr(f, "tags", None):
                return None
            for key in ("album", "ALBUM", "TALB", "\xa9alb"):
                try:
                    val = f.tags.get(key)
                except Exception:
                    val = None
                if val:
                    if isinstance(val, (list, tuple)):
                        val = val[0]
                    return str(val)
            return None
    except Exception:
        return None


def sanitize_filename(s: str, maxlen: int = 200) -> str:
    s = str(s)
    s = s.strip()
    s = s.replace("/", "_").replace("\\\\", "_")
    s = re.sub(r"[^\w \-\.()\[\]]+", "", s)
    s = re.sub(r"\s+", " ", s)
    if len(s) > maxlen:
        s = s[:maxlen].rstrip()
    return s


def safe_rename(old_path: str, new_name: str):
    dirp = os.path.dirname(old_path)
    target = os.path.join(dirp, new_name)
    base, ext = os.path.splitext(new_name)
    count = 1
    while os.path.exists(target) and os.path.abspath(target) != os.path.abspath(old_path):
        target = os.path.join(dirp, f"{base}_{count}{ext}")
        count += 1

    try:
        shutil.move(old_path, target)
        return target
    except Exception as e:
        print(f"Failed to rename {old_path} -> {target}: {e}")
        return old_path


def embed_cover(path: str, jpeg_bytes: bytes, backup: bool = False):
    _, ext = os.path.splitext(path)
    ext = ext.lower()
    print(f"Embedding JPEG cover into: {path}")

    try:
        if backup:
            base, ext = os.path.splitext(path)
            bak = f"{base}_backup{ext}"
            if not os.path.exists(bak):
                try:
                    shutil.copy2(path, bak)
                except Exception:
                    pass

        if ext == ".mp3":
            try:
                tags = ID3(path)
            except ID3NoHeaderError:
                tags = ID3()
            tags.delall("APIC")
            tags.add(APIC(encoding=3, mime="image/jpeg", type=3, desc="", data=jpeg_bytes))
            tags.save(path, v2_version=3)

        elif ext in (".m4a", ".mp4"):
            mp4 = MP4(path)
            mp4.tags["covr"] = [MP4Cover(jpeg_bytes, imageformat=MP4Cover.FORMAT_JPEG)]
            mp4.save()

        elif ext == ".flac":
            fl = FLAC(path)
            fl.clear_pictures()
            p = Picture()
            p.data = jpeg_bytes
            p.mime = "image/jpeg"
            p.type = 3
            try:
                p.description = ""
            except Exception:
                pass
            try:
                im = Image.open(io.BytesIO(jpeg_bytes))
                p.width, p.height = im.size
                mode = im.mode
                if mode == "RGB":
                    p.depth = 24
                    p.colors = 0
                elif mode == "RGBA":
                    p.depth = 32
                    p.colors = 0
                elif mode in ("L", "P"):
                    p.depth = 8
                    if mode == "P":
                        cols = im.getcolors()
                        p.colors = len(cols) if cols else 0
                    else:
                        p.colors = 0
                else:
                    p.depth = 24
                    p.colors = 0
            except Exception:
                pass
            fl.add_picture(p)
            fl.save()

        elif ext in (".ogg", ".opus"):
            ogg = OggVorbis(path)
            p = Picture()
            p.data = jpeg_bytes
            p.mime = "image/jpeg"
            p.type = 3
            try:
                p.description = ""
            except Exception:
                pass
            try:
                im = Image.open(io.BytesIO(jpeg_bytes))
                p.width, p.height = im.size
                mode = im.mode
                if mode == "RGB":
                    p.depth = 24
                    p.colors = 0
                elif mode == "RGBA":
                    p.depth = 32
                    p.colors = 0
                elif mode in ("L", "P"):
                    p.depth = 8
                    if mode == "P":
                        cols = im.getcolors()
                        p.colors = len(cols) if cols else 0
                    else:
                        p.colors = 0
                else:
                    p.depth = 24
                    p.colors = 0
            except Exception:
                pass
            raw = p.write()
            b64 = base64.b64encode(raw).decode("ascii")
            ogg.tags["METADATA_BLOCK_PICTURE"] = [b64]
            ogg.save()

        else:
            f = File(path)
            if f is None:
                print(f"Cannot open file for embedding: {path}")
                return
            try:
                tags = ID3(path)
                tags.delall("APIC")
                tags.add(APIC(encoding=3, mime="image/jpeg", type=3, desc="", data=jpeg_bytes))
                tags.save(path, v2_version=3)
                return
            except Exception:
                pass
            print(f"No embedding handler for extension {ext} (file: {path})")

    except Exception as e:
        print(f"Error embedding cover into {path}: {e}")


def get_majority_album(folder_path: str) -> Optional[str]:
    """Analyze all audio files in a folder and return the most common album name."""
    from collections import Counter
    
    albums = []
    for file_path in find_audio_files(folder_path, DEFAULT_EXTENSIONS):
        # Only check files directly in this folder (not subdirectories)
        if os.path.dirname(file_path) == os.path.abspath(folder_path):
            album = get_album(file_path)
            if album and album.strip():
                albums.append(album.strip())
    
    if not albums:
        return None
    
    # Get the most common album name
    counter = Counter(albums)
    most_common = counter.most_common(1)[0]
    return most_common[0]


def rename_folder_by_album(folder_path: str) -> tuple:
    """Rename folder based on majority album name from tracks.
    Returns (status, old_path, new_path_or_message).
    """
    try:
        album = get_majority_album(folder_path)
        if not album:
            return ("skipped", folder_path, "no album metadata found")
        
        # Get parent directory and current folder name
        parent = os.path.dirname(folder_path)
        current_name = os.path.basename(folder_path)
        
        # Sanitize album name for folder
        safe_album = sanitize_filename(album)
        
        # Skip if folder is already named correctly
        if current_name == safe_album:
            return ("skipped", folder_path, "already named correctly")
        
        # Create new path
        new_path = os.path.join(parent, safe_album)
        
        # Handle conflicts
        if os.path.exists(new_path):
            count = 1
            while os.path.exists(new_path):
                new_path = os.path.join(parent, f"{safe_album}_{count}")
                count += 1
        
        # Rename folder
        try:
            os.rename(folder_path, new_path)
            return ("processed", folder_path, new_path)
        except Exception as e:
            return ("error", folder_path, f"failed to rename: {e}")
    
    except Exception as e:
        return ("error", folder_path, str(e))


def process_path(path: str, args) -> tuple:
    """Worker to process a single file. Returns (status, path, message).
    status: 'processed', 'skipped', 'error'
    """
    try:
        did_something = False
        new_path = path
        
        # Handle embedding if requested
        if getattr(args, "do_embed", True):
            info = extract_cover_bytes(path)
            if info:
                img_bytes, mime = info
                jpeg = process_image_to_jpeg(img_bytes)
                embed_cover(path, jpeg, backup=getattr(args, "backup", False))
                did_something = True
            # If no cover but embed was requested, just skip the embed part
            # (don't fail the whole operation if rename is also requested)
        
        # Handle renaming if requested
        if getattr(args, "do_rename", False):
            track = get_track_number(path)
            if track is not None:
                title = get_title(path) or os.path.splitext(os.path.basename(path))[0]
                title = sanitize_filename(title)
                base_new = f"{int(track):02d}. {title}"
                ext = os.path.splitext(path)[1]
                new_name = base_new + ext
                new_path = safe_rename(path, new_name)
                print(f"Renamed to: {new_path}")
                did_something = True
            else:
                # Only fail if ONLY rename was requested and no track number
                if not getattr(args, "do_embed", True):
                    return ("skipped", path, "no track number metadata")
        
        # If we were supposed to do something but couldn't
        if not did_something:
            if getattr(args, "do_embed", True) and not getattr(args, "do_rename", False):
                return ("skipped", path, "no embedded cover")
            elif getattr(args, "do_rename", False) and not getattr(args, "do_embed", True):
                return ("skipped", path, "no track number metadata")
            else:
                return ("skipped", path, "no cover and no track number")
        
        return ("processed", new_path, "ok")
    except Exception as e:
        return ("error", path, str(e))
