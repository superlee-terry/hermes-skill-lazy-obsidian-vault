from .indexer import SkillIndexer
from .vault_ops import VaultOps
from .search import SkillSearch


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
