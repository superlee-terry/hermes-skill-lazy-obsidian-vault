---
categories:
- devops
- typeorm-ddl-gen
description: Convert TypeORM entity TypeScript files into production PostgreSQL DDL
  with proper dependency ordering and constraints.
name: typeorm-ddl-gen
summary: Convert TypeORM entity TypeScript files into production PostgreSQL DDL with
  proper dependency ordering and constraints.
triggers: []
---

# TypeORM Entity DDL Generation

Convert TypeScript TypeORM entity files into production PostgreSQL DDL (CREATE TABLE/INDEX/FK statements) for manual database initialization.

## When to Use

- Initializing a PostgreSQL database from existing TypeORM entities
- Creating a standalone migration NOT using TypeORM's synchronize
- Auditing what tables TypeORM would create in a project

## Key Pitfalls

### Entity to DDL Conversion Rules

| TypeORM Decorator | PostgreSQL Type |
|-------------------|-----------------|
| `@Entity('table_name')` | `CREATE TABLE table_name (...)` |
| `@PrimaryColumn({ type: 'text' })` | `TEXT PRIMARY KEY` |
| `@PrimaryGeneratedColumn()` | `SERIAL PRIMARY KEY` or `BIGSERIAL` |
| `@PrimaryGeneratedColumn('uuid')` | `UUID DEFAULT gen_random_uuid() PRIMARY KEY` |
| `@Column({ type: 'jsonb' })` | `JSONB NOT NULL DEFAULT '[]'` |
| `@Column({ type: 'bigint' })` | `BIGINT` |
| `@Column({ type: 'boolean' })` | `BOOLEAN` |
| `@Column({ type: 'text' })` | `TEXT` or `VARCHAR(255)` |
| `@ManyToOne(..., { onDelete: 'CASCADE' })` | `REFERENCES parent(id) ON DELETE CASCADE` |
| `@JoinColunm({ name: 'col' })` | Include FK constraint named `col` |
| `@Index(['col'])` | `CREATE INDEX idx_table_col ON table(col)` |
| `@Unique(['col1', 'col2'])` | `CONSTRAINT uq_table UNIQUE (col1, col2)` |

### Column Defaults

- `DEFAULT gen_random_uuid()::text` for UUID PKs
- `DEFAULT '[]'::jsonb` or `DEFAULT '[]'` for JSONB arrays
- `DEFAULT 'normal'` for text defaults
- `DEFAULT FALSE` for boolean defaults
- `DEFAULT NOW()::BIGINT` for epoch timestamps

### Generation Order

Always generate DDL in this order:

1. Parent tables (no foreign key dependencies)
2. Child tables (with FK to parents)
3. `CREATE INDEX IF NOT EXISTS` statements
4. `CREATE EXTENSION IF NOT EXISTS "uuid-ossp"` early

### Dependencies

- **`@types/node`** must be installed in the package's devDependencies (not just the workspace root)
- In a pnpm monorepo, each workspace package needs its own `@types/node`

## Post-Generation Verification

```bash
# 1. Execute migration
psql -U postgres -d <db> -f migration.sql

# 2. Verify tables exist
psql -U postgres -d <db> -c "\\dt public.*"

# 3. Verify indexes
psql -U postgres -d <db> -c "\\di"

# 4. Test with a simple INSERT
psql -U postgres -d <db> -c "INSERT INTO players (id, openid) VALUES (gen_random_uuid(), 'test'); DROP TABLE players;"

# 5. Run TypeScript compilation to ensure entity files are still valid
tsc
```

## Session Context

This skill was learned from working on the Fusheng Jianlu project at `/mnt/data/worldGameSpace/apps/fusheng-server/src/entities/` where 8 entity files (player, sword_spirit, item, equipment, seed_wallet, seed_batch, pending_battle, battle_log) were converted into a single complete PostgreSQL schema.

The migration script was written to `/mnt/data/worldGameSpace/apps/fusheng-server/src/init-db.sql` and executed via `docker exec postgres-local psql -U postgres -d local -f /tmp/migrate.sql`.

### Entity File Paths

| Entity | File Path | Table Name |
|--------|-----------|------------|
| `player` | `entities/player.entity.ts` | `players` |
| `sword_spirit` | `entities/sword-spirit.entity.ts` | `sword_spirits` |
| `item` | `entities/item.entity.ts` | `items` |
| `equipment` | `entities/equipment.entity.ts` | `equipment` |
| `seed_wallet` | `entities/seed-wallet.entity.ts` | `seed_wallets` |
| `seed_batch` | `entities/seed-batch.entity.ts` | `seed_batches` |
| `pending_battle` | `entities/pending-battle.entity.ts` | `pending_battles` |
| `battle_log` | `entities/battle-log.entity.ts` | `battle_logs` |

### Example Generated DDL Snippet

See the full DDL output at `/mnt/data/worldGameSpace/apps/fusheng-server/src/init-db.sql` which was successfully executed against PostgreSQL.

### TypeORM Entity → DDL Conversion Reference

Each entity maps as follows:

```
@Entity('table_name')                          → CREATE TABLE table_name
@PrimaryColumn({ type: 'text' })               → id            TEXT PRIMARY KEY
@PrimaryGeneratedColumn()                       → battle_id     SERIAL PRIMARY KEY
@Column({ type: 'text' })                       → name          TEXT NOT NULL
@Column({ type: 'jsonb', default: '[]' })     → affixes       JSONB NOT NULL DEFAULT '[]'
@Column({ type: 'bigint' })                     → created_at    BIGINT NOT NULL DEFAULT EXTRACT(EPOCH FROM NOW())
```

### Index Patterns

```
@Index(['playerId', 'isEquipped'])       → CREATE INDEX idx_items_player_equipped ON items(player_id, is_equipped)
@Unique(['playerId', 'slot'])            → CONSTRAINT uq_player_slot UNIQUE (player_id, slot)
```

### Foreign Key Patterns

```
@ManyToOne(() => PlayerEntity, { onDelete: 'CASCADE' })
@JoinColumn({ name: 'player_id' })        → player_id  TEXT NOT NULL REFERENCES players(id) ON DELETE CASCADE
```