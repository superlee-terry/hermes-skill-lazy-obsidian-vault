---
author: user
categories:
- testing
description: Minimal CI unit test to verify RNG isolation by asserting that each call
  to partitionRNG.getState() yields a unique RNG state.
name: ci-test-rng
summary: Minimal CI unit test to verify RNG isolation by asserting that each call
  to partitionRNG.getState() yields a unique RNG state.
triggers: []
version: 0.1
---

# CI Test for RNG Isolation

## Purpose
Ensure that the `partitionRNG` function returns a different RNG state each invocation, confirming runtime isolation.

## Steps
1. Create file `~/.hermes/scripts/ci-test-rng.ts`.
2. Paste the following test code:
```ts
import { partitionRNG } from '../rng-base';

const seen = new Set<string>();
for (let i = 0; i < 10; i++) {
  const state = await partitionRNG.getState();
  const hash = JSON.stringify(state);
  if (seen.has(hash)) throw new Error('state duplicate at call '+i);
  seen.add(hash);
}
console.log('PASS: All RNG states unique');
```
3. Run with `node --experimental-modules ci-test-rng.ts`.
4. Verify output contains "PASS". CI failure if error.

## Pitfalls
- Ensure `partitionRNG` resolves to a true RNG instance (not mocked).
- Disable other RNG seeds concurrently to avoid false positives.
- The script must run with `node --experimental-modules` due to ES modules.

## Verification in CI
Add to CI pipeline:
```yaml
- name: Run RNG isolation test
  run: node --experimental-modules ~/.hermes/scripts/ci-test-rng.ts
```
---