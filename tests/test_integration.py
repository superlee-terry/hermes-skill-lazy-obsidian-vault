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

        # 6. Session context
        ctx = build_session_context(str(tmp_vault), indexer, always_load=["tdd-workflow"])
        assert "<skill_categories>" in ctx
        assert "software-development" in ctx
        assert "<skill_discovery>" in ctx
        assert "TDD Workflow" in ctx

        indexer.close()

    def test_migration_then_query(self, tmp_path, tmp_vault):
        hermes_dir = tmp_path / "hermes_skills"
        skill_dir = hermes_dir / "testing" / "migrated-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "---\nname: migrated-skill\ncategories: [testing]\n"
            "triggers: ['迁移测试']\nsummary: A migrated skill\n---\n\n# Migrated",
            encoding="utf-8",
        )

        count = migrate_skills(str(hermes_dir), str(tmp_vault))
        assert count == 1

        ops = VaultOps(str(tmp_vault))
        skills = ops.scan_skills()
        assert len(skills) == 1
        assert skills[0].name == "migrated-skill"

        db_path = str(tmp_path / "mig_test.db")
        indexer = SkillIndexer(db_path)
        indexer.build_index(skills)

        tools = SkillTools(str(tmp_vault), indexer)
        results = tools.skill_lookup("迁移测试")
        assert len(results) == 1
        assert results[0]["name"] == "migrated-skill"

        content = tools.skill_load("migrated-skill")
        assert "Migrated" in content

        indexer.close()
