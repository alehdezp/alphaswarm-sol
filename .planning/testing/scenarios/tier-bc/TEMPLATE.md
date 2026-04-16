# Tier B/C Scenario Template

**Purpose:** Define Tier B/C scenarios that force graph-first, context-aware reasoning on complex vulnerabilities.

## Metadata [B10 core]
- scenario_id:
- title:
- tier: "B" | "C"
- vulnerability_class:
- pattern_ids:
- source_type: audit_report | cve | ctf | other
- source_reference: (URL or citation)
- protocol_type:
- scope: single-contract | multi-contract | cross-module
- expected_severity:

## Provenance (Required) [B10.B]
- external_source:
- ground_truth_reference: (report/CVE section or stable identifier)
- summary_of_vulnerability:
- exploit_path_summary:
- why_this_is_complex:
- complexity_factors: (cross-function, cross-contract, economic, timing, oracle)

## Context Pack (Required) [B10 core]
- protocol_context_pack_path:
- economic_context_pack_path:
- context.simulated: true | false
- simulated_context_artifact_path: (required if simulated)
- transcript_marker_required: [CONTEXT_SIMULATED] (required if simulated)

## Scenario Family (Required) [B10 core + B10.G]
### Vulnerable Case
- repo_or_fixture:
- entrypoint:
- expected_failure_mode:

### Safe Variant
- repo_or_fixture:
- change_from_vulnerable:
- expected_result:

### Counterfactual
- repo_or_fixture:
- alternate_failure_mode:
- why_it_is_not_the_target_bug:
- counterfactual_expected_outcome: should_not_trigger_detection

## Success Criteria (Required) [B10 core]
- must_find: (target vulnerability / exploit path)
- must_not_find: (known non-issues to avoid)
- evidence_threshold: (minimum evidence required to accept a finding)
- reasoning_threshold: (required graph nodes/edges, code locations)
- confidence_floor: (e.g., medium or higher)

## Attack Surface Enumeration (Required) [B10.D]
List these before any pattern reasoning.
- evidence_pack_section_title: Attack Surface

### Privileged Functions
- function_name:
- access_gate:
- reason_privileged:

### External Calls
- callsite:
- target:
- trusted_or_untrusted:

### Critical State
- state_variable:
- why_critical:
- update_path:

### Trust Boundaries / Roles
- roles:
- boundaries:

## Loss Path Model (Required) [B10.C]
Assets -> flows -> invariants -> loss condition. Tie to context pack fields.
- context_fields_used: (list context pack keys used below)

### Assets
- asset:
- custody_model:

### Flows
- flow_steps:
- actors:

### Invariants
- invariant_statement:
- expected_enforcement:

### Loss Condition
- trigger:
- impact:

## Mechanism-Level Invariants (Required) [B10.F]
List mechanism invariants and how they will be checked.

- invariant:
- rationale:
- check_method: VQL | reasoning | tool_output
- expected_evidence:
- result:
- attack_surface_refs: (IDs from Attack Surface Enumeration)

## VQL Requirements (Required) [B10 core]
### Minimum Query Set (Must Execute Before Conclusions)
Reference the VQL library and include transcript markers for each query.

- required_minimum_queries: [VQL-MIN-01, VQL-MIN-02, VQL-MIN-03, VQL-MIN-04, VQL-MIN-05]
- transcript_markers_required: [VQL_MIN_SET_START], [VQL-MIN-01], [VQL-MIN-02], [VQL-MIN-03], [VQL-MIN-04], [VQL-MIN-05], [VQL_MIN_SET_END]
- evidence_pack_section_title: VQL Minimum Set Output

### Cross-Contract Path Query (Required) [B10.E]
At least one cross-contract path query must run per scenario family.

- required_cross_contract_queries: [VQL-XCON-01]
- transcript_marker_required: [VQL-XCON-01]
- evidence_pack_section_title: Cross-Contract Paths
- null_result_handling: emit marker + "NO_PATHS" if none found

### Scenario-Specific Queries
- query_id:
- purpose:
- query_string:
- expected_signal:

## Evidence Contract (Required) [B10 core + B10.H]
- Graph-first: VQL/BSKG queries appear before conclusions.
- Orchestration markers: TaskCreate, TaskUpdate, and subagent markers present.
- Context markers: [CONTEXT_READY] or [CONTEXT_INCOMPLETE]; if simulated, [CONTEXT_SIMULATED].
- Output structure: Evidence -> Reasoning -> Impact -> Confidence for every finding.
- False-positive suppression: Rejected findings logged with TaskUpdate markers and discard rationale.
- Prioritization: Ranked findings using the rubric below.
- Coverage confidence: Score + rationale based on attack surface inventory.
- evidence_order_proof: include explicit marker ordering or timestamps

## Finding Template (Repeat Per Finding) [B10.H]
### Finding ID
#### Evidence
- graph_nodes:
- graph_edges:
- code_locations:
- vql_queries_used:

#### Reasoning
- attack_path_summary:
- invariant_violation:
- why_exploitable:

#### Impact
- affected_assets:
- worst_case_loss:
- protocol_consequences:

#### Confidence
- confidence_level:
- rationale:

## False-Positive Suppression Log (Required) [B10.G]
List discarded findings with evidence and TaskUpdate markers.

- finding_id:
- discard_reason:
- evidence_ref:
- taskupdate_marker:
- linked_counterfactual_case: (from Scenario Family)

## Prioritization Rubric (Required) [B10.I]
Score findings and provide a ranked list.

- severity_scale: Critical (5), High (4), Medium (3), Low (2), Info (1)
- exploitability_scale: Easy (3), Moderate (2), Hard (1)
- impact_scale: Total Loss (3), Partial Loss (2), Limited (1)
- ranking_method: severity + exploitability + impact

### Ranked Findings
| rank | finding_id | severity | exploitability | impact | total_score | rationale |
|---|---|---|---|---|---|---|

## Coverage Confidence Score (Required) [B10.P]
- score: 0.0 - 1.0
- rationale:
- attack_surface_coverage_notes:
- attack_surface_inventory_ref: (link to Attack Surface section)

## Expert Baseline Rationale (Required) [B10.Q]
Provide an expert-style rationale to benchmark reasoning depth.

- expert_rationale:
- key_assumptions:
- expected_evidence_depth:
- expert_profile: (role or perspective)

## Validation Checklist
- [ ] Provenance documented with external source
- [ ] Ground truth reference and exploit path recorded
- [ ] Context pack present (or [CONTEXT_SIMULATED] marker recorded)
- [ ] Attack surface enumerated before reasoning
- [ ] Loss path model completed
- [ ] Mechanism invariants defined and checked
- [ ] Minimum VQL query set executed with markers
- [ ] Cross-contract path query executed
- [ ] Findings follow Evidence -> Reasoning -> Impact -> Confidence
- [ ] Discarded findings logged with TaskUpdate markers
- [ ] Findings ranked using rubric
- [ ] Coverage confidence score recorded
- [ ] Expert baseline rationale captured
- [ ] Success criteria met
