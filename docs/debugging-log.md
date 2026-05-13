# 调试记录

本文档记录 obsidian-skill-vault 插件在 Hermes 环境中集成、调试过程中遇到的所有问题及解决方案。

---

## 1. python-frontmatter 缺失

### 现象

```
ModuleNotFoundError: No module named 'frontmatter'
```

插件加载时报错，Hermes 进程无法启动插件。

### 原因

Hermes 的 Python venv (`~/.hermes/hermes-agent/venv/`) 中未安装 `python-frontmatter` 包。插件的 `vault_ops.py` 和 `migrate.py` 依赖此包解析 SKILL.md 的 YAML frontmatter。

### 解决

```bash
~/.hermes/hermes-agent/venv/bin/pip3 install python-frontmatter
```

### 教训

Hermes 插件运行在 Hermes 自己的 venv 中，插件的依赖必须安装到该 venv。 Hermes 不会自动安装插件依赖。建议在插件安装文档中明确列出依赖安装步骤。

---

## 2. SQLite 线程安全错误

### 现象

```
sqlite3.ProgrammingError: SQLite objects created in a thread can only be used in that same thread.
```

插件在 skill_lookup 等工具调用时崩溃。

### 原因

插件在 `register(ctx)` 阶段（主线程）创建 `SkillIndexer` 实例并建立 SQLite 连接。但 Hermes 网关通过线程池分发工具调用，工具 handler 在不同线程中执行。Python 的 `sqlite3` 默认禁止跨线程使用同一连接（`check_same_thread=True`）。

### 解决

在 `indexer.py` 中修改连接参数：

```python
# 修改前
self.conn = sqlite3.connect(db_path)

# 修改后
self.conn = sqlite3.connect(db_path, check_same_thread=False)
```

### 影响

此设置在高并发下理论上存在风险（SQLite 写锁竞争），但插件的工具 handler 都是读操作（lookup/load/categories），只有 `skill_install` 和 sync 有写操作且不频繁，实际使用没有问题。

---

## 3. on_session_start 返回值被丢弃

### 现象

在 `on_session_start` hook 中返回 `{"context": "..."}` 期望注入到上下文，但实际上下文中没有出现技能分类索引。

### 原因

Hermes 的 `invoke_hook("on_session_start", ...)` 会收集返回值，但 `run_agent.py` 中的调用方不使用这些返回值。只有 `pre_llm_call` hook 的返回值会被检查——如果返回 `{"context": "..."}`，内容会被注入到当前轮次的 user message 中。

### 解决

将上下文注入从 `on_session_start` 移到 `pre_llm_call`：

```python
# on_session_start 只做初始化（日志、缓存预热）
def _on_session_start(**kwargs):
    logger.info("session started (id=%s)", kwargs.get("session_id"))

# pre_llm_call 负责注入上下文
def _on_pre_llm_call(**kwargs):
    context_text = build_session_context(config.vault_path, indexer, ...)
    return {"context": context_text}
```

### 设计考量

选择 `pre_llm_call` 而非 `on_session_start` 注入上下文有两个好处：
1. 这是 Hermes 唯一支持动态上下文注入的 hook
2. 每次 LLM 调用前都会触发，确保索引变更（如新增技能）能立即反映

---

## 4. 插件与项目源码的 Import 路径差异

### 现象

```
ImportError: No module named 'hermes_plugins.obsidian_skill_vault.config'
```

或

```
ModuleNotFoundError: No module named 'config'
```

### 原因

项目源码和安装后的插件有不同的包结构，导致 `__init__.py` 的 import 路径不同。

**项目源码结构**（`src/` 是顶级包，`__init__.py` 在 `src/` 中）：

```
src/
├── __init__.py      ← from .config import ...
├── config.py
├── tools.py
└── ...
config.yaml          ← Path(__file__).parent.parent / "config.yaml"
```

**插件安装结构**（`__init__.py` 在插件根目录，源码在 `src/` 子目录）：

```
~/.hermes/plugins/obsidian-skill-vault/
├── __init__.py      ← from .src.config import ...
├── config.yaml      ← Path(__file__).parent / "config.yaml"
├── src/
│   ├── config.py
│   ├── tools.py
│   └── ...
```

关键差异：

| 差异点 | 项目源码 | 插件 |
|--------|---------|------|
| Import | `from .config import VaultConfig` | `from .src.config import VaultConfig` |
| Config 路径 | `Path(__file__).parent.parent / "config.yaml"` | `Path(__file__).parent / "config.yaml"` |

### 解决

维护两套 `__init__.py`：
- 项目源码 `/src/__init__.py` 使用 `.xxx` import 和 `.parent.parent`
- 插件 `__init__.py` 使用 `.src.xxx` import 和 `.parent`

**禁止**用 `cp` 直接将项目 `src/__init__.py` 覆盖插件 `__init__.py`。

### 事故记录

在一次更新中，用 `cp /mnt/data/.../src/__init__.py ~/.hermes/plugins/.../__init__.py` 直接复制，导致插件 import 路径和 config 路径全部错误，gateway 日志报 `Failed to load plugin`。需要手动修正 import 和 config 路径后重启 gateway 才恢复。

---

## 5. LLM 优先使用原生 skills_list 而非 Plugin 工具

### 现象

禁用 skills 前，agent 面对技能相关问题时调用原生 `skills_list` 而不是 plugin 的 `skill_lookup`。即使在 `pre_llm_call` 中注入了 `<skill_categories>` 和工具使用指引，LLM 仍然优先使用原生工具。

### 原因

Hermes 原生 skills 系统通过两层机制确保 LLM 优先使用原生工具：

1. **System Prompt 注入**: `build_skills_system_prompt()` 生成 `<available_skills>` 标签（~15,324 chars），包含完整的技能列表和使用指引。此内容注入到 system prompt 中，LLM 将其视为系统级指令。

2. **强指令措辞**: 原生 system prompt 中包含 "MUST load it with skill_view()" 等强制性措辞，优先级高于 plugin 在 user message context 中注入的建议。

由于 system prompt 优先级高于 user message context，LLM 倾向于遵循 system prompt 中的原生工具指令。

### 解决

在 `~/.hermes/config.yaml` 中禁用整个 `skills` 工具集：

```yaml
agent:
  disabled_toolsets:
    - skills
```

这同时移除了：
- `skills_list`、`skill_view`、`skill_manage` 三个工具的 schema
- `<available_skills>` 的注入
- `SKILLS_GUIDANCE` 提示

Plugin 的工具注册在 `skill-vault` 工具集下，不受此禁用影响。

### 副作用处理

禁用后需要用 plugin 工具完全替代原生功能（详见 `docs/compatibility.md`）。

---

## 6. 新安装技能不同步到 Vault

### 现象

通过 `skill_manage` 安装的新技能写入 `~/.hermes/skills/`，但 plugin 的 vault（`~/.hermes/plugins/obsidian-skill-vault/vault/`）中没有同步，`skill_lookup` 搜不到新技能。

### 原因

Plugin 的 vault 和 Hermes 原生的 `~/.hermes/skills/` 是两个独立的存储位置，没有自动同步机制。`skill_manage` 只写入原生目录，不通知 plugin。

### 解决

实现三层同步机制：

1. **`post_tool_call` hook** — 监听 `skill_manage` 的 create/edit/patch/delete 调用，自动触发 vault 同步 + 索引更新（`src/sync.py`）
2. **`on_session_start` 索引同步** — 每次 session 启动时运行 `indexer.update_index()`，捕获 CLI 或外部安装的技能
3. **`skill_install` 双向同步** — plugin 的 `skill_install` 工具写入 vault 时，同时写入 `~/.hermes/skills/` 保持兼容

### 当前状态

由于 `skills` 工具集已禁用，`post_tool_call` 监听 `skill_manage` 的 hook 暂时不会触发（`skill_manage` 不可用）。但 `on_session_start` 的索引同步确保了 CLI 安装和手动创建的技能在下次会话时被发现。

---

## 7. Hub Notes 生成与 _index 目录

### 现象

迁移后 `vault/_index/` 目录生成了按分类聚合的 Hub Notes，但后续同步操作可能没有正确更新这些文件。

### 原因

Hub Notes 由 `_generate_hub_notes()` 函数在迁移时和每次 sync/remove 操作后调用。该函数扫描 vault 中所有技能的分类元数据，生成 `_<category>.md` 索引文件。

### 解决

确保 `sync_skill_to_vault()` 和 `remove_skill_from_vault()` 在完成 vault 操作后都调用 `_generate_hub_notes(vault_path)`。

---

## 8. hermes gateway restart 行为不一致

### 现象

执行 `hermes gateway restart` 后，有时 gateway 正常重启，有时 gateway 停止后不再启动。

### 原因

`hermes gateway restart` 的行为取决于当前 gateway 的运行方式：
- 如果 gateway 是通过 systemd/launchd 管理的，restart 会正常重启
- 如果 gateway 是通过 `nohup` 后台运行的，restart 可能只停止旧进程，不会自动拉起新进程

### 解决

当 restart 后 gateway 未启动时，手动启动：

```bash
cd ~/.hermes/hermes-agent && source venv/bin/activate
nohup hermes gateway run --replace > /tmp/hermes-gw.log 2>&1 & disown
```

---

## 9. Hermes Plugin Context 接口

### 背景

调试过程中需要理解 Hermes 的 PluginContext 接口。以下是经过验证的接口定义：

```python
ctx.register_tool(
    name="tool_name",        # 工具名，全局唯一
    toolset="toolset-name",  # 工具集名，决定是否受 disabled_toolsets 影响
    schema={...},            # OpenAI function-calling 格式的 schema
    handler=func,            # handler(args: dict, **kwargs) -> str，返回 JSON 字符串
    check_fn=func,           # check_fn() -> bool，返回 False 时工具不注册
    emoji="🔍",             # 显示用 emoji
)

ctx.register_hook(
    "hook_name",             # 生命周期事件名
    callback=func,           # callback(**kwargs) -> Optional[Any]
)
```

### 已验证的 Hook

| Hook | 参数 | 返回值处理 |
|------|------|-----------|
| `on_session_start` | `session_id` | 返回值**被丢弃** |
| `pre_llm_call` | (无特定参数) | 返回 `{"context": "..."}` 注入到 user message |
| `post_tool_call` | `tool_name, args, result, task_id, session_id, tool_call_id, duration_ms` | 返回值被忽略 |

### 工具 Handler 签名

```python
def handler(args: dict, **kwargs) -> str:
    # args 是 LLM 生成的参数（JSON 已解析为 dict）
    # 必须返回 JSON 字符串
    return json.dumps({"success": True, ...}, ensure_ascii=False)
```

---

## 环境信息

| 项目 | 值 |
|------|-----|
| Hermes 版本 | hermes-agent (Python 3.11) |
| 运行模式 | Gateway (feishu + weixin) |
| 插件框架 | Hermes PluginContext API |
| 数据库 | SQLite 3 + FTS5 |
| OS | Linux 6.8.0-111-generic |
| 调试日期 | 2026-05-14 |
