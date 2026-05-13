from pathlib import Path
from .config import VaultConfig
from .indexer import SkillIndexer
from .tools import SkillTools
from .hooks import build_session_context


def register(ctx):
    """Hermes Plugin entry point."""
    plugin_dir = Path(__file__).parent
    config_path = plugin_dir.parent / "config.yaml"
    config = VaultConfig.from_file(str(config_path))

    if not config.vault_path:
        config.vault_path = str(plugin_dir.parent / "vault")

    db_path = Path(config.db_path)
    if not db_path.is_absolute():
        db_path = plugin_dir.parent / config.db_path

    indexer = SkillIndexer(str(db_path))
    tools = SkillTools(config.vault_path, indexer)

    ctx.register_tool("skill_lookup", tools.skill_lookup)
    ctx.register_tool("skill_load", tools.skill_load)
    ctx.register_tool("skill_categories", tools.skill_categories)

    def on_session_start(**kwargs):
        return {
            "context": build_session_context(
                config.vault_path,
                indexer,
                always_load=config.always_load,
                discovery_prompt=config.discovery_prompt,
            )
        }

    ctx.register_hook("on_session_start", on_session_start)
