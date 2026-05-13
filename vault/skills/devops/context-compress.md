---
categories:
- devops
created: 2026-04-21
description: 'Automatic LLM session context compression.

  When the accumulated Hermes session size approaches the model''s context limit,
  this skill runs ``session_search`` to fetch recent exchanges, generates a concise
  summary, stores the summary in memory (tag `compressed_context`), and prunes older
  sessions to keep total context within the safe limit.

  '
name: context-compress
summary: 'Automatic LLM session context compression.

  When the accumulated Hermes session size approaches the model''s context limit,
  this skill runs ``session_search`` to fetch recent exchanges, generates a conc'
tags:
- memory
- compression
- lm
- context
triggers:
- memory
- compression
- lm
- context
---

**Trigger**

The skill should be invoked before any heavy tool call (e.g., ``terminal``, ``read_file``) when the current session size is high.

**Compression logic**
- Reads `/mnt/data/memory/context_used_chars.txt` – if file not found assume 0.
- If `chars_used > 0.9 * MAX_TOKENS` (≈260k chars), proceed.
- Perform ``session_search(query='recent Hermes exchange', limit=3)``.
- Use a local LLM (e.g., via `/new`) to produce a single‑paragraph summary.
- ``memory.add`` the summary with target `memory` and content like "Compressed context summary – <summary>".
- Identify the specific older ``session_*`` entries that caused the overflow (the ones older than the three fetched) and ``replace`` them with the summary or delete them via ``session_search`` + ``memory.remove``.
- Reset ``context_used_chars`` to ``0``.

**Notes**
- The skill must be able to call ``session_search`` and ``memory``; ensure those tool calls are listed in the agent's tool registry.
- Store run counters in ``~/.hermes/skills/metrics.json`` under key ``context_compress_runs``.
- The skill should be listed in ``hermes-session-usage`` for monitoring.

**Example invocation (Hermes):**
```ts
import { run_context_compress } from "context-compress";
await run_context_compress();
```