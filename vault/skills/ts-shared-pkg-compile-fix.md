---
categories:
- devops
- ts-shared-pkg-compile-fix
description: Systematic approach to fixing TypeScript compilation errors in pnpm monorepo
  shared packages, focusing on @types/node, module resolution, and barrel exports.
name: ts-shared-pkg-compile-fix
summary: Systematic approach to fixing TypeScript compilation errors in pnpm monorepo
  shared packages, focusing on @types/node, module resolution, and barrel exports.
triggers: []
---

# Shared Package TypeScript Compilation Fixes

When fixing TypeScript compilation errors in a pnpm monorepo shared package (e.g., `@fusheng/shared`), follow this systematic approach. These patterns recur across projects.

## Common Errors & Fixes

### Error: `Cannot find module '@types/node'` or `"types": ["node"]` missing

**Symptom:** `TS2688: Cannot find type definition file for 'node'`

**Fix:**
```bash
# 1. Add @types/node to the shared package (not workspace root!)
pnpm add -D @types/node --filter @fusheng/shared

# 2. Update tsconfig.json types field
{
  "compilerOptions": {
    "types": ["node"]   # ← add this line
  }
}
```

**Why:** TypeScript in Node environments needs `@types/node` for built-in modules (`fs`, `path`, etc.). The `types` field in tsconfig limits which type declaration files are loaded.

### Error: `Module 'X' has no exported member 'Y'`

**Symptom:** Wrong import path for a named export

**Fix:** Use the barrel export (`index.ts`) rather than deep import:
```typescript
// WRONG: import { SeededRandom } from '../rng/mulberry32'
// RIGHT: import { SeededRandom } from '../rng'   ← index.ts re-exports it
```

### Error: `Cannot find module 'fs' / 'path'` in Node.js TS projects

**Symptoms:** `TS2307: Cannot find module 'fs'` etc.

**Fix:** Ensure BOTH conditions are met:
1. `@types/node` is installed as a devDependency of the package
2. `tsconfig.json` has `"types": ["node"]`

### Error: `is possibly undefined` / `implicitly has an 'any' type`

**Symptom:** Strict mode catches missing null checks

**Fix:**
- Use explicit type annotations for JSON-parsed values: `as SeedState`
- Use optional chaining: `state.batches?.[key] ?? defaultValue`
- Don't strip valid code — add proper types

## Verification Steps

After fixes, ALWAYS verify in this order:

```bash
# 1. Compilation
cd /path/to/package && npx tsc --noEmit 2>&1
# Exit code 0 = clean

# 2. Test suite
npx vitest run

# 3. Parent package build (if consumed)
cd /path/to/workspace && pnpm --filter <parent> build
```

## Prevention

- Always add `@types/node` as devDependency before writing Node.js code in TS
- Use barrel exports (`import from '../index'`) to avoid import path drift
- Run `tsc --noEmit` before `tsc` to catch errors early without generating dist
- In pnpm monorepos, each workspace package needs its own `@types/node` (workspace protocol doesn't always propagate types)