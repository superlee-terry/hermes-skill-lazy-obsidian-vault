import pytest
from pathlib import Path


@pytest.fixture
def tmp_vault(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / ".obsidian").mkdir()
    (vault / "skills").mkdir()
    (vault / "_index").mkdir()
    return vault


@pytest.fixture
def sample_skills(tmp_vault):
    skills_dir = tmp_vault / "skills"
    skills = [
        {
            "name": "tdd-workflow",
            "dir": "software-development/testing",
            "meta": {
                "name": "tdd-workflow",
                "categories": ["software-development", "testing"],
                "tags": ["python", "testing", "tdd"],
                "triggers": ["TDD", "测试驱动", "test driven", "红绿重构"],
                "summary": "TDD 红-绿-重构工作流",
            },
            "content": "# TDD Workflow\n\n## 步骤\n1. 写一个失败的测试（红）\n2. 写最少的代码让测试通过（绿）\n3. 重构代码",
        },
        {
            "name": "systematic-debugging",
            "dir": "software-development/debugging",
            "meta": {
                "name": "systematic-debugging",
                "categories": ["software-development", "debugging"],
                "tags": ["debug", "troubleshooting", "bug"],
                "triggers": ["调试", "debug", "bug", "报错", "错误"],
                "summary": "系统性调试方法论",
            },
            "content": "# Systematic Debugging\n\n## 步骤\n1. 复现问题\n2. 缩小范围\n3. 形成假设\n4. 验证假设\n5. 修复并验证",
        },
        {
            "name": "code-review-checklist",
            "dir": "software-development/code-review",
            "meta": {
                "name": "code-review-checklist",
                "categories": ["software-development", "code-review"],
                "tags": ["review", "quality", "pr"],
                "triggers": ["代码审查", "code review", "PR review", "pull request"],
                "summary": "代码审查清单",
            },
            "content": "# Code Review Checklist\n\n- [ ] 逻辑正确性\n- [ ] 错误处理\n- [ ] 性能影响\n- [ ] 安全性\n- [ ] 可读性",
        },
        {
            "name": "web-search",
            "dir": "research",
            "meta": {
                "name": "web-search",
                "categories": ["research", "information-gathering"],
                "tags": ["search", "web", "internet"],
                "triggers": ["搜索", "search", "查找资料", "网上搜索"],
                "summary": "网络搜索与信息收集",
            },
            "content": "# Web Search\n\n使用搜索工具收集信息，验证事实，查找参考资料。",
        },
        {
            "name": "documentation-writing",
            "dir": "writing",
            "meta": {
                "name": "documentation-writing",
                "categories": ["writing", "documentation"],
                "tags": ["docs", "writing", "readme"],
                "triggers": ["写文档", "documentation", "README", "文档"],
                "summary": "技术文档编写规范",
            },
            "content": "# Documentation Writing\n\n## 原则\n- 简洁明了\n- 代码示例优先\n- 结构化章节",
        },
    ]
    for skill in skills:
        skill_path = skills_dir / skill["dir"] / f"{skill['name']}.md"
        skill_path.parent.mkdir(parents=True, exist_ok=True)
        fm_lines = ["---"]
        for k, v in skill["meta"].items():
            if isinstance(v, list):
                fm_lines.append(f"{k}:")
                for item in v:
                    fm_lines.append(f'  - "{item}"')
            else:
                fm_lines.append(f'{k}: "{v}"')
        fm_lines.append("---")
        full_content = "\n".join(fm_lines) + "\n\n" + skill["content"]
        skill_path.write_text(full_content, encoding="utf-8")
    return skills
