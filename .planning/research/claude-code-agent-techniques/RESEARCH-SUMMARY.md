# Claude Code Agent Techniques — Research Summary

**Purpose:** Consolidate modern, *applicable* agent techniques and conventions for Claude Code workflows.
**Scope:** Claude Code orchestration primitives (subagents, teammates, skills, hooks, task management) and prompt patterns relevant to AlphaSwarm. See `CLAUDE-CODE-PRIMITIVES.md` for canonical terminology.

---

## Sources (Primary)

**Claude Code / Anthropic docs** (official):
- Hooks, settings, subagents (Task tool children), teammates (Agent Teams peers), output styles, skill authoring best practices.

**Research papers (primary):**
- ReAct (reasoning + acting)
- Tree of Thoughts (deliberation tree)
- Plan‑and‑Solve (plan before execution)
- Reflexion (self‑critique + memory)
- Chain‑of‑Thought / Self‑Consistency

---

## Applicable Conventions (Claude Code)

### 1. Subagents and Teammates as Context Isolators

**Convention:** Use subagents (Task tool children) to isolate large outputs, and teammates (Agent Teams peers) for collaborative work with DMs.

**Implication for AlphaSwarm:**
- For debate: spawn attacker/defender/verifier as **teammates** (Agent Teams) with DMs and shared tasks.
- For isolated work: spawn as **subagents** (Task tool) for heavy graph queries or tool runs to preserve main context.
- Key distinction: teammates communicate peer-to-peer; subagents only report to parent.

### 2. Hooks as Deterministic Gates

**Convention:** Hooks can block tool use or completion using exit code 2 and can inject or validate context before/after actions.

**Implication:**
- Implement preflight gates (settings/tools/graph/context) via hooks.
- Enforce TaskCreate/TaskUpdate before Stop.
- Log evidence markers in PostToolUse.

### 3. Output Styles for Structured Results

**Convention:** Output styles can enforce structured formats and reduce ambiguity.

**Implication:**
- Standardize audit outputs and task summaries with structured output styles.

### 4. Skill Authoring Best Practices (`.claude/skills/`, NOT `.claude/commands/`)

**Convention:** Skill frontmatter descriptions should include triggers and be concise; keep SKILL.md small and move detail to references. Note: "commands" (`.claude/commands/`) is the legacy directory name; current Claude Code uses "skills" (`.claude/skills/`).

**Implication:**
- Enforce skill reviews with the Skill Reviewer gate (already required).

---

## Research‑Backed Techniques To Adopt (Where It Makes Sense)

### A. Plan‑Then‑Execute (Plan‑and‑Solve)

**Pattern:** Separate planning from execution, then follow the plan.

**AlphaSwarm use:**
- Audit entrypoint creates a plan (tasks) before running tools.
- TaskCreate records the plan explicitly.

### B. Reasoning + Acting Loops (ReAct)

**Pattern:** Interleave reasoning steps with external tool use, recording evidence.

**AlphaSwarm use:**
- Require graph queries before conclusions.
- Force tool calls to be referenced in evidence packets.

### C. Reflection / Verification Passes (Reflexion)

**Pattern:** Explicit self‑critique after a step, then adjust.

**AlphaSwarm use:**
- Verifier (teammate in debate, or subagent in solo mode) runs a critique pass before accepting findings.
- Stop hook blocks until critique is present.

### D. Tree‑of‑Thoughts for High‑Risk Logic

**Pattern:** Explore multiple reasoning branches before final decision.

**AlphaSwarm use:**
- For ambiguous findings, use multiple candidate hypotheses.
- Assign attacker/defender to competing branches (teammates if debate, subagents if isolated).

### E. Self‑Consistency for Determinism Checks

**Pattern:** Repeat reasoning to detect unstable conclusions.

**AlphaSwarm use:**
- Re‑run high‑impact checks to validate stability.

---

## Primitive Selection Guide

| Task | Use | Why |
|------|-----|-----|
| Adversarial debate (attacker vs defender) | **Agent Teams (teammates)** | Needs peer DMs and shared tasks |
| Isolated graph query or research | **Subagent (Task tool)** | No peer comms needed, lower cost |
| Defining an audit workflow | **Skill** (`.claude/skills/`) | Reusable instruction set, user-invocable |
| Blocking unsafe code reads | **Hook** (`.claude/hooks/`) | Deterministic enforcement, automatic |
| Defining attacker/defender role | **Agent definition** (`.claude/agents/`) | Reusable identity for teammate or subagent |

> For full taxonomy: see `.planning/research/CLAUDE-CODE-PRIMITIVES.md`

---

## Where These Fit In AlphaSwarm

| Technique | Applies To | Implementation Surface |
|---|---|---|
| Plan‑then‑execute | Audit entrypoint | TaskCreate/TaskUpdate lifecycle |
| ReAct | Graph & tools | Enforce evidence before conclusions |
| Reflexion | Verification | vrs‑verifier (teammate or subagent) |
| Tree‑of‑Thoughts | Ambiguous cases | Multi‑agent branching (teammates or subagents) |
| Self‑consistency | Regression checks | Repeat probes in testing harness |

---

## Non‑Goals (Avoid Overuse)

- Do not apply heavy deliberation to every step; reserve for ambiguous/high‑impact cases.
- Avoid meta‑prompting when a normal workflow can enforce structure.
- Do not spawn subagents if a task is trivial or sensitive to latency.

---

## Recommended Documentation Updates

These belong in product docs and workflow contracts:

- Add a reference doc on **Claude Code Orchestration Patterns** (hooks + tasks + subagents + teammates).
- Expand `docs/workflows/workflow-tasks.md` with Task lifecycle and enforcement requirements.
- Expand `docs/workflows/workflow-progress.md` with status line guidance.
- Add hook‑based validation to `docs/reference/testing-framework.md`.

---

## Implementation Roadmap (Phase 07.3.1.6)

1. Define hook‑based gates for audit preflight and completion.
2. Update workflow docs to reflect Task lifecycle and progress reporting.
3. Add validator subagent checks for evidence completeness.
4. Update testing scenarios to include these gates.

