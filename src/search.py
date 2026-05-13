import json
from .indexer import SkillIndexer


class SkillSearch:
    def __init__(self, indexer: SkillIndexer):
        self.indexer = indexer

    def search(self, query: str, category: str = None, top_k: int = 3) -> list[dict]:
        seen: dict[str, dict] = {}

        # 1. Trigger match — try quoted JSON form first, then bare substring (weight 0.5)
        for pattern in [f'%"{query}"%', f'%{query}%']:
            rows = self.indexer.conn.execute(
                "SELECT name, path, categories, summary FROM skills WHERE triggers LIKE ?",
                (pattern,),
            ).fetchall()
            for row in rows:
                if row[0] not in seen:
                    seen[row[0]] = {
                        "name": row[0], "path": row[1],
                        "categories": json.loads(row[2]),
                        "summary": row[3],
                        "score": 0.5, "match_type": "trigger",
                    }
            if rows:
                break

        # 2. Category filter — if specified, restrict to matching category (weight 0.3)
        if category:
            for pattern in [f'%"{category}"%', f'%{category}%']:
                rows = self.indexer.conn.execute(
                    "SELECT name, path, categories, summary FROM skills WHERE categories LIKE ?",
                    (pattern,),
                ).fetchall()
                if rows:
                    break
            cat_names = {row[0] for row in rows}
            # If category is specified, filter out non-matching results from step 1
            filtered = {}
            for name, result in seen.items():
                if name in cat_names:
                    filtered[name] = result
            # Add new results from category that weren't in trigger matches
            for row in rows:
                if row[0] not in filtered:
                    filtered[row[0]] = {
                        "name": row[0], "path": row[1],
                        "categories": json.loads(row[2]),
                        "summary": row[3],
                        "score": 0.3, "match_type": "category",
                    }
            seen = filtered

        # 3. FTS full-text search (fallback)
        try:
            fts_query = query.replace('"', '""')
            rows = self.indexer.conn.execute(
                "SELECT s.name, s.path, s.categories, s.summary, f.rank "
                "FROM skills_fts f JOIN skills s ON f.rowid = s.rowid "
                "WHERE skills_fts MATCH ? ORDER BY f.rank LIMIT ?",
                (fts_query, top_k),
            ).fetchall()
            for row in rows:
                if row[0] not in seen:
                    cats = json.loads(row[2])
                    # If category filter is active, skip non-matching FTS results
                    if category and category not in cats:
                        continue
                    seen[row[0]] = {
                        "name": row[0], "path": row[1],
                        "categories": json.loads(row[2]),
                        "summary": row[3],
                        "score": round(0.2 - row[4], 3),
                        "match_type": "fts",
                    }
        except Exception:
            pass

        results = sorted(seen.values(), key=lambda x: x["score"], reverse=True)
        return results[:top_k]
