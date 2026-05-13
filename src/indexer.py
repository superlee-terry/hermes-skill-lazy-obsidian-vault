import json
import sqlite3
from pathlib import Path
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
                summary TEXT DEFAULT '',
                mtime REAL DEFAULT 0
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
                "INSERT INTO skills (name, path, categories, tags, triggers, summary, mtime) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (skill.name, skill.path,
                 json.dumps(skill.categories, ensure_ascii=False),
                 json.dumps(skill.tags, ensure_ascii=False),
                 json.dumps(skill.triggers, ensure_ascii=False),
                 skill.summary, 0),
            )
            count += 1
        self.conn.commit()
        return count

    def update_index(self, vault_path: str) -> dict:
        """Incremental update: add new/modified skills, remove deleted ones.

        Returns {"added": int, "updated": int, "removed": int}.
        """
        from .vault_ops import VaultOps
        ops = VaultOps(vault_path)
        vault_skills = ops.scan_skills()

        # Map current vault state: name → (Skill, file_mtime)
        vault_map: dict[str, tuple[Skill, float]] = {}
        skills_dir = Path(vault_path) / "skills"
        if skills_dir.exists():
            for md_file in skills_dir.rglob("*.md"):
                mtime = md_file.stat().st_mtime
                name = md_file.stem
                for s in vault_skills:
                    if s.name == name:
                        vault_map[name] = (s, mtime)
                        break

        # Map current index state: name → mtime
        index_map: dict[str, float] = {}
        for row in self.conn.execute("SELECT name, mtime FROM skills").fetchall():
            index_map[row[0]] = row[1]

        stats = {"added": 0, "updated": 0, "removed": 0}

        # Remove skills no longer in vault
        for name in index_map:
            if name not in vault_map:
                self.conn.execute("DELETE FROM skills WHERE name = ?", (name,))
                stats["removed"] += 1

        # Add new or update modified
        for name, (skill, mtime) in vault_map.items():
            if name not in index_map:
                self.conn.execute(
                    "INSERT INTO skills (name, path, categories, tags, triggers, summary, mtime) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (skill.name, skill.path,
                     json.dumps(skill.categories, ensure_ascii=False),
                     json.dumps(skill.tags, ensure_ascii=False),
                     json.dumps(skill.triggers, ensure_ascii=False),
                     skill.summary, mtime),
                )
                stats["added"] += 1
            elif mtime > index_map[name] and index_map[name] > 0:
                self.conn.execute(
                    "UPDATE skills SET path=?, categories=?, tags=?, triggers=?, summary=?, mtime=? "
                    "WHERE name=?",
                    (skill.path,
                     json.dumps(skill.categories, ensure_ascii=False),
                     json.dumps(skill.tags, ensure_ascii=False),
                     json.dumps(skill.triggers, ensure_ascii=False),
                     skill.summary, mtime, name),
                )
                stats["updated"] += 1
            elif index_map[name] == 0:
                # Initial sync: just update mtime without counting as modified
                self.conn.execute(
                    "UPDATE skills SET mtime=? WHERE name=?", (mtime, name)
                )

        self.conn.commit()
        return stats

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
