# 架构设计：Obsidian 驱动的 Hermes Skill Lazy Loading

## 1. 核心问题

Hermes Agent 默认将所有 `~/.hermes/skills/**/*.md/SKILL.md` 构建为一个 `<available_skills>` 文本块注入 system prompt。当技能数量超过数百个时：

- **Context 膨胀**：2,147+ 技能产生 ~100KB 的技能索引，每次 API 调用都要付费
- **Prompt Cache 失效**：技能索引变更导致缓存失效，增加延迟和成本
- **检索效率低**：线性扫描全部技能描述，LLM 需要从海量文本中定位相关技能

## 2. 设计目标

| 目标 | 指标 |
|------|------|
| 减少 system prompt 中技能索引体积 | 从 ~100KB 降到 ~2KB（分类目录） |
| 支持大规模技能库 | 10K+ 技能不影响 context |
| 兼容 Hermes 现有 MCP 工具接口 | 无需修改 Hermes 核心代码 |
| 利用 Obsidian 进行技能管理 | 分类、搜索、可视化通过 Obsidian 完成 |
| 保持检索精度 | 按需加载的技能与全量预加载效果等价 |

## 3. 产物形态与集成方式

### 3.1 输出形态：Hermes Plugin（首选） + MCP Server（备选）

本项目的产物是 **Hermes Plugin**，不是独立应用。理由：

Hermes 有完整的 Plugin 系统（`plugin.yaml` + `__init__.py` + `register(ctx)`），提供 6 种注册能力：

| 能力 | 对应 API | 本项目用途 |
|------|---------|-----------|
| 注册工具 | `ctx.register_tool()` | 注册 skill_lookup / skill_load / skill_categories |
| 注册 Hook | `ctx.register_hook()` | `on_session_start` 注入分类目录到 system prompt |
| 注册技能 | `ctx.register_skill()` | 注册 plugin 自带的分类目录技能 |
| 注册 CLI 命令 | `ctx.register_cli_command()` | `hermes vault migrate`、`hermes vault index`、`hermes vault doctor` |
| LLM 访问 | `ctx.llm` | 可选：用 LLM 辅助分类推断 |
| 消息注入 | `ctx.inject_message()` | 可选：技能加载后注入提示 |

**Plugin 清单**（`plugin.yaml`）：

```yaml
name: obsidian-skill-vault
version: 1.0.0
description: "Obsidian Vault 驱动的技能懒加载，替代全量预加载"
author: hermes-skill-lazy-obsidian-vault
kind: standalone
provides_tools:
  - skill_lookup
  - skill_load
  - skill_categories
provides_hooks:
  - on_session_start
provides_commands:
  - vault-migrate
  - vault-index
  - vault-doctor
```

**Plugin 入口**（`__init__.py`）：

```python
def register(ctx):
    # 注册 MCP 风格工具（进程内调用，不走 MCP 协议）
    ctx.register_tool("skill_lookup", skill_lookup_handler)
    ctx.register_tool("skill_load", skill_load_handler)
    ctx.register_tool("skill_categories", skill_categories_handler)

    # Hook：会话开始时注入精简分类目录
    ctx.register_hook("on_session_start", inject_category_index)

    # CLI 命令：迁移、索引、健康检查
    ctx.register_cli_command("vault-migrate", migrate_cli)
    ctx.register_cli_command("vault-index", index_cli)
    ctx.register_cli_command("vault-doctor", doctor_cli)
```

**备选方案：纯 MCP Server**

如果用户不想安装 Plugin，本项目也支持以 MCP Server 模式运行：

```yaml
# ~/.hermes/config.yaml
skills:
  include_index_in_prompt: false
mcp_servers:
  obsidian-skill-vault:
    command: "obsidian-skill-vault"
    args: ["serve", "--vault", "/path/to/vault"]
```

两者共享同一套核心代码，区别仅在入口层：
- Plugin 模式：`register(ctx)` → 进程内调用，零延迟
- MCP 模式：stdio 子进程 → MCP 协议通信，有 ~50ms 启动开销

### 3.2 技能进入 Hermes 的方式：通过 Plugin Hook，不修改 Hermes 代码

**具体流程**：

```
Plugin 注册 on_session_start Hook
         │
         ▼
Hermes 创建新会话 → 调用 invoke_hook("on_session_start")
         │
         ▼
Plugin 的 inject_category_index() 被调用
         │
         ├── 读取 config.yaml → 获取 always_load 技能列表
         ├── 从 Vault 加载这 3-5 个核心技能的完整内容
         ├── 从索引读取分类目录（~2KB）
         ├── 读取 discovery_prompt 模板
         │
         ▼
返回 {"context": "<skill_categories>...<skill_discovery>..."}
         │
         ▼
Hermes 将此 context 注入 system prompt
```

**关键点**：全程通过 Hermes 官方扩展点（Plugin API + Hooks），**不修改任何 Hermes 核心文件**。

### 3.3 独立安装：无外部依赖的分发方案

**问题**：用户机器上可能没有 Python、没有 Obsidian、没有 Node.js。

**方案：PyInstaller 单文件二进制 + pip 双通道分发**

```
分发形态：
├── obsidian-skill-vault-linux-x86_64    # 单文件二进制 (~25MB)
├── obsidian-skill-vault-macos-arm64     # 单文件二进制 (~25MB)
├── obsidian-skill-vault-macos-x86_64    # 单文件二进制 (~25MB)
├── obsidian-skill-vault-windows-x86_64.exe
└── 或者: pip install obsidian-skill-vault   # 需要 Python
```

**内置组件（不依赖外部工具）**：

| 组件 | 内置方案 | 替代的依赖 |
|------|---------|-----------|
| Obsidian 交互 | 直接读写 Markdown + YAML frontmatter（自实现） | 不需要 Obsidian 桌面端 |
| Frontmatter 解析 | 内嵌 `python-frontmatter` | - |
| 全文搜索 | SQLite FTS5（Python 内置） | Elasticsearch 等 |
| 文件监听 | 内嵌 `watchdog` | inotifywait |
| Wikilink 解析 | 自实现正则（`[[name]]` 模式） | obsidiantools |
| YAML 处理 | 内嵌 PyYAML | - |
| MCP Server | 内嵌 `mcp` SDK | - |

**不内置 Obsidian CLI 的理由**：

Obsidian **没有**官方 CLI，也没有 headless 模式。我们的操作对象是 Vault 的文件系统（Markdown + `.obsidian/` 配置），不需要 Obsidian 应用运行。自实现一个轻量 vault 操作层（`vault_ops.py`）处理：

```python
# 内置 vault 操作层 — 不依赖 Obsidian 桌面端
class VaultOps:
    def read_note(self, path) -> dict:          # 解析 frontmatter + body
    def write_note(self, path, meta, body):      # 写入 Obsidian 格式
    def resolve_wikilink(self, name) -> str:     # [[name]] → 文件路径
    def list_tags(self) -> list[str]:            # 扫描所有 tags
    def list_backlinks(self, name) -> list[str]: # 反向链接
    def reindex(self):                           # 重建 SQLite 索引
    def validate(self) -> list[str]:             # 健康检查
```

**安装流程设计**：

```bash
# 方式 1：下载二进制（无需 Python）
curl -L https://github.com/.../releases/latest/download/obsidian-skill-vault-$(uname -s)-$(uname -m) \
  -o ~/.hermes/plugins/obsidian-skill-vault/bin/obsidian-skill-vault
chmod +x ~/.hermes/plugins/obsidian-skill-vault/bin/obsidian-skill-vault

# 方式 2：pip 安装
pip install obsidian-skill-vault

# 方式 3：hermes plugin install（如果未来 Hermes 支持）
hermes plugin install obsidian-skill-vault

# 初始化
obsidian-skill-vault init --vault ~/my-skill-vault
obsidian-skill-vault migrate --source ~/.hermes/skills --vault ~/my-skill-vault
obsidian-skill-vault index --vault ~/my-skill-vault
```

**Plugin 目录结构**（安装后）：

```
~/.hermes/plugins/obsidian-skill-vault/
├── plugin.yaml              # Plugin 清单
├── __init__.py              # register(ctx) 入口
├── bin/
│   └── obsidian-skill-vault # 单文件二进制（PyInstaller 产物）
├── vault_ops.py             # Vault 操作层
├── indexer.py               # SQLite 索引管理
├── tools.py                 # skill_lookup / skill_load / skill_categories
├── hooks.py                 # on_session_start hook
├── config.py                # 配置读取
└── cli.py                   # CLI 子命令
```

**构建流程**（CI/CD）：

```yaml
# .github/workflows/build.yml
strategy:
  matrix:
    include:
      - os: ubuntu-latest
        target: linux-x86_64
      - os: macos-latest
        target: macos-arm64
      - os: windows-latest
        target: windows-x86_64
steps:
  - uses: actions/setup-python@v5
    with: { python-version: '3.11' }
  - run: pip install pyinstaller && pip install -r requirements.txt
  - run: pyinstaller --onefile --name obsidian-skill-vault src/main.py
  - uses: actions/upload-artifact@v4
    with: { path: dist/obsidian-skill-vault* }
```

## 4. 架构总览

```
┌─────────────────────────────────────────────────────────┐
│                    Hermes Agent                          │
│                                                          │
│  System Prompt (精简):                                   │
│  ┌──────────────────────────────────────┐                │
│  │ [核心技能] 3-5 个 always-load 技能   │                │
│  │ [分类目录] ~20 个分类名+描述 (~2KB)  │                │
│  │ [MCP 工具] skill_lookup, skill_load  │                │
│  └──────────────────────────────────────┘                │
│           │                        │                     │
│           ▼                        ▼                     │
│    ┌─────────────┐         ┌──────────────┐              │
│    │ 直接使用     │         │ MCP Tool Call │              │
│    │ 核心技能     │         │ skill_lookup  │              │
│    └─────────────┘         └──────┬───────┘              │
│                                   │                      │
└───────────────────────────────────┼──────────────────────┘
                                    │
                    ┌───────────────▼───────────────┐
                    │     Obsidian Vault MCP Server  │
                    │                                │
                    │  ┌──────────┐  ┌────────────┐  │
                    │  │ SQLite   │  │ Full-text  │  │
                    │  │ Embedding│  │ Search     │  │
                    │  │ Index    │  │ (FTS5)     │  │
                    │  └────┬─────┘  └─────┬──────┘  │
                    │       │              │          │
                    │       ▼              ▼          │
                    │  ┌─────────────────────────┐    │
                    │  │   Obsidian Vault         │    │
                    │  │   (技能 Markdown 文件)    │    │
                    │  └─────────────────────────┘    │
                    └────────────────────────────────┘
```

## 5. 三层设计

### 4.1 存储层：Obsidian Vault

每个 SKILL.md 变成一个 Obsidian 笔记文件，保留原始内容并添加 YAML frontmatter：

```markdown
---
name: skill-name
version: 1.0.0
categories: [coding, debugging]
tags: [python, testing, tdd]
triggers: ["写测试", "test", "TDD", "单元测试"]
embedding: [0.012, -0.034, ...]  # 预计算向量（可选）
hermes_path: software-development/testing/tdd-workflow
created: 2026-05-13
updated: 2026-05-13
---

# TDD Workflow

（原始 SKILL.md 内容）
```

**Vault 文件夹结构**（物理组织）：

```
vault/skills/
├── software-development/
│   ├── testing/
│   │   ├── tdd-workflow.md
│   │   └── test-coverage.md
│   ├── debugging/
│   │   └── systematic-debugging.md
│   └── code-review/
│       └── pr-review-checklist.md
├── research/
│   ├── web-search.md
│   └── paper-analysis.md
├── writing/
│   ├── documentation.md
│   └── translation.md
└── ...
```

**分类笔记**（`vault/_index/`）— Hub Notes，用于 Obsidian 图谱可视化：

```markdown
---
type: hub
---

# 软件开发

相关技能：
- [[tdd-workflow]]
- [[test-coverage]]
- [[systematic-debugging]]
- [[pr-review-checklist]]

子分类：
- [[testing]]
- [[debugging]]
- [[code-review]]
```

### 4.2 索引层：混合检索

**方案 A：轻量级（推荐起步方案）**
- SQLite FTS5 全文搜索
- 基于 triggers 字段的精确匹配 + 模糊匹配
- 分类目录作为路由层（始终加载到 system prompt）

**方案 B：语义检索（扩展方案）**
- 预计算每个技能描述的 embedding 向量存入 SQLite
- 运行时对用户 query 做 embedding，ANN 检索最相关的技能
- 可选使用本地模型（如 sentence-transformers）避免 API 调用

**混合策略**：
1. 首先匹配 triggers 关键词（精确路由）
2. 其次匹配分类名称（分类路由）
3. 最后 fallback 到 FTS 全文搜索或语义检索

### 4.3 接口层：MCP Server

提供以下 MCP 工具给 Hermes Agent：

#### `skill_lookup(query: str, top_k: int = 3) -> list[SkillMeta]`

根据查询返回最匹配的技能元信息（不含完整内容）：

```python
{
    "tools": [{
        "name": "skill_lookup",
        "description": "搜索技能库，返回最相关的技能列表。用于发现可用技能。",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "自然语言查询"},
                "category": {"type": "string", "description": "分类过滤"},
                "top_k": {"type": "integer", "default": 3}
            }
        }
    }]
}
```

返回值示例：
```json
[
    {
        "name": "tdd-workflow",
        "categories": ["coding", "testing"],
        "summary": "TDD 红-绿-重构工作流",
        "relevance": 0.92,
        "path": "vault/skills/software-development/testing/tdd-workflow.md"
    }
]
```

#### `skill_load(name: str) -> str`

加载指定技能的完整内容：

```python
{
    "tools": [{
        "name": "skill_load",
        "description": "加载指定技能的完整内容。先 skill_lookup 找到技能，再用此工具加载。",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "技能名称"}
            },
            "required": ["name"]
        }
    }]
}
```

#### `skill_categories() -> list[Category]`

列出所有分类及其描述（也可直接从 system prompt 的分类目录获取）：

```python
{
    "tools": [{
        "name": "skill_categories",
        "description": "列出所有技能分类及其包含的技能数量",
        "input_schema": {"type": "object", "properties": {}}
    }]
}
```

## 6. System Prompt 结构变化

### Before（全量预加载）

```
<system>
... system prompt ...
<available_skills>
  - skill-1: 描述...（200字）
  - skill-2: 描述...（200字）
  ... 2000+ 个技能 ... (~100KB)
</available_skills>
</system>
```

### After（Obsidian Lazy Loading）

```
<system>
... system prompt ...
<skill_categories>
  software-development (45): 软件开发相关技能，包括编码、测试、调试、代码审查
  research (12): 信息搜索、论文分析、数据收集
  writing (18): 文档编写、翻译、内容创作
  ops (15): 部署、监控、故障排查
  ... ~20 个分类 (~2KB)
</skill_categories>
<skill_discovery>
  可用 MCP 工具发现和加载技能：
  - skill_lookup(query): 搜索相关技能
  - skill_load(name): 加载技能完整内容
  优先根据分类定位，再调用 skill_lookup 精确查找。
</skill_discovery>
</system>
```

**体积变化**：~100KB → ~2KB（减少 98%）

## 7. 工作流程

```
用户输入 "帮我用 TDD 方式写一个 Python 函数"
    │
    ▼
Agent 匹配分类目录 → "software-development" 相关
    │
    ▼
Agent 调用 skill_lookup("TDD Python testing")
    │
    ▼
MCP Server 搜索 Vault → 命中 triggers: ["TDD", "测试"]
    │
    ▼
返回: [{"name": "tdd-workflow", "relevance": 0.95}]
    │
    ▼
Agent 调用 skill_load("tdd-workflow")
    │
    ▼
MCP Server 读取 vault/skills/software-development/testing/tdd-workflow.md
    │
    ▼
返回完整技能内容 → Agent 按 TDD Workflow 执行任务
```

## 8. 迁移策略

从现有 `~/.hermes/skills/` 迁移到 Obsidian Vault：

```
~/.hermes/skills/software-development/testing/tdd-workflow/SKILL.md
                    │
                    ▼ migrate_skills.py
vault/skills/software-development/testing/tdd-workflow.md
                    │
                    ├── 提取元信息 → frontmatter
                    ├── 保留原始内容
                    └── 生成分类 wikilink
```

迁移脚本职责：
1. 递归扫描 `~/.hermes/skills/` 下所有 `SKILL.md`
2. 提取技能名称、描述、触发词
3. 按目录结构推断分类
4. 生成 frontmatter + Obsidian 格式笔记
5. 创建 Hub Notes（`_index/`）连接同分类技能
6. 构建初始 SQLite 索引

## 9. LLM 增强方案（Hermes v0.13.0+）

### 8.1 背景

Hermes v0.13.0 新增 `ctx.llm` API，允许插件直接调用宿主的 LLM，无需自带 Provider 或 API Key：

```python
# 聊天补全
result = ctx.llm.complete(
    messages=[{"role": "user", "content": "..."}],
    max_tokens=500,
)

# 结构化推理（JSON Schema 验证）
result = ctx.llm.complete_structured(
    instructions="根据技能内容生成摘要",
    input=[{"type": "text", "text": skill_body}],
    json_schema={
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "triggers": {"type": "array", "items": {"type": "string"}},
            "category": {"type": "string"},
        },
        "required": ["summary", "triggers"],
    },
)
```

### 8.2 增强场景

| 场景 | 触发时机 | LLM 任务 | 价值 |
|------|---------|---------|------|
| **创建技能时补全元数据** | `skill_install(action="create")` | 从内容推断 `summary`、`triggers`、`category` | 减少用户手动填写，提升索引质量 |
| **编辑技能时刷新摘要** | `skill_install(action="edit")` | 比较 diff，更新过时的 summary 和 triggers | 保持索引与内容同步 |
| **索引更新时批量优化** | `on_session_start` → `update_index()` 检测到 changed skills | 为缺少 summary/triggers 的技能补全 | 修复迁移遗留的空字段 |
| **搜索结果摘要优化** | `skill_lookup()` 返回结果 | 为匹配结果生成中文+英文双语 summary | 改善搜索结果的可读性 |
| **分类推断** | 技能无 category 或 category 不明确 | 根据内容推断最合适的分类 | 优化分类体系 |

### 8.3 实现策略

#### Phase 1：创建时补全（`tools.py` 的 `_create` 方法）

```python
def _create(self, name, content, category, description, ctx_llm=None):
    meta, body, err = self._normalize_meta(content, category, description)
    if err:
        return {"success": False, "error": err}

    # 如果 frontmatter 中缺少 summary 或 triggers，尝试 LLM 补全
    if ctx_llm and (not meta.get("summary") or not meta.get("triggers")):
        enriched = self._llm_enrich_metadata(ctx_llm, body, meta)
        if enriched.get("summary"):
            meta["summary"] = enriched["summary"]
        if enriched.get("triggers"):
            meta["triggers"] = enriched["triggers"]

    # ... 继续创建逻辑
```

#### Phase 2：索引更新时批量优化（`hooks.py` 的 `on_session_start`）

```python
def _on_session_start(indexer, config, ctx_llm=None, **kwargs):
    stats = indexer.update_index(config.vault_path)

    # 为新索引的技能补全元数据（仅处理缺少 summary 的）
    if ctx_llm and stats.get("added", 0) > 0:
        skills_needing_enrichment = indexer.get_skills_missing_field("summary")
        for skill in skills_needing_enrichment[:5]:  # 每次最多处理 5 个，避免延迟
            _enrich_skill_metadata(ctx_llm, skill, indexer, config.vault_path)
```

#### Phase 3：搜索结果增强（`tools.py` 的 `skill_lookup`）

```python
def skill_lookup(self, query, category=None, top_k=3, ctx_llm=None):
    results = self.search.search(query, category=category, top_k=top_k)

    # 如果 summary 太短或为空，异步补全（不阻塞返回）
    for r in results:
        if len(r.get("summary", "")) < 20 and ctx_llm:
            # 标记为需要补全，下次 lookup 时可能已有
            pass

    return results
```

### 8.4 配置

`ctx.llm` 需要在 `~/.hermes/config.yaml` 中配置信任标志：

```yaml
plugins:
  enabled:
    - obsidian-skill-vault
  entries:
    obsidian-skill-vault:
      llm:
        allow_model_override: true
        allowed_models:
          - "*"        # 允许使用任意模型
```

插件自身的配置扩展：

```yaml
# ~/.hermes/plugins/obsidian-skill-vault/config.yaml
llm:
  enabled: true                    # 是否启用 LLM 增强（默认 false）
  enrich_on_create: true           # 创建技能时补全元数据
  enrich_on_index: true            # 索引更新时批量补全
  max_enrich_per_session: 5        # 每次会话最多补全的技能数
  model: ""                        # 指定模型（留空使用默认）
```

### 8.5 降级策略

`ctx.llm` 是可选增强，不影响核心功能：

```
ctx.llm 可用？
├── Yes → 调用 LLM 补全 summary/triggers/category
│         超时或失败 → fallback 到规则引擎（现有逻辑）
└── No  → 使用规则引擎（_extract_triggers_from_body、_collect_tags）
          现有功能不受影响
```

| 降级条件 | 行为 |
|---------|------|
| Hermes < v0.13.0 | `ctx_llm` 为 None，完全跳过 LLM 增强 |
| `llm.enabled: false` | 跳过 LLM 增强 |
| `ctx.llm` 调用超时/失败 | 记录警告，使用规则引擎结果 |
| `plugins.entries` 未配置信任 | `ctx.llm` 调用会报错，catch 后降级 |

### 8.6 与 v0.12.x 的关系

v0.12.x 完全不支持 `ctx.llm`。插件 0.1.0 在 v0.12.x 上运行时：
- `register()` 的 `ctx` 参数没有 `.llm` 属性
- 插件不会尝试访问 `ctx.llm`，所有元数据通过规则引擎生成
- 功能完整，仅缺少 LLM 辅助的智能推断

升级到 v0.13.0 后，只需在 `config.yaml` 中添加 `plugins.entries` 配置即可启用 LLM 增强，无需修改插件代码。

## 10. 与现有项目的关系

| 项目 | 借鉴点 | 本项目的差异化 |
|------|--------|---------------|
| hermes-skills-lazy-index | config flag + MCP 工具模式 | 用 Obsidian Vault 替代纯 SQLite 后端 |
| oh-my-agent-skills | Bundle 分类体系 | 分类映射到 Obsidian 文件夹 + wikilink |
| baiye-hermes-skills | Obsidian Vault 目录结构 | 从"存储输出"改为"存储技能定义" |
| Zettelkasten-Obsidian-Hermes-Skill | 笔记分类方法论 | Hub/Structure notes 作为技能索引 |

## 11. 技术选型

| 组件 | 选择 | 理由 |
|------|------|------|
| Vault 文件格式 | Markdown + YAML frontmatter | Obsidian 原生支持 |
| 索引数据库 | SQLite + FTS5 | 零依赖、高性能、嵌入式 |
| Embedding（可选） | sentence-transformers (all-MiniLM-L6-v2) | 本地运行、22MB、多语言支持 |
| MCP Server | Python + mcp-sdk | 生态成熟、与 Hermes 兼容 |
| 迁移脚本 | Python | 处理 YAML、Markdown、文件操作 |

## 12. 风险与缓解

| 风险 | 缓解措施 |
|------|---------|
| 多轮检索增加延迟 | 分类目录预加载减少检索轮次；索引驻留内存 |
| Agent 不知道何时调用 skill_lookup | 在 system prompt 中加入清晰的 skill_discovery 指引 |
| Obsidian 文件变更不同步到索引 | 文件监听（watchdog）自动重建索引 |
| 分类不准确导致漏检 | Fallback 到全文搜索；分类可手动调整 |
