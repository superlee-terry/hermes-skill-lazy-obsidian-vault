import json
import logging
from pathlib import Path
from typing import Any

from .config import VaultConfig
from .indexer import SkillIndexer
from .tools import SkillTools
from .hooks import build_session_context
from .sync import sync_skill_to_vault, remove_skill_from_vault

logger = logging.getLogger(__name__)

# --- Schemas (OpenAI function-calling format) ---

SKILL_LOOKUP_SCHEMA = {
    "name": "skill_lookup",
    "description": (
        "Search the skill vault for relevant skills by query. "
        "Returns name, categories, summary, and relevance score. "
        "Use this first to find skills, then call skill_load to get full content."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query — keywords, trigger phrases, or natural language description of what you need.",
            },
            "category": {
                "type": "string",
                "description": "Optional category filter to narrow results.",
            },
            "top_k": {
                "type": "integer",
                "description": "Max number of results to return (default 3).",
            },
        },
        "required": ["query"],
    },
}

SKILL_LOAD_SCHEMA = {
    "name": "skill_load",
    "description": (
        "Load the full markdown content of a skill by name. "
        "Use skill_lookup first to find the right skill name."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Exact skill name (as returned by skill_lookup).",
            },
        },
        "required": ["name"],
    },
}

SKILL_CATEGORIES_SCHEMA = {
    "name": "skill_categories",
    "description": "List all skill categories with their skill counts.",
    "parameters": {
        "type": "object",
        "properties": {},
    },
}

SKILL_INSTALL_SCHEMA = {
    "name": "skill_install",
    "description": (
        "Create, edit, or delete a skill in the skill vault. "
        "Skills are reusable procedural knowledge for recurring task types. "
        "The skill is stored in the vault and indexed for search via skill_lookup.\n\n"
        "Actions:\n"
        "  create — Create a new skill (content = SKILL.md with YAML frontmatter + body)\n"
        "  edit   — Replace the full content of an existing skill\n"
        "  delete — Remove a skill from the vault\n\n"
        "Requirements for 'create':\n"
        "  - category is REQUIRED (e.g. 'devops', 'software-development', 'media')\n"
        "  - Frontmatter must include 'name' and 'description' (>= 10 chars)\n"
        "  - Skill name must be unique across the vault\n"
        "  - Skill will be stored under skills/<category>/<name>.md\n\n"
        "Create when: complex task succeeded, user-corrected approach worked, "
        "non-trivial workflow discovered, or user asks to remember a procedure.\n"
        "Update when: instructions are stale/wrong, missing steps found during use.\n"
        "Confirm with user before creating or deleting."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create", "edit", "delete"],
                "description": "The action to perform.",
            },
            "name": {
                "type": "string",
                "description": "Skill name (lowercase, hyphens/underscores). Must match an existing skill for edit/delete.",
            },
            "content": {
                "type": "string",
                "description": (
                    "Full SKILL.md content (YAML frontmatter + markdown body). "
                    "Required for 'create' and 'edit'. Frontmatter must include 'name' and 'description'."
                ),
            },
            "category": {
                "type": "string",
                "description": (
                    "Category for organizing the skill. REQUIRED for 'create'. "
                    "Examples: 'devops', 'software-development', 'media', 'game-development', "
                    "'testing', 'data-science', 'research', 'creative'. "
                    "Use existing categories when possible — call skill_categories() to list them."
                ),
            },
        },
        "required": ["action", "name"],
    },
}

# --- Handlers ---

_tools_instance: SkillTools | None = None
_config: VaultConfig | None = None
_indexer: SkillIndexer | None = None


def _get_tools(config_path: str) -> tuple[SkillTools, VaultConfig, SkillIndexer]:
    global _tools_instance, _config, _indexer
    if _tools_instance is not None:
        return _tools_instance, _config, _indexer

    config = VaultConfig.from_file(config_path)
    plugin_dir = Path(config_path).parent

    if not config.vault_path:
        config.vault_path = str(plugin_dir / "vault")

    db_path = Path(config.db_path)
    if not db_path.is_absolute():
        db_path = plugin_dir / config.db_path

    indexer = SkillIndexer(str(db_path))
    _tools_instance = SkillTools(config.vault_path, indexer)
    _config = config
    _indexer = indexer
    return _tools_instance, _config, _indexer


def _handle_skill_lookup(args: dict, **_kw) -> str:
    tools, config, indexer = _get_tools(
        str(Path(__file__).parent.parent / "config.yaml")
    )
    query = args.get("query", "")
    category = args.get("category") or None
    top_k = args.get("top_k", 3)
    results = tools.skill_lookup(query, category=category, top_k=top_k)
    return json.dumps({"success": True, "results": results}, ensure_ascii=False)


def _handle_skill_load(args: dict, **_kw) -> str:
    tools, config, indexer = _get_tools(
        str(Path(__file__).parent.parent / "config.yaml")
    )
    name = args.get("name", "")
    content = tools.skill_load(name)
    if content.startswith("Error:"):
        return json.dumps({"success": False, "error": content}, ensure_ascii=False)
    return json.dumps({"success": True, "name": name, "content": content}, ensure_ascii=False)


def _handle_skill_categories(args: dict, **_kw) -> str:
    tools, config, indexer = _get_tools(
        str(Path(__file__).parent.parent / "config.yaml")
    )
    categories = tools.skill_categories()
    return json.dumps({"success": True, "categories": categories}, ensure_ascii=False)


def _handle_skill_install(args: dict, **_kw) -> str:
    tools, config, indexer = _get_tools(
        str(Path(__file__).parent.parent / "config.yaml")
    )
    result = tools.skill_install(
        action=args.get("action", ""),
        name=args.get("name", ""),
        content=args.get("content", ""),
        category=args.get("category", ""),
        description=args.get("description", ""),
    )
    return json.dumps(result, ensure_ascii=False)


def _check_vault_ready() -> bool:
    try:
        tools, _, _ = _get_tools(str(Path(__file__).parent.parent / "config.yaml"))
        return True
    except Exception:
        return False


def _find_skill_md(name: str) -> str | None:
    """Find SKILL.md path in ~/.hermes/skills/ by skill name."""
    from pathlib import Path
    home = Path.home() / ".hermes" / "skills"
    if not home.exists():
        return None
    for md in home.rglob("SKILL.md"):
        if md.parent.name == name:
            return str(md)
    return None


def _on_post_tool_call(
    tool_name: str = "",
    args: dict | None = None,
    result: Any = None,
    task_id: str = "",
    session_id: str = "",
    tool_call_id: str = "",
    duration_ms: int = 0,
    **_: Any,
) -> None:
    """Sync vault when skill_manage creates/edits/deletes a skill."""
    if tool_name != "skill_manage":
        return
    if not isinstance(args, dict):
        return

    # Check if the tool call succeeded
    if isinstance(result, str):
        try:
            parsed = json.loads(result)
            if not parsed.get("success"):
                return
        except (json.JSONDecodeError, TypeError):
            return

    action = args.get("action", "")
    name = args.get("name", "")
    if not name:
        return

    tools, config, indexer = _get_tools(str(Path(__file__).parent.parent / "config.yaml"))
    vault_path = config.vault_path

    if action == "delete":
        if remove_skill_from_vault(name, vault_path):
            indexer.update_index(vault_path)
            logger.info("obsidian-skill-vault: synced delete for '%s'", name)
    elif action in ("create", "edit", "patch", "write_file"):
        skill_md = _find_skill_md(name)
        if skill_md:
            if sync_skill_to_vault(skill_md, vault_path):
                indexer.update_index(vault_path)
                logger.info("obsidian-skill-vault: synced %s for '%s'", action, name)
    elif action == "remove_file":
        # Supporting file removed — re-sync the whole skill
        skill_md = _find_skill_md(name)
        if skill_md:
            if sync_skill_to_vault(skill_md, vault_path):
                indexer.update_index(vault_path)
                logger.info("obsidian-skill-vault: synced remove_file for '%s'", name)


def register(ctx) -> None:
    """Hermes Plugin entry point — called by PluginManager."""
    config_path = str(Path(__file__).parent.parent / "config.yaml")
    tools, config, indexer = _get_tools(config_path)

    _TOOLS = (
        ("skill_lookup", SKILL_LOOKUP_SCHEMA, _handle_skill_lookup, "🔍"),
        ("skill_load", SKILL_LOAD_SCHEMA, _handle_skill_load, "📖"),
        ("skill_categories", SKILL_CATEGORIES_SCHEMA, _handle_skill_categories, "📂"),
        ("skill_install", SKILL_INSTALL_SCHEMA, _handle_skill_install, "📝"),
    )

    for name, schema, handler, emoji in _TOOLS:
        ctx.register_tool(
            name=name,
            toolset="skill-vault",
            schema=schema,
            handler=handler,
            check_fn=_check_vault_ready,
            emoji=emoji,
        )

    def _on_session_start(**kwargs):
        """Initialize session-scoped state and sync vault index."""
        logger.info("obsidian-skill-vault: session started (id=%s)", kwargs.get("session_id"))
        try:
            stats = indexer.update_index(config.vault_path)
            if stats["added"] or stats["updated"] or stats["removed"]:
                logger.info("obsidian-skill-vault: index sync +%d ~%d -%d",
                            stats["added"], stats["updated"], stats["removed"])
        except Exception:
            logger.debug("obsidian-skill-vault: index sync failed", exc_info=True)

    def _on_pre_llm_call(**kwargs):
        """Inject skill category index into the user message context."""
        context_text = build_session_context(
            config.vault_path,
            indexer,
            always_load=config.always_load,
            discovery_prompt=config.discovery_prompt,
        )
        return {"context": context_text}

    ctx.register_hook("on_session_start", _on_session_start)
    ctx.register_hook("pre_llm_call", _on_pre_llm_call)
    ctx.register_hook("post_tool_call", _on_post_tool_call)

    logger.info("obsidian-skill-vault plugin registered (vault=%s)", config.vault_path)
