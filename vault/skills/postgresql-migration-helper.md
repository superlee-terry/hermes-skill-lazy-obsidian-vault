---
categories:
- devops
- postgresql-migration-helper
description: Generate PostgreSQL migration from SQLite schema used by Fusheng (worldGameSpace).
name: postgresql-migration-helper
script_path: /mnt/data/worldGameSpace/scripts/generate-pgsql-migration.sh
summary: Generate PostgreSQL migration from SQLite schema used by Fusheng (worldGameSpace).
triggers: []
---

## Overview
This approach uses a Bash script (`generate-pgsql-migration.sh`) that reads the existing SQLite schema (`init-database.sql`) and rewrites it as a PostgreSQL-compatible migration. It drops existing tables, creates the necessary extensions, and defines the tables with appropriate types, indexes, and constraints.

### How the script works
1. **Load SQLite schema** (parsed as raw text) – for each `CREATE TABLE` statement, it translates data types:
   - `TEXT` → `TEXT`
   - `INTEGER` → `INTEGER`
   - `TEXT` for JSON arrays stays `TEXT` (PostgreSQL can store JSONB if desired)
   - `UNIQUE` constraints are rewritten as `CREATE UNIQUE INDEX`.
2. **Extension handling** – ensures `uuid-ossp` and `pgcrypto` are installed before table creation.
3. **Table recreation** – the script clears the target database (via `DROP TABLE IF EXISTS`) and rebuilds the schema.
4. **Idempotence** – running the script repeatedly will re‑create the tables; it is safe for local development but must be used with care on production.

### Usage
```bash
cd /mnt/data/worldGameSpace/scripts
./generate-pgsql-migration.sh
# Output will be written to /mnt/data/worldGameSpace/scripts/sql/migrate-postgres.sql
```

### Example output (first few lines)
```sql
-- PostgreSQL migration for Fusheng (Fusheng)

-- Drop existing tables
DROP TABLE IF EXISTS players CASCADE;
DROP TABLE IF EXISTS seed_wallets CASCADE;
DROP TABLE IF EXISTS seed_batches CASCADE;
DROP TABLE IF EXISTS pending_battles CASCADE;
DROP TABLE IF EXISTS seed_usage_log CASCADE;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Players table
CREATE TABLE players (
  id TEXT PRIMARY KEY,
  openid TEXT NOT NULL,
  level INTEGER NOT NULL DEFAULT 1,
  exp INTEGER NOT NULL DEFAULT 0,
  heart_level INTEGER NOT NULL DEFAULT 0,
  power INTEGER NOT NULL DEFAULT 0,
  created_at BIGINT NOT NULL DEFAULT (EXTRACT(EPOCH FROM now())::BIGINT),
  updated_at BIGINT NOT NULL DEFAULT (EXTRACT(EPOCH FROM now())::BIGINT),
  CONSTRAINT uniq_players_openid UNIQUE (openid)
);
...
VACUUM ANALYZE;
```

### Future improvements
* Parameterize DB host and credentials via environment variables.
* Add a `--dry-run` flag to preview the generated SQL without execution.
* Extend to support migration versioning (e.g., Alembic‑style scripts).

---