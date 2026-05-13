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
