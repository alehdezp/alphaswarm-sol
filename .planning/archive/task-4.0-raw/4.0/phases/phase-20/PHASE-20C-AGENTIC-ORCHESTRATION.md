# Phase 20.C: Agentic Orchestration Trials (Claude Code)

**Goal:** Prove Claude Code agents can reliably orchestrate BSKG tools, execute tasks, and review results without human babysitting.

---

## C.1 Core Questions

- Can the agent select the correct tool and command?
- Can it interpret output and detect tool failures?
- Can it map findings to categories/subcategories correctly?
- Can it self-correct when a run fails?
- Can it identify missing information and request re-crawl?

---

## C.2 Required Scenarios (Must Pass)

1. **Single vuln test**: agent builds KG, queries for one vuln, produces detection guidance.
2. **Multi-vuln audit**: agent processes a contract set and returns a ranked list.
3. **False positive filter**: agent runs a safe corpus and reports zero false positives.
4. **Missing context**: agent notices missing VulnDocs fields and flags for re-crawl.
5. **Ambiguous request**: agent clarifies scope before running.
6. **Error recovery**: agent detects command failure and retries with corrected input.
7. **Blind repo audit**: agent receives only repo + scope (no vuln hints) and produces findings.
8. **Scoped category audit**: agent receives category-level hints only (no vuln names or functions).
9. **Ground-truth isolation**: agent confirms no access to reports/ground truth and flags leakage risk.

---

## C.3 Claude Code Runbook

**Agent setup**
- Model: claude-haiku-4-5 for subagents; orchestrator model as configured.
- Skills available: `/vuln-build`, `/vuln-crawl`, `/vuln-process`, `/vuln-merge`, `/vuln-link`.

**Run sequence**
1. Confirm scope, corpus selection, and blinding status.
2. Build KG for target protocol.
3. Query for candidates and patterns based on graph signals (no ground-truth prompts).
4. Summarize detection, evidence, and remediation.
5. Record outcomes in the scorecard.

**PHILOSOPHY alignment**
- Evidence packets must include semantic operations and signatures.
- Findings should be tracked as beads with explicit verdicts.
- Use attacker/defender/verifier roles for complex cases.
- Document any Claude Code assumptions that reduce vendor-neutrality.

**Agent logging**
- Tool selection rationale
- Command and output summary
- Failure detection and recovery steps
- Blindness confirmation and scope hint level
- Leakage check (pass|fail)
- Orchestration trace written to `ORCHESTRATION_TRACE.md`

---

## C.3b Offline Subagent Template (Required)

All offline subagent runs must follow:
`task/4.0/phases/phase-20/SUBAGENT_SECURITY_ASSESSMENT_TEMPLATE.md`

This template enforces VKG-only reasoning, evidence-first reporting,
and strict context budgets.

---

## C.3c Real-Time Logic/Auth Pack (Required)

For time-boxed logic/auth assessments, use:
`task/4.0/phases/phase-20/REALTIME_LOGIC_AUTH_TEST_PACK.md`

This pack enforces strict timing, offline snapshots, and structured
output for complex business-logic flaws.

---

## C.4 Evaluation Rubric

| Metric | Target |
|--------|--------|
| Correct tool selection | 95%+ |
| Correct subcategory mapping | 90%+ |
| Recovery after failure | 80%+ |
| Minimal context usage | <= 3,000 tokens |
| Human intervention needed | < 10% of runs |
| Evidence packet completeness | 90%+ |
| Bead verdict coverage | 95%+ |

---

## C.5 Agent Scorecard Template

Store in `task/4.0/phases/phase-20/artifacts/AGENT_SCORECARDS.md`:

```
- run_id: A-001
  scenario: single-vuln
  tools_used: [build-kg, query]
  success: true|false
  notes: <what worked>
  failures: <what broke>
  recovery: <how it fixed it>
  missing_capabilities: <gaps>
```

---

## C.6 Failure Taxonomy

- **Tool failure**: command error, crash, timeout
- **Reasoning failure**: wrong tool, wrong scope, wrong mapping
- **Context failure**: missing VulnDocs fields, missing sources
- **Output failure**: poor explanation, wrong remediation

Every failure must include root cause and mitigation.

---

## C.6b Multi-Agent Role Protocol

For complex or ambiguous findings, run a three-role pass:

- **Attacker role**: demonstrate exploit path and required conditions.
- **Defender role**: argue why the issue is mitigated or non-exploitable.
- **Verifier role**: arbitrate using evidence packets and behavioral signatures.

Record role outputs in `AGENT_SCORECARDS.md` and reference bead IDs in `BEAD_LOG.md`.

---

## C.7 Deterministic Run Checklist (Claude Code)

- [ ] Start a fresh Claude Code session for each run.
- [ ] Record model and tool list at session start.
- [ ] Use the same seed prompt template (no ad-hoc variations).
- [ ] Pin the corpus and scope in the prompt.
- [ ] Ensure `.git` has been removed from the target repo (offline snapshot).
- [ ] Log every tool call with parameters and outputs.
- [ ] If a tool fails, retry once with explicit correction; otherwise stop.
- [ ] Summarize findings with evidence links and behavior-first signals.

---

## C.8 Claude Code Run Script Template

Use this exact run script for every orchestration trial:

```
RUN_ID: <A-###>
GOAL: <single-vuln|multi-vuln|false-positive|missing-context|ambiguous|recovery|blind|scoped>
SCOPE: <protocol name + contract list>
CORPUS: <manifest reference>
BLIND_MODE: <true|false>
SCOPE_HINT_LEVEL: <none|category|module>
GROUND_TRUTH_VISIBLE: <false>
TOOLS_ALLOWED: build-kg, query, vuln-build, vuln-crawl, vuln-process, vuln-merge, vuln-link
OUTPUTS: task/4.0/phases/phase-20/artifacts/AGENT_SCORECARDS.md

INSTRUCTIONS:
1) Confirm scope, corpus reference, and blinding status.
2) Execute build and query commands exactly once (retry only on failure).
3) Run blind pass first; run scoped pass only if hints are provided.
4) Report evidence: graph signals, semantic operations, behavioral signatures.
5) Log missing fields or missing sources.
6) Record evidence packet IDs and bead IDs.
7) Produce final verdict and remediation summary.
```
