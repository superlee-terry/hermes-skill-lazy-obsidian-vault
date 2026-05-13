---
categories:
- creative
description: 'Write comprehensive game narrative/storyline documents from multiple
  existing design docs. Workflow: parallel read, extract, structure, write in parts,
  merge. Handles 60KB+ documents.'
name: game-narrative-document
summary: 'Write comprehensive game narrative/storyline documents from multiple existing
  design docs. Workflow: parallel read, extract, structure, write in parts, merge.
  Handles 60KB+ documents.'
triggers: []
version: 1.0
---

# Game Narrative Document Workflow

## When to Use
When creating a large narrative document (storyline outline, quest bible, lore compendium) that must integrate elements from multiple existing game design documents. Especially for documents exceeding 30KB where single-pass writing risks context overflow.

## Workflow

### Step 1: Parallel Read and Extract
Use `delegate_task` with 3 parallel subagents to read and extract from all source docs. Group docs by theme (e.g., worldview+characters, maps+skills+items, game-modes+numerical-balance).

Each subagent should:
1. Read assigned files with `read_file`
2. Extract and return structured elements relevant to the narrative
3. Preserve original Chinese descriptions and key quotes verbatim
4. Flag cross-document connections and contradictions

**Context to pass**: Project name, document directory path, what narrative elements to extract (characters, plot hooks, world events, relationships, foreshadowing).

### Step 2: Structure the Narrative
Design the document structure before writing:
- Match structure to progression systems (level ranges, game chapters, map zones)
- Ensure each chapter has: 1 plot event + 1 NPC relationship beat + 1 progression milestone
- Plan foreshadowing: plant in early chapters, pay off in late chapters
- Track all extracted elements - nothing should go unused

### Step 3: Write in Parts
Write the document in 4-6 parts using `execute_code` with `write_file` to `/tmp/storyline_partN.md`.

**CRITICAL pitfalls**:
- **Chinese quotes in Python strings**: Full-width quotes are fine, but mixing markdown italics with nested Chinese quotes causes syntax errors. Use single-quoted Python strings or avoid nesting inside strings containing closing quotes.
- **Variables dont persist across execute_code calls**: Write each part to `/tmp` files, then merge in a final call using `read_file` to load parts.
- **Part size**: Each part should be 3-6KB (150-300 lines). Parts 1-4 can use one execute_code; the final merge must be a separate call.

### Step 4: Merge and Write Final
In the final `execute_code` call:
1. `read_file` all `/tmp` parts
2. `"\n".join()` them
3. `write_file` to the final destination path
4. Verify with `terminal` ls + wc

### Step 5: Verify
- Check line count and file size match expectations
- Confirm all sections from the outline are present
- Verify cross-references (character names, location names, item names) match source docs

## Quality Checklist
- Every named character from source docs appears in the storyline
- Every map zone has at least one story event
- Boss encounters from numerical-balance.md are integrated
- Five-element emotional system is woven into narrative themes
- Foreshadowing table: each entry has both planted and paid off columns
- Character arc table: each NPC has start state, conflict, end state
- Season/content update hooks for post-launch narrative

## Pitfalls
- **Context overflow on single write**: Never try to write 60KB+ in one shot. Always parts + merge.
- **SyntaxError from Chinese quotes**: Closing Chinese quote followed by markdown italic marker at end of Python string line confuses parser. Solution: escape or restructure.
- **Cross-call variable scope**: `execute_code` runs in fresh Python process each time. Write to `/tmp` files between calls.
- **Inconsistent naming across docs**: Source docs may use different names for the same entity. Resolve before writing by cross-referencing.