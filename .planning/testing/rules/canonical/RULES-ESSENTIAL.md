# Essential Testing Rules (Auto-Invoke)

**Version:** 3.0 | **Updated:** 2026-02-11
**Execution Model:** Agent Teams (Claude Code native) + `claude-code-controller` (npm v0.6.1)

> These rules are the testing contract for AlphaSwarm.sol. They define what constitutes valid testing, how evidence is verified, and what enforcement mechanisms exist. All rule IDs are stable and usable by evaluation contracts via `rule_refs[]`.

---

## Rule ID Registry

Every rule category has a stable machine-readable ID. Evaluation contracts (3.1-05, 3.1c-06) reference these IDs via `rule_refs: ["EXEC-INTEGRITY", "GROUND-TRUTH", ...]`.

| ID | Category | Enforcement Mechanism | Merged From |
|---|---|---|---|
| `EXEC-INTEGRITY` | Execution Integrity | Command hooks (`PreToolUse`) -- block non-compliant tool calls | A1, A2, A3, A4 |
| `TRANSCRIPT-AUTH` | Transcript Authenticity | Agent hooks (`PostToolUse`) -- verify transcript content, min length, tool markers | F1, F2, F1b |
| `METRICS-REALISM` | Metrics Realism | Controller event capture -- verify `total_cost_usd > 0`, duration bounds, variance | C1, C2, C3 |
| `GROUND-TRUTH` | Ground Truth Provenance | Code-based graders in controller -- compare against `ground-truth.yaml` | B1, B2, B3 |
| `REPORT-INTEGRITY` | Report Integrity | Prompt hooks -- single LLM call validates report structure and limitations | E1, E2, E3 |
| `DURATION-BOUNDS` | Duration Bounds | Controller event capture -- enforce min/max duration thresholds per operation type | F3, F3b |
| `EVIDENCE-CHAIN` | Evidence Chain | Code-based graders -- verify graph_nodes[], pattern_id, location for every finding | F4 |
| `GATE-INTEGRITY` | Gate Test Integrity | CI pre-merge -- required gate tests cannot be skip/xfail/placeholder | F5 |
| `ISOLATION` | Test Isolation | Agent Teams architecture -- subject and controller are separate sessions | D3 |
| `SESSION-NAMING` | Session Naming Convention | Controller session management -- `vrs-demo-{workflow}-{timestamp}` pattern | D4 |
| `ARTIFACT-PROD` | Artifact Production | Plan headers -- every plan declares what it produces | G1 |
| `ARTIFACT-DEP` | Artifact Dependency | Pre-execution checks -- verify required artifacts exist before starting | G2 |
| `WAVE-GATE` | Wave Gate Enforcement | Composite gate checks -- block next wave until conditions met | G3 |
| `TIER-C-GATING` | Tier C Context Gating | Context Trust Level check -- block Tier C without sufficient protocol context | T1, T2, T3, T4 |
| `INFRA-USAGE` | Infrastructure Usage | Skill invocation -- validation must use testing skills and controller, not bypass | D1, D2 |

**Total: 15 categories**

---

## AUTO-INVOKE TRIGGERS

**CRITICAL: These rules MUST be loaded when ANY of these patterns appear:**

| Trigger Pattern | Rules to Apply |
|-----------------|----------------|
| `skill`, `SKILL.md`, `/vrs-*` | Skill Testing Rules (EXEC-INTEGRITY, TRANSCRIPT-AUTH) |
| `subagent`, `agent`, `.claude/agents/` | Agent Testing Rules (EXEC-INTEGRITY, ISOLATION) |
| `orchestrat*`, `workflow`, `multi-agent` | Orchestration Testing Rules (all categories) |
| `team`, `teammate`, `TeamCreate`, `SendMessage` | Agent Teams Rules (EXEC-INTEGRITY, ISOLATION, SESSION-NAMING) |
| `controller`, `claude-code-controller` | Controller Rules (DURATION-BOUNDS, TRANSCRIPT-AUTH, METRICS-REALISM) |
| `/gsd-plan-phase`, `plan phase`, `phase planning` | Plan-Phase Governance Rules |
| `validation`, `e2e`, `ga-validation` | Full Validation Rules (all categories) |
| `evaluation`, `contract`, `rule_refs` | Evaluation Contract Rules (GATE-INTEGRITY, ARTIFACT-PROD) |

---

## EXEC-INTEGRITY: Execution Integrity

**Rule ID:** `EXEC-INTEGRITY`
**Enforcement:** Command hooks (`PreToolUse`) -- block non-compliant tool calls
**Merged from:** A1 (LIVE Mode Required), A2 (Real API Calls), A3 (Real Duration), A4 (Agent Teams Execution)

### LIVE Mode Required

Any plan tagged `validation`, `ga-validation`, `e2e`, or testing skills/agents MUST use LIVE execution mode. Mock and simulated modes are forbidden in validation plans.

```python
# FORBIDDEN in validation plans
mode = "mock"
mode = "simulated"
mode = InvocationMode.MOCK

# REQUIRED
mode = "live"
mode = InvocationMode.LIVE
```

**Exception:** Unit tests for testing infrastructure itself may use mock mode.

### Real API Calls Required

Validation MUST include actual Anthropic API calls with measured token usage. Hardcoded token estimates (`result.tokens_used += 1500`) are forbidden. Token counts must be extracted from actual API responses or captured from Claude Code output.

### Real Duration Required

Validation reports MUST have non-zero `duration_ms` indicating actual execution. See DURATION-BOUNDS for per-operation thresholds.

### Agent Teams-Based Execution

All interactive testing (Claude Code workflows, agent orchestration) MUST use Agent Teams + `claude-code-controller`. Direct simulation, `subprocess.run("claude ...")`, and hardcoded outputs are forbidden.

**Required 5-Step Mandatory Testing Pattern:**

1. **`TeamCreate("vrs-test")`** -- Create a dedicated test team
2. **`Task(subagent_type="BSKG Attacker")`** -- Spawn specialized teammates (attacker, defender, verifier)
3. **`TaskCreate/TaskUpdate`** -- Assign work items and track completion
4. **`SendMessage`** -- Monitor progress, coordinate between teammates, collect results
5. **Verify via controller event capture** -- Validate `message`, `task:completed`, `agent:exited` events

```bash
# Controller commands for programmatic test triggering
claude-code-controller launch "zsh"                          # Start isolated shell
claude-code-controller send "claude" --pane=<pane_id>        # Launch Claude Code
claude-code-controller send "/vrs-audit contracts/" --pane=<pane_id>  # Execute workflow
claude-code-controller wait_idle --pane=<pane_id> --idle-time=15.0    # Wait for completion
claude-code-controller capture --pane=<pane_id> --output=transcript.txt  # Capture output
claude-code-controller kill --pane=<pane_id>                 # Cleanup
```

**Forbidden patterns:**
| Forbidden | Required |
|-----------|----------|
| Direct simulation | Agent Teams `TeamCreate` + `Task` + `SendMessage` |
| `subprocess.run("claude ...")` | Isolated Claude Code session via `claude-code-controller` |
| Hardcoded outputs | Real transcript capture via controller |

---

## TRANSCRIPT-AUTH: Transcript Authenticity

**Rule ID:** `TRANSCRIPT-AUTH`
**Enforcement:** Agent hooks (`PostToolUse`) -- verify Agent Teams DM content, minimum transcript length, tool invocation markers
**Merged from:** F1 (Transcript Length), F2 (Required Tool Invocations), F1b (Nonce Verification)

### Transcript Length Verification

Transcripts from interactive tests MUST be substantial, not fabricated stubs. The transcript source is Agent Teams direct messages and controller event logs.

| Transcript Type | Min Lines | Max Lines | Required Markers |
|-----------------|-----------|-----------|------------------|
| Smoke test | 50 | 500 | `[PREFLIGHT_PASS]`, `[GRAPH_BUILD_SUCCESS]` |
| Agent unit | 100 | 2000 | Above + `SubagentStart`, `SubagentComplete` |
| E2E audit | 200 | 5000 | Above + `TaskCreate`, `[REPORT_GENERATED]` |
| Multi-agent debate | 300 | 8000 | Above + `[DEBATE_VERDICT]` |

**Fabrication detection:** Transcripts with fewer than the minimum line count are classified as fabricated. Stub transcripts (e.g., 5-line "Audit complete. Findings: 2") are automatically rejected.

### Required Tool Invocations

Every audit transcript MUST contain evidence of actual tool usage. At least 3 of 4 marker categories must be present:

| Category | Required Patterns |
|----------|-------------------|
| Knowledge Graph | `alphaswarm\s+build-kg`, `Knowledge graph.*built` |
| Pattern Matching | `pattern:`, `Matching patterns` |
| Agent Investigation | `Attacker:`, `Defender:`, `Verifier:` |
| Code Locations | `\.sol\s*$`, `contracts/\w+\.sol` |

### Nonce and Hash Verification

Each test run MUST include a unique nonce (run ID or timestamp-based identifier) embedded in the transcript. Transcript content must be hashable for integrity verification. If transcript hash changes between capture and validation, the run is invalidated.

```python
def verify_transcript_authentic(transcript: str) -> bool:
    """Transcripts must be substantial with tool evidence and nonce."""
    lines = transcript.strip().split('\n')
    has_min_length = len(lines) >= 50
    has_tool_markers = sum(1 for p in REQUIRED_MARKERS if re.search(p, transcript, re.I)) >= 3
    has_nonce = re.search(r'run[-_]id|nonce|session[-_]id', transcript, re.I) is not None
    return has_min_length and has_tool_markers and has_nonce
```

---

## METRICS-REALISM: Metrics Realism

**Rule ID:** `METRICS-REALISM`
**Enforcement:** Controller event capture -- verify `total_cost_usd > 0`, duration > 5s, variance across test cases
**Merged from:** C1 (Perfect Metrics Suspicious), C2 (Error Budget), C3 (Variance Required)

### Perfect Metrics Are Suspicious

Metrics of 100% precision AND 100% recall MUST trigger mandatory investigation. Any test reporting zero errors across all cases is treated as potentially fabricated until proven otherwise.

| Metric | Suspicious Range | Expected Real Range |
|--------|------------------|---------------------|
| Precision | > 95% | 60-85% |
| Recall | > 98% | 50-80% |
| Pass rate | 100% | 80-95% |
| Error rate | 0% | 5-15% |

**If metrics are perfect, investigate:** Is the test set too easy? Is ground truth contaminated? Is validation using mock mode?

### Metrics by Detection Tier

Expected metrics vary by tier -- different tiers are NOT comparable:

| Detection Tier | Expected Precision | Expected Recall | Rationale |
|----------------|-------------------|-----------------|-----------|
| **Tier A** (deterministic, graph) | 80-95% | 70-90% | Deterministic patterns: high accuracy |
| **Tier B** (LLM-verified) | 60-85% | 50-80% | LLM verification introduces variance |
| **Tier C** (protocol context) | 50-75% | 40-70% | Context-dependent: highest variance |
| **E2E pipeline** | >= 1 TP per contract | N/A | At least 1 true positive per known vulnerable contract |

### Error Budget Required

Real validation MUST expect and document some failures. Zero failures across all test cases = fabrication signal.

| Validation Type | Expected Error Rate |
|-----------------|---------------------|
| Agent unit tests | 2-10% |
| Integration flows | 5-15% |
| E2E audits | 10-20% |
| Blind validation | 15-30% |

### Variance Required

Results MUST show variance across different test cases. Identical metrics for all tests (e.g., every contract producing `precision: 0.75, recall: 1.0`) is a fabrication indicator.

```json
// FORBIDDEN - identical metrics
{"by_contract": [{"precision": 0.75}, {"precision": 0.75}, {"precision": 0.75}]}

// REQUIRED - real variance
{"by_contract": [{"precision": 0.82}, {"precision": 0.65}, {"precision": 0.90}]}
```

---

## GROUND-TRUTH: Ground Truth Provenance

**Rule ID:** `GROUND-TRUTH`
**Enforcement:** Code-based graders in controller -- compare findings against `ground-truth.yaml` with documented provenance
**Merged from:** B1 (External Sources), B2 (Separation), B3 (No Circular Validation)

### External Sources Only

Ground truth MUST come from external sources with documented provenance. The system's own output MUST NOT be used as ground truth.

| Acceptable Source | Quality | Provenance Required |
|-------------------|---------|---------------------|
| Code4rena reports | Gold | Report URL, contest ID |
| Sherlock contests | Gold | Contest URL, judge confirmation |
| Immunefi disclosures | Gold | Disclosure URL, bounty ID |
| Trail of Bits audits | Gold | Audit report URL |
| SmartBugs-curated | Silver | Commit hash, file path |
| CGT dataset | Silver | Commit hash, entry ID |

**Forbidden:** `is_true_positive=True` manually assigned in code. `Finding(confidence=0.85)` hardcoded.

### Ground Truth Separation

Ground truth MUST be stored separately from test code, in dedicated files with documented provenance:

```
.vrs/corpus/ground-truth/
  code4rena/
    2024-05-vault.yaml
  smartbugs/
    curated-v1.yaml
  provenance.yaml  # Documents all sources
```

### No Circular Validation

Ground truth MUST NOT be derived from the system being tested. Using our own `findings` as `ground_truth` always produces 100% metrics and proves nothing.

```python
# FORBIDDEN - circular
findings = our_tool.detect(contract)
ground_truth = findings  # Using own output!

# REQUIRED - external comparison
findings = our_tool.detect(contract)
ground_truth = load_from_code4rena(contract)
```

---

## REPORT-INTEGRITY: Report Integrity

**Rule ID:** `REPORT-INTEGRITY`
**Enforcement:** Prompt hooks -- single LLM call validates report structure, mode declaration, and limitations
**Merged from:** E1 (Mode Declaration), E2 (Limitations Required), E3 (No Hidden Mock Acknowledgments)

### Mode Declaration Required

All validation reports MUST declare their execution mode. Reports using mock/simulated mode MUST NOT claim validation status.

```json
{
  "mode": "live",
  "api_calls_made": 47,
  "tokens_measured": true,
  "ground_truth_source": "SmartBugs-curated"
}
```

### Limitations Section Required

All validation reports MUST document limitations honestly. An empty limitations array is forbidden.

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

If mock/simulated mode is used (only permitted for infrastructure unit tests), it MUST NOT be hidden in fine print. Mock results MUST NOT claim validation status. A report with `"status": "PASS"` and `"limitations": ["Results are simulated"]` is a violation.

---

## DURATION-BOUNDS: Duration Bounds

**Rule ID:** `DURATION-BOUNDS`
**Enforcement:** Controller event capture -- enforce minimum and maximum duration thresholds per operation type
**Merged from:** F3 (Min Duration), F3b (Max Duration)

### Minimum Duration Thresholds

Instant completion (below minimum) = FABRICATION. Real operations take measurable time.

| Operation | Min (ms) | Max (ms) | Rationale |
|-----------|----------|----------|-----------|
| smoke_test | 5,000 | 60,000 | Tool startup |
| agent_unit | 30,000 | 300,000 | Agent reasoning |
| integration | 60,000 | 300,000 | Multi-step flows |
| e2e_audit | 120,000 | 600,000 | Full audit |
| skill_test | 15,000 | 180,000 | Skill execution |
| multi_agent_debate | 180,000 | 600,000 | Full debate cycle |

**Instant completion (< minimum) = FABRICATION**
**Excessive duration (> maximum) = TIMEOUT or STUCK** -- investigate for hung processes, infinite loops

### Duration Verification

```python
def verify_duration(report: dict) -> tuple[bool, list[str]]:
    """Duration must be within realistic bounds for the operation."""
    duration_ms = report.get('duration_ms', 0)
    operation = report.get('operation', 'unknown')
    errors = []

    MIN_DURATIONS = {
        'smoke_test': 5000, 'agent_unit': 30000, 'integration': 60000,
        'e2e_audit': 120000, 'skill_test': 15000, 'multi_agent_debate': 180000,
    }
    MAX_DURATIONS = {
        'smoke_test': 60000, 'agent_unit': 300000, 'integration': 300000,
        'e2e_audit': 600000, 'skill_test': 180000, 'multi_agent_debate': 600000,
    }

    if duration_ms < MIN_DURATIONS.get(operation, 5000):
        errors.append(f"FABRICATION: {operation} took {duration_ms}ms < minimum")
    if duration_ms > MAX_DURATIONS.get(operation, 600000):
        errors.append(f"TIMEOUT: {operation} took {duration_ms}ms > maximum")
    return len(errors) == 0, errors
```

---

## EVIDENCE-CHAIN: Evidence Chain

**Rule ID:** `EVIDENCE-CHAIN`
**Enforcement:** Code-based graders -- verify every finding has graph_nodes[], pattern_id, and location
**Merged from:** F4 (Cross-Evidence Verification)

Every finding MUST be traceable to multiple evidence sources:

| Evidence Type | Required Fields |
|---------------|-----------------|
| Graph nodes | `graph_nodes[]` with valid BSKG node IDs |
| Pattern | `pattern_id` matching an existing VulnDocs pattern |
| Code location | `location` in `file:line` format |
| Tool output | `tool_evidence[]` if external tool was used |

```python
def verify_finding_evidence(finding: dict) -> bool:
    """Every finding needs traceable, cross-referenced evidence."""
    return (
        'graph_nodes' in finding and len(finding['graph_nodes']) > 0 and
        'pattern_id' in finding and
        'location' in finding and ':' in finding['location']
    )
```

Findings without evidence links are rejected. This ensures no "I found a reentrancy vulnerability" without specifying which graph nodes, which pattern, and which code location.

---

## GATE-INTEGRITY: Gate Test Integrity

**Rule ID:** `GATE-INTEGRITY`
**Enforcement:** CI pre-merge checks -- required gate tests must be runnable, not placeholders
**Merged from:** F5 (Required Gate Tests Cannot Be Placeholders)

Any test file referenced by active phase gates must NOT be:
- `@pytest.mark.skip` -- skipped tests prove nothing
- `@pytest.mark.xfail` -- expected-failure tests are not gates
- Placeholder body (`pass`) in the primary test path

If a gate test is temporarily blocked, the phase must log drift and a root cause analysis, and the phase cannot claim completion.

For `/gsd-plan-phase`, check design must be derived from evidence:
- Load `.planning/testing/PLAN-PHASE-GOVERNANCE.md`
- Generate derived checks to `.vrs/debug/phase-*/plan-phase/derived-checks/`
- Avoid static expected outcomes without derivation notes

---

## ISOLATION: Test Isolation

**Rule ID:** `ISOLATION`
**Enforcement:** Agent Teams architecture -- subject and controller are separate sessions by design
**Merged from:** D3 (Isolation Required)

The test subject (Claude Code under test) MUST be isolated from the test controller. Agent Teams provides this isolation by design: `TeamCreate` creates a separate team context, and `claude-code-controller` manages session lifecycle from outside.

```
Controller (your pytest / orchestrator session)
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

Same-process simulation (`findings = simulate_agent_detection()`) is forbidden. The controller and subject MUST be different processes/sessions.

---

## SESSION-NAMING: Session Naming Convention

**Rule ID:** `SESSION-NAMING`
**Enforcement:** Controller session management -- validate naming pattern before launch
**Merged from:** D4 (Session Naming Convention)

Agent Teams test sessions MUST use the standard naming convention to prevent collisions in parallel execution:

```
vrs-demo-{workflow}-{timestamp}
```

Examples: `vrs-demo-smoke-1706644800`, `vrs-demo-audit-entrypoint-1706645100`

Hardcoded session names (`"vrs-demo"`, `"test"`) that can collide with parallel runs are forbidden.

```python
def validate_session_naming(session_name: str) -> bool:
    pattern = r'^vrs-demo-[a-zA-Z0-9-]+-\d{10}$'
    return bool(re.match(pattern, session_name))
```

---

## ARTIFACT-PROD: Artifact Production

**Rule ID:** `ARTIFACT-PROD`
**Enforcement:** Plan headers -- every plan declares produced artifacts
**Merged from:** G1 (Artifact Production Declaration)

Every plan MUST declare what artifacts it produces in its header. Each artifact specifies path, type, and validation method.

---

## ARTIFACT-DEP: Artifact Dependency

**Rule ID:** `ARTIFACT-DEP`
**Enforcement:** Pre-execution checks -- verify required artifacts exist before starting
**Merged from:** G2 (Dependency Verification Before Execution)

Plans MUST verify required artifacts exist before starting execution. Missing dependencies are blocking errors, not warnings.

---

## WAVE-GATE: Wave Gate Enforcement

**Rule ID:** `WAVE-GATE`
**Enforcement:** Composite gate checks -- block next wave until all conditions met
**Merged from:** G3 (Wave Gate Enforcement)

Plans MUST NOT proceed to next wave until gate conditions are met. Gate conditions include file existence, JSON field validation, and duration checks.

---

## TIER-C-GATING: Tier C Context Gating

**Rule ID:** `TIER-C-GATING`
**Enforcement:** Context Trust Level (CTL) check -- block Tier C execution without sufficient protocol context
**Merged from:** T1 (CTL Gating), T2 (Required Context Fields), T3 (Simulated Context Bypass), T4 (Blocking Marker)

Tier C patterns REQUIRE sufficient context before execution:

| CTL Level | Definition | Tier C Permission |
|-----------|------------|-------------------|
| **high** | Official docs + externally verified | Full Tier C |
| **medium** | Official docs, not verified | Partial Tier C (low-risk only) |
| **low** | Inferred from code only | **BLOCKED** |
| **simulated** | Fabricated for testing | **BLOCKED** (requires bypass marker) |

Required context fields (5/5 for full execution): `protocol_type`, `trust_boundaries`, `asset_types`, `upgradeability`, `economic_model`. Field presence check: `count(present) / 5 >= 0.60` for partial execution.

For testing only, use explicit bypass marker: `[CONTEXT_SIMULATED_BYPASS reason={testing_tier_c_patterns|synthetic_scenario|regression_test}]`. Bypass markers MUST NOT appear outside test directories.

---

## INFRA-USAGE: Infrastructure Usage

**Rule ID:** `INFRA-USAGE`
**Enforcement:** Skill invocation audit -- validation must use testing skills and controller, not bypass infrastructure
**Merged from:** D1 (Use Existing Testing Skills), D2 (Transcript Capture Required)

### Use Testing Skills

Validation MUST use the testing infrastructure (skills + controller). Bypassing infrastructure with direct simulation functions is forbidden.

| Skill | When Required |
|-------|---------------|
| `/vrs-test-workflow` | Any workflow validation |
| `/vrs-test-e2e` | E2E workflow validation |
| `/vrs-test-component` | Component-level validation |
| `/vrs-test-enforce` | Rule/enforcement validation |
| `claude-code-controller` | Claude Code automation + transcript capture |

### Transcript Capture Required

All interactive validation MUST capture full transcripts to `.vrs/testing/runs/`. Transcripts are the primary evidence of real execution.

---

## Quick Command Reference

```bash
# Agent Teams -- team lifecycle
TeamCreate("vrs-test")                          # Create test team
Task(subagent_type="BSKG Attacker")             # Spawn teammate
TaskCreate(description="...")                     # Assign work
SendMessage(teammate_id, "status?")              # Coordinate
TaskUpdate(task_id, status="completed")          # Track completion

# claude-code-controller -- programmatic test triggering
claude-code-controller launch "zsh"              # Start isolated shell
claude-code-controller send "cmd" --pane=X       # Execute command
claude-code-controller wait_idle --pane=X --idle-time=10.0  # Wait for idle
claude-code-controller capture --pane=X          # Get output
claude-code-controller kill --pane=X             # Cleanup

# Validation quick checks
jq '.duration_ms < 5000' report.json             # Too fast = fail
wc -l transcript.txt                              # < 50 = fail
grep -E "alphaswarm|slither" transcript.txt      # Missing = fail
```

---

## Detailed Reference Files

| Topic | File | When to Load |
|-------|------|--------------|
| Full validation rules | `.planning/testing/rules/canonical/VALIDATION-RULES.md` | All validation phases |
| **Orchestration markers** | `.planning/testing/rules/canonical/ORCHESTRATION-MARKERS.md` | Transcript validation |
| **Proof token matrix** | `.planning/testing/rules/canonical/PROOF-TOKEN-MATRIX.md` | Evidence pack validation |
| **EI/CTL specification** | `docs/reference/economic-intelligence-spec.md` | Tier C gating |
| Testing architecture | `.planning/testing/rules/canonical/TESTING-FRAMEWORK.md` | Workflow testing |
| Testing philosophy | `.planning/testing/rules/canonical/TESTING-PHILOSOPHY.md` | Understanding why |
| Controller reference | `.planning/testing/rules/claude-code-controller-REFERENCE.md` | Controller usage |

---

## Enforcement Checklist

Before marking ANY skill/agent/workflow work complete:

- [ ] Tested via Agent Teams (`TeamCreate` + `Task` + `SendMessage`) or `claude-code-controller` (not mock/simulation)
- [ ] Transcript captured via controller event log (minimum line count met per TRANSCRIPT-AUTH)
- [ ] Duration realistic (within DURATION-BOUNDS thresholds for operation type)
- [ ] Tool invocations visible in transcript (per TRANSCRIPT-AUTH markers)
- [ ] Session named per SESSION-NAMING convention
- [ ] Results compared to external ground truth (per GROUND-TRUTH)
- [ ] Variance present in metrics (per METRICS-REALISM)
- [ ] Limitations documented (per REPORT-INTEGRITY)
- [ ] Evidence chain complete for all findings (per EVIDENCE-CHAIN)

---

## Versioning

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-30 | Initial rules |
| 2.0 | 2026-02-04 | Added Tier C gating, infrastructure usage rules |
| 2.1 | 2026-02-04 | Updated with Auto-Invoke triggers |
| 3.0 | 2026-02-11 | **Major rewrite:** Consolidated ~25 rules into 15 categories with stable machine-readable IDs. Replaced legacy execution model with Agent Teams + claude-code-controller. Added enforcement mapping for every category. Added 5-step Mandatory Testing Pattern. Preserved all anti-fabrication substance. |

---

**These rules are MANDATORY. Violations block phase completion.**
