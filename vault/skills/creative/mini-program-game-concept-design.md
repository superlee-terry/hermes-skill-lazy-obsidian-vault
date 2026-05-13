---
categories:
- creative
description: Structured workflow for brainstorming and designing mini-program (小程序)
  or game concepts — market research, concept proposals with pivots, monetization,
  user personas, and MVP roadmaps.
name: mini-program-game-concept-design
summary: Structured workflow for brainstorming and designing mini-program (小程序) or
  game concepts — market research, concept proposals with pivots, monetization, user
  personas, and MVP roadmaps.
triggers: []
version: 1.0
---

# Mini-Program / Game Concept Design Workflow

## When to Use
When the user wants to brainstorm, design, or plan a mini-program (小程序) or game concept. Especially useful for creative ideation sessions that may involve pivoting directions.

## Workflow

### Step 1: Broad Market Research
- Use `delegate_task` with 3 parallel subagents to research:
  1. **Direct competitors**: Existing products in the target space (search 小程序/小游戏 rankings, TapTap, etc.)
  2. **Adjacent trends**: Related market trends, overseas equivalents, emerging patterns
  3. **Market data**: User demographics, market size, monetization benchmarks
- Search engines (Bing) and platforms (TapTap, 知乎, 小红书) may be blocked or rate-limited — delegate to subagents which handle retries internally.

### Step 2: Initial Concept Proposal
Structure the proposal with these proven sections:
1. **Why this direction** — market trends table with evidence
2. **Core concept** — 1-paragraph narrative hook (e.g., "你是一个初入江湖的无名剑客...")
3. **Core systems** (3-5 pillars) — each with ASCII diagrams, tables, or visual breakdowns
4. **Visual style** — ASCII mockup + reference products
5. **Mobile adaptation** — 竖屏 layout (critical for mini-programs)
6. **Monetization** — 3-tier model: Free / Ads (IAA) / IAP, with revenue projections
7. **User personas** — 2-3 distinct profiles with triggers
8. **Growth strategy** — phased: seed → burst → long-term
9. **MVP roadmap** — phased weekly plan (6-8 weeks typical)
10. **One-line positioning** — memorable tagline

### Step 3: Expect User Pivot
- Users often change direction after seeing the first concept (observed: virtual pet → martial arts tower defense)
- **Don't resist the pivot** — embrace it and do another round of targeted research on the new direction
- Reuse the same proposal structure but with all-new content

### Step 4: Refined Proposal (Post-Pivot)
- Deeper research on the new specific direction
- More detailed system designs (e.g., individual subsystem breakdowns, numerical examples)
- Competitive differentiation table (vs existing products)
- Maintain the same clean structure from Step 2

## Key Principles
- **ASCII art and visual tables** are extremely effective for communicating game mechanics in text
- **Revenue projection tables** add credibility (DAU × paid rate × ARPU)
- **User personas with "trigger words"** help with later marketing planning
- **MVP phasing** shows practical feasibility
- Always include **"一句话定位"** (one-line positioning) as a memorable anchor

## Pitfalls
- Search engines may be blocked (Google CAPTCHA, 小红书 IP risk) — use delegate_task subagents or Bing as fallback
- Don't over-invest in the first concept — user will likely pivot
- Keep each system section self-contained so pivots only require replacing specific sections
- For game design: always specify **竖屏适配** (vertical screen) since it's a mini-program constraint