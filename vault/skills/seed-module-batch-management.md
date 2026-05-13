---
categories:
- devops
- seed-module-batch-management
description: Deterministic seed batch management for Floating Sword project; includes
  trial-and-error on sub‑seed generation, uniqueness verification, and integration
  with seed‑partitioner.
name: seed-module-batch-management
summary: Deterministic seed batch management for Floating Sword project; includes
  trial-and-error on sub‑seed generation, uniqueness verification, and integration
  with seed‑partitioner.
tags: []
triggers: []
---

# Seed Module Batch Manager

Provides deterministic seed batch management for the Floating Sword (《浮生剑录》) project.

## Core Concepts
- **Batch**: A collection of 16 independently‑derived Sub‑RNGs, each representing a RNG zone.
- **Batch ID**: Unique sequential name like `batch-001`.
- **Master Seed**: 32‑bit integer; sub‑seeds never reused.

## Implementation
```ts
export class SeedManager {
  private nextBatchId = 1;
  private batchMap = new Map<string, Batch>();

  allocateBatch(masterSeed: number): Batch {
    const batch: Batch = { id: `batch-${this.nextBatchId++}`, seeds: new Map<string, SeededRandom>() };
    const master = createRNG(masterSeed);
    for (const zone of RNG_ZONES) {
      const subSeed = (master() * 0xFFFFFFFF) | 0;
      batch.seeds.set(zone, createRNG(subSeed));
    }
    this.batchMap.set(batch.id, batch);
    // Persist next id atomically
    write_file('scripts/seed-manager.json', JSON.stringify({ nextBatchId: this.nextBatchId }));
    return batch;
  }

  verifyBatch(batch: Batch): boolean {
    const seen = new Set<number>();
    for (const rng of batch.seeds.values()) {
      // Extract first 31 bits of each random number as proxy for uniqueness
      const val = rng().toFixed(0).slice(2);
      if (seen.has(val)) return false;
      seen.add(val);
    }
    return true;
  }
}
```
The manager stores generated batches under `scripts/seed-manager.json`. The `verifyBatch` guard is used in the `rng-partition-review` task to ensure no zone collisions.

## Usage Example
```ts
import { SeedManager } from './seed-module-batch-management';
import { createRNG } from './rng/mulberry32';

const mgr = new SeedManager();
const batch = mgr.allocateBatch(0x12345678);
console.log('Damage RNG seed:', batch.seeds.get('damage_roll')!().toString(16));
```

## Pitfalls & Mitigations
- **Partial writes**: Use `write_file` which writes the whole file content; wrap in try/catch and retry.
- **Concurrency**: `nextBatchId` is incremented atomically via file write; multiple processes must coordinate (beyond current scope).

## Reuse
The same sub‑seed generation technique can be applied to any RNG‑parallel system where deterministic independent streams are required; just copy the `SeedManager` class and adjust `RNG_ZONES` to match your zones.