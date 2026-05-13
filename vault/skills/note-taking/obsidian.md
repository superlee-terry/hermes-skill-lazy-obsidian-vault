---
categories:
- note-taking
description: Read, search, and create notes in the Obsidian vault.
name: obsidian
summary: Read, search, and create notes in the Obsidian vault.
triggers: []
---

# Obsidian Vault

**Location:** Set via `OBSIDIAN_VAULT_PATH` environment variable (e.g. in `~/.hermes/.env`).

If unset, defaults to `~/Documents/Obsidian Vault`.

Note: Vault paths may contain spaces - always quote them.

**Troubleshooting Vault Location:**
If the default path (`~/Documents/Obsidian Vault`) is incorrect or missing:
1. Check env: `echo $OBSIDIAN_VAULT_PATH`
2. Check user config: `cat /home/superlee/.config/obsidian/obsidian.json`
3. Search disk: `find / -name ".obsidian" -type d 2>/dev/null | head -5`
4. Common custom locations: `/mnt/data/Obsidian/<VaultName>` or `~/Obsidian/<VaultName>`

## Read a note

```bash
VAULT="${OBSIDIAN_VAULT_PATH:-$HOME/Documents/Obsidian Vault}"
cat "$VAULT/Note Name.md"
```

## List notes

```bash
VAULT="${OBSIDIAN_VAULT_PATH:-$HOME/Documents/Obsidian Vault}"

# All notes
find "$VAULT" -name "*.md" -type f

# In a specific folder
ls "$VAULT/Subfolder/"
```

## Search (Recommended: ripgrep)

```bash
VAULT="${OBSIDIAN_VAULT_PATH:-$HOME/Documents/Obsidian Vault}"

# ripgrep (fastest, handles binary safely)
rg -n --heading=always -H -I -e "keyword" "$VAULT"

# If rg not available, use find + grep as fallback
find "$VAULT" -name "*.md" -type f -exec grep -l "keyword" {} \;
```

**Pitfall:** Obsidian has NO official CLI. Shell commands (rg, find, grep) are the standard approach for querying vault content programmatically.

## File Permissions

**Critical for multi-user environments:** When Python writes files that will be read by Obsidian, set proper permissions to avoid access issues.

```python
def _set_file_permissions(filepath: Path):
    """Ensure files are readable by all users."""
    os.chmod(filepath, 0o644)  # rw-r--r--
    dir_path = filepath.parent
    if dir_path.exists():
        os.chmod(dir_path, 0o755)  # rwxr-xr-x
```

**Pitfall:** Root user writing files without permission adjustment can cause Obsidian to fail reading them.

## Programmatic Access Pattern

For Python applications, use the archiver pattern:

```python
from obsidian.archiver import archiver

# Write notes
archiver.archive_ai_analysis(data)
archiver.archive_news_report(data)

# Query content
results = archiver.query_content("keyword", max_results=20)
files = archiver.search_stock_files("600519")
```

The query module uses ripgrep (rg) with find+grep fallback.

## Create a note

```bash
VAULT="${OBSIDIAN_VAULT_PATH:-$HOME/Documents/Obsidian Vault}"
cat > "$VAULT/New Note.md" << 'ENDNOTE'
# Title

Content here.
ENDNOTE
```

## Append to a note

```bash
VAULT="${OBSIDIAN_VAULT_PATH:-$HOME/Documents/Obsidian Vault}"
echo "
New content here." >> "$VAULT/Existing Note.md"
```

## Wikilinks

Obsidian links notes with `[[Note Name]]` syntax. When creating notes, use these to link related content.