import pytest
from src.vault_ops import VaultOps


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
