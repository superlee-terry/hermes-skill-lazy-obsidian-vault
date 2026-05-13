# Obsidian Skill Vault — Hermes Plugin 设计规范

## 概述

Hermes Plugin，将技能定义存储在 Obsidian Vault 中，通过 SQLite FTS5 索引实现按需加载（lazy loading），替代 Hermes 默认的全量 `<available_skills>` 预加载机制。

## 产物形态

**Hermes Plugin（standalone kind）** + **MCP Server（备选模式）**

Plugin 通过 `register(ctx)` 注册到 Hermes，不修改 Hermes 核心代码。两种模式共享核心代码，区别仅在入口层：

- Plugin 模式：进程内调用，零延迟
- MCP 模式：stdio 子进程，MCP 协议通信（~50ms 启动开销）

## MVP 范围

### 包含
- `vault_ops.py` — Obsidian Vault 读写（自实现，无 Obsidian 依赖）
- `indexer.py` — SQLite + FTS5 索引构建
- `search.py` — 三路混合检索（trigger → category → FTS）
- `tools.py` — skill_lookup / skill_load / skill_categories 工具注册
- `hooks.py` — on_session_start Hook 注入分类目录
- `migrate.py` — 从 ~/.hermes/skills/ 迁移到 Vault
- `cli.py` — migrate / index / doctor CLI 子命令
- 5-10 个内置示例技能文件

### 不包含（后续迭代）
- PyInstaller 打包
- watchdog 文件监听自动索引更新
- 语义检索（sentence-transformers）
- GitHub Actions CI/CD

## 核心模块

### 1. vault_ops.py — Vault 操作层

直接操作 Markdown + YAML frontmatter 文件，不依赖 Obsidian 桌面端。

```python
class VaultOps:
    def read_note(path) -> dict          # 解析 frontmatter + body
    def write_note(path, meta, body)     # 写入 Obsidian 格式
    def scan_skills(vault_path) -> list  # 递归扫描 vault/skills/**/*.md
    def resolve_wikilink(name) -> str    # [[name]] → 文件路径
```

依赖：pyyaml, python-frontmatter

### 2. indexer.py — 索引构建

SQLite + FTS5，全量构建模式。

```sql
CREATE TABLE skills (
    name TEXT PRIMARY KEY,
    path TEXT NOT NULL,
    categories TEXT,
    tags TEXT,
    triggers TEXT,
    summary TEXT
);
CREATE VIRTUAL TABLE skills_fts USING fts5(
    name, summary, triggers, content=skills
);
```

### 3. search.py — 混合检索

三路检索策略，加权合并：
1. Trigger 精确匹配（权重 0.5）
2. Category 过滤（权重 0.3）
3. FTS5 全文搜索 BM25（权重 0.2）

### 4. tools.py — Hermes 工具

| 工具 | 输入 | 输出 |
|------|------|------|
| skill_lookup | query, category?, top_k? | 元信息列表 |
| skill_load | name | 完整技能内容 |
| skill_categories | — | 分类列表+技能数 |

### 5. hooks.py — 会话启动

`on_session_start` 回调：
- 加载 always_load 核心技能（3-5 个）
- 读取分类目录（~2KB）
- 组装 `<skill_categories>` + `<skill_discovery>` 注入 system prompt

## 数据流

```
用户提问
  → Agent 读分类目录（~2KB，已在 system prompt）
  → Agent 调用 skill_lookup(query)
  → search.py 三路检索 → 返回匹配技能列表
  → Agent 调用 skill_load(name)
  → vault_ops 读取 Markdown → 返回完整技能内容
  → Agent 按技能指令执行任务
```

## 技能文件格式

```markdown
---
name: skill-name
categories: [category1, category2]
tags: [tag1, tag2]
triggers: ["触发词1", "trigger2"]
summary: 一句话描述
---

# Skill Name

（原始 SKILL.md 内容）
```

## 目录结构

```
src/
├── __init__.py      # register(ctx)
├── plugin.yaml      # Plugin 清单
├── config.py        # 配置管理
├── vault_ops.py     # Vault 读写
├── indexer.py       # SQLite 索引
├── search.py        # 混合检索
├── tools.py         # Hermes 工具注册
├── hooks.py         # on_session_start Hook
├── migrate.py       # 迁移逻辑
├── cli.py           # CLI 子命令
├── models.py        # 数据模型
└── main.py          # MCP Server 入口
```

## 设计决策记录

| 决策 | 选择 | 理由 |
|------|------|------|
| Plugin kind | standalone | 用户手动启用，不干扰默认行为 |
| 索引方案 | SQLite FTS5 | 零依赖、嵌入式、纯 Python |
| Vault 操作 | 自实现 | 无官方 Obsidian CLI，只需 Markdown + YAML |
| 检索策略 | 三路混合 | trigger 精确 > category > FTS 全文 |
| 分发方式 | PyInstaller（后续） | 单文件二进制，但 MVP 阶段先 pip install |
