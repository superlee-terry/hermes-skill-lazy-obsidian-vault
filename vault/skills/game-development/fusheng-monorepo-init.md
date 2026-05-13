---
categories:
- game-development
description: 'Initialize the 《浮生剑录》 pnpm monorepo with Taro 3 client, NestJS server,
  and shared package. Documents proven structure, dependency config, and known pitfalls.

  '
name: fusheng-monorepo-init
summary: Initialize the 《浮生剑录》 pnpm monorepo with Taro 3 client, NestJS server, and
  shared package. Documents proven structure, dependency config, and known pitfalls.
triggers: []
---

# 《浮生剑录》 Monorepo 初始化指南

## Structure

```
/mnt/data/worldGameSpace/
├── package.json              # monorepo root (no deps, scripts as aliases)
├── pnpm-workspace.yaml       # packages/* + apps/*
├── .npmrc                    # onlyBuiltDependencies (see Pitfall #1)
├── packages/
│   └── shared/               # @fusheng/shared (types/constants/formulas/rng/battle)
├── apps/
│   ├── fusheng-client/       # Taro 3 + React + TS + Zustand
│   └── fusheng-server/       # NestJS 11 + TypeORM + Bull + Socket.io
└── docs/                     # 策划文档 (已有)
```

## Key Dependencies

- **Taro**: `4.0.9` (all @tarojs/* packages must be same version)
- **NestJS**: `^11.0.0` + `@nestjs/config` (must add separately, not auto-included)
- **Shared**: `workspace:*` protocol in both client and server
- **Build**: shared uses `tsc`, server uses `nest build`, client uses `taro build`

## Steps

1. Create root `package.json` (private, no deps) + `pnpm-workspace.yaml`
2. Create `packages/shared` with src/{types,constants,formulas,rng} — build with `tsc`
3. Create `apps/fusheng-server` — NestJS with 8 modules (player,item,battle,pvp,social,tower,seed,anticheat)
4. Create `apps/fusheng-client` — Taro 3 with config/index.js (merge pattern), 10 pages, Zustand store
5. Create `.npmrc` with `onlyBuiltDependencies` (see Pitfall #1)
6. `pnpm install` then `pnpm --filter @fusheng/shared build`
7. `pnpm --filter fusheng-server build`

## NestJS Module Names

No hyphens in module directory/class names — TypeScript class names can't contain hyphens:
- `anti-cheat` → `anticheat` / `AnticheatModule`

## Shared Package Constraints

- Zero platform-specific imports (no `node:*`, no `@tarojs/*`, no 小程序API)
- All functions must be pure (no side effects) for cross-platform determinism
- `DropEntry`/`GatherEntry` types don't have `count` field — use type assertion: `as DropEntry & { count: number }`

## Pitfalls

1. **pnpm onlyBuiltDependencies**: Must be in root `package.json` under `"pnpm"` key, NOT in `.npmrc`. Without this, @nestjs/core, esbuild, @swc/core etc. won't run postinstall scripts and builds will fail.
2. **@nestjs/config**: Not included with `@nestjs/common` — must `pnpm add @nestjs/config` separately.
3. **NestJS tsconfig needs `"types": ["node"]`**: Without it, `Buffer`, `stream`, `util` types from @nestjs/common declarations won't resolve.
4. **Taro app.config.ts**: Uses `defineAppConfig()` export (global function injected by Taro), NOT a React component. Keep it as a plain `.ts` file.
5. **Taro version lock**: All `@tarojs/*` packages must be the exact same version (e.g., `4.0.9`). Mixing versions causes cryptic build errors.
6. **TypeORM Entity strictPropertyInitialization**: TypeORM entities with `@Column()` decorators cause 93+ TS2564 errors under `"strict": true`. Fix: add `"strictPropertyInitialization": false` to `apps/fusheng-server/tsconfig.json`. This is standard practice for NestJS+TypeORM projects — ORMs hydrate properties via reflection, not constructors.
7. **execute_code write_file 可靠性**: `execute_code` 内部的 `hermes_tools.write_file` 可能静默失败（文件不生成），尤其当路径包含多层不存在的目录时。**Fix**: 对关键文件写入一律使用顶层 `write_file` 工具，它有自动创建父目录的能力。
8. **Vitest `__tests__/` 子目录 import 路径**: 测试文件放在 `__tests__/` 子目录时，相对路径需要多退一层。如 `src/battle/__tests__/engine.test.ts` 导入 `src/battle/engine.ts` 应写 `'../engine'` 而非 `'../src/battle/engine'`。

## Verification Commands

```bash
pnpm --filter @fusheng/shared build   # shared compiles
pnpm --filter fusheng-server build     # server compiles
pnpm dev:client                         # Taro weapp dev
pnpm dev:server                         # NestJS dev (port 3000)
```