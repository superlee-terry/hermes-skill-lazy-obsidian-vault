import frontmatter
from pathlib import Path
from .models import Skill


class VaultOps:
    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        self.skills_dir = self.vault_path / "skills"

    def read_note(self, path: str) -> dict:
        full_path = self.vault_path / path
        if not full_path.exists():
            raise FileNotFoundError(f"Note not found: {path}")
        with open(full_path, "r", encoding="utf-8") as f:
            post = frontmatter.load(f)
        return {"metadata": post.metadata, "content": post.content}

    def write_note(self, path: str, metadata: dict, content: str) -> None:
        full_path = self.vault_path / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        post = frontmatter.Post(content, **metadata)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(frontmatter.dumps(post))

    def scan_skills(self) -> list[Skill]:
        skills = []
        if not self.skills_dir.exists():
            return skills
        for md_file in sorted(self.skills_dir.rglob("*.md")):
            rel_path = str(md_file.relative_to(self.vault_path))
            with open(md_file, "r", encoding="utf-8") as f:
                post = frontmatter.load(f)
            meta = post.metadata
            skills.append(Skill(
                name=meta.get("name", md_file.stem),
                path=rel_path,
                categories=meta.get("categories", []),
                tags=meta.get("tags", []),
                triggers=meta.get("triggers", []),
                summary=meta.get("summary", ""),
                content=post.content,
            ))
        return skills

    def resolve_wikilink(self, name: str) -> str | None:
        if not self.vault_path.exists():
            return None
        for md_file in self.vault_path.rglob("*.md"):
            if md_file.stem == name:
                return str(md_file.relative_to(self.vault_path))
        return None
