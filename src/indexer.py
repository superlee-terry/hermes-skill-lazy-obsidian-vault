import json
import sqlite3
from .models import Skill


class SkillIndexer:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self._init_schema()

    def _init_schema(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS skills (
                name TEXT PRIMARY KEY,
                path TEXT NOT NULL,
                categories TEXT DEFAULT '[]',
                tags TEXT DEFAULT '[]',
                triggers TEXT DEFAULT '[]',
                summary TEXT DEFAULT ''
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS skills_fts USING fts5(
                name, summary, triggers,
                content='skills', content_rowid='rowid'
            );

            CREATE TRIGGER IF NOT EXISTS skills_ai AFTER INSERT ON skills BEGIN
                INSERT INTO skills_fts(rowid, name, summary, triggers)
                VALUES (new.rowid, new.name, new.summary, new.triggers);
            END;

            CREATE TRIGGER IF NOT EXISTS skills_ad AFTER DELETE ON skills BEGIN
                INSERT INTO skills_fts(skills_fts, rowid, name, summary, triggers)
                VALUES('delete', old.rowid, old.name, old.summary, old.triggers);
            END;

            CREATE TRIGGER IF NOT EXISTS skills_au AFTER UPDATE ON skills BEGIN
                INSERT INTO skills_fts(skills_fts, rowid, name, summary, triggers)
                VALUES('delete', old.rowid, old.name, old.summary, old.triggers);
                INSERT INTO skills_fts(rowid, name, summary, triggers)
                VALUES (new.rowid, new.name, new.summary, new.triggers);
            END;
        """)
        self.conn.commit()

    def build_index(self, skills: list[Skill]) -> int:
        self.conn.execute("DELETE FROM skills")
        self.conn.commit()
        count = 0
        for skill in skills:
            self.conn.execute(
                "INSERT INTO skills (name, path, categories, tags, triggers, summary) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (skill.name, skill.path,
                 json.dumps(skill.categories, ensure_ascii=False),
                 json.dumps(skill.tags, ensure_ascii=False),
                 json.dumps(skill.triggers, ensure_ascii=False),
                 skill.summary),
            )
            count += 1
        self.conn.commit()
        return count

    def get_skill(self, name: str) -> dict | None:
        row = self.conn.execute(
            "SELECT name, path, categories, tags, triggers, summary FROM skills WHERE name = ?",
            (name,),
        ).fetchone()
        if row is None:
            return None
        return {
            "name": row[0], "path": row[1],
            "categories": row[2], "tags": row[3],
            "triggers": row[4], "summary": row[5],
        }

    def list_categories(self) -> list[dict]:
        rows = self.conn.execute("SELECT categories FROM skills").fetchall()
        cat_counts: dict[str, int] = {}
        for (cats_json,) in rows:
            for cat in json.loads(cats_json):
                cat_counts[cat] = cat_counts.get(cat, 0) + 1
        return [{"name": k, "skill_count": v} for k, v in sorted(cat_counts.items())]

    def close(self):
        self.conn.close()
