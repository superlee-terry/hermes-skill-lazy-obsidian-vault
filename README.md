# Hermes Skill Lazy Obsidian Vault

将 Hermes Agent 的 SKILL.md 技能定义迁移到本地 Obsidian Vault，通过 Obsidian 的文件夹结构、标签和 wikilink 实现技能分类，配合 Hermes Plugin 实现按需加载（lazy loading），替代默认的 `<available_skills>` 全量预加载机制。

## 产物形态

**Hermes Plugin**（首选） + **MCP Server**（备选），不修改 Hermes 核心代码。

通过 Hermes 官方 Plugin API（`register(ctx)`）注册工具、Hook、CLI 命令：
- `ctx.register_tool()` → skill_lookup / skill_load / skill_categories
- `ctx.register_hook("on_session_start")` → 注入精简分类目录到 system prompt
- `ctx.register_cli_command()` → `hermes vault migrate/index/doctor`

## 安装方式

```bash
# 方式 1：下载二进制（无需 Python / Obsidian）
curl -L https://github.com/.../releases/latest/download/obsidian-skill-vault-$(uname -s)-$(uname -m) \
  -o ~/.hermes/plugins/obsidian-skill-vault/bin/obsidian-skill-vault

# 方式 2：pip 安装
pip install obsidian-skill-vault

# 初始化
obsidian-skill-vault init --vault ~/my-skill-vault
obsidian-skill-vault migrate --source ~/.hermes/skills
obsidian-skill-vault index
```

**零外部依赖**：不要求安装 Obsidian 桌面端或 Python，二进制内置 Vault 操作层、SQLite FTS5、文件监听。可直接用 Obsidian 打开 Vault 目录进行可视化管理（可选）。

## 目录结构

```
hermes-skill-lazy-obsidian-vault/
├── README.md                    # 本文件
├── docs/
│   ├── design.md                # 架构设计文档
│   └── implementation-plan.md   # 实现计划
├── vault/                       # Obsidian Vault 根目录（可用 Obsidian 打开）
│   ├── .obsidian/               # Obsidian 配置
│   ├── _index/                  # 索引笔记（Hub Notes）
│   ├── _templates/              # 技能笔记模板
│   └── skills/                  # 技能定义存放区
├── src/                         # Plugin 源码
│   ├── __init__.py              # register(ctx) 入口
│   ├── plugin.yaml              # Plugin 清单
│   ├── vault_ops.py             # Vault 读写（自实现）
│   ├── indexer.py               # SQLite FTS5 索引
│   ├── search.py                # 混合检索
│   ├── tools.py                 # skill_lookup / skill_load / skill_categories
│   ├── hooks.py                 # on_session_start hook
│   ├── cli.py                   # CLI 子命令
│   ├── migrate.py               # 迁移逻辑
│   └── main.py                  # MCP Server 入口（备选）
├── scripts/                     # 构建/发布脚本
│   └── build.sh                 # PyInstaller 构建
└── config.yaml                  # 项目配置
```
