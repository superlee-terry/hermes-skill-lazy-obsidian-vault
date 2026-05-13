# 实现计划（v2 — Plugin 架构）

## Phase 0：项目骨架（0.5 天）

### 0.1 Hermes Plugin 结构
- [ ] 创建 `plugin.yaml`
- [ ] 创建 `__init__.py`（`register(ctx)` 入口）
- [ ] 创建 `config.py`（读取 vault 路径、索引模式等配置）
- [ ] 验证 Plugin 可被 Hermes 加载（`hermes plugins list`）

### 0.2 项目目录结构
```
src/
├── __init__.py          # register(ctx)
├── plugin.yaml          # Plugin 清单
├── config.py            # 配置管理
├── vault_ops.py         # Obsidian Vault 读写（自实现，无外部依赖）
├── indexer.py           # SQLite + FTS5 索引管理
├── search.py            # 混合检索（trigger → category → FTS）
├── tools.py             # skill_lookup / skill_load / skill_categories
├── hooks.py             # on_session_start → 注入分类目录
├── cli.py               # CLI 子命令（migrate/index/doctor/serve）
├── migrate.py           # 技能迁移逻辑
├── models.py            # 数据模型（Skill, Category 等）
└── main.py              # MCP Server 入口（备选模式）
```

## Phase 1：核心模块（2-3 天）

### 1.1 vault_ops.py — Vault 操作层（无 Obsidian 依赖）
- [ ] `read_note(path)` — 解析 YAML frontmatter + markdown body
- [ ] `write_note(path, meta, body)` — 写入 Obsidian 兼容格式
- [ ] `resolve_wikilink(name)` — `[[name]]` → 文件路径解析
- [ ] `list_tags()` — 扫描所有笔记的 tags 字段
- [ ] `list_backlinks(name)` — 反向链接查找
- [ ] `scan_skills(vault_path)` — 递归扫描 vault/skills/ 下所有 .md
- 依赖：仅 `pyyaml` + `python-frontmatter`（纯 Python，可 PyInstaller 打包）

### 1.2 indexer.py — SQLite 索引
- [ ] `build_index(vault_path, db_path)` — 全量构建
- [ ] `update_index(vault_path, db_path)` — 增量更新（mtime 比对）
- [ ] SQLite schema：
  ```sql
  CREATE TABLE skills (
    name TEXT PRIMARY KEY,
    path TEXT NOT NULL,
    categories TEXT,  -- JSON array
    tags TEXT,        -- JSON array
    triggers TEXT,    -- JSON array
    summary TEXT,
    mtime REAL
  );
  CREATE VIRTUAL TABLE skills_fts USING fts5(
    name, summary, triggers, content=skills
  );
  ```
- [ ] watchdog 文件监听 → 自动触发 `update_index`

### 1.3 search.py — 混合检索
- [ ] `search(query, category=None, top_k=3)` → 三路检索：
  1. Trigger 精确匹配（权重 0.5）
  2. Category 过滤（权重 0.3）
  3. FTS5 全文搜索 BM25（权重 0.2）
- [ ] 结果合并、去重、排序

## Phase 2：Plugin 接口层（1-2 天）

### 2.1 tools.py — 注册到 Hermes 的工具
- [ ] `skill_lookup(query, category, top_k)` → 调用 search.py → 返回元信息列表
- [ ] `skill_load(name)` → 调用 vault_ops.read_note() → 返回完整内容
- [ ] `skill_categories()` → 读取索引 → 返回分类列表+技能数

### 2.2 hooks.py — 会话启动 Hook
- [ ] `inject_category_index(session)` → on_session_start 回调
  - 读取 always_load 技能列表 → 加载核心技能
  - 读取分类目录（~2KB）
  - 组装 `<skill_categories>` + `<skill_discovery>` 文本
  - 返回 `{"context": "..."}` 注入 system prompt

### 2.3 cli.py — CLI 子命令
- [ ] `hermes vault migrate --source ~/.hermes/skills --vault ~/my-vault`
  - 扫描源目录所有 SKILL.md
  - 提取元信息、推断分类
  - 写入 Vault 格式笔记
  - 生成 Hub Notes
- [ ] `hermes vault index --vault ~/my-vault`
  - 触发全量/增量索引构建
- [ ] `hermes vault doctor --vault ~/my-vault`
  - 检查孤立笔记、断裂 wikilink、缺失 frontmatter
- [ ] `hermes vault serve --vault ~/my-vault`
  - 以 MCP Server 模式运行（备选方案入口）

## Phase 3：打包与分发（1 天）

### 3.1 PyInstaller 打包
- [ ] 编写 `pyinstaller.spec`
  - hidden imports：yaml, frontmatter, watchdog, sqlite3
  - exclude：tkinter, test, doc
  - 输出单文件二进制
- [ ] 本地测试：`dist/obsidian-skill-vault vault doctor --vault ...`

### 3.2 CI/CD（GitHub Actions）
- [ ] matrix 构建：linux-x86_64 / macos-arm64 / macos-x86_64 / windows-x86_64
- [ ] 自动发布到 GitHub Releases
- [ ] 同时发布到 PyPI（pip install obsidian-skill-vault）

### 3.3 安装脚本
- [ ] `install.sh` — 下载二进制 + 部署到 `~/.hermes/plugins/obsidian-skill-vault/`
- [ ] `install.ps1` — Windows 版本

## Phase 4：测试与优化（1-2 天）

### 4.1 功能测试
- [ ] 迁移 100+ 技能到 Vault，验证完整性
- [ ] skill_lookup 召回率测试（对比全量预加载场景）
- [ ] skill_load 延迟测试（< 100ms 目标）
- [ ] Hook 注入测试（system prompt 包含分类目录）

### 4.2 集成测试
- [ ] Hermes Plugin 加载测试
- [ ] 端到端：用户提问 → 分类匹配 → skill_lookup → skill_load → 执行
- [ ] MCP Server 模式备选测试

### 4.3 性能测试
- [ ] 1000 技能 / 5000 技能 / 10000 技能索引构建时间
- [ ] 检索延迟 vs 技能数量关系
- [ ] System prompt 体积对比（全量 vs lazy）

## 依赖

```
# requirements.txt（全部纯 Python，可 PyInstaller 打包）
pyyaml>=6.0
python-frontmatter>=1.0.0
watchdog>=3.0.0
mcp>=0.9.0           # 仅 MCP Server 模式需要
```

无 C 扩展依赖，PyInstaller 可在所有平台直接打包。
