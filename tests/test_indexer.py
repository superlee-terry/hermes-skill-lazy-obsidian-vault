import json
import pytest
from src.indexer import SkillIndexer
from src.vault_ops import VaultOps


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
        assert sw["skill_count"] == 3
