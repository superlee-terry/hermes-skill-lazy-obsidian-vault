---
categories:
- game-development
- wechat-taro-login-loop
description: Full WeChat Mini Program login integration with Taro client and NestJS
  server — code exchange, JWT, token refresh, and persistent store.
name: wechat-taro-login-loop
summary: Full WeChat Mini Program login integration with Taro client and NestJS server
  — code exchange, JWT, token refresh, and persistent store.
triggers: []
---

# WeChat Mini Program Login Integration (Taro + NestJS)

Implement the full login loop for a Taro-based WeChat Mini Program with a NestJS backend, handling code exchange, JWT issuance, and token storage.

## Architecture Decisions
- **Backend:** NestJS using `@nestjs/jwt`. `PlayerService` handles DB logic; `AuthService` handles auth. Use `forwardRef` to resolve circular dependency.
- **Frontend:** Taro (React). Request layer must intercept requests to handle token refresh (401 flow) to avoid infinite loops.

## Implementation Steps

### 1. Backend (NestJS) - `auth.service.ts`
- Inject `PlayerService` using `forwardRef`.
- `wxLogin(code: string)` logic:
  1. Call WeChat `code2Session` to get `openid`.
  2. Call `playerService.findOrCreatePlayer(openid)` to get the player row.
  3. Generate JWT: `{ id: player.id, openid: player.openid }`.
  4. Return `{ accessToken, refreshToken, expiresIn }`.
- **TS 5.7 Pitfall:** `expiresIn` needs `as any` in `@nestjs/jwt`.
- **Circular Dependency Fix:** `forwardRef(() => PlayerModule)` in imports, `forwardRef(() => this.playerService)` in constructor.

### 2. Frontend (Taro) - `utils/request.ts`
- Use `Taro.request` wrapping.
- **Interceptor Logic:**
  1. Attach `Authorization: Bearer <token>`.
  2. On **401** response: stop subsequent requests, call `POST /auth/refresh-token`, retry with new token.
  3. If refresh fails: clear token and show "Please login" toast.
  4. **Prevent Infinite Loops:** Queue concurrent requests during refresh (single refresh per queue, retry on success).

### 3. Frontend (Taro) - `store/player.ts`
- State: `accessToken`, `refreshToken`.
- `setTokens(at, rt, expires)`: `Taro.setStorageSync('fusheng_token', ...)`.
- `clearToken()`: `Taro.removeStorageSync(...)`.
- `login()`: `Taro.login()` → get `code` → `POST /auth/wx-login` → update state.

### 4. Frontend (Taro) - Page Init (`pages/index`)
- `useEffect` checks localStorage → restore or trigger login.

## Pitfalls
- NestJS `@InjectRepository`/`@Inject` on constructor only, not class body.
- Taro HTTP relative paths only.
- TypeScript 5.7 entity decorator errors are pre-existing; ignore them during new work.
- Always queue concurrent requests when refreshing tokens.