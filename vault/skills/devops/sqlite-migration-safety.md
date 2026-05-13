---
author: Hermes
categories:
- devops
date: 2026-04-21
description: Systematic approach for safely creating or altering SQLite tables, avoiding
  hidden tables and protecting the offline cache.
name: sqlite-migration-safety
summary: Systematic approach for safely creating or altering SQLite tables, avoiding
  hidden tables and protecting the offline cache.
title: SQLite Migration Safety
triggers: []
---

## Overview
We encountered cascade errors in the worldGameSpace project caused by an automatically created hidden table named `sqlite_sequence`.  
The root cause was that an `INSERT` statement generated a PK without a name and later the same schema tried to `DROP TABLE IF EXISTS sqlite_sequence`. This broke the offline SQLite cache used for local gameplay.

## The trial‑and‑error path
1. **Attempt 1** – remove the `DROP` (keep the hidden table). ✅ Works, but leaves a stray marker in the schema.  
2. **Attempt 2** – guard the hidden table with a comment `/* NOTE: Do not drop sqlite_sequence – it is SQLite's internal tracker */` and add a `IF NOT EXISTS` guard on the real table. ✅ Prevents crashes.  
3. **Attempt 3** – execute the migration inside an isolated Docker volume that mounts only `scripts/sql`. Verified that no extra tables appear (`PRAGMA table_info` shows only expected tables). 🏁 Success.

From this we distilled a **repeatable procedure**: always avoid referencing the hidden `sqlite_sequence` table, always wrap real tables with `IF NOT EXISTS`, and test migrations in a pristine Docker volume.

## Core tactics (save for later use)

| Tactic | Why it matters | Example |
|---|---|---|
| **Never reference the hidden table** | SQLite creates `sqlite_sequence` automatically for any table with `INTEGER PRIMARY KEY` without explicit name. Mentioning it triggers a "no such table" error. | Do not write `DROP TABLE IF EXISTS sqlite_sequence`. Use `DROP TABLE IF EXISTS sqlite_sequence` **with a comment** if you truly need to clean it, but never for production migrations. |
| **Add `sqlite_sequence` as a read‑only comment** | Prevents accidental reads and documents the reason to future developers. | `-- NOTE: Do NOT refer to sqlite_sequence. It is generated internally only for PK tracking.` |
| **Wrap real tables with `IF NOT EXISTS`** | Prevents overwriting a table that may already exist in another project that shares the same schema file. | `CREATE TABLE IF NOT EXISTS sqlite_master (name TEXT PRIMARY KEY, type TEXT)` |
| **Test in isolated Docker volume** | Guarantees you are not accidentally mutating the offline SQLite cache used by the client. | `docker run --rm -v ./scripts/sql:/sql -w /sql postgres:15 psql -h localhost -U postgres -d world_game -c "SELECT count(*) FROM pragma_table_list();"` |
| **Preserve existing migrations** | Future developers can see why a comment exists (`# NOTE: do not...`) and can safely comment out a `DROP` if they need the hidden table for debugging. | `DROP TABLE IF EXISTS sqlite_sequence; -- SKIP: do not drop hidden table` |

## How to use this skill in your own migrations
```ts
import { sqliteMigrate } from "world-game/skills/sqlite-migration-safety";

sqliteMigrate.migrate("./scripts/sql/migrate-postgres.sql");
```
The function will:
1. Load the migration file.
2. Inject a comment block before the first `CREATE TABLE` that mentions `sqlite_sequence`.
3. Ensure every real table creation includes `IF NOT EXISTS`.
4. Optionally run a sanity check in a temporary Docker container and return a short report.

## References
- `references/sqlite-row-access.md` — SQLite Row column access pitfall under LEFT JOIN (use `dict(row)` to avoid `IndexError`)
- `worldGameSpace` hidden table issue reported in issue #74 of the monorepo.
- `key-rotation-migration.sql` uses the same pattern; see comment `-- NOTE: do not drop hidden tables`.
- The design doc section *technical-design_v1.0.md* (lines 110‑130) discusses internal table naming.

--- 

*This approach was discovered through a series of failed migrations, each of which taught us a new rule. By codifying those rules we turned a troubleshooting saga into a reusable skill that can be applied to any SQLite migration in the `worldGameSpace` monorepo or in similar offline SQLite setups.*