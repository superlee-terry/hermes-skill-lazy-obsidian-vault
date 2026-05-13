import re
import logging
import frontmatter
from pathlib import Path

from .indexer import SkillIndexer
from .vault_ops import VaultOps
from .search import SkillSearch
from .migrate import _extract_triggers_from_body, _collect_tags, _generate_hub_notes

logger = logging.getLogger(__name__)


class SkillTools:
    def __init__(self, vault_path: str, indexer: SkillIndexer):
        self.vault_path = vault_path
        self.indexer = indexer
        self.search = SkillSearch(indexer)

    def skill_lookup(self, query: str, category: str = None, top_k: int = 3) -> list[dict]:
        results = self.search.search(query, category=category, top_k=top_k)
        return [
            {
                "name": r["name"],
                "categories": r["categories"],
                "summary": r["summary"],
                "score": r["score"],
                "match_type": r["match_type"],
            }
            for r in results
        ]

    def skill_load(self, name: str) -> str:
        skill_data = self.indexer.get_skill(name)
        if skill_data is None:
            return f"Error: Skill '{name}' not found"
        ops = VaultOps(self.vault_path)
        note = ops.read_note(skill_data["path"])
        return note["content"]

    def skill_categories(self) -> list[dict]:
        return self.indexer.list_categories()

    def skill_install(
        self,
        action: str,
        name: str,
        content: str = "",
        category: str = "",
        description: str = "",
    ) -> dict:
        """Create, edit, or delete a skill in the vault + index."""
        if action == "create":
            return self._create(name, content, category, description)
        elif action == "edit":
            return self._edit(name, content)
        elif action == "delete":
            return self._delete(name)
        return {"success": False, "error": f"Unknown action '{action}'. Use: create, edit, delete"}

    def _normalize_meta(self, content: str, category: str = "", description: str = "") -> tuple[dict, str]:
        """Parse SKILL.md content, normalize metadata. Returns (meta, body)."""
        if content.startswith("---"):
            post = frontmatter.loads(content)
            meta = dict(post.metadata)
            body = post.content
        else:
            meta = {}
            body = content

        if "name" not in meta:
            return None, None, "Frontmatter must include 'name' field."

        # Normalize categories
        cats = meta.get("categories", [])
        if isinstance(cats, str):
            cats = [cats]
        if category and category not in cats:
            cats.insert(0, category)
        meta["categories"] = list(dict.fromkeys(cats))

        # Summary
        if not meta.get("summary"):
            desc = description or meta.get("description", "")
            meta["summary"] = desc[:200].rstrip() if isinstance(desc, str) else ""

        # Triggers
        if not meta.get("triggers"):
            triggers = _extract_triggers_from_body(body)
            tags = _collect_tags(meta)
            for t in tags:
                if t not in triggers:
                    triggers.append(t)
            meta["triggers"] = triggers

        return meta, body, None

    def _create(self, name: str, content: str, category: str, description: str) -> dict:
        target = f"skills/{name}.md"
        vault_file = Path(self.vault_path) / target
        if vault_file.exists():
            return {"success": False, "error": f"Skill '{name}' already exists. Use action='edit' to update."}

        if not content.strip():
            return {"success": False, "error": "content is required for 'create'."}

        meta, body, err = self._normalize_meta(content, category, description)
        if err:
            return {"success": False, "error": err}

        ops = VaultOps(self.vault_path)
        ops.write_note(target, meta, body)
        self.indexer.update_index(self.vault_path)
        _generate_hub_notes(self.vault_path)

        # Sync to ~/.hermes/skills/ for compatibility
        self._sync_to_hermes(name, content, category)

        return {"success": True, "message": f"Skill '{name}' created.", "path": target}

    def _edit(self, name: str, content: str) -> dict:
        skill_data = self.indexer.get_skill(name)
        if skill_data is None:
            return {"success": False, "error": f"Skill '{name}' not found."}

        if not content.strip():
            return {"success": False, "error": "content is required for 'edit'."}

        meta, body, err = self._normalize_meta(content)
        if err:
            return {"success": False, "error": err}

        target = skill_data["path"]
        ops = VaultOps(self.vault_path)
        ops.write_note(target, meta, body)
        self.indexer.update_index(self.vault_path)
        _generate_hub_notes(self.vault_path)

        # Sync to ~/.hermes/skills/
        self._sync_to_hermes(name, content)

        return {"success": True, "message": f"Skill '{name}' updated.", "path": target}

    def _delete(self, name: str) -> dict:
        skill_data = self.indexer.get_skill(name)
        if skill_data is None:
            return {"success": False, "error": f"Skill '{name}' not found."}

        vault_file = Path(self.vault_path) / skill_data["path"]
        if vault_file.exists():
            vault_file.unlink()
            try:
                vault_file.parent.rmdir()
            except OSError:
                pass

        self.indexer.update_index(self.vault_path)
        _generate_hub_notes(self.vault_path)

        # Remove from ~/.hermes/skills/ too
        self._remove_from_hermes(name)

        return {"success": True, "message": f"Skill '{name}' deleted."}

    def _sync_to_hermes(self, name: str, content: str, category: str = "") -> None:
        """Write a copy to ~/.hermes/skills/ for native compatibility."""
        try:
            skills_dir = Path.home() / ".hermes" / "skills"
            if category:
                skill_dir = skills_dir / category / name
            else:
                skill_dir = skills_dir / name
            skill_dir.mkdir(parents=True, exist_ok=True)
            (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
        except Exception:
            logger.debug("Failed to sync '%s' to ~/.hermes/skills/", name, exc_info=True)

    def _remove_from_hermes(self, name: str) -> None:
        """Remove skill copy from ~/.hermes/skills/."""
        try:
            import shutil
            skills_dir = Path.home() / ".hermes" / "skills"
            if not skills_dir.exists():
                return
            for d in skills_dir.rglob(name):
                if d.is_dir() and (d / "SKILL.md").exists():
                    shutil.rmtree(d, ignore_errors=True)
                    # Clean empty parent (category dir)
                    try:
                        d.parent.rmdir()
                    except OSError:
                        pass
                    break
        except Exception:
            logger.debug("Failed to remove '%s' from ~/.hermes/skills/", name, exc_info=True)
