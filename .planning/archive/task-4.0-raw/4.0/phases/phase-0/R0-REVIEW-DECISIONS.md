# Phase 0 Review Decisions

**Document:** R0-REVIEW-DECISIONS.md
**Status:** COMPLETE
**Author:** BSKG Team
**Created:** 2026-01-08
**Last Updated:** 2026-01-08
**Tasks Completed:** R0.1, R0.2, R0.3

---

## R0.1: Phase Necessity Review

### Decision: KEEP

### Rationale

Phase 0 is the **foundation layer** that establishes the evidence packet contract, confidence bucket defaults, and routing rules. This phase directly supports all five philosophy pillars:

| Pillar | Phase 0 Contribution |
|--------|---------------------|
| **Knowledge Graph** | Builder refactor preserves behavioral signals; alignment specs ensure graph properties map correctly to evidence packets |
| **NL Query System** | Evidence packet mapping (P0.P.1) enables stable, predictable query outputs |
| **Agentic Automation** | Graph-quality debate routing (P0.P.3) and tool disagreement routing (P0.P.7) enable autonomous agent escalation |
| **Self-Improvement** | Completeness tests (P0.P.5) and deduplication tests (P0.P.6) provide the foundation for measuring and improving detection quality |
| **Task System (Beads)** | Packet mapping ensures findings are bead-ready with all required fields for investigation tasks |

### Philosophy Alignment Assessment

**Strong Alignment:**
- Evidence packet contract (P0.P.1) directly implements PHILOSOPHY.md Section "Evidence Packet Contract"
- Bucket defaults (P0.P.2) implement PHILOSOPHY.md Section "Confidence Buckets and Scoring"
- VulnDocs mapping (P0.P.4) connects semantic operations to PHILOSOPHY.md Section "VulnDocs: Knowledge System"
- Fallback rules (P0.P.8) implement PHILOSOPHY.md graceful degradation requirements

**No Modifications Required:** Phase 0 scope is well-aligned with philosophy. All alignment tasks (P0.P.1-P0.P.8) are documentation specifications that establish contracts for downstream implementation.

---

## R0.2: Task Necessity Review

### Summary

| Task | Decision | Justification |
|------|----------|---------------|
| P0.P.1 | **KEEP** | Critical foundation - defines evidence packet field mapping |
| P0.P.2 | **KEEP** | Critical foundation - defines Tier A bucket scoring |
| P0.P.3 | **KEEP** | Required for autonomous graph quality escalation |
| P0.P.4 | **KEEP** | Required for Phase 17 VulnDocs integration |
| P0.P.5 | **KEEP** | Required for Phase 2/3 test implementation |
| P0.P.6 | **KEEP** | Required for Phase 5 tool orchestration |
| P0.P.7 | **KEEP** | Required for multi-tool analysis (Phase 5+) |
| P0.P.8 | **KEEP** | Required for graceful degradation |

### Detailed Task Reviews

#### P0.P.1: Evidence Packet Mapping (post-graph)

**Decision:** KEEP (MUST)

**Justification:**
- Defines the contract for evidence packets as specified in PHILOSOPHY.md
- Maps all 13 required fields from graph properties and findings model
- Specifies behavioral signature derivation from semantic operations
- Provides the foundation for all downstream finding processing
- **741 lines** of comprehensive specification with code examples

**Downstream Dependencies:**
- Phase 1: Uses packet field mapping for Tier A alignment
- Phase 2: Uses packet structure for benchmark summaries
- Phase 3: Uses packet output contract for CLI output

**No merge candidates:** This is foundational specification that cannot be combined with other tasks.

---

#### P0.P.2: Bucket Defaults for Tier A

**Decision:** KEEP (MUST)

**Justification:**
- Defines deterministic confidence scoring for Tier A findings
- Specifies score factors: properties (+15 each), signature (+25), operations (+10 each), ordering (+20)
- Defines penalty factors: missing signature (-20), UNKNOWN ops (-15), tool disagreement (-25)
- Establishes threshold: score >= 0.75 maps to `likely`, below maps to `uncertain`
- Critical for ensuring Tier A determinism as required by PHILOSOPHY.md
- **720 lines** of specification with validation rules and examples

**Downstream Dependencies:**
- Phase 1: Uses bucket rules for Tier A finding output
- Phase 11: Tier B uses different rules but must not conflict

**No merge candidates:** Bucket scoring is independent concern from packet mapping.

---

#### P0.P.3: Graph Quality Debate Trigger

**Decision:** KEEP (SHOULD)

**Justification:**
- Defines 8 graph quality issue types (GQ-001 through GQ-008)
- Specifies convoy creation triggers and routing rules
- Enables autonomous escalation of builder/parser issues
- Supports the Agentic Automation pillar by routing issues without human intervention
- **1976 lines** of comprehensive specification with detection algorithms

**Downstream Dependencies:**
- Phase 6: Convoy system implementation
- Phase 11: Debate protocol receives graph-quality issues

**No merge candidates:** Distinct from tool disagreement (P0.P.7) which handles multi-tool conflicts, not graph quality issues.

---

#### P0.P.4: VulnDocs Category Mapping

**Decision:** KEEP (SHOULD)

**Justification:**
- Maps all 20 semantic operations to 11 VulnDocs categories
- Enables automatic retrieval of vulnerability knowledge for findings
- Supports the VulnDocs Knowledge System pillar
- Provides reverse mapping: category -> operations for navigation
- **560 lines** of specification with full operation x category matrix

**Downstream Dependencies:**
- Phase 17: VulnDocsNavigator consumes this mapping
- Phase 18: Knowledge mining uses category mapping

**No merge candidates:** Mapping specification is independent of other tasks.

---

#### P0.P.5: Evidence Packet Completeness Tests

**Decision:** KEEP (MUST)

**Justification:**
- Specifies **85 test requirements** across 7 categories
- Defines test scenarios for required fields, location validation, signature validation, bucket computation, fallback behavior
- Required for Phase 2 benchmark infrastructure
- Supports Self-Improvement pillar by enabling quality measurement
- **522 lines** of test requirement specification

**Downstream Dependencies:**
- Phase 2: Implements tests for P0.P.1 and P0.P.2
- Phase 3: Implements integration and regression tests

**No merge candidates:** Test requirements are distinct from specifications.

---

#### P0.P.6: Deduplication Rule Validation Tests

**Decision:** KEEP (SHOULD)

**Justification:**
- Specifies **98 test requirements** for deduplication
- Implements PHILOSOPHY.md deduplication rules: same location/class -> merge, same location/different class -> cluster
- Required for Phase 5 tool orchestration
- **620 lines** of test specification with algorithm pseudocode

**Downstream Dependencies:**
- Phase 5: Tool orchestration implements deduplication
- Phase 12: Integrator role uses deduplication

**No merge candidates:** Could theoretically merge with P0.P.5, but deduplication tests are substantially different (focus on finding relationships vs. packet completeness). Keep separate for clarity.

---

#### P0.P.7: Tool Disagreement Routing Rules

**Decision:** KEEP (MUST)

**Justification:**
- Defines 6 disagreement types (DIS-001 through DIS-006)
- Specifies tool agreement scoring with weights (VKG: 1.0, Slither: 0.9, Aderyn: 0.8)
- Defines routing targets: auto-confirm, uncertain, debate, escalate, convoy-debate
- Required for multi-tool analysis (Phase 5+)
- **1199 lines** of comprehensive routing specification

**Downstream Dependencies:**
- Phase 5: Tool orchestration uses disagreement routing
- Phase 11: Debate protocol receives disputed findings
- Phase 12: Integrator role resolves disputes

**No merge candidates:** Distinct from P0.P.3 (graph quality) which handles builder issues, not tool conflicts.

---

#### P0.P.8: Evidence Packet Fallback Rules

**Decision:** KEEP (MUST)

**Justification:**
- Implements PHILOSOPHY.md requirement: "If required fields are missing, set `request_more_context: true`"
- Defines fallback chains for all required fields
- Specifies confidence penalties per fallback category with caps
- Defines context budget handling (full/standard/compact/minimal/critical modes)
- **1411 lines** of comprehensive fallback specification with audit logging

**Downstream Dependencies:**
- Phase 2: Tests fallback behavior per P0.P.5
- Phase 9: Context optimization uses budget decisions

**No merge candidates:** Fallback logic is distinct from base mapping (P0.P.1) and scoring (P0.P.2).

---

### Merge Analysis

**Potential Merge Candidates Reviewed:**

1. **P0.P.5 + P0.P.6 (Test specifications)**
   - Decision: DO NOT MERGE
   - Reason: P0.P.5 tests packet completeness, P0.P.6 tests deduplication. Different concerns with different downstream consumers (Phase 2 vs Phase 5).

2. **P0.P.3 + P0.P.7 (Routing rules)**
   - Decision: DO NOT MERGE
   - Reason: P0.P.3 handles graph quality issues (builder/parser failures), P0.P.7 handles tool disagreement (multi-tool conflicts). Different triggers, different convoy types, different resolution paths.

3. **P0.P.1 + P0.P.8 (Packet mapping + fallbacks)**
   - Decision: DO NOT MERGE
   - Reason: P0.P.1 defines the ideal mapping, P0.P.8 defines degradation behavior. Keeping separate maintains clarity about what SHOULD happen vs. what happens when things are missing.

**Conclusion:** All 8 alignment tasks are necessary and appropriately scoped. No merges or cuts recommended.

---

## R0.3: Conflict Review

### Conflicts Identified from MASTER.md

The following conflicts from MASTER.md Section "Conflict Notes" are relevant to Phase 0:

| Conflict | Description | Resolution | Phase 0 Impact |
|----------|-------------|------------|----------------|
| **1. Output formats** | TOON vs YAML vs JSON | JSON is canonical; YAML optional for human review | P0.P.1 specifies JSON as output format. P0.P.8 context budget decisions may output compact JSON. No conflict. |
| **2. Determinism scope** | vs philosophy | Determinism gates apply to Tier A only | P0.P.2 explicitly states Tier A only produces `likely` or `uncertain`. P0.P.8 fallbacks are deterministic. No conflict. |
| **3. Evidence packet contract** | Missing in early phases | Add evidence packet generation as alignment tasks | **RESOLVED:** P0.P.1 fully specifies evidence packet contract. |
| **5. LLM safety controls** | Scheduled too late | Add context minimization gates in Phases 3 and 10 | P0.P.8 context budget handling supports this. No conflict with Phase 0. |

### New Conflicts Discovered

| ID | Conflict | Phases Affected | Severity | Resolution |
|----|----------|-----------------|----------|------------|
| C0.1 | P0.P.2 defines `likely` threshold at 0.75, but Phase 14 Confidence Calibration may adjust thresholds | Phase 0, Phase 14 | LOW | Phase 14 can adjust thresholds without breaking P0.P.2 contract. P0.P.2 defines Tier A DEFAULTS, calibration applies to Tier B or tuned models. |
| C0.2 | P0.P.3 convoy types overlap with Phase 6 convoy system | Phase 0, Phase 6 | LOW | P0.P.3 defines SPECIFICATION for graph-quality convoys. Phase 6 IMPLEMENTS convoy system. No conflict - specification precedes implementation. |
| C0.3 | P0.P.7 tool weights (Slither: 0.9, Aderyn: 0.8) may need calibration based on real-world performance | Phase 0, Phase 5 | LOW | Weights in P0.P.7 are DEFAULTS. Phase 5 implementation may tune based on validation results. Document as configurable. |
| C0.4 | P0.P.8 context budget thresholds (8000/4000/2000/1000) may conflict with Phase 9 PPR optimization | Phase 0, Phase 9 | LOW | P0.P.8 provides DEFAULT thresholds. Phase 9 PPR optimizes actual context. Thresholds can be configuration-driven. |

### Conflict Resolution Summary

**No blocking conflicts found.** All identified conflicts are LOW severity and resolved through:

1. **Specification vs Implementation:** Phase 0 provides specifications (contracts), downstream phases implement. Specifications remain stable; implementations can tune parameters.

2. **Defaults vs Calibration:** Phase 0 defines sensible defaults (0.75 threshold, tool weights, budget thresholds). Downstream phases (14, 5, 9) may calibrate based on real-world data without violating Phase 0 contracts.

3. **Explicit Configuration:** Where flexibility is needed (tool weights, budget thresholds), the specifications already note these are configurable values.

### Downstream Phase References

The following downstream phases should reference Phase 0 conflict notes:

- **Phase 5 TRACKER.md:** Reference C0.3 (tool weights configurable)
- **Phase 9 TRACKER.md:** Reference C0.4 (budget thresholds configurable)
- **Phase 14 TRACKER.md:** Reference C0.1 (calibration applies to Tier B/tuned models)

---

## Summary

### R0.1: Phase Necessity Review
- **Decision:** KEEP
- **Rationale:** Phase 0 directly supports all 5 philosophy pillars and is required foundation for downstream phases

### R0.2: Task Necessity Review
- **All 8 tasks:** KEEP
- **Merge candidates:** None (all tasks have distinct concerns and consumers)
- **Cut candidates:** None (all tasks are required for downstream phases)

### R0.3: Conflict Review
- **MASTER.md conflicts:** Conflict 3 (evidence packet) RESOLVED by P0.P.1
- **New conflicts:** 4 LOW severity conflicts identified, all resolvable via configuration
- **Blocking conflicts:** None

---

*R0 Review Decisions | Version 1.0 | 2026-01-08*
