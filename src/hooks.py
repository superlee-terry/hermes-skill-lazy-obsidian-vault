import json
from pathlib import Path
from .indexer import SkillIndexer
from .vault_ops import VaultOps

# Category Chinese description map
CATEGORY_CN: dict[str, str] = {
    "software-development": "软件开发",
    "devops": "运维部署",
    "media": "媒体视频",
    "game-development": "游戏开发",
    "finance-claw-workspace": "财经数据",
    "testing": "测试质量",
    "social-media": "社交媒体",
    "creative": "创意设计",
    "productivity": "效率工具",
    "research": "研究搜索",
    "data-science": "数据科学",
    "mlops": "机器学习",
    "smart-home": "智能家居",
    "automation": "自动化",
    "apple": "Apple生态",
    "autonomous-ai-agents": "AI Agent",
    "email": "邮件",
    "frontend": "前端开发",
    "gaming": "游戏",
    "github": "GitHub",
    "leisure": "休闲",
    "mcp": "MCP协议",
    "note-taking": "笔记",
    "openclaw-imports": "OpenClaw",
    "project-management": "项目管理",
    "red-teaming": "红队安全",
    "health": "健康",
}

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

    # Category index with Chinese descriptions
    categories = indexer.list_categories()
    if categories:
        # Load custom CN map from vault if available
        custom_cn = {}
        cn_path = Path(vault_path) / "_index" / "_category_cn.json"
        if cn_path.exists():
            try:
                custom_cn = json.loads(cn_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        cn_map = {**CATEGORY_CN, **custom_cn}

        cat_lines = ["<skill_categories>"]
        for cat in categories:
            cn = cn_map.get(cat["name"], "")
            if cn:
                cat_lines.append(f"  {cat['name']}/{cn} ({cat['skill_count']})")
            else:
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
