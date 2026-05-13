---
categories:
- yt-dlp-workflow
description: Common patterns for yt-dlp video extraction, download, and search
name: yt-dlp-workflow
summary: Common patterns for yt-dlp video extraction, download, and search
triggers: []
---

# yt-dlp Usage Patterns

Common yt-dlp patterns for video extraction and downloading.

## Extract info only (no download)
```python
import yt_dlp

ydl_opts = {
    "quiet": True,
    "no_warnings": True,
    "skip_download": True,
}
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info(url, download=False)
    title = info.get("title")
    duration = info.get("duration")
```

## YouTube search
```python
url = f"https://www.youtube.com/results?search_query={query}"
ydl_opts = {
    "extract_flat": "in_playlist",  # expand playlist entries without downloading
    "noplaylist": True,
    "skip_download": True,
    "quiet": True,
}
```

## Pitfall: YouTube search returns playlist format
YouTube search results come wrapped in a "search results" playlist. Without `noplaylist: True`, yt-dlp tries to download all videos in the search result page (hundreds).

## Pitfall: extract_flat drops upload_date
`extract_flat: "in_playlist"` returns `dict` entries but **omits `upload_date`** (the field is only populated in full extract). When you need `upload_date` in search results, use a two-step approach:

1. First pass: `extract_flat` to get video IDs (fast, ~20s)
2. Second pass: full `extract_info` per video (slow, ~10-30s each)

```python
from concurrent.futures import ThreadPoolExecutor

# Step 1: get IDs
flat_opts = {
    "extract_flat": "in_playlist",
    "quiet": True, "no_warnings": True,
    "skip_download": True, "noplaylist": True,
}
with yt_dlp.YoutubeDL(flat_opts) as ydl:
    info = ydl.extract_info(search_url, download=False)

# Step 2: full metadata per video
for vid_id in video_ids:
    with yt_dlp.YoutubeDL({"skip_download": True, "quiet": True, "no_warnings": True}) as ydl:
        meta = ydl.extract_info(f"https://www.youtube.com/watch?v={vid_id}", download=False)
        upload_date = meta.get("upload_date", "")  # Only populated here
```

⚠️ **Timeout**: YouTube search extract_flat can take 30-60s (JS challenge). Use `ThreadPoolExecutor` with generous timeout (120s+).

## Pitfall: YouTube JS runtime
```
WARNING: No supported JavaScript runtime could be found. Only deno is enabled by default
```
YouTube extraction requires a JS runtime for formats 1080p+. Without it, yt-dlp falls back to format 18 (360p). Install deno and configure it:

**CLI**: `yt-dlp --js-runtimes deno:/root/.deno/bin/deno --remote-components ejs:github ...`
**Python API (not reliable in daemon contexts)**: `ydl_opts = {"js_runtimes": {"deno": {"path": "/root/.deno/bin/deno"}}, "remote_components": "ejs:github"}`
**In PM2/daemon**: use CLI via `subprocess.run()`, not Python API — the Python API doesn't reliably pass js_runtimes in non-interactive contexts.

## Bilibili format codes
- `16`: 360p
- `32`: 480p
- `64,112`: 720p (combined audio+video)
- `80,116`: 1080p
- `120`: 1080p60 (often requires coins)

Use comma-separated: `"format": "64,112,32,16"` for quality fallback.

## Bilibili paywall
Most Bilibili videos are locked behind login/coins. Use `--cookies-from-browser` or `--cookies` for authenticated access.

## Format selection
```python
fmt_map = {
    "360p": "worst",
    "480p": "360",
    "720p": "best[height<=720]",
    "1080p": "best[height<=1080]",
    "max": "best",
}
```

## References
- `references/youtube-search-issues.md` — YouTube search page quirks, URL encoding, thread-local YDL

## Download with metadata
```python
ydl_opts = {
    "format": "best",
    "outtmpl": "output_%(title)s.%(ext)s",
    "merge_output_format": "mp4",
    "noplaylist": True,
    "postprocessors": [{
        "key": "FFmpegVideoConvertor",
        "preferedformat": "mp4",
    }],
}
```