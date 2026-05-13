---
categories:
- automation
description: 'Rotates `master_key` and `api_sign_key` in `config/keys.json` every
  30 days.

  Pure bash script — no Node.js dependency. Cron runs daily at midnight UTC;

  the script itself enforces the 30-day cooldown.

  '
name: key-rotation-cron
summary: 'Rotates `master_key` and `api_sign_key` in `config/keys.json` every 30 days.

  Pure bash script — no Node.js dependency. Cron runs daily at midnight UTC;

  the script itself enforces the 30-day cooldown.'
tags:
- automation
- security
- cron
- bash
title: Key Rotation Cron Workflow
triggers:
- automation
- security
- cron
- bash
---

# Overview

Single-file bash script at `scripts/rotate-keys.sh` that:
1. Reads `config/keys.json` to check `last_rotation`
2. If ≥ 30 days have passed, generates new `MASTER_KEY` and `API_SIGN_KEY` via `openssl rand -base64 32`
3. Writes new keys atomically to `config/keys.json` (write to tmp file + `mv`)
4. Updates `apps/fusheng-server/.env.local` with the new keys (so NestJS `ConfigService` picks them up on restart)
5. Sets file permissions to `600`
6. Logs every run (skip or rotate) to `logs/key-rotation.log`

Cron entry `0 0 * * *` triggers the check daily at midnight UTC.

# Dependencies

- `bash`, `jq`, `openssl`, `date` (coreutils)
- No Node.js, no ts-node

## File locations

| Path | Purpose |
|------|---------|
| `scripts/rotate-keys.sh` | Main rotation script |
| `scripts/verify-rng.js` | Best-effort RNG verification after rotation (pure Node.js crypto test) |
| `scripts/rotate-keys-wrapper.sh` | Backward-compat shim (delegates to rotate-keys.sh) |
| `config/keys.json` | Stores `master_key`, `api_sign_key`, `last_rotation` |
| `apps/fusheng-server/.env.local` | Updated with new `MASTER_KEY` and `API_SIGN_KEY` on rotation |
| `logs/key-rotation.log` | Timestamped log of every run |

# Cron setup

```bash
# Add to crontab (preserving existing entries):
(crontab -l 2>/dev/null; echo "0 0 * * * /mnt/data/worldGameSpace/scripts/rotate-keys.sh") | crontab -
```

# Manual run

```bash
# Dry-run (will skip if < 30 days since last rotation):
bash /mnt/data/worldGameSpace/scripts/rotate-keys.sh

# Force rotation (for emergencies):
jq '.last_rotation = "1970-01-01T00:00:00Z"' config/keys.json > /tmp/force.json && mv /tmp/force.json config/keys.json
bash /mnt/data/worldGameSpace/scripts/rotate-keys.sh
```

# Log format

```
2026-04-22T16:02:39Z INFO: Skipped — last rotation was 1 day(s) ago (< 30-day interval). Next rotation in 29 days.
2026-04-22T16:02:51Z SUCCESS: Keys rotated (interval was 31 days). last_rotation=2026-04-22T16:02:51Z
```

# History

- v1 (2026-04-22): Rewrote as pure bash. Removed Node.js/ts-node dependency that was broken on the server. Added 30-day guard, atomic writes, chmod 600, proper logging to `key-rotation.log`.