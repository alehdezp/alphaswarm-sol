# W2-7: Documentation & Hooks Enforcement Plan

**Date:** 2026-02-08
**Agent:** W2-7 (Documentation & Hooks System Designer)
**Input:** Wave 1 reports (T1-T7), WAVE-1-SYNTHESIS.md
**Confidence:** HIGH (based on verified codebase state + official Claude Code hooks documentation)

---

## Part 1: Documentation Honesty Overhaul

### 1.1 CLAUDE.md False Claims Audit

Every claim in CLAUDE.md was checked against Wave 1 findings. Below is the complete table of discrepancies.

| # | CLAUDE.md Claim | Reality (Wave 1 Evidence) | Severity | Corrected Text |
|---|-----------------|---------------------------|----------|----------------|
| 1 | "shippable multi-agent orchestration framework" | No audit has ever been produced end-to-end (T5). Pipeline breaks at stage 4. Multi-agent debate has never executed (T3). | CRITICAL | "Multi-agent orchestration framework for smart contract security (under active development)" |
| 2 | "human-like security assessments that go far beyond static analysis" | Zero evidence of superiority over running Slither directly (T6). No benchmarks. | CRITICAL | Remove entirely. Replace with: "Augments static analyzers with behavioral graph analysis and AI-driven investigation" |
| 3 | "complex authorization bugs, logic flaws, and novel vulnerabilities" | Zero real vulnerabilities discovered. Sherlock AI found $2.4M bug; AlphaSwarm: 0 (T6). | HIGH | "Targets authorization bugs, logic flaws, and economic vulnerabilities (benchmarking in progress)" |
| 4 | "Build the world's best AI-powered Solidity security tool" | No benchmarks, no external validation, no publications (T6, rated 5/10). | HIGH | "Goal: Build a competitive AI-powered Solidity security tool with evidence-backed detection" |
| 5 | "Agent Catalog: 24 agents" | 3 have Python implementations, 6 have full prompts, ~15 are placeholders (T3). | CRITICAL | "Agent Catalog: 6 core agents (attacker, defender, verifier, supervisor, integrator, secure-reviewer), 12 support agents in development" |
| 6 | "Skill Registry: 47 skills" | 19 have broken frontmatter (`skill:` not `name:`), 28 not installed. ~20 actually invocable (T5). | CRITICAL | "Skill Registry: ~20 invocable skills, additional skills in development" |
| 7 | "680+ patterns" / "556+ patterns" | 562 YAML files. 385 are dead code (orphan properties). ~6 proven working. ~172 could theoretically work. (T2) | CRITICAL | "~170 active patterns (6 proven, ~160 untested, 385 quarantined pending property implementation)" |
| 8 | "84.6% DVDeFi detection rate" (in STATE.md, referenced indirectly) | YAML annotation, not computed result. Ground truth is TODO placeholders. (T2) | CRITICAL | Remove entirely. Replace with: "Detection rate: not yet benchmarked" |
| 9 | "`uv run alphaswarm orchestrate start pool-id --scope contracts/`" | `--scope` flag doesn't exist (T5). | MEDIUM | Fix CLI command: `uv run alphaswarm orchestrate start <contracts-path>` |
| 10 | "Two-Tier Detection: Tier A + Tier B + Tier C" | 67/557 use Tier A. 23/557 use Tier B. 0/557 use Tier C. Tier C has no matcher. (T2) | HIGH | "Detection: Tier A (67 patterns, deterministic). Tier B (23 patterns, LLM-verified, experimental). Tier C (planned, not implemented)" |
| 11 | "Beads Orchestration: Self-contained investigation packages" | `.vrs/beads/` is EMPTY. `beads generate` crashes. No bead ever created. (T3, T5) | HIGH | "Beads Orchestration: Architecture implemented, pending integration fixes" |
| 12 | Core Modules LOC table ("orchestration/ ~6,400", "tools/ ~12,000", etc.) | Not verified against Wave 1 but likely inflated. | LOW | Add caveat: "(LOC includes tests and experimental code)" |
| 13 | "Graph-first enforcement: Agents MUST use BSKG queries" | Zero runtime enforcement. Agents can't even run `alphaswarm query` (wrong tool permissions). (T1, T3) | CRITICAL | "Graph-first enforcement: Mandated in prompts, runtime enforcement via hooks planned for 6.0" |
| 14 | "Milestone 5.0 GA Release ~98% complete" | Product cannot produce an audit. Multiple P0 bugs. (T5) | HIGH | "Milestone 5.0: Infrastructure ~98% complete. Integration and E2E validation incomplete — see known issues." |
| 15 | Quick Commands: `uv run alphaswarm vulndocs validate vulndocs/` | All 74 entries fail validation. (T5) | MEDIUM | Add note: "(currently all entries fail validation — fix in progress)" |
| 16 | "MANDATORY: exa-search for ALL research" | Exa MCP tool not always available. Creates friction when tool unavailable. | LOW | "PREFERRED: exa-search for web research when available. Fallback to WebSearch." |
| 17 | Pattern Rating table (draft/ready/excellent thresholds) | 482/557 have NO status field at all. (T2) | MEDIUM | Add: "Note: 86% of patterns currently lack status ratings. Pattern quality audit in progress." |

### 1.2 docs/ Audit

| File | Status | Issues | Action |
|------|--------|--------|--------|
| `docs/PHILOSOPHY.md` | **MIXED** (accurate vision, wrong "Current State" section) | Lines 335-370 describe "Current Reality" but are outdated. Line 247: "680+ patterns across 18 vulnerability categories" — inflated. Lines 299-313: Validation Gates G0-G7 never implemented. Line 454: "Gauntlet testing achieves 80%+ accuracy" — never run. | Update "Current State" to match Wave 1 findings. Fix pattern count. Mark G0-G7 as "designed, not implemented". Remove gauntlet claim. |
| `docs/architecture.md` | **ASPIRATIONAL** (presents desired state as current) | Line 4: "680+ patterns" → wrong. Line 5: "24 specialized agents" → inflated. Line 7: "evidence-linked findings with proof tokens" → never produced. Lines 156-158: "680+ patterns", "21 Tier C patterns" → Tier C doesn't work. Line 184: "24 specialized agents with defined roles" → 3-6 functional. | Rewrite with "Working" / "In Development" / "Planned" sections. |
| `docs/index.md` | **MISLEADING** (Quick Stats are all inflated) | Lines 9-14: Patterns 680+, Agents 24, Skills 47 — all inflated per Wave 1. Line 3: "~98% complete" — misleading given P0 bugs. | Replace Quick Stats with honest numbers. |
| `docs/LIMITATIONS.md` | **MISSING CRITICAL LIMITATIONS** | Doesn't mention: pipeline breaks at stage 4, 385 dead patterns, no E2E audit ever produced, all vulndocs fail validation. | Add "Known Critical Issues" section with Wave 1 findings. |
| `docs/getting-started/first-audit.md` | **CANNOT WORK** | Describes a flow that breaks at pattern matching (stage 4). | Add prominent warning: "E2E audit pipeline has known blocking issues. See LIMITATIONS.md." |
| `docs/reference/agents.md` | **INFLATED** | Claims 24 agents. Only 3-6 are functional. | Restructure: "Core (functional)", "Defined (prompts exist)", "Planned (catalog entry only)". |
| `docs/guides/patterns-basics.md` | **MOSTLY ACCURATE** for mechanics | Pattern authoring mechanics are correct. But doesn't mention 385 dead patterns or orphan property problem. | Add "Property Validation" section explaining the orphan property issue. |
| `docs/reference/tools-overview.md` | **MOSTLY ACCURATE** | Tool integration code is genuinely working. | Minor: note Mythril/Medusa not installed by default. |

### 1.3 Honest Metrics — What We Can Actually Claim

**Current honest numbers (as of Wave 1):**

| Metric | Inflated Claim | Honest Value | Evidence |
|--------|---------------|--------------|----------|
| Patterns (total YAML files) | 680+ | 562 | File count |
| Patterns (active, using real properties) | 556+ | ~172 | T2 property gap analysis |
| Patterns (proven working) | Not stated (implied all) | ~6 | T2 test coverage analysis |
| Detection rate | 84.6% | Not benchmarked | T2 DVDeFi analysis |
| Agents (functional) | 24 | 3-6 | T3 agent inventory |
| Agents (with prompts) | 24 | ~9 | T3 Tier 1+2 count |
| Skills (invocable) | 47 | ~20 | T5 frontmatter audit |
| Skills (broken) | 0 | 19 | T5 frontmatter audit |
| E2E audits completed | Implied many | 0 | T3, T5 state directory analysis |
| Beads created | Implied active | 0 | T3 `.vrs/beads/` empty |
| Real vulnerabilities found | Implied | 0 | T6 competitive analysis |
| Published benchmarks | Implied | 0 | T6 |

**What we CAN honestly claim:**

1. "Rich behavioral knowledge graph with 208 security properties per function" (T1 — proven)
2. "20 semantic operations extracted from Slither IR" (T1 — proven)
3. "Behavioral signatures for function operation ordering" (T1 — proven)
4. "~170 active detection patterns across 19 categories" (T2 — verified)
5. "Tool coordination for Slither, Aderyn, Mythril with parallel execution" (T5 — verified)
6. "Natural language graph queries" (T5 — verified)
7. "Multi-agent debate architecture with attacker/defender/verifier roles" (T3 — designed, prompts exist)
8. "9 core agent prompts with detailed role specifications" (T3 — verified)
9. "~20 invocable Claude Code skills" (T5 — verified)

---

## Part 2: Hook Enforcement System

### Design Principles

Based on T7 research and the claude-code-hooks-mastery reference implementation:

1. **Deterministic over probabilistic**: Prefer `type: "command"` hooks (shell scripts) over `type: "prompt"` hooks (LLM calls) where possible. Command hooks are faster, cheaper, and predictable.
2. **Fail-open for development, fail-closed for audit**: During development, hooks should warn. During `/vrs-audit`, hooks should block.
3. **Log everything**: All hook executions log to `.vrs/hooks/` for debugging and compliance tracking.
4. **Graceful degradation**: Hook failures (exit 1) should not block the entire session — only hook rejections (exit 2) should block.
5. **Audit-mode activation**: Hooks enforce stricter rules when a `.vrs/audit-active.json` file exists (created by `/vrs-audit` Stage 1).

### Hook Architecture Overview

```
.claude/
├── hooks/
│   ├── graph_first_gate.py          # Hook 1: PreToolUse - Graph-first enforcement
│   ├── evidence_completeness.py     # Hook 2: TaskCompleted - Evidence gate
│   ├── anti_drift_injector.py       # Hook 3: SessionStart - Context re-injection
│   ├── agent_quality_gate.py        # Hook 4: Stop - Finding quality verification
│   ├── teammate_work_validator.py   # Hook 5: TeammateIdle - Premature stop prevention
│   ├── audit_state_manager.py       # Hook 6: PreCompact - Save audit state before compaction
│   └── lib/
│       ├── audit_context.py         # Shared: read/write audit state
│       ├── evidence_schema.py       # Shared: evidence validation logic
│       └── hook_logger.py           # Shared: structured hook logging
```

---

### Hook 1: Graph-First Enforcement (PreToolUse)

**Purpose:** When an agent tries to Read/Grep/Glob Solidity files directly during an audit, verify that BSKG queries have been run first. If not, block the action and inject guidance.

**Trigger:** `PreToolUse` for `Read`, `Grep`, `Glob` tools
**Matcher:** `Read|Grep|Glob`
**Can block:** Yes (exit 2)
**Type:** `command` (deterministic — checks file existence, not LLM judgment)

**Logic:**
1. Check if audit mode is active (`.vrs/audit-active.json` exists)
2. If not in audit mode, allow (exit 0) — don't interfere with development
3. If in audit mode, check if the target file is a `.sol` file
4. If not `.sol`, allow (exit 0) — only gate Solidity code reading
5. Check if `.vrs/graphs/` contains a recent graph file (< 1 hour old)
6. If no graph exists, block (exit 2) with message: "Run `alphaswarm build-kg` before reading Solidity source directly"
7. Check if `.vrs/hooks/graph-queries.jsonl` contains at least one query entry for this session
8. If no queries logged, block (exit 2) with message: "Run BSKG queries before manual code inspection. Use: `uv run alphaswarm query '<your question>' --graph .vrs/graphs/graph.toon`"
9. If graph exists and queries logged, allow (exit 0)

**Implementation:**

```python
#!/usr/bin/env python3
"""Graph-first enforcement hook for PreToolUse.

Blocks direct Solidity file reads during audits unless BSKG queries
have been run first. Only active when .vrs/audit-active.json exists.

Exit codes:
  0 = allow tool call
  2 = block tool call (shows stderr to Claude)
"""
import json
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

GRAPH_DIR = ".vrs/graphs"
QUERY_LOG = ".vrs/hooks/graph-queries.jsonl"
AUDIT_STATE = ".vrs/audit-active.json"
GRAPH_MAX_AGE_HOURS = 2

def is_solidity_target(tool_name: str, tool_input: dict) -> bool:
    """Check if the tool targets a .sol file."""
    if tool_name == "Read":
        return tool_input.get("file_path", "").endswith(".sol")
    elif tool_name == "Grep":
        path = tool_input.get("path", "")
        glob = tool_input.get("glob", "")
        return path.endswith(".sol") or "*.sol" in glob or glob.endswith(".sol")
    elif tool_name == "Glob":
        pattern = tool_input.get("pattern", "")
        return "*.sol" in pattern or pattern.endswith(".sol")
    return False

def has_recent_graph() -> bool:
    """Check if a BSKG graph was built recently."""
    graph_dir = Path(GRAPH_DIR)
    if not graph_dir.exists():
        return False
    cutoff = datetime.now() - timedelta(hours=GRAPH_MAX_AGE_HOURS)
    for f in graph_dir.iterdir():
        if f.suffix in (".toon", ".json"):
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if mtime > cutoff:
                return True
    return False

def has_logged_queries() -> bool:
    """Check if any BSKG queries have been logged this session."""
    query_log = Path(QUERY_LOG)
    if not query_log.exists():
        return False
    return query_log.stat().st_size > 10  # non-trivial content

def main():
    try:
        input_data = json.load(sys.stdin)
        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})

        # Only enforce during active audits
        if not Path(AUDIT_STATE).exists():
            sys.exit(0)

        # Only gate Solidity file access
        if not is_solidity_target(tool_name, tool_input):
            sys.exit(0)

        # Check graph exists
        if not has_recent_graph():
            print(
                "GRAPH-FIRST VIOLATION: No BSKG graph found.\n"
                "Run: uv run alphaswarm build-kg <contracts-dir>\n"
                "before reading Solidity source directly.",
                file=sys.stderr
            )
            sys.exit(2)

        # Check queries have been run
        if not has_logged_queries():
            print(
                "GRAPH-FIRST VIOLATION: No BSKG queries logged.\n"
                "Run graph queries before manual code inspection:\n"
                "  uv run alphaswarm query 'functions with value transfers' "
                "--graph .vrs/graphs/graph.toon\n"
                "This ensures findings are evidence-grounded.",
                file=sys.stderr
            )
            sys.exit(2)

        sys.exit(0)

    except Exception:
        # Fail open — don't block on hook errors
        sys.exit(0)

if __name__ == "__main__":
    main()
```

**settings.json configuration:**
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Read|Grep|Glob",
        "hooks": [
          {
            "type": "command",
            "command": "python3 .claude/hooks/graph_first_gate.py"
          }
        ]
      }
    ]
  }
}
```

---

### Hook 2: Evidence Completeness (TaskCompleted)

**Purpose:** When a task is marked complete during an audit, verify the evidence packet contains required fields: graph node IDs, code locations, and operation sequences.

**Trigger:** `TaskCompleted`
**Can block:** Yes (exit 2 prevents task completion)
**Type:** `command` (checks evidence file structure)

**Logic:**
1. Check if audit mode is active
2. Read the task metadata to determine if this is an investigation task (not a setup/admin task)
3. Check if `.vrs/evidence/<task-id>/` directory exists
4. Validate evidence file has: `graph_nodes` (non-empty), `code_locations` (non-empty), `verdict` (one of confirmed/likely/uncertain/rejected)
5. If validation fails, block completion with specific missing-field feedback

**Implementation:**

```python
#!/usr/bin/env python3
"""Evidence completeness gate for TaskCompleted.

Prevents tasks from being marked complete during audits unless
evidence packets meet minimum requirements.

Exit codes:
  0 = allow completion
  2 = block completion (evidence incomplete)
"""
import json
import sys
import os
from pathlib import Path

AUDIT_STATE = ".vrs/audit-active.json"
EVIDENCE_DIR = ".vrs/evidence"

REQUIRED_FIELDS = {
    "graph_nodes": "At least one BSKG node ID referenced",
    "code_locations": "At least one file:line location",
    "verdict": "One of: confirmed, likely, uncertain, rejected",
}

VALID_VERDICTS = {"confirmed", "likely", "uncertain", "rejected"}

def validate_evidence(task_id: str) -> list[str]:
    """Validate evidence packet for a task. Returns list of issues."""
    issues = []
    evidence_dir = Path(EVIDENCE_DIR) / task_id

    if not evidence_dir.exists():
        return [f"No evidence directory at {evidence_dir}"]

    # Look for evidence file (YAML or JSON)
    evidence_file = None
    for ext in (".json", ".yaml", ".yml"):
        candidate = evidence_dir / f"evidence{ext}"
        if candidate.exists():
            evidence_file = candidate
            break

    if not evidence_file:
        return [f"No evidence file in {evidence_dir}"]

    try:
        with open(evidence_file) as f:
            if evidence_file.suffix == ".json":
                data = json.load(f)
            else:
                # Simple YAML parse for key presence
                import yaml
                data = yaml.safe_load(f)
    except Exception as e:
        return [f"Cannot parse evidence file: {e}"]

    if not isinstance(data, dict):
        return ["Evidence file is not a dictionary"]

    # Check required fields
    graph_nodes = data.get("graph_nodes", [])
    if not graph_nodes:
        issues.append("Missing graph_nodes: " + REQUIRED_FIELDS["graph_nodes"])

    code_locations = data.get("code_locations", [])
    if not code_locations:
        issues.append("Missing code_locations: " + REQUIRED_FIELDS["code_locations"])

    verdict = data.get("verdict", "")
    if verdict not in VALID_VERDICTS:
        issues.append(
            f"Invalid verdict '{verdict}': " + REQUIRED_FIELDS["verdict"]
        )

    return issues

def main():
    try:
        input_data = json.load(sys.stdin)

        # Only enforce during active audits
        if not Path(AUDIT_STATE).exists():
            sys.exit(0)

        # Extract task info
        task_id = input_data.get("task_id", "")
        task_metadata = input_data.get("metadata", {})

        # Skip non-investigation tasks (setup, admin, etc.)
        task_type = task_metadata.get("type", "")
        if task_type in ("setup", "admin", "infrastructure"):
            sys.exit(0)

        # Validate evidence
        issues = validate_evidence(task_id)
        if issues:
            msg = "EVIDENCE INCOMPLETE — cannot mark task as complete:\n"
            for i, issue in enumerate(issues, 1):
                msg += f"  {i}. {issue}\n"
            msg += "\nCreate evidence at: .vrs/evidence/{task_id}/evidence.json"
            print(msg, file=sys.stderr)
            sys.exit(2)

        sys.exit(0)

    except Exception:
        # Fail open
        sys.exit(0)

if __name__ == "__main__":
    main()
```

**settings.json configuration:**
```json
{
  "hooks": {
    "TaskCompleted": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 .claude/hooks/evidence_completeness.py"
          }
        ]
      }
    ]
  }
}
```

---

### Hook 3: Anti-Drift Context Re-Injection (SessionStart)

**Purpose:** When a session starts (especially after compaction or resume), re-inject critical audit context so the agent doesn't lose track of the investigation.

**Trigger:** `SessionStart` (fires on startup, resume, compact, and clear)
**Can block:** No (injects context via `additionalContext`)
**Type:** `command` (reads files, outputs JSON)

**Logic:**
1. Check session source (startup, resume, compact, clear)
2. If `.vrs/audit-active.json` exists, load audit state
3. Build context injection:
   - Current audit scope (contracts being audited)
   - Investigation progress (beads completed, pending)
   - Critical rules (graph-first, evidence requirements)
   - Recent findings (last 5 verdicts)
4. Output as `hookSpecificOutput.additionalContext`

**Implementation:**

```python
#!/usr/bin/env python3
"""Anti-drift context re-injection for SessionStart.

After compaction or resume, re-injects critical audit context to
prevent the agent from losing track of the investigation.

Always exits 0 (cannot block SessionStart).
Outputs JSON with additionalContext when audit is active.
"""
import json
import sys
import os
from pathlib import Path
from datetime import datetime

AUDIT_STATE = ".vrs/audit-active.json"
BEADS_DIR = ".vrs/beads"
HOOKS_LOG = ".vrs/hooks/sessions.jsonl"

def load_audit_state() -> dict | None:
    """Load current audit state if active."""
    state_path = Path(AUDIT_STATE)
    if not state_path.exists():
        return None
    try:
        with open(state_path) as f:
            return json.load(f)
    except Exception:
        return None

def count_beads() -> dict:
    """Count beads by status."""
    beads_dir = Path(BEADS_DIR)
    counts = {"total": 0, "investigating": 0, "confirmed": 0,
              "rejected": 0, "uncertain": 0}
    if not beads_dir.exists():
        return counts
    for f in beads_dir.glob("*.yaml"):
        counts["total"] += 1
        # Quick status check without full YAML parse
        try:
            content = f.read_text()
            for status in ("investigating", "confirmed", "rejected", "uncertain"):
                if f"status: {status}" in content:
                    counts[status] += 1
                    break
        except Exception:
            pass
    return counts

def build_context(source: str, audit_state: dict) -> str:
    """Build the context injection string."""
    lines = []
    lines.append("=" * 60)
    lines.append("AUDIT CONTEXT (re-injected after context event)")
    lines.append("=" * 60)
    lines.append(f"Session event: {source}")
    lines.append(f"Timestamp: {datetime.now().isoformat()}")
    lines.append("")

    # Audit scope
    scope = audit_state.get("scope", "unknown")
    stage = audit_state.get("current_stage", "unknown")
    lines.append(f"AUDIT SCOPE: {scope}")
    lines.append(f"CURRENT STAGE: {stage}")
    lines.append("")

    # Progress
    beads = count_beads()
    lines.append(f"BEADS: {beads['total']} total, "
                 f"{beads['investigating']} investigating, "
                 f"{beads['confirmed']} confirmed, "
                 f"{beads['rejected']} rejected")
    lines.append("")

    # Critical rules reminder
    lines.append("CRITICAL RULES (always enforced):")
    lines.append("1. GRAPH-FIRST: Run BSKG queries before reading .sol files")
    lines.append("2. EVIDENCE: Every finding needs graph_nodes + code_locations + verdict")
    lines.append("3. NO FABRICATION: If unsure, mark verdict as 'uncertain'")
    lines.append("4. TOOL USAGE: Use `uv run alphaswarm query` for graph queries")
    lines.append("")

    # Graph location
    graph_path = audit_state.get("graph_path", ".vrs/graphs/graph.toon")
    lines.append(f"GRAPH: {graph_path}")
    lines.append("=" * 60)

    return "\n".join(lines)

def log_session(source: str, session_id: str):
    """Append session event to log."""
    log_path = Path(HOOKS_LOG)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now().isoformat(),
        "source": source,
        "session_id": session_id,
        "audit_active": Path(AUDIT_STATE).exists()
    }
    with open(log_path, "a") as f:
        f.write(json.dumps(entry) + "\n")

def main():
    try:
        input_data = json.load(sys.stdin)
        source = input_data.get("source", "unknown")
        session_id = input_data.get("session_id", "unknown")

        # Log every session event
        log_session(source, session_id)

        # Check for active audit
        audit_state = load_audit_state()
        if audit_state is None:
            sys.exit(0)

        # Build and output context injection
        context = build_context(source, audit_state)
        output = {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": context
            }
        }
        print(json.dumps(output))
        sys.exit(0)

    except Exception:
        sys.exit(0)

if __name__ == "__main__":
    main()
```

**settings.json configuration:**
```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 .claude/hooks/anti_drift_injector.py"
          }
        ]
      }
    ]
  }
}
```

---

### Hook 4: Agent Quality Gate (Stop)

**Purpose:** When an agent finishes responding during an audit, verify that any findings mentioned have evidence anchoring. If findings lack evidence, force the agent to continue.

**Trigger:** `Stop`
**Can block:** Yes (exit 2 forces continuation)
**Type:** `command` (checks last response for unanchored claims)

**Logic:**
1. Check if audit mode is active
2. Read the agent's last response from transcript
3. Scan for vulnerability claims without evidence markers
4. If unanchored findings detected, block stop and request evidence
5. Allow stop after 3 consecutive Stop hook blocks (safety valve to prevent infinite loops)

**Implementation:**

```python
#!/usr/bin/env python3
"""Agent quality gate for Stop event.

Checks if the agent's response contains vulnerability claims
without evidence anchoring. Forces continuation if findings
lack graph references.

Exit codes:
  0 = allow stop
  2 = force continuation (insufficient evidence)
"""
import json
import sys
import os
import re
from pathlib import Path
from datetime import datetime

AUDIT_STATE = ".vrs/audit-active.json"
STOP_COUNTER = ".vrs/hooks/stop-counter.json"
MAX_CONSECUTIVE_BLOCKS = 3

# Patterns indicating vulnerability claims
VULN_CLAIM_PATTERNS = [
    r"(?i)\b(vulnerability|vuln|exploit|attack vector|security issue)\b.*\b(found|detected|identified|discovered)\b",
    r"(?i)\b(confirmed|likely|high severity|critical|medium severity)\b.*\b(finding|vulnerability|issue)\b",
    r"(?i)\bverdict:\s*(confirmed|likely)\b",
]

# Patterns indicating evidence anchoring
EVIDENCE_PATTERNS = [
    r"graph[_\s]?node",
    r"node[_\s]?id",
    r"[A-Z]{2,}_\d{3}",  # Bead IDs like VRS-042
    r"\bline\s+\d+\b",  # Line references
    r"\.sol:\d+",  # File:line references
    r"behavioral[_\s]?signature",
    r"R:bal|W:bal|X:out|C:auth|M:crit",  # Signature codes
    r"TRANSFERS_VALUE_OUT|CHECKS_PERMISSION|MODIFIES_CRITICAL_STATE",
]

def has_unanchored_claims(transcript_text: str) -> bool:
    """Check if the response has vulnerability claims without evidence."""
    has_claims = any(
        re.search(p, transcript_text) for p in VULN_CLAIM_PATTERNS
    )
    if not has_claims:
        return False

    has_evidence = any(
        re.search(p, transcript_text) for p in EVIDENCE_PATTERNS
    )
    return not has_evidence

def get_block_count() -> int:
    """Get consecutive block count."""
    counter_path = Path(STOP_COUNTER)
    if not counter_path.exists():
        return 0
    try:
        with open(counter_path) as f:
            data = json.load(f)
        return data.get("count", 0)
    except Exception:
        return 0

def set_block_count(count: int):
    """Set consecutive block count."""
    counter_path = Path(STOP_COUNTER)
    counter_path.parent.mkdir(parents=True, exist_ok=True)
    with open(counter_path, "w") as f:
        json.dump({"count": count, "updated": datetime.now().isoformat()}, f)

def main():
    try:
        input_data = json.load(sys.stdin)

        # Only enforce during active audits
        if not Path(AUDIT_STATE).exists():
            sys.exit(0)

        # Safety valve: don't block more than N times consecutively
        block_count = get_block_count()
        if block_count >= MAX_CONSECUTIVE_BLOCKS:
            set_block_count(0)
            sys.exit(0)

        # Get the transcript for the last response
        transcript_path = input_data.get("transcript_path", "")
        if not transcript_path or not os.path.exists(transcript_path):
            sys.exit(0)

        # Read last few lines of transcript (last assistant response)
        try:
            with open(transcript_path) as f:
                lines = f.readlines()
            # Get last 50 lines as proxy for last response
            last_chunk = "".join(lines[-50:])
        except Exception:
            sys.exit(0)

        # Check for unanchored claims
        if has_unanchored_claims(last_chunk):
            set_block_count(block_count + 1)
            print(
                "QUALITY GATE: Your response contains vulnerability claims "
                "without evidence anchoring.\n"
                "Please add:\n"
                "  - Graph node IDs from BSKG queries\n"
                "  - Code locations (file:line)\n"
                "  - Behavioral signature or semantic operations\n"
                "  - Explicit verdict (confirmed/likely/uncertain/rejected)\n"
                "Continue your response with evidence.",
                file=sys.stderr
            )
            sys.exit(2)

        # Reset counter on successful stop
        set_block_count(0)
        sys.exit(0)

    except Exception:
        sys.exit(0)

if __name__ == "__main__":
    main()
```

**settings.json configuration:**
```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 .claude/hooks/agent_quality_gate.py"
          }
        ]
      }
    ]
  }
}
```

---

### Hook 5: Teammate Work Validation (TeammateIdle)

**Purpose:** When a teammate goes idle during an audit, check if their assigned work is actually complete. Prevent premature stopping when investigation tasks remain open.

**Trigger:** `TeammateIdle`
**Can block:** Yes (exit 2 keeps teammate working)
**Type:** `command` (checks task list for open assigned tasks)

**Logic:**
1. Check if audit mode is active
2. Read teammate's name from input
3. Check task list for tasks assigned to this teammate with status != completed
4. If open tasks exist, block idle with reminder of pending work
5. Safety valve: allow idle after 2 consecutive blocks (same as Hook 4)

**Implementation:**

```python
#!/usr/bin/env python3
"""Teammate work validation for TeammateIdle.

Checks if a teammate has completed all assigned investigation tasks
before allowing them to go idle. Prevents premature stopping.

Exit codes:
  0 = allow idle
  2 = keep working (open tasks remain)
"""
import json
import sys
import os
import glob as glob_mod
from pathlib import Path
from datetime import datetime

AUDIT_STATE = ".vrs/audit-active.json"
IDLE_COUNTER_DIR = ".vrs/hooks/idle-counters"
MAX_CONSECUTIVE_BLOCKS = 2

def get_open_tasks_for_teammate(teammate_name: str) -> list[dict]:
    """Check task list for open tasks assigned to this teammate."""
    open_tasks = []

    # Check ~/.claude/tasks/ for team task lists
    tasks_dir = Path.home() / ".claude" / "tasks"
    if not tasks_dir.exists():
        return []

    for team_dir in tasks_dir.iterdir():
        if not team_dir.is_dir():
            continue
        for task_file in team_dir.glob("*.json"):
            try:
                with open(task_file) as f:
                    task = json.load(f)
                owner = task.get("owner", "")
                status = task.get("status", "")
                if owner == teammate_name and status in ("pending", "in_progress"):
                    open_tasks.append({
                        "id": task.get("id", task_file.stem),
                        "subject": task.get("subject", "unknown"),
                        "status": status,
                    })
            except Exception:
                continue

    return open_tasks

def get_idle_block_count(teammate: str) -> int:
    """Get consecutive idle block count for a teammate."""
    counter_path = Path(IDLE_COUNTER_DIR) / f"{teammate}.json"
    if not counter_path.exists():
        return 0
    try:
        with open(counter_path) as f:
            return json.load(f).get("count", 0)
    except Exception:
        return 0

def set_idle_block_count(teammate: str, count: int):
    """Set idle block count for a teammate."""
    counter_dir = Path(IDLE_COUNTER_DIR)
    counter_dir.mkdir(parents=True, exist_ok=True)
    with open(counter_dir / f"{teammate}.json", "w") as f:
        json.dump({"count": count, "updated": datetime.now().isoformat()}, f)

def main():
    try:
        input_data = json.load(sys.stdin)

        # Only enforce during active audits
        if not Path(AUDIT_STATE).exists():
            sys.exit(0)

        teammate_name = input_data.get("agent_name", "")
        if not teammate_name:
            sys.exit(0)

        # Safety valve
        block_count = get_idle_block_count(teammate_name)
        if block_count >= MAX_CONSECUTIVE_BLOCKS:
            set_idle_block_count(teammate_name, 0)
            sys.exit(0)

        # Check for open tasks
        open_tasks = get_open_tasks_for_teammate(teammate_name)
        if open_tasks:
            set_idle_block_count(teammate_name, block_count + 1)
            task_list = "\n".join(
                f"  - [{t['status']}] {t['id']}: {t['subject']}"
                for t in open_tasks[:5]
            )
            print(
                f"WORK INCOMPLETE: You have {len(open_tasks)} open task(s):\n"
                f"{task_list}\n"
                f"Complete your assigned tasks before going idle.",
                file=sys.stderr
            )
            sys.exit(2)

        # Reset counter
        set_idle_block_count(teammate_name, 0)
        sys.exit(0)

    except Exception:
        sys.exit(0)

if __name__ == "__main__":
    main()
```

**settings.json configuration:**
```json
{
  "hooks": {
    "TeammateIdle": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 .claude/hooks/teammate_work_validator.py"
          }
        ]
      }
    ]
  }
}
```

---

### Hook 6: Audit State Preservation (PreCompact)

**Purpose:** Before context compaction, save critical audit state to disk so the SessionStart hook (Hook 3) can restore it.

**Trigger:** `PreCompact`
**Can block:** No
**Type:** `command`

**Implementation:**

```python
#!/usr/bin/env python3
"""Audit state preservation for PreCompact.

Before compaction, saves a snapshot of critical audit context
to .vrs/hooks/pre-compact-state.json so it can be re-injected
by the SessionStart hook.

Always exits 0 (cannot block PreCompact).
"""
import json
import sys
import os
from pathlib import Path
from datetime import datetime

AUDIT_STATE = ".vrs/audit-active.json"
COMPACT_STATE = ".vrs/hooks/pre-compact-state.json"
BEADS_DIR = ".vrs/beads"

def main():
    try:
        input_data = json.load(sys.stdin)

        # Only save state if audit is active
        audit_path = Path(AUDIT_STATE)
        if not audit_path.exists():
            sys.exit(0)

        with open(audit_path) as f:
            audit_state = json.load(f)

        # Count current investigation status
        beads_dir = Path(BEADS_DIR)
        bead_statuses = {}
        if beads_dir.exists():
            for f in beads_dir.glob("*.yaml"):
                content = f.read_text()
                for status in ("investigating", "confirmed", "rejected", "uncertain"):
                    if f"status: {status}" in content:
                        bead_statuses[f.stem] = status
                        break

        # Save compact state
        compact_state = {
            "saved_at": datetime.now().isoformat(),
            "reason": "pre_compact",
            "audit_state": audit_state,
            "bead_statuses": bead_statuses,
            "session_id": input_data.get("session_id", ""),
        }

        compact_path = Path(COMPACT_STATE)
        compact_path.parent.mkdir(parents=True, exist_ok=True)
        with open(compact_path, "w") as f:
            json.dump(compact_state, f, indent=2)

        sys.exit(0)

    except Exception:
        sys.exit(0)

if __name__ == "__main__":
    main()
```

**settings.json configuration:**
```json
{
  "hooks": {
    "PreCompact": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 .claude/hooks/audit_state_manager.py"
          }
        ]
      }
    ]
  }
}
```

---

### Complete settings.json

This is the **full production settings.json** combining all hooks with the existing notification hooks and pyright plugin.

```json
{
  "enabledPlugins": {
    "pyright-lsp@claude-plugins-official": true
  },
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 .claude/hooks/anti_drift_injector.py"
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Read|Grep|Glob",
        "hooks": [
          {
            "type": "command",
            "command": "python3 .claude/hooks/graph_first_gate.py"
          }
        ]
      }
    ],
    "TaskCompleted": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 .claude/hooks/evidence_completeness.py"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 .claude/hooks/agent_quality_gate.py"
          }
        ]
      }
    ],
    "TeammateIdle": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 .claude/hooks/teammate_work_validator.py"
          }
        ]
      }
    ],
    "PreCompact": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 .claude/hooks/audit_state_manager.py"
          }
        ]
      }
    ],
    "Notification": [
      {
        "matcher": "permission_prompt",
        "hooks": [
          {
            "type": "command",
            "command": "osascript -e 'display notification \"Permission needed in '\"$(basename \"$CLAUDE_PROJECT_DIR\")\"'\" with title \"Claude Code\" subtitle \"Session: '\"${CLAUDE_SESSION_ID:-unknown}\"'\"' && curl -sS -H \"Title: Permission Required\" -H \"Tags: lock,claude\" -H \"Priority: high\" -d \"Project: $(basename \"$CLAUDE_PROJECT_DIR\")\" ntfy.sh/alesito-de-las-eras",
            "async": true
          }
        ]
      },
      {
        "matcher": "idle_prompt",
        "hooks": [
          {
            "type": "command",
            "command": "osascript -e 'display notification \"Waiting for input in '\"$(basename \"$CLAUDE_PROJECT_DIR\")\"'\" with title \"Claude Code\" subtitle \"Session: '\"${CLAUDE_SESSION_ID:-unknown}\"'\"' && curl -sS -H \"Title: Claude Idle\" -H \"Tags: hourglass,claude\" -H \"Priority: default\" -d \"Project: $(basename \"$CLAUDE_PROJECT_DIR\")\" ntfy.sh/alesito-de-las-eras",
            "async": true
          }
        ]
      }
    ]
  }
}
```

---

## Part 3: Additional Settings & Agent Configuration

### Agent Teams Enablement

The following environment variable must be set for Agent Teams support:

```bash
# Add to shell profile (.zshrc, .bashrc)
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
```

### Subagent Frontmatter Updates

Per T7 research, agent definitions should be updated with:

1. **`skills` preloading** — inject domain knowledge at spawn time
2. **`memory: project`** — enable persistent learning across sessions
3. **Per-agent hooks** — scoped enforcement within agent context
4. **Tool restrictions** — match to actual capabilities

Example updated `vrs-attacker.md` frontmatter:

```yaml
---
name: vrs-attacker
description: Construct exploit paths and attack preconditions for vulnerability beads
model: opus
tools: Read, Glob, Grep, Bash(uv run alphaswarm*)
disallowedTools: Write, Edit
permissionMode: plan
maxTurns: 30
skills:
  - graph-first-template
  - evidence-packet-format
memory: project
hooks:
  Stop:
    - hooks:
        - type: command
          command: "python3 .claude/hooks/agent_quality_gate.py"
---
```

**Critical fix from T1:** Change tool permission from `Bash(uv run python*)` to `Bash(uv run alphaswarm*)` so agents CAN actually run graph queries.

---

## Effort Estimate

| Work Item | Estimated Effort | Dependencies |
|-----------|------------------|--------------|
| **Part 1: CLAUDE.md rewrite** | 2-3 hours | Wave 1 reports (complete) |
| **Part 1: docs/ audit + rewrites** | 4-6 hours | CLAUDE.md rewrite |
| **Part 1: Honest metrics integration** | 1-2 hours | Pattern audit (T2), Agent audit (T3) |
| **Part 2: Hook 1 (graph-first)** | 2-3 hours | None |
| **Part 2: Hook 2 (evidence)** | 2-3 hours | Evidence schema design |
| **Part 2: Hook 3 (anti-drift)** | 1-2 hours | Audit state schema |
| **Part 2: Hook 4 (quality gate)** | 2-3 hours | Transcript access pattern |
| **Part 2: Hook 5 (teammate)** | 1-2 hours | Task list access pattern |
| **Part 2: Hook 6 (pre-compact)** | 1 hour | Audit state schema |
| **Part 2: settings.json integration** | 1 hour | All hooks |
| **Part 3: Agent frontmatter updates** | 2-3 hours | T3 agent inventory |
| **Testing all hooks** | 4-6 hours | All hooks implemented |
| **TOTAL** | **~22-34 hours** | — |

### Sequencing

```
Phase 1 (Week 1): CLAUDE.md + docs/ honesty overhaul
Phase 2 (Week 1-2): Implement hooks 1, 3, 6 (foundation: graph-first, anti-drift, state preservation)
Phase 3 (Week 2): Implement hooks 2, 4, 5 (quality gates: evidence, stop, teammate)
Phase 4 (Week 2): Integration testing (all hooks active during test audit)
Phase 5 (Week 3): Agent frontmatter updates + settings.json deployment
```

### Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Hooks slow down development workflow | HIGH | MEDIUM | Audit-mode-only activation (hooks check `.vrs/audit-active.json`) |
| Stop hook creates infinite loops | MEDIUM | HIGH | Safety valve: max 3 consecutive blocks, then allow |
| Graph-first gate blocks legitimate reads | MEDIUM | MEDIUM | Only gates `.sol` files; only during audits |
| Hook scripts fail on different platforms | LOW | HIGH | Graceful error handling (exit 0 on all exceptions) |
| Evidence schema too strict | MEDIUM | MEDIUM | Start with minimal fields, expand gradually |

---

## Summary

### Part 1 Deliverables
- CLAUDE.md rewritten with 17 false claims corrected
- 8 docs/ files audited with action plans
- Honest metrics table replacing all inflated numbers

### Part 2 Deliverables
- 6 production-ready hook scripts with implementations
- Complete settings.json configuration
- Safety valves for all blocking hooks
- Audit-mode activation pattern (hooks only enforce during `/vrs-audit`)

### Part 3 Deliverables
- Agent Teams environment configuration
- Updated agent frontmatter template with skills preloading and memory
- Critical tool permission fix (`Bash(uv run alphaswarm*)` not `Bash(uv run python*)`)

### Key Design Decision: Audit-Mode Activation

All blocking hooks gate on `.vrs/audit-active.json` — a file created by `/vrs-audit` Stage 1 (Preflight). This means:

- **During development**: Hooks log but don't block. Developers can read `.sol` files freely.
- **During audits**: Hooks enforce graph-first, evidence completeness, quality gates.
- **Activation is explicit**: Starting an audit creates the file. Finishing removes it.

This prevents the hooks from interfering with normal development while enforcing strict compliance during security analysis.
