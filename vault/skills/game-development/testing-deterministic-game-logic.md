---
categories:
- game-development
description: Test suite design and implementation for pure-function game logic with
  deterministic RNG in TypeScript.
files: []
name: testing-deterministic-game-logic
summary: Test suite design and implementation for pure-function game logic with deterministic
  RNG in TypeScript.
triggers: []
---

# Testing Deterministic Game Logic

### Steps to test pure-function game logic (like a battle engine) in TypeScript:

1. **Analyze Dependencies**: Read the implementation files (`engine.ts`, `types.ts`). Identify interfaces used for randomness, state inputs, and return values.
2. **Mock Randomness**: Create a deterministic Mock class that exactly matches the expected RNG interface (e.g., `random()` and `randomInt(max)`).
   - Use pre-piped `number` arrays so every function call yields a known constant.
   - **CRITICAL**: `random()` must return values strictly in `[0, 1)` — values `>= 1` will break `rollChance` logic (e.g., `1.0 < 1.0` is false, even for 100% crit).
   - This ensures tests are not flaky and replay the same logic.
3. **Design Test Suite**: Group tests by logic domain:
   - **Flow Control**: Win/loss conditions, turn iteration, empty inputs.
   - **Formula Validation**: Test math functions directly (e.g., `floor((atk * roll * 100) / def)`).
   - **Determinism**: Run twice with the same mock inputs. Compare outputs using `toEqual` (deep structural equality).
   - **Drops/Rewards**: Verify post-combat calculations.
4. **Implement with Vitest**: Use `describe` / `it` / `expect`.
   - Verify numerical outcomes (e.g., HP remaining, EXP gained).
   - Use `JSON.stringify` if `toEqual` fails on complex structures with undefined keys.
5. **Code Review & Flagging**: While writing tests, read the source carefully. Look for:
   - Variable name mutations (e.g., `const a = b = c`).
   - Array indexing errors vs. object property lookups.
   - Defensive coding issues (e.g., missing null checks).

### ⚠️  Known Pitfalls from Prior Work

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| **tsx/esbuild cannot parse destructuring defaults with `as` casts** | TransformError: `Expected "}" but found "["` | Refactor to parameterless opts object: `opts: { stage?: { enemies?: T[] }; ... }`. |
| **tsx/esbuild cannot parse ternary inside object literals** | TransformError: `Expected "}" but found ":"` | Use if-else to assign to a variable first, then reference the variable. |
| **MockRNG random() returning 1.0 breaks rollChance** | 100% crit never triggers because `1.0 < 1.0` is false | Ensure all mock random values are strictly `< 1.0` (e.g., use `0.99` not `1`). |
| **Engine returns `finalPlayerHp` from original player object** | Player HP in result always equals starting HP, never shows damage | Verify engine mutates player HP directly if cross-actor combat is implemented. |
| **vitest not available in monorepo** | `Cannot find module 'vitest'` | Use `npx tsx` for self-contained tests, or install vitest in appropriate package. |