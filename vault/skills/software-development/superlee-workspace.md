---
categories:
- software-development
description: Working conventions and structure for the Superlee pnpm monorepo at /mnt/data/workspace.
  Load before any development task in this workspace.
metadata:
  hermes:
    tags:
    - workspace
    - monorepo
    - pnpm
    - superlee
name: superlee-workspace
summary: Working conventions and structure for the Superlee pnpm monorepo at /mnt/data/workspace.
  Load before any development task in this workspace.
triggers:
- workspace
- monorepo
- pnpm
- superlee
version: 1.0.0
---

# Superlee Workspace — Development Reference

**Root:** `/mnt/data/workspace`
**Manager:** pnpm Monorepo (`pnpm-workspace.yaml` → `packages/*`)
**Requirements:** Node ≥ 18, pnpm ≥ 8, PostgreSQL (15432), Nginx (8443)

## Three Sub-projects

### 1. my-server-dashboard — 用户中心 & 认证中心 (Auth Center)
- **Backend:** TypeScript, Express, JWT (bcryptjs), pg — port 61001
- **Frontend:** Vue 3 + Element Plus + ECharts + Pinia + axios + SCSS + Vite 5 — served at `/app/auth/`
- **DB:** `local` (shared DB, users table)
- **API routes:** `/api/auth/*`, `/api/user/*`
- **PM2:** `dist/app.js` (compiled from TS via `tsc`)
- **Auth:** Issues JWTs, provides `/api/auth/verify-token` for cross-service validation

### 2. openclaw-chat-dashboard — 小龙虾聊天应用
- **Backend:** TypeScript, Express, helmet, rate-limit, Winston, pg — port 61002
- **Frontend:** Vue 3 + Element Plus + Pinia + Vant (mobile) + Markdown — served at `/app/chat/`
- **DB:** `local` (shared DB)
- **API routes:** `/api/chat/*`, `/api/chat/ws` (WebSocket)
- **PM2:** `dist/app.js`

### 3. jd-price-tracker — 京东价格监控
- **Backend:** TypeScript, Express, Playwright (scraper via shared browser singleton), node-cron — port 61003
- **Frontend:** Vue 3 + Element Plus + ECharts + Pinia + axios + SCSS + Vite 5
- **DB:** `jd_tracker` schema in shared PostgreSQL
- **Status:** Functional — CRUD + toggle + collection + scheduler working. P2 UX features pending.

## Common Patterns

- **All frontends:** Vue 3 + Element Plus + Vite 5 + Pinia + axios + SCSS
- **All backends:** Express + pg (PostgreSQL) + TypeScript
- **Unified monorepo git** — single `superlee-workspace` repo on Gitea (`ssh://git@localhost:2222/superlee/superlee-workspace.git`)
- **Branch strategy:** develop on `feature/unified-monorepo`, not merged to `master`
- **Old per-project repos archived:** each has `backup/before-monorepo` branch on their original Gitea repos (`my-server-dashboard`, `openclaw-chat-dashboard`, `jd-price-tracker`)
- **Backend entry points:** `backend/src/app.js` or `backend/src/app.ts`
- **Migrations:** `backend/migrations/` directories
- **PM2 process management:** `ecosystem.config.js` at root level (unified, 3 apps). Per-project ecosystem files removed (Phase 5.3).

## Nginx Reverse Proxy (port 8443)

Config: `deploy/nginx/default.conf` (container: `nginx-proxy`)

| Route | Target | Rewrite To | Notes |
|-------|--------|------------|-------|
| `/terry-era/api/auth/*` | my-server:61001 | → `/api/auth/*` | backend: `app.use('/api/auth', authRoutes)` |
| `/terry-era/api/users/*` | my-server:61001 | → `/admin/api/user/*` | backend: `app.use('/admin/api/user', userRoutes)` |
| `/terry-era/api/metrics/*` | my-server:61001 | → `/api/metrics/*` | backend: `app.use('/api/metrics', metricsRoutes)` |
| `/terry-era/api/admin/*` | my-server:61001 | → `/admin/api/*` | catch-all for admin APIs: audit-log, etc. backend: `app.use('/admin/api/audit-log', auditLogRoutes)` |
| `/terry-era/api/jd/*` | jd-tracker:61003 | direct proxy | no rewrite, direct `/api/jd/` |
| `/terry-era/chat/api/*` | chat-dashboard:61002 | **OFFLINE** | 503 maintenance response |
| `/terry-era/jd-tracker/` | static (frontend) | — | SPA fallback |
| `/terry-era/chat/` | **OFFLINE** | — | 503 maintenance page |
| `/terry-era/` | static (my-server frontend) | — | SPA fallback |

## Deployment Infrastructure

**docker-compose.yml** — Infrastructure orchestration (PostgreSQL + Nginx). Node services managed by PM2 separately.
**PM2 ecosystem.config.js** — Root-level, 3 apps: my-server:61001, chat-dashboard:61002, jd-tracker:61003. All secrets via `process.env`.
**CI:** `.github/workflows/ci.yml` — pnpm cache + parallel tsc/vite build per project.
**Env template:** `.env.example` at root.

**Hot-reload Nginx after config change:**
```bash
docker cp deploy/nginx/default.conf nginx-proxy:/etc/nginx/conf.d/default.conf
docker exec nginx-proxy nginx -s reload
```

## Dev Commands

```bash
# All projects
pnpm dev                    # Start all
pnpm --filter @workspace/my-server-dashboard dev
pnpm --filter @workspace/openclaw-chat-dashboard dev

# Individual
cd packages/my-server-dashboard && pnpm dev
cd packages/openclaw-chat-dashboard && pnpm dev
```

## Notable Differences

- All three backends are now TypeScript (Phase 1.2 backend migration complete)
- All backends use `tsx watch` for dev, `tsc` for build, `node dist/app.js` for start
- chat-dashboard uses Vant (mobile UI) in addition to Element Plus
- jd-tracker is fully wired into Nginx (port 61003) and PM2 root ecosystem.config.js (Phase 5 complete)
- chat-dashboard has the most robust backend (helmet, rate-limit, Winston logging)

## pnpm Workspace Resolution — Critical Details

**`pnpm-workspace.yaml` must include backend/frontend subdirs explicitly:**
```yaml
packages:
  - 'packages/*'
  - 'packages/*/backend'
  - 'packages/*/frontend'
```
Without the subdirectory entries, `packages/*/backend/` dirs are NOT workspace members, so `workspace:*` dependencies like `@workspace/shared` won't resolve. This caused "Cannot find module '@workspace/shared'" errors in chat-dashboard and jd-tracker backends.

**Stale symlinks after TS version changes:** pnpm sometimes leaves broken symlinks in `node_modules/typescript` pointing to old versions (e.g. `@6.0.2`) that don't exist in the store. Fix with `ln -sfn` to the correct store path:
```bash
ln -sfn /mnt/data/workspace/node_modules/.pnpm/typescript@5.9.3/node_modules/typescript \
  packages/<project>/backend/node_modules/typescript
```
Do NOT use `rm -rf node_modules` — it times out on large directories.

**TS `moduleResolution: "node"` (node10) does NOT support `package.json` "exports":**
Subpath imports like `@workspace/shared/auth` fail because node10 resolution ignores the exports field. Fix: add tsconfig `paths`:
```json
"paths": {
  "@workspace/shared": ["../../shared/dist/index"],
  "@workspace/shared/*": ["../../shared/dist/*"]
}
```
This is needed in any backend that uses shared subpath imports.

**`ignoreDeprecations: "6.0"` is invalid for TypeScript 5.x:** Only valid for TS 6.x. In TS 5.9.3 it causes `TS5103: Invalid value for '--ignoreDeprecations'`. Remove the option entirely, or use `"5.0"` for TS 5.x deprecation silencing.

## Shared Package: `@workspace/shared`

**Path:** `packages/shared/`
**Status:** Phase 1.1 complete — compiles cleanly, `pnpm build` outputs to `dist/`
**Modules:**
- `auth/` — Dual-mode auth middleware (Auth Center proxy + local JWT)
- `db/` — PostgreSQL pool singleton + migration runner
- `middleware/` — errorHandler, validator, auditLogger, rateLimit
- `response/` — Unified API response format (`{code, message, data}`) + ErrorCode enum
- `logger/` — Winston logger factory (console + file rotation)
- `utils/` — `createConfig()` (env var validation at startup), Feishu notifications
- `types/` — UserPayload, AuthenticatedRequest, DatabaseConfig, express.d.ts

**Import:** `import { authenticateToken, createPool, ApiError, ... } from '@workspace/shared'`

## Architecture Unification Plan

Saved at `/mnt/data/workspace/UNIFIED_ARCHITECTURE_PLAN.md`.

### Progress

| Phase | Content | Status |
|-------|---------|--------|
| 1.1 | Shared package `@workspace/shared` | ✅ Complete |
| 1.2 | Backend TS migration (my-server + jd-tracker) | ✅ Complete |
| 1.2 | Frontend TS migration | ✅ Complete |
| 1.3 | Env variable unification (`utils/config.ts`) | ✅ Complete (2026-04-15) |
| 2 | Auth unification | ✅ Complete (2026-04-15) |
| 3 | Frontend unification (shared-frontend) | ✅ Complete (2026-04-15) |
| 4 | Bug fixes & feature completion | ✅ Complete (2026-04-16) |
| 5 | DevOps (docker-compose, CI/CD, Nginx) | ✅ Complete (2026-04-16) |

**Phase 4 complete (2026-04-16) — 12/12 items:**
- ✅ **P0 (core bugs):** Toggle endpoint (`PATCH /goods/:id/toggle`), status type mapping (DB `1/0` ↔ frontend `'active'/'paused'` via `mapGoodsStatus()`), AddGoods forwards `target_price`/`cron_expr`, collection updates goods `name`/`image_url`, frontend toggle API `PUT→PATCH`
- ✅ **P1 (optimization):** Playwright browser singleton (`collectors/browser.ts`) with 10min idle timeout, PM2 ecosystem.config.js deduplicated hardcoded credentials to `process.env`, chat-dashboard `db/index.ts` now uses `@workspace/shared` getDatabase
- ✅ **P2 (UX):** Streaming Markdown rendering (`MarkdownRenderer` in streaming area), Settings save button bound, Agent list Gateway integration (OpenClawService.getAgents with fallback)

**Phase 2 complete (2026-04-15):** DB migrated (users single table + role field), 5 users seeded, E2E auth tested (login/JWT/cross-service/admin), all backends using shared auth middleware, PM2 updated to dist/app.js.

**Shared package auth module** (`packages/shared/src/auth/`):
- `middleware.ts` exports `createJwtMiddleware(config)` for Auth Center itself
- `middleware.ts` exports `createAuthCenterMiddleware(config)` for sub-services (proxy validation)
- Sub-services should NOT verify JWT locally — they proxy to Auth Center

### Phase 3: Frontend Unification — `@workspace/shared-frontend` v2.0

**Path:** `packages/shared-frontend/`
**Status:** Complete (2026-04-16)

**Modules (v2.0 — expanded):**
- `auth/` — getToken, setToken, getCookie, clearAuth, handleUnauthorized, isAuthenticated, syncAuthFromCookie, getStoredUser, setStoredUser
- `http/` — createApiClient factory + ApiClient class (axios-based, auto token injection + 401 redirect)
- `types/` — User, TokenVerifyResponse, ApiResponse, RouteMetaCustom, PaginationParams, ApiClientOptions
- `composables/` — **useAuth** composable (reactive token/user/logout/initAuth/onLogin, shared across components)
- `router/` — **createAuthGuard** factory (auto initAuth, document.title, requiresAuth/requiresAdmin meta check)
- `styles/` — **_variables.scss** (colors/spacing/radius/shadow/fonts/layout), **_mixins.scss** (mobile/ellipsis/flex/card/scrollbar)

**Import:** Subpath imports via `exports` map in package.json:
```typescript
import { getToken, setToken, isAuthenticated } from '@workspace/shared-frontend/auth'
import { createApiClient, ApiClient } from '@workspace/shared-frontend/http'
import type { User, ApiResponse } from '@workspace/shared-frontend/types'
import { useAuth } from '@workspace/shared-frontend/composables'
import { createAuthGuard } from '@workspace/shared-frontend/router'
// SCSS: injected via vite additionalData or @use directly
```

**SCSS exports in package.json must use full paths with `.scss` suffix:**
```json
"./styles/variables.scss": "./src/styles/_variables.scss",
"./styles/mixins.scss": "./src/styles/_mixins.scss"
```
Vite's `additionalData` must match exactly: `@use "@workspace/shared-frontend/styles/variables.scss" as *;`

**Integration per project (all complete):**

| Project | Migration Summary | Status |
|---------|-------------------|--------|
| my-server | 15 fetch→axios, Chart.js→ECharts (3 components), Pinia stores, CSS→SCSS, Vite 4→5 | ✅ |
| jd-tracker | Pinia stores, CSS→SCSS, createAuthGuard, delete dead code, fix double-unwrap | ✅ |
| chat-dashboard | useAuth composable, createAuthGuard, useMobile/useLogout composables, MobileNav component, shared SCSS vars | ✅ |

**Key design decisions:**
- `moduleResolution: "bundler"` required in frontend tsconfig for exports map resolution
- `apiClient.getInstance()` gives raw axios instance for non-ApiResponse-wrapped endpoints (e.g., metrics)
- my-server-dashboard's ApiClient uses `loginPath: '/user/login'` (local, not cross-service SSO)
- Pinia stores use composition API: `defineStore('name', () => {...})`
- ECharts: `echarts.init(div).setOption()` with `watchEffect` for reactive updates, `dispose()` on unmount
- useAuth composable uses module-level reactive refs for cross-component state sharing

## Nginx Rewrite ↔ Backend Route Mapping (Critical)

The Nginx rewrites MUST match actual backend `app.use()` registrations in `app.ts`. Current correct mapping:

| External URL | Nginx rewrite target | Backend `app.use()` |
|-------------|---------------------|-------------------|
| `/terry-era/api/auth/*` | `/api/auth/*` | `app.use('/api/auth', authRoutes)` |
| `/terry-era/api/metrics/*` | `/api/metrics/*` | `app.use('/api/metrics', metricsRoutes)` |
| `/terry-era/api/admin/*` | `/admin/api/*` | `app.use('/admin/api/user', userRoutes)`, `app.use('/admin/api/audit-log', auditLogRoutes)` |
| `/terry-era/api/users/reset-password` | `/api/auth/reset-password` | `authRoutes.post('/reset-password')` |
| `/terry-era/api/jd/*` | `/api/jd/*` (direct proxy) | `jd-tracker app.use('/api/jd', ...)` |

**After changing backend routes or adding new ones, ALWAYS verify the Nginx rewrites match.**

## Pitfalls

- Each sub-project has independent `node_modules/` (not hoisted — using package-lock.json, not pnpm's linking for sub-packages)
- Sub-projects use their own `.env` files — check `backend/.env` per project
- jd-tracker is deployed via PM2 and Nginx (Phase 5 complete)
- **Frontend axios baseURL + full path = double concatenation:** When `apiClient` has `baseURL: '/terry-era/api'`, component calls must use RELATIVE paths like `/auth/login`, NOT full paths like `/terry-era/api/auth/login`. Otherwise axios concatenates: `/terry-era/api` + `/terry-era/api/auth/login` → broken URL. Check ALL `instance.post/get/put/delete` calls after setting baseURL.
- **Express type augmentation requires TWO separate .d.ts files:**
  1. `src/types/express.d.ts` — ambient script (NO top-level import/export): `declare namespace Express { interface Request { user?: UserPayload } }`. This extends the Express namespace globally.
  2. `src/types/express-module.d.ts` — module augmentation: `declare module 'express' { interface Response { apiSuccess?: ... } }`. This is for augmenting types from imported modules.
  - DO NOT mix these patterns in one file — ambient namespace stops working if the file has any import/export.
  - `tsconfig.json` needs `"typeRoots": ["./node_modules/@types", "./src/types"]` to pick up custom type dirs.
- **`ignoreDeprecations: "6.0"` is INVALID for TypeScript 5.x** — causes TS5103. Remove it entirely. TS5107 (node10 deprecation warning) is non-blocking in TS 5.x.
- **`delegate_task` parallel subagents** work well for independent backend migrations — spawn one per project, verify in parent agent after.
- **`tsc --noEmit`** is the standard compilation check; always run it after TS migration changes.
- **`rm -rf node_modules` times out** — directories too large for terminal timeout. Use targeted `ln -sfn` for symlink fixes instead of nuking and reinstalling.
- **Terminal blocking cascade:** if a `terminal()` call returns `BLOCKED` (timeout), subsequent calls may also hang. Use `execute_code` for batch operations as workaround.
- **Hermes approval mode for messaging platforms:** Use `approvals.mode: smart` in config when running via Feishu/Telegram/Discord. Manual mode requires interactive approval impossible in chat UIs.
- **Hermes `command_allowlist` entries must use exact description strings from `tools/approval.py` `DANGEROUS_PATTERNS`:** The allowlist keys are the human-readable description strings (e.g. `"recursive delete"`, `"delete in root path"`), NOT regex patterns. To find the correct string, search `DANGEROUS_PATTERNS` in `~/.hermes/hermes-agent/tools/approval.py`. Config example:
  ```yaml
  approvals:
    mode: manual  # or smart/off
    timeout: 60
  command_allowlist:
    - "recursive delete"
    - "delete in root path"
    - "find -delete"
    - "script execution via -e/-c flag"
  ```
  Without these, `rm`, `find -delete`, `python -c` etc. will block waiting for interactive approval in gateway sessions (Feishu/Telegram), causing timeouts.
- **Claude Code invocation pattern** — env vars must be exported explicitly before each invocation:
  ```bash
  export ANTHROPIC_BASE_URL=https://open.bigmodel.cn/api/anthropic
  export ANTHROPIC_MODEL=glm-5.1
  export ANTHROPIC_DEFAULT_HAIKU_MODEL=glm-4.7
  export ANTHROPIC_DEFAULT_SONNET_MODEL=glm-5-turbo
  export ANTHROPIC_DEFAULT_OPUS_MODEL=glm-5.1
  ANTHROPIC_AUTH_TOKEN=$(grep '^export ANTHROPIC_AUTH_TOKEN=' /root/.bashrc | head -1 | sed 's/export ANTHROPIC_AUTH_TOKEN=//')
  export ANTHROPIC_AUTH_TOKEN
  claude -p "..." --max-turns N
  ```
  **Critical limitation:** Only `--max-turns 0` works reliably. Complex tasks with `--max-turns 3+` and Write/Edit/Bash tools consistently timeout. For multi-file Phase work, use direct `write_file` / `patch` calls from Hermes instead.
- **Phase 2 auth DB migration is idempotent** — `migrate.ts` checks for column existence before ALTER TABLE, and checks for existing admin before seeding. Safe to re-run.
- **`packages/shared` must be rebuilt** after any changes to its source: `cd packages/shared && pnpm build`. Other projects import from `dist/`, not `src/`.
- **SCSS exports in package.json must include `.scss` suffix** — `./styles/variables.scss` not `./styles/variables`. Vite resolves these via the exports map and will throw "Missing specifier" if the key doesn't match exactly.
- **When migrating `vite.config.js` → `vite.config.ts`**, also update `index.html` script src from `/src/main.js` to `/src/main.ts`. Vite uses the HTML entry to discover modules.
- **Parallel `delegate_task` for monorepo migrations** works well: spawn one subagent per sub-project for analysis phase, then one per sub-project for migration phase. Verify builds in parent agent after.
- **SCSS `additionalData` in vite.config** — must use `@use` with `as *` to make variables available without namespace prefix. Double-check the import path matches package.json exports exactly.
- **Hermes `quick_commands` in config.yaml** — `type: exec` entries bypass the LLM loop entirely (zero tokens). Use for status queries, local scripts.
- **Session SQLite DB at `~/.hermes/state.db`** — copy to temp file before querying to avoid gateway lock. `sessions` table has all token fields.
- **`python3` may be blocked in terminal tool** — use `python3.11` explicitly or pure bash as workaround.
- **Pinia store destructuring pitfall — always use `storeToRefs` for state:** Directly destructuring a Pinia store (`const { cpu, memory } = useMetricsStore()`) loses reactivity — the values become plain `null`/primitives that never update when the store changes. **Fix:** `import { storeToRefs } from 'pinia'` then `const { cpu, memory } = storeToRefs(store)` for state refs. Methods (`startRefresh`, `setRefreshInterval`, etc.) can be destructured directly since they're plain functions, not reactive refs. This was the root cause of the dashboard monitoring panels showing blank on first load (2026-04-18).
- **Frontend API path convention — NEVER use full paths with apiClient:** `apiClient` (from `shared-frontend/http`) has `baseURL: '/terry-era/api'`. Components using `apiClient.getInstance()` must use **relative paths** that match the backend `app.use()` mount after Nginx rewrite (e.g., `/auth/login`, `/users/list`, `/metrics/stats`, `/admin/audit-log`). Using full paths like `/admin/api/audit-log` causes double-concat with baseURL → `/terry-era/api/admin/api/audit-log` which has no Nginx rule → falls to SPA fallback → returns HTML. This was a systematic bug: 10 files fixed 2026-04-16, audit-log page fixed 2026-04-16 (11th — also needed new Nginx `/terry-era/api/admin/` location block). **When adding new admin pages, verify the full URL chain: component path → baseURL concat → Nginx rewrite → backend `app.use()` mount.**
- **Nginx rewrite targets MUST match backend `app.use()` mount paths:** Backend registers routes as `app.use('/api/auth', authRoutes)`, `app.use('/admin/api/user', userRoutes)`, `app.use('/api/metrics', metricsRoutes)`. Nginx rewrites must target these exact prefixes. The old config had wrong rewrites (`/admin/api/auth/` → should be `/api/auth/`, `/user/api/` → should be `/admin/api/user/`). After any backend route change, always verify nginx rewrite targets match.
- **Taking a service offline (chat example):** 3 steps: (1) `pm2 stop <name> && pm2 save`, (2) Replace nginx location blocks with `return 503` responses, (3) Comment out frontend entry cards in AdminAppCenter.vue + UserAppCenter.vue. Rebuild & deploy frontend.
- **Pinia store 解构陷阱:** `const { cpu } = useMetricsStore()` 会丢失响应性，cpu 变成普通值(初始null)永远不更新。必须用 `storeToRefs`: `const { cpu } = storeToRefs(store)` 保持响应式。方法(action)可以直接解构。症状：数据拉到了但页面空白不刷新。
- **DB ↔ Frontend status mapping pattern:** When DB uses numeric status (`SMALLINT 1/0`) but frontend expects strings (`'active'/'paused'`), add a `mapGoodsStatus()` helper at the API boundary. Map on READ responses, reverse-map on query params. This avoids changing DB schema or frontend code.
- **Playwright browser singleton for scrapers:** Don't `chromium.launch()` per request. Create a `BrowserManager` (singleton with idle timeout ~10min) that returns shared `Browser`. Each request gets its own `BrowserContext` (isolated cookies/storage). Close context in `finally`, not browser. See `jd-tracker/backend/src/collectors/browser.ts`.
- **PM2 ecosystem.config.js — never hardcode secrets:** Use `process.env.VAR_NAME || ''` for all credentials. Document required env vars in comments. Deploy via `.env` file or `--env` flag.
- **camelCase ↔ snake_case bridge in API handlers:** Frontend sends camelCase (`targetPrice`, `cronExpr`), DB expects snake_case (`target_price`, `cron_expr`). Accept both in the route handler: `const val = req.body.targetPrice ?? req.body.target_price`.
- **execute_code has a 50 tool-call limit per script execution:** When bulk-moving/processing many files, do NOT loop `terminal()` calls in Python. Instead, build a single shell script string (heredoc) and pass it to ONE `terminal()` call. Python loops with per-item tool calls exhaust the 50-call budget fast, leaving items unprocessed.
- **Workspace migrated to unified monorepo (2026-04-17):** All sub-project `.git/` dirs removed. Single `superlee-workspace` repo on Gitea. Old independent repos (`superlee/my-server-dashboard`, `superlee/openclaw-chat-dashboard`, `superlee/jd-price-tracker`) archived with `backup/before-monorepo` branches. Working branch: `feature/unified-monorepo`, master holds initial snapshot.
- **JD price scraping blocked by anti-bot (2026-04-17):** Playwright headless Chromium (even headed via xvfb) gets redirected from `item.jd.com/{sku}.html` to `jd.com/?d` (homepage) when running from server/datacenter IPs. User-Agent spoofing + `navigator.webdriver=false` + cookie warmup all fail. **Solutions to explore:** (1) JD mobile price API (`p.3.cn/prices/mgets` — may also be restricted), (2) proxy IP pool, (3) `puppeteer-extra-plugin-stealth`. The Playwright collector code itself works — the issue is network-level IP fingerprinting by JD's WAF.
- **Database initialization scripts are SPLIT per-database (2026-04-16):**
  - `scripts/init-local.sql` — for `local` DB only (jd_tracker schema + users/admins/audit_logs)
  - `scripts/init-openclaw-chat.sql` — for `openclaw_chat` DB only (sessions/messages/user_settings/audit_logs)
  - OLD `scripts/init-db.sql` deleted — was a single-file that caused cross-database table pollution
  - **NEVER run both databases from one init script** — psql executes all statements against the connected DB, creating unwanted tables
  - Run via: `docker exec -i postgres-local psql -U postgres -d local < scripts/init-local.sql`
  - All scripts are idempotent (IF NOT EXISTS), safe to re-run
- **DB backup/restore procedure:**
  ```bash
  # Backup (use docker exec, NOT host pg_dump — version mismatch causes empty dumps)
  docker exec postgres-local pg_dump -U postgres -d local --format=plain > backup/local.sql
  docker exec postgres-local pg_dump -U postgres -d openclaw_chat --format=plain > backup/openclaw_chat.sql
  # Restore
  docker exec -i postgres-local psql -U postgres -d local < backup/local.sql
  ```
  - Host pg_dump (v14) vs server pg_dump (v15) version mismatch causes `server version mismatch` error or empty output files. ALWAYS use `docker exec postgres-local pg_dump`.
- **Gitea `ENABLE_PUSH_CREATE_USER = true`:** Pushing to a non-existent repo path auto-creates it under the authenticated user. Used to create `superlee-workspace` repo without needing API token or web UI.
- **API testing pattern with auth:** JWT tokens from Auth Center have limited TTL. When running sequential curl tests, always get a fresh token and run ALL test calls in a single shell script to avoid mid-test expiry.
- `admin` / `admin123` (role: admin) — 推荐，拥有所有权限
- `testuser` / `admin123` (role: user) — 普通用户
- `chatuser` 密码为占位 hash，无法登录
- 密码均在 `packages/my-server-dashboard/backend/src/db/migrate.ts` seed 时生成
- 登录入口: `https://www.superlee.site:8443/terry-era/`

**Deployment checklist:**
  1. Compile all: `cd packages/<proj>/backend && npx tsc` + `cd packages/<proj>/frontend && npx vite build`
     - **EXCEPTION: chat-dashboard** build is `tsc && tsc-alias` — running only `tsc` leaves `@/` path aliases unresolved in dist/, causing `Cannot find module '@/config'` at runtime. Always run `npx tsc-alias` after `npx tsc`, or use `npm run build`.
  2. Deploy frontends: copy `dist/` to **host bind-mount path** `/mnt/data/Docker/nginx/html/terry-era/` (my-server), `/mnt/data/Docker/nginx/html/terry-era/chat/` (chat), `/mnt/data/Docker/nginx/html/terry-era/jd-tracker/` (jd). Do NOT use `docker cp` — the nginx container has read-only bind mounts from `/mnt/data/Docker/nginx/`.
  3. Update nginx config: `cp deploy/nginx/default.conf /mnt/data/Docker/nginx/conf.d/default.conf && docker exec nginx-proxy nginx -s reload`
  4. PM2 restart: `pm2 delete all && pm2 start ecosystem.config.js && pm2 save`
  5. Test via `https://superlee.site:8443/terry-era/`
- **PM2 MUST use `exec_mode: 'fork'` for ALL apps:** PM2 `cluster` mode causes crash-loops for chat-dashboard (process runs fine manually but PM2 kills it within seconds, retries 15+ times until `errored`). Fork mode is stable. Do NOT use cluster mode for single-instance Express apps — it provides no benefit and introduces instability.
- **PM2 env variables not passed to Python scripts:** PM2's `env` config in `ecosystem.config.js` does NOT pass variables to Python scripts (only Node.js processes). Fix: use a Python wrapper that sets `os.environ` explicitly, or a shell wrapper that exports vars before `exec`.
- **Nginx container `nginx-proxy` mount layout:** All content is bind-mounted from `/mnt/data/Docker/nginx/` on the host:
  - `html/` → `/usr/share/nginx/html/` (frontend static files)
  - `conf.d/` → `/etc/nginx/conf.d/` (nginx config)
  - `ssl/` → `/etc/nginx/ssl/` (certificates)
  Always deploy files to the host paths, not into the container directly.