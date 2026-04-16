# IMPROVEMENT-ROADMAP Improvement Proposals

**Phase:** 07.3.1.6-full-testing-hardening
**Created:** 2026-02-04
**Author:** Deep Analysis Agent
**Status:** Proposal for Review

---

## Executive Summary

After exhaustive review of all 16 plans, the testing framework, PHILOSOPHY.md, and the current IMPROVEMENT-ROADMAP (v4), I've identified **18 substantive improvements** organized into 5 categories. Each improvement addresses a real execution gap that would block or invalidate phase completion.

**Critical Finding:** The roadmap is well-structured but has **execution-readiness gaps** that will cause plans to fail during claude-code-controller execution. These aren't theoretical concerns—they are concrete missing artifacts, undefined mechanisms, and logical inconsistencies that will produce errors or fabricated results.

---

## Category 1: Execution Readiness (BLOCKING)

These improvements must be resolved before plans can execute successfully.

### IMP-M1: Test Contract Existence Verification Script

**Problem:** Plans 08, 09, 11, 12, 13, 15, 16 reference test contracts that **have not been verified to exist**:
- `tests/contracts/CrossFunctionReentrancy.sol`
- `tests/contracts/semantic-test-set/*.sol`
- `tests/contracts/hard-case/*.sol`
- `tests/fixtures/dvd/side-entrance/`

**Current State in IMPROVEMENT-ROADMAP:** IMP-B3 mentions "verify each exists OR document must be created" but provides no script or checklist.

**Why This Matters:** Every claude-code-controller execution will fail if the test contract doesn't exist. Anti-fabrication rules require **real execution**, not simulated. A missing contract causes plan failure.

**Required Improvement:**
```yaml
IMP-M1_test_contract_verification:
  description: "Create automated test contract verification"

  artifact_to_create: "scripts/verify_test_contracts.py"

  functionality:
    - Parse all plan files for contract references (regex: `tests/contracts/*.sol`, `tests/fixtures/*`)
    - Check each referenced path exists in filesystem
    - For missing contracts: output clear "MISSING: {path}" with which plan references it
    - For existing contracts: verify they compile (`solc` or `forge build`)

  output_format:
    ```
    TEST CONTRACT VERIFICATION REPORT
    =================================
    ✓ tests/contracts/CrossFunctionReentrancy.sol - EXISTS, COMPILES
    ✗ tests/contracts/semantic-test-set/RenamedWithdraw.sol - MISSING (Plan 09, IMP-I1)
    ✗ tests/contracts/hard-case/NovelStorageCollision.sol - MISSING (Plan 08, 13)

    BLOCKING: 3 missing contracts will cause 4 plans to fail
    ```

  blocking_impact: "Plans 08, 09, 11, 12, 13, 15, 16 cannot execute until all referenced contracts exist"

  suggested_wave: "Wave 1 prerequisite (before IMP-B3)"
  effort: Low
```

**Evidence of Gap:** Plan 11 task T3 explicitly calls `/vrs-audit tests/contracts/CrossFunctionReentrancy.sol`. If this file doesn't exist, the claude-code-agent-teams session will fail immediately. No plan verifies existence before execution.

---

### IMP-M2: VQL Query Schema Validation Before Execution

**Problem:** IMP-B5 defines VQL-MIN queries using **hypothetical Cypher-like syntax**:
```cypher
MATCH (f:Function)-[:HAS_MODIFIER]->(m) RETURN f, m
MATCH (f)-[:READS_USER_BALANCE]->(b)-[:CALLS_EXTERNAL]->(t)-[:WRITES_USER_BALANCE]->(w) RETURN f,b,t,w
```

But the **actual BSKG may use different edge types, node properties, or query syntax**.

**Current State in IMPROVEMENT-ROADMAP:** IMP-K1 mentions "verify VQL queries parse" but is in Wave 2 (Mechanisms) while VQL library (IMP-B5) is in Wave 1. This is a **dependency inversion**.

**Why This Matters:** If agents execute VQL queries that don't match the actual BSKG schema, queries will return empty results or errors. This makes graph-first validation (I-03) meaningless.

**Required Improvement:**
```yaml
IMP-M2_vql_schema_first:
  description: "Extract BSKG schema BEFORE defining VQL queries"

  dependency_fix:
    before: "IMP-B5 (VQL Library) must depend on schema extraction"
    after: "Schema extraction is prerequisite for VQL library"

  execution_sequence:
    1. Run `uv run alphaswarm build-kg tests/contracts/simple_vulnerable.sol` on a test contract
    2. Run `uv run alphaswarm schema --format yaml` to extract actual node/edge types
    3. Document actual schema in `.vrs/schema/bskg-schema.yaml`
    4. THEN write VQL-MIN queries that match actual schema
    5. Validate each query with `--dry-run` before adding to library

  verification_script: "scripts/validate_vql_queries.py"
    - For each VQL-MIN query: run `alphaswarm query --dry-run`
    - Fail loudly if any query has syntax errors
    - Report queries that return 0 results (may be ineffective)

  blocking_impact: "Without schema validation, VQL queries are theoretical and may never work"

  roadmap_update:
    move: "IMP-K1 (VQL Validation) from Wave 2 to Wave 1, before IMP-B5"
    reason: "Schema extraction must precede query authoring"

  effort: Medium
```

**Evidence of Gap:** The roadmap appendix shows "VQL Query Validation Protocol" but it's in an appendix, not in the wave execution order. No plan explicitly runs schema extraction before VQL authoring.

---

### IMP-M3: Graph Disable Mechanism Must Precede Ablation Study

**Problem:** IMP-G1 (Graph Ablation Study) requires running `/vrs-audit` **without the graph** to prove the graph adds value. But the `--no-graph` flag or settings variant **does not exist**.

**Current State in IMPROVEMENT-ROADMAP:** IMP-K3 defines the graph disable mechanism but is in Wave 2 (Mechanisms). IMP-G1 is in Wave 5 (Existential). This seems correct but there's a hidden dependency:

- Plans 11-15 may reference graph ablation comparisons as part of their validation
- If graph disable mechanism isn't implemented until Wave 2, any early plan that wants to demonstrate "with vs without graph" cannot do so

**Why This Matters:** The existential validation (IMP-G1) is the **most important test in the entire phase**. If it can't execute because the disable mechanism doesn't exist, the phase cannot complete with confidence.

**Required Improvement:**
```yaml
IMP-M3_graph_disable_early:
  description: "Implement graph disable mechanism in Wave 1, not Wave 2"

  rationale: |
    The graph ablation study is existential. All downstream validation depends on knowing
    whether the graph adds value. Delaying the disable mechanism risks:
    1. Plans making assumptions about graph value without evidence
    2. Ablation study being rushed at end of phase
    3. No time to react if graph proves unhelpful

  implementation_options:
    option_a:
      method: "CLI flag: --no-graph"
      changes: "Add flag to alphaswarm audit command"
      behavior: "Skip graph build, skip VQL queries, pattern matching only"
      marker: "[GRAPH_DISABLED reason=ablation_study]"

    option_b:
      method: "Settings override: .vrs/settings-no-graph.yaml"
      changes: "Add settings file that disables graph features"
      behavior: "Same as option_a but via config"

    option_c:
      method: "Skill variant: /vrs-audit-no-graph"
      changes: "Create parallel skill that skips graph"
      behavior: "Identical to /vrs-audit except graph features disabled"

  recommended: "option_a (CLI flag) - most explicit, easiest to verify in transcripts"

  roadmap_update:
    move: "IMP-K3 from Wave 2 to Wave 1"
    add_dependency: "IMP-G1 explicitly depends on IMP-K3"

  effort: Medium
```

**Evidence of Gap:** The decision tree for IMP-G1 (in `.planning/testing/decision-trees/`) requires metrics from both `with_graph` and `without_graph` runs. If `--no-graph` doesn't exist, the decision tree cannot be executed.

---

### IMP-M4: Single-Agent Baseline Skill for Multi-Agent Comparison

**Problem:** IMP-H1 (Single-Agent vs Multi-Agent Comparison) requires running the **same contract** with:
1. Single-agent mode (vrs-secure-reviewer only)
2. Multi-agent mode (attacker + defender + verifier)

No skill variant exists for single-agent mode.

**Current State in IMPROVEMENT-ROADMAP:** IMP-H1 describes what to compare but not **how to run single-agent mode**. The `/vrs-audit` skill always attempts multi-agent debate.

**Why This Matters:** Without a single-agent baseline, IMP-H1 cannot execute. The comparison is central to proving multi-agent value.

**Required Improvement:**
```yaml
IMP-M4_single_agent_mode:
  description: "Create mechanism for single-agent baseline runs"

  implementation_options:
    option_a:
      method: "CLI flag: --single-agent"
      behavior: "Run only vrs-secure-reviewer, skip attacker/defender/verifier debate"
      marker: "[SINGLE_AGENT_MODE agent=vrs-secure-reviewer]"

    option_b:
      method: "Skill variant: /vrs-audit-single"
      behavior: "Same as /vrs-audit but spawns only one agent"

    option_c:
      method: "Settings override: .vrs/settings-single-agent.yaml"
      behavior: "Configure debate_mode: single"

  metrics_to_capture_both_modes:
    - finding_count
    - evidence_depth (graph nodes cited per finding)
    - reasoning_length (tokens)
    - false_positive_count (vs ground truth)
    - false_negative_count (vs ground truth)
    - total_token_cost
    - execution_time

  comparison_protocol:
    1. Run single-agent on Contract X
    2. Run multi-agent on Contract X (same contract, same environment)
    3. Compare metrics
    4. Record cost ratio (multi-agent tokens / single-agent tokens)
    5. Record quality ratio (multi-agent quality / single-agent quality)
    6. Apply decision tree (IMP-J1 IMP-H1 section)

  roadmap_update:
    add: "IMP-M4 to Wave 2 (Mechanisms)"
    add_dependency: "IMP-H1 depends on IMP-M4"

  effort: Medium
```

**Evidence of Gap:** Plan 16 validates "debate produces better verdicts than single-agent" but has no mechanism to actually run single-agent mode.

---

## Category 2: Validation Mechanism Completeness

These improvements define missing measurement and enforcement mechanisms.

### IMP-M5: Anti-Fabrication Automation Script

**Problem:** Anti-fabrication rules (F1-F4) are documented in RULES-ESSENTIAL.md but enforcement is **manual**. A plan executor must:
1. Count transcript lines manually
2. Check duration manually
3. Search for tool markers manually
4. Check for 100%/100% metrics manually

**Current State in IMPROVEMENT-ROADMAP:** No automation script exists for anti-fabrication checking.

**Why This Matters:** Manual checking is error-prone and may not catch all fabrication. As plans execute in parallel, fabrication detection must be automated.

**Required Improvement:**
```yaml
IMP-M5_anti_fabrication_automation:
  description: "Create automated anti-fabrication checker for transcripts"

  artifact_to_create: "scripts/check_anti_fabrication.py"

  input: "Path to transcript file and test type (smoke/agent/e2e/multi_agent)"

  checks:
    F1_line_count:
      smoke: "min 50 lines"
      agent: "min 100 lines"
      e2e: "min 200 lines"
      multi_agent: "min 300 lines"

    F3_duration:
      smoke: "5s - 60s"
      agent: "30s - 300s"
      e2e: "120s - 600s"
      multi_agent: "180s - 600s"
      extract_method: "Parse first and last timestamps in transcript OR use manifest.json duration_ms"

    F2_tool_markers:
      required_any: ["alphaswarm", "slither", "aderyn", "mythril"]
      agent_required: ["vrs-attacker", "vrs-defender", "vrs-verifier"]

    F4_evidence_structure:
      check: "Findings have graph_nodes[], pattern_id, location"

    C1_perfect_metrics:
      flag: "Precision 100% OR Recall 100% OR Pass rate 100%"
      action: "ALERT: Perfect metrics detected - investigate for fabrication"

  output_format:
    ```
    ANTI-FABRICATION CHECK: .vrs/testing/runs/15-T1/transcript.txt
    ============================================================
    Type: e2e

    [✓] F1 Line Count: 347 lines (min 200) - PASS
    [✓] F3 Duration: 245s (range 120-600s) - PASS
    [✓] F2 Tool Markers: alphaswarm (L23), vrs-attacker (L89) - PASS
    [?] F4 Evidence: 3/4 findings have complete evidence - CHECK
    [!] C1 Perfect Metrics: Recall 100% detected - INVESTIGATE

    RESULT: NEEDS_INVESTIGATION (perfect recall suspicious)
    ```

  integration:
    - Call automatically after every claude-code-controller capture
    - Fail plan if FAIL result
    - Require human review if INVESTIGATE result

  effort: Medium
```

**Evidence of Gap:** No plan task includes anti-fabrication checking. The assumption is human review, but at scale (16 plans × multiple tasks), automation is necessary.

---

### IMP-M6: claude-code-agent-teams Session Isolation Verification Script

**Problem:** RULES-ESSENTIAL mandates claude-code-agent-teams session isolation (`vrs-demo-{workflow}-{timestamp}`) but no script verifies:
1. Session naming follows convention
2. Session is separate from dev environment
3. Pane cleanup only affects current run

**Current State in IMPROVEMENT-ROADMAP:** Rules exist but no enforcement mechanism.

**Why This Matters:** If plans execute in the dev session (not isolated demo session), results are contaminated. Evidence packs must record `session_label` and `pane_id` but no validation that these are correct.

**Required Improvement:**
```yaml
IMP-M6_session_isolation_verification:
  description: "Verify claude-code-agent-teams sessions follow isolation requirements"

  artifact_to_create: "scripts/verify_claude-code-agent-teams_isolation.py"

  pre_execution_checks:
    - Verify current session name matches `vrs-demo-*` pattern
    - Verify session is NOT the dev environment (check for active editor, shell history patterns)
    - Record session_label and pane_id for evidence pack

  post_execution_checks:
    - Verify no panes outside current `vrs-demo-*` session were killed
    - Verify manifest.json contains session_label and pane_id
    - Verify transcript references match manifest session

  integration_with_claude-code-agent-teams_cli:
    before_launch: "Call verify_claude-code-agent-teams_isolation.py --check-environment"
    after_capture: "Call verify_claude-code-agent-teams_isolation.py --verify-evidence {run_dir}"

  effort: Low
```

---

### IMP-M7: Graph Citation Verification Tool

**Problem:** IMP-G3 (Citation Traceability) requires verifying that graph node IDs cited in findings **actually exist in the BSKG**. No tool exists to perform this verification.

**Current State in IMPROVEMENT-ROADMAP:** IMP-G3 defines the requirement but `scripts/verify_graph_citations.py` is listed as "to create" with no specification.

**Why This Matters:** Agents could cite fabricated node IDs (e.g., "node-123" that doesn't exist). Without verification, evidence integrity is unproven.

**Required Improvement:**
```yaml
IMP-M7_graph_citation_verification:
  description: "Tool to verify graph node IDs exist and are relevant"

  artifact_to_create: "scripts/verify_graph_citations.py"

  input:
    - Evidence pack path (containing findings with node IDs)
    - Graph hash (to ensure checking against correct graph)

  verification_steps:
    1. Extract all node IDs from findings (regex: `node-[a-z0-9-]+` or actual BSKG format)
    2. For each node ID:
       a. Query BSKG: `alphaswarm query "MATCH (n) WHERE n.id = '{node_id}' RETURN n"`
       b. If no result: FLAG as INVALID_NODE
       c. If result: Extract node properties
    3. Verify relevance:
       a. Does node's semantic operation match finding type?
       b. Does node's file/line match finding location?
    4. Report:
       - valid_citations: [list]
       - invalid_citations: [list]
       - relevance_score: valid_relevant / total_citations

  thresholds_from_IMP_G3:
    validity_rate: ">= 90% of cited nodes must exist"
    query_traceability: ">= 80% of citations must appear in preceding VQL results"

  failure_action:
    if_validity_below_90: "FAIL finding - evidence not verifiable"
    if_invalid_citation: "Flag specific citation for review"

  effort: Medium
```

---

## Category 3: Plan Interdependency Fixes

These improvements fix logical flaws in plan dependencies.

### IMP-M8: Plan 15 Dependency Expansion

**Problem:** Plan 15 (Orchestration + E2E Proof) depends on Plans 03 and 04. But to prove the **full pipeline** works, it should also depend on:
- Plan 09 (Pattern Evaluation) - ensures patterns are evaluated correctly
- Plan 11 (Path Exploration) - ensures cross-function paths are explored
- Plan 14 (Naming Alignment) - ensures skills are invokable

**Current State in IMPROVEMENT-ROADMAP:** IMP-D1 mentions "Plan 15 should depend on 09-14" but the plan file itself hasn't been updated.

**Why This Matters:** If Plan 15 executes before Plans 09-14 complete, it may pass but not actually validate the full capability set.

**Required Improvement:**
```yaml
IMP-M8_plan15_dependency_fix:
  description: "Expand Plan 15 dependencies to ensure full pipeline validation"

  current_dependencies: ["03", "04"]

  required_dependencies: ["03", "04", "09", "10", "11", "12", "13", "14"]

  rationale:
    plan_09: "Pattern evaluation must work before E2E can validate findings quality"
    plan_10: "Tool maximization must work before E2E can validate tool integration"
    plan_11: "Path exploration must work before E2E can validate cross-function detection"
    plan_12: "Economic modeling must work before E2E can validate context-aware findings"
    plan_13: "Discovery pipeline must exist before E2E can validate coverage"
    plan_14: "Naming must be aligned before E2E can invoke skills correctly"

  update_required:
    file: ".planning/phases/07.3.1.6-full-testing-hardening/07.3.1.6-15-PLAN.md"
    change: "depends_on: ['03', '04'] -> depends_on: ['03', '04', '09', '10', '11', '12', '13', '14']"

  wave_impact:
    current: "Plan 15 in Wave 5"
    after_fix: "Plan 15 must wait for Wave 4 completion"
    note: "This is correct - E2E proof should be near-final validation"

  effort: Low
```

---

### IMP-M9: Circular Dependency Resolution - Definition Freeze Checkpoint

**Problem:** Plan 01 defines markers, thresholds, schemas. Plans 02-16 test against these definitions. But if Plans 02-16 reveal definition flaws:
- Must Plan 01 be re-executed?
- Do definitions change mid-phase?
- How is consistency maintained?

**Current State in IMPROVEMENT-ROADMAP:** IMP-D2 mentions "Definition Freeze checkpoint" but no mechanism exists.

**Why This Matters:** Without a freeze checkpoint, definitions could drift, causing inconsistent validation across plans.

**Required Improvement:**
```yaml
IMP-M9_definition_freeze_mechanism:
  description: "Implement definition freeze checkpoint after Plan 01"

  freeze_checkpoint:
    trigger: "Plan 01 completion"

    frozen_artifacts:
      - ".planning/testing/rules/canonical/ORCHESTRATION-MARKERS.md"
      - ".planning/testing/rules/canonical/PROOF-TOKEN-MATRIX.md"
      - ".planning/testing/rules/canonical/RULES-ESSENTIAL.md"
      - "docs/reference/economic-intelligence-spec.md"

    freeze_mechanism:
      option_a: "Git tag: definition-freeze-v1"
      option_b: "Hash verification: store SHA256 of each file"
      option_c: "Immutable copy: .planning/testing/frozen/wave0/"

    recommended: "option_b - hash verification is simplest"

  validation_script: "scripts/verify_definition_freeze.py"
    - Store hashes after Plan 01 completion
    - Before each subsequent plan: verify hashes unchanged
    - If hash mismatch: ALERT - definition drift detected

  change_request_process:
    if_definition_flaw_found:
      1. Document flaw in `.planning/phases/07.3.1.6-full-testing-hardening/DEFINITION-ISSUES.md`
      2. Complete current wave
      3. Schedule definition update for next wave boundary
      4. Update all affected plans after definition change
      5. Re-run affected validations

  effort: Low
```

---

### IMP-M10: Wave Prerequisite Automation

**Problem:** Wave gates are defined (Wave 0 → Wave 1 → ...) but enforcement is manual. The roadmap says "Gate: Cannot proceed to Wave 1 until Wave 0 complete" but no automation verifies this.

**Current State in IMPROVEMENT-ROADMAP:** IMP-E2 mentions `scripts/check_wave_gate.py` and marks it DONE, but I need to verify it actually enforces prerequisites.

**Why This Matters:** If Wave 1 plans start before Wave 0 is truly complete, downstream plans will fail.

**Required Improvement:**
```yaml
IMP-M10_wave_gate_automation:
  description: "Verify wave gate enforcement is complete and integrated"

  verification_checklist:
    - [ ] scripts/check_wave_gate.py exists
    - [ ] Script checks completion status of each IMP in previous wave
    - [ ] Script fails loudly if prerequisites not met
    - [ ] Script is called before each plan execution

  expected_behavior:
    command: "python scripts/check_wave_gate.py --check-wave 1"
    output_if_blocked:
      ```
      WAVE 1 GATE CHECK
      =================
      Wave 0 Status: INCOMPLETE

      Blocking Items:
        - IMP-A1 (Markers): DONE ✓
        - IMP-A2 (Thresholds): DONE ✓
        - IMP-J2 (Execution Sequences): IN_PROGRESS ✗

      RESULT: BLOCKED - Wave 0 not complete
      Cannot proceed to Wave 1 until: IMP-J2
      ```

  integration:
    - Add to plan execution template: "Call check_wave_gate.py before execution"
    - Fail plan immediately if wave gate not passed

  effort: Low (verify existing, extend if needed)
```

---

## Category 4: Evidence Chain Integrity

These improvements ensure evidence is traceable and verifiable.

### IMP-M11: Proof Token N/A Rule Validation

**Problem:** PROOF-TOKEN-MATRIX.md defines which proof tokens are N/A for different workflow types (e.g., install workflow can mark `agent_spawn` as N/A). But no validation exists that N/A is applied correctly.

**Why This Matters:** A finding could incorrectly mark critical proof tokens as N/A to hide missing evidence.

**Required Improvement:**
```yaml
IMP-M11_proof_token_na_validation:
  description: "Validate proof token N/A assignments are legitimate"

  artifact_to_create: "scripts/validate_proof_tokens.py"

  validation_rules:
    cli_install:
      required: [stage.health_check]
      allowed_na: [graph_build, agent_spawn, debate, context_pack, pattern_match]
      forbidden_na: [stage.health_check]

    graph_build:
      required: [stage.graph_build, stage.graph_integrity]
      allowed_na: [agent_spawn, debate, context_pack]
      forbidden_na: [stage.graph_build, stage.graph_integrity]

    audit_entrypoint:
      required: [health_check, graph_build, context_pack, pattern_match, agent_spawn, debate, report]
      allowed_na: []  # All tokens required
      forbidden_na: [ALL]

  validation_logic:
    1. Identify workflow type from evidence pack manifest
    2. Load applicable N/A rules from matrix
    3. For each proof token:
       a. If marked present: verify proof file exists
       b. If marked N/A: verify N/A is allowed for this workflow
       c. If required but missing: FAIL
    4. Report invalid N/A assignments

  failure_action:
    invalid_na: "FAIL evidence pack - N/A not allowed for this workflow type"
    missing_required: "FAIL evidence pack - required proof token missing"

  effort: Low
```

---

### IMP-M12: Evidence Pack Completeness Checker

**Problem:** Evidence packs have many required files (manifest.json, transcript.txt, report.json, proofs/). No single tool validates completeness.

**Required Improvement:**
```yaml
IMP-M12_evidence_pack_validation:
  description: "Comprehensive evidence pack completeness checker"

  artifact_to_create: "scripts/validate_evidence_pack.py"

  required_structure:
    .vrs/testing/runs/{run_id}/
      manifest.json:
        required_fields: [run_id, timestamp, workflow_type, session_label, pane_id, duration_ms]
      transcript.txt:
        required: true
        min_size: "1KB"
      report.json:
        required: true
        required_fields: [findings, summary, metrics]
      environment.json:
        required: true
        required_fields: [tool_versions, settings_hash]
      proofs/:
        depends_on: "workflow_type"

  validation_output:
    ```
    EVIDENCE PACK VALIDATION: .vrs/testing/runs/15-T1-orchestration-proof/
    ======================================================================

    Structure:
      [✓] manifest.json - present, valid JSON, all required fields
      [✓] transcript.txt - present, 347 lines (min requirement: 200)
      [✓] report.json - present, valid JSON, findings array present
      [!] environment.json - present, missing: settings_hash
      [✓] proofs/ - all required tokens present for audit_entrypoint

    Cross-Validation:
      [✓] manifest.session_label matches transcript header
      [✓] manifest.duration_ms within anti-fabrication range
      [✓] report.findings[].graph_nodes exist in graph

    RESULT: PARTIAL_PASS (1 warning)
    ```

  effort: Medium
```

---

## Category 5: Documentation and Usability

These improvements make the roadmap more usable.

### IMP-M13: Quick Reference Card for Plan Execution

**Problem:** The IMPROVEMENT-ROADMAP is 2400+ lines. A plan executor needs a quick reference showing:
- What IMP items block this plan?
- What artifacts must exist?
- What wave must be complete?

**Required Improvement:**
```yaml
IMP-M13_quick_reference_card:
  description: "Create one-page quick reference for plan execution"

  artifact_to_create: ".planning/phases/07.3.1.6-full-testing-hardening/PLAN-EXECUTION-QUICKREF.md"

  format:
    # Plan Execution Quick Reference

    ## Before Starting ANY Plan:
    1. Check wave gate: `python scripts/check_wave_gate.py --check-wave {plan_wave}`
    2. Verify test contracts: `python scripts/verify_test_contracts.py --plan {plan_number}`
    3. Verify definitions frozen: `python scripts/verify_definition_freeze.py`

    ## Per-Plan Prerequisites:

    | Plan | Wave | Must Complete First | Required Contracts | Required Skills |
    |------|------|---------------------|-------------------|-----------------|
    | 01 | 0 | - | - | - |
    | 02 | 1 | 01 | - | /vrs-workflow-test |
    | 03 | 2 | 02 | - | /vrs-audit |
    | ... | ... | ... | ... | ... |
    | 15 | 5 | 03,04,09-14 | CrossFunctionReentrancy.sol, dvd/side-entrance | /vrs-audit, agents |
    | 16 | 3 | 03,04 | CrossFunctionReentrancy.sol | /vrs-audit, agents |

    ## After Completing ANY Plan:
    1. Run anti-fabrication: `python scripts/check_anti_fabrication.py {transcript_path}`
    2. Validate evidence: `python scripts/validate_evidence_pack.py {run_dir}`
    3. Update wave status: `python scripts/check_wave_gate.py --record-completion {plan_number}`

  effort: Low
```

---

### IMP-M14: Existential Validation Execution Runbook

**Problem:** IMP-G1, IMP-H1, IMP-I1 are existential validations with decision trees. But no step-by-step runbook exists for executing them.

**Required Improvement:**
```yaml
IMP-M14_existential_runbook:
  description: "Step-by-step runbook for existential validations"

  artifact_to_create: ".planning/testing/guides/guide-existential-validations.md"

  content_for_IMP_G1:
    # IMP-G1: Graph Ablation Study Runbook

    ## Prerequisites:
    - IMP-K3 complete (--no-graph flag exists)
    - Test contract exists: tests/contracts/CrossFunctionReentrancy.sol
    - Ground truth for test contract exists

    ## Execution Steps:

    ### Step 1: Control Run (WITHOUT Graph)
    ```bash
    claude-code-controller launch "zsh"
    claude-code-controller send "cd {project_root}" --pane=X
    claude-code-controller send "claude" --pane=X
    claude-code-controller wait_idle --pane=X --idle-time=10.0
    claude-code-controller send "/vrs-audit tests/contracts/CrossFunctionReentrancy.sol --no-graph" --pane=X
    claude-code-controller wait_idle --pane=X --idle-time=180.0 --timeout=600
    claude-code-controller capture --pane=X --output=.vrs/testing/runs/ablation-control/transcript.txt
    ```

    ### Step 2: Test Run (WITH Graph)
    ```bash
    # Same steps but without --no-graph
    claude-code-controller send "/vrs-audit tests/contracts/CrossFunctionReentrancy.sol" --pane=X
    ...
    claude-code-controller capture --pane=X --output=.vrs/testing/runs/ablation-test/transcript.txt
    ```

    ### Step 3: Calculate Metrics
    ```bash
    python scripts/calculate_ablation_metrics.py \
      --control .vrs/testing/runs/ablation-control/report.json \
      --test .vrs/testing/runs/ablation-test/report.json \
      --ground-truth .vrs/corpus/ground-truth/CrossFunctionReentrancy.yaml \
      --output .vrs/testing/runs/ablation-comparison.yaml
    ```

    ### Step 4: Apply Decision Tree
    - Load decision tree: `.planning/testing/decision-trees/IMP-G1-graph-ablation.yaml`
    - Calculate: finding_delta, evidence_delta, graph_usage
    - Match to L1/L2/L3/L4 condition
    - Record verdict and action

    ### Step 5: If L3 or L4 (Marginal/No Improvement)
    - HALT phase immediately
    - Document in DEFINITION-ISSUES.md
    - Schedule architecture review within 48h

  effort: Medium
```

---

### IMP-M15: Metrics Collection Template

**Problem:** Many plans require collecting metrics (precision, recall, evidence depth, etc.) but no standardized template exists for metrics collection.

**Required Improvement:**
```yaml
IMP-M15_metrics_template:
  description: "Standardized metrics collection template"

  artifact_to_create: ".planning/testing/templates/METRICS-COLLECTION-TEMPLATE.md"

  template_structure:
    # Metrics Collection Report

    ## Run Information
    - Run ID:
    - Timestamp:
    - Plan:
    - Task:
    - Contract(s):

    ## Detection Metrics
    | Metric | Value | Threshold | Status |
    |--------|-------|-----------|--------|
    | True Positives | | | |
    | False Positives | | | |
    | False Negatives | | | |
    | Precision | | ≥50% | |
    | Recall | | ≥40% | |

    ## Evidence Metrics
    | Metric | Value | Threshold | Status |
    |--------|-------|-----------|--------|
    | Findings with graph nodes | | 100% | |
    | Avg nodes per finding | | ≥2 | |
    | Findings with code locations | | 100% | |
    | Valid node citations | | ≥90% | |

    ## Operational Metrics
    | Metric | Value | Threshold | Status |
    |--------|-------|-----------|--------|
    | Duration (seconds) | | 30-600 | |
    | Transcript lines | | ≥200 | |
    | Token usage | | <100k | |
    | Tool markers present | | Yes | |

    ## Anti-Fabrication Check
    - [ ] Duration in realistic range
    - [ ] Transcript length meets minimum
    - [ ] No perfect metrics (100%/100%)
    - [ ] Tool/agent markers present
    - [ ] Variance from other runs

  effort: Low
```

---

### IMP-M16: Visual Dependency Graph

**Problem:** The roadmap describes dependencies in text. A visual diagram would aid understanding.

**Required Improvement:**
```yaml
IMP-M16_visual_dependency_graph:
  description: "Create Mermaid diagram showing improvement dependencies"

  artifact_to_create: ".planning/phases/07.3.1.6-full-testing-hardening/DEPENDENCY-GRAPH.md"

  mermaid_diagram:
    ```mermaid
    graph TD
      subgraph "Wave 0: Definitions"
        A1[IMP-A1 Markers]
        A2[IMP-A2 Thresholds]
        A3[IMP-A3 Proof Tokens]
        A4[IMP-A4 EI/CTL]
        A5[IMP-A5 Tier C]
      end

      subgraph "Wave 0.5: Infrastructure"
        J1[IMP-J1 Decision Trees]
        J2[IMP-J2 Execution Sequences]
        J3[IMP-J3 Abort Criteria]
      end

      subgraph "Wave 1: Artifacts"
        B1[IMP-B1 Ground Truth]
        B5[IMP-B5 VQL Library]
        K3[IMP-K3 Graph Disable]
      end

      subgraph "Wave 5: Existential"
        G1[IMP-G1 Graph Ablation]
        H1[IMP-H1 Multi-Agent Comparison]
        I1[IMP-I1 Behavioral Detection]
      end

      A1 --> J2
      A2 --> J2
      J1 --> G1
      J1 --> H1
      J1 --> I1
      K3 --> G1
      B5 --> G1
      B1 --> H1
      B1 --> I1
    ```

  effort: Low
```

---

## Category 6: Missing Operational Mechanisms

### IMP-M17: Interrupted Execution Recovery Protocol

**Problem:** What happens if a plan execution is interrupted (network failure, Claude timeout, etc.)? No recovery protocol exists.

**Required Improvement:**
```yaml
IMP-M17_recovery_protocol:
  description: "Protocol for recovering from interrupted plan execution"

  artifact_to_create: ".planning/testing/guides/guide-execution-recovery.md"

  content:
    ## Recovery Protocol for Interrupted Execution

    ### Detecting Incomplete Runs
    - Evidence pack exists but missing report.json
    - Transcript ends mid-execution (no [REPORT_GENERATED])
    - manifest.json has status: "in_progress"

    ### Recovery Steps

    #### Option A: Resume from Checkpoint (if supported)
    1. Check for checkpoint file: `.vrs/state/checkpoint.yaml`
    2. If checkpoint exists and valid:
       - Run `/vrs-audit --resume {checkpoint_path}`
       - Verify graph not rebuilt (check transcript)
       - Verify beads not reprocessed
    3. Capture remaining transcript
    4. Merge with original transcript

    #### Option B: Clean Restart
    1. Archive incomplete evidence pack: `mv {run_dir} {run_dir}.incomplete`
    2. Create new run directory
    3. Re-execute from beginning
    4. Document interruption in manifest.json notes

    ### Validation After Recovery
    - Full anti-fabrication check on merged/new transcript
    - Verify no duplicate findings (if resumed)
    - Update manifest with recovery metadata

  effort: Low
```

---

### IMP-M18: Ground Truth Acquisition Protocol

**Problem:** IMP-B1 (Ground Truth Corpus) specifies structure but no protocol for **how to acquire** ground truth from external sources.

**Required Improvement:**
```yaml
IMP-M18_ground_truth_acquisition:
  description: "Protocol for acquiring and validating ground truth"

  artifact_to_create: ".planning/testing/guides/guide-ground-truth-acquisition.md"

  content:
    ## Ground Truth Acquisition Protocol

    ### Source Priority
    1. Code4rena audit reports (public)
    2. Immunefi bug bounties (public disclosures)
    3. SmartBugs benchmark (academic)
    4. Trail of Bits reports (public)
    5. Manual annotation (last resort)

    ### Acquisition Steps (Code4rena Example)

    1. **Select Contest**
       - Pick contests with ≥3 confirmed findings
       - Prefer recent (2024-2025) for relevance
       - Avoid contests with only QA findings

    2. **Download Contracts**
       - Clone contest repo
       - Identify scope contracts
       - Copy to tests/contracts/code4rena/{contest_name}/

    3. **Extract Findings**
       - Read audit report
       - For each confirmed finding:
         - Record: severity, category, file, line, description
         - Verify finding is in scope contracts
       - Create findings.yaml with structured data

    4. **Validate Provenance**
       - Record: contest URL, report URL, download date
       - Compute SHA256 of contracts
       - Store in provenance.yaml

    5. **Verify Contracts Compile**
       - Run `forge build` or `solc`
       - Fix any import issues
       - Document any modifications

    ### Minimum Corpus for Phase
    - 5 contracts from Code4rena (≥3 findings each)
    - 3 contracts from SmartBugs
    - 2 internal annotated contracts
    - Total: ≥30 ground truth findings

    ### Anti-Contamination
    - Ground truth MUST be stored separately from test code
    - Subject Claude sessions MUST NOT access ground truth during execution
    - Comparison happens AFTER execution, by controller

  effort: Medium
```

---

## Summary: Priority Order

| Priority | ID | Description | Wave | Effort |
|----------|-----|-------------|------|--------|
| CRITICAL | IMP-M1 | Test Contract Verification | 1 prereq | Low |
| CRITICAL | IMP-M2 | VQL Schema First | 1 prereq | Medium |
| CRITICAL | IMP-M3 | Graph Disable Early | 1 | Medium |
| CRITICAL | IMP-M4 | Single-Agent Mode | 2 | Medium |
| HIGH | IMP-M5 | Anti-Fabrication Automation | 1 | Medium |
| HIGH | IMP-M6 | Session Isolation Verification | 1 | Low |
| HIGH | IMP-M7 | Graph Citation Verification | 2 | Medium |
| HIGH | IMP-M8 | Plan 15 Dependencies | 1 | Low |
| MEDIUM | IMP-M9 | Definition Freeze | 1 | Low |
| MEDIUM | IMP-M10 | Wave Gate Automation | 1 | Low |
| MEDIUM | IMP-M11 | Proof Token N/A Validation | 2 | Low |
| MEDIUM | IMP-M12 | Evidence Pack Validation | 2 | Medium |
| LOW | IMP-M13 | Quick Reference Card | 1 | Low |
| LOW | IMP-M14 | Existential Runbook | 2 | Medium |
| LOW | IMP-M15 | Metrics Template | 1 | Low |
| LOW | IMP-M16 | Visual Dependency Graph | 1 | Low |
| LOW | IMP-M17 | Recovery Protocol | 2 | Low |
| LOW | IMP-M18 | Ground Truth Protocol | 1 | Medium |

---

## Integration with Current Roadmap

These 18 improvements should be integrated into the IMPROVEMENT-ROADMAP as follows:

1. **Add new category IMP-M (Execution Readiness)** containing IMP-M1 through IMP-M4
2. **Add to IMP-C (Validation Mechanisms):** IMP-M5, IMP-M6, IMP-M7
3. **Add to IMP-D (Logical Flaws):** IMP-M8, IMP-M9
4. **Add to IMP-E (Integration):** IMP-M10
5. **Add to IMP-F (Evidence Integrity):** IMP-M11, IMP-M12
6. **Add new section "Operational Guides":** IMP-M13 through IMP-M18

**Total improvements after integration:** 54 + 18 = **72 improvements**

---

## Verification Checklist

Before marking this improvement proposal complete:

- [ ] Each improvement has clear problem statement
- [ ] Each improvement has concrete artifact to create or change
- [ ] No improvement adds metrics for metrics' sake
- [ ] All improvements trace to real execution gaps
- [ ] Priority is based on blocking impact, not theoretical importance
- [ ] Integration path is clear for each improvement
