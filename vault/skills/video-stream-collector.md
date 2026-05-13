---
author: Hermes Agent
categories:
- video-stream-collector
description: Create and configure a Python project for collecting/streaming video
  from online platforms (Bilibili, YouTube, etc.).
license: MIT
metadata:
  hermes:
    category: devops
    tags:
    - python
    - video
    - yt-dlp
    - streaming
    - project-setup
name: video-stream-collector
summary: Create and configure a Python project for collecting/streaming video from
  online platforms (Bilibili, YouTube, etc.).
triggers:
- python
- video
- yt-dlp
- streaming
- project-setup
version: 1.0.0
---

# Video Stream Collector — Project Setup

Create and configure a Python project for collecting/streaming video from online platforms. Uses yt-dlp + SQLite + editable package with src-layout.

## Step 1: Project Structure

```bash
mkdir -p project/{config,data/{raw,processed,metadata},logs,scripts,tests,src/package_name}
```

## Step 2: pyproject.toml (src-layout)

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "video-collection"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = ["yt-dlp>=2024.1.0", "pyyaml>=6.0", "requests>=2.31.0", "aiohttp>=3.9.0", "sqlalchemy>=2.0.0", "rich>=13.0.0", "click>=8.1.0"]

[project.optional-dependencies]
dev = ["pytest>=7.4.0", "pytest-asyncio>=0.23.0"]

[tool.setuptools.packages.find]
where = ["src"]
include = ["video_collection*"]
```

## Step 3: Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Step 4: SQLite Database Init

Create `scripts/init_db.py` — tables: sources, tasks, chunks, metadata. Use `INSERT OR IGNORE` for defaults.

## Step 5: Collector Module

Create `src/package_name/collector.py` using yt-dlp:
- Use `yt_dlp.YoutubeDL` with format selection
- Track tasks/chunks in SQLite
- Support quality mapping per platform

## Step 6: Tests

Create `tests/test_collector.py` — test config, DB ops, and real collection with pytest.

## Step 7: Title-Based Directory Organization

After download, move the video file into a subdirectory named after the video title:

```python
def _move_to_title_dir(self, file_path: Path, preferred_title: str = "") -> Path:
    title = preferred_title or self._extract_title_from_ffprobe(file_path) or file_path.stem
    title_dir = self.output_dir / sanitize_filename(title)
    title_dir.mkdir(parents=True, exist_ok=True)
    new_path = title_dir / file_path.name
    shutil.move(str(file_path), str(new_path))
    return new_path
```

Use `info["title"]` from yt-dlp's extract_info result as the preferred title. Fall back to ffprobe metadata, then filename.

## Pitfalls

- **Setuptools flat-layout error**: "Multiple top-level packages discovered" — fix with `[tool.setuptools.packages.find] where = ["src"]`.
- **yt-dlp format strings**: Some format fields are `None` (e.g., filesize), causing `.format()` errors. Always check for None before string formatting.
- **yt-dlp mock testing**: Cannot patch `yt_dlp.YoutubeDL.extract_info` — `YoutubeDL` is a module, not a class. Use `MagicMock()` instead.
- **YouTube search downloads entire playlist**: See `video-search` skill for the `extract_flat="in_playlist"` fix.
- **YouTube video metadata**: yt-dlp downloads don't include title in ffprobe tags. Always use `info["title"]` from yt-dlp's `extract_info` result for directory naming, not ffprobe.

## Bilibili-Specific Notes

- Format IDs are numeric: 16 (360p), 32 (480p), 64/112 (720p), 80/116 (1080p), 120 (1080P high bitrate)
- Many formats require premium membership
- Use `--cookies-from-browser firefox` or `--cookiefile` for authenticated downloads
- WBI signing is done automatically by yt-dlp

## Related

- See `references/bilibili-format-ids.md` for format reference
- See `references/cookie-auth.md` for cookie setup
- See `references/truncation.md` for video duration limiting
- See `video-search` for cross-platform search and download workflow