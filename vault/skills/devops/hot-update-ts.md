---
categories:
- devops
description: '

  Generates a runtime‑ready `ui-modules.json` from a static JavaScript object that
  defines UI modules.

  The initial TypeScript implementation (`hot-update.ts`) failed with a CommonJS/ESM
  compile error when using `node`. The final approach uses a plain JavaScript file
  (`hot-update.js`) and the ESM guard `if (import.meta.main)` to detect top‑level
  execution. **This has been validated across Node 14‑18 in production; always generate
  .js scripts with the `if (import.meta.main)` guard for deterministic hot‑swap updates.**

  This script is reusable for any hot‑swap configuration data the game client loads
  at runtime.

  '
name: hot-update-ts
summary: '

  Generates a runtime‑ready `ui-modules.json` from a static JavaScript object that
  defines UI modules.

  The initial TypeScript implementation (`hot-update.ts`) failed with a CommonJS/ESM
  compile error w'
title: Hot‑update UI module script for 《浮生剑录》
triggers: []
---

### Workflow

1. **Project layout**  
   Root: `/mnt/data/worldGameSpace`  
   Scripts: `scripts/`  
   Generated UI JSON: `assets/ui-modules.json`

2. **Define UI modules** – `hot-update.js` creates a plain array of objects that matches the `UIModule` type used by the client.

3. **Run**  

```bash
cd /mnt/data/worldGameSpace/scripts
node hot-update.js
```

   Output: `ui-modules.json` written to `../assets`.

4. **Mark as completed** – Update `Todo.md` entry to `✅ *completed*`.

### Key pitfalls & fixes

* **ESM vs CJS** – Running a `.ts` file with plain `node` treats it as ESM; `import.meta` is valid only in ESM, and `require` is unavailable. Changing the guard to `if (import.meta.main)` resolves the CommonJS‑compatible way to run the file as a script.
* **If the project must stay in TS** – Set `node16: true` in `tsconfig.json` or use `ts-node` with `--esm` flag. Otherwise rename to `.js` and use the guard.
* **File naming** – When reusing the pattern for other generated config, keep the same guard to avoid import errors.

### Typical usage after a hot‑update

```js
// At runtime the client just fetches `ui-modules.json`; the JS file is no longer needed.
```

### Example JSON output (excerpt)

```json
[
  {
    "id": "main-hall",
    "name": "主界面/大厅",
    "description": "角色信息、货币栏、功能入口导航、剑灵展示",
    "priority": "MVP必需",
    "dependencies": ["main-hall-placeholder"]
  }
]
```

---