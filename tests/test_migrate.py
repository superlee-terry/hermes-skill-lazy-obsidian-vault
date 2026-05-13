import pytest
from src.migrate import migrate_skills
from src.vault_ops import VaultOps


@pytest.fixture
def hermes_skills_dir(tmp_path):
    skills = tmp_path / "hermes_skills"
    s1 = skills / "software-development" / "testing" / "my-tdd" / "SKILL.md"
    s1.parent.mkdir(parents=True)
    s1.write_text(
        "---\nname: my-tdd\ncategories: [testing]\ntriggers: ['TDD']\nsummary: TDD skill\n---\n\n# My TDD",
        encoding="utf-8",
    )
    s2 = skills / "research" / "search" / "SKILL.md"
    s2.parent.mkdir(parents=True)
    s2.write_text(
        "---\nname: search-skill\ncategories: [research]\ntriggers: ['搜索']\nsummary: Search skill\n---\n\n# Search",
        encoding="utf-8",
    )
    return skills


class TestMigrate:
    def test_migrate_creates_vault_files(self, hermes_skills_dir, tmp_vault):
        count = migrate_skills(str(hermes_skills_dir), str(tmp_vault))
        assert count == 2
        ops = VaultOps(str(tmp_vault))
        skills = ops.scan_skills()
        names = {s.name for s in skills}
        assert "my-tdd" in names
        assert "search-skill" in names

    def test_migrate_preserves_content(self, hermes_skills_dir, tmp_vault):
        migrate_skills(str(hermes_skills_dir), str(tmp_vault))
        ops = VaultOps(str(tmp_vault))
        skill = next(s for s in ops.scan_skills() if s.name == "my-tdd")
        assert "My TDD" in skill.content
        assert "TDD" in skill.triggers

    def test_migrate_preserves_directory_structure(self, hermes_skills_dir, tmp_vault):
        migrate_skills(str(hermes_skills_dir), str(tmp_vault))
        tdd_path = tmp_vault / "skills" / "software-development" / "testing" / "my-tdd.md"
        assert tdd_path.exists()

    def test_migrate_generates_hub_notes(self, hermes_skills_dir, tmp_vault):
        migrate_skills(str(hermes_skills_dir), str(tmp_vault))
        # Should have hub notes for each category
        testing_hub = tmp_vault / "_index" / "testing.md"
        research_hub = tmp_vault / "_index" / "research.md"
        assert testing_hub.exists()
        assert research_hub.exists()
        ops = VaultOps(str(tmp_vault))
        note = ops.read_note("_index/testing.md")
        assert "[[my-tdd]]" in note["content"]

    def test_migrate_generates_no_duplicate_hubs(self, hermes_skills_dir, tmp_vault):
        migrate_skills(str(hermes_skills_dir), str(tmp_vault))
        migrate_skills(str(hermes_skills_dir), str(tmp_vault))
        # Second run should overwrite, not duplicate
        ops = VaultOps(str(tmp_vault))
        skills = ops.scan_skills()
        assert len(skills) == 2
