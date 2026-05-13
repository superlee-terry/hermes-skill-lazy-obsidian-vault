---
categories:
- game-development
description: Generates CSV numerical attribute tables for the Fusheng Jianlu project
  using the formulas from character-attribute-design.md.
name: numerical-balance-generator
summary: Generates CSV numerical attribute tables for the Fusheng Jianlu project using
  the formulas from character-attribute-design.md.
tags: []
triggers: []
---

# Overview
This skill auto‑generates a CSV table listing HP, ATK, DEF, SPD, and MP for levels 1‑max_lv. It reads the base parameters from the project’s YAML config (or uses defaults) and can be overridden via CLI arguments.

# Usage (Python)

```python
from numerical_balance import generate_table
csv = generate_table(max_lv=160, hp_base=120, atk_lv_exp=0.15)
print(csv)
```

# CLI
```bash
python scripts/numerical_balance.py          # prints CSV to stdout
python scripts/numerical_balance.py 160 --hp-base 120 --atk-lv-exp 0.2
```

# Pitfalls
- Keep the parameter list in `character-attribute-design.md` synchronized with the implementation in `scripts/numerical_balance.py`.
- The script rounds to two decimal places; modify the `round` calls if higher precision is required for downstream calculations.
- Parameter changes do not automatically propagate to other systems; re‑run the script for the whole table after any config adjustment.

# Linked Files
- `scripts/numerical_balance.py` – core implementation.