---
categories:
- devops
description: 'Ensures that all generated files for the Fúshēng Jiàn Lù project stay
  under /mnt/data/worldGameSpace, avoiding cross‑project contamination.

  '
name: project-path-management
summary: Ensures that all generated files for the Fúshēng Jiàn Lù project stay under
  /mnt/data/worldGameSpace, avoiding cross‑project contamination.
triggers: []
---

# Project Path Management Skill

## Synopsis
Whenever you generate or write files for the project, make sure they are placed in the correct workspace.

## Steps to enforce

1. **Detect workspace** – Verify that `process.cwd()` equals `/mnt/data/worldGameSpace`. If not, `cd` there.
2. **Create relative paths** – Use `path.resolve(relativePath)` to compute file locations.
3. **Write files** – Provide the relative path; the tool will write under the project root.
4. **Validate after write** – Run `read_file(path)` and confirm the content is non‑empty.
5. **If mismatched, abort and alert** – Log a warning and optionally fall back to a temporary location with a flag.

## Common pitfalls
- Using absolute paths pointing at `/mnt/data/workspace` – older projects may have files there.
- Hard‑coding `/mnt/data/workspace/...` in tooling.
- Not checking the return value of `read_file` – it may be `''` on failure.

## Example (Node/TS)

```ts
import { ensureProjectRoot } from '../src/path-utils';

await ensureProjectRoot();
await write_file('scripts/sql/init-database.sql', '-- DB init script');
// Output file will be at: /mnt/data/worldGameSpace/scripts/sql/init-database.sql
```

---