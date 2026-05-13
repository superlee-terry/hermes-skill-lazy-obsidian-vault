# 系统兼容性与影响分析

本插件通过禁用 Hermes 内建的 `skills` 工具集，用 Obsidian Vault + SQLite FTS5 方案替代。本文档详细说明禁用后的影响及插件的补偿措施。

## Hermes 版本兼容性矩阵

| 功能 | v0.12.0 | v0.13.0+ | 说明 |
|------|---------|----------|------|
| `register_tool()` | ✅ | ✅ | 无变更 |
| `register_hook()` | ✅ | ✅ | 无变更 |
| `pre_llm_call` 返回 `{"context": ...}` | ✅ | ✅ | 无变更 |
| `post_tool_call` hook | ✅ | ✅ | v0.13.0 新增 `chat_id` 到 hook_ctx，不影响现有参数 |
| `on_session_start` hook | ✅ | ✅ | 无变更 |
| `disabled_toolsets: [skills]` | ✅ | ✅ | 配置方式不变 |
| `ctx.llm.complete()` | ❌ | ✅ | v0.13.0 新增，需要 `plugins.entries` 配置信任标志 |
| `ctx.llm.complete_structured()` | ❌ | ✅ | v0.13.0 新增，JSON Schema 验证 |
| `transform_llm_output` hook | ❌ | ✅ | v0.13.0 新增，可用于输出格式化 |
| `skill_utils` mtime 缓存 | ❌ | ✅ | v0.13.0 性能优化，~120 技能启动从 10s+ 降到 <1s |

**升级建议**：v0.12.0 → v0.13.0 无破坏性变更，可直接 `git pull && pip install -e .`。`ctx.llm` 为可选增强，不启用不影响现有功能。

## 禁用的工具集

在 `~/.hermes/config.yaml` 中配置：

```yaml
agent:
  disabled_toolsets:
    - skills
```

禁用的 `skills` 工具集包含 3 个内建工具：

| 原生工具 | 功能 | 禁用后影响 |
|---------|------|-----------|
| `skills_list` | 列出所有技能 + 注入 `<available_skills>` 到 system prompt | system prompt 不再包含全量技能列表（节省 ~15k chars） |
| `skill_view` | 加载单个技能完整内容 | agent 无法按需查看技能 |
| `skill_manage` | 创建/编辑/删除技能 | agent 无法在会话中管理技能 |

## 插件替代方案

### 工具替代

| 原生工具 | Plugin 替代 | 注册位置 |
|---------|------------|---------|
| `skills_list` | `skill_lookup(query, category?, top_k?)` | `skill-vault` 工具集 |
| `skills_list` | `skill_categories()` | `skill-vault` 工具集 |
| `skill_view` | `skill_load(name)` | `skill-vault` 工具集 |
| `skill_manage` | `skill_install(action, name, content?, category?)` | `skill-vault` 工具集 |

### System Prompt 替代

| 原生行为 | Plugin 替代 |
|---------|------------|
| `<available_skills>` 全量列表 (~15,324 chars) | `<skill_categories>` 分类摘要 (~500 chars) |
| 注入到 system prompt | 通过 `pre_llm_call` hook 注入到 user message context |
| 每次 API 调用都携带 | 每次 API 调用都携带 |

### Guidance 替代

| 原生行为 | Plugin 替代 |
|---------|------------|
| `SKILLS_GUIDANCE` 提示 agent 何时创建技能 | `<skill_discovery>` 中包含等效的创建/更新指引 |
| 通过 system prompt 注入 | 通过 `pre_llm_call` hook 注入 |

## 禁用后的间接影响

以下影响由 Hermes 核心代码 (`run_agent.py`) 中的硬编码逻辑产生，但**不影响正常使用**：

### 1. 技能自动复习不触发

**代码位置**: `run_agent.py:14119-14121`

Hermes 有一个自动机制：每隔一定 tool 调用次数后，触发后台 skill review fork，检查是否有需要更新或合并的技能。此逻辑通过检查 `"skill_manage" in valid_tool_names` 判断是否启用。

**影响**: 后台 review 不会自动触发。

**补偿**: 可通过 `hermes curator` CLI 手动管理技能归档和合并。

### 2. `_iters_since_skill` 计数器失效

**代码位置**: `run_agent.py:9608-9609`, `run_agent.py:10017-10018`

当 agent 调用 `skill_manage` 时重置计数器，用于追踪距离上次技能操作经过的迭代数。

**影响**: 计数器始终为 0，不影响其他逻辑。

### 3. 后台 Skill Review Fork 不运行

**代码位置**: `run_agent.py:14134`

`_should_review_skills` 永远为 `False`，不会 fork 出子进程做技能审查。

**影响**: 不会自动发现和修复过时技能。

**补偿**: `skill_install` 的 schema description 包含了"发现过时技能立即更新"的指引，由 agent 主动维护。

### 4. 背景 Prompt 中的引用

**代码位置**: `run_agent.py:3432-3454`, `run_agent.py:3503-3509`

后台 review fork 的 prompt 中引用了 `skill_view`、`skills_list`、`skill_manage`。由于 review fork 本身不触发（见 #3），这些引用无实际影响。

**影响**: 无。

## 插件的 Hook 注册

插件注册了 3 个生命周期 Hook：

| Hook | 功能 | 作用 |
|------|------|------|
| `on_session_start` | 增量索引同步 | 检测 vault 与索引的差异，自动同步新增/修改/删除 |
| `pre_llm_call` | 注入分类目录 + 技能指引 | 替代原生 `<available_skills>`，注入精简的分类索引和工具使用说明 |
| `post_tool_call` | 监听 `skill_manage` 调用 | 当原生 `skill_manage` 可用时，自动同步 vault + 索引（兜底机制） |

## 双向同步机制

### Vault → ~/.hermes/skills/（正向）

`skill_install` 工具在 vault 中创建/编辑技能时，自动将副本写入 `~/.hermes/skills/`，保持与原生技能目录的兼容。

### ~/.hermes/skills/ → Vault（反向）

当原生 `skill_manage` 工具可用时（如未来重新启用 skills 工具集），`post_tool_call` hook 会自动将变更同步到 vault 并更新索引。

### CLI/外部安装 → Vault

通过 `hermes curator install` 或直接在 `~/.hermes/skills/` 下创建的技能，在下次会话启动时由 `on_session_start` 的 `update_index()` 自动检测并同步。

## 安全性

- 插件工具注册在 `skill-vault` 工具集下，不受 `disabled_toolsets: [skills]` 影响
- 所有工具 handler 返回 JSON 字符串，符合 Hermes Plugin API 规范
- SQLite 连接使用 `check_same_thread=False` 以兼容 Hermes 网关的多线程调度
- 不修改 Hermes 核心代码，完全通过 Plugin API 实现
