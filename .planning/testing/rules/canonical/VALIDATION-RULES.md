# Validation Rules for AlphaSwarm.sol

**Version:** 2.0
**Updated:** 2026-02-11
**Execution Model:** Agent Teams (Claude Code native) + `claude-code-controller` (npm v0.6.1)
**Status:** Active policy for Phase 3.1+. Rules enforced via hooks, controller events, and code-based graders.
**Shared Rule ID Namespace:** All rule IDs below match the Rule ID Registry in `RULES-ESSENTIAL.md`.

---

## PURPOSE

This document defines MANDATORY validation rules for all testing activities in AlphaSwarm.sol. These rules exist because Phase 07.3 GA Validation was found to be entirely fabricated -- using mock/simulated modes, hardcoded ground truth, and perfect metrics that prove nothing.

**The testing infrastructure exists. These rules ensure it is actually used.**

**Execution model:** Agent Teams (`TeamCreate`, `Task`, `SendMessage`, `TaskCreate/TaskUpdate`) for orchestration. `claude-code-controller` for programmatic test triggering from pytest. Controller event capture (`message`, `task:completed`, `agent:exited`) for verification.

---

## RULE ID CROSS-REFERENCE

All rule IDs below are from the shared namespace defined in `RULES-ESSENTIAL.md`. Evaluation contracts reference these via `rule_refs[]`.

| ID | Category | Section Below |
|---|---|---|
| `EXEC-INTEGRITY` | Execution Integrity | Execution Mode Rules |
| `TRANSCRIPT-AUTH` | Transcript Authenticity | Anti-Fabrication Rules |
| `METRICS-REALISM` | Metrics Realism | Metrics Rules |
| `GROUND-TRUTH` | Ground Truth Provenance | Ground Truth Rules |
| `REPORT-INTEGRITY` | Report Integrity | Reporting Rules |
| `DURATION-BOUNDS` | Duration Bounds | Anti-Fabrication Rules |
| `EVIDENCE-CHAIN` | Evidence Chain | Anti-Fabrication Rules |
| `GATE-INTEGRITY` | Gate Test Integrity | Anti-Fabrication Rules |
| `ISOLATION` | Test Isolation | Infrastructure Rules |
| `SESSION-NAMING` | Session Naming Convention | Infrastructure Rules |
| `ARTIFACT-PROD` | Artifact Production | Artifact Dependency Rules |
| `ARTIFACT-DEP` | Artifact Dependency | Artifact Dependency Rules |
| `WAVE-GATE` | Wave Gate Enforcement | Artifact Dependency Rules |
| `TIER-C-GATING` | Tier C Context Gating | (see RULES-ESSENTIAL.md) |
| `INFRA-USAGE` | Infrastructure Usage | Infrastructure Rules |

---

## EXEC-INTEGRITY: Execution Mode Rules (BLOCKING)

### LIVE Mode Required for Validation

**Rule ID:** `EXEC-INTEGRITY`
**Enforcement:** Command hooks (`PreToolUse`) -- block non-compliant tool calls

Any plan tagged `type: validation`, `type: ga-validation`, or `type: e2e` MUST use LIVE execution mode.

```python
# FORBIDDEN in validation plans
mode = "mock"
mode = "simulated"
mode = InvocationMode.MOCK
mode = InvocationMode.SIMULATED

# REQUIRED
mode = "live"
mode = InvocationMode.LIVE
```

**Verification command:**
```bash
grep -r "mode.*mock\|mode.*simulated" scripts/run_*.py && echo "FAIL: Mock mode in validation" && exit 1
```

**Exception:** Unit tests for testing infrastructure itself may use mock mode.

### Real API Calls Required

Validation MUST include actual Anthropic API calls with measured token usage. Hardcoded token estimates are forbidden.

```python
# FORBIDDEN
result.tokens_used += 1500   # Hardcoded estimate

# REQUIRED
result.tokens_used = api_response.usage.total_tokens  # Measured from API
tokens = extract_tokens_from_transcript(transcript)    # Or from Claude Code output
```

**Verification command:**
```bash
grep -r "tokens_used.*+=" scripts/run_*.py && echo "FAIL: Hardcoded tokens" && exit 1
```

### Real Duration Required

Validation reports MUST have non-zero `duration_ms` indicating actual execution. See `DURATION-BOUNDS` for per-operation thresholds.

**Verification command:**
```bash
jq '.duration_ms < 5000' .vrs/testing/reports/*.json | grep -q true && echo "FAIL: Below minimum duration" && exit 1
```

### Agent Teams-Based Execution for Interactive Tests

**Rule ID:** `EXEC-INTEGRITY` (sub-rule)
**Enforcement:** Command hooks (`PreToolUse`)

Interactive tests MUST use Agent Teams + `claude-code-controller`. Direct simulation and `subprocess.run("claude ...")` are forbidden.

**Required pattern:**
```bash
# Via claude-code-controller for programmatic test triggering
claude-code-controller launch "zsh"
claude-code-controller send "claude" --pane=<pane_id>
claude-code-controller send "/vrs-audit contracts/" --pane=<pane_id>
claude-code-controller wait_idle --pane=<pane_id> --idle-time=15.0
claude-code-controller capture --pane=<pane_id> --output=.vrs/testing/runs/<run_id>/transcript.txt
```

**Or via Agent Teams native:**
```
TeamCreate("vrs-test")
Task(subagent_type="BSKG Attacker")
TaskCreate(description="Investigate vault.sol")
SendMessage(teammate_id, "What findings?")
# Verify via controller event capture
```

---

## GROUND-TRUTH: Ground Truth Rules (BLOCKING)

### External Ground Truth Required

**Rule ID:** `GROUND-TRUTH`
**Enforcement:** Code-based graders in controller -- compare against `ground-truth.yaml`

Ground truth for validation MUST come from external sources with documented provenance. The system's own output MUST NOT be used as ground truth.

| Source | Quality | Provenance Required |
|--------|---------|---------------------|
| Code4rena reports | Gold | Report URL, contest ID |
| Sherlock contests | Gold | Contest URL, judge confirmation |
| Immunefi disclosures | Gold | Disclosure URL, bounty ID |
| Trail of Bits audits | Gold | Audit report URL |
| SmartBugs-curated | Silver | Commit hash, file path |
| CGT dataset | Silver | Commit hash, entry ID |

**Verification command:**
```bash
grep -r "is_true_positive.*True\|is_true_positive.*False" scripts/ && echo "FAIL: Hardcoded ground truth" && exit 1
```

### Ground Truth Separation

Ground truth MUST be stored separately from test code:

```
.vrs/corpus/ground-truth/
  code4rena/
    2024-05-vault.yaml
  smartbugs/
    curated-v1.yaml
  provenance.yaml
```

### No Circular Validation

Ground truth MUST NOT be derived from the system being tested. Using own findings as ground truth always produces 100% metrics and proves nothing.

```python
# FORBIDDEN
findings = our_tool.detect(contract)
ground_truth = findings  # Using own output!

# REQUIRED
findings = our_tool.detect(contract)
ground_truth = load_from_code4rena(contract)  # Independent source
```

---

## METRICS-REALISM: Metrics Rules (WARNING -> BLOCKING)

### Metrics Interpretation by Detection Tier

**Rule ID:** `METRICS-REALISM`
**Enforcement:** Controller event capture -- verify variance, error budget, tier-appropriate ranges

Expected metrics vary by detection tier -- different tiers are NOT comparable:

| Detection Tier | Expected Precision | Expected Recall | Rationale |
|----------------|-------------------|-----------------|-----------|
| **Tier A** (deterministic, graph patterns) | 80-95% | 70-90% | Deterministic patterns: high accuracy |
| **Tier B** (LLM-verified) | 60-85% | 50-80% | LLM verification introduces variance |
| **Tier C** (protocol context required) | 50-75% | 40-70% | Context-dependent: highest variance |
| **E2E pipeline** | >= 1 TP per contract | N/A | At least 1 true positive per known vulnerable contract |

**Required in reports:**
```yaml
metrics_context:
  detection_tier: "B"
  expected_precision_range: [0.60, 0.85]
  expected_recall_range: [0.50, 0.80]
  interpretation: "Metrics within expected range for Tier B detection"
```

### Perfect Metrics are Suspicious

Metrics of 100% precision AND 100% recall MUST trigger investigation.

| Metric | Suspicious Range | Expected Real Range |
|--------|------------------|---------------------|
| Precision | > 95% | 60-85% |
| Recall | > 98% | 50-80% |
| Pass rate | = 100% | 80-95% |
| Error rate | = 0% | 5-15% |

**If metrics are perfect, investigate:** Is the test set too easy? Is ground truth contaminated? Is validation using mock mode?

**Verification command:**
```bash
jq 'select(.precision >= 0.95 and .recall >= 0.98)' report.json && echo "WARN: Perfect metrics - investigate"
```

### Error Budget Required

Real validation MUST expect and document some failures:

| Validation Type | Expected Error Rate |
|-----------------|---------------------|
| Agent unit tests | 2-10% |
| Integration flows | 5-15% |
| E2E audits | 10-20% |
| Blind validation | 15-30% |

Zero failures across all test cases = fabrication signal.

### Variance Required

Results MUST show variance across different test cases. Identical metrics for all tests = fabrication indicator.

```json
// FORBIDDEN - identical
{"by_contract": [{"precision": 0.75, "recall": 1.0}, {"precision": 0.75, "recall": 1.0}]}

// REQUIRED - real variance
{"by_contract": [{"precision": 0.82, "recall": 0.91}, {"precision": 0.65, "recall": 1.0}]}
```

---

## ISOLATION + SESSION-NAMING + INFRA-USAGE: Infrastructure Rules (BLOCKING)

### Test Isolation

**Rule ID:** `ISOLATION`
**Enforcement:** Agent Teams architecture -- subject and controller are separate sessions by design

Test subject (Claude Code under test) MUST be isolated from test controller. Agent Teams provides isolation by design: `TeamCreate` creates a separate team context, and `claude-code-controller` manages session lifecycle externally.

```
Controller (pytest / orchestrator session)
    |
    | orchestrates via Agent Teams (TeamCreate, SendMessage, TaskCreate)
    | + claude-code-controller (launch, send, capture, kill)
    |
    v
Subject (isolated Claude Code session / team)
    |
    | real execution with real tools
    v
Output (captured transcript via controller event log)
```

Same-process simulation is forbidden. Controller and subject MUST be different processes/sessions.

### Session Naming Convention

**Rule ID:** `SESSION-NAMING`
**Enforcement:** Controller session management -- validate before launch

Agent Teams test sessions MUST use the standard naming convention:

```
vrs-demo-{workflow}-{timestamp}
```

Examples: `vrs-demo-smoke-1706644800`, `vrs-demo-audit-entrypoint-1706645100`

Hardcoded session names that can collide with parallel runs are forbidden.

```python
def validate_session_naming(session_name: str) -> bool:
    pattern = r'^vrs-demo-[a-zA-Z0-9-]+-\d{10}$'
    return bool(re.match(pattern, session_name))
```

**Capture interval:** 500ms (`CAPTURE_INTERVAL_MS`) for fast output detection.

### Use Existing Testing Infrastructure

**Rule ID:** `INFRA-USAGE`
**Enforcement:** Skill invocation audit

Validation MUST use testing skills and controller:

| Skill | When Required |
|-------|---------------|
| `/vrs-test-workflow` | Any workflow validation |
| `/vrs-test-e2e` | E2E workflow validation |
| `/vrs-test-component` | Component-level validation |
| `/vrs-test-enforce` | Rule/enforcement validation |
| `claude-code-controller` | Claude Code automation + capture |

### Transcript Capture Required

All interactive validation MUST capture full transcripts:

```
.vrs/testing/runs/
  workflow-test-20260130-143200.txt
  solo-vs-swarm-20260130-150000.txt
  e2e-audit-20260130-160000.txt
```

**Verification command:**
```bash
ls .vrs/testing/runs/*/transcript.txt | wc -l  # Must be > 0
```

---

## TRANSCRIPT-AUTH + DURATION-BOUNDS + EVIDENCE-CHAIN + GATE-INTEGRITY: Anti-Fabrication Rules (BLOCKING)

These rules detect when AI creates false tests that pass expected results without actually testing anything.

### Transcript Authenticity

**Rule ID:** `TRANSCRIPT-AUTH`
**Enforcement:** Agent hooks (`PostToolUse`) -- verify Agent Teams DM content, min transcript length, tool markers

Transcripts from interactive tests MUST be substantial, not fabricated stubs. The transcript source is Agent Teams direct messages and controller event logs.

**Minimum requirements:**

| Transcript Type | Minimum Lines | Required Markers |
|-----------------|---------------|------------------|
| Smoke test | 50 | `[PREFLIGHT_PASS]`, `[GRAPH_BUILD_SUCCESS]` |
| Agent unit test | 100 | Above + `SubagentStart`, `SubagentComplete` |
| E2E audit | 200 | Above + `TaskCreate`, `[REPORT_GENERATED]` |
| Full debate | 300 | Above + `[DEBATE_VERDICT]` |

**Nonce verification:** Each test run MUST include a unique nonce (run ID or timestamp) embedded in the transcript. Transcript content must be hashable for integrity verification -- if the hash changes between capture and validation, the run is invalidated.

**Required tool invocations (at least 3 of 4 categories):**

| Category | Required Patterns |
|----------|-------------------|
| Knowledge Graph | `alphaswarm\s+build-kg`, `Knowledge graph.*built` |
| Pattern Matching | `pattern:`, `Matching patterns` |
| Agent Investigation | `Attacker:`, `Defender:`, `Verifier:` |
| Code Locations | `\.sol\s*$`, `contracts/\w+\.sol` |

**Verification command:**
```bash
wc -l .vrs/testing/runs/*/transcript.txt | awk '$1 < 50 {print "FAIL:", $2; exit 1}'
for f in .vrs/testing/runs/*/transcript.txt; do
    grep -qE "alphaswarm|slither|Attacker:|Defender:" "$f" || echo "FAIL: No tool invocations in $f"
done
```

### Duration Bounds

**Rule ID:** `DURATION-BOUNDS`
**Enforcement:** Controller event capture -- min/max thresholds per operation

| Operation | Minimum (ms) | Maximum (ms) | Rationale |
|-----------|--------------|--------------|-----------|
| `smoke_test` | 5,000 | 60,000 | Basic smoke requires tool startup |
| `agent_unit` | 30,000 | 300,000 | Agent reasoning takes time |
| `integration` | 60,000 | 300,000 | Multi-step flows |
| `e2e_audit` | 120,000 | 600,000 | Full audit with debate |
| `skill_test` | 15,000 | 180,000 | Skill execution |
| `multi_agent_debate` | 180,000 | 600,000 | Full debate cycle |

**Instant completion (< minimum) = FABRICATION**
**Excessive duration (> maximum) = TIMEOUT or STUCK** -- investigate for hung processes

**Verification command:**
```bash
jq -r 'select(.operation == "e2e_audit" and .duration_ms < 120000) | "FAIL: \(.duration_ms)ms"' .vrs/testing/reports/*.json
```

### Evidence Chain

**Rule ID:** `EVIDENCE-CHAIN`
**Enforcement:** Code-based graders -- verify graph_nodes[], pattern_id, location

Every finding MUST have traceable evidence:

| Evidence Type | Required Fields |
|---------------|-----------------|
| Graph nodes | `graph_nodes[]` with valid BSKG node IDs |
| Pattern | `pattern_id` matching existing pattern |
| Code location | `location` in `file:line` format |
| Tool output | `tool_evidence[]` if tool was used |

Findings without evidence links are rejected.

**Verification function:**
```python
def verify_finding_evidence(finding: dict) -> bool:
    return (
        'graph_nodes' in finding and len(finding['graph_nodes']) > 0 and
        'pattern_id' in finding and
        'location' in finding and ':' in finding['location']
    )
```

### Gate Test Integrity

**Rule ID:** `GATE-INTEGRITY`
**Enforcement:** CI pre-merge -- required gate tests must be runnable

Any test file referenced by active phase gates must NOT be:
- `@pytest.mark.skip` -- skipped tests prove nothing
- `@pytest.mark.xfail` -- expected-failure tests are not gates
- Placeholder body (`pass`) in the primary test path

If a gate test is temporarily blocked, the phase must log drift + RCA and cannot claim completion.

**Verification command:**
```bash
rg -n "pytest\\.mark\\.(skip|xfail)|\\bpass\\b" tests/e2e tests/integration tests/workflow_harness
```

---

## REPORT-INTEGRITY: Reporting Rules (BLOCKING)

### Mode Declaration Required

**Rule ID:** `REPORT-INTEGRITY`
**Enforcement:** Prompt hooks -- single LLM call validates report structure

All validation reports MUST declare their execution mode:

```json
{
  "mode": "live",
  "api_calls_made": 47,
  "tokens_measured": true,
  "ground_truth_source": "SmartBugs-curated"
}
```

### Limitations Section Required

All validation reports MUST document limitations honestly. An empty limitations array is forbidden:

```json
{
  "limitations": [
    "Ground truth limited to SmartBugs contracts",
    "3 contracts timed out and were excluded",
    "Blind validation shows 15% lower recall than corpus validation"
  ]
}
```

### No Hidden Mock Acknowledgments

Mock results MUST NOT claim validation status. A report with `"status": "PASS"` and `"limitations": ["Results are simulated"]` is a violation.

---

## ARTIFACT-PROD + ARTIFACT-DEP + WAVE-GATE: Artifact Dependency Rules (BLOCKING)

### Artifact Production Declaration

**Rule ID:** `ARTIFACT-PROD`
**Enforcement:** Plan headers

Every plan MUST declare what artifacts it produces:

```yaml
produces:
  - path: ".vrs/testing/reports/smoke-test.json"
    type: report
    validation: json_schema
```

### Dependency Verification Before Execution

**Rule ID:** `ARTIFACT-DEP`
**Enforcement:** Pre-execution checks

Plans MUST verify required artifacts exist before starting execution:

```python
def verify_dependencies(plan_id: str) -> list[str]:
    DEPENDENCIES = {
        "02-v4": [".vrs/testing/reports/tool-install-test.json"],
        "05-v4": [".vrs/testing/reports/integration-tests.json", ".vrs/corpus/ground-truth.yaml"],
        "08-v4": [".vrs/testing/reports/e2e-audit.json", ".vrs/testing/reports/blind-validation.json"],
    }
    return [a for a in DEPENDENCIES.get(plan_id, []) if not Path(a).exists()]
```

### Wave Gate Enforcement

**Rule ID:** `WAVE-GATE`
**Enforcement:** Composite gate checks

Plans MUST NOT proceed to next wave until gate conditions are met:

```yaml
gate_1:
  name: "Smoke Verification"
  conditions:
    - file_exists: ".vrs/testing/reports/smoke-test.json"
    - json_field: ".vrs/testing/reports/smoke-test.json:.status == 'passed'"
    - duration_check: ".vrs/testing/reports/smoke-test.json:.duration_ms >= 5000"
  action_on_fail: "BLOCK - Fix smoke test before proceeding"
```

---

## AUTOMATED ENFORCEMENT

### Pre-Merge Check

```bash
#!/bin/bash
set -e
echo "=== VALIDATION RULES CHECK ==="

# EXEC-INTEGRITY: No mock mode in validation
if grep -r "mode.*mock\|mode.*simulated" scripts/run_*.py 2>/dev/null; then
    echo "FAIL: Mock mode detected in validation scripts"; exit 1
fi
echo "EXEC-INTEGRITY: No mock mode"

# EXEC-INTEGRITY: No hardcoded tokens
if grep -r "tokens_used.*+=" scripts/run_*.py 2>/dev/null; then
    echo "FAIL: Hardcoded token counts detected"; exit 1
fi
echo "EXEC-INTEGRITY: No hardcoded tokens"

# GROUND-TRUTH: No fabricated ground truth
if grep -r "is_true_positive.*=" scripts/run_*.py 2>/dev/null; then
    echo "FAIL: Hardcoded ground truth labels detected"; exit 1
fi
echo "GROUND-TRUTH: No fabricated ground truth"

# DURATION-BOUNDS: Check for zero duration
for report in .vrs/testing/reports/*.json; do
    if [ -f "$report" ]; then
        if jq -e '.duration_ms == 0' "$report" > /dev/null 2>&1; then
            echo "FAIL: Zero duration in $report"; exit 1
        fi
    fi
done
echo "DURATION-BOUNDS: Non-zero durations"

# TRANSCRIPT-AUTH: Transcript length verification
for transcript in .vrs/testing/runs/*/transcript.txt; do
    if [ -f "$transcript" ]; then
        lines=$(wc -l < "$transcript")
        if [ "$lines" -lt 50 ]; then
            echo "FAIL: Transcript too short ($lines lines): $transcript"; exit 1
        fi
    fi
done
echo "TRANSCRIPT-AUTH: Transcript lengths valid"

# TRANSCRIPT-AUTH: Tool invocation markers
for transcript in .vrs/testing/runs/*/transcript.txt; do
    if [ -f "$transcript" ]; then
        if ! grep -qE "alphaswarm|slither|Attacker:|Defender:|Verifier:" "$transcript"; then
            echo "FAIL: No tool invocations in: $transcript"; exit 1
        fi
    fi
done
echo "TRANSCRIPT-AUTH: Tool invocations present"

# DURATION-BOUNDS: Per-operation thresholds
for report in .vrs/testing/reports/*.json; do
    if [ -f "$report" ]; then
        operation=$(jq -r '.operation // "unknown"' "$report")
        duration=$(jq -r '.duration_ms // 0' "$report")
        case "$operation" in
            e2e_audit)
                if [ "$duration" -lt 120000 ]; then
                    echo "FAIL: E2E audit too fast (${duration}ms): $report"; exit 1
                fi ;;
            agent_unit)
                if [ "$duration" -lt 30000 ]; then
                    echo "FAIL: Agent unit too fast (${duration}ms): $report"; exit 1
                fi ;;
        esac
    fi
done
echo "DURATION-BOUNDS: Duration thresholds met"

echo ""
echo "=== ALL VALIDATION RULES PASSED ==="
```

### Report Validation Script

```python
#!/usr/bin/env python3
"""scripts/validate_report_integrity.py -- validates reports against rule IDs."""

import json
import re
import sys
from pathlib import Path

MIN_DURATIONS = {
    'smoke_test': 5000, 'agent_unit': 30000, 'integration': 60000,
    'e2e_audit': 120000, 'full_audit': 180000, 'skill_test': 15000,
}

REQUIRED_MARKERS = [
    r"alphaswarm\s+build-kg", r"Knowledge graph.*built",
    r"Attacker:|Defender:|Verifier:", r"\.sol\s*$|contracts/\w+\.sol",
]


def validate_report(path: Path) -> list[str]:
    errors = []
    with open(path) as f:
        report = json.load(f)

    # EXEC-INTEGRITY: Non-zero duration
    if report.get("duration_ms", 0) < 1000:
        errors.append(f"EXEC-INTEGRITY: duration_ms={report.get('duration_ms')} < 1000")

    # METRICS-REALISM: Suspicious perfect metrics
    precision = report.get("precision", 0)
    recall = report.get("recall", 0)
    if precision >= 0.95 and recall >= 0.98:
        errors.append(f"METRICS-REALISM: Suspiciously perfect (P={precision}, R={recall})")

    # REPORT-INTEGRITY: Mode declaration
    mode = report.get("mode") or report.get("metadata", {}).get("mode")
    if mode in ["mock", "simulated"]:
        errors.append(f"REPORT-INTEGRITY: Uses {mode} mode, not 'live'")

    # REPORT-INTEGRITY: Limitations required
    if not report.get("limitations"):
        errors.append("REPORT-INTEGRITY: No limitations section")

    # DURATION-BOUNDS: Threshold by operation type
    operation = report.get("operation", "unknown")
    duration = report.get("duration_ms", 0)
    min_duration = MIN_DURATIONS.get(operation, 5000)
    if duration < min_duration:
        errors.append(f"DURATION-BOUNDS: {operation} {duration}ms < {min_duration}ms minimum")

    # EVIDENCE-CHAIN: Cross-evidence for findings
    for i, finding in enumerate(report.get("findings", [])):
        fid = finding.get("id", f"finding-{i}")
        if not finding.get("graph_nodes"):
            errors.append(f"EVIDENCE-CHAIN: {fid} has no graph_nodes")
        if not finding.get("pattern_id"):
            errors.append(f"EVIDENCE-CHAIN: {fid} has no pattern_id")
        loc = finding.get("location", "")
        if not loc or ":" not in loc:
            errors.append(f"EVIDENCE-CHAIN: {fid} has no valid location")

    return errors


def validate_transcript(path: Path) -> list[str]:
    errors = []
    content = path.read_text()
    lines = content.strip().split('\n')

    # TRANSCRIPT-AUTH: Length
    if len(lines) < 50:
        errors.append(f"TRANSCRIPT-AUTH: {len(lines)} lines (< 50 minimum)")

    # TRANSCRIPT-AUTH: Tool markers
    marker_matches = sum(1 for p in REQUIRED_MARKERS if re.search(p, content, re.I))
    if marker_matches < 2:
        errors.append(f"TRANSCRIPT-AUTH: Only {marker_matches}/4 tool markers (need >= 2)")

    return errors


if __name__ == "__main__":
    all_errors = []
    for path in Path(".vrs/testing/reports").glob("*.json"):
        all_errors.extend([f"{path.name}: {e}" for e in validate_report(path)])
    for path in Path(".vrs/testing/runs").glob("*.txt"):
        all_errors.extend([f"{path.name}: {e}" for e in validate_transcript(path)])

    if all_errors:
        print("VALIDATION FAILURES:")
        for e in all_errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("All reports and transcripts pass validation")
```

---

## PHASE COMPLETION CHECKLIST

Before marking ANY validation phase complete:

### Execution Checks (EXEC-INTEGRITY)
- [ ] All tests use LIVE mode (not mock/simulated)
- [ ] Durations are non-zero and realistic (within DURATION-BOUNDS)
- [ ] Token usage is measured from API (not hardcoded)
- [ ] Agent Teams-based execution used for interactive tests (TeamCreate + Task + SendMessage)

### Ground Truth Checks (GROUND-TRUTH)
- [ ] Ground truth comes from external source (Code4rena, Sherlock, etc.)
- [ ] Provenance documented for all labels
- [ ] No `is_true_positive=True/False` in code
- [ ] Ground truth stored separately from test code

### Metrics Checks (METRICS-REALISM)
- [ ] Metrics show variance across test cases
- [ ] No suspiciously perfect results (100%/0%)
- [ ] Error budget documented and realistic
- [ ] Metrics interpreted relative to detection tier

### Infrastructure Checks (ISOLATION, SESSION-NAMING, INFRA-USAGE)
- [ ] Testing skills used for validation (`/vrs-test-workflow`, etc.)
- [ ] Transcripts captured and stored in `.vrs/testing/runs/`
- [ ] Test subject isolated from controller (separate sessions)
- [ ] Session naming follows `vrs-demo-{workflow}-{timestamp}` convention

### Reporting Checks (REPORT-INTEGRITY)
- [ ] Mode declared as "live"
- [ ] Limitations documented honestly
- [ ] No hidden mock acknowledgments

### Anti-Fabrication Checks (TRANSCRIPT-AUTH, DURATION-BOUNDS, EVIDENCE-CHAIN, GATE-INTEGRITY)
- [ ] Transcripts have minimum line count (50+ for smoke, 200+ for E2E)
- [ ] Transcripts contain tool invocation markers (3+ of 4 categories)
- [ ] Nonce/hash verification for transcript integrity
- [ ] Duration matches operation type thresholds (min AND max)
- [ ] Findings have cross-evidence (graph_nodes, pattern_id, location)
- [ ] Required gate tests are not skip/xfail/placeholder

### Artifact Dependency Checks (ARTIFACT-PROD, ARTIFACT-DEP, WAVE-GATE)
- [ ] Plan declares produced artifacts
- [ ] Dependencies verified before execution
- [ ] Wave gate conditions met before proceeding

---

## RETROACTIVE APPLICATION

These rules apply RETROACTIVELY to Phase 07.3:
1. **Invalidate** all existing 07.3 reports (mode=mock/simulated)
2. **Archive** simulation scripts to `scripts/archive/simulations/`
3. **Re-execute** validation using LIVE mode per redesign
4. **Re-report** with measured metrics and honest limitations

---

## VERSIONING

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-30 | Initial rules based on 07.3 audit |
| 1.1 | 2026-01-30 | Added Category F (Anti-Fabrication) and Category G (Artifact Dependency) |
| 1.2 | 2026-02-03 | Added C0 (Metrics by Tier) and F3b (Max Duration) |
| 2.0 | 2026-02-11 | **Major rewrite:** Aligned with stable rule IDs from RULES-ESSENTIAL.md v3.0. Replaced legacy execution model with Agent Teams + claude-code-controller. Updated D3 (Isolation) for Agent Teams architecture. Removed legacy session naming rules. Preserved all anti-fabrication rules (nonce, hash, duration > 5s, evidence). All rules use shared ID namespace with RULES-ESSENTIAL.md. |

---

**These rules are MANDATORY. Violations block phase completion.**
