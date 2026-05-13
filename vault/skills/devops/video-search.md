---
author: Hermes Agent
categories:
- devops
description: Cross-platform video search and download workflow — search YouTube/Bilibili/Twitch,
  display results, let user pick, then download.
license: MIT
metadata:
  hermes:
    category: devops
    tags:
    - python
    - video
    - yt-dlp
    - search
    - streaming
name: video-search
summary: Cross-platform video search and download workflow — search YouTube/Bilibili/Twitch,
  display results, let user pick, then download.
triggers:
- python
- video
- yt-dlp
- search
- streaming
version: 1.0.0
---

# Video Search — Cross-Platform Search & Download

Search video content across YouTube, Bilibili, Twitch, and other platforms, display results to the user, and download the selected video.

## Core Classes

### VideoResult

```python
from dataclasses import dataclass

@dataclass
class VideoResult:
    id: str
    title: str
    source: str
    url: str
    duration: float = 0.0
    thumbnail: str = ""
    uploader: str = ""
    view_count: int = 0
```

### SearchOptions

```python
@dataclass
class SearchOptions:
    platform: str = "all"       # "youtube", "bilibili", "twitch", "douyin", "all"
    quality: str = "720p"
    max_results: int = 10
    max_duration: int = 3600
    download_dir: str = "data/raw"
    chunk_duration: int = 300
    max_retries: int = 3
```

### VideoSearcher

Register platform-specific searchers and search across all of them:

```python
searcher = VideoSearcher()
searcher.register("youtube", search_youtube)
searcher.register("bilibili", search_bilibili)
results = searcher.search("query", options)
results.sort(key=lambda r: (-r.view_count, -r.duration or 0))
```

## Platform Search Implementations

### YouTube

```python
def search_youtube(query: str, options: SearchOptions) -> list[VideoResult]:
    import yt_dlp
    url = f"https://www.youtube.com/results?search_query={query}"
    ydl_opts = {
        "extract_flat": "in_playlist",   # KEY: NOT True
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,              # KEY: prevents playlist expansion
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        # Entries may be strings (video IDs), not dicts!
        results = []
        for entry in info.get("entries", [])[:options.max_results]:
            if entry:
                eid = entry.get("id", "") if isinstance(entry, dict) else str(entry)
                if eid and "youtube.com" not in eid:
                    results.append(VideoResult(
                        id=eid,
                        title=entry.get("title", f"video_{eid}") if isinstance(entry, dict) else "",
                        source="youtube",
                        url=f"https://www.youtube.com/watch?v={eid}",
                        duration=entry.get("duration", 0) if isinstance(entry, dict) else 0,
                        uploader=entry.get("uploader", "") if isinstance(entry, dict) else "",
                    ))
        return results
```

### Bilibili

```python
def search_bilibili(query: str, options: SearchOptions) -> list[VideoResult]:
    import yt_dlp
    url = f"https://search.bilibili.com/all?keyword={query}"
    ydl_opts = {
        "extract_flat": "in_playlist",
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return [VideoResult(...) for entry in info.get("entries", [])[:options.max_results]]
```

## Display & Selection

### Format Results

```python
def format_results(results: list[VideoResult]) -> str:
    lines = ["\n[bold cyan]搜索结果[/]\n"]
    for i, r in enumerate(results, 1):
        dur = _format_duration(r.duration)
        lines.append(f"[bold]{i}[/]. {r.title}")
        lines.append(f"   来源: {r.source}  |  时长: {dur}  |  上传者: {r.uploader}")
        lines.append(f"   链接: {r.url}")
        lines.append("")
    return "\n".join(lines)
```

### User Selection → Download

```python
def download_selected(video_id: str, source_name: str, url: str, quality: str = "720p"):
    from video_collection.collector import StreamCollector, CollectorConfig
    config = CollectorConfig(quality=quality)
    output_dir = f"data/raw/{source_name}"
    collector = StreamCollector(source_name, url, output_dir, config)
    return collector.collect()
```

## Pitfalls

- **YouTube search downloads entire playlist**: Using `extract_flat=True` on YouTube search URLs causes yt-dlp to treat the search results page as a playlist and download ALL videos. Fix: `extract_flat="in_playlist"` + `noplaylist=True`.
- **Search entries can be strings**: yt-dlp search results may return video IDs as plain strings, not dicts with `"url"` keys. Always check `isinstance(entry, dict)` before accessing dict keys.
- **None duration**: Some search entries have `duration=None`. Handle with `entry.get("duration", 0) or 0`.
- **Bilibili requires cookies for premium**: Higher quality formats (1080P+) require authentication. Use `--cookies-from-browser firefox` or `--cookiefile` for logged-in downloads.

## Related

- See `references/youtube-search-bug.md` for the playlist download bug
- See `video-stream-collector` for project setup, SQLite init, and collector module