import re
import logging
import frontmatter
from pathlib import Path
from typing import Callable

from .indexer import SkillIndexer
from .vault_ops import VaultOps
from .search import SkillSearch
from .migrate import _extract_triggers_from_body, _collect_tags, _generate_hub_notes

logger = logging.getLogger(__name__)


class SkillTools:
    def __init__(self, vault_path: str, indexer: SkillIndexer,
                 llm_enricher: Callable | None = None):
        self.vault_path = vault_path
        self.indexer = indexer
        self.search = SkillSearch(indexer)
        self._llm_enricher = llm_enricher

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

    def _normalize_meta(self, content: str, category: str = "", description: str = "",
                        mode: str = "create") -> tuple[dict, str]:
        """Parse SKILL.md content, normalize metadata. Returns (meta, body, error)."""
        if content.startswith("---"):
            post = frontmatter.loads(content)
            meta = dict(post.metadata)
            body = post.content
        else:
            meta = {}
            body = content

        if "name" not in meta:
            return None, None, "Frontmatter must include 'name' field."

        # Validate description
        desc = description or meta.get("description", "")
        if not desc or not str(desc).strip():
            return None, None, "Frontmatter must include 'description' field."
        if len(str(desc)) < 10:
            return None, None, f"Description too vague ({len(str(desc))} chars). Provide at least 10 characters."

        # Normalize categories: use provided category, fall back to existing
        cats = meta.get("categories", [])
        if isinstance(cats, str):
            cats = [cats]
        if category and category not in cats:
            cats.insert(0, category)
        # Remove self-name from categories (should not be its own category)
        name = meta["name"]
        cats = [c for c in cats if c != name]
        meta["categories"] = list(dict.fromkeys(cats))

        # Summary
        if not meta.get("summary"):
            meta["summary"] = str(desc)[:200].rstrip() if isinstance(desc, str) else ""

        # Triggers
        if not meta.get("triggers"):
            triggers = _extract_triggers_from_body(body)
            tags = _collect_tags(meta)
            for t in tags:
                if t not in triggers:
                    triggers.append(t)
            # Always include name as trigger
            name_trigger = name.replace("-", " ")
            if name_trigger not in triggers:
                triggers.insert(0, name_trigger)
            meta["triggers"] = triggers

        # LLM enrichment (optional, graceful degradation)
        if self._llm_enricher is not None:
            try:
                meta = self._llm_enricher(meta, body, mode=mode)
            except Exception:
                logger.debug("LLM enricher failed, using rule-based metadata", exc_info=True)

        return meta, body, None

    def _create(self, name: str, content: str, category: str, description: str) -> dict:
        # Validate body length
        if not content.strip():
            return {"success": False, "error": "content is required for 'create'."}

        meta, body, err = self._normalize_meta(content, category, description, mode="create")
        if err:
            return {"success": False, "error": err}

        skill_name = meta["name"]
        cats = meta.get("categories", [])

        # Must have at least one real category
        if not cats:
            return {"success": False, "error": "Category is required. Provide a meaningful category (e.g. 'devops', 'software-development', 'media')."}

        # Store under category directory: skills/<category>/<name>.md
        primary_cat = cats[0]
        target = f"skills/{primary_cat}/{skill_name}.md"
        vault_file = Path(self.vault_path) / target
        if vault_file.exists():
            return {"success": False, "error": f"Skill '{skill_name}' already exists at {target}. Use action='edit' to update."}

        # Check for duplicates by FTS name match
        existing = self.indexer.get_skill(skill_name)
        if existing:
            return {"success": False, "error": f"Skill '{skill_name}' already exists at {existing['path']}. Use action='edit' to update."}

        ops = VaultOps(self.vault_path)
        ops.write_note(target, meta, body)
        self.indexer.update_index(self.vault_path)
        _generate_hub_notes(self.vault_path)

        # Sync to ~/.hermes/skills/ for compatibility
        self._sync_to_hermes(skill_name, content, primary_cat)

        return {"success": True, "message": f"Skill '{skill_name}' created.", "path": target, "category": primary_cat}

    def _edit(self, name: str, content: str) -> dict:
        skill_data = self.indexer.get_skill(name)
        if skill_data is None:
            return {"success": False, "error": f"Skill '{name}' not found."}

        if not content.strip():
            return {"success": False, "error": "content is required for 'edit'."}

        meta, body, err = self._normalize_meta(content, mode="edit")
        if err:
            return {"success": False, "error": err}

        target = skill_data["path"]
        ops = VaultOps(self.vault_path)
        ops.write_note(target, meta, body)
        self.indexer.update_index(self.vault_path)
        _generate_hub_notes(self.vault_path)

        # Sync to ~/.hermes/skills/
        cats = meta.get("categories", [])
        cat = cats[0] if cats else ""
        self._sync_to_hermes(name, content, cat)

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

    def enrich_skill(self, name: str) -> bool:
        """Re-read a skill, enrich its metadata via LLM, write back.

        Returns True if metadata was updated, False otherwise.
        """
        if self._llm_enricher is None:
            return False

        skill_data = self.indexer.get_skill(name)
        if skill_data is None:
            return False

        ops = VaultOps(self.vault_path)
        note = ops.read_note(skill_data["path"])
        meta = dict(note["metadata"])
        body = note["content"]

        try:
            enriched = self._llm_enricher(meta, body, mode="index")
        except Exception:
            logger.debug("LLM enricher failed for '%s'", name, exc_info=True)
            return False

        if enriched == meta:
            return False

        ops.write_note(skill_data["path"], enriched, body)
        return True

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
