import re
import shutil
import frontmatter
from pathlib import Path
from .vault_ops import VaultOps
from .migrate import _extract_triggers_from_body, _collect_tags, _generate_hub_notes


def sync_skill_to_vault(skill_source_path: str, vault_path: str) -> bool:
    """Migrate a single skill SKILL.md into the vault.

    Args:
        skill_source_path: Absolute path to the SKILL.md file.
        vault_path: Absolute path to the vault root.

    Returns:
        True if the skill was synced successfully.
    """
    skill_md = Path(skill_source_path)
    if not skill_md.exists() or skill_md.name != "SKILL.md":
        return False

    with open(skill_md, "r", encoding="utf-8") as f:
        post = frontmatter.load(f)

    meta = dict(post.metadata)

    if "name" not in meta:
        meta["name"] = skill_md.parent.stem

    # Normalize categories
    if "categories" not in meta:
        cats = []
        if "category" in meta and meta["category"]:
            cats.append(meta["category"])
        parts = skill_md.parent.relative_to(skill_md.parent.parent).parts
        if parts:
            cats.append(parts[0])
        meta["categories"] = list(dict.fromkeys(cats))
        meta.pop("category", None)

    # Generate summary
    if "summary" not in meta or not meta["summary"]:
        desc = meta.get("description", "")
        if isinstance(desc, str):
            meta["summary"] = desc[:200].rstrip()
        else:
            meta["summary"] = ""

    # Generate triggers
    if "triggers" not in meta or not meta["triggers"]:
        triggers = _extract_triggers_from_body(post.content)
        tags = _collect_tags(meta)
        for t in tags:
            if t not in triggers:
                triggers.append(t)
        meta["triggers"] = triggers

    # Figure out target path: use the skill name directly under skills/
    target_path = f"skills/{meta['name']}.md"

    ops = VaultOps(vault_path)
    ops.write_note(target_path, meta, post.content)

    # Regenerate Hub Notes
    _generate_hub_notes(vault_path)

    return True


def remove_skill_from_vault(skill_name: str, vault_path: str) -> bool:
    """Remove a skill from the vault by name.

    Returns True if the skill was found and removed.
    """
    vault = Path(vault_path)
    skills_dir = vault / "skills"
    if not skills_dir.exists():
        return False

    # Find the skill file
    for md_file in skills_dir.rglob("*.md"):
        if md_file.stem == skill_name:
            md_file.unlink()
            # Remove empty parent dirs
            try:
                md_file.parent.rmdir()
            except OSError:
                pass
            # Regenerate Hub Notes
            _generate_hub_notes(vault_path)
            return True

    return False
