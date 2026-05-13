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
        results = tools.skill_lookup("debug", category="research")
        assert all("research" in r["categories"] for r in results)

    def test_no_results_returns_empty(self, tools):
        results = tools.skill_lookup("xyzzy_not_real_999")
        assert results == []


class TestSkillLoad:
    def test_loads_full_content(self, tools):
        content = tools.skill_load("tdd-workflow")
        assert "TDD Workflow" in content

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
