import json
import logging
from pathlib import Path

from .config import VaultConfig
from .indexer import SkillIndexer
from .tools import SkillTools
from .hooks import build_session_context

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


def _check_vault_ready() -> bool:
    try:
        tools, _, _ = _get_tools(str(Path(__file__).parent.parent / "config.yaml"))
        return True
    except Exception:
        return False


def register(ctx) -> None:
    """Hermes Plugin entry point — called by PluginManager."""
    config_path = str(Path(__file__).parent.parent / "config.yaml")
    tools, config, indexer = _get_tools(config_path)

    _TOOLS = (
        ("skill_lookup", SKILL_LOOKUP_SCHEMA, _handle_skill_lookup, "🔍"),
        ("skill_load", SKILL_LOAD_SCHEMA, _handle_skill_load, "📖"),
        ("skill_categories", SKILL_CATEGORIES_SCHEMA, _handle_skill_categories, "📂"),
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
        """Initialize session-scoped state (warm caches, etc.)."""
        logger.info("obsidian-skill-vault: session started (id=%s)", kwargs.get("session_id"))

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

    logger.info("obsidian-skill-vault plugin registered (vault=%s)", config.vault_path)
