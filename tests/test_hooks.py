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
