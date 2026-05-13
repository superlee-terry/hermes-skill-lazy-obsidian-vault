---
author: Hermes AI
categories:
- devops
description: 'Safely initialize a local SQLite database for the *worldGameSpace* project.

  Assumes the workspace root is stored in user memory at `/mnt/data/worldGameSpace`.

  The procedure creates the `scripts/sql` folder, writes an idempotent

  `init-database.sql` (using `CREATE TABLE IF NOT EXISTS` and safe indexes),

  removes any stray `init-database.sql` files that may exist elsewhere (e.g.

  `/mnt/data/workspace/...`), runs the SQLite command and verifies that all

  required tables exist.

  This is reusable for any new deployment of the project.

  '
name: sqlite-local-init
summary: 'Safely initialize a local SQLite database for the *worldGameSpace* project.

  Assumes the workspace root is stored in user memory at `/mnt/data/worldGameSpace`.

  The procedure creates the `scripts/sql` f'
triggers: []
---

# Steps

1. **Read workspace root from user memory**
   ```
   workdir = "/mnt/data/worldGameSpace"
   ```

2. **Create the directory for the scripts (if it does not exist)**
   ```
   mkdir -p "$workdir/scripts/sql"
   ```

3. **Write the idempotent SQL script**
   - File: `$workdir/scripts/sql/init-database.sql`
   - Ensure the script uses `IF NOT EXISTS` for each `CREATE TABLE` and for indexes.
   - Use the following schema (trimmed for brevity; the full version is in the skill files if needed).

   ```sql
   CREATE TABLE IF NOT EXISTS players (
     id TEXT PRIMARY KEY,
     openid TEXT NOT NULL,
     level INTEGER DEFAULT 1,
     exp INTEGER DEFAULT 0,
     heart_level INTEGER DEFAULT 0,
     power INTEGER DEFAULT 0,
     created_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),
     updated_at INTEGER NOT NULL DEFAULT (strftime('%s','now'))
   );

   CREATE TABLE IF NOT EXISTS seed_wallets (
     wallet_id TEXT PRIMARY KEY,
     player_id TEXT NOT NULL,
     active_batch_id TEXT NOT NULL,
     available_count INTEGER DEFAULT 50,
     total_batches INTEGER DEFAULT 0,
     last_refill_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),
     FOREIGN KEY (player_id) REFERENCES players(id)
   );

   CREATE TABLE IF NOT EXISTS seed_batches (
     batch_id TEXT PRIMARY KEY,
     player_id TEXT NOT NULL,
     seeds TEXT NOT NULL, -- JSON array of ints
     seed_count INTEGER NOT NULL,
     consumed_index INTEGER DEFAULT 0,
     status TEXT DEFAULT 'active' CHECK (status IN ('active','exhausted','revoked')),
     created_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),
     FOREIGN KEY (player_id) REFERENCES players(id)
   );

   CREATE TABLE IF NOT EXISTS pending_battles (
     battle_id INTEGER PRIMARY KEY AUTOINCREMENT,
     batch_id TEXT NOT NULL,
     seed_index INTEGER NOT NULL,
     scene_type TEXT NOT NULL CHECK (scene_type IN ('pve','explore','enhance','tower')),
     scene_id TEXT NOT NULL,
     actions TEXT NOT NULL, -- JSON array of actions
     result TEXT NOT NULL, -- JSON of final result
     snapshot TEXT NOT NULL, -- JSON of start state
     created_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),
     submitted INTEGER DEFAULT 0,
     FOREIGN KEY (batch_id) REFERENCES seed_batches(batch_id)
   );

   CREATE TABLE IF NOT EXISTS seed_usage_log (
     log_id INTEGER PRIMARY KEY AUTOINCREMENT,
     batch_id TEXT NOT NULL,
     seed_index INTEGER NOT NULL,
     used_at INTEGER NOT NULL,
     scene_type TEXT NOT NULL CHECK (scene_type IN ('pve','explore','enhance','tower')),
     UNIQUE (batch_id, seed_index)
   );

   CREATE INDEX IF NOT EXISTS idx_players_openid ON players(openid);
   CREATE INDEX IF NOT EXISTS idx_batches_player ON seed_batches(player_id);
   CREATE INDEX IF NOT EXISTS idx_pending_battles_submitted ON pending_battles(submitted);
   ```

   **Note:** Do *not* create the `sqlite_sequence` table manually – SQLite auto‑creates it for INTEGER PRIMARY KEY AUTOINCREMENT.

4. **Delete any stray init‑script outside the correct workdir**
   ```
   find "$HOME/mnt/data/workspace" -type f -name 'init-database.sql' -exec rm -f {} + 2>/dev/null || true
   ```

5. **Execute the script in the correct location**
   ```
   sqlite3 "$workdir/worldGameSpace.db" < "$workdir/scripts/sql/init-database.sql"
   ```

6. **Verify**
   ```
   sqlite3 "$workdir/worldGameSpace.db" ".tables"
   ```
   The command should list at least these tables:
   `players seed_wallets seed_batches pending_battles seed_usage_log`

   If the list is incomplete, abort and alert the user.

7. **Record success in user memory** (optional)
   ```
   memory.add('sqlite_init_success', '2026-04-21T15:30:00Z')
   ```

### Pitfalls (Learned)

- **Location matters.** Previously the script was written under `/mnt/data/workspace` and caused a conflict with the reserved keyword `sqlite_sequence`. The fix was to place the file *inside* the actual project root directory (`worldGameSpace` scripts folder) so that paths are relative to the correct workspace.
- **Idempotency:** Using `IF NOT EXISTS` stops duplicate‑table errors when the script is run in a CI loop or multiple times locally.
- **Cleanup of stray files** prevented the script from being executed twice (once from the wrong folder, once from the right folder) and caused the `sqlite_sequence` error.
- **Use `autoincrement` only for the primary key column** (`battle_id` in `pending_battles` and any other integer PKs); do *not* reference the reserved table `sqlite_sequence` explicitly.

### Reuse

This skill can be invoked for any future project that uses a local SQLite database and needs a safe “one‑click” initialisation. It also serves as a template for other init scripts (PostgreSQL migrations, etc.) – just switch the CLI command.

---