import argparse
import sys
from pathlib import Path
from .config import VaultConfig
from .vault_ops import VaultOps
from .indexer import SkillIndexer
from .migrate import migrate_skills


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="obsidian-skill-vault",
        description="Obsidian Vault skill management for Hermes Agent",
    )
    sub = parser.add_subparsers(dest="command")

    p_migrate = sub.add_parser("migrate", help="Migrate skills from Hermes skills dir to vault")
    p_migrate.add_argument("--source", required=True, help="Source Hermes skills directory")
    p_migrate.add_argument("--vault", required=True, help="Target Obsidian vault path")

    p_index = sub.add_parser("index", help="Build/rebuild search index")
    p_index.add_argument("--vault", required=True, help="Obsidian vault path")
    p_index.add_argument("--db", default="skill_index.db", help="SQLite database path")

    p_doctor = sub.add_parser("doctor", help="Validate vault health")
    p_doctor.add_argument("--vault", required=True, help="Obsidian vault path")

    p_serve = sub.add_parser("serve", help="Run as MCP Server")
    p_serve.add_argument("--vault", required=True, help="Obsidian vault path")
    p_serve.add_argument("--db", default="skill_index.db", help="SQLite database path")

    args = parser.parse_args(argv)

    if args.command == "migrate":
        count = migrate_skills(args.source, args.vault)
        print(f"Migrated {count} skills to {args.vault}")

    elif args.command == "index":
        ops = VaultOps(args.vault)
        skills = ops.scan_skills()
        indexer = SkillIndexer(args.db)
        count = indexer.build_index(skills)
        indexer.close()
        print(f"Indexed {count} skills to {args.db}")

    elif args.command == "doctor":
        ops = VaultOps(args.vault)
        skills = ops.scan_skills()
        issues = []
        for s in skills:
            if not s.categories:
                issues.append(f"  WARNING: {s.name} has no categories")
            if not s.triggers:
                issues.append(f"  WARNING: {s.name} has no triggers")
            if not s.summary:
                issues.append(f"  WARNING: {s.name} has no summary")
        if issues:
            print(f"Found {len(issues)} issues:")
            for issue in issues:
                print(issue)
        else:
            print(f"All {len(skills)} skills are healthy")

    elif args.command == "serve":
        from .main import serve
        db = args.db
        if not Path(db).is_absolute():
            db = str(Path(args.vault).parent / db)
        serve(args.vault, db)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
