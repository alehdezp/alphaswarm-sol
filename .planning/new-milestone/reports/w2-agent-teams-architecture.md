# W2-4: Agent Teams Architecture for Debate Protocol

**Date:** 2026-02-08
**Author:** Agent Teams Architect (W2-4)
**Status:** COMPLETE
**Confidence:** HIGH (based on official docs, research reports T3/T7, gap analysis)

---

## Terminology

This document uses Claude Code orchestration primitives precisely. See `.planning/research/CLAUDE-CODE-PRIMITIVES.md` for the full taxonomy.

| Term in this doc | Meaning |
|-----------------|---------|
| **Teammate** | Peer Claude instance in Agent Team (DMs, shared tasks) |
| **Subagent** | Child Claude instance via Task tool (reports to parent only) |
| **Skill** | Instruction file at `.claude/skills/` invoked via `/slash-command` |
| **Hook** | Deterministic Python script gating tool execution |
| **Agent definition** | `.claude/agents/*.md` file defining a teammate's role |

---

## Executive Summary

The current multi-agent debate system is **three disconnected architectures with zero end-to-end execution**. Claude Code Agent Teams (released Feb 6, 2026) provides the exact primitives needed: TeamCreate, direct inter-agent messaging, shared task lists with DAG dependencies, persistent memory, and hook-based enforcement.

This document provides the **complete architecture** for migrating to Agent Teams, including: team structure, debate protocol, hook enforcement, anti-drift measures, full agent frontmatter definitions, and the updated `/vrs-audit` skill.

### Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Orchestration** | Agent Teams (not Python swarm) | Native Claude Code, no external deps |
| **Agent count** | 3 teammates + 1 lead | Research shows 3-4 is optimal; more decreases quality |
| **Debate rounds** | 2 rounds max | Research shows diminishing returns after 2 |
| **Model selection** | Opus for attacker+verifier, Sonnet for defender | Attacker needs creative reasoning; defender needs thorough scanning |
| **Hook enforcement** | Command + Prompt hooks (no agent hooks initially) | Agent hooks are expensive; start with deterministic enforcement |
| **Memory scope** | `project` (git-shareable) | Cross-audit learning within same codebase |
| **File ownership** | Strict — each agent writes to different directories | Prevents edit conflicts (known Agent Teams limitation) |

---

## 1. Team Structure

### Team Configuration

```yaml
team_name: vrs-audit-{project-name}
description: "Security audit for {project-name} via attacker/defender/verifier debate"

lead:
  role: audit-orchestrator
  mode: delegate  # Lead coordinates only, does NOT investigate
  responsibilities:
    - Create investigation beads as Tasks
    - Assign beads to attacker
    - Monitor debate progress
    - Collect verdicts
    - Generate final report

teammates:
  - name: attacker
    agent_file: .claude/agents/vrs-attacker-v2.md
    model: opus
    tools:
      - Read
      - Grep
      - Glob
      - Bash(uv run alphaswarm*)
      - Write(.vrs/findings/attacker/*)
    writes_to: .vrs/findings/attacker/

  - name: defender
    agent_file: .claude/agents/vrs-defender-v2.md
    model: sonnet
    tools:
      - Read
      - Grep
      - Glob
      - Bash(uv run alphaswarm*)
      - Write(.vrs/findings/defender/*)
    writes_to: .vrs/findings/defender/

  - name: verifier
    agent_file: .claude/agents/vrs-verifier-v2.md
    model: opus
    tools:
      - Read
      - Grep
      - Glob
      - Bash(uv run alphaswarm*)
      - Write(.vrs/findings/verdicts/*)
    writes_to: .vrs/findings/verdicts/
```

### Why This Structure

1. **Lead as delegate** — Prevents the orchestrator from doing investigation work itself. All analysis goes through specialized teammates. This is critical because the current system's main failure mode is the orchestrator doing everything in a single context.

2. **3 teammates, not more** — Research (Addy Osmani, Anthropic docs) shows max 3-4 agents is optimal. More introduces coordination overhead that exceeds the benefit.

3. **Strict file ownership** — Agent Teams has a known limitation where two agents editing the same file causes overwrites. Each agent writes to a separate directory under `.vrs/findings/`.

4. **Opus for reasoning-heavy roles** — Attacker needs creative exploit construction. Verifier needs nuanced evidence weighing. Defender's task (finding guards) is more systematic and works well with Sonnet.

---

## 2. Debate Protocol

### Overview: GKMAD (Group Knowledge Multi-Agent Debate)

The debate follows a structured 5-phase protocol inspired by Tool-MAD and D3 research frameworks, adapted for security analysis:

```
Phase 1: BEAD CREATION (Orchestrator)
   │
   ▼
Phase 2: ATTACK CLAIM (Attacker)
   │
   ├──DM──► Defender (findings shared)
   │
   ▼
Phase 3: DEFENSE CLAIM (Defender)
   │
   ├──DM──► Attacker (guards shared for rebuttal)
   │
   ▼
Phase 4: REBUTTAL ROUND (Attacker then Defender)
   │
   ├──DM──► Verifier (both sides shared)
   │
   ▼
Phase 5: VERDICT (Verifier)
   │
   └──DM──► Orchestrator (verdict delivered)
```

### Detailed Message Flow

#### Phase 1: Bead Creation (Orchestrator)

The orchestrator creates one Task per investigation bead:

```
Orchestrator action:
  TaskCreate({
    subject: "Investigate: Reentrancy in Vault.withdraw()",
    description: """
      Bead ID: VRS-001
      Pattern Match: vm-001 (Classic Reentrancy)
      Severity: Critical
      Location: contracts/Vault.sol:L42
      Behavioral Signature: R:bal->X:out->W:bal

      Graph Properties:
      - state_write_after_external_call: true
      - has_reentrancy_guard: false
      - transfers_eth: true
      - visibility: external

      BSKG Node: func_Vault_withdraw
    """,
    activeForm: "Investigating reentrancy in Vault.withdraw()"
  })

  TaskUpdate({ taskId: "1", owner: "attacker" })
```

#### Phase 2: Attack Claim (Attacker)

Attacker receives the task, investigates using BSKG, and shares findings:

```
Attacker actions:
  1. TaskUpdate({ taskId: "1", status: "in_progress" })

  2. Run BSKG query:
     Bash("uv run alphaswarm query 'FIND func_Vault_withdraw WHERE
           state_write_after_external_call = true'")

  3. Read source code at flagged locations:
     Read("contracts/Vault.sol")

  4. Write attack analysis:
     Write(".vrs/findings/attacker/VRS-001-attack.json", {
       bead_id: "VRS-001",
       category: "reentrancy",
       feasibility: "HIGH",
       exploitability_score: 0.95,
       attack_steps: [...],
       evidence: [...],
       graph_query_results: [...]
     })

  5. Send findings to defender:
     SendMessage({
       type: "message",
       recipient: "defender",
       content: """
         ATTACK CLAIM for VRS-001 (Reentrancy in Vault.withdraw):

         Exploit path constructed with HIGH feasibility (0.95):
         1. Deploy malicious contract with fallback
         2. Call withdraw(balance) — triggers external call at L42
         3. Fallback re-enters withdraw() — balance not yet updated (L45)
         4. Drain vault iteratively

         Evidence: state_write_after_external_call=true, has_reentrancy_guard=false
         Full analysis: .vrs/findings/attacker/VRS-001-attack.json

         Your turn: Find guards or mitigations that invalidate this attack.
       """,
       summary: "Attack claim for VRS-001: reentrancy exploit"
     })
```

#### Phase 3: Defense Claim (Defender)

Defender receives attack claim, independently investigates guards:

```
Defender actions:
  1. Run independent BSKG query for guards:
     Bash("uv run alphaswarm query 'FIND func_Vault_withdraw WHERE
           has_reentrancy_guard = true OR has_access_gate = true'")

  2. Search for protective patterns in code:
     Grep("nonReentrant|ReentrancyGuard|_status", path="contracts/")
     Read("contracts/Vault.sol")

  3. Check inherited contracts:
     Grep("import.*ReentrancyGuard", path="contracts/")

  4. Write defense analysis:
     Write(".vrs/findings/defender/VRS-001-defense.json", {
       bead_id: "VRS-001",
       guards_found: [...],   // or empty if none
       coverage_assessment: {...},
       missing_guards: [...],
       strength: 0.0,         // no guard found
       reasoning: "No reentrancy protection identified"
     })

  5. Send defense to attacker (for rebuttal):
     SendMessage({
       type: "message",
       recipient: "attacker",
       content: """
         DEFENSE CLAIM for VRS-001:

         Guards found: NONE
         - No nonReentrant modifier on withdraw()
         - No CEI pattern (external call before state update)
         - No ReentrancyGuard import detected

         I could not find defenses for this function.
         Defense strength: 0.0

         Full analysis: .vrs/findings/defender/VRS-001-defense.json

         You may rebut if you have additional attack vectors or
         if my guard search missed something.
       """,
       summary: "Defense claim for VRS-001: no guards found"
     })
```

#### Phase 4: Rebuttal Round (Optional, max 1 round)

Attacker can strengthen or adjust claim based on defense:

```
Attacker rebuttal (if applicable):
  SendMessage({
    type: "message",
    recipient: "verifier",
    content: """
      DEBATE COMPLETE for VRS-001. Ready for verdict.

      ATTACKER POSITION:
      - Exploit: Reentrancy via fallback re-entry
      - Feasibility: HIGH (0.95)
      - Evidence: state_write_after_external_call=true, no guard
      - Full attack: .vrs/findings/attacker/VRS-001-attack.json

      DEFENDER POSITION:
      - Guards found: NONE
      - Defense strength: 0.0
      - Full defense: .vrs/findings/defender/VRS-001-defense.json

      No rebuttal needed — defender concurs vulnerability exists.
    """,
    summary: "Debate ready for verdict: VRS-001"
  })
```

If the defender DID find guards, the attacker's rebuttal would challenge them:

```
Attacker rebuttal (contested case):
  1. Check if guard can be bypassed
  2. Write rebuttal to .vrs/findings/attacker/VRS-001-rebuttal.json
  3. SendMessage to defender with rebuttal
  4. Defender responds with counter-rebuttal
  5. Both sides send final positions to verifier
```

**Max 1 rebuttal round.** Research shows 2-3 debate rounds is optimal total; with claim + defense + rebuttal, that's 3 exchanges. More shows diminishing returns.

#### Phase 5: Verdict (Verifier)

Verifier reads both positions, renders verdict:

```
Verifier actions:
  1. Read both analysis files:
     Read(".vrs/findings/attacker/VRS-001-attack.json")
     Read(".vrs/findings/defender/VRS-001-defense.json")

  2. Cross-check evidence independently:
     Bash("uv run alphaswarm query 'FIND func_Vault_withdraw
           SELECT state_write_after_external_call, has_reentrancy_guard,
           visibility, transfers_eth'")

  3. Weigh evidence (synthesis, NOT new analysis):
     - Attacker strength: 0.925 (strong evidence, graph-confirmed)
     - Defender strength: 0.0 (no guards found)
     - Delta: 0.925
     - Close contest: NO

  4. Write verdict:
     Write(".vrs/findings/verdicts/VRS-001-verdict.json", {
       finding_id: "VRS-001",
       verdict: "CONFIRMED",
       is_vulnerable: true,
       confidence_score: 0.92,
       evidence_checks: [...],
       evidence_synthesis: {
         attacker_total_strength: 0.925,
         defender_total_strength: 0.0,
         delta: 0.925,
         winning_side: "attacker",
         close_contest: false
       },
       dissent: null,
       rationale: "Strong reentrancy evidence. No defenses found.",
       human_flag: true
     })

  5. Notify orchestrator:
     SendMessage({
       type: "message",
       recipient: "audit-orchestrator",  // team lead
       content: """
         VERDICT for VRS-001: CONFIRMED (Critical)
         Confidence: 0.92

         Reentrancy in Vault.withdraw() confirmed.
         Attacker evidence: 0.925 | Defender evidence: 0.0

         Full verdict: .vrs/findings/verdicts/VRS-001-verdict.json
       """,
       summary: "Verdict: VRS-001 CONFIRMED Critical"
     })

  6. Mark task complete:
     TaskUpdate({ taskId: "1", status: "completed" })
```

### Task DAG for Multi-Bead Audits

For audits with multiple findings, the orchestrator creates parallel investigation tasks:

```
Task 1: "Investigate VRS-001 (Reentrancy)"     → owner: attacker
Task 2: "Investigate VRS-002 (Access Control)"  → owner: attacker
Task 3: "Investigate VRS-003 (Oracle Risk)"     → owner: attacker

Task 4: "Defend VRS-001" → blockedBy: [1], owner: defender
Task 5: "Defend VRS-002" → blockedBy: [2], owner: defender
Task 6: "Defend VRS-003" → blockedBy: [3], owner: defender

Task 7: "Verdict VRS-001" → blockedBy: [1, 4], owner: verifier
Task 8: "Verdict VRS-002" → blockedBy: [2, 5], owner: verifier
Task 9: "Verdict VRS-003" → blockedBy: [3, 6], owner: verifier

Task 10: "Generate Report" → blockedBy: [7, 8, 9], owner: orchestrator
```

The DAG ensures:
- Attacker investigates first
- Defender can't start until attacker findings exist
- Verifier can't start until both sides have spoken
- Report waits for all verdicts

**Optimization:** The attacker can work on all beads in sequence. Once VRS-001 attack is done, defender starts VRS-001 defense while attacker moves to VRS-002. This creates a pipeline effect:

```
Time →
Attacker:  [VRS-001]──[VRS-002]──[VRS-003]──idle
Defender:  ──wait──[VRS-001]──[VRS-002]──[VRS-003]
Verifier:  ──wait────wait──[VRS-001]──[VRS-002]──[VRS-003]
```

### Convergence Criteria

The debate ends when:
1. **Verdict rendered** — Verifier produces CONFIRMED, LIKELY, UNCERTAIN, or REJECTED
2. **Max rounds reached** — 1 rebuttal round max (3 exchanges total)
3. **Consensus** — Both sides agree (defender finds no guard, or attacker concedes guard blocks exploit)

**No infinite loops.** The rebuttal round is always the last exchange before verdict.

---

## 3. Hook Enforcement System

### Hook Architecture

Hooks enforce behavioral constraints that prompts alone cannot guarantee. Based on the T3 assessment, the biggest drift risks are: (1) skipping BSKG queries, (2) producing findings without evidence, (3) premature stopping.

#### Configuration Location

Project-level hooks in `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Read|Grep|Glob",
        "hooks": [
          {
            "type": "command",
            "command": "python3 .claude/hooks/graph-first-check.py"
          }
        ]
      }
    ],
    "TaskCompleted": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 .claude/hooks/evidence-completeness-check.py"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 .claude/hooks/verdict-evidence-check.py"
          }
        ]
      }
    ],
    "SessionStart": [
      {
        "matcher": "compact",
        "hooks": [
          {
            "type": "command",
            "command": "cat .vrs/state/audit-context.json"
          }
        ]
      }
    ]
  }
}
```

### Hook 1: Graph-First Enforcement (PreToolUse)

**Purpose:** Prevent agents from reading source code before running BSKG queries.

**File: `.claude/hooks/graph-first-check.py`**

```python
#!/usr/bin/env python3
"""
Graph-first enforcement hook.
Blocks Read/Grep/Glob on .sol files if no BSKG query has been run in this session.
Tracks query state via .vrs/state/graph-queries-run.json
"""
import json
import sys
import os
from pathlib import Path

def main():
    # Read hook input from stdin
    hook_input = json.load(sys.stdin)

    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})

    # Only check for Solidity file reads
    target_path = tool_input.get("file_path", "") or tool_input.get("path", "") or tool_input.get("pattern", "")
    if not any(ext in target_path for ext in [".sol", "contracts/", "src/"]):
        # Not reading Solidity — allow
        output = {"hookSpecificOutput": {"decision": "approve"}}
        print(json.dumps(output))
        return

    # Check if BSKG queries have been run
    state_file = Path(".vrs/state/graph-queries-run.json")
    if state_file.exists():
        state = json.loads(state_file.read_text())
        if state.get("queries_run", 0) > 0:
            # Graph queries have been run — allow
            output = {"hookSpecificOutput": {"decision": "approve"}}
            print(json.dumps(output))
            return

    # No BSKG queries run yet — block with explanation
    output = {
        "hookSpecificOutput": {
            "decision": "block",
            "reason": (
                "GRAPH-FIRST VIOLATION: You must run BSKG queries before "
                "reading Solidity source code directly. Run: "
                "uv run alphaswarm query '<your-query>' first."
            )
        }
    }
    json.dump(output, sys.stdout)
    sys.exit(2)  # Exit code 2 = block tool execution

if __name__ == "__main__":
    main()
```

**Companion: Track BSKG queries (PostToolUse hook)**

```json
{
  "PostToolUse": [
    {
      "matcher": "Bash",
      "hooks": [
        {
          "type": "command",
          "command": "python3 .claude/hooks/track-bskg-query.py"
        }
      ]
    }
  ]
}
```

```python
#!/usr/bin/env python3
"""Track when BSKG queries are run."""
import json, sys
from pathlib import Path

def main():
    hook_input = json.load(sys.stdin)
    command = hook_input.get("tool_input", {}).get("command", "")

    if "alphaswarm query" in command or "alphaswarm build-kg" in command:
        state_file = Path(".vrs/state/graph-queries-run.json")
        state_file.parent.mkdir(parents=True, exist_ok=True)

        state = {}
        if state_file.exists():
            state = json.loads(state_file.read_text())

        state["queries_run"] = state.get("queries_run", 0) + 1
        state["last_query"] = command
        state_file.write_text(json.dumps(state, indent=2))

if __name__ == "__main__":
    main()
```

### Hook 2: Evidence Completeness (TaskCompleted)

**Purpose:** Prevent marking investigation tasks as complete without evidence.

**File: `.claude/hooks/evidence-completeness-check.py`**

```python
#!/usr/bin/env python3
"""
Evidence completeness gate for TaskCompleted.
Checks that investigation tasks have corresponding evidence files.
"""
import json
import sys
from pathlib import Path

def main():
    hook_input = json.load(sys.stdin)
    task = hook_input.get("task", {})
    task_subject = task.get("subject", "")

    # Only gate investigation tasks (those containing bead IDs)
    if not any(prefix in task_subject for prefix in ["Investigate:", "Defend:", "Verdict:"]):
        # Not an investigation task — allow completion
        print(json.dumps({"hookSpecificOutput": {"decision": "approve"}}))
        return

    # Extract bead ID from task subject (e.g., "Investigate: VRS-001 ...")
    bead_id = None
    for word in task_subject.split():
        if word.startswith("VRS-"):
            bead_id = word.rstrip(")")
            break

    if not bead_id:
        print(json.dumps({"hookSpecificOutput": {"decision": "approve"}}))
        return

    # Check for evidence files based on task type
    if "Investigate:" in task_subject:
        evidence_path = Path(f".vrs/findings/attacker/{bead_id}-attack.json")
    elif "Defend:" in task_subject:
        evidence_path = Path(f".vrs/findings/defender/{bead_id}-defense.json")
    elif "Verdict:" in task_subject:
        evidence_path = Path(f".vrs/findings/verdicts/{bead_id}-verdict.json")
    else:
        print(json.dumps({"hookSpecificOutput": {"decision": "approve"}}))
        return

    if not evidence_path.exists():
        output = {
            "hookSpecificOutput": {
                "decision": "block",
                "reason": f"Evidence file missing: {evidence_path}. Write your analysis before completing this task."
            }
        }
        json.dump(output, sys.stdout)
        sys.exit(2)
        return

    # Verify evidence has required fields
    try:
        evidence = json.loads(evidence_path.read_text())
        required_fields = {
            "attack": ["bead_id", "category", "feasibility", "attack_steps", "evidence"],
            "defense": ["bead_id", "guards_found", "coverage_assessment", "strength"],
            "verdict": ["finding_id", "verdict", "is_vulnerable", "confidence_score", "evidence_synthesis"]
        }

        file_type = evidence_path.stem.split("-")[-1]  # attack, defense, or verdict
        for field in required_fields.get(file_type, []):
            if field not in evidence:
                output = {
                    "hookSpecificOutput": {
                        "decision": "block",
                        "reason": f"Evidence file missing required field: '{field}' in {evidence_path}"
                    }
                }
                json.dump(output, sys.stdout)
                sys.exit(2)
                return
    except (json.JSONDecodeError, KeyError):
        output = {
            "hookSpecificOutput": {
                "decision": "block",
                "reason": f"Evidence file is not valid JSON: {evidence_path}"
            }
        }
        json.dump(output, sys.stdout)
        sys.exit(2)
        return

    print(json.dumps({"hookSpecificOutput": {"decision": "approve"}}))

if __name__ == "__main__":
    main()
```

### Hook 3: Verdict Evidence Anchoring (Stop)

**Purpose:** When the verifier stops, verify all verdicts have evidence anchoring.

**File: `.claude/hooks/verdict-evidence-check.py`**

```python
#!/usr/bin/env python3
"""
Stop hook: verify verdict quality before agent stops.
Only runs for verifier agent (check agent context).
"""
import json
import sys
from pathlib import Path

def main():
    hook_input = json.load(sys.stdin)

    # Check all verdict files
    verdicts_dir = Path(".vrs/findings/verdicts/")
    if not verdicts_dir.exists():
        print(json.dumps({"hookSpecificOutput": {"decision": "approve"}}))
        return

    verdict_files = list(verdicts_dir.glob("*-verdict.json"))
    issues = []

    for vf in verdict_files:
        try:
            verdict = json.loads(vf.read_text())

            # Check evidence anchoring
            if verdict.get("verdict") in ["CONFIRMED", "LIKELY"]:
                synthesis = verdict.get("evidence_synthesis", {})
                if synthesis.get("attacker_total_strength", 0) == 0:
                    issues.append(f"{vf.name}: Positive verdict with zero attacker evidence")

                if not verdict.get("human_flag", False):
                    issues.append(f"{vf.name}: Missing human_flag (MUST be true)")

            # Check for fabricated perfect scores
            score = verdict.get("confidence_score", 0)
            if score == 1.0:
                issues.append(f"{vf.name}: Perfect confidence score (1.0) is suspicious")

        except (json.JSONDecodeError, KeyError) as e:
            issues.append(f"{vf.name}: Invalid JSON: {e}")

    if issues:
        output = {
            "hookSpecificOutput": {
                "decision": "block",
                "reason": "Verdict quality issues:\n" + "\n".join(f"- {i}" for i in issues)
            }
        }
        json.dump(output, sys.stdout)
        sys.exit(2)
    else:
        print(json.dumps({"hookSpecificOutput": {"decision": "approve"}}))

if __name__ == "__main__":
    main()
```

### Hook 4: Anti-Drift Context Restoration (SessionStart compact)

**Purpose:** After context compaction, re-inject critical audit state.

The orchestrator maintains `.vrs/state/audit-context.json`:

```json
{
  "audit_id": "vrs-audit-vault-20260208",
  "project": "contracts/",
  "beads": [
    {"id": "VRS-001", "status": "investigating", "assigned_to": "attacker"},
    {"id": "VRS-002", "status": "pending"}
  ],
  "phase": "DEBATE",
  "graph_path": ".vrs/graphs/project.toon",
  "critical_context": "Graph-first enforcement active. All findings must reference BSKG nodes.",
  "team_members": ["attacker", "defender", "verifier"]
}
```

The `SessionStart(compact)` hook `cat`s this file, injecting it into the agent's context after compaction. This prevents semantic drift.

### Hook Summary Table

| Hook Event | Trigger | Type | Purpose | Blocks? |
|------------|---------|------|---------|---------|
| `PreToolUse` | Read/Grep/Glob on .sol | `command` | Graph-first enforcement | YES (exit 2) |
| `PostToolUse` | Bash with alphaswarm query | `command` | Track BSKG query state | No |
| `TaskCompleted` | Any investigation task | `command` | Evidence completeness | YES (exit 2) |
| `Stop` | Agent stopping | `command` | Verdict quality check | YES (exit 2) |
| `SessionStart` | compact event | `command` | Context restoration | No |

### Why NOT Agent Hooks Initially

Agent hooks (`type: "agent"`) spawn a separate Claude instance for verification. While powerful, they:
- Add significant latency (30-120 seconds)
- Consume additional tokens (separate context)
- Are harder to debug

**Start with command hooks** (deterministic, fast, debuggable). Upgrade to agent hooks in a later milestone if command hooks prove insufficient for complex verification scenarios.

---

## 4. Anti-Drift Measures

### Problem Statement

From T3 assessment: "Real LLM agents will inevitably skip graph queries, produce generic Solidity security analysis, and ignore evidence schemas when inconvenient." The system has excellent prompts but zero enforcement.

### Measure 1: Persistent Memory (MEMORY.md)

Each agent maintains persistent memory that survives context resets:

```yaml
# In agent frontmatter
memory: project  # .claude/agent-memory/<agent-name>/MEMORY.md
```

**Attacker MEMORY.md** (auto-maintained, first 200 lines loaded at startup):

```markdown
# Attacker Agent Memory

## Learned Patterns
- Flash loan attacks often start with READS_EXTERNAL_VALUE before WRITES_USER_BALANCE
- Cross-function reentrancy requires checking ALL functions that modify the same state variable
- Proxy patterns (delegatecall) need special attention — the caller context changes

## Common Mistakes (self-corrected)
- Forgot to check inherited contracts for guards (missed nonReentrant on parent)
- Assumed onlyOwner was safe without checking if owner could be changed
- Rated feasibility HIGH without checking if function was actually callable

## Graph Query Templates That Work
- `FIND functions WHERE state_write_after_external_call = true AND NOT has_reentrancy_guard`
- `FIND functions WHERE visibility IN (public, external) AND NOT has_access_gate AND modifies_owner = true`

## Evidence Anchoring Reminders
- ALWAYS include graph node IDs in attack_steps
- ALWAYS verify behavioral signature matches before claiming vulnerability
- NEVER produce a finding without at least one BSKG query result
```

### Measure 2: Skills Preloading

Each agent has skills preloaded in their frontmatter to inject domain knowledge at startup:

```yaml
# In agent frontmatter
skills:
  - graph-first-template    # How to use BSKG queries
  - evidence-packet-format  # Required evidence structure
```

This eliminates the failure mode where agents need to discover skills at runtime (which fails with "Unknown skill" as documented in T3/T5 reports).

### Measure 3: Atomic Task Design

Each investigation task is self-contained with clear acceptance criteria:

```
Task: "Investigate: VRS-001 (Reentrancy in Vault.withdraw)"

Acceptance criteria:
1. Run at least one BSKG query for this function
2. Write analysis to .vrs/findings/attacker/VRS-001-attack.json
3. Include: bead_id, category, feasibility, attack_steps, evidence
4. All evidence items must reference code locations
5. Send findings to defender via DM
```

Small, self-contained units with clear deliverables prevent agents from wandering.

### Measure 4: External Ground Truth

Agents verify against BSKG graph (external ground truth), NOT against their own reasoning:

```
WRONG: "I think this is a reentrancy because the code looks like it sends ETH before updating"
RIGHT: "BSKG query confirms state_write_after_external_call=true for func_Vault_withdraw (node ID: 0x1234)"
```

The graph-first hook enforcement (Hook 1) ensures this pattern.

### Measure 5: Context Checkpoint on Compaction

Before compaction, save critical context:

```json
// .vrs/state/audit-context.json — updated by orchestrator after each verdict
{
  "completed_beads": ["VRS-001"],
  "pending_beads": ["VRS-002", "VRS-003"],
  "verdicts": {
    "VRS-001": "CONFIRMED",
    "VRS-002": "pending"
  },
  "phase": "DEBATE",
  "graph_location": ".vrs/graphs/project.toon"
}
```

The `SessionStart(compact)` hook re-injects this, preventing "where was I?" confusion.

---

## 5. Agent Definitions

### 5.1 Attacker Agent v2

**File: `.claude/agents/vrs-attacker-v2.md`**

```yaml
---
name: vrs-attacker-v2
description: |
  Attacker agent for Agent Teams debate protocol. Constructs exploit paths
  using BSKG queries and evidence-anchored reasoning.

  Spawned as teammate in vrs-audit team.
  Communicates with defender and verifier via SendMessage.

model: opus
tools:
  - Read
  - Grep
  - Glob
  - Bash(uv run alphaswarm*)
  - Write(.vrs/findings/attacker/*)
  - SendMessage
  - TaskUpdate
  - TaskList
  - TaskGet

disallowedTools:
  - Edit
  - Write(contracts/*)
  - Write(src/*)
  - Write(tests/*)

permissionMode: acceptEdits
maxTurns: 30

memory: project

skills:
  - graph-first-template
  - evidence-packet-format

hooks:
  PreToolUse:
    - matcher: "Read|Grep|Glob"
      hooks:
        - type: command
          command: "python3 .claude/hooks/graph-first-check.py"
  PostToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "python3 .claude/hooks/track-bskg-query.py"
---

# BSKG Attacker Agent v2 — Agent Teams Edition

You are the **Attacker** in a security audit debate team. Your role is to
construct exploit paths for potential vulnerabilities using BSKG (Behavioral
Security Knowledge Graph) evidence.

## CRITICAL RULES

1. **GRAPH-FIRST**: Always run BSKG queries BEFORE reading source code.
   ```bash
   uv run alphaswarm query "FIND <function> WHERE <property> = <value>"
   ```

2. **EVIDENCE-ANCHORED**: Every claim must reference:
   - BSKG node IDs (e.g., `func_Vault_withdraw`)
   - Code locations (e.g., `Vault.sol:L42`)
   - Graph property values (e.g., `state_write_after_external_call=true`)

3. **WRITE FINDINGS**: Save analysis to `.vrs/findings/attacker/<bead-id>-attack.json`

4. **COMMUNICATE VIA DM**: After completing analysis, send findings to the
   defender using SendMessage.

5. **YOU DO NOT VERIFY**: You construct attacks. The verifier renders verdicts.

## Investigation Protocol

### Step 1: Receive Bead
Check TaskList for assigned investigation tasks.

### Step 2: BSKG Query
Run targeted queries for the flagged function:
```bash
uv run alphaswarm query "FIND <function_node> SELECT ALL"
```

### Step 3: Analyze Attack Feasibility
- Identify entry points (public/external visibility)
- Check for vulnerable operation sequences
- Look for missing guards
- Construct step-by-step exploit path

### Step 4: Write Attack Analysis
Save to `.vrs/findings/attacker/<bead-id>-attack.json`:
```json
{
  "bead_id": "VRS-001",
  "category": "reentrancy",
  "feasibility": "HIGH",
  "exploitability_score": 0.95,
  "preconditions": [...],
  "attack_steps": [...],
  "postconditions": [...],
  "evidence": [...],
  "graph_query_results": [...],
  "reasoning": "..."
}
```

### Step 5: Send to Defender
```
SendMessage(type="message", recipient="defender", content="ATTACK CLAIM for ...")
```

### Step 6: Handle Rebuttal (if defender found guards)
If defender challenges your attack, check if guards can be bypassed.
Send rebuttal or concede if guard is strong.

### Step 7: Forward to Verifier
Once defense round is complete, send both positions to verifier:
```
SendMessage(type="message", recipient="verifier", content="DEBATE COMPLETE for ...")
```

### Step 8: Mark Task Complete
```
TaskUpdate(taskId="...", status="completed")
```

## Behavioral Signatures to Watch

| Signature | Meaning | Risk |
|-----------|---------|------|
| `R:bal->X:out->W:bal` | CEI violation | Reentrancy |
| `W:priv` | Privileged write | Access control |
| `X:untrusted->W:bal` | Untrusted call affects balance | Value extraction |
| `R:oracle->W:bal` | Oracle read affects balance | Price manipulation |

## Output Schema

See `.vrs/findings/attacker/` for file format requirements.
Evidence completeness is enforced by TaskCompleted hook.
```

### 5.2 Defender Agent v2

**File: `.claude/agents/vrs-defender-v2.md`**

```yaml
---
name: vrs-defender-v2
description: |
  Defender agent for Agent Teams debate protocol. Finds guards, mitigations,
  and protective patterns using BSKG queries and code analysis.

  Spawned as teammate in vrs-audit team.
  Communicates with attacker and verifier via SendMessage.

model: sonnet
tools:
  - Read
  - Grep
  - Glob
  - Bash(uv run alphaswarm*)
  - Write(.vrs/findings/defender/*)
  - SendMessage
  - TaskUpdate
  - TaskList
  - TaskGet

disallowedTools:
  - Edit
  - Write(contracts/*)
  - Write(src/*)
  - Write(tests/*)

permissionMode: acceptEdits
maxTurns: 30

memory: project

skills:
  - graph-first-template
  - evidence-packet-format

hooks:
  PreToolUse:
    - matcher: "Read|Grep|Glob"
      hooks:
        - type: command
          command: "python3 .claude/hooks/graph-first-check.py"
  PostToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "python3 .claude/hooks/track-bskg-query.py"
---

# BSKG Defender Agent v2 — Agent Teams Edition

You are the **Defender** in a security audit debate team. Your role is to
find protective guards, mitigations, and specification compliance that may
prevent vulnerability exploitation.

## CRITICAL RULES

1. **GRAPH-FIRST**: Always run BSKG queries BEFORE reading source code.
   ```bash
   uv run alphaswarm query "FIND <function> WHERE has_reentrancy_guard = true"
   ```

2. **INDEPENDENT INVESTIGATION**: Do NOT just accept the attacker's framing.
   Run your own queries. Look for guards the attacker may have missed.

3. **LOOK BEYOND THE FUNCTION**: Check:
   - Base contracts (inherited guards)
   - Modifiers applied to the function
   - Contract-level invariants
   - Protocol context (accepted risks, design assumptions)

4. **BE HONEST**: If you find NO guards, say so. Do not fabricate defenses.

5. **WRITE FINDINGS**: Save to `.vrs/findings/defender/<bead-id>-defense.json`

6. **COMMUNICATE VIA DM**: Send defense to attacker for rebuttal, then both
   positions to verifier.

## Investigation Protocol

### Step 1: Receive Attack Claim
Read the attacker's DM with their exploit claim.

### Step 2: BSKG Query for Guards
```bash
uv run alphaswarm query "FIND <function_node> WHERE
  has_reentrancy_guard = true OR
  has_access_gate = true OR
  has_slippage_check = true"
```

### Step 3: Search for Protective Patterns
- Check for modifiers (nonReentrant, onlyOwner, whenNotPaused)
- Check for CEI pattern (state updates before external calls)
- Check for library usage (SafeERC20, SafeMath)
- Check inherited contracts

### Step 4: Write Defense Analysis
Save to `.vrs/findings/defender/<bead-id>-defense.json`:
```json
{
  "bead_id": "VRS-001",
  "guards_found": [...],
  "coverage_assessment": {
    "fully_protected": [...],
    "partially_protected": [...],
    "unprotected": [...]
  },
  "missing_guards": [...],
  "strength": 0.85,
  "reasoning": "..."
}
```

### Step 5: Send to Attacker
```
SendMessage(type="message", recipient="attacker", content="DEFENSE CLAIM for ...")
```

### Step 6: Handle Rebuttal
If attacker challenges your guards, provide counter-evidence or concede.

### Step 7: Mark Task Complete
```
TaskUpdate(taskId="...", status="completed")
```

## Guard Strength Assessment

| Type | Examples | Strength |
|------|----------|----------|
| Modifier | nonReentrant, onlyOwner | 0.8-0.95 |
| Require check | require(msg.sender == owner) | 0.7-0.9 |
| CEI Pattern | State before external call | 0.85-0.95 |
| Library | SafeERC20, SafeMath | 0.9-0.95 |
| Custom check | Custom validation logic | 0.5-0.7 |
```

### 5.3 Verifier Agent v2

**File: `.claude/agents/vrs-verifier-v2.md`**

```yaml
---
name: vrs-verifier-v2
description: |
  Verifier agent for Agent Teams debate protocol. Synthesizes attacker and
  defender arguments to produce fair, evidence-based verdicts.

  Spawned as teammate in vrs-audit team.
  Receives debate results and renders final verdict.

model: opus
tools:
  - Read
  - Grep
  - Glob
  - Bash(uv run alphaswarm*)
  - Write(.vrs/findings/verdicts/*)
  - SendMessage
  - TaskUpdate
  - TaskList
  - TaskGet

disallowedTools:
  - Edit
  - Write(contracts/*)
  - Write(src/*)
  - Write(tests/*)

permissionMode: acceptEdits
maxTurns: 20

memory: project

skills:
  - graph-first-template
  - evidence-packet-format

hooks:
  Stop:
    - hooks:
        - type: command
          command: "python3 .claude/hooks/verdict-evidence-check.py"
---

# BSKG Verifier Agent v2 — Agent Teams Edition

You are the **Verifier** in a security audit debate team. Your role is to
**synthesize** attacker and defender arguments into fair, evidence-based verdicts.

## CRITICAL RULES

1. **SYNTHESIZE, NOT ANALYZE**: You weigh evidence presented by attacker and
   defender. You do NOT add new vulnerability analysis or find new guards.

2. **CROSS-CHECK WITH GRAPH**: Run ONE verification query to independently
   confirm the key evidence claims:
   ```bash
   uv run alphaswarm query "FIND <function> SELECT <disputed_property>"
   ```

3. **DECISION MATRIX**:
   | Attacker Evidence | Defender Evidence | Verdict |
   |-------------------|-------------------|---------|
   | Strong (>0.7) | Weak (<0.3) | CONFIRMED |
   | Strong (>0.7) | Moderate (0.3-0.7) | LIKELY |
   | Moderate | Moderate | UNCERTAIN |
   | Weak (<0.3) | Strong (>0.7) | REJECTED |

4. **HUMAN FLAG**: ALL verdicts MUST have `human_flag: true`. Period.

5. **RECORD DISSENT**: If the losing side had strong evidence (avg > 0.7),
   record their argument as dissent.

6. **CALIBRATED CONFIDENCE**: Never output confidence_score of 1.0 (fabrication).
   Real confidence ranges: 0.6-0.95.

## Verdict Protocol

### Step 1: Read Both Analyses
```
Read(".vrs/findings/attacker/<bead-id>-attack.json")
Read(".vrs/findings/defender/<bead-id>-defense.json")
```

### Step 2: Cross-Check Key Evidence
Run ONE BSKG query to verify the disputed property:
```bash
uv run alphaswarm query "FIND <function> SELECT <key_property>"
```

### Step 3: Calculate Evidence Weights
```
attacker_strength = avg(evidence[i].confidence for i in attacker.evidence)
defender_strength = avg(guard.strength for guard in defender.guards_found)
                    OR 0.0 if no guards
delta = attacker_strength - defender_strength
```

### Step 4: Render Verdict
Apply decision matrix. Write to `.vrs/findings/verdicts/<bead-id>-verdict.json`:
```json
{
  "finding_id": "VRS-001",
  "verdict": "CONFIRMED",
  "is_vulnerable": true,
  "confidence_score": 0.92,
  "evidence_checks": [...],
  "evidence_synthesis": {
    "attacker_total_strength": 0.925,
    "defender_total_strength": 0.0,
    "delta": 0.925,
    "winning_side": "attacker",
    "close_contest": false
  },
  "dissent": null,
  "rationale": "...",
  "human_flag": true
}
```

### Step 5: Notify Orchestrator
```
SendMessage(type="message", recipient="audit-orchestrator",
  content="VERDICT for VRS-001: CONFIRMED (Critical) ...")
```

### Step 6: Mark Task Complete
```
TaskUpdate(taskId="...", status="completed")
```

## Anti-Patterns (FORBIDDEN)

- Adding new vulnerability analysis (you SYNTHESIZE)
- Finding new guards (that's the defender's job)
- Modifying evidence (report what was presented)
- Skipping human_flag (ALWAYS true)
- Perfect confidence scores (1.0 = fabrication)
- Ignoring strong dissenting evidence (record it)
```

### 5.4 Orchestrator Configuration

The orchestrator is the **team lead** — it's the user's Claude Code session that creates the team. It does NOT need a separate agent file. Instead, the `/vrs-audit` skill guides its behavior.

The orchestrator's responsibilities are codified in the updated skill (Section 6).

---

## 6. Updated /vrs-audit Skill

**File: `.claude/skills/vrs-audit-v2.md`**

```yaml
---
skill: vrs-audit
version: "2.0.0"
description: End-to-end smart contract security audit using Agent Teams debate
invocation: /vrs-audit <contracts_path> [--mode team|solo] [--skip-setup]
model: sonnet
evidence_required: true
output_format: markdown
---

# /vrs-audit — Agent Teams Edition

**Single entry point for AlphaSwarm.sol security audits.**

```
/vrs-audit contracts/
```

This skill orchestrates a 7-stage audit pipeline using Agent Teams for
multi-agent debate.

---

## Pipeline (7 Stages)

### Stage 1: Setup & Validation

```bash
# Check prerequisites
which alphaswarm || echo "ERROR: Install with: uv tool install alphaswarm"
which slither || echo "ERROR: Install with: pip install slither-analyzer"

# Detect project type
ls foundry.toml 2>/dev/null && echo "Foundry project detected"
ls hardhat.config.js 2>/dev/null && echo "Hardhat project detected"

# Create output directories
mkdir -p .vrs/state .vrs/graphs .vrs/findings/attacker .vrs/findings/defender .vrs/findings/verdicts .vrs/reports
```

### Stage 2: Build Knowledge Graph

```bash
uv run alphaswarm build-kg <contracts_path> --with-labels --output .vrs/graphs/
```

The BSKG extracts 50+ security properties per function, computes semantic
operations and behavioral signatures, and builds the knowledge graph that
all agents will query.

### Stage 3: Pattern Matching

```bash
uv run alphaswarm query "pattern:*" --graph .vrs/graphs/project.toon
```

Identify Tier A (deterministic) and Tier B (needs verification) matches.
Each match becomes an investigation bead.

### Stage 4: Create Investigation Team

```python
# Create Agent Teams debate team
TeamCreate({
    team_name: "vrs-audit-{project}",
    description: "Security audit debate for {project}"
})

# Spawn teammates
Task({
    name: "attacker",
    subagent_type: "vrs-attacker-v2",
    prompt: """You are the attacker in a security audit team for {project}.
    The BSKG graph is at .vrs/graphs/project.toon.
    Check TaskList for your assigned investigation beads.
    For each bead: query graph → analyze → write findings → DM defender.""",
    team_name: "vrs-audit-{project}"
})

Task({
    name: "defender",
    subagent_type: "vrs-defender-v2",
    prompt: """You are the defender in a security audit team for {project}.
    The BSKG graph is at .vrs/graphs/project.toon.
    Wait for attack claims from the attacker via DM.
    For each claim: query graph for guards → analyze → write defense → DM attacker.""",
    team_name: "vrs-audit-{project}"
})

Task({
    name: "verifier",
    subagent_type: "vrs-verifier-v2",
    prompt: """You are the verifier in a security audit team for {project}.
    The BSKG graph is at .vrs/graphs/project.toon.
    Wait for debate results from attacker/defender.
    For each debate: read both analyses → cross-check graph → render verdict → DM orchestrator.""",
    team_name: "vrs-audit-{project}"
})
```

### Stage 5: Create Investigation Tasks (DAG)

For each pattern match (bead), create a task pipeline:

```python
for bead in pattern_matches:
    # Attack task
    attack_task = TaskCreate({
        subject: f"Investigate: {bead.id} ({bead.description})",
        description: f"""
        Bead ID: {bead.id}
        Pattern: {bead.pattern_id}
        Severity: {bead.severity}
        Location: {bead.location}
        Signature: {bead.signature}
        Graph Node: {bead.node_id}
        """,
        activeForm: f"Investigating {bead.id}"
    })
    TaskUpdate({ taskId: attack_task.id, owner: "attacker" })

    # Defense task (blocked by attack)
    defense_task = TaskCreate({
        subject: f"Defend: {bead.id}",
        description: "Review attacker findings and search for guards.",
        activeForm: f"Defending {bead.id}"
    })
    TaskUpdate({
        taskId: defense_task.id,
        owner: "defender",
        addBlockedBy: [attack_task.id]
    })

    # Verdict task (blocked by both attack and defense)
    verdict_task = TaskCreate({
        subject: f"Verdict: {bead.id}",
        description: "Synthesize debate and render verdict.",
        activeForm: f"Verifying {bead.id}"
    })
    TaskUpdate({
        taskId: verdict_task.id,
        owner: "verifier",
        addBlockedBy: [attack_task.id, defense_task.id]
    })
```

### Stage 6: Monitor Debate Progress

The orchestrator monitors via TaskList:

```python
while not all_verdicts_complete:
    tasks = TaskList()
    completed = [t for t in tasks if t.status == "completed"]
    pending = [t for t in tasks if t.status == "pending"]

    # Log progress
    print(f"Progress: {len(completed)}/{len(tasks)} tasks complete")

    # Check for stuck work (no progress in 5 minutes)
    if no_progress_for(300):
        # Send nudge to stuck agent
        SendMessage(type="message", recipient=stuck_agent,
            content="Status check: are you blocked on anything?")

    wait(30)  # Check every 30 seconds
```

### Stage 7: Generate Report

After all verdicts are in:

```python
# Collect all verdicts
verdicts = read_all(".vrs/findings/verdicts/*-verdict.json")

# Sort by severity and confidence
critical = [v for v in verdicts if v.verdict == "CONFIRMED" and v.severity == "critical"]
high = [v for v in verdicts if v.verdict in ["CONFIRMED", "LIKELY"] and v.severity == "high"]

# Generate report
Write(".vrs/reports/audit-report.md", generate_report(verdicts))

# Shutdown team
SendMessage(type="shutdown_request", recipient="attacker")
SendMessage(type="shutdown_request", recipient="defender")
SendMessage(type="shutdown_request", recipient="verifier")
```

### Report Format

```markdown
# Security Audit Report: {project}

## Executive Summary
- **Contracts Audited:** {count}
- **BSKG Nodes:** {node_count}
- **Pattern Matches:** {match_count}
- **Debate Rounds:** {debate_count}

| Severity | Confirmed | Likely | Uncertain | Rejected |
|----------|-----------|--------|-----------|----------|
| Critical | N | N | N | N |
| High | N | N | N | N |
| Medium | N | N | N | N |

## Findings

### [C-01] {title}
**Verdict:** CONFIRMED | **Confidence:** 0.92 | **Location:** {file}:{line}

**Attack Path:**
{attacker_summary}

**Defense Assessment:**
{defender_summary}

**Verifier Rationale:**
{verifier_rationale}

**Evidence:**
- BSKG Node: {node_id}
- Properties: {key_properties}
- Behavioral Signature: {signature}

**Recommendation:**
{recommendation}

---

## Methodology
This audit used AlphaSwarm.sol multi-agent debate protocol:
1. BSKG construction with 50+ security properties per function
2. Pattern matching against 680+ vulnerability signatures
3. Attacker-Defender-Verifier debate for each finding
4. All verdicts require human review (human_flag: true)
```

---

## Solo Mode (/vrs-audit --mode solo)

For quick audits without full debate, use solo mode:

```python
# No team creation
# Single attacker agent investigates all beads
# No debate — findings are UNVERIFIED
# Faster but lower confidence
```

Solo mode uses a single subagent (not Agent Teams) to investigate
pattern matches and produce findings without debate verification.
Findings are marked as UNVERIFIED and require manual review.

---

## Cost Estimate

| Component | Model | Est. Tokens | Est. Cost (per bead) |
|-----------|-------|-------------|---------------------|
| Attacker investigation | Opus | ~15K input + ~5K output | ~$0.45 |
| Defender investigation | Sonnet | ~15K input + ~5K output | ~$0.15 |
| Verifier verdict | Opus | ~10K input + ~3K output | ~$0.25 |
| Orchestrator overhead | Sonnet | ~5K | ~$0.05 |
| **Total per bead** | | | **~$0.90** |
| **10-bead audit** | | | **~$9.00** |

Covered by Claude Code Max subscription ($200/month).
```

---

## 7. Migration Path

### Phase 1: Foundation (Week 1-2)

**Goal:** Make ONE debate work end-to-end.

| Task | Description | Effort |
|------|-------------|--------|
| Create v2 agent files | Write `vrs-attacker-v2.md`, `vrs-defender-v2.md`, `vrs-verifier-v2.md` | 2 hours |
| Create hook scripts | Write 4 Python hook scripts | 4 hours |
| Create output directories | `.vrs/findings/{attacker,defender,verdicts}/` | 10 min |
| Create skills stubs | `graph-first-template`, `evidence-packet-format` | 1 hour |
| Manual test: one bead | Run debate on simple reentrancy contract | 2 hours |
| Capture transcript | Save complete execution evidence | 30 min |

**Success criteria:** One bead goes through attacker → defender → verifier with real DMs, evidence files written, and verdict produced.

### Phase 2: Pipeline Integration (Week 2-3)

**Goal:** Connect BSKG → Pattern Matching → Debate → Report.

| Task | Description | Effort |
|------|-------------|--------|
| Fix `build-kg` integration | Ensure graph builds successfully | P0 bug |
| Fix pattern matching | Ensure `beads generate` works | P0 bug |
| Implement DAG task creation | Auto-create task pipeline from pattern matches | 4 hours |
| Implement report generation | Aggregate verdicts into markdown report | 3 hours |
| Test: 3-bead audit | Run full pipeline on test contracts | 4 hours |

**Success criteria:** `/vrs-audit contracts/` produces a complete report with 3+ verified findings.

### Phase 3: Enforcement & Robustness (Week 3-4)

**Goal:** Hooks prevent drift, evidence is enforced.

| Task | Description | Effort |
|------|-------------|--------|
| Enable graph-first hook | PreToolUse enforcement | 2 hours |
| Enable evidence completeness hook | TaskCompleted gate | 2 hours |
| Enable verdict quality hook | Stop gate | 2 hours |
| Enable context restoration hook | SessionStart(compact) | 1 hour |
| Test hooks with intentional violations | Verify hooks block bad behavior | 3 hours |
| Persistent memory seeding | Seed initial MEMORY.md for each agent | 2 hours |

**Success criteria:** Hooks catch violations, agents produce graph-anchored evidence.

### Phase 4: Deprecation (Week 4)

| Task | Description | Effort |
|------|-------------|--------|
| Archive Python swarm system | Move `swarm/agents.py` to archive | 30 min |
| Archive v1 agent files | Rename `vrs-attacker.md` → `vrs-attacker-v1.md.bak` | 30 min |
| Archive v1 skill | Rename `vrs-audit.md` → `vrs-audit-v1.md.bak` | 30 min |
| Update CLAUDE.md | Reflect new architecture | 1 hour |
| Update catalog.yaml | Remove placeholder agents | 1 hour |

### What NOT to Migrate

| Component | Decision | Rationale |
|-----------|----------|-----------|
| Python swarm agents | ARCHIVE | Separate architecture, never used |
| Python AttackerAgent class | ARCHIVE | Claude Code agents replace this |
| debate.py orchestrator | KEEP (reference) | Useful for schema definitions |
| Hardcoded rebuttals | DELETE | Agent Teams DMs replace these |
| DebateOrchestrator | ARCHIVE | Team lead + Task DAG replaces this |
| Evidence schemas | KEEP | Still valid for JSON file format |

---

## 8. Risk Assessment

### Known Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Agent Teams experimental status | MEDIUM | HIGH | Keep v1 agents as fallback |
| Two agents edit same file | LOW | MEDIUM | Strict file ownership per agent |
| Token cost exceeds budget | MEDIUM | LOW | Sonnet for defender, monitor costs |
| Hook scripts have bugs | MEDIUM | MEDIUM | Test hooks in isolation first |
| Agents ignore DM protocol | MEDIUM | MEDIUM | Clear prompts + task design |
| Context compaction loses state | HIGH | MEDIUM | SessionStart(compact) hook |
| Skill auto-invocation fails | HIGH | LOW | Skills preloaded, not runtime |

### Rollback Plan

If Agent Teams doesn't work:
1. Fall back to sequential subagent spawning (existing pattern)
2. Orchestrator manually shuttles messages between subagents
3. Loses direct DM benefit but still works
4. Keep hook enforcement (works with subagents too)

---

## 9. Effort Estimate

| Phase | Duration | Effort (person-hours) |
|-------|----------|----------------------|
| Phase 1: Foundation | 1-2 weeks | 10-12 hours |
| Phase 2: Pipeline Integration | 1-2 weeks | 12-15 hours |
| Phase 3: Enforcement | 1 week | 10-12 hours |
| Phase 4: Deprecation | 2-3 days | 3-4 hours |
| **Total** | **3-5 weeks** | **35-43 hours** |

### Dependencies

- **Requires:** P0 bugs fixed (W2-1) — `build-kg` and pattern matching must work
- **Requires:** Agent Teams enabled — `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`
- **Parallelizable with:** W2-2 (property gap), W2-5 (benchmarks)
- **Blocks:** W2-6 (test framework needs real agent execution to test)

---

## Appendix A: File Structure

```
.claude/
├── agents/
│   ├── vrs-attacker-v2.md      # NEW: Agent Teams attacker
│   ├── vrs-defender-v2.md      # NEW: Agent Teams defender
│   ├── vrs-verifier-v2.md      # NEW: Agent Teams verifier
│   ├── vrs-attacker.md         # OLD: archive after migration
│   ├── vrs-defender.md         # OLD: archive after migration
│   └── vrs-verifier.md         # OLD: archive after migration
├── hooks/
│   ├── graph-first-check.py    # NEW: PreToolUse enforcement
│   ├── track-bskg-query.py     # NEW: PostToolUse tracking
│   ├── evidence-completeness-check.py  # NEW: TaskCompleted gate
│   └── verdict-evidence-check.py       # NEW: Stop gate
├── skills/
│   ├── vrs-audit-v2.md         # NEW: Agent Teams audit skill
│   ├── graph-first-template.md # NEW: Preloaded skill
│   └── evidence-packet-format.md # NEW: Preloaded skill
├── agent-memory/               # Persistent memory (git-tracked)
│   ├── vrs-attacker-v2/
│   │   └── MEMORY.md
│   ├── vrs-defender-v2/
│   │   └── MEMORY.md
│   └── vrs-verifier-v2/
│       └── MEMORY.md
└── settings.json               # Hook configuration

.vrs/
├── state/
│   ├── audit-context.json      # Orchestrator state (for compaction recovery)
│   └── graph-queries-run.json  # BSKG query tracking (per session)
├── graphs/
│   └── project.toon            # Built BSKG
├── findings/
│   ├── attacker/               # Attacker writes here only
│   │   ├── VRS-001-attack.json
│   │   └── VRS-001-rebuttal.json
│   ├── defender/               # Defender writes here only
│   │   └── VRS-001-defense.json
│   └── verdicts/               # Verifier writes here only
│       └── VRS-001-verdict.json
└── reports/
    └── audit-report.md         # Final aggregated report
```

## Appendix B: Settings.json Additions

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  },
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Read|Grep|Glob",
        "hooks": [
          {
            "type": "command",
            "command": "python3 .claude/hooks/graph-first-check.py"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python3 .claude/hooks/track-bskg-query.py"
          }
        ]
      }
    ],
    "TaskCompleted": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 .claude/hooks/evidence-completeness-check.py"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 .claude/hooks/verdict-evidence-check.py"
          }
        ]
      }
    ],
    "SessionStart": [
      {
        "matcher": "compact",
        "hooks": [
          {
            "type": "command",
            "command": "cat .vrs/state/audit-context.json 2>/dev/null || echo '{}'"
          }
        ]
      }
    ]
  }
}
```

## Appendix C: Comparison — Current vs. Proposed

| Aspect | Current (Broken) | Proposed (Agent Teams) |
|--------|------------------|----------------------|
| **Debate execution** | Never ran | Native Agent Teams DMs |
| **Agent communication** | None (3 disconnected systems) | SendMessage between teammates |
| **Rebuttals** | Hardcoded templates | Real agent-driven challenge/response |
| **Evidence enforcement** | Prompt-only (ignored) | Hook-enforced (blocks tool execution) |
| **Graph-first** | Documented, not enforced | PreToolUse hook blocks non-graph reads |
| **Task management** | Manual/none | DAG with auto-unblocking |
| **Persistent memory** | None | MEMORY.md per agent |
| **Context recovery** | None (lost on compaction) | SessionStart(compact) hook |
| **File conflicts** | N/A (never ran) | Strict directory ownership |
| **Agent count** | 24 claimed, 3-4 real | 3 teammates + 1 lead (honest) |
| **Architecture** | 3 disconnected systems | 1 unified Agent Teams system |
