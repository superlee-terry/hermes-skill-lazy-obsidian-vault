import json
import pytest
from src.main import skill_lookup, skill_load, skill_categories, _init
from src.vault_ops import VaultOps
from src.indexer import SkillIndexer


@pytest.fixture(autouse=True)
def setup_tools(tmp_vault, sample_skills, tmp_path):
    """Initialize the MCP server tools with test data."""
    ops = VaultOps(str(tmp_vault))
    skills = ops.scan_skills()
    db_path = str(tmp_path / "mcp_test.db")
    indexer = SkillIndexer(db_path)
    indexer.build_index(skills)
    _init(str(tmp_vault), db_path)
    yield
    indexer.close()


class TestMCPSkillLookup:
    def test_returns_json(self):
        result = skill_lookup("TDD")
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) > 0
        assert parsed[0]["name"] == "tdd-workflow"

    def test_with_category_filter(self):
        result = skill_lookup("debug", category="research")
        parsed = json.loads(result)
        assert all("research" in r["categories"] for r in parsed)

    def test_empty_category_ignored(self):
        result = skill_lookup("TDD", category="")
        parsed = json.loads(result)
        assert len(parsed) > 0

    def test_top_k_respected(self):
        result = skill_lookup("debug", top_k=1)
        parsed = json.loads(result)
        assert len(parsed) <= 1

    def test_no_match(self):
        result = skill_lookup("xyzzy_not_real_999")
        parsed = json.loads(result)
        assert parsed == []

    def test_chinese_query(self):
        result = skill_lookup("调试")
        parsed = json.loads(result)
        assert len(parsed) > 0
        assert parsed[0]["name"] == "systematic-debugging"


class TestMCPSkillLoad:
    def test_loads_content(self):
        result = skill_load("tdd-workflow")
        assert "TDD Workflow" in result

    def test_not_found(self):
        result = skill_load("nonexistent")
        assert "not found" in result.lower() or "error" in result.lower()


class TestMCPSkillCategories:
    def test_returns_json(self):
        result = skill_categories()
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) > 0
        assert any(c["name"] == "software-development" for c in parsed)

    def test_has_counts(self):
        result = skill_categories()
        parsed = json.loads(result)
        for cat in parsed:
            assert "skill_count" in cat
            assert cat["skill_count"] > 0
