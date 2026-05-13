---
categories:
- devops
description: Automatically rotates the `master_key` and `api_sign_key` for the worldGameSpace
  project every 30 days.  The rotation is driven by a Bash wrapper that checks the
  interval, executes a TypeScript (or JS) rotation script, writes new keys to `config/keys.json`,
  and logs the operation to `logs/key-rotate.log`. Includes fallback handling for
  missing directories, timestamp comparison, and Node ES‑module vs CommonJS environments.
name: cron-30d-key-rotation
summary: Automatically rotates the `master_key` and `api_sign_key` for the worldGameSpace
  project every 30 days.  The rotation is driven by a Bash wrapper that checks the
  interval, executes a TypeScript (or JS
tags:
- cron
- key rotation
- security
- automation
- devops
title: 30‑day Cron Key Rotation
triggers:
- cron
- key rotation
- security
- automation
- devops
---

## Overview
Automate periodic key rotation while maintaining security best‑practices. The solution comprises a TypeScript generation script, a robust Bash wrapper, and a cron entry that self‑throttles to enforce a true 30‑day cadence.

## File Layout
```
worldGameSpace/
├─ config/
│   └─ keys.json        # { master_key, api_sign_key, last_rotation }
├─ logs/
│   └─ key-rotate.log   # Human‑readable audit trail
└─ scripts/
    ├─ rotate-keys.ts          # TS rotation logic (crypto.randomBytes → keys.json)
    ├─ rotate-keys-wrapper.sh  # Bash wrapper with 30‑day throttle & dir checks
    └─ rotate-keys.js          # Optional JS fallback
```

## Script Details
### `scripts/rotate-keys.ts`
```ts
import * as fs from 'fs';
import * as path from 'path';
import * as crypto from 'crypto';

const keyFile = path.resolve(__dirname, '..', 'config', 'keys.json');

function rotate() {
  const newMaster = crypto.randomBytes(32).toString('base64');
  const newSign   = crypto.randomBytes(32).toString('base64');
  const now = new Date().toISOString();

  const keys = JSON.parse(fs.readFileSync(keyFile, 'utf8'));
  keys.master_key = newMaster;
  keys.api_sign_key = newSign;
  keys.last_rotation = now;
  fs.writeFileSync(keyFile, JSON.stringify(keys, null, 2));
  console.log(`Rotated keys at ${now}`);
}
if (require.main === module) rotate();
```
### `scripts/rotate-keys-wrapper.sh`
```bash
#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/mnt/data/worldGameSpace"
SCRIPT_DIR="${PROJECT_ROOT}/scripts"
KEY_FILE="${PROJECT_ROOT}/config/keys.json"
LOG_DIR="${PROJECT_ROOT}/logs"
LOG_FILE="${LOG_DIR}/key-rotate.log"

mkdir -p "$(dirname "$KEY_FILE")" "$LOG_DIR"

# create placeholder if missing
if [[ ! -f "$KEY_FILE" ]]; then
  cat > "$KEY_FILE" <<'EOF'
{
  "master_key": "INIT_MASTER_KEY",
  "api_sign_key": "INIT_API_SIGN_KEY",
  "last_rotation": "1970-01-01T00:00:00Z"
}
EOF
  echo "Initialized empty keys.json"
fi

LAST_ROTATE=$(jq -r .last_rotation "$KEY_FILE" 2>/dev/null || echo "1970-01-01T00:00:00Z")
NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
DIFF=$(( ($(date -u -d "$NOW" +%s) - $(date -u -d "$LAST_ROTATE" +%s)) / 86400 ))

if (( DIFF < 30 )); then
  echo "$(date) - Skipping rotation; last at $LAST_ROTATE ($DIFF days ago)" >> "$LOG_FILE"
  exit 0
fi

echo "$(date) - Rotating keys (last $LAST_ROTATE, $DIFF days ago)" >> "$LOG_FILE"
# Use ts-node if available, otherwise plain node with the JS fallback
if command -v npx >/dev/null; then
  npx ts-node --register ts "$SCRIPT_DIR/rotate-keys.ts" >> "$LOG_FILE" 2>&1
else
  node "$SCRIPT_DIR/rotate-keys.js" >> "$LOG_FILE" 2>&1
fi

echo "$(date) - Rotated successfully" >> "$LOG_FILE"
```
### `scripts/rotate-keys.js` (fallback)
```js
"use strict";
const fs=require('fs'),crypto=require('crypto'),path=require('path');
const keyPath=path.resolve(__dirname,'..','config','keys.json');
function rotate(){
  const master=crypto.randomBytes(32).toString('hex');
  const sign=crypto.randomBytes(32).toString('hex');
  const data=JSON.parse(fs.readFileSync(keyPath,'utf8'));
  data.master_key=master;
  data.api_sign_key=sign;
  data.last_rotation=new Date().toISOString();
  fs.writeFileSync(keyPath,JSON.stringify(data,null,2));
  console.log(`Rotated keys at ${data.last_rotation}`);
}
if(require.main===module)rotate();
```
## Installation & Verification
```bash
chmod +x /mnt/data/worldGameSpace/scripts/rotate-keys-wrapper.sh
/mnt/data/worldGameSpace/scripts/rotate-keys-wrapper.sh   # manual test
# Should create keys.json and log a rotation after 30 days (or instantly on first run).
cat /mnt/data/worldGameSpace/logs/key-rotate.log
```
## Usage
Add the following line to the user’s `crontab`:
```
15 0 * * * /mnt/data/worldGameSpace/scripts/rotate-keys-wrapper.sh >> /mnt/data/worldGameSpace/logs/cron.log 2>&1
```
The wrapper enforces a true 30‑day rotation regardless of daily execution.

---