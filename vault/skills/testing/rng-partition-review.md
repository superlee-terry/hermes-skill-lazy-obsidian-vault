---
categories:
- testing
description: Automated verification that each RNG zone in 坐剑 (Fúshēng Jiàn Lù) receives
  a unique sub‑seed, guaranteeing deterministic isolation for battle simulations.
name: rng-partition-review
summary: Automated verification that each RNG zone in 坐剑 (Fúshēng Jiàn Lù) receives
  a unique sub‑seed, guaranteeing deterministic isolation for battle simulations.
triggers: []
---

# rng-partition-review.skill.md

## Overview
Runs `scripts/verify-rng.ts` which loads the `seedManager` and triggers `partitionRNG` for every zone. The script prints a unified ✅ line only if every zone's RNG state is unique. Any ⚠️ indicates a seed collision and must be fixed before proceeding to battle engine activation.

## Prerequisites
- The `seedManager` class (`src/seed-module/seed-manager.ts`) is compiled and available via the workspace `pnpm`.
- `npx ts-node` points to the project's `tsconfig-paths/register`.
- The environment variable `NODE_ENV=production` ensures the test uses the production config.

## Workflow
1. **Run the verifier**
```bash
cd /mnt/data/worldGameSpace
npx ts-node -r tsconfig-paths/register scripts/verify-rng.ts
```
2. **Inspect output**
- Acceptable output:
```text
✅ All RNG instances have unique seeds
```
- If you see:
```text
⚠️  Collision detected between zones 5 and 7 (seed 0x3a7b...), aborting.
```
> The RNG isolation is broken; the batch id must be increased and the collision source investigated.

3. **Commit the test script** – `git add scripts/verify-rng.ts && git commit -m "Add RNG isolation verifier"` (skip if not a git repository).

4. **Mark as Done** – update `TODO.md` entry for `rng-partition-review` to `✅`.

## Known Pitfalls
- **Off‑by‑one in `subSeed` generation** – the `seed-partitioner` originally used `masterRNG() & 0x7fffffff`. Ensure you mask the sign bit for 31‑bit positive numbers only.
- **Parallel execution** – the verifier is designed for a single run. If you parallelise, each runner must receive a deterministic counter‑derived sub‑seed, not a fresh `Math.random()` call.
- **Local vs. remote RNG state** – `SeedManager` caches its state in `config/seed-manager-state.json`. If a stale file exists, verify its `nextBatchId` matches the script's expectation; otherwise clear the file and re‑run.

## Example Output (Success)
```
$ npx ts-node -r tsconfig-paths/register scripts/verify-rng.ts
✅ All RNG instances have unique seeds
```

## Integration
- The `key‑rotation‑cron` skill calls this verifier after each master‑key rotation. If the verifier fails, the rotation script aborts and writes a `FAIL` entry to `logs/key-rotation.log`.
- The skill also triggers a Slack webhook (optional) to alert developers.

--