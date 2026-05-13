import frontmatter
from pathlib import Path
from .vault_ops import VaultOps


def migrate_skills(source_dir: str, vault_path: str) -> int:
    source = Path(source_dir)
    ops = VaultOps(vault_path)
    count = 0

    for skill_md in sorted(source.rglob("SKILL.md")):
        with open(skill_md, "r", encoding="utf-8") as f:
            post = frontmatter.load(f)

        meta = dict(post.metadata)
        if "name" not in meta:
            meta["name"] = skill_md.parent.stem

        rel_parent = skill_md.parent.parent.relative_to(source)
        target_path = f"skills/{rel_parent / meta['name']}.md"

        ops.write_note(target_path, meta, post.content)
        count += 1

    # Generate Hub Notes after migration
    _generate_hub_notes(vault_path)
    return count


def _generate_hub_notes(vault_path: str):
    """Create Hub Notes in _index/ that link skills by category."""
    ops = VaultOps(vault_path)
    skills = ops.scan_skills()

    # Group skills by category
    cat_skills: dict[str, list[str]] = {}
    for s in skills:
        for cat in s.categories:
            cat_skills.setdefault(cat, []).append(s.name)

    index_dir = Path(vault_path) / "_index"
    index_dir.mkdir(parents=True, exist_ok=True)

    for cat, names in sorted(cat_skills.items()):
        hub_path = f"_index/{cat}.md"
        links = "\n".join(f"- [[{n}]]" for n in sorted(names))
        content = f"# {cat}\n\n## 技能列表\n\n{links}\n"
        ops.write_note(hub_path, {"type": "hub", "category": cat}, content)
