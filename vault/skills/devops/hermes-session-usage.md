---
categories:
- devops
description: Query per-session token usage from Hermes session store. hermes status
  doesn't show this; use sessions export instead.
name: hermes-session-usage
summary: Query per-session token usage from Hermes session store. hermes status doesn't
  show this; use sessions export instead.
triggers: []
version: 1.0
---

# Hermes Session Usage Query

Query per-session token usage from Hermes session store.

## Context

`hermes status` does NOT show per-session token usage. `hermes insights` shows aggregated 30-day stats only. But `hermes sessions export --session-id <id>` exports JSONL with built-in token fields.

## Quick Query (installed script)

A script is installed at `/usr/local/bin/session-usage`:

```bash
session-usage                    # Latest session
session-usage <session-id>       # Specific session
session-usage --all              # All sessions summary
```

### Output includes:
- Input/Output/Cache Read/Cache Write tokens
- Message count, tool call count
- Estimated cost
- Session metadata (source, model, start time)

## Manual Query (if script is missing)

```bash
# Export a specific session
hermes sessions export --session-id <session-id> /tmp/session.jsonl

# Parse token fields from the JSONL first line
python3 -c "
import json
s = json.loads(open('/tmp/session.jsonl').readline())
total = s['input_tokens'] + s['output_tokens'] + s['cache_read_tokens'] + s['cache_write_tokens']
print(f'Input: {s[\"input_tokens\"]:,}  Output: {s[\"output_tokens\"]:,}  Cache R/W: {s[\"cache_read_tokens\"]:,}/{s[\"cache_write_tokens\"]:,}  Total: {total:,}  Cost: \${s[\"estimated_cost_usd\"]:.4f}')
"
```

## Available Session Fields

The JSONL export contains per-session fields:
- `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_write_tokens`
- `message_count`, `tool_call_count`
- `estimated_cost_usd`, `actual_cost_usd`, `cost_status`, `cost_source`
- `billing_provider`, `billing_base_url`
- `model`, `source`, `started_at`, `ended_at`
- `title`, `parent_session_id`

## Recreating the Script

If `/usr/local/bin/session-usage` is missing, the full script is a standalone Python file that:
1. Calls `hermes sessions export --session-id <id> /tmp/_su.jsonl`
2. Parses JSONL, extracts token fields
3. Formats with `fmt_tokens()` (K/M abbreviations) and box-drawing output

## Pitfalls
- `hermes sessions export` requires a writable path; `/tmp/` works
- Session IDs can be found via `hermes sessions list --limit N`
- The "latest session" detection parses `hermes sessions list` output to find the session ID pattern