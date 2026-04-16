---
phase: 07.3.1.6-full-testing-hardening
type: improvement-roadmap
created: 2026-02-03
updated: 2026-02-04
status: proposal-v4
---

# Phase 07.3.1.6 Improvement Roadmap (v4)

## Executive Summary

**Current State**: The testing framework is architecturally sophisticated but operationally hollow. All 16 plans are well-documented but contain **~44 blocking gaps** preventing execution. Zero claude-code-controller transcripts exist proving any workflow works. The project is 98% feature-complete but 0% validation-hardened.

**Root Cause**: Plans are documentation-first, not execution-first. They describe what SHOULD happen but don't:
1. Lock down fundamental definitions (markers, thresholds, schemas)
2. Create required artifacts (ground truth, templates, fixtures, VQL library)
3. Define validation mechanisms (measurement methods, enforcement logic)
4. **Prove the knowledge graph actually improves agent reasoning** (existential requirement)
5. **Validate HENTI multi-orchestration produces better results than single-agent**
6. **Provide concrete claude-code-controller execution sequences** (new in v4)
7. **Define decision trees and abort criteria for existential tests** (new in v4)

**Critical Path**: This roadmap prioritizes gaps that BLOCK execution over theoretical improvements. Every improvement must either:
- Enable a blocked plan to execute, OR
- Fix a logical flaw that would produce invalid results, OR
- **Prove core architectural decisions add value** (graph, multi-agent, economic context), OR
- **Provide concrete execution infrastructure** (decision trees, abort criteria, execution sequences)

**Change from v3**: v3 had 42 improvements. v4 adds:
- **12 Gap Analysis Items** (GAP-01 through GAP-12) — identifies critical execution blockers
- **IMP-J category**: Execution Infrastructure (4 items) — decision trees, execution sequences, abort criteria
- **IMP-K category**: Technical Debt (4 items) — VQL validation, ground truth seeding, pack unification
- **IMP-L category**: Performance Infrastructure (4 items) — baselines, iteration entry points
- **Bidirectional Plan↔IMP Mapping** — explicit traceability in both directions
- **Wave 0.5** — execution infrastructure before artifacts
- **Abort Criteria** — explicit halt conditions for existential validations

**Existential Requirement**: If the knowledge graph doesn't materially improve agent reasoning, the project's core justification fails. This roadmap includes explicit validation AND decision trees for what to do if validation fails.

---

## Improvement Categories

| Category | Description | Count | Impact |
|----------|-------------|-------|--------|
| **IMP-A** | Blocking Definitions | 5 | CRITICAL - blocks all downstream |
| **IMP-B** | Missing Artifacts | 5 | HIGH - blocks specific plans |
| **IMP-C** | Validation Mechanisms | 4 | HIGH - prevents false positives |
| **IMP-D** | Logical Flaws | 4 | MEDIUM - produces incorrect conclusions |
| **IMP-E** | Integration Gaps | 3 | MEDIUM - breaks cross-plan flow |
| **IMP-F** | Clarity & Consistency | 3 | LOW - improves maintainability |
| **IMP-G** | Knowledge Graph Value Proof | 3 | **EXISTENTIAL** - proves graph is essential |
| **IMP-H** | Multi-Agent Value Proof | 3 | **EXISTENTIAL** - proves debate adds value |
| **IMP-I** | Pattern Reasoning Effectiveness | 2 | **HIGH** - proves behavioral detection works |
| **IMP-J** | Execution Infrastructure (v4) | 4 | **CRITICAL** - enables execution |
| **IMP-K** | Technical Debt (v4) | 4 | **HIGH** - fixes implementation gaps |
| **IMP-L** | Performance Infrastructure (v4) | 4 | **MEDIUM** - enables benchmarking |
| **I-** | High-Level Validations | 7 | HIGH - proves system works |
| **HENTI-** | System-Level Validations | 3 | HIGH - proves production readiness |

**Total: 44 IMP items + 7 I-validations + 3 HENTI = 54 total improvements**

---

# Part 1: Blocking Requirements (IMP-A through IMP-F)

These must be resolved BEFORE plans can execute and BEFORE I-01 to I-07 can be validated.

---

## Category IMP-A: Blocking Definitions (CRITICAL)

### IMP-A1: Orchestration Marker Specification

**Problem**: Plans reference "orchestration markers" but exact strings, parameters, and emission responsibility are undefined.

**Current State**: PHILOSOPHY.md mentions 9 stages but:
- Marker format not locked (`TaskCreate(task-001)` vs `[TASK_CREATE task=001]`)
- Dynamic fields (task IDs, timestamps) not specified
- Emission responsibility unclear (skill? tool? Claude Code?)

**Required Specification**:
```yaml
orchestration_markers:
  preflight:
    success: "[PREFLIGHT_PASS duration={ms}]"
    failure: "[PREFLIGHT_FAIL reason={reason}]"
  graph_build:
    success: "[GRAPH_BUILD_SUCCESS nodes={n} edges={e} hash={h}]"
  task_lifecycle:
    create: "TaskCreate(id={task_id}, subject={subject})"
    update: "TaskUpdate(id={task_id}, status={status}, verdict={verdict})"
  subagent:
    spawn: "SubagentStart(type={vrs-attacker|vrs-defender|vrs-verifier})"
    complete: "SubagentComplete(type={type}, findings={count})"
  context:
    ready: "[CONTEXT_READY protocol={name}]"
    incomplete: "[CONTEXT_INCOMPLETE missing={fields}]"
    simulated: "[CONTEXT_SIMULATED reason={reason}]"
  detection:
    complete: "[DETECTION_COMPLETE patterns={count} deduped={count}]"
  report:
    generated: "[REPORT_GENERATED findings={count}]"
  progress:
    saved: "[PROGRESS_SAVED state={path}]"
```

**Blocks**: Plans 01, 03, 15, 16 cannot verify success without locked markers.

**Files to Create/Update**:
- `CREATE: .planning/testing/rules/canonical/ORCHESTRATION-MARKERS.md`
- `UPDATE: .planning/testing/rules/canonical/RULES-ESSENTIAL.md` (reference new file)

---

### IMP-A2: Anti-Fabrication Threshold Standardization

**Problem**: Different plans use different thresholds inconsistently.

**Current Inconsistencies**:
| Source | Smoke | Agent | E2E | Duration |
|--------|-------|-------|-----|----------|
| RULES-ESSENTIAL.md | 50 | 100 | 200 lines | 5s/30s/120s |
| Plan 09 | 50-200 | - | - | 5-30s |
| Plan 16 | - | 150 | - | 60s |

**Required Standardization** (single source of truth):
```yaml
anti_fabrication_thresholds:
  smoke_test:
    min_lines: 50
    min_duration_ms: 5000
    max_duration_ms: 60000
    required_markers: ["ALPHASWARM-START", "alphaswarm"]

  agent_unit_test:
    min_lines: 100
    min_duration_ms: 30000
    max_duration_ms: 300000
    required_markers: ["Attacker:", "Defender:", "Verifier:"]

  e2e_validation:
    min_lines: 200
    min_duration_ms: 120000
    max_duration_ms: 600000
    required_markers: ["TaskCreate", "TaskUpdate", "SubagentStart", "REPORT_GENERATED"]

  multi_agent_debate:
    min_lines: 300
    min_duration_ms: 180000
    max_duration_ms: 600000
    required_markers: ["Attacker:", "Defender:", "Verifier:", "verdict"]
```

**Blocks**: Cross-plan validation becomes inconsistent without standardization.

**Files to Update**:
- `UPDATE: .planning/testing/rules/canonical/RULES-ESSENTIAL.md` (lock thresholds)
- `UPDATE: configs/claude_code_controller_markers.yaml` (reflect canonical values)
- `UPDATE: Plans 09, 15, 16` (reference canonical thresholds)

---

### IMP-A3: Proof Token Matrix

**Problem**: Evidence packs require proof tokens per stage, but the matrix is incomplete.

**Current State**: `guide-evidence.md` lists tokens but marks some N/A without enumeration.

**Required Matrix**:
```yaml
proof_token_matrix:
  cli_install:
    required: [stage.health_check]
    na: [graph_build, agent_spawn, debate, context_pack, pattern_match]

  graph_build:
    required: [stage.graph_build, stage.graph_integrity]
    na: [agent_spawn, debate, context_pack]

  audit_entrypoint:
    required: [health_check, graph_build, context_pack, pattern_match, agent_spawn, debate, report]
    na: []

  e2e_validation:
    required: [ALL]
    na: []
```

**Blocks**: Plan 02 (Evidence Standardization) cannot produce usable evidence packs.

**Files to Create**:
- `CREATE: .planning/testing/rules/canonical/PROOF-TOKEN-MATRIX.md`
- `UPDATE: .planning/testing/guides/guide-evidence.md` (reference matrix)

---

### IMP-A4: EI/CTL Definition

**Problem**: Plans reference "EI" (Economic Intelligence) and "CTL" (Context Trust Level) but never define them operationally.

**Required Definition**:
```yaml
economic_intelligence:
  required_outputs:
    - actor_analysis: "List of actors with roles"
    - asset_flows: "Map of value flows between actors"
    - attack_profitability: "Numeric: profit - cost > 0?"
    - incentive_alignment: "Do incentives prevent attack? Boolean + reasoning"

  quality_levels:
    complete: "All 4 outputs with concrete numbers"
    partial: "Actor + flows present; profitability vague"
    absent: "No economic analysis"

context_trust_level:
  levels:
    high: "Official docs + externally verified"
    medium: "Official docs, not verified"
    low: "Inferred from code only"
    simulated: "Fabricated for testing"

  tier_gating:
    tier_c_requires: ["high", "medium"]
    tier_c_blocked: ["low", "simulated"]
```

**Blocks**: Plan 01 T1, Plan 07 (Context Gate) cannot proceed.

**Files to Create**:
- `CREATE: docs/reference/economic-intelligence-spec.md`
- `UPDATE: Plan 01, Plan 07` (reference spec)

---

### IMP-A5: Tier C Gating Thresholds

**Problem**: Tier C gating mentioned but numeric thresholds not defined.

**Required Definition**:
```yaml
tier_c_gating:
  required_context_fields:
    - protocol_type
    - trust_boundaries
    - asset_types
    - upgradeability
    - economic_model

  thresholds:
    full_execution:
      fields_present: 5/5 (100%)
      ctl_minimum: "medium"

    partial_execution:
      fields_present: 3/5 (60%)
      ctl_minimum: "medium"
      note: "Low-risk Tier C only"

    blocked:
      fields_present: < 3/5
      marker: "[TIER_C_BLOCKED reason={missing_fields}]"
```

**Blocks**: Plan 03 T4, Plan 07 cannot implement gating.

**Files to Update**:
- `UPDATE: .planning/testing/rules/canonical/VALIDATION-RULES.md` (add Tier C section)

---

## Category IMP-B: Missing Artifacts (HIGH)

### IMP-B1: Ground Truth Corpus

**Problem**: E2E validation requires external ground truth, but no corpus exists.

**Required Structure**:
```
.vrs/corpus/ground-truth/
├── provenance.yaml              # Source docs with dates, URLs
├── code4rena/
│   ├── 2023-01-ondo/
│   │   ├── findings.yaml        # Validated findings
│   │   └── source.md            # Report link
│   └── ...
├── smartbugs/
│   └── manifest.yaml            # Commit hash, subset
└── internal/
    └── annotated/               # Manual annotations
```

**Minimum Viable**:
- 5 contracts from Code4rena (≥3 findings each)
- 3 contracts from SmartBugs
- 2 annotated internal contracts

**Blocks**: Plans 05, 06, 15 (E2E) cannot compare against ground truth.

**Files to Create**:
- `CREATE: .vrs/corpus/ground-truth/provenance.yaml`
- `CREATE: .vrs/corpus/ground-truth/code4rena/` (5 contests)

---

### IMP-B2: Missing Templates (4 Required)

**Problem**: Plans 11, 12, 13, 15 reference templates that don't exist.

**Required Templates**:

1. **PATH-EXPLORATION-TEMPLATE.md** (Plan 11)
   - Query configuration, entry/exit points
   - Evidence contract for path enumeration

2. **ECONOMIC-MODEL-LIBRARY.md** (Plan 12)
   - 4+ protocol type templates (Lending, DEX, Oracle, etc.)
   - Actor/flow/incentive structure per type

3. **PATTERN-DISCOVERY-LOG.md** (Plan 13)
   - Trigger types, anomaly description
   - Candidate fields, routing decision

4. **GUIDE-ORCHESTRATION-PROOF.md** (Plan 15)
   - 9-stage pipeline with expected markers
   - Sequence validation rules

**Blocks**: Plans 11, 12, 13, 15 cannot produce valid evidence.

**Files to Create**:
- `CREATE: .planning/testing/templates/PATH-EXPLORATION-TEMPLATE.md`
- `CREATE: .planning/testing/scenarios/economic/ECONOMIC-MODEL-LIBRARY.md`
- `CREATE: .planning/testing/templates/PATTERN-DISCOVERY-LOG.md`
- `CREATE: .planning/testing/guides/guide-orchestration-proof.md`

---

### IMP-B3: Test Contract Verification

**Problem**: Plans assume contracts exist but don't verify.

**Referenced (Unverified)**:
| Contract | Plans | Status |
|----------|-------|--------|
| `tests/contracts/CrossFunctionReentrancy.sol` | 11, 15, 16 | UNVERIFIED |
| `tests/fixtures/dvd/side-entrance/` | 11, 12 | UNVERIFIED |
| `tests/contracts/hard-case/` | 13 | UNVERIFIED |
| `tests/contracts/semantic-test-set/` | 09 | UNVERIFIED |

**Required Action**:
1. Verify each exists OR document must be created
2. Add to `tests/contracts/MANIFEST.yaml` with metadata

**Blocks**: Plans 09, 11, 12, 13, 15, 16 cannot execute.

**Files to Verify/Create**:
- `VERIFY/CREATE: tests/contracts/CrossFunctionReentrancy.sol`
- `UPDATE: tests/contracts/MANIFEST.yaml` (complete inventory)

---

### IMP-B4: Skill Registry Verification

**Problem**: Plans reference skills that may not exist in registry.

**Referenced Skills**:
| Skill | Status |
|-------|--------|
| `/vrs-workflow-test` | VERIFY |
| `/vrs-evaluate-workflow` | VERIFY |
| `/vrs-claude-code-agent-teams-runner` | VERIFY |
| `/pattern-forge` | VERIFY |
| `/vrs-refine` | VERIFY |

**Required Action**: Check `src/alphaswarm_sol/skills/registry.yaml` for each.

**Blocks**: Plans cannot invoke non-existent skills.

**Files to Verify**:
- `VERIFY: src/alphaswarm_sol/skills/registry.yaml`

---

### IMP-B5: VQL Query Library (Minimum Set)

**Problem**: Graph-first enforcement requires VQL queries before conclusions, but no standardized query library exists. References to "VQL-MIN-01", "VQL-MIN-02" have no registry.

**Why This Matters**: Without a standardized VQL library:
1. Cannot verify "graph-first" rule objectively
2. Cannot measure query quality across agents
3. Agents may use ad-hoc queries that miss critical patterns

**Required VQL Minimum Set**:
```yaml
vql_minimum_set:
  structural_queries:
    VQL-MIN-01:
      name: "function_entry_points"
      query: "MATCH (f:Function)-[:HAS_MODIFIER]->(m) RETURN f, m"
      purpose: "Find entry points with/without protection"

    VQL-MIN-02:
      name: "external_calls"
      query: "MATCH (f:Function)-[:CALLS_EXTERNAL]->(t:Target) RETURN f, t"
      purpose: "Find external call targets"

    VQL-MIN-03:
      name: "state_writes"
      query: "MATCH (f:Function)-[:WRITES_STATE]->(v:Variable) RETURN f, v"
      purpose: "Find state-modifying functions"

  semantic_queries:
    VQL-MIN-04:
      name: "reentrancy_pattern"
      query: "MATCH (f)-[:READS_USER_BALANCE]->(b)-[:CALLS_EXTERNAL]->(t)-[:WRITES_USER_BALANCE]->(w) RETURN f,b,t,w"
      purpose: "Detect R:bal → X:out → W:bal pattern"

    VQL-MIN-05:
      name: "access_control_gap"
      query: "MATCH (f:Function)-[:WRITES_CRITICAL_STATE]->(s) WHERE NOT (f)-[:CHECKS_PERMISSION]->() RETURN f,s"
      purpose: "Detect unprotected state modifications"

    VQL-MIN-06:
      name: "value_transfer_without_check"
      query: "MATCH (f:Function)-[:TRANSFERS_VALUE_OUT]->(t) WHERE NOT (f)-[:CHECKS_PERMISSION]->() RETURN f,t"
      purpose: "Detect unprotected value transfers"

  path_queries:
    VQL-MIN-07:
      name: "cross_function_flow"
      query: "MATCH path = (entry:Function)-[:CALLS*1..3]->(target:Function) WHERE target.has_external_call RETURN path"
      purpose: "Find multi-hop attack paths"

    VQL-MIN-08:
      name: "callback_reachability"
      query: "MATCH (f:Function)-[:CALLS_EXTERNAL]->(t)-[:HAS_CALLBACK]->(cb) RETURN f,t,cb"
      purpose: "Find callback attack surfaces"
```

**Required Implementation**:
1. Create VQL library file with all queries
2. Add query ID markers to transcripts: `[VQL_QUERY id=VQL-MIN-01]`
3. Modify `scripts/validate_graph_first.py` to detect these markers

**Blocks**: IMP-C2 (graph-first enforcement), I-03 (graph-first proof)

**Files to Create**:
- `CREATE: docs/reference/vql-library.md`
- `CREATE: src/alphaswarm_sol/kg/queries/vql_minimum_set.yaml`

---

## Category IMP-C: Validation Mechanisms (HIGH)

### IMP-C1: Transcript Measurement Methodology

**Problem**: "Lines" and "duration" undefined for measurement.

**Required Definition**:
```yaml
transcript_measurement:
  line_counting:
    method: "raw_newlines (wc -l)"
    exclude_blank: false

  duration_measurement:
    method: "first_to_last_timestamp OR manifest duration_ms"

  marker_presence:
    logic: "all_required" (every marker must appear)
```

**Blocks**: Different evaluators produce different results.

**Files to Create**:
- `CREATE: .planning/testing/rules/canonical/TRANSCRIPT-MEASUREMENT.md`

---

### IMP-C2: Graph-First Enforcement Mechanism

**Problem**: "Graph-first reasoning" rule has no verification mechanism.

**Required Definition**:
```yaml
graph_first_verification:
  query_markers: "[VQL_MIN_SET_START]", "VQL-MIN-{id}"
  conclusion_markers: "Finding:", "verdict:", "severity:"

  rule: "first_query_line < first_conclusion_line"
  threshold: "80% of findings must have preceding queries"
```

**Blocks**: Plan 03 I-03 cannot be implemented.

**Files to Create**:
- `CREATE: scripts/validate_graph_first.py`
- `UPDATE: RULES-ESSENTIAL.md` (add verification section)

---

### IMP-C3: Control Run Mechanism (Economic Context)

**Problem**: Plan 12 needs "with vs without economic context" but disable mechanism undefined.

**Required Definition**:
```yaml
control_run:
  disable_method:
    settings_override: "--settings .vrs/settings-no-economic.yaml"
    # OR env: VRS_ECONOMIC_CONTEXT=disabled
    # OR flag: --no-economic-context

  verification:
    control_shows: "[ECONOMIC_CONTEXT_DISABLED]"
    test_shows: "[ECONOMIC_CONTEXT_ENABLED]"
```

**Blocks**: Plan 12 T3 cannot run comparison.

**Files to Create**:
- `CREATE: .vrs/settings-no-economic.yaml`

---

### IMP-C4: Debate Quality Baseline

**Problem**: Plan 16 claims debate is "better" but no baseline for comparison.

**Required Definition**:
```yaml
baseline:
  single_agent:
    agents: ["vrs-secure-reviewer"]
    capture: [finding_count, evidence_depth, reasoning_length]

  multi_agent:
    agents: ["vrs-attacker", "vrs-defender", "vrs-verifier"]
    capture: [same metrics]

  comparison:
    nuance: "multi > single * 1.5 reasoning length"
    evidence: "multi > single evidence depth"
```

**Blocks**: Plan 16 cannot prove debate adds value.

**Files to Create**:
- `CREATE: .planning/testing/templates/DEBATE-BASELINE-COMPARISON.md`

---

## Category IMP-D: Logical Flaws (MEDIUM)

### IMP-D1: Plan 15 Dependency Incompleteness

**Problem**: Plan 15 depends on 03, 04 but should depend on 09-14 to validate complex reasoning is orchestrated.

**Fix**: Add dependency check in Plan 15 T1 for Plans 09-14 completion.

**Files to Update**:
- `UPDATE: 07.3.1.6-15-PLAN.md` (add dependencies)

---

### IMP-D2: Circular Documentation Dependency

**Problem**: Plan 01 defines what 02-16 test, but 02-16 validate 01's definitions.

**Fix**: Add "Definition Freeze" checkpoint after Plan 01. Any changes require re-validation.

**Files to Update**:
- `UPDATE: 07.3.1.6-01-PLAN.md` (add freeze checkpoint)

---

### IMP-D3: Plan 13 Hard-Case Selection Undefined

**Problem**: Plan 13 needs vulnerability "NOT covered by existing patterns" but doesn't specify which.

**Fix**: Specify contract and verify no patterns match:
```yaml
discovery_hard_case:
  contract: "tests/contracts/hard-case/NovelStorageCollision.sol"
  vulnerability: "Storage Collision via Delegatecall"
  verification: "uv run alphaswarm patterns match → 0 matches"
```

**Files to Create/Update**:
- `CREATE: tests/contracts/hard-case/NovelStorageCollision.sol`
- `UPDATE: Plan 13` (reference specific contract)

---

### IMP-D4: Resume Checkpoint Format Undefined

**Problem**: Plan 06 I-06 needs checkpoint detection but format undefined.

**Fix**: Define checkpoint schema:
```yaml
checkpoint:
  file: ".vrs/state/checkpoint.yaml"
  fields: [audit_id, phase, graph.hash, beads.processed, beads.pending]
  resume_logic: "if hash matches, skip rebuild; resume from pending"
```

**Files to Create**:
- `CREATE: docs/reference/checkpoint-format.md`

---

## Category IMP-E: Integration Gaps (MEDIUM)

### IMP-E1: Scenario Manifest ↔ Workflow Docs Misalignment

**Problem**: Manifest uses different command format than workflow docs.

**Fix**: Standardize execution pattern:
```yaml
controller_command: "/vrs-workflow-test workflow=audit-entrypoint"
subject_command: "/vrs-audit {target}"
```

**Files to Update**:
- `UPDATE: .planning/testing/templates/scenario-manifest.yaml`
- `UPDATE: workflow docs` (align with manifest)

---

### IMP-E2: Wave Gate Implementation

**Problem**: Wave Gates 1-5 defined but not implemented.

**Fix**: Create gate checker script:
```python
# scripts/check_wave_gate.py
def check_gate(gate_id): ...
```

**Files to Create**:
- `CREATE: scripts/check_wave_gate.py`

---

### IMP-E3: Tool Bypass Handling

**Problem**: Plan 10 mentions bypass markers but doesn't define format.

**Fix**: Define bypass marker:
```yaml
bypass_marker: "[TOOL_BYPASS tool={name} reason={reason}]"
allowed_reasons: [tool_unavailable, tool_timeout, scope_exclusion]
```

**Files to Update**:
- `UPDATE: Plan 10` (add bypass definition)
- `UPDATE: RULES-ESSENTIAL.md` (document bypass)

---

## Category IMP-F: Clarity & Consistency (LOW)

### IMP-F1: Plan-to-B10 Mapping

**Problem**: Plans 07-14 map to B10 requirements but mapping is implicit.

**Fix**: Add mapping table to PLAN-INDEX.md:
| Plan | B10 Req | Description |
|------|---------|-------------|
| 07 | B10.A | Context Gate |
| 08 | B10.J | Hard Cases |
| 09 | B10.K | Pattern Eval |
| ... | ... | ... |

---

### IMP-F2: Evidence Pack Directory Standardization

**Problem**: Multiple plans reference different paths for evidence.

**Fix**: Lock structure:
```
.vrs/testing/
├── runs/{run_id}/          # Complete packs
├── transcripts/            # Symlinks
├── reports/                # Symlinks
└── corpus/ground-truth/    # External truth
```

---

### IMP-F3: Semantic Accuracy Threshold

**Problem**: Plan 09 T4 validates semantic accuracy but no threshold defined.

**Fix**: Define threshold:
```yaml
semantic_accuracy:
  test_set: "tests/contracts/semantic-test-set/"
  min_functions: 30
  threshold: "precision >= 0.7 AND recall >= 0.7"
```

---

## Category IMP-G: Knowledge Graph Value Proof (EXISTENTIAL)

**Why This Category Exists**: The knowledge graph is the architectural foundation of AlphaSwarm.sol. If agents don't use it meaningfully, or if it doesn't improve detection quality, the entire project collapses to a fancy Slither wrapper. These items prove the graph is essential, not decorative.

### IMP-G1: Graph Ablation Study

**Problem**: No evidence that the knowledge graph improves agent reasoning vs. code-only analysis.

**Why This Matters**: If agents can produce equivalent findings without the graph, the graph is overhead. The graph's value must be proven empirically.

**Required Validation**:
```yaml
ablation_study:
  control_condition:
    name: "without_graph"
    method: "Run /vrs-audit with --no-graph flag OR disable BSKG queries"
    capture: [findings, evidence_depth, reasoning_quality, graph_node_citations]

  test_condition:
    name: "with_graph"
    method: "Run /vrs-audit normally with full BSKG access"
    capture: [same_metrics]

  comparison_metrics:
    - finding_count: "with_graph >= without_graph * 1.2 (20% more findings)"
    - evidence_depth: "with_graph citations > without_graph * 1.5"
    - cross_function: "with_graph detects cross-function vulns that without_graph misses"
    - graph_node_usage: "with_graph cites ≥5 distinct graph nodes per finding"

  test_contracts:
    - "tests/contracts/CrossFunctionReentrancy.sol" (requires path analysis)
    - "tests/contracts/semantic-test-set/AuthBypass.sol" (requires semantic ops)
    - "tests/fixtures/dvd/side-entrance/" (requires economic context)

  success_threshold:
    critical: "with_graph outperforms without_graph on ≥2 of 3 contracts"
    existential: "If ablation shows no difference, HALT and redesign graph integration"
```

**Implementation Requirements**:
1. Add `--no-graph` flag to `/vrs-audit` skill (or create control variant)
2. Create ablation test protocol in `.planning/testing/templates/ABLATION-PROTOCOL.md`
3. Execute both conditions on 3+ contracts with known vulnerabilities
4. Document results with honest assessment of graph value

**Blocks**: Project justification. If graph doesn't help, project needs fundamental redesign.

**Files to Create**:
- `CREATE: .planning/testing/templates/ABLATION-PROTOCOL.md`
- `UPDATE: /vrs-audit skill` (add --no-graph flag or control mode)

---

### IMP-G2: Graph Query Effectiveness Measurement

**Problem**: No metrics on whether VQL queries return useful results for vulnerability detection.

**Why This Matters**: Queries could return empty sets, irrelevant nodes, or overwhelming data. Query effectiveness determines graph utility.

**Required Validation**:
```yaml
query_effectiveness:
  metrics_per_query:
    - relevance: "% of returned nodes that appear in final findings"
    - coverage: "% of actual vulnerabilities that matching queries identify"
    - noise: "% of returned nodes that are irrelevant (false positives)"
    - timing: "Query execution time (should be <100ms for usability)"

  test_protocol:
    1. Run VQL-MIN queries on 5 vulnerable contracts
    2. Record: nodes_returned, nodes_used_in_findings, execution_time
    3. Compare to ground truth: queries_that_found_vulns / total_vulns

  success_criteria:
    relevance: ">= 30% of returned nodes used in reasoning"
    coverage: ">= 60% of vulns reachable via standard queries"
    noise: "<= 50% irrelevant nodes"
    timing: "<= 100ms per query"

  failure_action:
    if_coverage_low: "Add new queries to VQL-MIN set"
    if_noise_high: "Refine query filters or add semantic constraints"
    if_timing_slow: "Optimize graph indices or simplify queries"
```

**Blocks**: IMP-B5 (VQL library), I-03 (graph-first proof)

**Files to Create**:
- `CREATE: scripts/measure_query_effectiveness.py`
- `CREATE: .planning/testing/templates/QUERY-EFFECTIVENESS-REPORT.md`

---

### IMP-G3: Graph Node Citation Traceability

**Problem**: Findings may claim to use graph evidence but citations are fabricated or generic.

**Why This Matters**: Agents could cite "node-123" without that node existing or being relevant. Evidence must be verifiable.

**Required Validation**:
```yaml
citation_traceability:
  verification_steps:
    1. Extract all graph node IDs from finding evidence (e.g., "node-fn-withdraw-42")
    2. Query BSKG: Does node exist? What are its properties?
    3. Verify relevance: Does node's semantic operation match finding type?
    4. Cross-reference: Did a VQL query return this node before the conclusion?

  automated_check:
    script: "scripts/verify_graph_citations.py"
    input: "evidence_pack.json"
    output:
      - valid_citations: [list of verified node IDs]
      - invalid_citations: [list of non-existent or irrelevant nodes]
      - citation_validity_rate: "valid / total"

  success_criteria:
    validity_rate: ">= 90% of cited nodes exist and are relevant"
    query_traceability: ">= 80% of citations appear in preceding VQL results"

  anti_fabrication:
    - Node IDs must match BSKG schema (not made-up format)
    - Cited properties must exist on the node
    - Findings without valid citations → FAIL evidence check
```

**Blocks**: Plan 15 (orchestration proof), Plan 16 (debate validation)

**Files to Create**:
- `CREATE: scripts/verify_graph_citations.py`

---

## Category IMP-H: Multi-Agent Value Proof (EXISTENTIAL)

**Why This Category Exists**: The attacker/defender/verifier debate is the core differentiator from single-agent tools. If debate doesn't produce better verdicts than a single agent, the complexity is unjustified.

### IMP-H1: Single-Agent vs Multi-Agent Comparison

**Problem**: No baseline proving multi-agent debate improves outcomes vs. single-agent review.

**Why This Matters**: Multi-agent orchestration is expensive (3x+ token cost, complexity). Must prove it's worth it.

**Required Validation**:
```yaml
multi_agent_comparison:
  single_agent_baseline:
    agent: "vrs-secure-reviewer"
    mode: "solo"
    task: "Review {contract} for vulnerabilities"
    capture:
      - finding_count
      - evidence_depth (graph nodes cited)
      - reasoning_length (tokens)
      - verdict_confidence
      - false_positive_count (vs ground truth)
      - false_negative_count (vs ground truth)

  multi_agent_test:
    agents: ["vrs-attacker", "vrs-defender", "vrs-verifier"]
    mode: "debate"
    capture: [same_metrics]

  comparison_requirements:
    - Run BOTH modes on SAME contract (identical conditions)
    - Use 3+ contracts with known vulnerabilities
    - Record token cost for each mode

  success_criteria:
    quality_improvement:
      - "multi_agent.false_negatives < single_agent.false_negatives"
      - "multi_agent.evidence_depth > single_agent.evidence_depth * 1.3"
      - "multi_agent.reasoning shows synthesis (not just concatenation)"

    cost_justification:
      - "If 3x cost but 1.5x quality → MARGINAL (document trade-off)"
      - "If 3x cost but <1.2x quality → FAIL (reconsider architecture)"
      - "If 3x cost and 2x+ quality → SUCCESS"

  existential_check:
    if_no_improvement: "Document honestly. Consider simpler architecture."
```

**Blocks**: Plan 16 (debate validation), I-02 (agent spawn validation)

**Files to Create**:
- `CREATE: .planning/testing/templates/SINGLE-VS-MULTI-COMPARISON.md`
- `UPDATE: IMP-C4` (integrate baseline comparison)

---

### IMP-H2: Debate Quality Assessment

**Problem**: Debate could be performative (agents talk but don't influence each other).

**Why This Matters**: Real debate means verifier considers attacker AND defender arguments. Fake debate is just concatenated outputs.

**Required Validation**:
```yaml
debate_quality:
  indicators_of_real_debate:
    - attacker_challenge: "Attacker explicitly addresses defender's guard claims"
    - defender_rebuttal: "Defender responds to attacker's exploit hypothesis"
    - verifier_synthesis: "Verifier cites SPECIFIC claims from both sides"
    - verdict_differs: "Verifier verdict ≠ simple attacker conclusion"
    - evidence_flow: "Graph nodes from attacker appear in verifier reasoning"

  indicators_of_fake_debate:
    - no_cross_reference: "Agents don't reference each other's outputs"
    - template_responses: "Boilerplate structure with no specific content"
    - identical_conclusions: "All 3 agents say same thing (no synthesis)"
    - missing_conflict: "No disagreement or nuance between agents"

  measurement_protocol:
    1. Parse transcript for agent turns
    2. Extract cross-references (agent A mentions agent B's claim)
    3. Check for specific citations (not generic "attacker says...")
    4. Compare verifier verdict to raw attacker conclusion
    5. Score: cross_refs + specific_citations + verdict_nuance

  success_criteria:
    cross_references: "≥2 explicit cross-references per debate"
    specific_citations: "Verifier cites ≥1 specific claim from each side"
    verdict_nuance: "Verifier adds reasoning not present in attacker OR defender"

  anti_boilerplate:
    detection: "If 3 debates have >80% structural similarity → BOILERPLATE ALERT"
    action: "Improve agent prompts with anti-template instructions"
```

**Blocks**: Plan 16 T2

**Files to Create**:
- `CREATE: scripts/analyze_debate_quality.py`

---

### IMP-H3: Verifier Independence Validation

**Problem**: Verifier could rubber-stamp attacker conclusions without adding value.

**Why This Matters**: If verifier just agrees with attacker, it's a waste of tokens. Verifier must add independent judgment.

**Required Validation**:
```yaml
verifier_independence:
  test_cases:
    - scenario: "Attacker claims HIGH, Defender claims SAFE"
      expected: "Verifier weighs evidence, may disagree with attacker"

    - scenario: "Attacker claims MEDIUM, Defender partial mitigation"
      expected: "Verifier provides nuanced verdict with confidence"

    - scenario: "Attacker wrong (false positive)"
      expected: "Verifier rejects or downgrades attacker claim"

  metrics:
    agreement_rate: "% of verdicts where verifier = attacker conclusion"
    rejection_rate: "% of verdicts where verifier disagrees with attacker"
    confidence_correlation: "Does verifier confidence track evidence quality?"

  success_criteria:
    - agreement_rate: "<= 80% (verifier sometimes disagrees)"
    - rejection_rate: ">= 10% (verifier catches some false positives)"
    - evidence_based: "Every disagreement cites specific defender evidence"

  failure_indicators:
    - 100% agreement: "Verifier is rubber stamp → redesign verifier prompt"
    - 0% rejection: "Verifier never catches FPs → add skepticism to prompt"
    - no_evidence_cited: "Verifier decides without evidence → enforce evidence requirement"
```

**Files to Create**:
- `UPDATE: .claude/agents/vrs-verifier/` (add independence requirements)

---

## Category IMP-I: Pattern Reasoning Effectiveness (HIGH)

**Why This Category Exists**: Behavioral detection (semantic operations, patterns) is the core innovation. Must prove it works better than name-based detection.

### IMP-I1: Behavioral vs Name-Based Detection Comparison

**Problem**: No proof that behavioral detection (semantic ops) outperforms name-based detection.

**Why This Matters**: "Names lie, behavior doesn't" is the thesis. Must prove behavior-based detection catches more bugs.

**Required Validation**:
```yaml
behavioral_comparison:
  name_based_baseline:
    method: "Match function names: withdraw, transfer, send, call"
    detection: "Flag any function with dangerous names"
    capture: [findings, false_positives, false_negatives]

  behavioral_detection:
    method: "Match semantic operations: R:bal → X:out → W:bal"
    detection: "Flag operation sequences regardless of names"
    capture: [same_metrics]

  test_contracts:
    # Contracts where names are misleading
    - "tests/contracts/semantic-test-set/RenamedWithdraw.sol"
      # withdraw() renamed to processUserRequest()
    - "tests/contracts/semantic-test-set/SafeNameUnsafeCode.sol"
      # safeTransfer() that's actually vulnerable
    - "tests/contracts/semantic-test-set/ObfuscatedReentrancy.sol"
      # Reentrancy via callback with innocent names

  success_criteria:
    behavioral_advantage:
      - "Behavioral detects vulns in renamed functions (name-based misses)"
      - "Behavioral has lower FP rate on safe-named functions"
      - "Behavioral catches ≥2 vulns that name-based misses"

  existential_check:
    if_no_advantage: "Behavioral detection not proven valuable. Simplify to name-based?"
```

**Blocks**: Plan 09 (pattern evaluation), I-04 (semantic accuracy)

**Files to Create**:
- `CREATE: tests/contracts/semantic-test-set/RenamedWithdraw.sol`
- `CREATE: tests/contracts/semantic-test-set/SafeNameUnsafeCode.sol`
- `CREATE: tests/contracts/semantic-test-set/ObfuscatedReentrancy.sol`
- `CREATE: .planning/testing/templates/BEHAVIORAL-VS-NAME-COMPARISON.md`

---

### IMP-I2: Pattern Precision/Recall Per Vulnerability Class

**Problem**: Patterns may work for some vulnerability classes but fail for others. No per-class metrics.

**Why This Matters**: Claiming "pattern-based detection works" without per-class breakdown hides weaknesses.

**Required Validation**:
```yaml
per_class_metrics:
  vulnerability_classes:
    - class: "reentrancy"
      tier: "A"
      expected_precision: ">= 80%"
      expected_recall: ">= 70%"
      test_contracts: ["classic-reentrancy.sol", "cross-function-reentrancy.sol", "read-only-reentrancy.sol"]

    - class: "access_control"
      tier: "A/B"
      expected_precision: ">= 75%"
      expected_recall: ">= 65%"
      test_contracts: ["missing-auth.sol", "incorrect-modifier.sol", "role-bypass.sol"]

    - class: "oracle_manipulation"
      tier: "B/C"
      expected_precision: ">= 60%"
      expected_recall: ">= 50%"
      test_contracts: ["spot-price-oracle.sol", "twap-manipulation.sol"]

    - class: "economic_exploits"
      tier: "C"
      expected_precision: ">= 50%"
      expected_recall: ">= 40%"
      test_contracts: ["flash-loan-attack.sol", "sandwich-attack.sol"]

  reporting_format:
    | Class | Tier | Precision | Recall | Status |
    |-------|------|-----------|--------|--------|
    | reentrancy | A | 85% | 72% | SUPPORTED |
    | access_control | A/B | 78% | 68% | SUPPORTED |
    | oracle_manipulation | B/C | 55% | 45% | PARTIAL |
    | economic_exploits | C | 42% | 35% | LIMITED |

  success_criteria:
    - "≥2 classes meet 'SUPPORTED' threshold"
    - "No class has precision < 30% (too noisy to be useful)"
    - "Tier expectations are respected (Tier A > Tier B > Tier C)"

  capability_documentation:
    - Document which classes are "Supported", "Partial", "Limited", "Out of Scope"
    - Link each rating to test evidence
    - Update capability doc when patterns improve
```

**Blocks**: Plan 09 (pattern evaluation), I-07 (capability boundaries)

**Files to Create**:
- `CREATE: .planning/testing/templates/PER-CLASS-METRICS-REPORT.md`
- `UPDATE: docs/reference/capability-boundaries.md` (add per-class breakdown)

---

## Category IMP-J: Execution Infrastructure (CRITICAL - v4)

**Why This Category Exists**: v3 identified WHAT needs to be validated but not HOW to execute validations. These items provide the concrete execution infrastructure.

### IMP-J1: Decision Trees for Existential Validations

**Problem**: IMP-G, H, I describe WHAT to test but not the decision logic when tests fail.

**Why This Matters**: Without decision trees:
1. Unclear when to HALT vs iterate
2. No defined thresholds for "failure"
3. Risk of ignoring negative results

**Required Decision Trees**:
```yaml
IMP-G1_decision_tree:
  name: "Graph Ablation Decision Tree"

  metric_collection:
    - metric: "finding_delta"
      formula: "(test_findings - control_findings) / control_findings"
    - metric: "evidence_delta"
      formula: "(test_evidence_depth - control_evidence_depth) / control_evidence_depth"
    - metric: "graph_usage"
      formula: "distinct_graph_nodes_cited / total_findings"

  decision_tree:
    L1_significant_improvement:
      condition: "finding_delta >= 0.20 AND evidence_delta >= 0.50 AND graph_usage >= 5"
      verdict: "GRAPH_ESSENTIAL"
      action: "Document success. Proceed with graph-first architecture."

    L2_moderate_improvement:
      condition: "finding_delta >= 0.10 AND evidence_delta >= 0.30 AND graph_usage >= 3"
      verdict: "GRAPH_HELPFUL"
      action: "Graph adds value but not essential. Document trade-offs."

    L3_marginal_improvement:
      condition: "finding_delta > 0 OR evidence_delta > 0"
      verdict: "GRAPH_MARGINAL"
      action: "HALT and conduct architecture review."

    L4_no_improvement:
      condition: "finding_delta <= 0 AND evidence_delta <= 0"
      verdict: "GRAPH_NOT_VALUABLE"
      action: "CRITICAL: HALT phase immediately. Redesign required."
```

**Files to Create**:
- `CREATE: .planning/testing/decision-trees/IMP-G1-graph-ablation.yaml`
- `CREATE: .planning/testing/decision-trees/IMP-H1-multi-agent.yaml`
- `CREATE: .planning/testing/decision-trees/IMP-I1-behavioral.yaml`

---

### IMP-J2: Concrete claude-code-controller Execution Sequences

**Problem**: Each IMP item describes WHAT to validate but not the exact claude-code-controller commands.

**Why This Matters**: Without concrete commands:
1. Ambiguity in validation execution
2. Inconsistent test approaches
3. No reproducible validation

**Required Execution Sequences**:
```yaml
IMP-G1_execution:
  name: "Graph Ablation Study"

  control_run:
    session: "vrs-demo-ablation-control-{timestamp}"
    commands:
      - cmd: "claude-code-controller launch zsh"
        capture: "pane_id"
      - cmd: "claude-code-controller send 'cd /path/to/project' --pane={pane_id}"
        wait: "idle --idle-time=2.0"
      - cmd: "claude-code-controller send 'claude' --pane={pane_id}"
        wait: "idle --idle-time=10.0"
      - cmd: "claude-code-controller send '/vrs-audit tests/contracts/CrossFunctionReentrancy.sol --no-graph' --pane={pane_id}"
        wait: "idle --idle-time=180.0 --timeout=600"
      - cmd: "claude-code-controller capture --pane={pane_id} --output=.vrs/testing/runs/ablation-control/transcript.txt"

  test_run:
    session: "vrs-demo-ablation-test-{timestamp}"
    commands:
      # Same as control but without --no-graph flag
```

**Files to Create**:
- `CREATE: .planning/testing/execution-sequences/IMP-G1-ablation.yaml`
- `CREATE: .planning/testing/execution-sequences/IMP-H1-single-vs-multi.yaml`
- `CREATE: .planning/testing/execution-sequences/I-01-orchestration-proof.yaml`
- `CREATE: .planning/testing/execution-sequences/I-05-e2e-pipeline.yaml`

---

### IMP-J3: Abort Criteria for Existential Tests

**Problem**: Existential validations describe success but not explicit abort criteria.

**Why This Matters**: Without abort criteria:
1. Risk of endless iteration on failing tests
2. No defined escalation path
3. Unclear when to stop

**Required Abort Criteria**:
```yaml
abort_criteria:
  IMP-G1_graph_ablation:
    max_iterations: 3
    abort_conditions:
      - condition: "Three consecutive runs show finding_delta < 0.05"
        action: "ABORT: Graph not providing value"
        escalation: "Architecture review within 48h"
      - condition: "Graph queries fail on >50% of test contracts"
        action: "ABORT: Graph implementation broken"

  IMP-H1_multi_agent:
    max_iterations: 3
    abort_conditions:
      - condition: "Multi-agent false_negatives >= single_agent false_negatives"
        action: "ABORT: Debate not catching more bugs"
      - condition: "Multi-agent cost > 5x single-agent with quality < 1.2x"
        action: "ABORT: Cost not justified"

  global_abort:
    condition: "Any two existential validations fail"
    action: "HALT PHASE"
    escalation: "Document all failures. Schedule architecture review."
```

**Files Created/Updated**:
- `CREATE: .planning/testing/decision-trees/abort-criteria.yaml` - DONE (2026-02-04)
- `CREATE: scripts/check_wave_gate.py` - DONE (2026-02-04)

**CLI Usage**:
```bash
# Check abort status for a validation
python scripts/check_wave_gate.py --check-abort --validation IMP-G1_graph_ablation

# Check wave gate status
python scripts/check_wave_gate.py --check-wave --wave 5

# Record an iteration result
python scripts/check_wave_gate.py --record-iteration --validation IMP-G1_graph_ablation \
    --metrics-file results.yaml --verdict L2 --notes "Iteration notes"

# Get full status report
python scripts/check_wave_gate.py --status
python scripts/check_wave_gate.py --status --json  # JSON output
```

---

### IMP-J4: Improvement File Reconciliation

**Problem**: Two improvement files exist with incompatible schemas:
- `07.3.1.6-IMPROVEMENTS.md`: Task-oriented (IMP-01 through IMP-22)
- `IMPROVEMENT-ROADMAP.md`: Strategic (IMP-A through IMP-I)

**Why This Matters**: No explicit mapping causes duplicate tracking and status drift.

**Required Reconciliation**:
```yaml
reconciliation_map:
  IMP-01: [IMP-B4]  # Skill alignment
  IMP-02: [IMP-A1]  # claude-code-controller consistency
  IMP-03: [IMP-A3, IMP-B2]  # Evidence pack
  IMP-06: [IMP-G1, IMP-G2]  # Graph ablation
  IMP-07: [HENTI-01]  # Performance
  IMP-20: [IMP-B1]  # Ground truth

  orphaned_strategic:
    - IMP-C2, IMP-C3, IMP-C4  # Need task items
    - IMP-G3, IMP-H1, IMP-H2, IMP-H3  # Need task items
    - IMP-I1, IMP-I2  # Need task items
```

**Files to Update**:
- `UPDATE: 07.3.1.6-IMPROVEMENTS.md` (add IMP-23 through IMP-31)
- `UPDATE: IMPROVEMENT-ROADMAP.md` (add reconciliation section)

---

## Category IMP-K: Technical Debt (HIGH - v4)

### IMP-K1: VQL Query Syntax Validation

**Problem**: IMP-B5 VQL queries use hypothetical syntax that may not match actual BSKG.

**Required Validation**:
```yaml
vql_validation:
  step_1: "Extract BSKG schema: uv run alphaswarm schema --format yaml"
  step_2: "Verify each VQL-MIN query parses: uv run alphaswarm query --dry-run"
  step_3: "Verify queries return results on test contracts"
```

**Files to Create**:
- `CREATE: scripts/validate_vql_queries.py`
- `CREATE: .vrs/schema/bskg-schema.yaml`

---

### IMP-K2: Ground Truth Corpus Seeding

**Problem**: IMP-B1 defines structure but no actual data exists.

**Required Seeding**:
```yaml
minimum_corpus:
  code4rena: 5 contracts
  smartbugs: 3 contracts
  internal: 2 contracts
  total_findings: 30+
```

**Files to Create**:
- `CREATE: .vrs/corpus/ground-truth/provenance.yaml` (with data)
- `CREATE: scripts/verify_ground_truth_checksums.py`

---

### IMP-K3: Graph Disable Mechanism

**Problem**: IMP-G1 requires `--no-graph` flag but it doesn't exist.

**Required Implementation**:
```yaml
options:
  cli_flag: "Add --no-graph to alphaswarm audit"
  settings: "Create .vrs/settings-no-graph.yaml"
  skill_variant: "Create /vrs-audit-no-graph"
```

**Files to Modify**:
- `UPDATE: src/alphaswarm_sol/cli/audit.py` (add flag)
- `UPDATE: .claude/skills/vrs-audit/SKILL.md` (document flag)

---

### IMP-K4: Evidence Pack Schema Unification

**Problem**: Two evidence pack schemas exist (07.3.1.5 vs 07.3.2).

**Required Unification**:
```yaml
unified_schema_v2:
  required:
    - manifest.json (session metadata)
    - transcript.txt (raw output)
    - report.json (results)
    - environment.json (context)
  optional:
    - commands.log
    - ground_truth.json
    - proofs/
```

**Files to Update**:
- `UPDATE: scripts/validate_evidence_pack.py` (accept both, warn on old)
- `UPDATE: .planning/testing/guides/guide-evidence.md`

---

## Category IMP-L: Performance Infrastructure (MEDIUM - v4)

### IMP-L1: HENTI Performance Baselines

**Problem**: HENTI-01 defines metrics but no baseline values to compare.

**Required Baselines**:
```yaml
baseline_collection:
  test_contracts:
    - SimpleVault.sol (150 LOC)
    - MultiTokenVault.sol (450 LOC)
    - DeFiProtocol.sol (1200 LOC)
  runs_per_contract: 5
  metrics: [timing, tokens, throughput]
```

**Files to Create**:
- `CREATE: scripts/collect_henti_baseline.py`
- `CREATE: .vrs/benchmarks/baseline-initial.json`

---

### IMP-L2: Iteration Loop Entry Points

**Problem**: HENTI-03 describes loop but not how to trigger it.

**Required Entry Points**:
```yaml
automatic_triggers:
  - precision_below_50: "/vrs-refine --pattern {id}"
  - false_negative: "/vrs-investigate --mode gap_analysis"
  - boilerplate_detected: "Manual prompt update"
  - query_empty: "scripts/diagnose_empty_query.py"
```

**Files to Create**:
- `CREATE: scripts/run_iteration_loop.py`
- `CREATE: scripts/check_iteration_triggers.py`

---

### IMP-L3: Debate Quality Operationalization

**Problem**: IMP-H2 describes quality but not programmatic measurement.

**Required Operationalization**:
```yaml
metrics:
  cross_reference_detection:
    patterns: ["(Attacker|Defender) (claims|argues)", "per Attacker"]
    threshold: ">= 2 per debate"
  specific_citation_detection:
    patterns: ["node|function|line|L\\d+"]
    threshold: ">= 0.5 specificity ratio"
  boilerplate_detection:
    method: "structural similarity across 3 debates"
    threshold: "< 80% similarity"
```

**Files to Create**:
- `CREATE: scripts/analyze_debate_quality.py` (with all metrics)

---

### IMP-L4: Bidirectional Plan↔IMP Mapping

**Problem**: Plans reference IMPs but IMPs don't map back to plans.

**Required Mapping**:
```yaml
plan_to_imp:
  plan_01: [IMP-A1, IMP-A2, IMP-A3, IMP-A4, IMP-A5]
  plan_02: [IMP-B2, IMP-B3, IMP-C1]
  # ...

imp_to_plan:
  IMP-A1: {implemented_by: plan_01, validated_by: [plan_02, plan_03]}
  # ...

orphans:
  IMP-B4: {recommended_owner: plan_14}
  IMP-G1: {recommended_owner: "pre-completion gate"}
```

---

# Part 2: High-Level Validations (I-01 to I-07)

These validate that the system WORKS. They depend on IMP-A through IMP-L being resolved first.

**Important:** I-01 through I-07 cannot produce trustworthy results until:
- IMP-G (Graph Value Proof) confirms graph is essential
- IMP-H (Multi-Agent Value Proof) confirms debate improves outcomes
- IMP-I (Pattern Effectiveness) confirms behavioral detection works
- IMP-J (Execution Infrastructure) provides decision trees and abort criteria

If existential validations fail, I-01 through I-07 may need redesign.

---

## I-01: Orchestration Behavior Proof (HIGH PRIORITY)

### Gap Identified

Plans describe Claude Code using TaskCreate/TaskUpdate and spawning agents, but **no plan validates this actually happens**.

### Why This Matters

If orchestration doesn't work, the system collapses to single-agent CLI calls—no different from Slither.

### Proposed Validation

```
1. Run /vrs-audit on contract with known vulnerabilities
2. Parse transcript for orchestration markers (per IMP-A1)
3. Fail if ANY required marker missing
4. Record timestamps to prove sequencing
```

**Success Criteria**:
- Transcript contains all 9 stage markers
- ≥3 TaskCreate invocations
- ≥2 subagent spawns
- Markers in correct sequence

**Depends On**: IMP-A1 (marker spec), IMP-A2 (thresholds), IMP-J2 (execution sequences)

---

## I-02: Agent Spawn and Return Validation (HIGH PRIORITY)

### Gap Identified

Plans reference agents but don't test:
1. Spawn actually occurs
2. Output feeds into verification
3. Debate produces reasoned verdicts

### Why This Matters

Attacker/defender/verifier debate is the core differentiator. Without it, findings are pattern matches with LLM summary.

### Proposed Validation

```
1. Contract with medium-complexity vulnerability
2. Run /vrs-audit with agent tracing
3. Capture:
   - vrs-attacker: exploit hypothesis + nodes
   - vrs-defender: guard analysis + nodes
   - vrs-verifier: verdict citing both
4. Validate verifier cites specific claims
```

**Success Criteria**:
- 3 agents spawned for ≥1 bead
- Each output contains graph node refs
- Verifier addresses attacker AND defender claims
- Verdict has confidence rationale

**Depends On**: IMP-C4 (baseline), IMP-B3 (test contracts), IMP-H1-H3 (multi-agent proof)

---

## I-03: Graph-First Reasoning Proof (HIGH PRIORITY)

### Gap Identified

Philosophy mandates "No manual code reading before BSKG queries" but no validation that:
1. Agents query BSKG before conclusions
2. Conclusions cite graph node IDs
3. Graph contains sufficient semantic info

### Why This Matters

If agents skip BSKG, the knowledge graph is decorative. Behavioral detection requires graph usage.

### Proposed Validation

```
1. Contract with vulnerability detectable via semantic ops
2. Run /vrs-audit with query tracing
3. For each agent:
   - VQL query BEFORE conclusion
   - Conclusion cites graph nodes
4. Count: queries_before vs conclusions_without
```

**Success Criteria**:
- ≥80% conclusions have preceding queries
- All verdicts cite ≥2 graph node IDs
- Evidence packets contain operation sequences

**Depends On**: IMP-C2 (enforcement mechanism), IMP-G1-G3 (graph value proof)

---

## I-04: Semantic Operation Accuracy Validation (MEDIUM PRIORITY)

### Gap Identified

System relies on semantic operations for detection. No validation that:
1. Labeler assigns correct operations
2. Sequences indicate vulnerabilities
3. False labels don't cause false positives

### Proposed Validation

```
1. 50 functions with known behavior
2. Compare: labeler ops vs manual annotation
3. For vulnerable: check indicator sequences present
4. For safe: check indicator sequences absent
```

**Success Criteria**:
- Precision ≥85%
- Vulnerable have expected sequences ≥80%
- Safe don't have false sequences ≥90%

**Depends On**: IMP-F3 (threshold), IMP-B3 (semantic-test-set), IMP-I1-I2 (pattern effectiveness)

---

## I-05: End-to-End Pipeline Validation (HIGH PRIORITY)

### Gap Identified

Plans test components individually but no plan tests complete pipeline from invocation to report.

### Proposed Validation

```
1. Fresh environment (clean .vrs/)
2. Run: install → /vrs-audit → report
3. Validate:
   - Report exists, non-empty
   - ≥1 finding with evidence
   - Finding traces to graph + code
4. Compare to ground truth
```

**Success Criteria**:
- Pipeline completes 60-600s
- ≥1 true positive
- Fabricated evidence rejected
- Precision ≥50% (realistic)

**Depends On**: IMP-B1 (ground truth), IMP-B2 (templates), IMP-J2 (execution sequences)

---

## I-06: Resume and Checkpoint Validation (MEDIUM PRIORITY)

### Gap Identified

Plan 06 mentions resume but doesn't validate:
1. Interrupted audits resume from checkpoint
2. Completed work not reprocessed
3. State preserved across resume

### Proposed Validation

```
1. Start audit, interrupt after graph + 2 beads
2. Verify AUDIT-PROGRESS.md has checkpoint
3. Resume with --resume
4. Validate:
   - No graph rebuild
   - No bead reprocess
   - Final report complete
```

**Success Criteria**:
- Resume recognized and executed
- No duplicate work
- Final report = uninterrupted equivalent

**Depends On**: IMP-D4 (checkpoint format)

---

## I-07: Capability Boundary Documentation (MEDIUM PRIORITY)

### Gap Identified

Plans assume all vulnerabilities should be found. No documentation of:
1. In-scope classes
2. Out-of-scope classes
3. Expected failure modes

### Proposed Validation

```
1. Categorize by tier (A/B/C)
2. Run on curated set with labels
3. Measure success per category
4. Document:
   - ≥70% recall: "Supported"
   - 40-70%: "Partial"
   - <40%: "Out of Scope"
```

**Success Criteria**:
- Capability doc with evidence links
- ≥3 classes "Supported"
- ≥2 classes "Out of Scope" with rationale

**Depends On**: IMP-B1 (ground truth), IMP-B3 (test contracts), IMP-I2 (per-class metrics)

---

# Part 3: System-Level Performance Validations

These validate that the orchestrated system performs as intended at scale and under real-world conditions.

---

## HENTI-01: Multi-Orchestration Performance Benchmarking

### Gap Identified

The HENTI (Human-like ENhanced Testing Infrastructure) multi-orchestration system has no performance benchmarks proving it operates efficiently.

### Why This Matters

Multi-agent orchestration is expensive. Without performance benchmarks:
1. Cannot identify bottlenecks
2. Cannot optimize token usage
3. Cannot predict costs for real audits
4. Cannot compare to simpler alternatives

### Proposed Validation

```yaml
henti_performance_benchmarks:
  timing_benchmarks:
    - metric: "graph_build_time"
      target: "<30s for <1000 LOC, <60s for <5000 LOC"

    - metric: "full_debate_cycle_time"
      target: "<120s per bead"

    - metric: "total_audit_time"
      target: "120-600s for single contract"

  token_benchmarks:
    - metric: "tokens_per_agent"
      target: "attacker <4k, defender <3k, verifier <5k"

    - metric: "tokens_per_audit"
      target: "<100k tokens for single contract"

  success_criteria:
    - All timing targets met OR documented blockers
    - Token usage within budget
    - No memory leaks or hung processes
```

**Blocks**: Production readiness, cost estimation

**Depends On**: IMP-L1 (baselines)

**Files to Create**:
- `CREATE: scripts/benchmark_henti_performance.py`
- `CREATE: .planning/testing/templates/HENTI-PERFORMANCE-REPORT.md`

---

## HENTI-02: Real Human Behavior Simulation

### Gap Identified

Current tests execute commands mechanically. No validation that workflows match real human auditor behavior patterns.

### Why This Matters

A human auditor:
- Pauses to think between actions
- Re-reads outputs before proceeding
- Backtracks when confused
- Iterates on findings
- Asks clarifying questions

If tests don't simulate this, they may pass on mechanical execution but fail on realistic usage.

### Proposed Validation

```yaml
human_behavior_simulation:
  scenario_types:
    - type: "confident_user"
      behavior: "Execute commands quickly, minimal pauses"

    - type: "careful_user"
      behavior: "Read outputs, pause frequently, verify steps"

    - type: "confused_user"
      behavior: "Try wrong commands, need help, backtrack"

    - type: "interrupted_user"
      behavior: "Start, stop, come back later"

  success_criteria:
    - "Workflows succeed for all 4 user types"
    - "Error recovery guidance is helpful"
    - "Resume works after any interrupt point"
```

**Files to Create**:
- `CREATE: .planning/testing/templates/HUMAN-BEHAVIOR-SCENARIOS.md`
- `UPDATE: .planning/testing/guides/guide-claude-code-controller.md` (add human-like timing patterns)

---

## HENTI-03: Iteration and Learning Loop Validation

### Gap Identified

No validation that the system improves when results fall short.

### Why This Matters

A static testing system that never improves is brittle. Must prove:
1. Failures are detected automatically
2. Improvement actions are identified
3. Re-runs show improvement
4. Learning is captured for future runs

### Proposed Validation

```yaml
iteration_loop:
  failure_detection:
    - trigger: "precision < 50%"
      action: "Flag pattern for refinement"

    - trigger: "false_negative on ground truth"
      action: "Analyze why vuln was missed"

  improvement_protocol:
    1. Record failure with full context
    2. Classify failure type
    3. Apply improvement
    4. Re-run same scenario
    5. Compare before/after metrics

  success_criteria:
    - "≥1 documented iteration with improvement"
    - "Re-run shows measurable improvement"
    - "Learning log captures the iteration"
```

**Depends On**: IMP-L2 (entry points)

**Files to Create**:
- `CREATE: scripts/run_iteration_loop.py`
- `CREATE: .vrs/learning/iteration-log.yaml` (template)

---

# Part 4: Implementation Priority Matrix

## Wave 0: Blocking Definitions (Do FIRST - CRITICAL)

| Item | Effort | Blocks | Status |
|------|--------|--------|--------|
| IMP-A1 Markers | Medium | Plans 01, 03, 15, 16, I-01 | TODO |
| IMP-A2 Thresholds | Low | All plans, I-01 | TODO |
| IMP-A3 Proof Tokens | Medium | Plan 02, all evidence | TODO |
| IMP-A4 EI/CTL | Medium | Plan 01, 07 | TODO |
| IMP-A5 Tier C | Low | Plan 03, 07 | TODO |

**Gate:** Cannot proceed to Wave 0.5 until ALL Wave 0 items are DONE.

## Wave 0.5: Execution Infrastructure (NEW in v4)

| Item | Effort | Blocks | Status |
|------|--------|--------|--------|
| IMP-J1 Decision Trees | Medium | Wave 5 (existential) | DONE |
| IMP-J2 Execution Sequences | Medium | All validations | IN PROGRESS (4/4 files) |
| IMP-J3 Abort Criteria | Low | Wave 5 (existential) | DONE (abort-criteria.yaml + check_wave_gate.py) |
| IMP-J4 File Reconciliation | Low | Tracking | DONE |

**Gate:** Cannot run existential validations without decision trees and abort criteria.

## Wave 1: Missing Artifacts (Before Plan Execution)

| Item | Effort | Blocks | Status |
|------|--------|--------|--------|
| IMP-B1 Ground Truth | High | Plans 05, 06, 15, I-05, I-07 | TODO |
| IMP-B2 Templates | Medium | Plans 11, 12, 13, 15 | TODO |
| IMP-B3 Contracts | Low | Plans 09-16, I-02, I-04 | TODO |
| IMP-B4 Skills | Low | All plans | TODO |
| IMP-B5 VQL Library | Medium | IMP-C2, I-03 | TODO |
| IMP-K1 VQL Validation | Medium | IMP-B5 | TODO |
| IMP-K2 GT Seeding | High | IMP-B1 | TODO |

**Gate:** Cannot start plan execution until Wave 1 complete.

## Wave 2: Validation Mechanisms (Before Testing)

| Item | Effort | Blocks | Status |
|------|--------|--------|--------|
| IMP-C1 Measurement | Low | All validation | TODO |
| IMP-C2 Graph-First | Medium | Plan 03, I-03 | TODO |
| IMP-C3 Control Run | Low | Plan 12 | TODO |
| IMP-C4 Baseline | Medium | Plan 16, I-02 | TODO |
| IMP-K3 Graph Disable | Medium | IMP-G1 | TODO |
| IMP-K4 Pack Unification | Low | Evidence validation | TODO |

**Gate:** Cannot validate results until Wave 2 complete.

## Wave 3: Logical Fixes (During Execution)

| Item | Effort | Blocks | Status |
|------|--------|--------|--------|
| IMP-D1 Plan 15 Deps | Low | Plan 15 | TODO |
| IMP-D2 Freeze | Low | All plans | TODO |
| IMP-D3 Hard Case | Medium | Plan 13 | TODO |
| IMP-D4 Checkpoint | Medium | Plan 06, I-06 | TODO |

## Wave 4: Integration & Clarity (Ongoing)

| Item | Effort | Blocks | Status |
|------|--------|--------|--------|
| IMP-E1-E3 | Low-Medium | Various | TODO |
| IMP-F1-F3 | Low | Documentation | TODO |
| IMP-L3 Debate Metrics | Medium | IMP-H2 | TODO |
| IMP-L4 Plan Mapping | Low | Traceability | TODO |

## Wave 5: Existential Validations (CRITICAL - Project Justification)

**Why Wave 5 is Critical:** If these fail, the project's core architecture may need redesign.

| Item | Effort | Blocks | Status |
|------|--------|--------|--------|
| IMP-G1 Graph Ablation | High | Project justification | TODO |
| IMP-G2 Query Effectiveness | Medium | Graph utility proof | TODO |
| IMP-G3 Citation Traceability | Medium | Evidence integrity | TODO |
| IMP-H1 Single vs Multi | High | Architecture justification | TODO |
| IMP-H2 Debate Quality | Medium | Multi-agent value | TODO |
| IMP-H3 Verifier Independence | Medium | Verifier utility | TODO |
| IMP-I1 Behavioral vs Name | High | Detection philosophy | TODO |
| IMP-I2 Per-Class Metrics | Medium | Capability documentation | TODO |

**EXISTENTIAL GATE with Decision Trees (IMP-J1):**
- If IMP-G1 shows graph has no value → Follow L3/L4 decision tree → HALT or redesign
- If IMP-H1 shows multi-agent has no improvement → Follow decision tree → HALT or simplify
- If IMP-I1 shows behavioral detection has no advantage → Follow decision tree → HALT or reconsider

## Wave 6: High-Level Validations (After IMP Complete)

| Item | Priority | Depends On | Status |
|------|----------|------------|--------|
| I-01 | HIGH | IMP-A1, A2, G1-G3, J2 | TODO |
| I-02 | HIGH | IMP-C4, B3, H1-H3, J2 | TODO |
| I-03 | HIGH | IMP-C2, B5, G2, J2 | TODO |
| I-05 | HIGH | IMP-B1, B2, J2 | TODO |
| I-04 | MEDIUM | IMP-F3, B3, I1-I2 | TODO |
| I-06 | MEDIUM | IMP-D4 | TODO |
| I-07 | MEDIUM | IMP-B1, B3, I2 | TODO |

## Wave 7: HENTI System-Level Validations (Performance & Behavior)

| Item | Effort | Blocks | Status |
|------|--------|--------|--------|
| HENTI-01 Performance | High | Production readiness | TODO |
| HENTI-02 Human Behavior | Medium | Realistic validation | TODO |
| HENTI-03 Iteration Loop | Medium | Continuous improvement | TODO |
| IMP-L1 Baselines | Medium | HENTI-01 | TODO |
| IMP-L2 Entry Points | Medium | HENTI-03 | TODO |

**Gate:** Cannot claim "production ready" until HENTI validations complete.

---

# Execution Sequence Summary (v4)

```
Wave 0: Definitions → Gate: All specs locked (IMP-A1 to A5)
    ↓
Wave 0.5: Execution Infrastructure → Gate: Decision trees, sequences ready (IMP-J1 to J4)
    ↓
Wave 1: Artifacts → Gate: All templates/contracts/GT exist (IMP-B1 to B5, K1-K2)
    ↓
Wave 2: Mechanisms → Gate: All validators ready (IMP-C1 to C4, K3-K4)
    ↓
Wave 3: Fixes → Gate: All logical flaws resolved (IMP-D1 to D4)
    ↓
Wave 4: Integration → Gate: Cross-plan flow verified (IMP-E1-E3, F1-F3, L3-L4)
    ↓
Wave 5: EXISTENTIAL → Gate: Graph/Multi-Agent/Behavioral PROVEN valuable
    ↓                       (IMP-G1-G3, H1-H3, I1-I2)
    ↓                       **Use decision trees (IMP-J1)**
    ↓                       **If ANY fails → follow abort criteria (IMP-J3)**
Wave 6: Validations → Gate: I-01 to I-07 complete with evidence
    ↓
Wave 7: HENTI System → Gate: Performance + human behavior validated
    ↓                        (HENTI-01-03, IMP-L1-L2)
    ↓
PHASE COMPLETE → GA RELEASE READY
```

---

# Document Maintenance

Update this roadmap:
- When item completed → mark DONE with date + evidence link
- When gap discovered → add to appropriate category
- When item unnecessary → mark SKIPPED with reason
- When existential test fails → follow decision tree (IMP-J1), execute abort criteria (IMP-J3)
- When iteration improves metrics → update tracking

**Tracking:**
- Total items: 44 IMP + 7 I + 3 HENTI = **54 total improvements**
- Wave 0 (Definitions): 5 items - **5 DONE**
- Wave 0.5 (Execution Infrastructure): 4 items - **4 DONE** (IMP-J1 trees, IMP-J2 sequences, IMP-J3 abort, IMP-J4 reconciliation)
- Wave 1 (Artifacts): 7 items
- Wave 2 (Mechanisms): 6 items
- Wave 3 (Fixes): 4 items
- Wave 4 (Integration): 7 items
- Wave 5 (Existential): 8 items
- Wave 6 (Validations): 7 items
- Wave 7 (HENTI): 6 items
- **Completed: 9** (IMP-A1, IMP-A2, IMP-A3, IMP-A4, IMP-A5, IMP-J1, IMP-J2, IMP-J3, IMP-J4)
- **In Progress: 0**
- **Next: Wave 1 (Artifacts)** - IMP-B1 to B5, IMP-K1, IMP-K2

---

# Quick Reference: Files to Create

**Wave 0 (Definitions):**
- [x] `.planning/testing/rules/canonical/ORCHESTRATION-MARKERS.md` (IMP-A1) ✅ DONE 2026-02-04
- [x] `.planning/testing/rules/canonical/PROOF-TOKEN-MATRIX.md` (IMP-A3) ✅ DONE 2026-02-04
- [x] `docs/reference/economic-intelligence-spec.md` (IMP-A4) ✅ DONE 2026-02-04
- [x] RULES-ESSENTIAL.md updated with IMP-A2 thresholds + IMP-A5 Tier C section ✅ DONE 2026-02-04

**Wave 0.5 (Execution Infrastructure):**
- [x] `.planning/testing/decision-trees/IMP-G1-graph-ablation.yaml` (IMP-J1) ✅ DONE 2026-02-04
- [x] `.planning/testing/decision-trees/IMP-H1-multi-agent.yaml` (IMP-J1) ✅ DONE 2026-02-04
- [x] `.planning/testing/decision-trees/IMP-I1-behavioral.yaml` (IMP-J1) ✅ DONE 2026-02-04
- [x] `.planning/testing/execution-sequences/IMP-G1-ablation.yaml` (IMP-J2) ✅ DONE 2026-02-04
- [x] `.planning/testing/execution-sequences/I-01-orchestration-proof.yaml` (IMP-J2) ✅ DONE 2026-02-04
- [x] `.planning/testing/execution-sequences/IMP-H1-single-vs-multi.yaml` (IMP-J2) ✅ DONE 2026-02-04
- [x] `.planning/testing/execution-sequences/I-05-e2e-pipeline.yaml` (IMP-J2) ✅ DONE 2026-02-04

**Wave 1 (Artifacts):**
- `.vrs/corpus/ground-truth/provenance.yaml` (IMP-B1, IMP-K2)
- `.planning/testing/templates/PATH-EXPLORATION-TEMPLATE.md` (IMP-B2)
- `.planning/testing/scenarios/economic/ECONOMIC-MODEL-LIBRARY.md` (IMP-B2)
- `.planning/testing/templates/PATTERN-DISCOVERY-LOG.md` (IMP-B2)
- `.planning/testing/guides/guide-orchestration-proof.md` (IMP-B2)
- `tests/contracts/MANIFEST.yaml` update (IMP-B3)
- `docs/reference/vql-library.md` (IMP-B5)
- `src/alphaswarm_sol/kg/queries/vql_minimum_set.yaml` (IMP-B5)
- `scripts/validate_vql_queries.py` (IMP-K1)
- `.vrs/schema/bskg-schema.yaml` (IMP-K1)
- `scripts/verify_ground_truth_checksums.py` (IMP-K2)

**Wave 2 (Mechanisms):**
- `.planning/testing/rules/canonical/TRANSCRIPT-MEASUREMENT.md` (IMP-C1)
- `scripts/validate_graph_first.py` (IMP-C2)
- `.vrs/settings-no-economic.yaml` (IMP-C3)
- `.planning/testing/templates/DEBATE-BASELINE-COMPARISON.md` (IMP-C4)
- `.vrs/settings-no-graph.yaml` or CLI flag (IMP-K3)

**Wave 3 (Fixes):**
- `tests/contracts/hard-case/NovelStorageCollision.sol` (IMP-D3)
- `docs/reference/checkpoint-format.md` (IMP-D4)

**Wave 4 (Integration):**
- `scripts/check_wave_gate.py` (IMP-E2)
- `scripts/analyze_debate_quality.py` (IMP-L3)

**Wave 5 (Existential):**
- `.planning/testing/templates/ABLATION-PROTOCOL.md` (IMP-G1)
- `scripts/measure_query_effectiveness.py` (IMP-G2)
- `.planning/testing/templates/QUERY-EFFECTIVENESS-REPORT.md` (IMP-G2)
- `scripts/verify_graph_citations.py` (IMP-G3)
- `.planning/testing/templates/SINGLE-VS-MULTI-COMPARISON.md` (IMP-H1)
- `tests/contracts/semantic-test-set/RenamedWithdraw.sol` (IMP-I1)
- `tests/contracts/semantic-test-set/SafeNameUnsafeCode.sol` (IMP-I1)
- `tests/contracts/semantic-test-set/ObfuscatedReentrancy.sol` (IMP-I1)
- `.planning/testing/templates/BEHAVIORAL-VS-NAME-COMPARISON.md` (IMP-I1)
- `.planning/testing/templates/PER-CLASS-METRICS-REPORT.md` (IMP-I2)

**Wave 7 (HENTI):**
- `scripts/benchmark_henti_performance.py` (HENTI-01)
- `.planning/testing/templates/HENTI-PERFORMANCE-REPORT.md` (HENTI-01)
- `scripts/collect_henti_baseline.py` (IMP-L1)
- `.vrs/benchmarks/baseline-initial.json` (IMP-L1)
- `.planning/testing/templates/HUMAN-BEHAVIOR-SCENARIOS.md` (HENTI-02)
- `scripts/run_iteration_loop.py` (HENTI-03, IMP-L2)
- `scripts/check_iteration_triggers.py` (IMP-L2)
- `.vrs/learning/iteration-log.yaml` (HENTI-03)

---

**Last Updated**: 2026-02-04 (IMP-J4 reconciliation complete)
**Status**: Active - Wave 0 definitions complete, Wave 0.5 execution infrastructure in progress
**Completed**: IMP-A1 (markers), IMP-A2 (thresholds), IMP-A3 (proof tokens), IMP-A4 (EI/CTL), IMP-A5 (Tier C), IMP-J1 (decision trees), IMP-J4 (file reconciliation)
**Next Action**: Complete IMP-J2 (execution sequences) and IMP-J3 (abort criteria) then proceed to Wave 1

---

# Appendix: Critical Dependencies Summary

| If This Fails | Impact | Decision Tree | Action |
|---------------|--------|---------------|--------|
| IMP-G1 (Graph Ablation) | Graph may be decorative | IMP-J1 | Follow L1-L4 decision tree |
| IMP-H1 (Single vs Multi) | Multi-agent overhead not justified | IMP-J1 | Follow decision tree |
| IMP-I1 (Behavioral vs Name) | Behavioral detection not proven | IMP-J1 | Follow decision tree |
| IMP-B1 (Ground Truth) | Cannot validate precision/recall | N/A | Acquire external corpus before E2E |
| IMP-B5 (VQL Library) | Cannot enforce graph-first | N/A | Define minimum query set |
| Wave 5 (any existential) | Core architecture may need redesign | IMP-J3 | Follow abort criteria |

---

# Appendix: Improvement File Reconciliation Map

This section maps between the two improvement tracking systems:
- `07.3.1.6-IMPROVEMENTS.md`: Task-oriented (IMP-01 through IMP-31)
- `IMPROVEMENT-ROADMAP.md`: Strategic (IMP-A1 through IMP-L4)

**Status:** COMPLETE (IMP-J4 reconciliation completed 2026-02-04)

## Complete Bidirectional Mapping

### Task-Oriented to Strategic (IMP-01 to IMP-31)

```yaml
task_to_strategic_map:
  # Original task items (IMP-01 through IMP-22)
  IMP-01: [IMP-B4]         # Skill/Test-Framework Alignment
  IMP-02: [IMP-A1]         # claude-code-controller skill vs CLI consistency
  IMP-03: [IMP-A3, IMP-B2] # Evidence Pack Schema
  IMP-04: [IMP-E1]         # Scenario Manifest Schema
  IMP-05: [IMP-A1]         # Canonical Marker Registry
  IMP-06: [IMP-G1, IMP-G2] # Graph Contribution & Ablation
  IMP-07: [HENTI-01]       # Multi-Orchestration Performance
  IMP-08: [IMP-A4, IMP-A5] # Context Quality Gate
  IMP-09: [IMP-B2]         # Economic Modeling Library
  IMP-10: [IMP-B2]         # Missing Templates
  IMP-11: [IMP-B4]         # Command Inventory
  IMP-12: [IMP-D1, IMP-D2] # Plan-Doc Path Corrections
  IMP-13: [IMP-B4]         # Canonical Skill Source
  IMP-14: [IMP-F2]         # Evidence Pack Location
  IMP-15: [IMP-E1]         # Scenario Manifest Alignment
  IMP-16: [IMP-A1]         # Context Gate Marker Unification
  IMP-17: [IMP-C1]         # claude-code-agent-teams Workflow Realism
  IMP-18: [IMP-D1]         # Plan Dependency Alignment
  IMP-19: [IMP-B3]         # Missing Fixtures
  IMP-20: [IMP-B1]         # External Ground Truth
  IMP-21: [IMP-A1]         # Session Label Enforcement
  IMP-22: [IMP-F1]         # Doc Index Coverage

  # New task items (IMP-23 through IMP-31) covering orphaned strategic items
  IMP-23: [IMP-C2]         # Graph-First Enforcement Mechanism
  IMP-24: [IMP-C3]         # Control Run Mechanism (Economic Context)
  IMP-25: [IMP-C4]         # Debate Quality Baseline
  IMP-26: [IMP-G3]         # Graph Citation Traceability
  IMP-27: [IMP-H1]         # Single-Agent vs Multi-Agent Comparison
  IMP-28: [IMP-H2]         # Debate Quality Assessment
  IMP-29: [IMP-H3]         # Verifier Independence Validation
  IMP-30: [IMP-I1]         # Behavioral vs Name-Based Detection
  IMP-31: [IMP-I2]         # Per-Class Pattern Metrics
```

### Strategic to Task-Oriented

```yaml
strategic_to_task_map:
  # Category IMP-A: Blocking Definitions
  IMP-A1: [IMP-02, IMP-05, IMP-16, IMP-21]  # Marker specs
  IMP-A2: []                                  # Thresholds (in RULES-ESSENTIAL)
  IMP-A3: [IMP-03]                            # Proof tokens
  IMP-A4: [IMP-08]                            # EI/CTL
  IMP-A5: [IMP-08]                            # Tier C

  # Category IMP-B: Missing Artifacts
  IMP-B1: [IMP-20]                            # Ground truth corpus
  IMP-B2: [IMP-03, IMP-09, IMP-10]            # Templates
  IMP-B3: [IMP-19]                            # Test contracts
  IMP-B4: [IMP-01, IMP-11, IMP-13]            # Skills
  IMP-B5: []                                  # VQL library (standalone)

  # Category IMP-C: Validation Mechanisms
  IMP-C1: [IMP-17]                            # Transcript measurement
  IMP-C2: [IMP-23]                            # Graph-first enforcement
  IMP-C3: [IMP-24]                            # Control run
  IMP-C4: [IMP-25]                            # Debate baseline

  # Category IMP-D: Logical Flaws
  IMP-D1: [IMP-12, IMP-18]                    # Plan deps
  IMP-D2: [IMP-12]                            # Circular deps
  IMP-D3: []                                  # Hard-case (standalone)
  IMP-D4: []                                  # Checkpoint (standalone)

  # Category IMP-E: Integration Gaps
  IMP-E1: [IMP-04, IMP-15]                    # Manifest alignment
  IMP-E2: []                                  # Wave gate (standalone)
  IMP-E3: []                                  # Tool bypass (standalone)

  # Category IMP-F: Clarity & Consistency
  IMP-F1: [IMP-22]                            # Plan-B10 mapping
  IMP-F2: [IMP-14]                            # Evidence directory
  IMP-F3: []                                  # Semantic accuracy (standalone)

  # Category IMP-G: Knowledge Graph Value Proof (EXISTENTIAL)
  IMP-G1: [IMP-06]                            # Graph ablation
  IMP-G2: [IMP-06]                            # Query effectiveness
  IMP-G3: [IMP-26]                            # Citation traceability

  # Category IMP-H: Multi-Agent Value Proof (EXISTENTIAL)
  IMP-H1: [IMP-27]                            # Single vs multi
  IMP-H2: [IMP-28]                            # Debate quality
  IMP-H3: [IMP-29]                            # Verifier independence

  # Category IMP-I: Pattern Reasoning Effectiveness
  IMP-I1: [IMP-30]                            # Behavioral vs name
  IMP-I2: [IMP-31]                            # Per-class metrics

  # Categories IMP-J, K, L: Infrastructure (standalone)
  IMP-J1 to J4: []                            # Execution infrastructure
  IMP-K1 to K4: []                            # Technical debt
  IMP-L1 to L4: []                            # Performance infrastructure

  # High-Level Validations (standalone)
  I-01 to I-07: []                            # Validation protocols
  HENTI-01: [IMP-07]                          # Performance benchmarks
  HENTI-02 to 03: []                          # System-level (standalone)
```

### Reconciliation Summary

| Category | Task Items | Strategic Items | Coverage |
|----------|------------|-----------------|----------|
| Blocking Definitions | IMP-02,05,08,16,21 | IMP-A1 to A5 | 100% |
| Missing Artifacts | IMP-01,03,09,10,11,13,19,20 | IMP-B1 to B5 | 100% |
| Validation Mechanisms | IMP-17,23,24,25 | IMP-C1 to C4 | 100% |
| Logical Flaws | IMP-12,18 | IMP-D1 to D4 | Partial |
| Integration Gaps | IMP-04,15 | IMP-E1 to E3 | Partial |
| Clarity & Consistency | IMP-14,22 | IMP-F1 to F3 | Partial |
| Graph Value Proof | IMP-06,26 | IMP-G1 to G3 | 100% |
| Multi-Agent Proof | IMP-27,28,29 | IMP-H1 to H3 | 100% |
| Pattern Effectiveness | IMP-30,31 | IMP-I1 to I2 | 100% |

### Previously Orphaned Items (Now Mapped)

All previously orphaned strategic items now have task-oriented equivalents:

| Strategic | Task | Description |
|-----------|------|-------------|
| IMP-C2 | IMP-23 | Graph-first enforcement mechanism |
| IMP-C3 | IMP-24 | Control run mechanism |
| IMP-C4 | IMP-25 | Debate quality baseline |
| IMP-G3 | IMP-26 | Citation traceability |
| IMP-H1 | IMP-27 | Single vs multi comparison |
| IMP-H2 | IMP-28 | Debate quality assessment |
| IMP-H3 | IMP-29 | Verifier independence |
| IMP-I1 | IMP-30 | Behavioral vs name detection |
| IMP-I2 | IMP-31 | Per-class metrics |

### Standalone Items (Remain Unlinked)

Infrastructure and implementation items that don't need task equivalents:
- IMP-A2 (thresholds) — defined in RULES-ESSENTIAL.md
- IMP-B5 (VQL library) — standalone artifact creation
- IMP-D3, D4 (hard-case, checkpoint) — standalone specs
- IMP-E2, E3 (wave gate, tool bypass) — standalone scripts/specs
- IMP-F3 (semantic accuracy) — embedded in I-04
- IMP-J1 to J4 — execution infrastructure
- IMP-K1 to K4 — technical debt
- IMP-L1 to L4 — performance infrastructure
- I-01 to I-07 — high-level validations
- HENTI-02, HENTI-03 — system-level validations

---

# Appendix: Bidirectional Plan↔IMP Mapping

## Plan → IMP Mapping

```yaml
plan_to_imp_mapping:
  plan_01:
    implements: [IMP-A1, IMP-A2, IMP-A3, IMP-A4, IMP-A5]
    validates: []
    note: "Definition gate - creates all foundational specs"

  plan_02:
    implements: [IMP-B2, IMP-B3, IMP-C1]
    validates: [IMP-A1, IMP-A2, IMP-A3]
    note: "Evidence standardization + B1 install proof"

  plan_03:
    implements: [IMP-C2, IMP-E1, IMP-E3]
    validates: [IMP-A1, IMP-A4, IMP-A5]
    note: "Orchestration hardening + workflow contracts"

  plan_04:
    implements: [IMP-B5, IMP-C4]
    validates: [IMP-C2]
    note: "Tier B/C harness + VQL library"

  plan_05:
    implements: [IMP-F1, IMP-F2]
    validates: [I-07]
    note: "Coverage + robustness + capability boundaries"

  plan_06:
    implements: [IMP-B1, IMP-D4]
    validates: [I-06]
    note: "Phase exit + provenance + resume"

  plan_07:
    implements: []
    validates: [IMP-A4, IMP-A5]
    note: "Context quality gate validation"

  plan_08:
    implements: [IMP-D3]
    validates: []
    note: "Hard-case library"

  plan_09:
    implements: [IMP-I2]
    validates: [I-04]
    note: "Pattern evaluation + semantic accuracy"

  plan_10:
    implements: []
    validates: [IMP-E3]
    note: "Tool maximization + bypass handling"

  plan_11:
    implements: []
    validates: [IMP-B5]
    note: "Cross-function path exploration"

  plan_12:
    implements: [IMP-C3]
    validates: [IMP-A4]
    note: "Economic behavior modeling"

  plan_13:
    implements: []
    validates: []
    note: "Novel pattern discovery pipeline"

  plan_14:
    implements: []
    validates: [IMP-B4]
    note: "Naming alignment"

  plan_15:
    implements: []
    validates: [I-01, I-05]
    note: "Orchestration + E2E proof (CRITICAL)"

  plan_16:
    implements: []
    validates: [I-02, IMP-H2, IMP-H3]
    note: "Multi-agent debate proof (CRITICAL)"
```

## IMP → Plan Mapping

```yaml
imp_to_plan_mapping:
  # Wave 0 - Definitions
  IMP-A1: {implemented_by: plan_01, validated_by: [plan_02, plan_03]}
  IMP-A2: {implemented_by: plan_01, validated_by: plan_02}
  IMP-A3: {implemented_by: plan_01, validated_by: plan_02}
  IMP-A4: {implemented_by: plan_01, validated_by: [plan_03, plan_07, plan_12]}
  IMP-A5: {implemented_by: plan_01, validated_by: [plan_03, plan_07]}

  # Wave 1 - Artifacts
  IMP-B1: {implemented_by: plan_06, validated_by: [plan_15]}
  IMP-B2: {implemented_by: plan_02, validated_by: []}
  IMP-B3: {implemented_by: plan_02, validated_by: [plan_08]}
  IMP-B4: {implemented_by: null, validated_by: [plan_14]}  # ORPHAN
  IMP-B5: {implemented_by: plan_04, validated_by: [plan_11]}

  # Wave 2 - Mechanisms
  IMP-C1: {implemented_by: plan_02, validated_by: []}
  IMP-C2: {implemented_by: plan_03, validated_by: [plan_04, plan_09]}
  IMP-C3: {implemented_by: plan_12, validated_by: []}
  IMP-C4: {implemented_by: plan_04, validated_by: [plan_16]}

  # Orphans (need implementing plan or pre-completion gate)
  orphans:
    IMP-B4: {recommended_owner: plan_14, action: "Add skill verification"}
    IMP-G1: {recommended_owner: "pre-completion gate", action: "Execute ablation study"}
    IMP-G2: {recommended_owner: "plan_04 OR plan_11", action: "Add query metrics"}
    IMP-G3: {recommended_owner: "plan_09 OR plan_15", action: "Add citation verification"}
    IMP-H1: {recommended_owner: plan_16, action: "Add baseline comparison"}
    IMP-H2: {recommended_owner: plan_16, action: "Expand metrics"}
    IMP-H3: {recommended_owner: plan_16, action: "Add independence check"}
    IMP-I1: {recommended_owner: plan_09, action: "Add comparison protocol"}
    IMP-I2: {recommended_owner: plan_09, action: "Ensure per-class breakdown"}
```

---

# Appendix: VQL Query Validation Protocol

Before using VQL-MIN queries, validate against actual BSKG schema:

```yaml
vql_validation_protocol:
  step_1_schema_extraction:
    description: "Extract actual BSKG node and edge types"
    command: "uv run alphaswarm schema --format yaml > .vrs/schema/bskg-schema.yaml"
    output_fields:
      - node_types: ["Function", "Contract", "Variable", "Modifier", ...]
      - edge_types: ["CALLS", "READS", "WRITES", "HAS_MODIFIER", ...]
      - property_names: ["visibility", "has_reentrancy_guard", "transfers_eth", ...]

  step_2_query_syntax_validation:
    description: "Verify each VQL-MIN query parses successfully"
    for_each_query:
      - parse: "uv run alphaswarm query --dry-run '{query}'"
      - expected: "exit code 0, no syntax errors"
      - on_failure: "Rewrite query to match actual schema"

  step_3_query_result_validation:
    description: "Verify queries return expected results on test contracts"
    test_contract: "tests/contracts/semantic-test-set/KnownVulnerable.sol"
    for_each_query:
      - execute: "uv run alphaswarm query '{query}' --output json"
      - verify: "result contains expected node IDs"
      - on_empty: "Flag as potentially ineffective"

  rewrite_candidates:
    VQL-MIN-04:
      original: "MATCH (f)-[:READS_USER_BALANCE]->(b)-[:CALLS_EXTERNAL]->(t)-[:WRITES_USER_BALANCE]->(w)"
      issue: "Edge names may differ from semantic operation names"
      potential_rewrite: |
        # May need property-based query instead:
        MATCH (f:Function)
        WHERE f.reads_user_balance = true
          AND f.calls_external = true
          AND f.writes_user_balance = true
        RETURN f
```

---

# Appendix: Ground Truth Corpus Seeding

Minimum viable ground truth corpus specification:

```yaml
ground_truth_seed:
  code4rena_entries:
    - contest: "2023-01-ondo"
      url: "https://code4rena.com/reports/2023-01-ondo"
      contracts:
        - name: "OndoFlashLoan.sol"
          findings:
            - id: "H-01"
              severity: "High"
              type: "reentrancy"
              location: "flashLoan():L142-L168"
              description: "Flash loan callback allows reentrancy before state update"
      retrieval_date: "2026-02-04"
      checksum: "sha256:..."

    - contest: "2023-03-asymmetry"
      url: "https://code4rena.com/reports/2023-03-asymmetry"
      contracts:
        - name: "SafEth.sol"
          findings:
            - id: "H-02"
              severity: "High"
              type: "access_control"
              location: "setMaxSlippage():L89"
              description: "Missing access control on critical setter"
      retrieval_date: "2026-02-04"
      checksum: "sha256:..."

  minimum_viable_corpus:
    total_contracts: 10
    by_source:
      code4rena: 5
      smartbugs: 3
      internal_annotated: 2
    by_vulnerability:
      reentrancy: 4
      access_control: 3
      oracle_manipulation: 2
      economic_exploit: 1
    coverage_target: "At least 1 contract per Tier (A, B, C)"
```

---

# Appendix: Graph Disable Implementation Options

For IMP-G1 ablation study, implement graph disable via one of:

```yaml
graph_disable_options:
  option_1_cli_flag:  # RECOMMENDED
    implementation: "Add --no-graph flag to alphaswarm audit command"
    behavior:
      - "Skip knowledge graph build"
      - "Disable all VQL queries"
      - "Agents fall back to direct code reading"
      - "Emit [GRAPH_DISABLED] marker in transcript"
    pros: "Clean, explicit, easy to verify"
    cons: "Requires CLI modification"
    effort: "Medium"

  option_2_settings_override:
    implementation: "Create .vrs/settings-no-graph.yaml"
    content: |
      graph:
        enabled: false
        fallback: "code_reading"
      detection:
        skip_vql_queries: true
    pros: "No code changes"
    cons: "May not fully disable graph if hardcoded"
    effort: "Low"

  option_3_skill_variant:
    implementation: "Create /vrs-audit-no-graph skill"
    behavior: "Copy of /vrs-audit with graph steps removed"
    pros: "Complete isolation"
    cons: "Skill duplication, maintenance burden"
    effort: "Medium"

  verification:
    - "Run /vrs-audit --no-graph on test contract"
    - "Verify transcript contains [GRAPH_DISABLED] marker"
    - "Verify NO VQL queries executed"
    - "Verify agents use direct code reading"
```

---

# Appendix: Debate Quality Metrics (Operationalized)

Programmatic measurement of multi-agent debate quality:

```yaml
debate_quality_metrics:
  cross_reference_detection:
    description: "Detect when agents reference each other's claims"
    patterns:
      - regex: "(Attacker|Defender|Verifier)\\s+(claims|argues|asserts|states)\\s+that"
      - regex: "(as|per|according to)\\s+(Attacker|Defender|Verifier)"
      - regex: "(challenging|disputing|confirming)\\s+(Attacker|Defender)'s"
    measurement:
      script: "scripts/analyze_debate_quality.py"
      function: "count_cross_references(transcript)"
      output: "cross_ref_count: int"
    threshold:
      minimum: 2
      good: 4
      excellent: 6+

  specific_citation_detection:
    description: "Detect specific vs generic citations"
    specific_patterns:
      - regex: "(node|function|line|L\\d+)\\s*:\\s*(\\w+)"
      - regex: "graph_node_id\\s*[=:]\\s*['\"]?([\\w-]+)"
    generic_patterns:
      - regex: "the (attacker|defender) (claims|says|argues)"
      - regex: "based on (the|this) analysis"
    measurement:
      function: "citation_specificity_ratio(transcript)"
      output: "specific_ratio: float (0.0-1.0)"
    threshold:
      minimum: 0.5
      good: 0.7
      excellent: 0.9+

  boilerplate_detection:
    description: "Detect template-filling without reasoning"
    method: "Compare 3+ debates for structural overlap"
    threshold: "If >80% structure identical → BOILERPLATE"
    generic_phrases:
      - "Based on the analysis"
      - "After careful review"
      - "The evidence suggests"
    measurement:
      function: "boilerplate_score(transcripts[])"
      output: "boilerplate_ratio: float (0.0-1.0)"
    threshold:
      acceptable: "<0.3"
      warning: "0.3-0.5"
      fail: ">0.5"

  composite_quality_score:
    formula: |
      quality = (
        cross_ref_score * 0.25 +
        specificity_score * 0.30 +
        nuance_score * 0.25 +
        (1 - boilerplate_ratio) * 0.20
      )
    thresholds:
      excellent: ">= 0.85"
      good: "0.70-0.84"
      acceptable: "0.50-0.69"
      poor: "< 0.50"
```

---

# Appendix: Evidence Pack Schema Unification

Two schemas exist; use unified v2:

```yaml
evidence_pack_unification:
  legacy_schemas:
    schema_07315:
      location: ".planning/phases/07.3.1.5-full-testing-orchestrator/"
      structure: |
        run_id/
        ├── transcript.txt
        ├── summary.json
        ├── metrics.json
        └── artifacts/
    schema_0732:
      location: ".planning/phases/07.3.2-execution-evidence-protocol/"
      structure: |
        run_id/
        ├── transcript.txt
        ├── report.json
        ├── manifest.json
        ├── environment.json
        └── proofs/

  unified_schema_v2:
    version: "2.0"
    structure: |
      run_id/
      ├── manifest.json        # Session metadata (required)
      ├── transcript.txt       # Raw output (required)
      ├── report.json          # Results + metrics (required)
      ├── environment.json     # Runtime context (required)
      ├── commands.log         # Executed commands (optional)
      ├── ground_truth.json    # External labels (if validation)
      └── proofs/              # Stage-specific proof tokens
          ├── proof-graph.json
          ├── proof-agents.json
          └── proof-report.json

    required_fields_manifest:
      - run_id
      - workflow
      - session_label
      - pane_id
      - timestamp_utc
      - git_commit
      - duration_ms
      - line_count
      - schema_version  # Track which schema

    migration_path:
      from_07315: "Add manifest.json with session_label, rename summary.json to report.json"
      from_0732: "Already compatible, add schema_version field"
```

---

# Appendix: HENTI Baseline Collection

Methodology for establishing performance baselines:

```yaml
henti_baseline_collection:
  methodology:
    - "Run 5 audits on standardized test contracts"
    - "Record all metrics per run"
    - "Calculate mean, stddev, p95 for each metric"
    - "Set targets as p50 (achievable) and p25 (stretch)"

  test_contracts:
    - name: "SimpleVault.sol"
      loc: 150
      complexity: "low"
      expected_findings: 1-2
    - name: "MultiTokenVault.sol"
      loc: 450
      complexity: "medium"
      expected_findings: 2-4
    - name: "DeFiProtocol.sol"
      loc: 1200
      complexity: "high"
      expected_findings: 4-8

  baseline_collection_protocol:
    runs_per_contract: 5
    total_runs: 15
    metrics_collected:
      - graph_build_time_ms
      - context_generation_time_ms
      - single_agent_response_time_ms
      - full_debate_cycle_time_ms
      - total_audit_time_ms
      - tokens_per_agent
      - tokens_per_audit
      - findings_per_audit

  output_format:
    file: ".vrs/benchmarks/baseline-{date}.json"
    example: |
      {
        "collection_date": "2026-02-04",
        "contracts_tested": [...],
        "runs_per_contract": 5,
        "metrics": {
          "graph_build_time_ms": {
            "mean": 12500,
            "stddev": 2100,
            "p50": 11800,
            "p95": 16200
          }
        }
      }
```

---

# Appendix: Iteration Loop Entry Points

Triggers and entry points for continuous improvement:

```yaml
iteration_loop_entry_points:
  automatic_triggers:
    - trigger: "precision_below_threshold"
      condition: "precision < 0.50 for any vulnerability class"
      action: "Flag pattern for refinement"
      entry_point: "/vrs-refine --pattern {pattern_id} --reason precision_low"

    - trigger: "false_negative_on_ground_truth"
      condition: "Known vulnerability not detected"
      action: "Analyze detection gap"
      entry_point: "/vrs-investigate --bead {bead_id} --mode gap_analysis"

    - trigger: "boilerplate_detected"
      condition: "boilerplate_ratio > 0.5 in debate"
      action: "Improve agent prompts"
      entry_point: "Manual: Update agent prompt, re-run debate"

    - trigger: "query_empty_result"
      condition: "VQL-MIN query returns 0 nodes on known vulnerable contract"
      action: "Check graph completeness"
      entry_point: "scripts/diagnose_empty_query.py --query {query_id} --contract {contract}"

  manual_triggers:
    - trigger: "review_feedback"
      description: "Human reviewer identifies improvement opportunity"
      entry_point: "/gsd:add-todo --description '{feedback}'"

    - trigger: "new_vulnerability_class"
      description: "Novel vulnerability type discovered"
      entry_point: "/vrs-add-vulnerability --url {source_url}"

  iteration_tracking:
    file: ".vrs/learning/iteration-log.yaml"
    entry_schema:
      iteration_id: "iter-{timestamp}"
      trigger: "trigger_name"
      before_metrics: {}
      improvement_applied: "description"
      after_metrics: {}
      delta: {}
      status: "improved|no_change|regressed"
```

---

# Appendix: Detailed Abort Criteria

Per-validation abort criteria for existential tests:

```yaml
abort_criteria:
  IMP-G1_graph_ablation:
    max_iterations: 3
    abort_conditions:
      - condition: "Three consecutive runs show finding_delta < 0.05"
        action: "ABORT: Graph not providing value"
        escalation: "Architecture review within 48h"
      - condition: "Graph queries fail on >50% of test contracts"
        action: "ABORT: Graph implementation broken"
        escalation: "Debug graph builder before continuing"
    continue_conditions:
      - condition: "finding_delta > 0.05 but < 0.20"
        action: "ITERATE: Try different query patterns"
        max_attempts: 2

  IMP-H1_multi_agent:
    max_iterations: 3
    abort_conditions:
      - condition: "Multi-agent false_negatives >= single_agent false_negatives"
        action: "ABORT: Debate not catching more bugs"
        escalation: "Consider single-agent architecture"
      - condition: "Multi-agent cost > 5x single-agent with quality < 1.2x"
        action: "ABORT: Cost not justified"
        escalation: "Document trade-off, consider hybrid"
    continue_conditions:
      - condition: "Multi-agent better on 1/3 contracts but not 2/3"
        action: "ITERATE: Analyze why debate helps some contracts"
        max_attempts: 2

  IMP-I1_behavioral_detection:
    max_iterations: 3
    abort_conditions:
      - condition: "Behavioral detection catches same or fewer vulns than name-based"
        action: "ABORT: Behavioral detection not advantageous"
        escalation: "Reconsider detection philosophy"
      - condition: "Behavioral false_positive_rate > 2x name-based"
        action: "ABORT: Too noisy to be useful"
        escalation: "Refine semantic operation definitions"
    continue_conditions:
      - condition: "Behavioral catches 1 extra vuln but misses 1 other"
        action: "ITERATE: Analyze edge cases"
        max_attempts: 2

  global_abort:
    condition: "Any two existential validations fail"
    action: "HALT PHASE"
    escalation: |
      1. Document all failures in STATE.md
      2. Schedule architecture review
      3. Prepare redesign proposals
      4. Do NOT proceed to GA validation
```

---

# Appendix: B10 Sub-Seed to Plan Mapping

| B10 Req | Description | Implemented In | Status |
|---------|-------------|----------------|--------|
| B10.A | Protocol Context Quality Gate | Plan 07 | TODO |
| B10.B | VQL Query Library | IMP-B5 | TODO |
| B10.C | Economic Loss Reasoning | Plan 12 | TODO |
| B10.D | Attack Surface Enumeration | Plan 04 | TODO |
| B10.E | Cross-Contract Reasoning | Plan 11 | TODO |
| B10.F | Mechanism-Level Invariants | Plan 04 | TODO |
| B10.G | False-Positive Suppression | Plan 09 | TODO |
| B10.H | Outcome Explainability | Plan 04 | TODO |
| B10.I | Prioritization Heuristic | Plan 04 | TODO |
| B10.J | Protocol Hard-Cases Library | Plan 08 | TODO |
| B10.K | Pattern Evaluation Protocol | Plan 09 | TODO |
| B10.L | Developer Tool Maximization | Plan 10 | TODO |
| B10.M | Cross-Function Path Exploration | Plan 11 | TODO |
| B10.N | Economic Behavior Modeling | Plan 12 | TODO |
| B10.O | Novel Pattern Discovery | Plan 13 | TODO |
| B10.P | Coverage Confidence Scoring | Plan 05 | TODO |
| B10.Q | Expert Reasoning Baseline | Plan 04 | TODO |

---

# Appendix: Anti-Patterns to Avoid

1. **Don't add metrics for metrics' sake** — Every metric must tie to a decision
2. **Don't create theoretical docs** — Every doc must be exercised in claude-code-agent-teams
3. **Don't expand scope** — Focus on unblocking, not adding requirements
4. **Don't fabricate baselines** — Control runs must be real executions
5. **Don't skip ground truth** — External provenance is mandatory
6. **Don't assume graph adds value** — Prove it with ablation study (IMP-G1)
7. **Don't assume multi-agent is better** — Prove it with comparison (IMP-H1)
8. **Don't accept boilerplate outputs** — Check for template-filling without reasoning
9. **Don't claim perfect metrics** — 100%/100% = fabrication, expect realistic variance
10. **Don't skip existential validations** — They determine if project architecture is sound
11. **Don't ignore decision trees** — Use IMP-J1 when existential tests fail (v4)
12. **Don't iterate endlessly** — Use IMP-J3 abort criteria to know when to stop (v4)
