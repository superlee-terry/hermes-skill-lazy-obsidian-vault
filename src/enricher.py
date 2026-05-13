"""LLM-based skill metadata enrichment.

Uses Hermes v0.13.0+ ctx.llm to auto-generate summary, triggers,
and category suggestions for skills. Gracefully degrades to no-op
when ctx.llm is unavailable (Hermes < v0.13.0 or LLM fails).
"""

import json
import logging
from typing import Any, Callable

from .config import LlmConfig

logger = logging.getLogger(__name__)

# Module-level state, injected once from register()
_llm: Any = None
_llm_config: LlmConfig = LlmConfig()
_llm_available: bool = True

ENRICH_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {
            "type": "string",
            "description": "1-2 sentence description of what this skill does",
        },
        "triggers": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Short phrases a user might say to indicate they need this skill",
        },
    },
    "required": ["summary", "triggers"],
}

ENRICH_INSTRUCTIONS = (
    "You are a skill metadata generator for an AI assistant's skill vault. "
    "Given the markdown body of a skill document, generate concise metadata.\n\n"
    "Requirements:\n"
    "- summary: 1-2 sentences (max 200 chars) describing what the skill does and when to use it. "
    "Write in the same language as the skill body.\n"
    "- triggers: 5-10 short phrases (2-60 chars each) that a user might say or type "
    "to indicate they need this skill. Include both English and Chinese variants if applicable.\n\n"
    "Do not invent information not present in the skill content. Be specific, not generic."
)


def configure(llm_ref: Any, llm_config: LlmConfig) -> None:
    """Called once from register() to inject ctx.llm and config."""
    global _llm, _llm_config, _llm_available
    _llm = llm_ref
    _llm_config = llm_config
    _llm_available = True
    if _llm is None:
        logger.info("obsidian-skill-vault: ctx.llm not available, LLM enrichment disabled")
    elif not _llm_config.enabled:
        logger.info("obsidian-skill-vault: LLM enrichment disabled by config")
    else:
        logger.info("obsidian-skill-vault: LLM enrichment enabled")


def enrich_meta(meta: dict, body: str, mode: str = "create") -> dict:
    """Enrich skill metadata via LLM. Returns original meta on any failure.

    Args:
        meta: Current frontmatter metadata dict.
        body: Skill markdown body.
        mode: "create", "edit", or "index".
    """
    if _llm is None or not _llm_available or not _llm_config.enabled:
        return meta

    if mode == "create" and not _llm_config.enrich_on_create:
        return meta
    if mode == "edit" and not _llm_config.enrich_on_edit:
        return meta
    if mode == "index" and not _llm_config.enrich_on_index:
        return meta

    if not _needs_enrichment(meta, mode):
        return meta

    result = _call_llm_structured(body, meta)
    if result is None:
        return meta

    # Merge: only overwrite fields that need improvement
    enriched = dict(meta)

    new_summary = result.get("summary", "").strip()
    if new_summary and _summary_needs_replacement(meta.get("summary", "")):
        enriched["summary"] = new_summary[:200]

    new_triggers = result.get("triggers", [])
    if new_triggers and isinstance(new_triggers, list):
        existing = meta.get("triggers", [])
        merged = existing + [t for t in new_triggers if t not in existing]
        enriched["triggers"] = list(dict.fromkeys(merged))

    return enriched


def _summary_needs_replacement(current: str) -> bool:
    """True if the current summary is empty, too short, or a verbatim truncation."""
    if not current or not current.strip():
        return True
    if len(current) < 20:
        return True
    return False


def _needs_enrichment(meta: dict, mode: str) -> bool:
    """Check if metadata would benefit from LLM enrichment."""
    summary = meta.get("summary", "")
    triggers = meta.get("triggers", [])

    if not summary or not summary.strip() or len(summary) < 20:
        return True
    if not triggers or len(triggers) < 3:
        return True
    return False


def _call_llm_structured(body: str, meta: dict) -> dict | None:
    """Call ctx.llm.complete_structured with enrichment prompt.

    Returns parsed dict or None on any failure.
    """
    global _llm_available
    if _llm is None:
        return None

    name = meta.get("name", "unknown")
    desc = meta.get("description", "")
    input_text = f"Skill name: {name}\n"
    if desc:
        input_text += f"Description: {desc}\n"
    input_text += f"\n--- Skill content ---\n{body[:3000]}"

    try:
        result = _llm.complete_structured(
            instructions=ENRICH_INSTRUCTIONS,
            input=[{"type": "text", "text": input_text}],
            json_schema=ENRICH_SCHEMA,
            schema_name="skill_enrichment",
            max_tokens=300,
            temperature=0.3,
            timeout=_llm_config.timeout_seconds,
            purpose="skill_metadata_enrichment",
        )

        parsed = None
        if hasattr(result, "parsed") and result.parsed:
            parsed = result.parsed
        elif hasattr(result, "text") and result.text:
            try:
                parsed = json.loads(result.text)
            except (json.JSONDecodeError, TypeError):
                pass

        if not parsed or not isinstance(parsed, dict):
            logger.debug("obsidian-skill-vault: LLM enrichment returned no valid data for '%s'", name)
            return None

        if not parsed.get("summary") or not parsed.get("triggers"):
            logger.debug("obsidian-skill-vault: LLM enrichment missing required fields for '%s'", name)
            return None

        return parsed

    except Exception:
        _llm_available = False
        logger.debug("obsidian-skill-vault: LLM enrichment failed, disabling for session", exc_info=True)
        return None


def enrich_newly_indexed(tools: Any, config: Any, index_stats: dict) -> int:
    """Batch-enrich skills missing metadata after index update.

    Called from on_session_start. Returns count of enriched skills.
    """
    if _llm is None or not _llm_available or not _llm_config.enabled:
        return 0
    if not _llm_config.enrich_on_index:
        return 0

    added = index_stats.get("added", 0)
    updated = index_stats.get("updated", 0)
    if not added and not updated:
        return 0

    indexer = tools.indexer
    if not hasattr(indexer, "get_skills_needing_enrichment"):
        # Fallback: get all skills and filter
        return _enrich_from_scan(tools, config)

    candidates = indexer.get_skills_needing_enrichment(limit=_llm_config.max_enrich_per_session)
    count = 0
    for skill in candidates:
        try:
            if tools.enrich_skill(skill["name"]):
                count += 1
                logger.debug("obsidian-skill-vault: enriched '%s' during index sync", skill["name"])
        except Exception:
            logger.debug("obsidian-skill-vault: failed to enrich '%s'", skill.get("name", "?"), exc_info=True)
            continue
        if count >= _llm_config.max_enrich_per_session:
            break

    if count:
        logger.info("obsidian-skill-vault: enriched %d skills during index sync", count)
    return count


def _enrich_from_scan(tools: Any, config: Any) -> int:
    """Fallback: scan all indexed skills and enrich those with weak metadata."""
    from .vault_ops import VaultOps

    indexer = tools.indexer
    vault_path = tools.vault_path
    ops = VaultOps(vault_path)
    count = 0

    try:
        # Get all skills from index
        rows = indexer._conn.execute(
            "SELECT name, path, summary, triggers FROM skills ORDER BY mtime ASC"
        ).fetchall()
    except Exception:
        return 0

    for row in rows:
        name, path, summary, triggers_json = row
        try:
            triggers = json.loads(triggers_json) if triggers_json else []
        except (json.JSONDecodeError, TypeError):
            triggers = []

        if not _needs_enrichment({"summary": summary or "", "triggers": triggers}, "index"):
            continue

        try:
            note = ops.read_note(path)
            meta = dict(note["metadata"])
            body = note["content"]
            enriched = enrich_meta(meta, body, mode="index")
            if enriched != meta:
                ops.write_note(path, enriched, body)
                count += 1
                logger.debug("obsidian-skill-vault: enriched '%s' via scan", name)
        except Exception:
            logger.debug("obsidian-skill-vault: failed to enrich '%s' via scan", name, exc_info=True)
            continue

        if count >= _llm_config.max_enrich_per_session:
            break

    if count:
        indexer.update_index(vault_path)
        logger.info("obsidian-skill-vault: enriched %d skills via scan", count)
    return count
