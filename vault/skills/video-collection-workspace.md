---
categories:
- video-collection-workspace
description: Build a complete video collection project with venv, yt-dlp, SQLite,
  search, and web UI
name: video-collection-workspace
summary: Build a complete video collection project with venv, yt-dlp, SQLite, search,
  and web UI
triggers: []
---

# Video Collection Workspace

Build a complete video collection project: Python package in a venv, yt-dlp engine, SQLite metadata, search UI, title-based directory storage, ffmpeg truncation.

## Step 1 — Create project structure
```bash
mkdir -p /mnt/data/<project_name>/{config,data/{raw,processed,metadata},logs,scripts,tests,docs,webui}
cd /mnt/data/<project_name>
```

## Step 2 — Initialize venv
```bash
python3 -m venv .venv
echo "3.11" > .python-version
```

## Step 3 — Package setup
- Use `src-layout`: `src/<pkg>/`
- `pyproject.toml` with `tool.setuptools.packages.find` → `where = ["src"]`
- Dependencies: `yt-dlp>=2024.1.0`, `ffmpeg-python>=0.2.0`, `pyyaml`, `requests`, `aiohttp`, `sqlalchemy`, `rich`, `click`, `fastapi`, `uvicorn`, `jinja2` (or static HTML)

## Step 4 — Database
- SQLite for metadata: `data/metadata/collection.db`
- Tables: `sources`, `tasks`, `chunks`, `metadata`
- Schema: source_id, source_name, url, quality, chunk_duration, max_duration, status, started_at, finished_at
- Use `scripts/init_db.py` as entry point

## Step 5 — Collector
- `yt_dlp.YoutubeDL` with `format` selection and `noplaylist: True`
- Bilibili: use format codes `16,32,64,112,80,116,120` (fallback chain)
- YouTube: use `extract_flat: in_playlist` + `noplaylist: True`
- Output: `%(id)s` or title-based with `sanitize_filename`
- **Title-based directory**: rename files into `<sanitize_filename(title)>/` subdirectory
- **Truncation**: use ffmpeg `-c copy` (not re-encode) to avoid quality loss
- **Thumbnail capture**: after download, extract `thumbnail` from yt-dlp info dict, download via `urllib.request` with User-Agent header, save as `<title>.jpg` in output dir, store path in `metadata` table under key `thumbnail`.
- **File path recording**: after `_move_to_title_dir()`, always record the final file path to `metadata` table (`file_path` key). Without this, the `/api/video/{task_id}` endpoint returns 404.

## Step 6 — Search
- Use yt-dlp search endpoints:
  - YouTube: `https://www.youtube.com/results?search_query=...` (append `&sort_by=dd|ld|p|a|rr` for date/views/rating/relevance)
  - Bilibili: `https://search.bilibili.com/all?keyword=...`
- Return `VideoResult` objects with id, title, source, url, duration, uploader, upload_date
- **YouTube sort_by**: see `references/youtube-sort-params.md`
- **YouTube JS runtime**: needs deno installed; without it, some formats are missing
- **Time filtering**: filter results by `upload_date >= cutoff` where cutoff = `(now - N days).strftime("%Y%m%d")`

## Step 7 — CLI
- Interactive: `scripts/search_and_download.py --keyword ... --platform ...`
- Programmatic: `python -c "from video_collection.collector import collect; ..."`

## Step 8 — Web UI (optional)
- FastAPI + static HTML (no Jinja2 — use `FileResponse` instead)
- Tailwind CSS via CDN
- Pure JavaScript (no framework)
- Static HTML avoids Jinja2 template conflicts with `{{ }}` and `{% %}` syntax
- **Quality selector**: replace platform dropdown with quality dropdown when only one platform is active. Default 480p, options: 360p, 480p, 720p, 1080p, max. Pass selected quality to both search API and download API.
- **Video playback**: add `/api/video/{task_id}` endpoint that reads `file_path` from `metadata` table and returns `FileResponse`. Frontend: modal with `<video controls>` element, `playVideo(taskId, title)` opens, `closeVideoModal()` pauses + clears src.
- **Video thumbnail**: add `/api/video-thumb/{task_id}` endpoint serving thumbnail images. Collect them during download (see Step 5).
- **Watch tab**: `/api/videos` returns all finished videos with metadata. Frontend: card grid layout with thumbnail, title, source badge, uploader, duration overlay, and hover play button.
- **Thumbnail proxy**: `/api/thumb-proxy?src=<yt-dlp-thumbnail-url>` looks up the cached thumbnail file by URL and serves it. Used for search results where thumbnails come from external CDNs. Also expose `/api/thumbnails` to bulk-return URL→task_id mappings.
- **Downloads tab**: filter tasks by `status='running'` (not `active_downloads` dict) to show current downloads. Populate source filter dynamically from the task list.
- **Search results thumbnails**: render yt-dlp thumbnail URLs directly (not via proxy) in search results table — external CDN URLs usually load without CORS issues.
- **Download API quality param**: `/api/download` endpoint accepts `quality` in request body; defaults to 720p but should reflect the UI selector. Output dir: `data/raw/youtube/{video_id}/`.

## Pitfalls
- **YouTube search upload_date from HTML**: `extract_flat: in_playlist` may not return `upload_date` in the entry dict. Fallback: fetch raw HTML from search URL, parse `<time datetime="YYYY-MM-DD">` tags. The `<time>` elements appear in YouTube's search results page HTML. Extract via regex, then map index-by-index to the entries from yt-dlp.
- **SQLite LEFT JOIN column selection**: When you have multiple LEFT JOINs, you MUST list each column in the SELECT clause. Having `LEFT JOIN metadata m6 ON ...` in the query is NOT enough — you must explicitly include `m6.value AS upload_date` in the SELECT. Without this, `d.get("upload_date")` returns `None` even though the join is correct.
- **History tab API choice**: Use `/api/videos` for the history/downloaded videos tab, NOT `/api/status`. `/api/videos` includes `upload_date` in its response, while `/api/status`'s metadata dict does not include `upload_date` for each task.
- **Backfill upload_date for old videos**: Use `scripts/migrate_upload_dates.py` to extract upload dates from YouTube URLs via yt-dlp. Run with `.venv/bin/python scripts/migrate_upload_dates.py`.
- **yt-dlp YouTube search**: returns playlist format by default — always set `noplaylist: True` and `extract_flat: in_playlist`
- **yt-dlp YouTube search**: returns playlist format by default — always set `noplaylist: True` and `extract_flat: in_playlist`
- **YouTube JS runtime**: needs deno installed; without it, some formats are missing
- **escapeJson in HTML onclick**: `JSON.stringify()` produces `"` characters that break HTML attribute boundaries. When passing JSON objects into `onclick="..."` attributes, must escape both `'` (to not break the wrapper) AND `"` (to not break the attribute). Use: `JSON.stringify(obj).replace(/'/g, "\\'").replace(/"/g, '&quot;')`. Browser auto-renders `&quot;` back to `"` so `JSON.parse()` still works.
- **URL as source_name**: `source_name` in `collect()` is often a full URL (e.g., `watch?v=xxx`) not a clean identifier. Extract video ID via regex: `re.search(r'[?&]v=([a-zA-Z0-9_-]{11})', url)`. Output directory should be `data/raw/{source_name}/{video_id}/`.
- **Bilibili paywalls**: most formats require login/coins; format codes `64,112` are 720p, `80,116` are 1080p+ (often locked)
- **Jinja2 + JavaScript**: `{% raw %}` needed but messy; prefer static HTML with `FileResponse`
- **ffmpeg copy mode**: use `-c copy` for speed, but verify duration matches (not always exact)
- **SQLite file locking**: close connections promptly; use context managers
- **yt-dlp progress**: use `yt_dlp.YoutubeDL` with `progress_hooks` for real-time updates
- **VideoResult serialization**: use Pydantic BaseModel instead of dataclass for `.model_dump()`
- **Nginx video path**: frontend must use full path `/terry-era/api/video-collection/video/{id}`, not just `/terry-era/api/video-collection/{id}`. The nginx rewrite strips `/terry-era/api/video-collection/` prefix and forwards the remainder — so `/video/{id}` is needed to reach the backend route `/api/video/{id}`.
- **Watch tab filtering**: history tab supports status/source/search/order filters; populate source filter dynamically from task list.
- **YouTube 1080p+ requires deno JS runtime**: yt-dlp cannot resolve YouTube's encrypted signature without a JavaScript runtime. Without deno, only 360p (format 18) is available regardless of quality selection. Install deno (`curl -fsSL https://deno.land/install.sh | sh`) and configure it via `--js-runtimes deno:/root/.deno/bin/deno`.
- **Use yt-dlp CLI, not Python API, for JS runtime config**: The Python `yt_dlp.YoutubeDL` API doesn't reliably support `js_runtimes` in daemon/PM2 environments (even with `subprocess.Popen`). Use `subprocess.run(['yt-dlp', ...])` with CLI flags `--js-runtimes deno:/root/.deno/bin/deno --remote-components ejs:github`.
- **PM2 uses system Python, not venv**: PM2's `start` command uses the system Python, not the project's venv. Fix: (a) set shebang `#!/path/to/venv/bin/python`, and (b) use `os.execv(venv_python, [venv_python, script] + sys.argv[1:])` to re-exec with the venv interpreter. Without this, `import yt_dlp` fails with `ModuleNotFoundError`.
- **deno path must be absolute in --js-runtimes**: `--js-runtimes deno` alone fails because deno is not on the system PATH (it's at `/root/.deno/bin/deno`). Must use `--js-runtimes deno:/root/.deno/bin/deno`.
- **yt-dlp --dump-single-json output conflicts with download**: `--dump-single-json` writes metadata to stdout, which interferes with download progress output. Use it only in a separate `--skip-download` step, not during actual download.
- **SQLite Row dict conversion for LEFT JOIN**: When querying SQLite with `LEFT JOIN`, using `r["column_name"]` directly on a `Row` object can fail with `IndexError: No item with that key` in some versions. Safe pattern: `d = dict(r)` then `d["column_name"]` or `d.get("column_name")`.
- **yt-dlp search API must have timeout**: YouTube search via yt-dlp can hang indefinitely when JS challenge solving fails (node process crash, missing runtime, rate limiting). Always wrap `search()` in a `ThreadPoolExecutor` with a timeout (60s). Without timeout, the webapp blocks and nginx returns 504 Gateway Timeout. Example:
  ```python
  from concurrent.futures import ThreadPoolExecutor, TimeoutError
  with ThreadPoolExecutor(max_workers=1) as pool:
      future = pool.submit(search, keyword, options)
      return future.result(timeout=60)
  ```