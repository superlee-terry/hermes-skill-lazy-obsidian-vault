---
categories:
- devops
description: Set up Nginx to load-balance multiple Ollama instances, preserving tools/SSE
  capability better than LiteLLM proxy.
name: ollama-nginx-loadbalance
summary: Set up Nginx to load-balance multiple Ollama instances, preserving tools/SSE
  capability better than LiteLLM proxy.
triggers: []
---

# Ollama Nginx Load Balancing

Proxy and load-balance multiple Ollama instances via Nginx for Hermes/LLM use cases.

## When to use
- You have 2+ Ollama nodes (e.g., multi-GPU) and want to distribute requests evenly.
- LiteLLM is unsuitable (known issues with breaking `tools` function calling or SSE handling).
- Need transparent HTTP proxy to preserve strict JSON payloads (tool definitions).

## Setup Steps

### 1. Verify Ollama Nodes
Ensure both nodes serve Ollama's native API or OpenAI-compatible format.
- Check `http://<host>:11434/api/tags` manually.
- Confirm `--api-format openai` flag is set if using OpenAI-compatible endpoint.

### 2. Resolve Docker Networks (CRITICAL: containers must share a network)
**Pitfall:** Ollama containers and Nginx are often on DIFFERENT Docker networks. Even if host ports are mapped, Nginx CANNOT reach them cross-network.

Steps:
- Find Nginx network: `docker inspect nginx-proxy --format '{{.NetworkSettings.Networks}}'`
- Find all networks: `docker network ls --format "{{.Name}}"`
- If Ollama containers are NOT on the same network as Nginx, connect them:
  `docker network connect <nginx-network> <ollama-container>`
- Get container IPs on shared network:
  `docker network inspect <nginx-network> --format '{{range .Containers}}{{.Name}}:{{.IPv4Address}}\n{{end}}'`

### 2b. Resolve Ollama Container Internal Port
**Pitfall:** Docker port mapping is host-side ONLY (e.g., `0.0.0.0:11435->11434`). **Ollama always listens on port 11434 internally.** The upstream MUST target the container-internal port `11434`, NOT the host-mapped port (11435).

Verify: `docker inspect <ollama-container> --format "{{json .NetworkSettings.Ports}}"`

### 3. Nginx Configuration
Create `/path/to/nginx/conf.d/ollama-balance.conf`. Use the **container IPs on the shared network** obtained in Step 2:
```nginx
upstream ollama_cluster {
    server 172.23.0.x:11434 weight=1;  # container-IP:11434 (NOT host-mapped port)
    server 172.23.0.y:11434 weight=1;  # container-IP:11434
}

server {
    listen 21434;

    location /api/ {
        proxy_pass http://ollama_cluster;
        proxy_buffering off; # REQUIRED for SSE streaming
        proxy_cache off;
        proxy_set_header Connection '';
        proxy_read_timeout 300s;
    }

    location /v1/ {
        proxy_pass http://ollama_cluster/v1/;
        proxy_buffering off;
        proxy_cache off;
        proxy_set_header Connection '';
        proxy_read_timeout 300s;
    }
}
```

### 4. Docker Compose Port Mapping
Add port:
```yaml
ports:
  - "21434:21434"
```

### 5. Reload & Verify
```bash
docker exec nginx-proxy nginx -t
docker exec nginx-proxy nginx -s reload
```

## Pitfalls
- **`proxy_buffering off;`** is mandatory for SSE. Without it, Hermes will hang.
- **Docker Compose `ports` changes** require full `down` + `up -d`.
- **Nginx `upstream` variables** — variables are NOT supported. Use direct IP addresses.
- **502 Bad Gateway** — upstream IP wrong, network not bridged, or wrong port.
- **Ollama container port**: Docker port mapping is host-side only. Ollama **always listens on port 11434 internally**. If you mapped host port 11435→container 11434, upstream must use container-IP:11434, NOT container-IP:11435.
- **Upstream keepalive breaks round-robin**: Using `proxy_set_header Connection ''` (or `keepalive` directive) causes Nginx to reuse the FIRST upstream connection for all subsequent requests, making round-robin appear "broken". **Fix:** Use `proxy_set_header Connection 'close';` in each location block to force per-request upstream selection.

## Updating Weights
Modify `weight=N` in `upstream` to control load ratio.