---
categories:
- core
- battle-core
description: Deterministic battle engine for 《浮生剑录》. Shared TypeScript types, pure-function
  simulateBattle, RNG interface, turn snapshot capture.
name: battle-core
summary: Deterministic battle engine for 《浮生剑录》. Shared TypeScript types, pure-function
  simulateBattle, RNG interface, turn snapshot capture.
title: Battle Engine Core
triggers: []
---

# Overview 

This skill stores the core battle engine implementation already written under `/mnt/data/worldGameSpace/scripts/battle/types.ts` and `engine.ts`. The engine is a pure‑function simulation used by both the Taro front‑end and NestJS back‑end.

## Files Included 
``` 
scripts/ 
  └─ battle/ 
      ├─ types.ts      // shared data structures 
      └─ engine.ts     // simulateBattle, rawDamage, processTurn, RNG interface 
``` 

## Public API 
```ts
import { simulateBattle } from 'battle-core'; 

const rng = createRNG(masterSeed); // SeededRandom with 10 child zones 
const result = simulateBattle({ 
  stage: { enemies: enemyArray }, 
  player: playerActor, 
  actions: actionsList, 
  rng, 
}); 
``` 

## Tests 
Located in `scripts/battle/tests/` and executed via `pnpm test:battle` (runs `pytest -n 4`). The test suite validates: 
- **Determinism** – identical seed → identical `BattleResult` and turn snapshots. 
- **RNG independence** – 10 child RNG zones keep their own state; mutating one zone never affects another (verified 30 times). 
- **Edge cases** – no enemies, early kill, max damage, empty action list, zero RNG output. 
- **Pitfall handling** – tests also check that the RNG object is immutable (no method chaining that mutates internal state). 

## Pitfalls & Learnings (non‑trivial discovery) 
- **Do not mutate the RNG instance** – the engine assumes `rng.random()` and `rng.randomInt()` are pure functions. Previously, the split‑seed code reused the same object for multiple calls, causing cross‑zone RNG cross‑talk and flaky failures. Fix: create a fresh `SeededRandom` per simulation and pass the same object for the whole run; it internally creates 10 child RNGs but never mutates after creation. 
- **Build before test** – earlier runs showed the test suite failing because `@fusheng/shared` built files were missing when tests looked for `simulateBattle` from the compiled package. The reliable workflow now: `pnpm --filter @fusheng/shared build && pnpm --filter @fusheng/shared test`. This step is now documented in the README. 
- **RNG partition order discovery** – during early trials, the engine sometimes reported mismatched loot when the damage‑zone RNG was called after a status‑effect RNG. The fix was to move the `SeededRandom` creator that generated 10 deterministic child seeds *before* any game logic runs, guaranteeing a fixed order of RNG calls for the entire simulation. 
- **Unit‑test order for parallel test runs** – when `pnpx jest --maxWorkers=4` ran, the same seed produced different results across workers. The root cause was shared global state in `SeededRandom`. The solution: each test spawns its own RNG instance, avoiding any shared mutable state across test processes. 
## Critical Bug — Determinism Violation in StatusEffect ID
**Symptom**: Battle replay verification fails; RNG sequence drifts mid‑combat after a skill with status‑effect (debuff/hot) is cast.
**Cause**: `engine.ts` StatusEffect `id` generation uses `Date.now()` and `Math.random()`:
```ts
id: `se_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`
```
These are **non‑deterministic** and consume random numbers outside the RNG framework, desynchronizing all subsequent RNG calls.
**Fix**: Use zone‑separated RNG for id generation:
```ts
const idStr = rng.getZone('status_hit')().toString(36).slice(2, 10)
  + rng.getZone('drop_check')().toString(36).slice(2, 6);
id: `se_${idStr}`
```
**Prevention**: In ANY battle engine file, grep for `Date.now()`, `Math.random()`, `crypto.randomUUID()`, `Math.random()` — these must NOT exist. All randomness must flow through `SeededRandom` zones only.
## Audit Before Rewrite Principle
**Principle**: Before writing new code for a battle engine feature, always audit `/mnt/data/worldGameSpace/packages/shared/src/battle/` first. The shared package already contains a complete implementation (~1000+ lines: engine.ts, formulas.ts, types.ts, __tests__/) with 24 passing tests. Rewriting duplicated code wastes effort and introduces regressions. Use `npx vitest run src/battle/__tests__/engine.test.ts` to verify the existing implementation before starting any changes. 

## Recommended Usage 
1. Import the shared battle core from the monorepo: `import { simulateBattle } from '@fusheng/shared/battle'`. 
2. Create a deterministic RNG with a per‑player master seed: 
   ```ts
   import { createRNG } from '@fusheng/shared/rng'; 
   const rng = createRNG(playerSeed); // internally builds child RNGs 
   ``` 
3. Call `simulateBattle` with the stage config, player, and actions. 
4. Do **not** modify the `rng` object after passing it. 

## Next Steps 
- Extend the engine to allow custom loot providers per zone (inject a `lootFn`). 
- Add a `watchDog` that records RNG mutation attempts in CI. 
- Benchmark with real player data (30‑player concurrent battle‑testing) and explore a WASM port for >500 concurrent sims.

---
> **Lesson**: When a pure‑function workflow fails under realistic assumptions, trace the call‑graph, isolate side‑effects, and ensure reproducibility by designing the RNG as a *purely functional* data structure. This same pattern was later applied to the key‑rotation cron that now stores a hash‑protected key list in a read‑only JSON file.

---
*This section would go into the **Skill** under *`battle-core`* and should be saved for future reference.*