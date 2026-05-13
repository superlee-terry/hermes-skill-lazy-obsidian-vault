---
categories:
- frontend
description: Enables automated extraction of MVP UI modules from a game project's
  documentation and creation of a prioritized UI backlog.
name: ui-mvp-extraction-from-docs
summary: Enables automated extraction of MVP UI modules from a game project's documentation
  and creation of a prioritized UI backlog.
tags:
- extraction
- ui
- backlog
- documentation
triggers:
- extraction
- ui
- backlog
- documentation
---

## Overview
This skill reads the documentation located in `/mnt/data/worldGameSpace/docs/`, extracts all MVP UI module entries marked as `MVP必需` from `ui-module-extraction.md`, and cross‑references them with source data files (`characters.md`, `skills.md`, `items.md`, `maps.md`) to produce an ordered UI backlog. The output can be written to `TODO.md` or a dedicated `ui-backlog.md`.

## Procedure
1. **Locate docs** – `read_file('/mnt/data/worldGameSpace/docs/ui-module-extraction.md')`.
2. **Parse lines** – Filter for `MVP必需` or `MVP必须` tags using regex.
3. **Cross‑reference** – For each module, search the supporting files for its technical specs and collect key parameters (e.g., layout dimensions, interactive elements).
4. **Generate backlog** – Produce an ordered list (core combat UI first, then core exploration, economy, auxiliary).
5. **Commit updates** – Use `write_file` to append items to `/mnt/data/worldGameSpace/TODO.md` (or create `ui-backlog.md`) with a checklist.

## Pitfalls & Work‑arounds
- **Missing front‑end folder** – If `src/ui/` does not exist, create it and add an entry in `package.json`.
- **Hermes stream timeout** – Set `HERMES_STREAM_STALE_TIMEOUT=420` before launching long‑running UI tools.
- **Key‑rotation script not executable** – Verify `/mnt/data/worldGameSpace/scripts/rotate-keys.sh` has the executable bit (`chmod +x`).

## Output Artifacts
- `ui-backlog.md`: markdown summary of extracted UI items.
- Updated `TODO.md` with MVP items marked `[MVP]`.

## Dependencies
None – uses only built‑in file tools.