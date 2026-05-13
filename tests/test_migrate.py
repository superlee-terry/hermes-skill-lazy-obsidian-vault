import pytest
from src.migrate import migrate_skills, _extract_triggers_from_body, _collect_tags
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


@pytest.fixture
def real_style_skills_dir(tmp_path):
    """Skills that mimic real Hermes skills: only description, no triggers/summary."""
    skills = tmp_path / "real_skills"

    # Skill with "When to use" section and hermes tags
    s1 = skills / "media" / "spotify" / "SKILL.md"
    s1.parent.mkdir(parents=True)
    s1.write_text(
        "---\n"
        "name: spotify\n"
        'description: "Spotify: play, search, queue, manage playlists and devices."\n'
        "metadata:\n"
        "  hermes:\n"
        "    tags: [spotify, music, playback, playlists, media]\n"
        "---\n\n"
        "# Spotify\n\n"
        "## When to use this skill\n\n"
        'The user says something like "play X", "pause", "skip", "queue up X", '
        '"what\'s playing", "search for X", "add to my X playlist", "make a playlist".\n',
        encoding="utf-8",
    )

    # Skill with no "When to use" section, only tags
    s2 = skills / "productivity" / "pptx" / "SKILL.md"
    s2.parent.mkdir(parents=True)
    s2.write_text(
        "---\n"
        "name: pptx\n"
        'description: "Create, read, edit .pptx decks, slides, notes, templates."\n'
        "tags: [pptx, powerpoint, slides]\n"
        "---\n\n"
        "# PowerPoint\n\n## Overview\n\nMake slides.\n",
        encoding="utf-8",
    )

    # Skill with only description, no tags or triggers
    s3 = skills / "dev" / "git-helper" / "SKILL.md"
    s3.parent.mkdir(parents=True)
    s3.write_text(
        "---\n"
        "name: git-helper\n"
        "description: Git workflow helper for branching and merging.\n"
        "---\n\n"
        "# Git Helper\n",
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


class TestTriggerExtraction:
    def test_extract_quoted_phrases(self):
        content = (
            "## When to use this skill\n\n"
            'The user says something like "play X", "pause", "skip".\n'
        )
        triggers = _extract_triggers_from_body(content)
        assert "play X" in triggers
        assert "pause" in triggers
        assert "skip" in triggers

    def test_extract_from_when_to_use_no_quotes(self):
        content = (
            "## When to use\n\n"
            "Use when the user mentions deck, slides, or presentation.\n"
        )
        triggers = _extract_triggers_from_body(content)
        # No quoted phrases and no "like/such as" pattern
        assert triggers == []

    def test_no_when_to_use_section(self):
        triggers = _extract_triggers_from_body("# Overview\n\nSome text.\n")
        assert triggers == []

    def test_collect_tags_from_hermes_metadata(self):
        meta = {
            "metadata": {
                "hermes": {"tags": ["spotify", "music"]},
            },
            "tags": ["playback"],
        }
        tags = _collect_tags(meta)
        assert tags == ["playback", "spotify", "music"]

    def test_collect_tags_no_hermes_metadata(self):
        tags = _collect_tags({"tags": ["a", "b"]})
        assert tags == ["a", "b"]


class TestRealStyleMigration:
    def test_generates_summary_from_description(self, real_style_skills_dir, tmp_vault):
        migrate_skills(str(real_style_skills_dir), str(tmp_vault))
        ops = VaultOps(str(tmp_vault))
        skill = next(s for s in ops.scan_skills() if s.name == "spotify")
        assert skill.summary == "Spotify: play, search, queue, manage playlists and devices."

    def test_generates_triggers_from_when_to_use(self, real_style_skills_dir, tmp_vault):
        migrate_skills(str(real_style_skills_dir), str(tmp_vault))
        ops = VaultOps(str(tmp_vault))
        skill = next(s for s in ops.scan_skills() if s.name == "spotify")
        assert "play X" in skill.triggers
        assert "pause" in skill.triggers
        # hermes tags should also be included
        assert "spotify" in skill.triggers

    def test_fallback_triggers_from_tags(self, real_style_skills_dir, tmp_vault):
        migrate_skills(str(real_style_skills_dir), str(tmp_vault))
        ops = VaultOps(str(tmp_vault))
        skill = next(s for s in ops.scan_skills() if s.name == "pptx")
        assert "pptx" in skill.triggers
        assert "powerpoint" in skill.triggers

    def test_summary_from_description_only_skill(self, real_style_skills_dir, tmp_vault):
        migrate_skills(str(real_style_skills_dir), str(tmp_vault))
        ops = VaultOps(str(tmp_vault))
        skill = next(s for s in ops.scan_skills() if s.name == "git-helper")
        assert skill.summary == "Git workflow helper for branching and merging."
        assert skill.triggers == []  # no "When to use", no tags
