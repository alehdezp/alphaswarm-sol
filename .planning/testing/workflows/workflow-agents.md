# Workflow Sub-Agent Testing

**Purpose:** Validate that sub-agents spawn, route, and respond correctly.

## When To Use

- Any change to agent catalog or delegation logic.

## Preconditions

- claude-code-controller installed.
- Agents inventory from ` src/alphaswarm_sol/agents/catalog.yaml `.
- Agents installed under `.claude/agents/vrs-*`.

## Steps

1. Run an agent-focused workflow that delegates to attacker, defender, and verifier.
2. Confirm each agent speaks in transcript with expected markers.
3. Capture evidence packs for each run.

## claude-code-controller Commands

```bash
claude-code-controller launch "zsh"
claude-code-controller send "cd /path/to/project" --pane=X
claude-code-controller wait_idle --pane=X
claude-code-controller send "claude" --pane=X
claude-code-controller wait_idle --pane=X --idle-time=10.0 --timeout=30
claude-code-controller send "/vrs-workflow-test /vrs-audit contracts/ --criteria agent" --pane=X
claude-code-controller wait_idle --pane=X --idle-time=20.0 --timeout=300
claude-code-controller capture --pane=X --output=.vrs/testing/runs/<run_id>/transcript.txt
claude-code-controller send "/exit" --pane=X
claude-code-controller kill --pane=X
```

## Required Evidence

- Transcript with attacker, defender, verifier turns.
- Report with duration and mode=live.

## Reasoning-Based Evaluation (Phase 3.1c)

**Agent behavioral tests live in Phase 3.1c (plan 3.1c-10), not Phase 3.1b.** This is because agents must be evaluated with the full evaluation pipeline (capability contracts + reasoning evaluation + debrief + graph value scoring), not just mechanical liveness checks. Binary pass/fail testing cannot assess whether an agent's reasoning was sound, whether its graph queries were genuine or performative, or whether its conclusions were well-supported by evidence.

When the reasoning evaluation framework is active, agent workflows are additionally evaluated by:

### Evaluation Contract

Each agent (attacker, defender, verifier, secure-reviewer) has an evaluation contract (defined in plan 3.1c-06) at `tests/workflow_harness/contracts/workflows/vrs-{agent}.yaml` that defines:
- Required evaluation hooks: PreToolUse, PostToolUse, Stop
- Scored dimensions: graph_utilization, reasoning_depth, evidence_grounding, role_compliance, novel_insight
- Minimum scores per dimension
- Debrief mode: blocking (agent must answer debrief questions before shutdown)

### Interactive Debrief Protocol

After investigation, each agent receives debrief questions:
1. GRAPH REASONING: Which graph queries were most useful?
2. TOOL CHOICES: Why did you choose the tools you used?
3. SCOPE: Did your analysis stay within the targeted scope?
4. CONFIDENCE: What is your honest confidence in your conclusions?
5. GAPS: What did you wish you had but didn't?
6. INSTRUCTIONS: Were instructions clear? What was missing?

Debrief responses are parsed from the agent's transcript and fed to the LLM evaluator.

### Graph Value Score

Investigation agents are scored on whether graph queries actually informed analysis:
- `utilization_ratio`: queries referenced / total queries
- `impact_ratio`: queries leading to findings / total queries
- `waste_ratio`: queries ignored / total queries
- Checkbox detection: generic/template queries without customization are flagged

### Improvement Loop

When evaluation identifies weaknesses:
1. Copy production agent .md to sandbox
2. Modify copy with improvement suggestion
3. Re-run same scenario
4. Compare scores (detect regression)
5. Report to human for production update decision

## Failure Diagnosis

- Missing agent markers indicates spawn or routing failure.
- Single-agent output indicates delegation failure.
