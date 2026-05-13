from dataclasses import dataclass, field


@dataclass
class Skill:
    name: str
    path: str
    categories: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    triggers: list[str] = field(default_factory=list)
    summary: str = ""
    content: str = ""


@dataclass
class Category:
    name: str
    description: str = ""
    skill_count: int = 0
