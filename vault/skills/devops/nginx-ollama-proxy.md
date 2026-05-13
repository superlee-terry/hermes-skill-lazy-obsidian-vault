---
categories:
- devops
description: Nginx transparent proxy for multi-node Ollama load balancing. Use when
  LiteLLM tool-call fidelity issues are encountered or when hardware load balancing
  is preferred over LiteLLM's model-aware routing.
name: nginx-ollama-proxy
summary: Nginx transparent proxy for multi-node Ollama load balancing. Use when LiteLLM
  tool-call fidelity issues are encountered or when hardware load balancing is preferred
  over LiteLLM's model-aware routing
tags:
- nginx
- ollama
- load-balancing
- proxy
- openai-compat
triggers:
- nginx
- ollama
- load-balancing
- proxy
- openai-compat
---

# Nginx Proxy for Ollama Load Balancing

## When to Use

**Choose Nginx proxy over LiteLLM when:**
- Tool/function-calling fidelity is critical (LiteLLM may strip or corrupt tool definitions)
- Multiple Ollama nodes on same machine need load balancing
- Simple HTTP passthrough with zero payload inspection
- SSE streaming must be preserved byte-for-byte

**Choose LiteLLM when:**
- Model-aware routing needed (different models on different nodes)
- Fallback between models, per-model rate limiting
- API key management, token spend tracking

## File Location
Config: `/mnt/data/Docker/nginx/conf.d/ollama-balanced.conf`
Docker container name: `nginx` (from `/mnt/data/Docker/nginx/docker-compose.yml`)
Docker compose dir: `/mnt/data/Docker/nginx/`

## Configuration Template

```nginx
upstream ollama_balanced {
    server 127.0.0.1:11434 weight=1;
    server 127.0.0.1:11435 weight=1;
}

server {
    listen 21434;
    server_name localhost;

    # OpenAI-compatible API
    location /v1/ {
        proxy_pass http://ollama_balanced;
        proxy_buffering off;              # MUST: SSE streaming
        proxy_cache off;
        proxy_read_timeout 300s;
        proxy_set_header Connection '';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_http_version 1.1;
    }

    location /api/ {
        proxy_pass http://ollama_balanced;
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
        proxy_set_header Connection '';
        proxy_http_version 1.1;
    }

    location /health {
        access_log off;
        return 200 '{"status":"healthy","proxy":"ollama-balanced"}';
        default_type application/json;
    }
}
```

## Key Configuration Points

- `proxy_buffering off` — ESSENTIAL for SSE. Enables Hermes to receive streaming tokens.
- `proxy_read_timeout 300s` — Long inference tasks (29min on MI50) need generous timeout.
- `proxy_http_version 1.1` + `Connection ''` — Enables keep-alive.
- Round-robin by default; use `weight=N` for uneven GPU resources.
- **No path rewriting** — `/v1/chat/completions` forwarded verbatim to preserve tool definitions.

## Apply & Verify

```bash
# Reload nginx (config mounted via bind mount in docker-compose)
docker compose -f /mnt/data/Docker/nginx/docker-compose.yml exec nginx nginx -s reload

# Test proxy health
curl -s http://127.0.0.1:21434/health

# Verify tool-calling works (send tools parameter, check it returns through)
curl -s http://127.0.0.1:21434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3.6:35b-a3b","messages":[{"role":"user","content":"test"}],"tools":[{"type":"function","function":{"name":"test_tool","parameters":{"type":"object","properties":{},"type":"object"}}}]}'
```

## On This System

**Current state** (2026-04-23):
- Ollama Node 1: `127.0.0.1:11434` ✅ (7 models)
- Ollama Node 2: `127.0.0.1:11435` ❌ (not running)
- Nginx Proxy: `127.0.0.1:21434` ✅ (config ready, 1-of-2 upstreams active)

**Ollama instances models** (Node 1: 11434):
- qwen3.6-agent:latest (22.3GB)
- nemotron-cascade-2:30b-a3b-q4_K_M (22.6GB)
- qwen3.5:2b-q4_K_M (1.8GB)
- nemotron-3-nano:30b-a3b-q4_K_M (22.6GB)
- qwen3.6:35b-a3b (22.3GB)
- glm-4.7-flash:latest (17.7GB)
- qwen3-embedding:latest (4.4GB)

## Troubleshooting

### SSE streaming appears to hang
- Check `proxy_buffering off` is set (not `on`)
- Ensure `proxy_read_timeout 300s` (or more for long models)

### Only one upstream working
- Verify both Ollama containers are running: `docker ps | grep ollama`
- Test each directly: `curl http://127.0.0.1:11434/api/tags`

### Tools not working through proxy
- Nginx is transparent passthrough — tools go through unmodified
- If tools fail, check the target Ollama node directly
- This was the original reason to choose Nginx over LiteLLM

### High connection count on nginx
- Add `keepalive 64;` to `upstream {}` block
- Add `proxy_set_header Connection 'keep-alive';` to `server {}`