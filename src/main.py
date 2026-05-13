import json
from pathlib import Path
from mcp.server.fastmcp import FastMCP
from .config import VaultConfig
from .indexer import SkillIndexer
from .tools import SkillTools

mcp = FastMCP("obsidian-skill-vault")

_tools: SkillTools | None = None
_indexer: SkillIndexer | None = None


def _init(vault_path: str, db_path: str):
    global _tools, _indexer
    if _tools is not None:
        return
    _indexer = SkillIndexer(db_path)
    _tools = SkillTools(vault_path, _indexer)


@mcp.tool(title="Search Skills")
def skill_lookup(query: str, category: str = "", top_k: int = 3) -> str:
    """Search the skill vault for skills matching the query.

    Args:
        query: Natural language search query (e.g. "TDD", "debug", "写文档")
        category: Optional category filter (e.g. "software-development", "research")
        top_k: Maximum number of results to return (default 3)

    Returns:
        JSON array of matching skills with name, categories, summary, score, match_type
    """
    cat = category if category else None
    results = _tools.skill_lookup(query, category=cat, top_k=top_k)
    return json.dumps(results, ensure_ascii=False, indent=2)


@mcp.tool(title="Load Skill")
def skill_load(name: str) -> str:
    """Load the full content of a skill by name.

    Args:
        name: Exact skill name (as returned by skill_lookup)

    Returns:
        Full skill content as markdown text
    """
    return _tools.skill_load(name)


@mcp.tool(title="List Categories")
def skill_categories() -> str:
    """List all skill categories and their skill counts.

    Returns:
        JSON array of categories with name and skill_count
    """
    cats = _tools.skill_categories()
    return json.dumps(cats, ensure_ascii=False, indent=2)


def serve(vault_path: str, db_path: str):
    _init(vault_path, db_path)
    mcp.run(transport="stdio")


def main():
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="Obsidian Skill Vault MCP Server")
    parser.add_argument("--vault", required=True, help="Path to Obsidian vault")
    parser.add_argument("--db", default="skill_index.db", help="SQLite index path")
    args = parser.parse_args()

    db = args.db
    if not Path(db).is_absolute():
        db = str(Path(args.vault).parent / db)

    serve(args.vault, db)


if __name__ == "__main__":
    main()
