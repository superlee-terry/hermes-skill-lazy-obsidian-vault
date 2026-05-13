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

        # Strip the SKILL.md's parent dir (the skill name folder) from the path
        # e.g. software-development/testing/my-tdd/SKILL.md → software-development/testing
        rel_parent = skill_md.parent.parent.relative_to(source)
        target_path = f"skills/{rel_parent / meta['name']}.md"

        ops.write_note(target_path, meta, post.content)
        count += 1

    return count
