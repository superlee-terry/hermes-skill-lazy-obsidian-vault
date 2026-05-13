---
categories:
- fastapi-static-html
description: Serve static HTML with FastAPI without Jinja2 template engine
name: fastapi-static-html
summary: Serve static HTML with FastAPI without Jinja2 template engine
triggers: []
---

# FastAPI Static HTML

Serve static HTML with FastAPI without Jinja2 template engine.

## Approach
Use `StaticFiles` mount + `FileResponse` for individual pages.

## Example
```python
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

app = FastAPI()
BASE_DIR = Path(__file__).parent

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = BASE_DIR / "static" / "index.html"
    if html_path.exists():
        return FileResponse(html_path)
    return JSONResponse({"error": "index.html not found"}, status_code=500)
```

## Pitfall: Jinja2 conflicts with JavaScript
When using Jinja2 templates, JavaScript code with `{{ }}` and `{% %}` gets parsed as template variables.

**Solutions (in order of preference):**
1. **Static HTML + FileResponse** — no template engine needed for simple pages
2. **`{% raw %}` / `{% endraw %}`** — wraps JavaScript in Jinja2 templates
3. **Escape manually** — `{{ variable|tojson }}` for data passing

## Pitfall: Duplicate FastAPI app creation
When modifying an existing FastAPI file, avoid creating two `app = FastAPI(...)` lines. Clean up old references.

## Pitfall: HTMLResponse import
When switching from Jinja2 to static HTML, make sure `HTMLResponse` is still imported — `FileResponse` is in `fastapi.responses` but `HTMLResponse` is separate.

## Pitfall: escapeJson for onclick attributes
When embedding dynamic data in HTML `onclick` attributes using single-quote delimiters, `JSON.stringify` output MUST escape both `'` and `"`:
```js
function escapeJson(obj) {
    return JSON.stringify(obj).replace(/'/g, "\\'").replace(/"/g, '&quot;');
}
```
Escaping only one type causes truncated JS (e.g., `"` in JSON breaks the HTML attribute, `'` breaks the JS string).

## Pitfall: Tailwind CSS CDN is JavaScript, not CSS
`https://cdn.tailwindcss.com/X.X.X` serves a **JavaScript bundle** (not CSS). It parses Tailwind class names at runtime and injects CSS. For production, compile locally:
1. `npm init -y && npm install -D tailwindcss`
2. `npx tailwindcss init`
3. `npx tailwindcss -i input.css -o dist/tailwind.css`
4. Link `<link href="dist/tailwind.css" rel="stylesheet">` instead of the CDN script.