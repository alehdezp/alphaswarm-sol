# Pattern Discovery Log

**Status:** CANONICAL
**Purpose:** Capture novel pattern candidates when anomalies are detected during vulnerability analysis.
**Required By:** Plan 13 (Novel Pattern Discovery Pipeline)
**References:** `.planning/testing/guides/guide-pattern-discovery.md`, `.planning/testing/rules/canonical/ORCHESTRATION-MARKERS.md`

---

## Overview

This log template captures candidate patterns discovered during analysis when:
1. Evidence contradicts known patterns
2. False-positive suppression removes all candidates
3. Cross-function paths show novel operation sequencing

Captured candidates are routed to `/pattern-forge` (new patterns) or `/vrs-refine` (improvements to existing).

---

## Log Entry

### Metadata

```yaml
discovery_id: ""                    # Unique ID (e.g., disc-2026-02-04-001)
timestamp: ""                       # ISO 8601 format
contract_analyzed: ""               # Path to contract
session_id: ""                      # claude-code-agent-teams session ID
transcript_ref: ""                  # Path to transcript
analyst: ""                         # Agent or human performing discovery
status: "candidate"                 # candidate | validated | rejected | routed
```

---

## Trigger Information

### Trigger Type

Select the trigger condition that initiated discovery:

```yaml
trigger:
  type: ""                          # evidence_contradiction | fp_wipeout | novel_sequencing

  # For evidence_contradiction
  evidence_contradiction:
    expected_pattern: ""            # Pattern ID that should have matched
    expected_evidence: ""           # What evidence was expected
    actual_evidence: ""             # What evidence was actually found
    contradiction_details: ""       # How they contradict

  # For false_positive_wipeout
  fp_wipeout:
    initial_candidates: []          # Pattern IDs initially matched
    suppression_reasons: []         # Why each was marked as FP
    remaining_candidates: 0         # Should be 0 for this trigger

  # For novel_sequencing
  novel_sequencing:
    discovered_sequence: []         # Operation sequence found (e.g., [READ, EXTERNAL, WRITE])
    closest_known_sequence: ""      # Most similar existing pattern
    sequence_difference: ""         # How it differs from known patterns
```

### Trigger Markers

Orchestration markers that should appear in transcript when trigger fires:

```yaml
trigger_markers:
  - marker: "[PATTERN_ANOMALY trigger={type}]"
    description: "Initial anomaly detection"
  - marker: "[DISCOVERY_START candidate={id}]"
    description: "Discovery process initiated"
```

---

## Anomaly Description

Detailed description of the anomaly that triggered discovery.

```yaml
anomaly:
  summary: ""                       # One-line description of anomaly
  detailed_description: |
    Provide a detailed explanation of:
    - What was expected based on existing patterns
    - What was actually observed
    - Why this constitutes an anomaly worthy of investigation

  vulnerability_hypothesis: |
    If this anomaly represents a real vulnerability pattern:
    - What would it detect?
    - What operation sequence characterizes it?
    - What makes it different from existing patterns?

  false_discovery_risk: ""          # How likely is this a noise/FP? (low/medium/high)
  confidence: 0.0                   # 0.0-1.0 confidence this is a real pattern
```

---

## Candidate Pattern

The proposed new pattern or pattern improvement.

### Pattern Definition

```yaml
candidate:
  name: ""                          # Proposed pattern name
  hypothesis: |
    Describe what vulnerability this pattern would detect and why.

  # Semantic operation sequence (core of the pattern)
  operation_sequence:
    - step: 1
      operation: ""                 # e.g., READS_USER_BALANCE
      notes: ""
    - step: 2
      operation: ""
      notes: ""
    - step: 3
      operation: ""
      notes: ""

  # Detection criteria
  detection_criteria:
    required_operations: []         # Must be present
    forbidden_operations: []        # Must NOT be present
    ordering_constraints: []        # Order requirements

  # Comparison to existing patterns
  similar_patterns:
    - pattern_id: ""
      similarity: ""                # How similar (0-100%)
      key_difference: ""            # What makes this different
```

### Evidence

```yaml
evidence:
  # Graph evidence
  evidence_node_ids:
    - node_id: ""
      role: ""                      # What this node represents in the pattern
    - node_id: ""
      role: ""

  # Code evidence
  code_locations:
    - file: ""
      line: 0
      snippet: ""
      relevance: ""                 # Why this code is relevant

  # Transcript evidence
  transcript_excerpts:
    - ref: ""                       # Line range or marker
      content: ""
      significance: ""              # Why this excerpt matters

  # Graph query that discovered this
  discovery_query:
    query_id: ""                    # VQL query ID if applicable
    query_string: ""
    result_count: 0
```

---

## Routing Decision

Determine how to handle this candidate.

### Route Selection

```yaml
routing:
  route_to: ""                      # /pattern-forge | /vrs-refine | manual_review | reject

  # Routing criteria
  criteria:
    is_novel_pattern: false         # True -> /pattern-forge
    is_improvement: false           # True -> /vrs-refine
    needs_more_evidence: false      # True -> manual_review
    likely_false_positive: false    # True -> reject

  rationale: |
    Explain why this route was chosen:
    - For /pattern-forge: Why this is a genuinely new pattern
    - For /vrs-refine: Which existing pattern to improve and how
    - For manual_review: What additional evidence is needed
    - For reject: Why this is not a valid pattern candidate
```

### Routing Markers

```yaml
routing_markers:
  - marker: "[DISCOVERY_ROUTE target={route_to} candidate={id}]"
    description: "Routing decision marker"
```

---

## Validation Notes

Track validation attempts and status.

```yaml
validation:
  expected_validation: |
    Describe how this pattern would be validated:
    - What test contracts would prove it works?
    - What true positives should it find?
    - What false positives should it NOT produce?

  validation_status: ""             # not_started | in_progress | passed | failed

  validation_results:
    - attempt: 1
      date: ""
      result: ""                    # pass | fail
      notes: ""
      test_contracts: []
      true_positives_found: 0
      false_positives: 0

  current_status: "draft"           # draft | validated | rejected

  next_steps: |
    If not yet validated, describe next steps:
    - Tests to run
    - Evidence to gather
    - Questions to answer
```

---

## Anti-Fabrication Compliance

Ensure this discovery is authentic.

```yaml
anti_fabrication:
  transcript_line_count: 0          # Must be >= 100
  duration_ms: 0                    # Must be >= 30000
  markers_present:
    - marker: ""
      found: false

  compliance_check:
    min_lines_met: false            # >= 100 lines
    min_duration_met: false         # >= 30s
    markers_present: false          # Required markers found
    not_perfect_metrics: true       # 100%/100% is invalid

  validation_result: ""             # pass | fail
```

---

## Completion Checklist

- [ ] Trigger type identified and documented
- [ ] Anomaly description explains expected vs actual evidence
- [ ] Candidate pattern has clear hypothesis
- [ ] Operation sequence defined
- [ ] Evidence includes graph node IDs and code locations
- [ ] Routing decision made with rationale
- [ ] Next steps documented if not yet validated
- [ ] Anti-fabrication thresholds verified

---

## Example Entry (Reference)

```yaml
discovery_id: "disc-2026-02-04-001"
timestamp: "2026-02-04T14:30:00Z"
contract_analyzed: "tests/contracts/hard-case/NovelCallback.sol"
session_id: "vrs-demo-discovery-1707056400"
transcript_ref: ".vrs/testing/runs/13-T3-discovery/transcript.txt"
status: "candidate"

trigger:
  type: "novel_sequencing"
  novel_sequencing:
    discovered_sequence: ["READS_ORACLE", "CALLS_EXTERNAL", "WRITES_BALANCE", "READS_ORACLE"]
    closest_known_sequence: "reentrancy (R:bal -> X:call -> W:bal)"
    sequence_difference: "Oracle read both before and after external call"

anomaly:
  summary: "Oracle value used both pre and post external call, enabling manipulation"
  vulnerability_hypothesis: |
    Pattern: Read oracle -> external call -> write based on (possibly stale) oracle value
    The external call could manipulate the oracle, making the post-call read return different value.

candidate:
  name: "oracle-manipulation-via-callback"
  operation_sequence:
    - step: 1
      operation: "READS_ORACLE"
      notes: "Pre-call oracle read"
    - step: 2
      operation: "CALLS_EXTERNAL"
      notes: "External call that could manipulate oracle"
    - step: 3
      operation: "WRITES_BALANCE"
      notes: "State write based on potentially stale oracle"

routing:
  route_to: "/pattern-forge"
  rationale: |
    This is a novel pattern not covered by existing reentrancy or oracle manipulation patterns.
    The key insight is the oracle read timing relative to external calls.

validation:
  current_status: "draft"
  next_steps: |
    1. Create test contract with this vulnerability
    2. Run pattern-forge to formalize
    3. Validate against Code4rena oracle exploits
```

---

## Usage Instructions

1. **When to Create Entry**: Create entry when any of the three trigger conditions fire
2. **Evidence Collection**: Ensure all graph node IDs and code locations are captured
3. **Routing**: Follow routing criteria strictly
4. **Validation**: Don't mark as validated without actual test results
5. **Integration**: Routed candidates should be processed within 1 planning cycle

**Related Documents:**
- `.planning/testing/guides/guide-pattern-discovery.md` (discovery protocol)
- `.planning/testing/rules/canonical/ORCHESTRATION-MARKERS.md` (marker formats)
- `docs/guides/patterns-basics.md` (pattern fundamentals)

---

**Template Version:** 2.0
**Last Updated:** 2026-02-04
