# 安装指南

## 前置条件

- Hermes Agent 已安装并运行（网关模式或 CLI 模式），**v0.12.0+**
- Python 3.10+
- `python-frontmatter` 包（Hermes venv 中需要安装）

> **版本说明**：插件 0.1.0 适用于 Hermes v0.12.x，提供完整的技能搜索/加载/管理功能。
> Hermes v0.13.0+ 额外提供 `ctx.llm` 能力（可选），用于 LLM 辅助技能增强。
> 详见 [compatibility.md](compatibility.md)。

## 安装方式

### 方式一：手动安装

#### 1. 获取插件代码

```bash
# 克隆仓库
git clone https://github.com/superlee-terry/hermes-skill-lazy-obsidian-vault.git /tmp/obsidian-skill-vault

# 创建插件目录
mkdir -p ~/.hermes/plugins/obsidian-skill-vault
```

#### 2. 复制插件文件

```bash
# 复制源码到插件目录（注意目录结构）
cp -r /tmp/obsidian-skill-vault/src/* ~/.hermes/plugins/obsidian-skill-vault/
cp /tmp/obsidian-skill-vault/src/plugin.yaml ~/.hermes/plugins/obsidian-skill-vault/
cp /tmp/obsidian-skill-vault/src/__init__.py ~/.hermes/plugins/obsidian-skill-vault/
cp /tmp/obsidian-skill-lazy-obsidian-vault/config.yaml ~/.hermes/plugins/obsidian-skill-vault/
```

安装后的目录结构：

```
~/.hermes/plugins/obsidian-skill-vault/
├── __init__.py          # Plugin 入口 (register, hooks, handlers)
├── plugin.yaml          # Plugin 清单
├── config.yaml          # 插件配置
├── src/
│   ├── config.py        # 配置解析
│   ├── models.py        # 数据模型
│   ├── vault_ops.py     # Vault 读写
│   ├── indexer.py       # SQLite FTS5 索引
│   ├── search.py        # 混合检索
│   ├── tools.py         # 工具实现 (lookup/load/categories/install)
│   ├── hooks.py         # Hook 实现 (session_start/pre_llm/post_tool)
│   ├── sync.py          # 增量同步
│   └── migrate.py       # 技能迁移
├── vault/               # Obsidian Vault (运行时生成)
│   ├── skills/          # 技能笔记
│   └── _index/          # Hub Notes
└── skill_index.db       # SQLite 索引 (运行时生成)
```

#### 3. 安装 Python 依赖

```bash
# 在 Hermes 的 venv 中安装 frontmatter
~/.hermes/hermes-agent/venv/bin/pip3 install python-frontmatter
```

### 方式二：通过对话指令安装

在 Hermes 对话中发送以下指令（需要 agent 有 `terminal` 工具权限）：

```
请帮我安装 obsidian-skill-vault 插件：
1. git clone https://github.com/superlee-terry/hermes-skill-lazy-obsidian-vault.git /tmp/obsidian-skill-vault
2. mkdir -p ~/.hermes/plugins/obsidian-skill-vault/src
3. 复制 src/ 下所有 .py 文件到 ~/.hermes/plugins/obsidian-skill-vault/src/
4. 复制 plugin.yaml、__init__.py 到 ~/.hermes/plugins/obsidian-skill-vault/
5. 复制 config.yaml 到 ~/.hermes/plugins/obsidian-skill-vault/
6. pip install python-frontmatter 到 hermes venv
7. 执行技能迁移（见下方"迁移技能"章节）
8. 修改配置（见下方"配置 Hermes"章节）
9. 重启网关
```

## 迁移技能

安装完成后，需要将 Hermes 原有的技能迁移到 Vault 中：

```bash
cd ~/.hermes/hermes-agent
source venv/bin/activate

# 执行迁移（从 ~/.hermes/skills/ 导入到 vault）
python3 -c "
import sys
sys.path.insert(0, '/tmp/obsidian-skill-vault')
from src.migrate import migrate_skills, build_index
stats = migrate_skills(
    source_dir='$HOME/.hermes/skills',
    vault_dir='$HOME/.hermes/plugins/obsidian-skill-vault/vault'
)
print(f'Migrated: {stats}')

# 构建索引
from src.indexer import SkillIndexer
idx = SkillIndexer('$HOME/.hermes/plugins/obsidian-skill-vault/skill_index.db')
count = idx.build_index_from_vault('$HOME/.hermes/plugins/obsidian-skill-vault/vault')
print(f'Indexed: {count} skills')
idx.close()
"
```

## 配置 Hermes

### 1. 启用插件 + 禁用原生 skills 工具集

编辑 `~/.hermes/config.yaml`，修改以下两处：

```yaml
# 在 agent 段添加 disabled_toolsets
agent:
  disabled_toolsets:
    - skills

# 在 plugins 段添加插件
plugins:
  enabled:
    - obsidian-skill-vault
```

**注意**：`disabled_toolsets: [skills]` 会禁用内建的 `skills_list`、`skill_view`、`skill_manage` 三个工具。插件提供的 `skill_lookup`、`skill_load`、`skill_categories`、`skill_install` 注册在 `skill-vault` 工具集下，不受此配置影响。

### 2. 插件配置（可选）

编辑 `~/.hermes/plugins/obsidian-skill-vault/config.yaml`：

```yaml
vault:
  path: vault          # Vault 相对路径（相对于插件目录）
  db_path: skill_index.db  # SQLite FTS5 索引路径

hermes:
  always_load: []       # 始终注入完整内容的技能名列表
  include_category_index: true
  discovery_prompt: ""  # 自定义发现提示（留空使用默认模板）
  llm:                  # LLM 增强（Hermes v0.13.0+，v0.12.x 自动跳过）
    enabled: true           # 总开关
    enrich_on_create: true  # 创建技能时用 LLM 补全 summary/triggers
    enrich_on_edit: true    # 编辑技能时用 LLM 刷新元数据
    enrich_on_index: true   # 会话启动时批量补全缺元数据的技能
    max_enrich_per_session: 5  # 每次会话最多补全技能数
    timeout_seconds: 5.0       # 单次 LLM 调用超时（秒）
```

如需启用 `ctx.llm`（Hermes v0.13.0+），还需在 `~/.hermes/config.yaml` 中配置信任标志：

```yaml
plugins:
  enabled:
    - obsidian-skill-vault
  entries:
    obsidian-skill-vault:
      llm: {}             # 空 block 即可启用，无需覆盖模型
```

不配置此条目时，`ctx.llm` 调用会失败，插件自动降级到规则引擎，不影响核心功能。

### 3. 重启网关

```bash
cd ~/.hermes/hermes-agent
source venv/bin/activate
hermes gateway restart
```

或手动重启：

```bash
hermes gateway run --replace
```

## 验证安装

### 检查插件加载

查看日志确认插件注册成功：

```bash
grep "obsidian-skill-vault" ~/.hermes/logs/agent.log | tail -5
```

应看到：

```
INFO hermes_plugins.obsidian_skill_vault: obsidian-skill-vault plugin registered (vault=vault)
```

### 测试工具调用

在 Hermes 对话中发送：

```
帮我搜索一下跟"PowerPoint"相关的技能
```

如果 agent 调用了 `skill_lookup` 工具并返回结果，说明插件工作正常。

### 检查上下文优化效果

对比禁用 skills 前后的 system prompt 大小：

| 指标 | 禁用前 | 禁用后 | 节省 |
|------|--------|--------|------|
| `<available_skills>` 长度 | ~15,324 chars | 0 chars | 100% |
| `<skill_categories>` 长度 | - | ~500 chars | - |
| **Net 节省** | | | **~14,800 chars** |

## 注意事项

### 1. 插件目录与项目源码的差异

插件的 `__init__.py` 和项目源码的 `src/__init__.py` 存在两个关键差异，**不能直接用 `cp` 覆盖**：

| 差异点 | 项目源码 (`src/__init__.py`) | 插件 (`__init__.py`) |
|--------|---------------------------|---------------------|
| Import 路径 | `from .config import ...` | `from .src.config import ...` |
| Config 路径 | `Path(__file__).parent.parent / "config.yaml"` | `Path(__file__).parent / "config.yaml"` |

如果从项目源码更新插件，修改 `__init__.py` 后需手动修正这两处。

### 2. 新安装的技能同步

安装插件后，新技能可以通过以下方式添加：

- **通过 agent 对话**：agent 会调用 `skill_install` 创建技能，自动同步到 vault + 索引
- **通过 CLI**：`hermes curator install` 安装的技能，下次会话启动时由 `on_session_start` hook 自动同步
- **手动复制**：直接将 SKILL.md 放到 `~/.hermes/skills/` 下，下次会话启动时自动同步

### 3. 重新启用原生 skills 工具集

如果需要恢复原生 skills 工具，只需从 `config.yaml` 中移除 `disabled_toolsets` 中的 `skills`：

```yaml
agent:
  disabled_toolsets: []  # 或直接删除此配置
```

此时原生 `skills_list`/`skill_view`/`skill_manage` 和插件的 `skill_lookup`/`skill_load`/`skill_install` 会同时可用。插件的 `post_tool_call` hook 会自动同步原生 `skill_manage` 的变更到 vault。

### 4. SQLite 线程安全

插件使用 `check_same_thread=False` 连接 SQLite。这是 Hermes 网关多线程调度工具 handler 的必要设置。在正常并发量下不会出现问题。

### 5. Vault 数据不在 Git 中

`vault/skills/` 和 `vault/_index/` 已在 `.gitignore` 中排除。技能数据是用户特定的，不应提交到公开仓库。每个部署环境需要独立执行技能迁移。

### 6. LLM 增强的降级行为

LLM 增强是可选功能，不启用不影响核心技能搜索/加载/管理：

| 条件 | 行为 |
|------|------|
| Hermes v0.12.x | `ctx.llm` 不存在，LLM 增强完全跳过 |
| `llm.enabled: false` | 所有 LLM 调用跳过，使用规则引擎 |
| `plugins.entries` 未配置 | `ctx.llm` 调用失败，自动降级 |
| LLM 超时/报错 | 首次失败后禁用当前会话的 LLM 增强 |
