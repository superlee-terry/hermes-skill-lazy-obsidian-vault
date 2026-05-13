---
categories:
- productivity
description: Recall and summarize what was accomplished across today's or recent Hermes
  sessions, with filesystem verification to detect interrupted tasks.
metadata:
  hermes:
    tags:
    - session-review
    - daily-summary
    - productivity
name: session-history-review
summary: Recall and summarize what was accomplished across today's or recent Hermes
  sessions, with filesystem verification to detect interrupted tasks.
triggers:
- session-review
- daily-summary
- productivity
version: 1.0.0
---

# Session History Review

Recall and summarize what was accomplished across today's (or recent) Hermes sessions, with filesystem verification.

## When to Use
- User asks "今天做了什么", "回忆一下对话", "总结一下工作进度"
- Any request to review/summarize past session activity

## Approach

### Step 1 — List Today's Sessions
```bash
ls -la ~/.hermes/sessions/ | grep "$(date +%Y%m%d)" | sort
```
Filter out `request_dump_*` files — only `session_*.json` files contain conversation data. Also note `session_cron_*` for automated tasks.

### Step 2 — Extract Messages via Python
Use `execute_code` to parse session JSON files. `session_search` cannot search by session ID — direct file reading is required.

```python
import json, os

sessions_dir = os.path.expanduser("~/.hermes/sessions/")
session_files = ["session_YYYYMMDD_HHMMSS_xxxxx.json", ...]

for fname in session_files:
    fpath = os.path.join(sessions_dir, fname)
    with open(fpath, 'r') as f:
        data = json.load(f)
    msgs = data if isinstance(data, list) else data.get('messages', [])
    for m in msgs:
        role = m.get('role', '')
        content = m.get('content', '')
        if isinstance(content, list):
            texts = [p.get('text', '') for p in content if isinstance(p, dict) and p.get('type') == 'text']
            content = ' '.join(texts)
        if role == 'user' and content:
            print(f">>> USER: {content[:300]}")
        elif role == 'assistant' and content:
            if any(kw in content for kw in ['完成', '实现', '更新', '创建', '已完成']):
                print(f"    ASST: {content[:400]}")
```

### Step 3 — Verify Claims Against Filesystem
Session logs may claim tasks were completed but stream stalls could have prevented writes. Verify:

```bash
# Check file sizes (skeleton files are ~13 lines, real implementations are 200+)
wc -l <relevant files>

# Check file headers to confirm content was written
head -5 <relevant files>

# Check TODO.md or project tracking files
head -50 <project>/TODO.md
```

**Key signal**: Files with ≤15 lines are likely unfinished skeletons. Files with 100+ lines indicate real implementation.

### Step 4 — Produce Structured Summary
Output format:
```
## Session N — HH:MM ~ HH:MM (X messages) — Task Title
- ✅ Completed items (with file paths and line counts)
- ⚠️ Partially completed / interrupted items
- ❌ Not started items

## Unfinished Items (cross-session)
- Item 1 — blocked by X
- Item 2 — next priority

## Blocking Issues
- Stream stall, compilation error, etc.
```

## Pitfalls
- **session_search can't find by ID**: Always use direct file reading for specific sessions.
- **Stream stalls inflate "completed" count**: Assistant may report success for write_file calls that were interrupted. Always verify with `wc -l` and `head`.
- **Duplicate sessions**: `/new` restarts create new sessions with identical content. Deduplicate before summarizing — check if two sessions have the same user message sequence.
- **request_dump files are noise**: Ignore `request_dump_*.json` files; they're debug artifacts, not conversations.
- **Large session files**: Some sessions are 200-300KB. Use Python parsing (not raw read_file) to avoid context flooding.