# Orchestration Proof Guide

**Status:** CANONICAL
**Purpose:** Validate that multi-agent orchestration actually occurs during execution.
**Required By:** Plan 15 (Orchestration Behavior Proof + E2E Pipeline Validation)
**References:** `.planning/testing/rules/canonical/ORCHESTRATION-MARKERS.md`, `docs/PHILOSOPHY.md`

---

## Overview

This guide defines how to prove that AlphaSwarm.sol's multi-agent orchestration actually executes. Without this validation, the system could be a single-agent report generator masquerading as a multi-agent orchestration framework.

**Critical Insight:** The system must prove that:
1. All 9 pipeline stages execute in correct sequence
2. TaskCreate produces distinct, security-relevant work items
3. Subagent spawns produce reasoned outputs with graph evidence
4. The full pipeline works end-to-end on fresh environments

---

## The 9-Stage Pipeline

From `docs/PHILOSOPHY.md`, the orchestration pipeline has 9 stages:

| Stage | Name | Purpose | Required Marker |
|-------|------|---------|-----------------|
| 1 | Preflight | Validate environment | `[PREFLIGHT_PASS]` or `[PREFLIGHT_FAIL]` |
| 2 | Graph Build | Build BSKG | `[GRAPH_BUILD_SUCCESS nodes=X edges=Y hash=Z]` |
| 3 | Context Load | Load protocol context | `[CONTEXT_READY]` or `[CONTEXT_SIMULATED]` |
| 4 | Task Creation | Create work items | `TaskCreate(id=..., subject=...)` |
| 5 | Detection | Run pattern matching | `[DETECTION_START]` ... `[DETECTION_COMPLETE]` |
| 6 | Deduplication | Merge duplicate findings | `[DEDUP_COMPLETE]` |
| 7 | Subagent Spawns | Run attacker/defender/verifier | `SubagentStart(type=...)` |
| 8 | Debate | Arbitrate findings | `[DEBATE_VERDICT]` |
| 9 | Report | Generate final report | `[REPORT_GENERATED]` |

---

## Stage Marker Specifications

### Stage 1: Preflight

**Purpose:** Verify tools are available, environment is ready.

**Markers:**
```
[PREFLIGHT_START]
[PREFLIGHT_PASS duration_ms={ms}]
  OR
[PREFLIGHT_FAIL reason={reason}]
```

**Expected Dynamic Values:**
- `duration_ms`: Integer (actual preflight duration, e.g., 1250)
- `reason`: String (if failed, e.g., "slither_not_found")

**Validation:**
- Marker must contain numeric duration (not placeholder)
- Duration should be realistic (100ms - 30000ms)

---

### Stage 2: Graph Build

**Purpose:** Construct the Behavioral Smart Contract Knowledge Graph (BSKG).

**Markers:**
```
[GRAPH_BUILD_START target={path}]
[GRAPH_BUILD_SUCCESS nodes={n} edges={e} hash={h}]
  OR
[GRAPH_BUILD_FAIL reason={reason}]
```

**Expected Dynamic Values:**
- `nodes`: Integer (number of graph nodes, e.g., 142)
- `edges`: Integer (number of graph edges, e.g., 387)
- `hash`: String (first 12 chars of SHA256, e.g., "a3f8c2b1e9d4")

**Validation:**
- Node count should match contract complexity (typically 50-500 for single contract)
- Edge count typically 2-4x node count
- Hash must be 12 hex characters
- Same contract should produce same hash (deterministic)

---

### Stage 3: Context Load

**Purpose:** Load protocol-specific context (economic model, trust boundaries).

**Markers:**
```
[CONTEXT_LOAD_START protocol={name}]
[CONTEXT_READY protocol={name} ctl={high|medium|low|simulated}]
  OR
[CONTEXT_INCOMPLETE protocol={name} missing={fields}]
  OR
[CONTEXT_SIMULATED protocol={name} reason={reason}]
```

**Expected Dynamic Values:**
- `protocol`: String (protocol name, e.g., "lending")
- `ctl`: Enum (Context Trust Level: high/medium/low/simulated)
- `missing`: Comma-separated list of missing fields

**Validation:**
- CTL must be one of the valid enum values
- If SIMULATED, reason must be provided
- For Tier C analysis, CTL must be "high" or "medium"

---

### Stage 4: Task Creation

**Purpose:** Create security investigation tasks.

**Markers:**
```
TaskCreate(id={task_id}, subject={subject})
TaskUpdate(id={task_id}, status={status})
```

**Expected Dynamic Values:**
- `id`: String (unique task ID, e.g., "task-001", "bead-abc123")
- `subject`: String (security-relevant description)
- `status`: Enum (pending, in_progress, completed, pending_dedup, ready)

**Validation:**
- At least 3 distinct task IDs in a full audit
- Subjects should describe specific security concerns (not "Task 1")
- TaskUpdate should follow corresponding TaskCreate
- State transitions should be logical (pending -> in_progress -> completed)

---

### Stage 5: Detection

**Purpose:** Run pattern matching against graph.

**Markers:**
```
[DETECTION_START patterns={count}]
[DETECTION_MATCH pattern={id} function={name} confidence={score}]
[DETECTION_COMPLETE matches={count} unique={count}]
```

**Expected Dynamic Values:**
- `patterns`: Integer (number of patterns checked)
- `confidence`: Float (0.0-1.0)
- `matches`: Integer (total matches before dedup)
- `unique`: Integer (matches after initial grouping)

**Validation:**
- Pattern count should reflect VulnDocs library size
- Confidence scores should not all be 1.0 (suspicious)
- Unique <= matches

---

### Stage 6: Deduplication

**Purpose:** Merge duplicate/overlapping findings.

**Markers:**
```
[DEDUP_START findings={count}]
[DEDUP_MERGE source={id1} target={id2} reason={reason}]
[DEDUP_COMPLETE original={count} deduplicated={count}]
```

**Expected Dynamic Values:**
- `original`: Integer (pre-dedup count)
- `deduplicated`: Integer (post-dedup count)
- `reason`: String (why merged, e.g., "same_root_cause")

**Validation:**
- deduplicated <= original
- Some merges expected for complex contracts

---

### Stage 7: Subagent Spawns

**Purpose:** Deploy specialized agents for investigation.

**Markers:**
```
SubagentStart(type={vrs-attacker|vrs-defender|vrs-verifier|vrs-secure-reviewer})
SubagentComplete(type={type}, findings={count}, evidence_nodes={count})
```

**Expected Dynamic Values:**
- `type`: Enum (vrs-attacker, vrs-defender, vrs-verifier, vrs-secure-reviewer)
- `findings`: Integer (findings from this agent)
- `evidence_nodes`: Integer (graph nodes referenced)

**Validation:**
- For multi-agent debate: at least attacker, defender, verifier
- Each SubagentComplete should have preceding SubagentStart
- evidence_nodes > 0 (agents must use graph)

---

### Stage 8: Debate

**Purpose:** Arbitrate between attacker and defender claims.

**Markers:**
```
[DEBATE_START bead={id}]
[DEBATE_ROUND attacker_claims={n} defender_claims={n}]
[DEBATE_VERDICT bead={id} severity={severity} confidence={score}]
```

**Expected Dynamic Values:**
- `bead`: String (finding/bead ID)
- `severity`: Enum (critical, high, medium, low, informational, safe)
- `confidence`: Float (0.0-1.0)

**Validation:**
- VERDICT should follow START for same bead
- Severity should not always be same value
- Confidence should not always be 1.0 (suspicious)

---

### Stage 9: Report Generation

**Purpose:** Produce final security report.

**Markers:**
```
[REPORT_START format={json|markdown|sarif}]
[REPORT_GENERATED findings={count} path={path}]
```

**Expected Dynamic Values:**
- `findings`: Integer (final finding count)
- `path`: String (report file path)

**Validation:**
- Path should exist and be non-empty
- findings count should match DEDUP_COMPLETE deduplicated count
- Report should be parseable

---

## Sequence Validation Rules

### Required Sequence Order

Stages must execute in order (some can be skipped with markers):

```
PREFLIGHT_START
  -> PREFLIGHT_PASS
  -> GRAPH_BUILD_START
  -> GRAPH_BUILD_SUCCESS
  -> CONTEXT_LOAD_START
  -> CONTEXT_READY (or CONTEXT_SIMULATED)
  -> TaskCreate (one or more)
  -> DETECTION_START
  -> DETECTION_COMPLETE
  -> DEDUP_START
  -> DEDUP_COMPLETE
  -> SubagentStart (vrs-attacker)
  -> SubagentComplete (vrs-attacker)
  -> SubagentStart (vrs-defender)
  -> SubagentComplete (vrs-defender)
  -> SubagentStart (vrs-verifier)
  -> SubagentComplete (vrs-verifier)
  -> DEBATE_VERDICT
  -> REPORT_GENERATED
```

### Sequence Validation Script

```python
def validate_sequence(transcript: str) -> tuple[bool, list[str]]:
    """Validate marker sequence in transcript.

    Returns (is_valid, list_of_errors).
    """
    errors = []
    markers_found = []

    # Extract markers with line numbers
    for i, line in enumerate(transcript.split('\n')):
        for pattern in MARKER_PATTERNS:
            if match := re.search(pattern, line):
                markers_found.append((i, match.group(0)))

    # Check required markers present
    required = [
        r'\[PREFLIGHT_PASS',
        r'\[GRAPH_BUILD_SUCCESS',
        r'TaskCreate\(',
        r'SubagentStart\(',
        r'\[REPORT_GENERATED',
    ]
    for req in required:
        if not any(re.search(req, m[1]) for m in markers_found):
            errors.append(f"Missing required marker: {req}")

    # Check sequence order
    stage_order = {
        'PREFLIGHT': 1,
        'GRAPH_BUILD': 2,
        'CONTEXT': 3,
        'TaskCreate': 4,
        'DETECTION': 5,
        'DEDUP': 6,
        'SubagentStart': 7,
        'DEBATE': 8,
        'REPORT': 9,
    }

    last_stage = 0
    for line_num, marker in markers_found:
        for stage_name, order in stage_order.items():
            if stage_name in marker:
                if order < last_stage:
                    errors.append(f"Out of order: {stage_name} at line {line_num}")
                last_stage = max(last_stage, order)
                break

    return len(errors) == 0, errors
```

---

## Anti-Fabrication Requirements

### Minimum Thresholds for E2E Orchestration Proof

| Metric | Threshold | Rationale |
|--------|-----------|-----------|
| Transcript lines | >= 200 | Real orchestration produces substantial output |
| Duration | >= 120s | Multi-agent debate takes time |
| Task creates | >= 3 | Real audits create multiple tasks |
| Subagent spawns | >= 2 | Multi-agent requires multiple agents |
| Dynamic values | Required | Markers must not be static template text |

### Invalid Patterns (Fabrication Indicators)

- All confidence scores = 1.0
- All severities = same value
- Hash is placeholder text (not 12 hex chars)
- Duration is round number (exactly 60000ms)
- No TaskUpdate following TaskCreate
- Subagent outputs have no graph node IDs

### Validation Checklist

```yaml
anti_fabrication_checklist:
  - check: "Transcript >= 200 lines"
    how: "wc -l transcript.txt"
  - check: "Duration >= 120s"
    how: "Parse timestamps from first to last marker"
  - check: "At least 3 TaskCreate with distinct IDs"
    how: "grep TaskCreate | extract id= values"
  - check: "At least 2 subagent spawns"
    how: "grep SubagentStart | count"
  - check: "Graph hash is valid hex"
    how: "Extract hash from GRAPH_BUILD_SUCCESS, verify [a-f0-9]{12}"
  - check: "Confidence scores vary"
    how: "Extract all confidence values, ensure not all same"
  - check: "Report file exists"
    how: "Check path from REPORT_GENERATED exists"
```

---

## E2E Pipeline Validation Protocol

### Fresh Environment Test

1. **Setup:** Start with clean `.vrs/` directory (no prior state)
2. **Execute:** Run `/vrs-audit` on contract with known vulnerability
3. **Verify:** All 9 stages complete with valid markers
4. **Validate:** Report contains finding traceable to graph and code

### claude-code-controller Execution Sequence

```bash
# Launch fresh claude-code-agent-teams session
claude-code-controller launch "zsh"

# Start Claude Code
claude-code-controller send "claude" --pane=X
claude-code-controller wait_idle --pane=X --idle-time=10.0

# Execute audit
claude-code-controller send "/vrs-audit tests/contracts/CrossFunctionReentrancy.sol" --pane=X
claude-code-controller wait_idle --pane=X --idle-time=30.0 --timeout=600

# Capture transcript
claude-code-controller capture --pane=X --output=.vrs/testing/runs/orchestration-proof/transcript.txt
```

### Finding Traceability Test

For each finding in the report:

1. **Graph Evidence:** Extract graph node ID from finding
2. **Verify Node:** Confirm node exists in graph (query or dump)
3. **Code Location:** Extract file:line from finding
4. **Verify Location:** Confirm file and line exist
5. **True Positive:** Compare against ground truth

---

## Orchestration Proof Report Template

When documenting orchestration proof, include:

```yaml
orchestration_proof:
  session_id: ""
  timestamp: ""
  contract: ""

  stage_markers:
    preflight:
      marker: "[PREFLIGHT_PASS duration_ms=1234]"
      line: 42
    graph_build:
      marker: "[GRAPH_BUILD_SUCCESS nodes=142 edges=387 hash=a3f8c2b1e9d4]"
      line: 58
    # ... all stages

  task_analysis:
    task_count: 5
    tasks:
      - id: "task-001"
        subject: "Reentrancy in withdraw function"
        updates: ["pending", "in_progress", "completed"]
      - id: "task-002"
        subject: "Access control in transfer"
        updates: ["pending", "in_progress", "completed"]

  subagent_analysis:
    spawns:
      - type: "vrs-attacker"
        evidence_nodes: 12
        findings: 2
      - type: "vrs-defender"
        evidence_nodes: 8
        findings: 0
      - type: "vrs-verifier"
        evidence_nodes: 15
        verdict: "critical"

  anti_fabrication:
    transcript_lines: 342
    duration_ms: 187000
    markers_complete: true
    sequence_valid: true
    dynamic_values_valid: true

  finding_traceability:
    - finding_id: "bead-001"
      graph_node: "node-142"
      code_location: "CrossFunctionReentrancy.sol:45"
      ground_truth_match: true
```

---

## Failure Handling

### If Orchestration Proof Fails

| Failure Mode | Indicates | Action |
|--------------|-----------|--------|
| Missing markers | Orchestration not happening | Debug skill/tool emission |
| Wrong sequence | Stage coordination broken | Fix orchestration flow |
| Static values | Markers are hardcoded | Fix dynamic value injection |
| No subagent output | Agents not producing work | Debug agent prompts |
| Instant completion | Fake execution | Anti-fabrication audit |

### Recovery Protocol

1. **Identify failure mode** from validation output
2. **Locate emission point** for missing/invalid marker
3. **Trace through orchestration** to find coordination bug
4. **Fix and re-run** full validation
5. **Document fix** in phase report

---

## Usage Instructions

1. **Before Validation:** Review all marker specifications
2. **During Execution:** Use claude-code-controller to capture full transcript
3. **After Capture:** Run sequence validation script
4. **Document Results:** Fill out orchestration proof report
5. **Address Failures:** Follow recovery protocol

**Related Documents:**
- `.planning/testing/rules/canonical/ORCHESTRATION-MARKERS.md` (marker specifications)
- `.planning/testing/templates/ORCHESTRATION-MARKER-CHECKLIST.md` (checklist template)
- `docs/PHILOSOPHY.md` (9-stage pipeline definition)
- `.planning/testing/rules/canonical/RULES-ESSENTIAL.md` (testing rules)

---

**Guide Version:** 1.0
**Last Updated:** 2026-02-04
