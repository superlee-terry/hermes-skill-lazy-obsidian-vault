---
categories:
- finance-claw-workspace
created: 2026-05-08
description: Finance Claw workspace - financial data collection, AI analysis, and
  Obsidian archiving for Chinese A-share stocks
name: finance-claw-workspace
related_skills:
- finance-news-analysis
- finance-claw-archiver
- finance-claw-obsidian
summary: Finance Claw workspace - financial data collection, AI analysis, and Obsidian
  archiving for Chinese A-share stocks
triggers: []
updated: 2026-05-09
version: 3.0
---

# Finance Claw Workspace - 财经数据采集与分析系统

## 项目概述

Finance Claw是一个集成新浪财经数据、本地AI分析、Obsidian存储的财经系统。

## 快速启动

```bash
cd /mnt/data/finance_claw_workspace
source venv/bin/activate
```

## 核心功能

### 1. 数据采集

```python
from src.obsidian.archiver import archiver

# 归档新浪数据（新闻+公告+正文）
archiver.archive_sina_data_v2({
    'code': '600745',
    'name': '闻泰科技',
    'date': '2026-05-08'
})
```

### 2. 股票分析

```python
from src.ai.analyst import analyst

# AI技术分析
result = analyst.analyze(
    code='600745',
    name='闻泰科技',
    max_tokens=32768
)
print(analyst.format_result(result))
```

### 3. 意图路由

```python
from src.router.intent import handle_query

# 自然语言查询
result = handle_query('分析600745闻泰科技走势 后期操作建议')
```

## 文件结构

```
finance_claw_workspace/
├── src/
│   ├── ai/analyst.py          # AI分析器
│   ├── analyzer/indicators.py # 技术指标
│   ├── fetcher/
│   │   ├── kline.py           # K线数据
│   │   ├── market.py          # 行情数据
│   │   ├── news.py            # 新闻采集
│   │   └── sina_source.py     # 新浪财经
│   ├── obsidian/
│   │   ├── archiver.py        # 归档入口
│   │   ├── obsidian_cli.py    # CLI封装
│   │   ├── vault.py           # 目录管理
│   │   └── stock_folder.py    # 股票文件夹
│   └── router/intent.py       # 意图路由
├── config/                    # 配置文件
└── venv/                      # 虚拟环境
```

## Obsidian存储结构

```
Vault/Finance/股票代码-股票名/
├── .collected_urls.json       # 采集记录（用于重复检测）
├── 新闻列表-股票代码-日期.md
├── 公告列表-股票代码-日期.md
├── 正文索引-股票代码-日期.md
├── AI分析报告-股票代码-日期.md
└── 正文/
    ├── 01-文章标题.md
    ├── 02-文章标题.md
    └── ...
```

## 关键配置

```python
# config.py 关键配置
OBSIDIAN_VAULT_PATH = "/mnt/data/Obsidian/Default/"
OLLAMA_BASE_URL = "http://127.0.0.1:11434"
OLLAMA_MODEL = "qwen3.6"
OLLAMA_MAX_TOKENS = 32768
```

### Ollama API端点（重要）

**工作端点**：`v1/chat/completions`（OpenAI兼容格式）
- 端点URL：`http://127.0.0.1:11434/v1/chat/completions`
- 使用方式：`requests.post(url, json={"model": "qwen3.6", "messages": [...]})`

**不推荐使用**：`/api/generate` 端点（可能返回unknown path错误）

### 部署架构说明

当前环境使用Docker容器代理架构：
- `llama-lb`（nginx）→ `llama-gpu0`/`llama-gpu1`（llama.cpp容器）
- 所有API调用通过 `127.0.0.1:11434` 统一访问
- 模型存储在GPU容器的 `/models` 目录

### akshare安装

akshare未预装在Hermes venv中，使用前需安装：
```bash
# 在Hermes venv中安装
/root/.hermes/hermes-agent/venv/bin/pip install akshare
```

## 权限注意事项

Obsidian CLI需要正确的文件权限：
- 目录权限：0755
- 文件权限：0644
- 所有者：superlee

## 重复采集检测

系统自动跟踪已采集的URL，存储在`.collected_urls.json`中。
检测逻辑：
1. 加载已有记录
2. 对比新采集的URL
3. 跳过已存在的URL
4. 保存新的URL记录

## 完整正确流程（2026-05-09更新）

### 标准操作流程

```
1. 清理旧的URL记录（避免重复检测干扰）
   rm -f /Vault/Finance/股票代码-股票名/.collected_urls.json

2. 修复目录权限
   chown -R superlee:superlee /Vault/Finance/股票代码-股票名/
   chmod -R 755 /Vault/Finance/股票代码-股票名/

3. 执行数据采集
   archiver.archive_sina_data_v2({
       'code': '002060',
       'name': '广东建工',
       'date': '2026-05-08'
   })
   
   此步骤会自动完成：
   - 采集新闻列表（多数据源）
   - 采集公告列表
   - 采集10篇新闻正文（独立页面）
   - 创建正文索引
   - 保存URL采集记录
   - 创建正文目录

4. 验证文件创建
   ls -la /Vault/Finance/股票代码-股票名/正文/
   # 应看到10个.md文件

5. 执行AI分析
   analyst.analyze(code, name, max_tokens=32768)

6. 保存AI分析结果
   写入 /Vault/Finance/股票代码-股票名/AI分析-股票代码-日期.md
```

### 权限注意事项（关键）

**obsidian-cli的"创建成功"可能是假象**：
1. 如果目录所有者是root，obsidian-cli会报告成功但实际无法写入
2. **必须**在运行archiver之前修复权限
3. **必须**用`ls`验证正文目录中有文件

**权限修复命令**：
```bash
# 修复整个股票目录
chown -R superlee:superlee /Vault/Finance/股票代码-股票名/
chmod -R 755 /Vault/Finance/股票代码-股票名/

# 如果正文目录不存在，先创建
mkdir -p /Vault/Finance/股票代码-股票名/正文
chown -R superlee:superlee /Vault/Finance/股票代码-股票名/正文
chmod -R 755 /Vault/Finance/股票代码-股票名/正文
```

### 常见陷阱和修复

#### 1. archiver.py变量名bug
**症状**：`NameError: name 'news' is not defined`
**位置**：`src/obsidian/archiver.py` 第407行
**修复**：
```bash
cd /mnt/data/finance_claw_workspace
sed -i 's/if news:/if all_news:/g' src/obsidian/archiver.py
sed -i 's/for idx, item in enumerate(news\[:10\]/for idx, item in enumerate(all_news[:10]/g' src/obsidian/archiver.py
```

#### 2. Ollama端点错误
**症状**：调用失败或返回unknown path
**正确端点**：`http://127.0.0.1:11434/v1/chat/completions`
**注意**：使用OpenAI兼容格式，不是`/api/generate`

#### 3. Docker容器架构
**环境**：`llama-lb`（nginx代理）→ `llama-gpu0/llama-gpu1`
**访问**：统一通过 `127.0.0.1:11434`
**模型**：qwen3.6（34.66B参数，21GB GGUF）

#### 4. URL重复检测
**机制**：`.collected_urls.json` 存储已采集URL
**首次运行**：会采集所有10篇正文
**后续运行**：跳过已采集内容
**强制重新采集**：删除 `.collected_urls.json`

#### 5. akshare数据源
**使用场景**：Sina/Eastmoney API受限时的备选
**安装**：`/root/.hermes/hermes-agent/venv/bin/pip install akshare`

### 验证清单

运行完成后检查：
- [ ] 新闻列表文件存在（约5KB）
- [ ] 公告列表文件存在（约3KB）
- [ ] 正文索引文件存在（约5KB）
- [ ] 正文目录存在且有10个.md文件
- [ ] 所有文件所有者为superlee
- [ ] 正文目录权限为755
- [ ] AI分析文件存在（约5KB）

### 数据源配置

```python
# config.py
NEWS_SOURCES = {
    'sina_news': {
        'enabled': True,
        'type': 'news',
        'name': '新浪财经-新闻',
        'limit': 30
    },
    'sina_bulletin': {
        'enabled': True,
        'type': 'bulletin',
        'name': '新浪公告',
        'limit': 20
    },
    'eastmoney': {
        'enabled': True,
        'type': 'news',
        'name': '东方财富',
        'limit': 10
    },
    'cls': {
        'enabled': True,
        'type': 'news',
        'name': '财联社',
        'limit': 30
    },
    'cninfo': {
        'enabled': False,
        'type': 'bulletin',
        'name': '巨潮资讯',
        'limit': 20
    }
}
```

#### 股票分析标准流程（用户要求）

**触发条件**：用户提出"分析股票"、"走势分析"、"操作策略"等相关问题

**执行步骤**：
1. **获取K线数据**：使用akshare获取最近3年K线走势
   ```bash
   akshare.stock_zh_a_hist(symbol="股票代码", period="daily", start_date="20230101", end_date="当前日期", adjust="qfq")
   ```

2. **获取资讯和公告**：通过archiver归档到Obsidian
   ```bash
   archiver.archive_sina_data_v2({
       'code': '股票代码',
       'name': '股票名称',
       'date': '日期'
   })
   ```
   此步骤自动完成：
   - 通过Obsidian CLI写入新闻列表、公告列表
   - 采集10篇新闻正文到正文目录
   - 创建正文索引
   - 保存URL采集记录

3. **AI分析并写入Obsidian**：整合K线数据、资讯、公司公告等内容
   ```python
   from src.ai.analyst import analyst
   result = analyst.analyze(code, name, max_tokens=32768)
   # 将分析结果写入 /Vault/Finance/股票代码-股票名/AI分析-股票代码-日期.md
   ```

4. **输出总结结论**：将AI分析结果以结构化格式输出给用户

**注意事项**：
- 必须先加载finance-claw-workspace技能
- 不可简化步骤，必须按标准流程执行
- 分析前必须检查并修复目录权限
- archiver.py第407行有bug，运行前须修复

- 首次运行会下载所有数据，后续运行会自动跳过已采集内容
- AI分析需要Ollama服务正常运行，使用 `v1/chat/completions` 端点
- 正文采集限制10篇，避免过多网络请求
- **obsidian-cli显示"创建成功"但文件可能未真正创建（权限问题），必须用ls验证**
- archiver.py第407行有变量名bug（`news`→`all_news`），运行前须修复
- **每次运行archiver前必须检查并修复目录权限**
- 强制重新采集正文时需删除 `.collected_urls.json`

## 相关技能

### 核心技能（已整合）

- **finance-claw-workspace** - 主技能，包含完整工作流
- **finance-news-analysis** - LLM驱动的财经新闻情感分析和AI解读
- **finance-claw-archiver** - 财经新闻/公告归档，智能去重和元数据标记
- **finance-claw-obsidian** - Finance Claw Obsidian集成标准和陷阱

### 已迁移/删除的技能

以下技能的功能已整合到上述核心技能中，不再单独存在：

- ~~finance-claw-stock-data-sources~~ - 功能已整合到finance-claw-workspace
- ~~china-stock-data-sources~~ - 功能已整合到finance-claw-workspace
- ~~china-stock-realtime-data~~ - 功能已整合到finance-claw-workspace
- ~~obsidian-integration~~ - 功能已整合到finance-claw-obsidian

### 通用技能

- **obsidian-filesystem-operations** - 通用Obsidian文件系统操作（文件创建、读取、编辑）
- **obsidian** - 通用Obsidian笔记读写和搜索