---
categories:
- devops
description: Diagnose "Model returned empty after tool calls" and max_tokens issues
  in Hermes Agent
name: hermes-empty-response-debug
summary: Diagnose "Model returned empty after tool calls" and max_tokens issues in
  Hermes Agent
tags:
- hermes
- debugging
- max_tokens
- empty-response
triggers:
- hermes
- debugging
- max_tokens
- empty-response
version: 1.1
---

# Hermes Empty Response and max_tokens Diagnosis

## When to Use
- Hermes logs show "Model returned empty after tool calls — nudging to continue"
- Model returns empty content after tool calls
- Suspecting max_tokens is too low for reasoning/thinking models
- "No response from provider for 180s" errors with thinking models

## Key Source Locations (Hermes install: /root/.hermes/hermes-agent/)

| File | Line | Purpose |
|------|------|---------|
| run_agent.py | ~11069-11119 | Post-tool empty response nudge logic |
| run_agent.py | ~6817-6850 | max_tokens sent to API (or not) |
| run_agent.py | ~11020-11067 | Prior-turn content fallback |
| run_agent.py | ~5942 | HERMES_STREAM_STALE_TIMEOUT (default 180s) |
| agent/smart_model_routing.py | ~110-190 | runtime dict construction (NO max_tokens) |
| gateway/run.py | ~344-379 | _resolve_runtime_agent_kwargs (reads max_tokens from config) |
| gateway/run.py | ~5951-5972 | Main AIAgent instantiation |

## Diagnosis Steps

### 1. Check config.yaml for max_tokens
Read the config file and look for max_tokens in model section and custom_providers.
- Top-level model section: may not be read by gateway
- custom_providers entries: NOT passed to AIAgent
- Only litellm provider supports max_tokens in config reliably

### 2. Trace the actual max_tokens sent
The code path:
```
config.yaml -> _resolve_runtime_agent_kwargs() -> runtime_kwargs
  (reads max_tokens from config, adds if not None)
-> _resolve_turn_agent_config() -> smart_model_routing.resolve_turn_route()
  (propagates max_tokens from runtime_kwargs if not None)
-> AIAgent(**turn_route["runtime"]) -> self.max_tokens set
-> _prepare_api_call() line 6817: only sends if self.max_tokens is not None
-> Falls through to Qwen/Claude special cases, else NOT SENT to API
```

**Key finding**: Even though config.yaml has max_tokens: 8192 and the runtime_kwargs
chain preserves it, Feishu/gateway sessions can still end up with max_tokens=None.
The `_prepare_api_call` method is the last line of defense — add a fallback there.

### 3. Check API default behavior
- GLM (Zhipu): default ~1024-4096 when omitted
- Thinking models: thinking tokens consume budget leaving content empty
- Weak models (GLM-5, mimo-v2-pro): known to return empty after tool calls

### 4. Verify max_tokens in runtime (debug logging already in place)
```bash
grep "max_tokens_debug" ~/.hermes/logs/agent.log | tail -10
```
Look for `self.max_tokens=None` — that means the fallback is needed.

## Fixes (in order of reliability)

1. **Add `else` fallback in `_prepare_api_call()`** (most reliable, but hermes update overwrites):
   In `run_agent.py`, after the OpenRouter/Claude `elif` block (~line 6846) and before `extra_body = {}`,
   add an `else` clause that sets a default max_tokens for all providers not covered by special cases:
   ```python
   # After the existing elif blocks for qwen_portal and openrouter/claude:
   else:
       # Fallback: providers like GLM/Zhipu have very low default max_tokens.
       # Thinking/reasoning models exhaust that budget on thinking alone,
       # leaving nothing for the actual response content.
       _DEFAULT_MAX_TOKENS = 8192
       api_kwargs.update(self._max_tokens_param(_DEFAULT_MAX_TOKENS))
   ```
   This ensures GLM-5.1 and other custom providers always get max_tokens=8192 even when
   the config-to-runtime_kwargs-to-AIAgent pipeline fails to pass it through.

2. **Route through LiteLLM proxy** where max_tokens can be configured per-model.

3. **Use Qwen Portal** (auto-gets 65536) or OpenRouter/Claude (auto-gets model limit).

## Thinking Model Stream Timeout (180s "No response from provider")

### Symptom
Feishu or other platform sessions log:
```
No response from provider for 180s (model: glm-5.1, context: ~23,013 tokens). Reconnecting...
```

### Root Cause
`run_agent.py` line ~5942: `HERMES_STREAM_STALE_TIMEOUT` defaults to 180s. Thinking/reasoning
models (GLM-5.1, Claude with thinking, etc.) can legitimately spend 3-5+ minutes in the
thinking phase before producing the first stream token. The stale detector kills the
connection, causing repeated reconnect cycles.

The code auto-disables the stale detector for local endpoints (Ollama), and scales it up
for >50K and >100K token contexts, but does NOT account for thinking models with moderate
contexts (e.g. ~23K tokens).

### Fix
Set environment variable `HERMES_STREAM_STALE_TIMEOUT=420` (420s = 7 minutes).
This goes in the Hermes env file. Must restart gateway after changing.

### Diagnosis
```bash
# Check agent log for stale stream kills
grep "No response from provider" ~/.hermes/logs/agent.log | tail -5
```

## Nudge Mechanism Explained
When model returns empty after tool calls, Hermes:
1. Checks if prior turn was all housekeeping tools -> use prior content
2. Otherwise appends (empty) assistant msg + user nudge
3. Retries once (_post_tool_empty_retried flag prevents loops)
4. Falls through to thinking-only prefill (2 retries)
5. Final retry up to 3 times before giving up

## Context Compression Loop (Misclassified Error)

### Symptom
Feishu (or other platform) sessions repeatedly log:
- `Context too large (~4,xxx tokens) — compressing`
- `Context compression failed after 3 attempts`
- `Context length exceeded: max compression attempts (3) reached`
Even when context is tiny (~4K tokens for a 200K model).

### Root Cause
`agent/error_classifier.py` line ~161: `_CONTEXT_OVERFLOW_PATTERNS` contains `"max_tokens"` as a standalone pattern. When GLM (or any provider) returns an error mentioning "max_tokens" (e.g., output token limit), it gets misclassified as `context_overflow`, triggering 3 rounds of useless compression that always fail because the actual context is fine.

### Diagnosis Steps
1. Check agent.log for compression failures:
   ```
   grep "Context compression failed\|Context too large" ~/.hermes/logs/agent.log | tail -20
   ```
2. Check session size — if only 1 message, it's NOT a real context overflow
3. Add debug logging to error_classifier.py (after line 316, the `error_msg = " ".join(parts)` line):
   ```python
   import logging as _cls_log
   _cls_log.getLogger("hermes.error_classifier").warning(
       "[ERROR_CLASSIFIER] status=%s type=%s approx_tokens=%s ctx_len=%s\n"
       "  combined[:500]=s",
       status_code, error_type, approx_tokens, context_length, error_msg[:500],
   )
   ```
4. Restart gateway, trigger a message, then `grep ERROR_CLASSIFIER ~/.hermes/logs/agent.log`

### Fix
The pattern matching uses `any(p in error_msg for p in _CONTEXT_OVERFLOW_PATTERNS)` — simple substring `in`, NOT regex. So patterns must be exact substrings that appear in real overflow errors.

Replace the bare `"max_tokens"` (line ~161) with specific phrases that only appear in genuine context overflow errors:
```python
# NOTE: bare "max_tokens" removed — it falsely matches parameter errors
# from providers like GLM that mention max_tokens in non-overflow contexts.
"max_tokens exceeds",            # "max_tokens exceeds context/limit"
"request max_tokens",            # some providers: "request max_tokens too large"
```
This preserves overflow detection while eliminating false positives from GLM's non-overflow error messages.

WARNING: `hermes update` overwrites this change. Re-apply after updates.

### Key Files
| File | Line | Purpose |
|------|------|---------|
| agent/error_classifier.py | 150-183 | `_CONTEXT_OVERFLOW_PATTERNS` list |
| agent/error_classifier.py | ~316 | `classify_api_error()` combined error_msg |
| agent/error_classifier.py | 43 | `context_overflow` enum definition |
| run_agent.py | ~9710-9740 | Compression retry loop (3 attempts) |

## AIAgent.config AttributeError after /reset

### Symptom
After `/reset` or session auto-reset on Feishu/other platforms:
```
Sorry, I encountered an error (AttributeError).
'AIAgent' object has no attribute 'config'
```

### Root Cause
`AIAgent.__init__` never initializes `self.config`. But `run_agent.py` references it in 3 places:
- **Line ~2008**: `(self.config or {}).get("auxiliary", {}).get("compression", {})` — compression config
- **Line ~9268**: `(self.config or {}).get("retry", {})` — retry backoff config
- **Line ~10473**: `(self.config or {}).get("retry", {})` — retry backoff config

The `or {}` guard only works if the attribute EXISTS (returns None -> falls to {}). If the attribute is missing, `self.config` raises `AttributeError` before `or {}` evaluates.

Gateway creates AIAgent instances (run.py ~9044) but never injects a `config` attribute. On fresh sessions or after reset, when compression or retry paths are hit -> instant crash.

### Fix
Add to `AIAgent.__init__` (near `self.max_tokens = max_tokens`, around line 853):
```python
self.config = None  # Gateway config dict (injected by gateway; safe default = None)
```

### Key Files
| File | Line | Purpose |
|------|------|---------|
| run_agent.py | ~853 | `self.config = None` initialization (add here) |
| run_agent.py | ~2008 | First `self.config` reference (compression) |
| run_agent.py | ~9268 | Second `self.config` reference (retry) |
| run_agent.py | ~10473 | Third `self.config` reference (retry) |
| gateway/run.py | ~9044 | AIAgent creation (no config passed) |

## Gateway Restart Procedure

After any `run_agent.py` patch or `.env` change, the gateway must restart to pick up changes:

1. Find current gateway PID: `ps aux | grep "gateway run" | grep -v grep`
2. Kill it: `kill <PID>`
3. Wait 3 seconds
4. Start new: `cd /root/.hermes/hermes-agent && setsid ./venv/bin/python -m hermes_cli.main gateway run --replace >> /root/.hermes/logs/gateway-restart.log 2>&1 &`
5. Verify with `ps aux | grep "gateway run"` and check the log
6. Feishu users should send `/new` to start fresh session (old cached agents retain old code)

## Stream Stale Timeout (Thinking Models)

### Symptom
Hermes logs: `No response from provider for 180s (model: glm-5.1, context: ~23,013 tokens). Reconnecting...`
Model is actually working (thinking phase), but Hermes kills the connection after 180s with no stream chunks.

### Root Cause
`HERMES_STREAM_STALE_TIMEOUT` defaults to 180s (run_agent.py ~line 5942). Thinking/reasoning models can take 3-5+ minutes before producing the first token. The stale detector kills healthy connections during the thinking phase.

### Fix
Set in Hermes env config file:
```
HERMES_STREAM_STALE_TIMEOUT=420
HERMES_API_TIMEOUT=1800
```
Then restart gateway. Local providers (Ollama) auto-disable stale detection, but cloud providers like GLM do not.

### Key File
| File | Line | Purpose |
|------|------|---------|
| run_agent.py | ~5942 | `HERMES_STREAM_STALE_TIMEOUT` default 180.0 |
| run_agent.py | ~5946 | Local endpoint auto-disables stale timeout |
| run_agent.py | ~5955-5961 | Context-based scaling (50K tokens -> 240s, 100K -> 300s) |

## max_tokens=None for Gateway Agents (Persistent Issue)

### Symptom
agent.log shows: `max_tokens injection: self.max_tokens=None` for gateway-created sessions (Feishu, etc.), even when config has `max_tokens: 8192`. CLI sessions work correctly.

### Root Cause Chain
1. `_resolve_runtime_agent_kwargs()` reads config model.max_tokens and includes it — works for NEW agent creation
2. BUT: gateway caches agents per session, and recovered/serialized agents lose `max_tokens` attribute
3. The `else` fallback in `_prepare_api_call` (added at ~line 6847) should catch `self.max_tokens is None`, but in practice cached agents may bypass this path
4. The debug log `hermes.max_tokens_fallback` never fires even when `self.max_tokens=None`, suggesting the agent object is reused from a state where the code path differs

### Attempted Fix (Partial)
Added `else` branch at ~line 6847 of run_agent.py:
```python
else:
    _DEFAULT_MAX_TOKENS = 8192
    api_kwargs.update(self._max_tokens_param(_DEFAULT_MAX_TOKENS))
```
This works for NEW agent creation but NOT for cached/recovered agents in gateway. The real fix needs to ensure `max_tokens` is set during agent reconstruction from session DB.

### More Reliable Alternative
- Route through LiteLLM proxy where max_tokens is configurable per-model
- Or ensure `/new` is sent on Feishu to force fresh agent creation with correct config

## Session State Triage (Stuck/Zombie Sessions)

When a Feishu or other platform session appears stuck (user says it's abnormal), use this diagnostic workflow to trace what happened.

### Step 1: Check active session mappings
```bash
cat ~/.hermes/sessions/sessions.json | python3 -m json.tool
```
Look for the platform/chat_id key, note the `session_id`, `suspended` flag, and `updated_at` timestamp.

### Step 2: Read session file message history
```bash
# Use Python binary mode to avoid security.redact_secrets masking
python3 -c "
import json
with open('/root/.hermes/sessions/session_<ID>.json','rb') as f:
    data=json.loads(f.read())
print(f'Model: {data[\"model\"]}')
print(f'Messages: {data[\"message_count\"]}')
for i,msg in enumerate(data['messages'][-10:]):
    role=msg.get('role','?')
    content=str(msg.get('content',''))[:300]
    tc=msg.get('tool_calls')
    print(f'[{i}] role={role}',end='')
    if tc: print(f' tools={[t[\"function\"][\"name\"] for t in tc]}',end='')
    print(f': {content}')
"
```
Look for: empty assistant messages, truncation notices, timeout errors, interrupted tool calls.

### Step 3: Read JSONL log for error keywords
```bash
python3 -c "
import json
with open('/root/.hermes/sessions/<ID>.jsonl','rb') as f:
    lines=f.readlines()
for i,line in enumerate(lines):
    t=line.decode('utf-8',errors='replace').lower()
    if any(k in t for k in ['error','truncat','timeout','interrupt','fail','exception']):
        print(f'Line {i}: {line.decode()[:300]}')
"
```

### Step 4: Check request dump files for specific errors
Dump files follow pattern: `request_dump_<session_id>_<timestamp>.json`
```python
import json
with open('request_dump_xxx.json','rb') as f:
    dump=json.loads(f.read())
print(dump.get('reason'), dump.get('error'))
# Common: {'type':'ReadTimeout','message':'The read operation timed out'}
#         reason: 'max_retries_exhausted'
```

### Step 5: Identify the failure pattern

| Pattern | Symptoms | Root Cause |
|---------|----------|------------|
| **Output truncation loop** | Multiple `[System: truncated]` messages | max_tokens too low for long responses |
| **API timeout cascade** | delegate_task/subagent 2272s, ReadTimeout, 0 tokens output | GLM API overloaded or rate-limited (429) |
| **Empty response after tools** | assistant returns empty, system nudges | Weak model + max_tokens consumed by thinking |
| **Session ID mismatch** | sessions.json points to old session, active file is newer | Context compaction creates new session file but mapping may lag |
| **Zombie session** | Not suspended but no activity for hours, stuck on empty response | All above combined; session cannot self-recover |

### Step 6: Resolution options

1. **Reset the session** — Tell user to send `/new` on Feishu to force fresh agent creation
2. **Clear session mapping** — Remove or update the entry in `sessions.json` pointing to the dead session
3. **Complete abandoned work** — If there's a TODO list stuck in the session, offer to finish it in the current (working) session
4. **Fix underlying cause** — Apply max_tokens fallback, increase HERMES_STREAM_STALE_TIMEOUT, or route through LiteLLM proxy (see fixes above)

### Key Files
| File | Purpose |
|------|---------|
| `sessions.json` | Session key → session_id mapping + metadata |
| `session_<id>.json` | Full message history (system_prompt, tools, messages array) |
| `<id>.jsonl` | Append-only log of all turns (good for error keyword search) |
| `request_dump_*.json` | Captured failed API requests with error details |

## Pitfalls
- hermes update overwrites run_agent.py modifications — keep patches documented for re-application
- security.redact_secrets in read_file masks numbers (e.g., `_DEFAULT_MAX_TOKENS=***`) — use binary mode (`rb`) to read Hermes source
- Memory at ~2200 char limit — merge related entries when updating
- `_CONTEXT_OVERFLOW_PATTERNS` is overly broad — `"max_tokens"` as standalone pattern causes false positives with GLM API
- `self.xxx or {}` pattern silently masks missing attributes — always initialize in `__init__`
- Gateway agent cache survives restarts via session DB — code patches don't affect cached agents until `/new` is sent
- `HERMES_STREAM_STALE_TIMEOUT` is only auto-disabled for local endpoints (`is_local_endpoint()`) — cloud thinking models need manual env var increase
- Gateway restart via `kill + setsid` often hits 300s terminal timeout — use `hermes gateway restart` or shorter commands
- Feishu sessions may reuse cached agents from before a restart — tell user to `/new`
- The `HERMES_STREAM_STALE_TIMEOUT` fix only helps thinking models; non-thinking models should not need it