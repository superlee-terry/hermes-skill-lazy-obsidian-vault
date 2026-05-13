---
categories:
- game-development
description: 'Core battle engine design for 《浮生剑录》 that uses deterministic mulberry32
  RNG with sub-seed partitioning, pure function turn processing, and offline/online
  sync for anti-cheat.

  '
name: battle-engine-design
summary: Core battle engine design for 《浮生剑录》 that uses deterministic mulberry32 RNG
  with sub-seed partitioning, pure function turn processing, and offline/online sync
  for anti-cheat.
tags: []
triggers: []
---

# Battle Engine Design

## Overview
- Deterministic turn‑based calculation based on master seed.
- RNG sub‑seeds per battle domain (damage, crit, drop, etc.) using `SeededRandom`.
- Engine is a pure function `processTurn(state, actions) -> newState, logHash`.
- Offline logs stored in SQLite `pending_battles`; online replay validates hash and state.
- Multi‑platform verification via unit tests on Node, WeChat dev tools (iOS/Android simulators).

## Steps
1. Implement mulberry32 RNG and `SeededRandom` class.
2. Write pure‑function turn processor with state hashing.
3. Add migration for battle tables (`seed_batches`, `pending_battles`).
4. Integrate NestJS `BattleModule` with DTOs and service.
5. Create cross‑platform tests that run same seed on Node & WeChat Simulator; compare logs.

## Pitfalls
- Sub‑seed order mismatch causes cascade errors → always derive sub‑seeds in a fixed deterministic order.
- Hash collision – use SHA‑256 and include state version.
- Offline log size grows quickly – prune settled battles after replay.

## Testing
- Seed 48271: run on Node and WeChat iOS simulator, ensure final state and logHash identical.
- Fault injection: corrupt sub‑seed order, expect hash mismatch.

Created by user for reuse.