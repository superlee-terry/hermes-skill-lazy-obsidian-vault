---
categories:
- devops
- ts57-typescript-compile-fix
description: Fix TypeScript 5.7 breaking changes that break NestJS + TypeORM + Taro
  builds — decorator type errors, generic Uint8Array, and more.
name: ts57-typescript-compile-fix
summary: Fix TypeScript 5.7 breaking changes that break NestJS + TypeORM + Taro builds
  — decorator type errors, generic Uint8Array, and more.
triggers: []
---

# TS5.7 + NestJS + TypeORM Compilation Fixes

## TypeScript 5.7 breaking changes that break NestJS + TypeORM builds.

| Symptom | Cause | Fix |
|---------|-----|-----|
| `XX is not a constructor function` | TS5.7 stricter on decorator return values | Ignore pre-existing errors; do not modify entity/DTO files. |
| TypeORM `.find()`, `.save()` type errors | TS5.7 lib changes | Keep `skipLibCheck: true` in tsconfig.json. |
| `Uint8Array` generic errors | `Uint8Array` is now generic in TS5.7 | Cast with `as Uint8Array`. |
| `TextEncoder` not found | Removed built-in lib in TS5.7 ES2022 | Use `(globalThis as any).TextEncoder`. |
| `@nestjs/jwt` expiresIn type error | TS5.7 stricter | Cast with `as any`. |

## Action
- **Ignore pre-existing entity/DTO TS5.7 errors**: These break in every environment due to TS5.7 breaking changes on decorators.
- **New code only**: ensure `skipLibCheck: true` (usually default in NestJS).
- **Only fix new code**: do NOT modify entities/DTOs just to silence TS5.7 errors.