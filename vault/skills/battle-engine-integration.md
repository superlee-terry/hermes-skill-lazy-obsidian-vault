---
categories:
- devops
- battle-engine-integration
description: "Step‑by‑step guide for integrating a deterministic battle engine with
  offline/online sync \nin the Fúshēng Jiàn Lù (Floating Sword) project. Includes
  RNG partition, pure‑function \ncombat turn processing, atomic logging, controller
  integration and cross‑platform verification.\n"
name: battle-engine-integration
summary: "Step‑by‑step guide for integrating a deterministic battle engine with offline/online
  sync \nin the Fúshēng Jiàn Lù (Floating Sword) project. Includes RNG partition,
  pure‑function \ncombat turn processin"
triggers: []
---

# Battle Engine Integration Skill

## Synopsis
Provides a reproducible deterministic combat loop that can be run offline (single‑player) 
and later verified online against a server. The engine logs every turn with a SHA256 
hash and uses a sync module to queue offline logs before sending them in order.

## Steps

1. **RNG partition (`seed-partitioner.ts`)**
   - Use the mulberry32 hash to generate a master RNG.
   - Derive sub‑seeds for each combat scenario (damage, crit, dodge, …).
   - Export a `SeededRandom` class exposing methods: `damageRoll(), critCheck(), dodgeCheck(), ...`.
   - Avoid creating a new instance per turn – instantiate once per session and reuse.

2. **Pure‑function combat turn (`engine.ts`)**
   ```ts
   import { BattleState } from '../../shared/battle/types';
   import { SeededRandom } from '../rng/seed-partitioner';
   import { createHash } from 'crypto';

   export function processTurn(
       state: BattleState,
       actions: any[],
       rng: SeededRandom,
   ): { state: BattleState; hash: string } {
       // 1️⃣ deterministic combat calculations
       const dmg = rng.damageRoll();      // 0.9‑1.1 multiplier
       const crit = rng.critCheck(0.3);
       const dodge = rng.dodgeCheck(0.2);
       // … compute newState based on actions and dmg/crit/dodge ...

       const logData = JSON.stringify({
           state,
           dmg,
           crit,
           dodge,
           newState,
       });
       const hash = createHash('sha256').update(logData).digest('hex');

       // 2️⃣ write with sync (offline write + online queue)
       battleSync.addLogEntry(logData, hash);

       return { state: newState, hash };
   }
   ```
   - Guarantees **no side effects**: all randomness goes through `rng`, all state is immutable.

3. **Sync module (`sync.ts`)**
   - Two in‑memory queues: `offlineLogQueue` for pending logs and `onlineSubmitQueue` for the actual HTTP request.
   - `addLogEntry(logData, hash)` writes the log atomically:
     ```ts
     function writeOffline(log: string, hash: string) {
         const file = \`offline/${Date.now()}.json\`;
         write_file(file, JSON.stringify({log, hash}), { ensureDir: true });
     }
     ```
   - `flushOffline()` reads pending files, sorts them by write time, and POSTs them to the backend.
   - The write operation uses `write_file` from `hermes_tools` which guarantees the whole file is written at once (no partial writes).

4. **NestJS controller (`battle.controller.ts`)**
   ```ts
   @Post('turn')
   async onTurn(@Body() dto: ProcessTurnDto, @Res() res) {
       const rng = battleSync.getOrCreateRNG(42); // deterministic demo seed
       const { state, hash } = processTurn(dto.currentState, dto.actions, rng);
       res.json({ state, hash });
   }
   ```
   - The controller returns the same hash the client can later verify against the server‑side logs.

## Pitfalls & Mitigations

| Pitfall | Why it hurts | Fix |
|---------|---------------|-----|
| **Different RNG instances on client vs server** | Randomness will diverge → verification fails. | Export a singleton `SeededRandom` per player ID; inject the same instance via DI. |
| **Unordered log writes** (multiple turn requests hit at once) | Sync module may send logs out‑of‑order, breaking replay validation. | Use a per‑player `logIndex` (atomically incremented) and store the index in each log file; `flushOffline` sorts by index before sending. |
| **Partial JSON writes** (file I/O error) | Server reads garbage → hash mismatch. | `write_file` from hermes tools writes whole content in one go; wrap in try/catch and retry 3×. |
| **Cross‑platform Node version differences** (Linux vs WeChat sandbox) | `Math.imul` may behave slightly different in some JS engines. | Prefer `bitwise` arithmetic on 32‑bit integers; test on both environments with the provided `engine_test.ts`. |

## Validation Checklist

- ✅ Run `engine_test.ts` with seed `42` and 1000 deterministic actions on Linux Node 18. Verify the final SHA256 matches the one logged in `offline/`.
- ✅ Simulate a network partition: turn off the web server, let a few turns complete offline; reconnect and run `flushOffline()`. Ensure all logs are delivered and the server’s replay hash list is identical.
- ✅ Open the built UI page (`/mnt/data/worldGameSpace/ui/ui_home/index.html`) in Chrome and click the “开启战斗” button – the alert popup should show the engine’s state without throwing errors.

**Why this skill is reusable**  
The same pattern can be applied to any turn‑based mini‑game, offline sync services, or any blockchain‑like append‑only log where deterministic state + hash is required.

---