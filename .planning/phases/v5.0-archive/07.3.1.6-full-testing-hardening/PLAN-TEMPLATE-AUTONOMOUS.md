# Phase 07.3.1.6 Autonomous Plan Template

**Purpose:** Standard template for fully autonomous plan execution with conditional human confirmation.

---

## Core Principles

1. **All execution is autonomous** - no human involvement during plan execution
2. **Self-validation gates** - system validates pass/fail based on explicit criteria
3. **Human confirmation only at plan completion** - and only when confidence < threshold
4. **Complete context packages** - when human input needed, provide everything to decide

---

## Template Structure

```yaml
---
phase: 07.3.1.6-full-testing-hardening
plan: "{NN}"
type: execute
wave: {N}
depends_on: ["{prior_plans}"]

# Execution model - ALL plans are autonomous
execution:
  mode: autonomous
  human_confirmation: conditional  # only if confidence < threshold
  confidence_threshold: 0.95       # above this = auto-complete, below = request confirmation

# Files this plan modifies
files_modified:
  - path/to/file.md

# Validation gates - ALL must pass for plan success
validation_gates:
  # Gate 1: Transcript quality (for claude-code-agent-teams-based tasks)
  - name: transcript_quality
    applies_to: [task_ids_that_produce_transcripts]
    checks:
      - metric: line_count
        operator: ">="
        threshold: 100  # per RULES-ESSENTIAL F1
      - metric: duration_seconds
        operator: ">="
        threshold: 30   # per RULES-ESSENTIAL F3
    on_fail: mark_plan_failed

  # Gate 2: Required markers present
  - name: marker_presence
    applies_to: [task_ids_that_produce_transcripts]
    checks:
      - marker: "TaskCreate"
        required: true
      - marker: "TaskUpdate"
        required: true
      - marker: "alphaswarm"
        required: true
    on_fail: mark_plan_failed

  # Gate 3: Artifact existence
  - name: artifacts_exist
    applies_to: all
    checks:
      - path: "path/to/expected/artifact.md"
        exists: true
        contains: "required_content"
    on_fail: mark_plan_failed

  # Gate 4: Anti-fabrication (for claude-code-agent-teams tasks)
  - name: anti_fabrication
    applies_to: [task_ids_that_produce_transcripts]
    checks:
      - metric: precision
        operator: "<"
        threshold: 1.0  # perfect metrics = fabrication
      - metric: recall
        operator: "<"
        threshold: 1.0
    on_fail: mark_plan_failed

# Success criteria - what "done" means
must_haves:
  truths:
    - "Explicit testable statement 1"
    - "Explicit testable statement 2"
  artifacts:
    - path: "path/to/artifact.md"
      provides: "What this artifact proves"
      contains: "required_string"
      validation_script: "scripts/validate_X.py"  # optional

# Human confirmation context (used only if confidence < threshold)
human_confirmation_context:
  summary: "Brief description of what this plan accomplished"
  key_evidence:
    - "Evidence item 1 with path"
    - "Evidence item 2 with path"
  verification_steps:
    - "Step 1: Check X at path Y"
    - "Step 2: Verify Z shows expected output"
  expected_vs_actual:
    expected: "What should have happened"
    actual: "{{populated_at_runtime}}"
  decision_prompt: "Does the actual outcome match expected? Confirm plan completion."
---
```

---

## Task Structure (Autonomous)

```xml
<tasks>

<task id="T1" type="auto">
  <name>Task name in imperative form</name>
  <files>
    path/to/file1.md
    path/to/file2.md
  </files>
  <action>
    What to do - specific, actionable steps.
  </action>

  <!-- Autonomous validation - no human involvement -->
  <validation>
    <gate name="artifact_exists">
      <check path="path/to/output.md" exists="true" contains="required_string"/>
    </gate>
    <gate name="script_passes">
      <check command="python scripts/validate_X.py" exit_code="0"/>
    </gate>
  </validation>

  <!-- Success criteria - machine-verifiable -->
  <done_when>
    - File exists at expected path
    - Validation script returns exit code 0
    - Contains required content markers
  </done_when>
</task>

<task id="T2" type="claude-code-agent-teams">
  <name>Task requiring claude-code-agent-teams execution</name>
  <scenario>scenario_id_from_manifest</scenario>
  <files>
    .planning/testing/scenarios/SCENARIO-MANIFEST.yaml
    .vrs/testing/runs/{plan_id}-{task_id}/transcript.txt
  </files>
  <action>
    Execute scenario in claude-code-agent-teams session:
    - claude-code-controller launch "zsh"
    - claude-code-controller send "claude" --pane=X
    - claude-code-controller send "/vrs-audit contracts/" --pane=X
    - claude-code-controller wait_idle --pane=X --idle-time=15.0
    - claude-code-controller capture --pane=X --output=.vrs/testing/runs/{plan_id}-{task_id}/transcript.txt
  </action>

  <!-- Autonomous validation for claude-code-agent-teams tasks -->
  <validation>
    <gate name="transcript_quality">
      <check metric="line_count" operator=">=" threshold="100"/>
      <check metric="duration_seconds" operator=">=" threshold="30"/>
    </gate>
    <gate name="markers_present">
      <check marker="TaskCreate" required="true"/>
      <check marker="TaskUpdate" required="true"/>
      <check marker="alphaswarm" required="true"/>
    </gate>
    <gate name="evidence_pack">
      <check path=".vrs/testing/evidence/{plan_id}-{task_id}/manifest.json" exists="true"/>
      <check path=".vrs/testing/evidence/{plan_id}-{task_id}/report.json" exists="true"/>
    </gate>
    <gate name="anti_fabrication">
      <check metric="precision" operator="<" threshold="1.0"/>
      <check metric="recall" operator="<" threshold="1.0"/>
    </gate>
  </validation>

  <done_when>
    - Transcript exists with >= 100 lines
    - Duration >= 30 seconds
    - All required markers present
    - Evidence pack validates
    - Metrics show variance (not perfect)
  </done_when>
</task>

</tasks>
```

---

## Plan Completion Logic

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PLAN COMPLETION FLOW                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Execute All Tasks (Autonomous)                                      │
│  ├─ Task 1 → validation gates → pass/fail                           │
│  ├─ Task 2 → validation gates → pass/fail                           │
│  └─ Task N → validation gates → pass/fail                           │
│                                                                      │
│                         ↓                                            │
│                                                                      │
│  Aggregate Task Results                                              │
│  ├─ all_tasks_passed = (T1.pass AND T2.pass AND ... TN.pass)       │
│  └─ confidence = calculate_confidence(task_results, evidence)       │
│                                                                      │
│                         ↓                                            │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                   DECISION LOGIC                             │    │
│  ├─────────────────────────────────────────────────────────────┤    │
│  │                                                              │    │
│  │  IF any task failed:                                         │    │
│  │      → status = FAILED                                       │    │
│  │      → log failure details                                   │    │
│  │      → DO NOT request human confirmation                     │    │
│  │      → queue for autonomous retry or escalate                │    │
│  │                                                              │    │
│  │  ELSE IF all_tasks_passed AND confidence >= 0.95:            │    │
│  │      → status = COMPLETE                                     │    │
│  │      → NO human confirmation needed                          │    │
│  │      → log success with evidence paths                       │    │
│  │                                                              │    │
│  │  ELSE IF all_tasks_passed AND confidence < 0.95:             │    │
│  │      → status = PENDING_CONFIRMATION                         │    │
│  │      → generate human_confirmation_package                   │    │
│  │      → await human decision: confirm/reject                  │    │
│  │      → IF confirmed: status = COMPLETE                       │    │
│  │      → IF rejected: status = FAILED, queue for retry         │    │
│  │                                                              │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Human Confirmation Package Format

When (and only when) human confirmation is needed:

```yaml
human_confirmation_package:
  plan_id: "07.3.1.6-02"
  plan_name: "Evidence Standardization + B1 Install Validation"
  timestamp: "2026-02-03T14:32:00Z"
  confidence: 0.87
  reason_for_confirmation: "First-time workflow execution, baseline establishment"

  scenario:
    id: "b1-install"
    description: "Installation and first-run validation"

  workflow:
    name: "/vrs-audit"
    target: "tests/fixtures/foundry-vault/"

  evidence_location:
    transcript: ".vrs/testing/runs/02-T3-b1-install/transcript.txt"
    evidence_pack: ".vrs/testing/evidence/02-T3/"
    report: ".vrs/testing/evidence/02-T3/report.json"

  verification_checklist:
    - check: "Transcript has >= 100 lines"
      result: "PASS (127 lines)"
    - check: "Duration >= 30 seconds"
      result: "PASS (45s)"
    - check: "TaskCreate marker present"
      result: "PASS (line 23)"
    - check: "TaskUpdate marker present"
      result: "PASS (line 89)"
    - check: "Evidence pack validates"
      result: "PASS"

  expected_outcome: |
    - alphaswarm init completes without errors
    - alphaswarm health-check shows all tools available
    - Evidence pack contains report.json, environment.json
    - Transcript shows ALPHASWARM-START and ALPHASWARM-END markers

  actual_outcome: |
    - alphaswarm init completed in 12s
    - health-check passed (slither: ok, aderyn: ok, mythril: ok)
    - Evidence pack valid: manifest.json, report.json, environment.json present
    - Transcript markers: ALPHASWARM-START (line 1), ALPHASWARM-END (line 127)

  decision_required: |
    Does the actual outcome match the expected outcome?

    [ ] CONFIRM - Plan completed successfully
    [ ] REJECT - Plan needs revision (provide reason)
```

---

## Confidence Calculation

```python
def calculate_confidence(task_results, evidence):
    """
    Calculate confidence score for plan completion.
    Returns value between 0.0 and 1.0.
    """
    base_confidence = 1.0

    # Reduce confidence for first-time executions
    if is_first_execution(plan_id):
        base_confidence -= 0.10

    # Reduce confidence for edge cases
    if has_negative_test_cases(task_results):
        base_confidence -= 0.05

    # Reduce confidence if metrics are at boundary
    for task in task_results:
        if task.line_count < 150:  # close to 100 threshold
            base_confidence -= 0.02
        if task.duration < 45:  # close to 30s threshold
            base_confidence -= 0.02

    # Reduce confidence if any warnings (but not failures)
    warnings = count_warnings(task_results)
    base_confidence -= (warnings * 0.03)

    # Boost confidence for strong evidence
    if all_markers_present(evidence):
        base_confidence += 0.05
    if evidence_pack_validates(evidence):
        base_confidence += 0.05

    return max(0.0, min(1.0, base_confidence))
```

---

## Migration from Old Format

| Old Field | New Field | Notes |
|-----------|-----------|-------|
| `autonomous: true` | `execution.mode: autonomous` | All plans are now autonomous |
| `autonomous: false` | `execution.mode: autonomous` | Remove this distinction |
| "Human validation requested" | `execution.human_confirmation: conditional` | Only at plan end |
| `<verify>` (manual) | `<validation><gate>` | Machine-verifiable gates |
| "Request human review" | Remove | Automatic based on confidence |

---

## Example Transformed Plan Header

```yaml
---
phase: 07.3.1.6-full-testing-hardening
plan: "02"
type: execute
wave: 1
depends_on: ["01"]

execution:
  mode: autonomous
  human_confirmation: conditional
  confidence_threshold: 0.95

files_modified:
  - .planning/testing/guides/guide-evidence.md
  - .planning/testing/templates/evidence-checklist.md
  # ... etc

validation_gates:
  - name: transcript_quality
    applies_to: ["T3"]
    checks:
      - metric: line_count
        operator: ">="
        threshold: 100
      - metric: duration_seconds
        operator: ">="
        threshold: 30
    on_fail: mark_plan_failed

  - name: marker_presence
    applies_to: ["T3"]
    checks:
      - marker: "TaskCreate"
        required: true
      - marker: "alphaswarm"
        required: true
    on_fail: mark_plan_failed

  - name: artifacts_exist
    applies_to: ["T1", "T2", "T3"]
    checks:
      - path: ".planning/testing/guides/guide-evidence.md"
        exists: true
        contains: "ALPHASWARM-START"
      - path: ".planning/testing/templates/evidence-pack-example/validator-output.json"
        exists: true
    on_fail: mark_plan_failed

must_haves:
  truths:
    - "Evidence packs include transcript headers and boundary markers"
    - "Evidence checklist, example pack, and validator output are defined"
    - "Iteration protocol defines failure taxonomy and timeout budgets"
    - "Install/init/help/health-check are validated in live claude-code-agent-teams sessions"
  artifacts:
    - path: ".planning/testing/guides/guide-evidence.md"
      provides: "Evidence pack and transcript header rules"
      contains: "ALPHASWARM-START"
      validation_script: null
    - path: ".planning/testing/templates/evidence-pack-example/validator-output.json"
      provides: "Evidence pack validator output"
      contains: "status"
      validation_script: "scripts/validate_evidence_pack.py"

human_confirmation_context:
  summary: "Evidence standardization complete and B1 install validated"
  key_evidence:
    - "Evidence checklist: .planning/testing/templates/evidence-checklist.md"
    - "Install transcript: .vrs/testing/runs/02-T3-b1-install/transcript.txt"
  verification_steps:
    - "Confirm evidence pack example validates cleanly"
    - "Confirm B1 transcript has >= 100 lines, >= 30s duration"
    - "Confirm TaskCreate/TaskUpdate markers present"
  expected_vs_actual:
    expected: "Evidence framework defined, B1 install passes all gates"
    actual: "{{populated_at_runtime}}"
  decision_prompt: "Does evidence framework meet requirements? Confirm plan completion."
---
```
