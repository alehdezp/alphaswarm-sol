# Phase 3 Plan 05: Evidence and Bead Integrations Summary

**Status:** COMPLETE
**Duration:** ~5 minutes
**Date:** 2026-01-20

## One-liner

Evidence/bead integration layer with violated assumptions as first-class finding type, accepted risk auto-filtering, and token-budgeted bead context inheritance.

## What Was Built

### 1. Evidence Context Extension (evidence.py - 757 LOC)

Created `EvidenceContextExtension` dataclass with PHILOSOPHY.md evidence packet fields:
- `protocol_context`: Relevant protocol context sections
- `relevant_assumptions`: Assumptions supporting finding
- `violated_assumptions`: Assumptions this finding would violate (first-class finding type)
- `offchain_dependencies`: Off-chain inputs affecting finding
- `business_impact`: "user funds at risk because X role can do Y"
- `is_accepted_risk` + `accepted_risk_reason`: For auto-filtering

Created `EvidenceContextProvider` service:
- `get_context_for_finding()`: Aggregates all context for a finding
- `get_relevant_assumptions()`: By function name and operation categories
- `check_violated_assumptions()`: First-class violated assumption detection
- `check_accepted_risk()`: Auto-filter matching accepted risks
- `derive_business_impact()`: Role-capability based impact derivation
- `get_offchain_dependencies()`: Oracle/keeper dependency tracking

### 2. Bead Context Inheritance (bead.py - 683 LOC)

Created `BeadContext` dataclass for targeted LLM context:
- Protocol name and type
- Relevant roles with capabilities and trust assumptions
- Relevant assumptions
- Relevant invariants
- Off-chain dependencies
- Security model summary
- Matching accepted risks
- Token estimate for context budgeting

Created `BeadContextProvider` service:
- `get_context_for_bead()`: With max_tokens budget parameter
- `enrich_bead()`: Add context to existing bead via metadata
- `get_prompt_extension()`: Format context for LLM prompt
- `_trim_context()`: Stay within token budget (priority-based trimming)
- `to_prompt_section()`: Formatted prompt section for LLM consumption

### 3. Mappings for Customization

Exported mappings users can extend:
- `OPERATION_TO_ASSUMPTION_CATEGORIES`: 20 BSKG ops to assumption categories
- `VULN_CLASS_TO_ASSUMPTION_CATEGORIES`: 10 vuln classes to categories
- `VULN_CLASS_TO_CAPABILITIES`: Vuln classes to relevant role capabilities

## Commits

| Hash | Description |
|------|-------------|
| ff0230f | feat(03-05): add evidence context extension and provider |
| 1f6a284 | feat(03-05): add bead context inheritance provider |
| dbeb7f4 | feat(03-05): update integration exports in context module |

## Files Created/Modified

| File | LOC | Purpose |
|------|-----|---------|
| `src/true_vkg/context/integrations/__init__.py` | 70 | Integration module exports |
| `src/true_vkg/context/integrations/evidence.py` | 757 | Evidence packet extension |
| `src/true_vkg/context/integrations/bead.py` | 683 | Bead context inheritance |
| `src/true_vkg/context/__init__.py` | +8 | Added integration exports |

## Key Links Verified

| From | To | Pattern |
|------|----|---------|
| evidence.py | schema.py | `from..context.schema.*import` (TYPE_CHECKING) |
| bead.py | beads/schema.py | `from...beads.schema.*import` (TYPE_CHECKING) |
| bead.py | evidence.py | `from.evidence import EvidenceContextProvider` |

## Verification Results

All must_haves verified:

1. **Evidence packets include context fields**: protocol_context, assumptions, offchain_inputs, violated_assumptions, business_impact all available in to_dict()

2. **Violated assumptions as first-class finding**: `check_violated_assumptions()` returns list of violated assumption descriptions based on finding and semantic ops

3. **Beads inherit context automatically**: `BeadContextProvider.get_context_for_bead()` returns targeted context, `enrich_bead()` adds to bead metadata

4. **Accepted risks auto-filtered**: `check_accepted_risk()` returns (True, reason) for matching accepted risks

5. **Token budgeting**: `BeadContext.token_estimate` populated, `_trim_context()` keeps within max_tokens budget

## Success Criteria Met

- [x] Evidence packets can include protocol_context, assumptions, offchain_inputs
- [x] Violated assumptions tracked as first-class finding type
- [x] Beads inherit relevant context sections automatically
- [x] Accepted risks auto-filtered from findings
- [x] Token budgeting for minimal context loading
- [x] All exports available from true_vkg.context

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| TYPE_CHECKING imports for schema classes | Avoid circular imports while maintaining type hints |
| Operation-to-category mapping | Enables fuzzy assumption matching by semantic operation |
| Priority-based context trimming | Keeps most important context when over token budget |
| Bead context in graph_context dict | Leverages existing bead mechanism without schema changes |
| Fuzzy assumption violation detection | Keyword-based matching for violation pattern detection |

## Next Phase Readiness

Plan 03-05 complete. Context integrations ready for:
- Plan 03-06: CLI + Testing (final Phase 3 plan)
- Pattern engine integration via EvidenceContextProvider
- Bead creation with automatic context via BeadContextProvider
- Agent investigation prompts with protocol context sections
