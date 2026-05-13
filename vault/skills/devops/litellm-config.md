---
categories:
- devops
description: Configure and troubleshoot LiteLLM proxy for local Ollama models. Covers
  config file location, think-mode pitfalls, and restart procedures.
name: litellm-config
summary: Configure and troubleshoot LiteLLM proxy for local Ollama models. Covers
  config file location, think-mode pitfalls, and restart procedures.
tags:
- litellm
- ollama
- proxy
- docker
triggers:
- litellm
- ollama
- proxy
- docker
---

# LiteLLM Proxy Configuration

## File Location
Config: `/mnt/data/Docker/litellm/config.yaml`
Docker container name: `litellm`

## Restart
```bash
docker restart litellm
```
Wait ~5 seconds after restart before testing.

## Test a model
```bash
curl -s http://127.0.0.1:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-empty" \
  -d '{"model":"MODEL_NAME","messages":[{"role":"user","content":"hello"}]}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d, indent=2, ensure_ascii=False))"
```

## Pitfall: Think-mode models return empty content

**Symptom**: Models with thinking capability (e.g. `qwen3.6-35b-a3b`) return `"content": ""` with non-zero `completion_tokens`.

**Root cause**: The thinking/reasoning tokens consume the `max_tokens` budget first. If `max_tokens` is too small (e.g. 200), there's no budget left for the actual response content, resulting in an empty string.

**Fix**: Set a generous `max_tokens` in the LiteLLM config for think-mode models:
```yaml
- model_name: qwen3.6-35b-a3b
  litellm_params:
    model: ollama/qwen3.6:35b-a3b
    api_base: http://172.17.0.1:11434
    max_tokens: 8192
```

**Prevention**: Always set `max_tokens >= 4096` for any model that uses thinking/reasoning chains. Ollama's internal API uses `num_predict` which LiteLLM maps to `max_tokens` — if unset, defaults can be too low.

## CRITICAL: LiteLLM max_tokens has NO floor enforcement

LiteLLM does **NOT** support a minimum/floor value for `max_tokens`. The config `max_tokens` is only a **default** — if the caller passes `max_tokens=50`, it completely overrides the config value.

**Verified** (LiteLLM v1.82.6):
- Source: `common_request_processing.py` L690 — `if user_max_tokens: self.data["max_tokens"] = user_max_tokens`
- `LiteLLM_Params` has no `min_tokens` / `max_tokens_floor` field
- No environment variable for min enforcement
- `litellm.DEFAULT_MAX_TOKENS = 4096` is only used as fallback, not as a floor

**Impact on Hermes**: If Hermes (or any caller) sends a small `max_tokens` (e.g. 200 for auxiliary tasks), think-mode models will silently return empty content. This cannot be fixed at the LiteLLM config level.

**Mitigation options**:
1. Use `-nothink` variants for any automated/auxiliary calls (recommended)
2. Ensure callers pass `max_tokens >= 1024` for think-mode models
3. Write a LiteLLM custom guardrail plugin to enforce a floor (complex)

## Nothink mode
For models that have a think variant, create a separate entry with `think: false`:
```yaml
- model_name: qwen3.6-35b-a3b-nothink
  litellm_params:
    model: ollama/qwen3.6:35b-a3b
    api_base: http://172.17.0.1:11434
    extra_body:
      think: false
```
Nothink mode doesn't need large `max_tokens` since there's no thinking overhead.

## Hermes config reference (updated 2026-04-18)

### custom_providers
Only 2 providers needed — ZAI for main model, LiteLLM for local:
```yaml
custom_providers:
- name: zai
  base_url: https://open.bigmodel.cn/api/coding/paas/v4
  api_key: <ZAI_API_KEY>
  api_mode: chat_completions
  model: glm-5.1
- name: litellm
  base_url: http://127.0.0.1:4000
  api_key: sk-empty
  api_mode: chat_completions
  model: qwen3.6-35b-a3b-nothink
```

### auxiliary models (all via ZAI GLM-5-Turbo)
ALL 8 auxiliary services (vision, web_extract, compression, session_search, skills_hub, approval, mcp, flush_memories) use ZAI online API — no think-mode issues, fast and stable:
```yaml
auxiliary:
  vision:   # (and all others)
    provider: custom:zai
    model: GLM-5-Turbo
    base_url: https://open.bigmodel.cn/api/coding/paas/v4
    api_key: <ZAI_API_KEY>
```

**Why ZAI for auxiliary**: Online API handles thinking internally (content never empty). No local GPU dependency. GLM-5-Turbo is cheaper and faster than GLM-5.1.

**Change history**:
- 2026-04-18: Switched from Ollama qwen3.5 → LiteLLM qwen3.6-nothink → ZAI GLM-5-Turbo

## Debugging: Tracing request sources

When you see unexpected API call volume on LiteLLM or Ollama, use this approach:

### 1. LiteLLM default logs are useless for debugging
`docker logs litellm` at default level only shows `INFO: IP - "POST /chat/completions 200 OK"` — NO model name, NO token count, NO client identity. To trace requests:
- Enable `set_verbose: true` in LiteLLM config (restart required) — logs full request/response but VERY verbose
- Or enable LiteLLM DB (`database_url:`) for `/spend/keys` endpoint
- Or use Docker network tracing (see below)

### 2. Docker network topology (critical)
```
ai-goofish-monitor (172.27.0.2, ai-goofish-monitor_default network)
  → http://192.168.100.110:4000 → host NIC → docker-proxy → LiteLLM

LiteLLM (172.17.0.2, bridge network)
  → http://172.17.0.1:11434 → docker0 gateway → host port 11434
  → docker-proxy → ollama-mi50 container (172.19.0.2, docker_default network)

ollama-mi50 (172.19.0.2, docker_default network)
  - Host port binding: 0.0.0.0:11434 → container:11434
  - All requests appear from gateway IP (172.19.0.1 or 127.0.0.1)
```

**Key insight**: ollama-mi50 is on `docker_default` network, NOT `bridge`. LiteLLM accesses it via `172.17.0.1:11434` which goes through host port binding → docker-proxy → ollama-mi50. This works but adds latency.

### 3. Container timezone != host timezone
- ollama-mi50 uses UTC, host uses CST (UTC+8)
- Ollama log timestamp `00:41 UTC` = `08:41 CST`
- Always check: `docker exec <container> date`

### 4. Identifying request sources
```bash
# Check which containers connect to LiteLLM
docker network inspect bridge --format '{{range .Containers}}{{.Name}} {{end}}'
ss -tnp | grep ':4000'

# Check all Docker container IPs and networks
docker network inspect $(docker network ls -q) --format '{{.Name}} {{range .Containers}}{{.Name}} {{.IPv4Address}}{{end}}'

# Count LiteLLM requests by status
docker logs litellm 2>&1 | grep 'POST.*chat/completions' | grep -oE '[0-9]{3} (OK|Bad Request|Internal Server Error)' | sort | uniq -c

# Ollama request duration analysis (spot slow model inference)
docker logs ollama-mi50 2>&1 | grep '\\[GIN\\].*POST.*generate' | tail -20
```

### 5. Known LiteLLM clients on this system
- **ai-goofish-monitor** (`/mnt/data/Docker/ai-goofish-monitor/.env`): `OPENAI_BASE_URL=http://192.168.100.110:4000`, model `qwen3.6-35b-a3b-nothink`. Runs every 30 min, calls AI analysis per new item found.
- **Hermes**: auxiliary tasks (when configured for LiteLLM) + main model sessions using qwen3.6

### 6. Ollama performance expectations
- qwen3.6:35b-a3b on MI50 dual-GPU: **3-29 minutes per request** (model-dependent)
- Multiple concurrent requests will queue — Ollama processes serially by default
- If `session_search` timeout is 60s but model inference takes 15+ min, every call will timeout and retry 3x

### What was removed
- `ollama` custom_provider (direct Ollama access) — replaced by LiteLLM proxy
- `local-qwen3.6` custom_provider (think mode) — merged into `litellm` with nothink
- `litellm` custom_provider — kept for delegation/optional use, but auxiliary no longer uses it