import re
import frontmatter
from pathlib import Path
from .vault_ops import VaultOps


def _extract_triggers_from_body(content: str) -> list[str]:
    """Extract trigger phrases from 'When to use' section in body."""
    triggers = []
    match = re.search(
        r"^##\s+When to use(?:\s+this skill)?\s*\n(.*?)(?=\n##\s|\Z)",
        content,
        re.DOTALL | re.MULTILINE,
    )
    if not match:
        return triggers

    section = match.group(1)

    # Extract quoted phrases like "play X", "search for X"
    for m in re.finditer(r'"([^"]+)"', section):
        phrase = m.group(1).strip()
        if phrase and len(phrase) <= 80:
            triggers.append(phrase)

    # Extract comma-separated verbs/phrases from "like X, Y, Z" patterns
    like_match = re.search(r'(?:something like|such as|includes?:?)\s*(.+?)(?:\.\s|\n|$)', section)
    if like_match and not triggers:
        raw = like_match.group(1)
        for part in re.split(r'[;,]', raw):
            part = re.sub(r'["\']', '', part).strip()
            if 2 <= len(part) <= 60:
                triggers.append(part)

    return triggers


def _collect_tags(meta: dict) -> list[str]:
    """Collect tags from frontmatter tags, metadata.hermes.tags."""
    tags = []
    for t in meta.get("tags", []):
        if t not in tags:
            tags.append(t)
    hermes_meta = meta.get("metadata", {})
    if isinstance(hermes_meta, dict):
        for t in hermes_meta.get("hermes", {}).get("tags", []):
            if t not in tags:
                tags.append(t)
    return tags


def migrate_skills(source_dir: str, vault_path: str) -> int:
    source = Path(source_dir)
    ops = VaultOps(vault_path)
    count = 0

    for skill_md in sorted(source.rglob("SKILL.md")):
        with open(skill_md, "r", encoding="utf-8") as f:
            post = frontmatter.load(f)

        meta = dict(post.metadata)

        # Ensure name
        if "name" not in meta:
            meta["name"] = skill_md.parent.stem

        # Normalize categories: accept "category" (singular), "categories" (plural),
        # or infer from directory structure
        if "categories" not in meta:
            cats = []
            if "category" in meta and meta["category"]:
                cats.append(meta["category"])
            # Infer from first-level directory under source
            parts = skill_md.parent.relative_to(source).parts
            if parts:
                cats.append(parts[0])
            meta["categories"] = list(dict.fromkeys(cats))  # deduplicate, preserve order
            # Remove singular form to avoid confusion
            meta.pop("category", None)

        # Generate summary from description if missing
        if "summary" not in meta or not meta["summary"]:
            desc = meta.get("description", "")
            if isinstance(desc, str):
                meta["summary"] = desc[:200].rstrip()
            else:
                meta["summary"] = ""

        # Generate triggers from body "When to use" section + tags if missing
        if "triggers" not in meta or not meta["triggers"]:
            triggers = _extract_triggers_from_body(post.content)
            tags = _collect_tags(meta)
            for t in tags:
                if t not in triggers:
                    triggers.append(t)
            meta["triggers"] = triggers

        # Strip the SKILL.md's parent dir (the skill name folder) from the path
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

    # Remove old hub notes before regenerating
    for old_hub in index_dir.glob("*.md"):
        if old_hub.name != "README.md":
            old_hub.unlink()

    for cat, names in sorted(cat_skills.items()):
        hub_path = f"_index/{cat}.md"
        links = "\n".join(f"- [[{n}]]" for n in sorted(names))
        content = f"# {cat}\n\n## 技能列表\n\n{links}\n"
        ops.write_note(hub_path, {"type": "hub", "category": cat}, content)
