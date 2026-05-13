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

    def test_finds_debug_by_english_trigger(self, search_engine):
        results = search_engine.search("bug")
        assert len(results) > 0
        names = [r["name"] for r in results]
        assert "systematic-debugging" in names


class TestCategoryFilter:
    def test_filter_excludes_non_matching(self, search_engine):
        # "debug" matches systematic-debugging trigger, but it's not in "research" category
        results = search_engine.search("debug", category="research")
        assert all("research" in r["categories"] for r in results)

    def test_category_adds_new_results(self, search_engine):
        # "search" matches web-search by trigger; writing category adds documentation-writing
        results = search_engine.search("search", category="writing")
        names = [r["name"] for r in results]
        assert "documentation-writing" in names

    def test_category_filter_reduces_results(self, search_engine):
        all_results = search_engine.search("debug", top_k=10)
        filtered = search_engine.search("debug", category="research", top_k=10)
        assert len(filtered) <= len(all_results)


class TestFTSFallback:
    def test_fts_finds_by_name_token(self, search_engine):
        results = search_engine.search("web")
        names = [r["name"] for r in results]
        assert "web-search" in names

    def test_fts_finds_by_summary_english(self, search_engine):
        results = search_engine.search("debugging")
        assert len(results) > 0


class TestTopK:
    def test_respects_top_k(self, search_engine):
        results = search_engine.search("debug", top_k=2)
        assert len(results) <= 2

    def test_default_top_k_is_3(self, search_engine):
        results = search_engine.search("debug")
        assert len(results) <= 3


class TestNoResults:
    def test_no_match_returns_empty(self, search_engine):
        results = search_engine.search("xyzzy_not_a_real_thing_12345")
        assert results == []
