---
categories:
- project-management
description: 'Auto‑validate and sync TODO tasks with their implementation files.

  '
last_updated: 2026-04-23
name: sync-todo-with-code
pitfalls: '* Enforce a minimum size (≥100 bytes) for implementation files.

  * Do not write outside the project root.

  '
prerequisites: 'Project root at `/mnt/data/worldGameSpace`.

  Requires `read_file`, `search_files`, `patch` tools.

  '
summary: Auto‑validate and sync TODO tasks with their implementation files.
triggers: []
usage: 'Run `node scripts/sync_todo.js` from the project root.

  It updates `TODO.md` in place and prints a concise summary.

  '
---

**How it works**

1. Parse `TODO.md` looking for lines with `⏳ ****<task>****`.
2. For each such task, compute the expected file path using the mapping in `scripts/sync_todo.js`.
3. `read_file` the expected file. If present and larger than 100 bytes, replace `⏳` with `✅`; otherwise keep `⏳` and log a warning.
4. Write the updated `TODO.md` back to disk.

**Example output**
```
✅ seed-module — implementation found.
⏳ battle-engine — missing file; keep status.