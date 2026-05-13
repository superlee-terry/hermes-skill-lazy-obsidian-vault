# MCP Server Mode 设计规范

## 概述

为 obsidian-skill-vault 添加 MCP Server 模式，作为 Hermes Plugin 的备选方案。通过 stdio 传输暴露 skill_lookup / skill_load / skill_categories 三个 MCP 工具，使任何支持 MCP 的 agent（Hermes、Claude Code、Cursor 等）都能使用。

## 方案

使用 `mcp` Python SDK（>=0.9.0），stdio 传输。新建 `src/main.py` 作为 MCP Server 入口，复用现有 SkillTools / SkillIndexer / VaultOps。

## 架构

```
MCP Client (Hermes/Claude Code)
    │ stdio (JSON-RPC)
    ▼
src/main.py (MCP Server)
    │
    ├── skill_lookup(query, category?, top_k?) → SkillTools.skill_lookup()
    ├── skill_load(name)                        → SkillTools.skill_load()
    └── skill_categories()                      → SkillTools.skill_categories()
```

## 变更清单

1. **新建 `src/main.py`** — MCP Server 入口，用 `mcp` SDK 注册工具
2. **修改 `src/cli.py`** — `serve` 命令调用 `main.py` 的 server
3. **修改 `requirements.txt`** — 添加 `mcp>=0.9.0`
4. **新建 `tests/test_mcp_server.py`** — MCP 工具注册和调用测试

## src/main.py 设计

```python
import mcp.server.stdio
from mcp.server import Server

app = Server("obsidian-skill-vault")

@app.tool("skill_lookup")
def skill_lookup(query: str, category: str = None, top_k: int = 3) -> list[dict]:
    ...

@app.tool("skill_load")
def skill_load(name: str) -> str:
    ...

@app.tool("skill_categories")
def skill_categories() -> list[dict]:
    ...

def serve(vault_path: str, db_path: str):
    # Init VaultOps → Indexer → SkillTools
    # Run MCP server on stdio
```

## Hermes config.yaml 集成方式

```yaml
mcp_servers:
  obsidian-skill-vault:
    command: "obsidian-skill-vault"
    args: ["serve", "--vault", "/path/to/vault"]
```

## 测试策略

- 单元测试：mock stdio，验证工具注册和调用逻辑
- 手动测试：用 `mcp-client` 或直接通过 Hermes 调用

## 依赖

```
mcp>=0.9.0    # 新增
```
