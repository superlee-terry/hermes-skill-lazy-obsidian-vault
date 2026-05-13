---
categories:
- devops
description: Detect and resolve false positive TypeScript lint errors (e.g., TS1240,
  TS2564) caused by lint using a simplified tsconfig that disables decorator support
  and library checks.
importance: 0.85
name: ts-lint-false-positive-handler
summary: Detect and resolve false positive TypeScript lint errors (e.g., TS1240, TS2564)
  caused by lint using a simplified tsconfig that disables decorator support and library
  checks.
tags:
- typescript
- lint
- false-positive
- tsconfig
triggers:
- typescript
- lint
- false-positive
- tsconfig
---

# Problem
When using the project's lint script, many TS1xxx/TSxxx errors appear that TSC (tsc --noEmit) does not report. The lint script runs a stripped‑down `tsconfig.generated.json` missing `emitDecoratorMetadata`, `skipLibCheck`, etc., leading to spurious failures.

# Detection Steps
1. Run `npm run lint` and note errors such as `TS1240` or `TS2564` on decorated classes or emitter‑config fields.
2. Compare with `npx tsc --noEmit` – the same errors are absent.
3. Review the lint's `tsconfig.generated.json`; missing `exclude` and `include` sections that disable the real tsc behaviour.

# Resolution Workflow
1. **Verify** – open a failing file and ensure the line causing the error is a real misuse (e.g., using `@Injectable` on a class not decorated with `emitDecoratorMetadata`).
2. **Fix Lint Config** – merge the project’s real `tsconfig.json` (which has proper decorators) into `tsconfig.generated.json` or update the lint script to use the full config.
3. **Alternatively** – add a lint configuration override like `"*{ compilerOptions: { skipLibCheck: true } }"` for specific files.
4. **Run** – `npm run tsc` (or `tsc --noEmit`) to confirm zero errors, then `npm run lint` again to verify the false positives are gone.

# Pitfalls
- Do not disable `emitDecoratorMetadata` if you use NestJS decorators.
- Ensure any generated `tsconfig` is tracked in source control; do not overwrite the real `tsconfig.json`.

# Verification
- After applying the fix, local `npm run lint` should pass (no TS1xxx/TSxxx errors).
- CI lint job should also succeed; if it still fails, re‑run `npm run tsc` to capture any new errors.

# Usage
Include this workflow in lint configuration reviews and when the CI reports many TS1- or TS2- errors that TSC does not raise.

# References
- https://www.typescriptlang.org/docs/handbook/compiler-options.html
- https://nestjs.com/docs/packages/common#customize-dependency-injection