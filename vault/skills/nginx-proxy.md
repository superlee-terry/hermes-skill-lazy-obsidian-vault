---
categories:
- nginx-proxy
description: 'Nginx deployment patterns for web apps: static frontend + API reverse
  proxy, Docker networking, and PM2 integration.'
name: nginx-proxy
summary: 'Nginx deployment patterns for web apps: static frontend + API reverse proxy,
  Docker networking, and PM2 integration.'
tags:
- nginx
- proxy
- deployment
- docker
triggers:
- nginx
- proxy
- deployment
- docker
---

# Nginx Proxy for Web Application Deployment

## When to Use

- Deploying a web application with Nginx reverse proxy
- Static frontend + API backend needs path-based routing
- Setting up HTTPS via self-signed or Let's Encrypt certs
- Configuring proxy headers, timeouts, and static file serving
- Integrating with PM2, Docker, or Kubernetes for backend management

## Basic Setup

1. **Static frontend** — Place compiled static files (HTML/JS/CSS) under a directory that Nginx serves, or use `root` / `alias` directives.

2. **API reverse proxy** — Add a `location` block:
```nginx
location ^~ /api/ {
    proxy_pass http://backend;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 120s;
    proxy_send_timeout 120s;
}
```

3. **Reload** — Copy config into container volume, then `docker exec nginx-proxy nginx -s reload`.

4. **Verify** — Test both static and API endpoints with `curl` or browser.

## Pitfalls

- See `references/nginx-pm2-python.md` for Docker-to-host networking and PM2 Python configuration issues.
- `proxy_pass` with trailing slash vs without: trailing slash causes path stripping, no trailing slash preserves the original URI.
- `^~` modifier stops further `location` matching — useful when you want to match a prefix and not be overridden by more specific patterns.
- Rewrite + proxy_pass: when using `rewrite ... break`, ensure the rewritten path matches a route that the backend actually handles.
- **Frontend path resolution when served under a prefix** (e.g. `/terry-era/video-collection/`): API fetch URLs must use absolute paths like `/terry-era/api/...`, NOT relative paths like `../api/` or `./api/`. Relative paths resolve from the browser's current URL, not the project root — `../api/` from `/terry-era/video-collection/` resolves to `/api/` which nginx treats as a static file and returns 404.
- **PM2 env variables not passed to Python scripts**: PM2's `env` config in `ecosystem.config.js` does NOT pass variables to Python scripts (only Node.js processes). Fix: use a Python wrapper that sets `os.environ` explicitly, or a shell wrapper that exports vars before `exec`.

## See Also

- `references/nginx-pm2-python.md` — Docker-to-host networking, PM2 Python port config, and Jinja2 + JavaScript conflicts.