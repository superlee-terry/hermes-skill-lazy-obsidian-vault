import yaml
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class LlmConfig:
    enabled: bool = True
    enrich_on_create: bool = True
    enrich_on_edit: bool = True
    enrich_on_index: bool = True
    max_enrich_per_session: int = 5
    timeout_seconds: float = 5.0


@dataclass
class VaultConfig:
    vault_path: str = ""
    db_path: str = "skill_index.db"
    always_load: list[str] = field(default_factory=list)
    include_category_index: bool = True
    discovery_prompt: str = ""
    llm: LlmConfig = field(default_factory=LlmConfig)

    @classmethod
    def from_file(cls, path: str) -> "VaultConfig":
        p = Path(path)
        if not p.exists():
            return cls()
        with open(p, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        vault_cfg = data.get("vault", {})
        hermes_cfg = data.get("hermes", {})
        llm_cfg = hermes_cfg.get("llm", {})
        return cls(
            vault_path=vault_cfg.get("path", ""),
            db_path=vault_cfg.get("db_path", "skill_index.db"),
            always_load=hermes_cfg.get("always_load", []),
            include_category_index=hermes_cfg.get("include_category_index", True),
            discovery_prompt=hermes_cfg.get("discovery_prompt", ""),
            llm=LlmConfig(
                enabled=llm_cfg.get("enabled", True),
                enrich_on_create=llm_cfg.get("enrich_on_create", True),
                enrich_on_edit=llm_cfg.get("enrich_on_edit", True),
                enrich_on_index=llm_cfg.get("enrich_on_index", True),
                max_enrich_per_session=llm_cfg.get("max_enrich_per_session", 5),
                timeout_seconds=float(llm_cfg.get("timeout_seconds", 5.0)),
            ),
        )
