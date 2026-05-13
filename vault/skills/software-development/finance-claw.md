---
categories:
- software-development
description: 'Finance Claw project: financial data collection, archival, and AI analysis
  workflow. Includes data source fetching, news archiving with deduplication, Obsidian
  vault integration, sentiment analysis, and config-driven architecture for extensibility.

  '
name: finance-claw
summary: 'Finance Claw project: financial data collection, archival, and AI analysis
  workflow. Includes data source fetching, news archiving with deduplication, Obsidian
  vault integration, sentiment analysis, a'
tags:
- finance
- archival
- obsidian
- ai-analysis
- data-collection
triggers:
- finance
- archival
- obsidian
- ai-analysis
- data-collection
---

# Finance Claw — Financial Data Collection & Analysis

## Overview

Finance Claw is a system for collecting financial data (news, announcements),
archiving with deduplication, and performing AI-powered sentiment analysis.
Data is stored in an Obsidian vault for searchability and AI reference.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Data Sources   │────▶│  Archiver        │────▶│  Obsidian Vault │
│  (Sina, etc.)   │     │  (Dedup, Tag)    │     │  (Storage)      │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │  AI Analysis     │
                       │  (Sentiment)     │
                       └──────────────────┘
```

## Subsystems

### 1. Config-Driven Module Loading

**See also:** `references/config-driven-architecture.md`

The project uses config-driven architecture for dynamic module loading:
- `importlib.import_module()` + `getattr()` for runtime discovery
- Configuration entries define `fetcher_module` and `fetcher_function`
- `SourceRegistry` class manages loaded modules

### 2. Archival with Deduplication

**See also:** `references/archival-dedup-pattern.md`

Core archival pattern:
- URL deduplication via `.collected_urls.json` (supports new nested format and legacy flat format)
- Per-article metadata tagging (publication date, source, collection timestamp)
- Incremental collection (only new content)
- Storage in `{stock_dir}/正文/` subdirectory

### 3. Obsidian Vault Operations

**See also:** `references/obsidian-operations.md`

Vault structure:
```
Obsidian Vault/
├── Finance/
│   ├── <code>-<name>/
│   │   ├── .collected_urls.json
│   │   ├── 新闻列表-<code>-<date>.md
│   │   ├── 公告列表-<code>-<date>.md
│   │   ├── 正文索引-<code>-<date>.md
│   │   ├── 正文/
│   │   └── AI分析报告-<code>-<date>.md
```

**Critical pitfalls:**
- **Permission propagation**: All parent directories need 0o755, not just leaf
- **JSON format compatibility**: Support both `{"urls": {...}}` and flat `{"url": "ts"}` formats
- **No official CLI**: Obsidian has no official CLI; use Python file ops or rg for search
- **Field name mapping**: archiver expects `analysis_summary` but note_writer uses `analysis`

### 4. Sentiment Analysis

**See also:** `references/sentiment-analysis.md`

LLM-powered sentiment scoring:
- Prompt maps to -1 (bearish), 0 (neutral), 1 (bullish)
- Batch analysis for multiple headlines
- Combined with technical analysis for comprehensive reports
- Pitfall: short headlines often return neutral — consider adding article content

## Environment

- **Python**: 3.11 isolated venv at `/mnt/data/finance_claw_workspace/venv/`
- **Vault path**: `/mnt/data/Obsidian/Default/` (per user preference)
- **Config**: `src/config.py` with `OBSIDIAN_VAULT_PATH`, `OBSIDIAN_ARCHIVE_ENABLED`, etc.

## Support Files

- `references/config-driven-architecture.md` — Config-driven module loading guide (extends software-development skill)
- `references/archival-dedup-pattern.md` — Web archival with deduplication (extends web-archival-dedup skill)
- `references/obsidian-operations.md` — Obsidian file operations (extends obsidian-filesystem-operations skill)
- `references/sentiment-analysis.md` — Sentiment analysis patterns (extends finance-news-analysis skill)
- `templates/collection-metadata.json` — Collection metadata file template (from web-archival-dedup)
- `templates/article-header.md` — Article metadata header template (from web-archival-dedup)