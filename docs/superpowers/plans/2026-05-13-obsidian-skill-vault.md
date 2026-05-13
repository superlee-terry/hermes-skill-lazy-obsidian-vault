# Obsidian Skill Vault Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Hermes Plugin that stores skill definitions in an Obsidian Vault and loads them on-demand via SQLite FTS5 search, replacing the default eager-loading of all skills into system prompt.

**Architecture:** Hermes Plugin (standalone kind) registers 3 tools (skill_lookup, skill_load, skill_categories) and 1 hook (on_session_start). Skills live as Markdown+YAML frontmatter files in an Obsidian Vault. A SQLite FTS5 index enables hybrid search (trigger → category → full-text). A vault_ops layer reads/writes vault files without requiring Obsidian desktop.

**Tech Stack:** Python 3.11+, pyyaml, python-frontmatter, SQLite FTS5, Hermes Plugin API

---

## File Structure

```
/mnt/data/hermes-skill-lazy-obsidian-vault/
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── src/
│   ├── __init__.py          # Plugin entry: register(ctx)
│   ├── plugin.yaml          # Hermes plugin manifest
│   ├── config.py            # Config loading
│   ├── models.py            # Skill, Category dataclasses
│   ├── vault_ops.py         # Vault read/write (no Obsidian dep)
│   ├── indexer.py           # SQLite FTS5 index build/query
│   ├── search.py            # Hybrid search orchestration
│   ├── tools.py             # Hermes tool handlers
│   ├── hooks.py             # on_session_start hook
│   ├── migrate.py           # ~/.hermes/skills/ → vault migration
│   ├── cli.py               # CLI subcommands
│   └── main.py              # MCP Server entry (backup mode)
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Shared fixtures (tmp vault, sample skills)
│   ├── test_models.py
│   ├── test_vault_ops.py
│   ├── test_indexer.py
│   ├── test_search.py
│   ├── test_migrate.py
│   └── test_hooks.py
├── vault/
│   ├── .obsidian/
│   ├── _index/
│   │   └── README.md
│   ├── _templates/
│   │   └── skill-template.md
│   └── skills/              # Sample data goes here
└── docs/
    └── ...
```

---

### Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `requirements.txt`
- Create: `requirements-dev.txt`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[project]
name = "obsidian-skill-vault"
version = "0.1.0"
description = "Hermes Plugin: Obsidian Vault-driven skill lazy loading"
requires-python = ">=3.11"
dependencies = [
    "pyyaml>=6.0",
    "python-frontmatter>=1.0.0",
]

[project.optional-dependencies]
mcp = ["mcp>=0.9.0"]
dev = ["pytest>=7.0", "pytest-tmp-files>=0.0.2"]

[project.scripts]
obsidian-skill-vault = "src.main:main"

[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"
```

- [ ] **Step 2: Create requirements files**

`requirements.txt`:
```
pyyaml>=6.0
python-frontmatter>=1.0.0
```

`requirements-dev.txt`:
```
-r requirements.txt
pytest>=7.0
```

- [ ] **Step 3: Create tests/__init__.py** (empty file)

- [ ] **Step 4: Create tests/conftest.py with shared fixtures**

```python
import os
import json
import shutil
import pytest
from pathlib import Path


@pytest.fixture
def tmp_vault(tmp_path):
    """Create a temporary Obsidian vault with .obsidian dir."""
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / ".obsidian").mkdir()
    (vault / "skills").mkdir()
    (vault / "_index").mkdir()
    return vault


@pytest.fixture
def sample_skills(tmp_vault):
    """Create 5 sample skill files in the temp vault."""
    skills_dir = tmp_vault / "skills"
    skills = [
        {
            "name": "tdd-workflow",
            "dir": "software-development/testing",
            "meta": {
                "name": "tdd-workflow",
                "categories": ["software-development", "testing"],
                "tags": ["python", "testing", "tdd"],
                "triggers": ["TDD", "测试驱动", "test driven", "红绿重构"],
                "summary": "TDD 红-绿-重构工作流",
            },
            "content": "# TDD Workflow\n\n## 步骤\n1. 写一个失败的测试（红）\n2. 写最少的代码让测试通过（绿）\n3. 重构代码",
        },
        {
            "name": "systematic-debugging",
            "dir": "software-development/debugging",
            "meta": {
                "name": "systematic-debugging",
                "categories": ["software-development", "debugging"],
                "tags": ["debug", "troubleshooting", "bug"],
                "triggers": ["调试", "debug", "bug", "报错", "错误"],
                "summary": "系统性调试方法论",
            },
            "content": "# Systematic Debugging\n\n## 步骤\n1. 复现问题\n2. 缩小范围\n3. 形成假设\n4. 验证假设\n5. 修复并验证",
        },
        {
            "name": "code-review-checklist",
            "dir": "software-development/code-review",
            "meta": {
                "name": "code-review-checklist",
                "categories": ["software-development", "code-review"],
                "tags": ["review", "quality", "pr"],
                "triggers": ["代码审查", "code review", "PR review", "pull request"],
                "summary": "代码审查清单",
            },
            "content": "# Code Review Checklist\n\n- [ ] 逻辑正确性\n- [ ] 错误处理\n- [ ] 性能影响\n- [ ] 安全性\n- [ ] 可读性",
        },
        {
            "name": "web-search",
            "dir": "research",
            "meta": {
                "name": "web-search",
                "categories": ["research", "information-gathering"],
                "tags": ["search", "web", "internet"],
                "triggers": ["搜索", "search", "查找资料", "网上搜索"],
                "summary": "网络搜索与信息收集",
            },
            "content": "# Web Search\n\n使用搜索工具收集信息，验证事实，查找参考资料。",
        },
        {
            "name": "documentation-writing",
            "dir": "writing",
            "meta": {
                "name": "documentation-writing",
                "categories": ["writing", "documentation"],
                "tags": ["docs", "writing", "readme"],
                "triggers": ["写文档", "documentation", "README", "文档"],
                "summary": "技术文档编写规范",
            },
            "content": "# Documentation Writing\n\n## 原则\n- 简洁明了\n- 代码示例优先\n- 结构化章节",
        },
    ]
    for skill in skills:
        skill_path = skills_dir / skill["dir"] / f"{skill['name']}.md"
        skill_path.parent.mkdir(parents=True, exist_ok=True)
        # Write frontmatter + content manually
        fm_lines = ["---"]
        for k, v in skill["meta"].items():
            if isinstance(v, list):
                fm_lines.append(f"{k}:")
                for item in v:
                    fm_lines.append(f"  - \"{item}\"")
            elif isinstance(v, str) and any(c in v for c in " -:,#{}[]|>&*?!%'@\""):
                fm_lines.append(f'{k}: "{v}"')
            else:
                fm_lines.append(f"{k}: {v}")
        fm_lines.append("---")
        full_content = "\n".join(fm_lines) + "\n\n" + skill["content"]
        skill_path.write_text(full_content, encoding="utf-8")
    return skills
```

- [ ] **Step 5: Install dependencies and verify**

Run: `cd /mnt/data/hermes-skill-lazy-obsidian-vault && pip install -r requirements-dev.txt`
Expected: Successfully installed

- [ ] **Step 6: Commit**

```bash
git init
git add pyproject.toml requirements.txt requirements-dev.txt tests/
git commit -m "chore: project scaffolding with test fixtures"
```

---

### Task 2: Data Models

**Files:**
- Create: `src/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write the test**

```python
# tests/test_models.py
from src.models import Skill, Category


def test_skill_creation():
    skill = Skill(
        name="tdd-workflow",
        path="skills/software-development/testing/tdd-workflow.md",
        categories=["software-development", "testing"],
        tags=["python", "tdd"],
        triggers=["TDD", "测试驱动"],
        summary="TDD 红-绿-重构工作流",
        content="# TDD Workflow\n\n步骤...",
    )
    assert skill.name == "tdd-workflow"
    assert len(skill.categories) == 2
    assert skill.triggers == ["TDD", "测试驱动"]


def test_skill_defaults():
    skill = Skill(name="minimal", path="skills/minimal.md")
    assert skill.categories == []
    assert skill.tags == []
    assert skill.triggers == []
    assert skill.summary == ""
    assert skill.content == ""


def test_category_creation():
    cat = Category(name="software-development", description="软件开发", skill_count=15)
    assert cat.name == "software-development"
    assert cat.skill_count == 15


def test_category_defaults():
    cat = Category(name="test")
    assert cat.description == ""
    assert cat.skill_count == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /mnt/data/hermes-skill-lazy-obsidian-vault && python -m pytest tests/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src'`

- [ ] **Step 3: Write implementation**

```python
# src/models.py
from dataclasses import dataclass, field


@dataclass
class Skill:
    name: str
    path: str
    categories: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    triggers: list[str] = field(default_factory=list)
    summary: str = ""
    content: str = ""


@dataclass
class Category:
    name: str
    description: str = ""
    skill_count: int = 0
```

Also create minimal `src/__init__.py` (empty file) so the package is importable.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /mnt/data/hermes-skill-lazy-obsidian-vault && PYTHONPATH=. python -m pytest tests/test_models.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/__init__.py src/models.py tests/test_models.py
git commit -m "feat: add Skill and Category data models"
```

---

### Task 3: Vault Operations

**Files:**
- Create: `src/vault_ops.py`
- Create: `tests/test_vault_ops.py`

- [ ] **Step 1: Write the test**

```python
# tests/test_vault_ops.py
import pytest
from src.vault_ops import VaultOps
from src.models import Skill


class TestReadNote:
    def test_read_note_with_frontmatter(self, tmp_vault, sample_skills):
        ops = VaultOps(str(tmp_vault))
        note = ops.read_note("skills/software-development/testing/tdd-workflow.md")
        assert note["metadata"]["name"] == "tdd-workflow"
        assert "TDD Workflow" in note["content"]
        assert note["metadata"]["categories"] is not None

    def test_read_note_not_found(self, tmp_vault):
        ops = VaultOps(str(tmp_vault))
        with pytest.raises(FileNotFoundError):
            ops.read_note("skills/nonexistent.md")


class TestWriteNote:
    def test_write_and_read_roundtrip(self, tmp_vault):
        ops = VaultOps(str(tmp_vault))
        meta = {
            "name": "new-skill",
            "categories": ["test"],
            "tags": ["example"],
            "triggers": ["新技能"],
            "summary": "测试技能",
        }
        content = "# New Skill\n\n测试内容"
        ops.write_note("skills/test/new-skill.md", meta, content)

        result = ops.read_note("skills/test/new-skill.md")
        assert result["metadata"]["name"] == "new-skill"
        assert "New Skill" in result["content"]

    def test_write_creates_parent_dirs(self, tmp_vault):
        ops = VaultOps(str(tmp_vault))
        ops.write_note("skills/a/b/c/deep.md", {"name": "deep"}, "# Deep")
        result = ops.read_note("skills/a/b/c/deep.md")
        assert result["metadata"]["name"] == "deep"


class TestScanSkills:
    def test_scan_finds_all_skills(self, tmp_vault, sample_skills):
        ops = VaultOps(str(tmp_vault))
        skills = ops.scan_skills()
        assert len(skills) == 5
        names = {s.name for s in skills}
        assert "tdd-workflow" in names
        assert "web-search" in names

    def test_scan_empty_vault(self, tmp_vault):
        ops = VaultOps(str(tmp_vault))
        skills = ops.scan_skills()
        assert skills == []

    def test_scan_skill_has_content(self, tmp_vault, sample_skills):
        ops = VaultOps(str(tmp_vault))
        skills = ops.scan_skills()
        tdd = next(s for s in skills if s.name == "tdd-workflow")
        assert "TDD Workflow" in tdd.content
        assert tdd.categories == ["software-development", "testing"]
        assert "TDD" in tdd.triggers


class TestResolveWikilink:
    def test_resolve_existing(self, tmp_vault, sample_skills):
        ops = VaultOps(str(tmp_vault))
        path = ops.resolve_wikilink("tdd-workflow")
        assert path is not None
        assert "tdd-workflow.md" in path

    def test_resolve_nonexistent(self, tmp_vault):
        ops = VaultOps(str(tmp_vault))
        assert ops.resolve_wikilink("nonexistent") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /mnt/data/hermes-skill-lazy-obsidian-vault && PYTHONPATH=. python -m pytest tests/test_vault_ops.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.vault_ops'`

- [ ] **Step 3: Write implementation**

```python
# src/vault_ops.py
import frontmatter
from pathlib import Path
from .models import Skill


class VaultOps:
    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        self.skills_dir = self.vault_path / "skills"

    def read_note(self, path: str) -> dict:
        full_path = self.vault_path / path
        if not full_path.exists():
            raise FileNotFoundError(f"Note not found: {path}")
        with open(full_path, "r", encoding="utf-8") as f:
            post = frontmatter.load(f)
        return {"metadata": post.metadata, "content": post.content}

    def write_note(self, path: str, metadata: dict, content: str) -> None:
        full_path = self.vault_path / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        post = frontmatter.Post(content, **metadata)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(frontmatter.dumps(post))

    def scan_skills(self) -> list[Skill]:
        skills = []
        if not self.skills_dir.exists():
            return skills
        for md_file in sorted(self.skills_dir.rglob("*.md")):
            rel_path = str(md_file.relative_to(self.vault_path))
            with open(md_file, "r", encoding="utf-8") as f:
                post = frontmatter.load(f)
            meta = post.metadata
            skills.append(Skill(
                name=meta.get("name", md_file.stem),
                path=rel_path,
                categories=meta.get("categories", []),
                tags=meta.get("tags", []),
                triggers=meta.get("triggers", []),
                summary=meta.get("summary", ""),
                content=post.content,
            ))
        return skills

    def resolve_wikilink(self, name: str) -> str | None:
        if not self.vault_path.exists():
            return None
        for md_file in self.vault_path.rglob("*.md"):
            if md_file.stem == name:
                return str(md_file.relative_to(self.vault_path))
        return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /mnt/data/hermes-skill-lazy-obsidian-vault && PYTHONPATH=. python -m pytest tests/test_vault_ops.py -v`
Expected: 9 passed

- [ ] **Step 5: Commit**

```bash
git add src/vault_ops.py tests/test_vault_ops.py
git commit -m "feat: add VaultOps for Obsidian vault read/write"
```

---

### Task 4: SQLite Indexer

**Files:**
- Create: `src/indexer.py`
- Create: `tests/test_indexer.py`

- [ ] **Step 1: Write the test**

```python
# tests/test_indexer.py
import json
import pytest
from src.indexer import SkillIndexer
from src.vault_ops import VaultOps
from src.models import Skill


@pytest.fixture
def indexer(tmp_path):
    db_path = str(tmp_path / "test_index.db")
    idx = SkillIndexer(db_path)
    yield idx
    idx.close()


@pytest.fixture
def indexed_vault(tmp_vault, sample_skills, indexer):
    ops = VaultOps(str(tmp_vault))
    skills = ops.scan_skills()
    indexer.build_index(skills)
    return indexer


class TestBuildIndex:
    def test_build_indexes_all_skills(self, tmp_vault, sample_skills, indexer):
        ops = VaultOps(str(tmp_vault))
        skills = ops.scan_skills()
        count = indexer.build_index(skills)
        assert count == 5

    def test_build_index_empty(self, tmp_vault, indexer):
        ops = VaultOps(str(tmp_vault))
        skills = ops.scan_skills()
        count = indexer.build_index(skills)
        assert count == 0

    def test_rebuild_replaces_old_data(self, tmp_vault, sample_skills, indexer):
        ops = VaultOps(str(tmp_vault))
        skills = ops.scan_skills()
        indexer.build_index(skills)
        # Rebuild with only first 2
        indexer.build_index(skills[:2])
        rows = indexer.conn.execute("SELECT COUNT(*) FROM skills").fetchone()
        assert rows[0] == 2


class TestQueryIndex:
    def test_get_skill_by_name(self, indexed_vault):
        skill = indexed_vault.get_skill("tdd-workflow")
        assert skill is not None
        assert skill["name"] == "tdd-workflow"
        assert "software-development" in json.loads(skill["categories"])

    def test_get_nonexistent_skill(self, indexed_vault):
        skill = indexed_vault.get_skill("nonexistent")
        assert skill is None

    def test_list_categories(self, indexed_vault):
        cats = indexed_vault.list_categories()
        cat_names = [c["name"] for c in cats]
        assert "software-development" in cat_names
        assert "research" in cat_names
        assert "writing" in cat_names

    def test_category_skill_counts(self, indexed_vault):
        cats = indexed_vault.list_categories()
        sw = next(c for c in cats if c["name"] == "software-development")
        assert sw["skill_count"] == 3  # tdd, debugging, code-review
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /mnt/data/hermes-skill-lazy-obsidian-vault && PYTHONPATH=. python -m pytest tests/test_indexer.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

```python
# src/indexer.py
import json
import sqlite3
from pathlib import Path
from .models import Skill


class SkillIndexer:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self._init_schema()

    def _init_schema(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS skills (
                name TEXT PRIMARY KEY,
                path TEXT NOT NULL,
                categories TEXT DEFAULT '[]',
                tags TEXT DEFAULT '[]',
                triggers TEXT DEFAULT '[]',
                summary TEXT DEFAULT ''
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS skills_fts USING fts5(
                name, summary, triggers,
                content='skills', content_rowid='rowid'
            );

            CREATE TRIGGER IF NOT EXISTS skills_ai AFTER INSERT ON skills BEGIN
                INSERT INTO skills_fts(rowid, name, summary, triggers)
                VALUES (new.rowid, new.name, new.summary, new.triggers);
            END;

            CREATE TRIGGER IF NOT EXISTS skills_ad AFTER DELETE ON skills BEGIN
                INSERT INTO skills_fts(skills_fts, rowid, name, summary, triggers)
                VALUES('delete', old.rowid, old.name, old.summary, old.triggers);
            END;

            CREATE TRIGGER IF NOT EXISTS skills_au AFTER UPDATE ON skills BEGIN
                INSERT INTO skills_fts(skills_fts, rowid, name, summary, triggers)
                VALUES('delete', old.rowid, old.name, old.summary, old.triggers);
                INSERT INTO skills_fts(rowid, name, summary, triggers)
                VALUES (new.rowid, new.name, new.summary, new.triggers);
            END;
        """)
        self.conn.commit()

    def build_index(self, skills: list[Skill]) -> int:
        self.conn.execute("DELETE FROM skills")
        self.conn.commit()
        count = 0
        for skill in skills:
            self.conn.execute(
                "INSERT INTO skills (name, path, categories, tags, triggers, summary) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (skill.name, skill.path,
                 json.dumps(skill.categories), json.dumps(skill.tags),
                 json.dumps(skill.triggers), skill.summary),
            )
            count += 1
        self.conn.commit()
        return count

    def get_skill(self, name: str) -> dict | None:
        row = self.conn.execute(
            "SELECT name, path, categories, tags, triggers, summary FROM skills WHERE name = ?",
            (name,),
        ).fetchone()
        if row is None:
            return None
        return {
            "name": row[0], "path": row[1],
            "categories": row[2], "tags": row[3],
            "triggers": row[4], "summary": row[5],
        }

    def list_categories(self) -> list[dict]:
        rows = self.conn.execute("SELECT categories FROM skills").fetchall()
        cat_counts: dict[str, int] = {}
        for (cats_json,) in rows:
            for cat in json.loads(cats_json):
                cat_counts[cat] = cat_counts.get(cat, 0) + 1
        return [{"name": k, "skill_count": v} for k, v in sorted(cat_counts.items())]

    def close(self):
        self.conn.close()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /mnt/data/hermes-skill-lazy-obsidian-vault && PYTHONPATH=. python -m pytest tests/test_indexer.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add src/indexer.py tests/test_indexer.py
git commit -m "feat: add SkillIndexer with SQLite FTS5"
```

---

### Task 5: Hybrid Search

**Files:**
- Create: `src/search.py`
- Create: `tests/test_search.py`

- [ ] **Step 1: Write the test**

```python
# tests/test_search.py
import pytest
from src.search import SkillSearch
from src.indexer import SkillIndexer
from src.vault_ops import VaultOps


@pytest.fixture
def search_engine(tmp_vault, sample_skills, tmp_path):
    ops = VaultOps(str(tmp_vault))
    skills = ops.scan_skills()
    indexer = SkillIndexer(str(tmp_path / "search_test.db"))
    indexer.build_index(skills)
    engine = SkillSearch(indexer)
    yield engine
    indexer.close()


class TestTriggerMatch:
    def test_finds_tdd_by_trigger(self, search_engine):
        results = search_engine.search("TDD")
        assert len(results) > 0
        assert results[0]["name"] == "tdd-workflow"
        assert results[0]["match_type"] == "trigger"

    def test_finds_debug_by_chinese_trigger(self, search_engine):
        results = search_engine.search("调试")
        assert len(results) > 0
        assert results[0]["name"] == "systematic-debugging"


class TestCategoryFilter:
    def test_filter_by_category(self, search_engine):
        results = search_engine.search("技能", category="research")
        assert len(results) > 0
        assert all("research" in r["categories"] for r in results)

    def test_category_filter_narrows_results(self, search_engine):
        all_results = search_engine.search("技能", top_k=10)
        filtered = search_engine.search("技能", category="writing", top_k=10)
        assert len(filtered) <= len(all_results)


class TestFTSFallback:
    def test_fts_finds_by_content_keyword(self, search_engine):
        results = search_engine.search("重构")
        names = [r["name"] for r in results]
        assert "tdd-workflow" in names

    def test_fts_finds_by_name(self, search_engine):
        results = search_engine.search("web")
        names = [r["name"] for r in results]
        assert "web-search" in names


class TestTopK:
    def test_respects_top_k(self, search_engine):
        results = search_engine.search("技能", top_k=2)
        assert len(results) <= 2

    def test_default_top_k_is_3(self, search_engine):
        results = search_engine.search("技能")
        assert len(results) <= 3


class TestNoResults:
    def test_no_match_returns_empty(self, search_engine):
        results = search_engine.search("xyzzy_not_a_real_thing_12345")
        assert results == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /mnt/data/hermes-skill-lazy-obsidian-vault && PYTHONPATH=. python -m pytest tests/test_search.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

```python
# src/search.py
import json
from .indexer import SkillIndexer


class SkillSearch:
    def __init__(self, indexer: SkillIndexer):
        self.indexer = indexer

    def search(self, query: str, category: str = None, top_k: int = 3) -> list[dict]:
        seen: dict[str, dict] = {}

        # 1. Trigger exact match (weight 0.5)
        rows = self.indexer.conn.execute(
            "SELECT name, path, categories, summary FROM skills WHERE triggers LIKE ?",
            (f'%"{query}"%',),
        ).fetchall()
        for row in rows:
            seen[row[0]] = {
                "name": row[0], "path": row[1],
                "categories": json.loads(row[2]),
                "summary": row[3],
                "score": 0.5, "match_type": "trigger",
            }

        # 2. Category filter (weight 0.3)
        if category:
            rows = self.indexer.conn.execute(
                "SELECT name, path, categories, summary FROM skills WHERE categories LIKE ?",
                (f'%"{category}"%',),
            ).fetchall()
            for row in rows:
                if row[0] not in seen:
                    seen[row[0]] = {
                        "name": row[0], "path": row[1],
                        "categories": json.loads(row[2]),
                        "summary": row[3],
                        "score": 0.3, "match_type": "category",
                    }

        # 3. FTS full-text search (weight based on rank)
        try:
            fts_query = query.replace('"', '""')
            rows = self.indexer.conn.execute(
                "SELECT s.name, s.path, s.categories, s.summary, f.rank "
                "FROM skills_fts f JOIN skills s ON f.rowid = s.rowid "
                "WHERE skills_fts MATCH ? ORDER BY f.rank LIMIT ?",
                (fts_query, top_k),
            ).fetchall()
            for row in rows:
                if row[0] not in seen:
                    seen[row[0]] = {
                        "name": row[0], "path": row[1],
                        "categories": json.loads(row[2]),
                        "summary": row[3],
                        "score": round(0.2 - row[4], 3),  # rank is negative
                        "match_type": "fts",
                    }
        except Exception:
            pass  # FTS query syntax error is non-fatal

        results = sorted(seen.values(), key=lambda x: x["score"], reverse=True)
        return results[:top_k]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /mnt/data/hermes-skill-lazy-obsidian-vault && PYTHONPATH=. python -m pytest tests/test_search.py -v`
Expected: 9 passed

- [ ] **Step 5: Commit**

```bash
git add src/search.py tests/test_search.py
git commit -m "feat: add hybrid search (trigger → category → FTS)"
```

---

### Task 6: Migration Tool

**Files:**
- Create: `src/migrate.py`
- Create: `tests/test_migrate.py`

- [ ] **Step 1: Write the test**

```python
# tests/test_migrate.py
import pytest
from pathlib import Path
from src.migrate import migrate_skills
from src.vault_ops import VaultOps


@pytest.fixture
def hermes_skills_dir(tmp_path):
    """Simulate ~/.hermes/skills/ structure."""
    skills = tmp_path / "hermes_skills"
    # Skill 1: nested with SKILL.md
    s1 = skills / "software-development" / "testing" / "my-tdd" / "SKILL.md"
    s1.parent.mkdir(parents=True)
    s1.write_text(
        "---\nname: my-tdd\ncategories: [testing]\ntriggers: ['TDD']\nsummary: TDD skill\n---\n\n# My TDD",
        encoding="utf-8",
    )
    # Skill 2: another category
    s2 = skills / "research" / "search" / "SKILL.md"
    s2.parent.mkdir(parents=True)
    s2.write_text(
        "---\nname: search-skill\ncategories: [research]\ntriggers: ['搜索']\nsummary: Search skill\n---\n\n# Search",
        encoding="utf-8",
    )
    return skills


class TestMigrate:
    def test_migrate_creates_vault_files(self, tmp_path, hermes_skills_dir, tmp_vault):
        count = migrate_skills(str(hermes_skills_dir), str(tmp_vault))
        assert count == 2
        ops = VaultOps(str(tmp_vault))
        skills = ops.scan_skills()
        names = {s.name for s in skills}
        assert "my-tdd" in names
        assert "search-skill" in names

    def test_migrate_preserves_content(self, tmp_path, hermes_skills_dir, tmp_vault):
        migrate_skills(str(hermes_skills_dir), str(tmp_vault))
        ops = VaultOps(str(tmp_vault))
        skill = next(s for s in ops.scan_skills() if s.name == "my-tdd")
        assert "My TDD" in skill.content
        assert "TDD" in skill.triggers

    def test_migrate_preserves_directory_structure(self, tmp_path, hermes_skills_dir, tmp_vault):
        migrate_skills(str(hermes_skills_dir), str(tmp_vault))
        tdd_path = tmp_vault / "skills" / "software-development" / "testing" / "my-tdd.md"
        assert tdd_path.exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /mnt/data/hermes-skill-lazy-obsidian-vault && PYTHONPATH=. python -m pytest tests/test_migrate.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

```python
# src/migrate.py
import frontmatter
from pathlib import Path
from .vault_ops import VaultOps


def migrate_skills(source_dir: str, vault_path: str) -> int:
    """Migrate SKILL.md files from Hermes skills dir to Obsidian Vault."""
    source = Path(source_dir)
    ops = VaultOps(vault_path)
    count = 0

    for skill_md in sorted(source.rglob("SKILL.md")):
        with open(skill_md, "r", encoding="utf-8") as f:
            post = frontmatter.load(f)

        meta = dict(post.metadata)
        if "name" not in meta:
            meta["name"] = skill_md.parent.stem

        # Build target path: preserve directory structure, rename SKILL.md → <name>.md
        rel_parent = skill_md.parent.relative_to(source)
        target_path = f"skills/{rel_parent / meta['name']}.md"

        ops.write_note(target_path, meta, post.content)
        count += 1

    return count
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /mnt/data/hermes-skill-lazy-obsidian-vault && PYTHONPATH=. python -m pytest tests/test_migrate.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/migrate.py tests/test_migrate.py
git commit -m "feat: add migrate_skills for Hermes → Vault migration"
```

---

### Task 7: Configuration

**Files:**
- Create: `src/config.py`

- [ ] **Step 1: Write implementation** (simple config loader, no separate test needed)

```python
# src/config.py
import yaml
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class VaultConfig:
    vault_path: str = ""
    db_path: str = "skill_index.db"
    always_load: list[str] = field(default_factory=list)
    include_category_index: bool = True
    discovery_prompt: str = ""

    @classmethod
    def from_file(cls, path: str) -> "VaultConfig":
        p = Path(path)
        if not p.exists():
            return cls()
        with open(p, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        vault_cfg = data.get("vault", {})
        hermes_cfg = data.get("hermes", {})
        return cls(
            vault_path=vault_cfg.get("path", ""),
            db_path=vault_cfg.get("db_path", "skill_index.db"),
            always_load=hermes_cfg.get("always_load", []),
            include_category_index=hermes_cfg.get("include_category_index", True),
            discovery_prompt=hermes_cfg.get("discovery_prompt", ""),
        )
```

- [ ] **Step 2: Commit**

```bash
git add src/config.py
git commit -m "feat: add VaultConfig loader"
```

---

### Task 8: Session Hook

**Files:**
- Create: `src/hooks.py`
- Create: `tests/test_hooks.py`

- [ ] **Step 1: Write the test**

```python
# tests/test_hooks.py
import pytest
from src.hooks import build_session_context
from src.indexer import SkillIndexer
from src.vault_ops import VaultOps


@pytest.fixture
def hooked_env(tmp_vault, sample_skills, tmp_path):
    ops = VaultOps(str(tmp_vault))
    skills = ops.scan_skills()
    indexer = SkillIndexer(str(tmp_path / "hook_test.db"))
    indexer.build_index(skills)
    yield ops, indexer
    indexer.close()


class TestBuildSessionContext:
    def test_includes_category_index(self, hooked_env, tmp_vault):
        ops, indexer = hooked_env
        ctx = build_session_context(str(tmp_vault), indexer)
        assert "<skill_categories>" in ctx
        assert "software-development" in ctx

    def test_includes_discovery_prompt(self, hooked_env, tmp_vault):
        ops, indexer = hooked_env
        ctx = build_session_context(str(tmp_vault), indexer)
        assert "<skill_discovery>" in ctx
        assert "skill_lookup" in ctx
        assert "skill_load" in ctx

    def test_always_load_skills(self, hooked_env, tmp_vault):
        ops, indexer = hooked_env
        ctx = build_session_context(
            str(tmp_vault), indexer,
            always_load=["tdd-workflow"],
        )
        assert "TDD Workflow" in ctx

    def test_category_shows_counts(self, hooked_env, tmp_vault):
        ops, indexer = hooked_env
        ctx = build_session_context(str(tmp_vault), indexer)
        assert "3" in ctx  # software-development has 3 skills
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /mnt/data/hermes-skill-lazy-obsidian-vault && PYTHONPATH=. python -m pytest tests/test_hooks.py -v`
Expected: FAIL

- [ ] **Step 3: Write implementation**

```python
# src/hooks.py
from .indexer import SkillIndexer
from .vault_ops import VaultOps

DEFAULT_DISCOVERY = """\
<skill_discovery>
可用 MCP 工具发现和加载技能：
- skill_lookup(query, category?, top_k?): 搜索相关技能
- skill_load(name): 加载技能完整内容
- skill_categories(): 列出所有分类
优先根据分类定位，再调用 skill_lookup 精确查找。
</skill_discovery>"""


def build_session_context(
    vault_path: str,
    indexer: SkillIndexer,
    always_load: list[str] | None = None,
    discovery_prompt: str = "",
) -> str:
    parts: list[str] = []

    # Category index
    categories = indexer.list_categories()
    if categories:
        cat_lines = ["<skill_categories>"]
        for cat in categories:
            cat_lines.append(f"  {cat['name']} ({cat['skill_count']})")
        cat_lines.append("</skill_categories>")
        parts.append("\n".join(cat_lines))

    # Always-load skills
    if always_load:
        ops = VaultOps(vault_path)
        for name in always_load:
            skill_data = indexer.get_skill(name)
            if skill_data:
                note = ops.read_note(skill_data["path"])
                parts.append(f"<skill name=\"{name}\">\n{note['content']}\n</skill>")

    # Discovery prompt
    parts.append(discovery_prompt or DEFAULT_DISCOVERY)

    return "\n\n".join(parts)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /mnt/data/hermes-skill-lazy-obsidian-vault && PYTHONPATH=. python -m pytest tests/test_hooks.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/hooks.py tests/test_hooks.py
git commit -m "feat: add session hook for category index injection"
```

---

### Task 9: Hermes Tool Handlers

**Files:**
- Create: `src/tools.py`
- Create: `tests/test_tools.py`

- [ ] **Step 1: Write the test**

```python
# tests/test_tools.py
import pytest
from src.tools import SkillTools
from src.indexer import SkillIndexer
from src.vault_ops import VaultOps


@pytest.fixture
def tools(tmp_vault, sample_skills, tmp_path):
    ops = VaultOps(str(tmp_vault))
    skills = ops.scan_skills()
    indexer = SkillIndexer(str(tmp_path / "tools_test.db"))
    indexer.build_index(skills)
    t = SkillTools(str(tmp_vault), indexer)
    yield t
    indexer.close()


class TestSkillLookup:
    def test_returns_matching_skills(self, tools):
        results = tools.skill_lookup("TDD")
        assert len(results) > 0
        assert results[0]["name"] == "tdd-workflow"

    def test_returns_metadata_not_content(self, tools):
        results = tools.skill_lookup("TDD")
        assert "content" not in results[0]
        assert "summary" in results[0]

    def test_with_category_filter(self, tools):
        results = tools.skill_lookup("技能", category="research")
        assert all("research" in r["categories"] for r in results)

    def test_no_results_returns_empty(self, tools):
        results = tools.skill_lookup("xyzzy_not_real_999")
        assert results == []


class TestSkillLoad:
    def test_loads_full_content(self, tools):
        content = tools.skill_load("tdd-workflow")
        assert "TDD Workflow" in content
        assert "红" in content or "重构" in content

    def test_not_found_returns_error(self, tools):
        result = tools.skill_load("nonexistent")
        assert "not found" in result.lower() or "error" in result.lower()


class TestSkillCategories:
    def test_lists_all_categories(self, tools):
        cats = tools.skill_categories()
        assert len(cats) > 0
        names = [c["name"] for c in cats]
        assert "software-development" in names

    def test_categories_have_counts(self, tools):
        cats = tools.skill_categories()
        for cat in cats:
            assert "skill_count" in cat
            assert cat["skill_count"] > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /mnt/data/hermes-skill-lazy-obsidian-vault && PYTHONPATH=. python -m pytest tests/test_tools.py -v`
Expected: FAIL

- [ ] **Step 3: Write implementation**

```python
# src/tools.py
from .indexer import SkillIndexer
from .vault_ops import VaultOps
from .search import SkillSearch


class SkillTools:
    def __init__(self, vault_path: str, indexer: SkillIndexer):
        self.vault_path = vault_path
        self.indexer = indexer
        self.search = SkillSearch(indexer)

    def skill_lookup(self, query: str, category: str = None, top_k: int = 3) -> list[dict]:
        results = self.search.search(query, category=category, top_k=top_k)
        # Strip internal fields, return only metadata
        return [
            {
                "name": r["name"],
                "categories": r["categories"],
                "summary": r["summary"],
                "score": r["score"],
                "match_type": r["match_type"],
            }
            for r in results
        ]

    def skill_load(self, name: str) -> str:
        skill_data = self.indexer.get_skill(name)
        if skill_data is None:
            return f"Error: Skill '{name}' not found"
        ops = VaultOps(self.vault_path)
        note = ops.read_note(skill_data["path"])
        return note["content"]

    def skill_categories(self) -> list[dict]:
        return self.indexer.list_categories()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /mnt/data/hermes-skill-lazy-obsidian-vault && PYTHONPATH=. python -m pytest tests/test_tools.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add src/tools.py tests/test_tools.py
git commit -m "feat: add SkillTools (lookup, load, categories)"
```

---

### Task 10: Plugin Entry Point

**Files:**
- Create: `src/plugin.yaml`
- Modify: `src/__init__.py`

- [ ] **Step 1: Create plugin.yaml**

```yaml
name: obsidian-skill-vault
version: 0.1.0
description: "Obsidian Vault 驱动的技能懒加载 Plugin"
author: hermes-skill-lazy-obsidian-vault
kind: standalone
provides_tools:
  - skill_lookup
  - skill_load
  - skill_categories
provides_hooks:
  - on_session_start
```

- [ ] **Step 2: Update __init__.py with register(ctx)**

```python
# src/__init__.py
from pathlib import Path
from .config import VaultConfig
from .indexer import SkillIndexer
from .tools import SkillTools
from .hooks import build_session_context


def register(ctx):
    """Hermes Plugin entry point."""
    # Locate config
    plugin_dir = Path(__file__).parent
    config_path = plugin_dir.parent / "config.yaml"
    config = VaultConfig.from_file(str(config_path))

    if not config.vault_path:
        config.vault_path = str(plugin_dir.parent / "vault")

    db_path = Path(config.db_path)
    if not db_path.is_absolute():
        db_path = plugin_dir.parent / config.db_path

    # Initialize indexer
    indexer = SkillIndexer(str(db_path))

    # Initialize tools
    tools = SkillTools(config.vault_path, indexer)

    # Register tools
    ctx.register_tool("skill_lookup", tools.skill_lookup)
    ctx.register_tool("skill_load", tools.skill_load)
    ctx.register_tool("skill_categories", tools.skill_categories)

    # Register hook
    def on_session_start(**kwargs):
        return {
            "context": build_session_context(
                config.vault_path,
                indexer,
                always_load=config.always_load,
                discovery_prompt=config.discovery_prompt,
            )
        }

    ctx.register_hook("on_session_start", on_session_start)
```

- [ ] **Step 3: Commit**

```bash
git add src/plugin.yaml src/__init__.py
git commit -m "feat: add Hermes Plugin entry point with register(ctx)"
```

---

### Task 11: CLI Commands

**Files:**
- Create: `src/cli.py`

- [ ] **Step 1: Write implementation**

```python
# src/cli.py
import argparse
import sys
from pathlib import Path
from .config import VaultConfig
from .vault_ops import VaultOps
from .indexer import SkillIndexer
from .migrate import migrate_skills


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="obsidian-skill-vault",
        description="Obsidian Vault skill management for Hermes Agent",
    )
    sub = parser.add_subparsers(dest="command")

    # migrate
    p_migrate = sub.add_parser("migrate", help="Migrate skills from ~/.hermes/skills/ to vault")
    p_migrate.add_argument("--source", required=True, help="Source Hermes skills directory")
    p_migrate.add_argument("--vault", required=True, help="Target Obsidian vault path")

    # index
    p_index = sub.add_parser("index", help="Build/rebuild search index")
    p_index.add_argument("--vault", required=True, help="Obsidian vault path")
    p_index.add_argument("--db", default="skill_index.db", help="SQLite database path")

    # doctor
    p_doctor = sub.add_parser("doctor", help="Validate vault health")
    p_doctor.add_argument("--vault", required=True, help="Obsidian vault path")

    # serve (MCP mode)
    p_serve = sub.add_parser("serve", help="Run as MCP Server")
    p_serve.add_argument("--vault", required=True, help="Obsidian vault path")
    p_serve.add_argument("--db", default="skill_index.db", help="SQLite database path")

    args = parser.parse_args(argv)

    if args.command == "migrate":
        count = migrate_skills(args.source, args.vault)
        print(f"Migrated {count} skills to {args.vault}")

    elif args.command == "index":
        ops = VaultOps(args.vault)
        skills = ops.scan_skills()
        indexer = SkillIndexer(args.db)
        count = indexer.build_index(skills)
        indexer.close()
        print(f"Indexed {count} skills → {args.db}")

    elif args.command == "doctor":
        ops = VaultOps(args.vault)
        skills = ops.scan_skills()
        issues = []
        for s in skills:
            if not s.categories:
                issues.append(f"  WARNING: {s.name} has no categories")
            if not s.triggers:
                issues.append(f"  WARNING: {s.name} has no triggers")
            if not s.summary:
                issues.append(f"  WARNING: {s.name} has no summary")
        if issues:
            print(f"Found {len(issues)} issues:")
            for issue in issues:
                print(issue)
        else:
            print(f"All {len(skills)} skills are healthy")

    elif args.command == "serve":
        print("MCP Server mode not yet implemented in MVP")
        sys.exit(1)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Test CLI manually**

Run: `cd /mnt/data/hermes-skill-lazy-obsidian-vault && PYTHONPATH=. python -m src.cli --help`
Expected: Help text showing migrate, index, doctor, serve commands

- [ ] **Step 3: Commit**

```bash
git add src/cli.py
git commit -m "feat: add CLI commands (migrate, index, doctor, serve)"
```

---

### Task 12: Sample Data + Integration Test

**Files:**
- Create: `tests/test_integration.py`
- Modify: `vault/skills/` (sample data)

- [ ] **Step 1: Write the integration test**

```python
# tests/test_integration.py
"""End-to-end integration test: full pipeline from vault → index → search → load."""
import pytest
from src.vault_ops import VaultOps
from src.indexer import SkillIndexer
from src.tools import SkillTools
from src.hooks import build_session_context
from src.migrate import migrate_skills


class TestEndToEnd:
    def test_full_pipeline(self, tmp_vault, sample_skills, tmp_path):
        # 1. Scan vault
        ops = VaultOps(str(tmp_vault))
        skills = ops.scan_skills()
        assert len(skills) == 5

        # 2. Build index
        db_path = str(tmp_path / "integration.db")
        indexer = SkillIndexer(db_path)
        count = indexer.build_index(skills)
        assert count == 5

        # 3. Search
        tools = SkillTools(str(tmp_vault), indexer)
        results = tools.skill_lookup("TDD")
        assert len(results) > 0
        assert results[0]["name"] == "tdd-workflow"

        # 4. Load
        content = tools.skill_load("tdd-workflow")
        assert "TDD Workflow" in content

        # 5. Categories
        cats = tools.skill_categories()
        assert len(cats) >= 3
        assert any(c["name"] == "software-development" for c in cats)

        # 6. Session context (what gets injected into system prompt)
        ctx = build_session_context(str(tmp_vault), indexer, always_load=["tdd-workflow"])
        assert "<skill_categories>" in ctx
        assert "software-development" in ctx
        assert "<skill_discovery>" in ctx
        assert "TDD Workflow" in ctx  # always-load skill content

        indexer.close()

    def test_migration_then_query(self, tmp_path, tmp_vault):
        # Setup: fake hermes skills dir
        hermes_dir = tmp_path / "hermes_skills"
        skill_dir = hermes_dir / "testing" / "migrated-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "---\nname: migrated-skill\ncategories: [testing]\n"
            "triggers: ['迁移测试']\nsummary: A migrated skill\n---\n\n# Migrated",
            encoding="utf-8",
        )

        # Migrate
        count = migrate_skills(str(hermes_dir), str(tmp_vault))
        assert count == 1

        # Index
        ops = VaultOps(str(tmp_vault))
        skills = ops.scan_skills()
        assert len(skills) == 1
        assert skills[0].name == "migrated-skill"

        db_path = str(tmp_path / "mig_test.db")
        indexer = SkillIndexer(db_path)
        indexer.build_index(skills)

        # Query
        tools = SkillTools(str(tmp_vault), indexer)
        results = tools.skill_lookup("迁移测试")
        assert len(results) == 1
        assert results[0]["name"] == "migrated-skill"

        content = tools.skill_load("migrated-skill")
        assert "Migrated" in content

        indexer.close()
```

- [ ] **Step 2: Run all tests**

Run: `cd /mnt/data/hermes-skill-lazy-obsidian-vault && PYTHONPATH=. python -m pytest tests/ -v`
Expected: All tests pass (models: 4, vault_ops: 9, indexer: 7, search: 9, migrate: 3, hooks: 4, tools: 7, integration: 2 = 45 total)

- [ ] **Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add end-to-end integration tests"
```

---

### Task 13: Run Full Test Suite + Verify

- [ ] **Step 1: Run complete test suite**

Run: `cd /mnt/data/hermes-skill-lazy-obsidian-vault && PYTHONPATH=. python -m pytest tests/ -v --tb=short`

Expected: ~45 tests pass, 0 fail

- [ ] **Step 2: Run CLI against real vault**

```bash
cd /mnt/data/hermes-skill-lazy-obsidian-vault
PYTHONPATH=. python -m src.cli doctor --vault ./vault
PYTHONPATH=. python -m src.cli index --vault ./vault --db ./skill_index.db
```

Expected: doctor reports healthy, index reports skill count

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "chore: MVP complete — vault_ops, indexer, search, tools, hooks, migrate CLI"
```
