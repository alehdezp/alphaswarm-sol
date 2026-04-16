# GAP-01: Confirm tier_a_required semantics under tag-absent conditions

**Created by:** improve-phase
**Source:** P1-IMP-01
**Priority:** HIGH
**Status:** resolved
**depends_on:** []

## Question

When `tier_a_required` mode is used in access-tierb-001 pattern and Tier B tags are uncomputed (absent from the graph), does the pattern fire or not fire? This determines whether all 18+ baseline FPs are Tier A-only false positives.

## Context

Plan 01 tests whether tuning access-tierb-001's YAML `none:` conditions reduces FPs. But the pattern operates in two evaluation tiers: Tier A (deterministic, graph-only) and Tier B (LLM-verified, tag-dependent). If Tier B tags are absent (uncomputed), the behavior of `tier_a_required` determines whether the pattern fires on Tier A criteria alone or is silently skipped.

If the pattern fires on Tier A alone when tags are absent, then all 18+ FPs are Tier A-only. If it skips, the FP count is different. This changes Plan 01's scope and interpretation.

## Research Approach

- Read the pattern engine source code for `tier_a_required` handling
- Check `vulndocs/access-control/general/patterns/access-tierb-001-trust-assumption-violation.yaml` for the field
- Search for how `tier_a_required` interacts with the match engine when tags are absent
- Check if there's a fallback behavior documented

## Findings

**Confidence: HIGH** — derived from direct source code analysis.

**Source:** `src/alphaswarm_sol/queries/patterns.py` lines 326-329, 723-808; `src/alphaswarm_sol/queries/tier_b.py` lines 123-141, 247-279.

### tier_a_required Semantics

The `tier_a_required` aggregation mode means **Tier A is the gate; Tier B provides optional context only.** Specifically:

1. **Aggregation mode parsing** (patterns.py:326-329): Three modes exist — `tier_a_only`, `tier_a_required`, and `voting`. The mode is read from pattern YAML `aggregation.mode`.

2. **When Tier B tags are absent** (tier_b.py:123-141): `ensure_node_tags()` returns an empty `NodeTags` object. Tier B match conditions that check tags will fail (early exit at each condition check).

3. **Critical behavior** (patterns.py:764-775): In `_aggregate_tiers()`, when mode is `tier_a_required`:
   - If Tier A does NOT match → pattern does NOT fire (regardless of Tier B)
   - If Tier A DOES match → `final_matched = tier_a_matched` — pattern fires **regardless of Tier B result**
   - Tier B result is included as context (`tier_b_context`) but does NOT gate the match

4. **Conclusion:** When `tier_a_required` is used and Tier B tags are uncomputed (absent), the pattern fires on Tier A criteria alone. **All 18+ baseline FPs from access-tierb-001 are Tier A-only false positives.**

### Implications for Plan 01

- Plan 01's scope is correct: tuning Tier A `none:` conditions is the right lever
- The 18+ FPs are all from Tier A overfiring, not Tier B confusion
- No Tier B tag computation is needed to measure Plan 01's FP reduction

## Recommendation

**Do X:** Plan 01 should proceed as designed — tune Tier A `none:` conditions in access-tierb-001. The FP baseline of 18+ is entirely Tier A-driven.

**CONTEXT.md changes:** Update Plan 01 description to explicitly note: "All baseline FPs are Tier A-only (confirmed by code analysis of `_aggregate_tiers()` tier_a_required mode)." This removes the ambiguity that prompted this gap.

**Affected plans:** Plan 01 only. No other plans depend on this semantic.
