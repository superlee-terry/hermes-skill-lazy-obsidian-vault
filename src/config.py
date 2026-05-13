import yaml
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class VaultConfig:
    vault_path: str = ""
    db_path: str = "skill_index.db"
    always_load: list[str] = field(default_factory=list)
    include_category_index: bool = True
    discovery_prompt: str = ""

    @classmethod
    def from_file(cls, path: str) -> "VaultConfig":
        p = Path(path)
        if not p.exists():
            return cls()
        with open(p, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        vault_cfg = data.get("vault", {})
        hermes_cfg = data.get("hermes", {})
        return cls(
            vault_path=vault_cfg.get("path", ""),
            db_path=vault_cfg.get("db_path", "skill_index.db"),
            always_load=hermes_cfg.get("always_load", []),
            include_category_index=hermes_cfg.get("include_category_index", True),
            discovery_prompt=hermes_cfg.get("discovery_prompt", ""),
        )
