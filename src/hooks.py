from .indexer import SkillIndexer
from .vault_ops import VaultOps

DEFAULT_DISCOVERY = """\
<skill_discovery>
可用 MCP 工具发现和加载技能：
- skill_lookup(query, category?, top_k?): 搜索相关技能
- skill_load(name): 加载技能完整内容
- skill_categories(): 列出所有分类
优先根据分类定位，再调用 skill_lookup 精确查找。
</skill_discovery>"""


def build_session_context(
    vault_path: str,
    indexer: SkillIndexer,
    always_load: list[str] | None = None,
    discovery_prompt: str = "",
) -> str:
    parts: list[str] = []

    # Category index
    categories = indexer.list_categories()
    if categories:
        cat_lines = ["<skill_categories>"]
        for cat in categories:
            cat_lines.append(f"  {cat['name']} ({cat['skill_count']})")
        cat_lines.append("</skill_categories>")
        parts.append("\n".join(cat_lines))

    # Always-load skills
    if always_load:
        ops = VaultOps(vault_path)
        for name in always_load:
            skill_data = indexer.get_skill(name)
            if skill_data:
                note = ops.read_note(skill_data["path"])
                parts.append(f'<skill name="{name}">\n{note["content"]}\n</skill>')

    # Discovery prompt
    parts.append(discovery_prompt or DEFAULT_DISCOVERY)

    return "\n\n".join(parts)
