---
categories:
- devops
description: Configure Hermes auxiliary model settings for 8 background tasks
name: hermes-auxiliary-config
summary: Configure Hermes auxiliary model settings for 8 background tasks
triggers: []
version: '1.1'
---

# Hermes Auxiliary Configuration Guide

## Source Files
- Config defaults: `hermes_cli/config.py` (~line 483)
- Client router: `agent/auxiliary_client.py`
- Task resolution: `_resolve_task_provider_model()` (~line 2280)

## 8 Auxiliary Tasks

### 1. vision — Multimodal (MUST support image input)
- Triggered by: `browser_vision`, `vision_analyze`, `camofox_vision`
- Source: tools/vision_tools.py, tools/browser_camofox.py
- Requires: Image/multimodal support. Non-vision models will FAIL.
- Timeout: 120s + download_timeout 30s
- Recommended: gemini-flash, gpt-4o-mini, glm-4v, qwen-vl

### 2. web_extract — Long text summarization
- Triggered by: Every web search result extraction
- Source: tools/web_tools.py (~line 456, `_resolve_web_extract_auxiliary()`)
- Input: Can be entire webpage, needs long context
- Timeout: 360s (6 min)
- Recommended: Long context + good summarization

### 3. compression — Context window auto-compression
- Triggered by: Conversation history exceeds compression threshold
- Source: run_agent.py (~line 1440), trajectory_compressor.py
- Input: Full conversation history
- Timeout: 120s
- Recommended: Good at extracting key info from long text

### 4. session_search — History search summarization
- Triggered by: `/history` command, session_search queries
- Source: tools/session_search_tool.py (~line 205)
- Timeout: 30s
- Recommended: Fast + cheap

### 5. skills_hub — Skill search and match
- Triggered by: `/skills` slash command (search, install)
- Source: hermes_cli/skills_hub.py
- Timeout: 30s
- Recommended: Fast + cheap

### 6. approval — Smart command approval
- Triggered by: `approvals.mode: smart` in config
- Source: tools/approval.py (~line 549, `_smart_approve()`)
- Calls: `call_llm(task="approval", temperature=0, max_tokens=16)`
- Output: Single word APPROVE/DENY/ESCALATE
- Timeout: 30s
- Recommended: Fast + cheap

### 7. mcp — MCP server sampling requests
- Triggered by: MCP servers requesting LLM sampling
- Source: tools/mcp_tool.py (~line 665)
- Task: General LLM inference on behalf of MCP servers
- Timeout: 30s
- Recommended: General-purpose

### 8. flush_memories — Session-end memory extraction
- Triggered by: End of conversation, auto-extracts durable facts
- Source: run_agent.py (~line 7565)
- May use tool calling for structured extraction
- Timeout: 60s
- Recommended: Good at distinguishing important vs trivial info

## Config Format (config.yaml)

```yaml
auxiliary:
  vision:
    provider: auto
    model: ""
    base_url: http://127.0.0.1:11434/v1
    api_key: ""
    timeout: 120
    download_timeout: 30
  web_extract:        # timeout: 360
    provider: auto
    model: ""
    base_url: http://127.0.0.1:11434/v1
    api_key: ""
    timeout: 360
  compression:        # timeout: 120
    provider: auto
    model: ""
    base_url: http://127.0.0.1:11434/v1
    api_key: ""
    timeout: 120
  session_search:     # timeout: 30
    provider: auto
    model: ""
    base_url: http://127.0.0.1:11434/v1
    api_key: ""
    timeout: 30
  skills_hub:         # timeout: 30
    provider: auto
    model: ""
    base_url: http://127.0.0.1:11434/v1
    api_key: ""
    timeout: 30
  approval:           # timeout: 30
    provider: auto
    model: ""
    base_url: http://127.0.0.1:11434/v1
    api_key: ""
    timeout: 30
  mcp:                # timeout: 30
    provider: auto
    model: ""
    base_url: http://127.0.0.1:11434/v1
    api_key: ""
    timeout: 30
  flush_memories:     # timeout: 60
    provider: auto
    model: ""
    base_url: http://127.0.0.1:11434/v1
    api_key: ""
    timeout: 60
```

**Note:** All auxiliary tasks now default **base_url** to `http://127.0.0.1:11434/v1`, which points to the local Ollama model (`llama://...`). The older default (`http://127.0.0.1:4000`) is deprecated and should be removed from any custom configuration. If you have existing `base_url` entries for auxiliary tasks, replace them with the URL above.

## Resolution Priority
1. Explicit provider/model/base_url args in code
2. Config file auxiliary.{task}.provider/model/base_url
3. `auto` chain: OpenRouter → Nous → Codex → Anthropic → direct API providers

## Pitfalls
- vision task with non‑vision model: Will fail. GLM series needs glm‑4v/glm‑5v‑turbo, not plain glm‑4.7.
- web_extract timeout 360s for reason, local models may need more.
- flush_memories with thinking models: ensure max_tokens ≥ 8192.
- auxiliary fields limited to 6: {provider, model, base_url, api_key, timeout} + task‑specific extras only.
- Vision Invocation Conditions: Hermes calls the vision sub‑task only when the user explicitly requests image analysis, an internal step requires a screenshot, and `vision.enabled` is true.

## Changes in v1.1 (April 21, 2026)
- Updated all auxiliary task **base_url** values to use Ollama (`http://127.0.0.1:11434/v1`).
- Documented the deprecation of the old `http://127.0.0.1:4000` endpoint.
- Added an explicit note for config users.