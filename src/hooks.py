from .indexer import SkillIndexer
from .vault_ops import VaultOps

SKILL_INSTALL_GUIDANCE = (
    "After completing a complex task (5+ tool calls), fixing a tricky error, "
    "or discovering a non-trivial workflow, save the approach as a "
    "skill with skill_install so you can reuse it next time.\n"
    "When using a skill and finding it outdated, incomplete, or wrong, "
    "update it immediately with skill_install(action='edit') — don't wait to be asked. "
    "Skills that aren't maintained become liabilities."
)

DEFAULT_DISCOVERY = f"""\
<skill_discovery>
可用 MCP 工具发现和加载技能：
- skill_lookup(query, category?, top_k?): 搜索相关技能
- skill_load(name): 加载技能完整内容
- skill_categories(): 列出所有分类
- skill_install(action, name, content?, category?): 创建/编辑/删除技能
优先根据分类定位，再调用 skill_lookup 精确查找。

{SKILL_INSTALL_GUIDANCE}
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
