# Feature Landscape

**Domain:** LLM-facing graph interface for security analysis
**Researched:** 2026-01-27

## Table Stakes

Features users (LLM agents) expect. Missing = agents make incorrect conclusions.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Path-qualified ordering | Agents need "always/sometimes/never before" not just "CFG order" | High | Requires dominance tree |
| Explicit unknowns | Missing data must not be interpreted as "safe" | Medium | Every output field needs unknown state |
| Evidence references | Findings without evidence are unverifiable | Medium | Already partially implemented |
| Consistent slicing | Same query should produce same context regardless of surface | Medium | Unify fragmented slicers |
| Schema validation | Invalid outputs should fail fast, not silently malform | Low | Pydantic integration |
| Coverage scores | Agents need to know what fraction of relevant data they received | Medium | Requires formal definition |

## Differentiators

Features that set AlphaSwarm.sol apart. Not expected by default, but highly valued.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Guard dominance semantics | Distinguish "guard exists" from "guard dominates sink" | High | Novel for Solidity analysis |
| Interprocedural ordering | Modifiers and internal calls affect operation ordering | High | Requires call summaries |
| Clause matrix output | Truth-table style clause breakdown with per-clause evidence | Medium | Enables agent debugging |
| Taint with sanitizers | Track not just sources but also data cleansing | Medium | Industry standard but uncommon in Solidity |
| External-return taint | Taint values returned from external calls | Medium | Critical for oracle manipulation |
| Call-target control taint | Track when user controls call destination | Medium | Critical for delegatecall attacks |
| Debug slice mode | Bypass pruning for diagnosis | Low | Enables agent self-debugging |
| Ops taxonomy registry | Single source of truth for operation mapping | Medium | Eliminates drift |
| Interface as ABI | Semver + compatibility shim for schema changes | Medium | Enables gradual migration |

## Anti-Features

Features to explicitly NOT build. Common mistakes in this domain.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Implicit unknowns | Silent failures cause false safety | Explicit unknown states everywhere |
| Boolean-only guards | "has_reentrancy_guard: true" hides bypass paths | Dominance qualification: dominating/bypassable/unknown |
| Flat confidence scores | 0.7 confidence tells nothing about what's missing | Clause matrix with per-clause status |
| Multiple slicing paths | Router, LLM, KG slicers produce different outputs | Unified pipeline with role budgets |
| Lossy pruning | Pruning without recording what was cut | Omission ledger with cut sets |
| Name-based taxonomy | "TRANSFERS_ETH" vs "TRANSFERS_VALUE_OUT" drift | Registry with migration map |
| Schema warnings | Non-compliant outputs with warnings still break agents | Schema validation as gate (fail fast) |

## Feature Dependencies

```
Interface Contract v2 (05.9-01)
    |
    +-- Ops Taxonomy Registry (05.9-02)
    |       |
    |       +-- Pattern Migration
    |       +-- SARIF Alias Mapping
    |
    +-- Omission Ledger (05.9-03)
    |       |
    |       +-- Coverage Scoring
    |       +-- Cut Set Recording
    |
    +-- Evidence IDs (05.9-04)
            |
            +-- Build Hash Binding
            +-- Deterministic Resolution
                    |
                    +-- Dominance Ordering (05.9-05)
                    |       |
                    |       +-- Path Qualification (always/sometimes/never/unknown)
                    |       +-- Guard Dominance
                    |       +-- Interprocedural Summaries
                    |
                    +-- Taint Expansion (05.9-06)
                            |
                            +-- External Returns
                            +-- Call-Target Control
                            +-- Sanitizers
                            +-- Availability Flags
                                    |
                                    +-- Unified Slicing (05.9-07)
                                            |
                                            +-- Debug Mode
                                            +-- Role Budgets
                                                    |
                                                    +-- Pattern Outputs v2 (05.9-08)
                                                            |
                                                            +-- Clause Matrix
                                                            +-- Unknowns Gating
                                                                    |
                                                                    +-- Skills (05.9-09)
```

## MVP Recommendation

For Phase 5.9 MVP, prioritize:

1. **Interface Contract v2** - Foundation for all other work
2. **Ops Taxonomy Registry** - Eliminates drift that confuses agents
3. **Omission Ledger + Coverage** - Prevents false safety conclusions
4. **Evidence IDs** - Makes findings reproducible
5. **Dominance Ordering** - Core analysis upgrade (single differentiator)

Defer to post-5.9 (or 5.10+):
- **Full interprocedural analysis**: Complex; partial summaries may suffice for 5.9
- **Call-target control taint**: Important but can be added later
- **Sophisticated sanitizer detection**: Start with explicit patterns, refine later

## Quality Metrics for Features

| Feature | Success Metric | Target |
|---------|---------------|--------|
| Path-qualified ordering | Correct always/sometimes classification | 95%+ on test suite |
| Guard dominance | True positive rate on guard bypass patterns | 90%+ |
| Coverage scoring | Correlation with actual omission impact | > 0.8 |
| Unknowns gating | False safety rate with unknowns | < 5% |
| Schema compliance | Validation failures in production | 0% |

## Framework & Tooling Features

Features for the MSD planning framework itself (not the product).

### plan-aware-improvements

**ID:** `plan-aware-improvements`
**Status:** proposed
**Target phase:** N/A (MSD framework enhancement)
**Created:** 2026-02-25
**Owner:** —

**Problem:** The `improve-phase` → `implement-improvements` pipeline only modifies CONTEXT.md. When plans already exist in a phase directory, improvements that should update plan task steps, schemas, and EXPECTED.md files are applied to CONTEXT.md prose instead — creating drift between the context and the concrete plans that executors follow. This was directly observed in Phase 3.1e, where 211 improvements across 7 passes all targeted CONTEXT.md while 5 plan files went stale.

**Desired behavior:**
- `improve-phase`: When `*-PLAN.md` files exist, improvement agents receive plan content alongside CONTEXT.md. Items can target `PLAN-{NN}` (already supported in template) AND the improvement agents are briefed to look for plan-level execution gaps, not just context-level design gaps.
- `implement-improvements`: Applies changes to ALL phase artifacts — CONTEXT.md, PLAN.md files, and EXPECTED.md files. Can also propose: new plans (if a gap requires a new execution unit), plan deprecation (if an improvement makes a plan unnecessary), plan restructuring (merge/split).
- `improve-phase` agents: Should be briefed with plan summaries AND plan task-level detail when plans exist. Current briefing only includes plan summaries (titles + must-haves).
- Frontmatter and EXPECTED.md: When plan content changes, the frontmatter (`must_haves`, `artifacts`, `key_links`) and the corresponding EXPECTED.md alignment criteria should be updated automatically.
- Research spikes: Should be able to target plan-specific questions, not just CONTEXT-level questions.

**Scope options:**
1. **Extend existing workflow:** Modify `improve-phase.md` to detect plans and adjust agent briefings + targets. Modify `implement-improvements.md` to handle PLAN/EXPECTED targets alongside CONTEXT. Lower risk, incremental.
2. **New unified workflow:** Create a `refine-phase` command that handles both context and plan improvements in a single pass. More elegant but higher implementation cost and testing burden.
3. **Hybrid:** Keep `improve-phase` for context-only (pre-plan) phases. Add `improve-plans` for post-plan phases. Cleaner separation but more commands.

**Affected MSD files:**
- `commands/msd/improve-phase.md` (agent briefing, area detection, plan-awareness)
- `commands/msd/implement-improvements.md` (multi-target merge, plan editing, EXPECTED.md sync)
- `agents/msd-improvement-agent.md` (plan-level briefing format)
- `agents/msd-adversarial-reviewer.md` (plan-level review lenses)
- `agents/msd-synthesis-agent.md` (cross-plan synthesis)
- `scripts/pipeline-classify.js` (plan-targeted item classification)
- `templates/improvement-file.md` (Target: PLAN-{NN} already exists, may need sub-targeting)

**Dependencies:** None (standalone MSD feature).

**Notes:** The improvement item template already supports `**Target:** PLAN-{NN}`, but (a) improvement agents rarely propose plan-targeted items because they aren't briefed with plan detail, and (b) implement-improvements ignores the PLAN target and writes to CONTEXT.md anyway. Both gaps need fixing.

---

### context-driven-area-splitting

**ID:** `context-driven-area-splitting`
**Status:** proposed
**Target phase:** N/A (MSD framework enhancement — `msd:improve-phase`)
**Created:** 2026-02-25
**Owner:** —
**Related:** `plan-aware-improvements`

**Problem:** Steps 2 and 6 of `improve-phase` perform expensive, redundant work. Step 2 reads ALL PLAN.md files upfront, builds summaries, runs a token-budget check, and extracts high-signal sections. Step 6 then re-derives area groupings from scratch using an arbitrary count-based heuristic (≤2 plans → 1 agent, 3-5 → 2-3 areas, 6+ → 3-5 areas). The problem: CONTEXT.md's `<plans>` section already organizes plans into logical groups with dependency relationships. The skill reads what CONTEXT.md already knows, re-derives it, and reconstructs it — wasting tokens and adding complexity that drifts from the source of truth.

A secondary issue: Step 6's scaling heuristic is plan-count-based, not structure-based. A phase with 6 tightly coupled plans (one area) gets 3-5 agents; a phase with 2 independent plans (two orthogonal areas) gets 1 agent. Count ≠ complexity.

**Desired behavior:**
- Step 6 reads CONTEXT.md `<plans>` section structure as area definitions — the groupings are already there (written by the planner)
- PLAN.md files are loaded lazily per area: only the plans assigned to an area are read when constructing that area's agent prompt
- The scaling heuristic is replaced by structure detection: number of top-level plan groups in `<plans>` = number of areas (capped at 5)
- Token budget complexity disappears — plans are loaded on-demand, so you never load plans for other areas
- `plan_summaries` and `plan_contents` are per-area from the start, not globally accumulated then filtered

**What gets removed / simplified:**
- Step 2 "Also build plan_contents (full plan content with token budget)" block — eliminated; replaced by lazy per-area load in Step 8
- Step 2 TOKEN BUDGET CHECK block — eliminated; each area loads only its own plans
- Step 6 "Scaling heuristic" (≤2 / 3-5 / 6+ count rules) — replaced by structure detection
- Step 6 "Group by: shared assumptions, coupled plans" re-derivation — eliminated; CONTEXT.md already did this
- Step 6 "Plans not assigned to any area → other_plan_summaries" cross-contamination logic — eliminated; each area carries only its plans

**What stays:**
- Step 2 still detects which PLAN.md files exist (glob only — no reads)
- Step 2 still reads RESEARCH.md summary (cheap, single file)
- Step 6 still extracts area metadata (name, content slice, summary) from CONTEXT.md — but now uses structure that already exists
- Step 7 metaprompt generation is unchanged
- Steps 8+ are unchanged

**Scope options:**
1. **Minimal (correct):** Change Steps 2 and 6 only. Step 8 reads plans lazily when constructing each area's prompt. ~30 lines removed, no new logic.
2. **Full:** Also update `msd-improvement-agent.md` briefing format to accept pre-structured area context instead of re-slicing it internally.

**Affected MSD files:**
- `commands/msd/improve-phase.md` (Steps 2 and 6 — primary change)
- `agents/msd-improvement-agent.md` (optional: remove internal re-slicing if it exists)

**Dependencies:** None. Backwards-compatible — CONTEXT.md already has `<plans>` sections.

**Notes:** This is the correct fix for the problem observed in Phase 3.1e: 7 passes × 5 plans = 35 plan reads that each derived the same area groupings CONTEXT.md already encoded. The fix is structural, not cosmetic — it removes a design error, not a style preference.

---

## Sources

- [05.9-CONTEXT.md](./.planning/phases/05.9-llm-graph-interface-improvements/05.9-CONTEXT.md)
- [PHILOSOPHY.md](./docs/PHILOSOPHY.md)
- [TaintSentinel: Path-Level Vulnerability Detection](https://arxiv.org/html/2510.18192)
- [Knowledge Graph Incompleteness in RAG](https://arxiv.org/html/2508.08344v1)
