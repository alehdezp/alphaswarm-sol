# W2-3: E2E Pipeline Plan

**Date:** 2026-02-08
**Confidence:** HIGH — Based on code reading and cross-referencing with W1 reports
**Author:** W2-3 E2E Pipeline Designer

---

## Current State

### What Works

| Stage | Component | Status | Evidence |
|-------|-----------|--------|----------|
| 1 | `alphaswarm --version` | WORKS | CLI loads, typer app boots |
| 1 | `alphaswarm tools status` | WORKS | Detects slither/aderyn availability |
| 2 | `alphaswarm build-kg contracts/` | WORKS | VKGBuilder + Slither → graph.json with 208 properties |
| 2 | `alphaswarm query "..."` | WORKS | NL query parser + executor produce results |
| - | Pool creation (`orchestrate start`) | WORKS | Creates scope + pool YAML in `.vrs/pools/` |
| - | Bead storage | WORKS | BeadStorage can save/load bead YAML |
| - | Pool storage | WORKS | PoolStorage can save/load pool YAML |

### What's Broken (with exact root causes)

| Stage | Component | Error | Root Cause | File:Line |
|-------|-----------|-------|------------|-----------|
| 4 | `beads generate` | `TypeError: PatternEngine.__init__() got an unexpected keyword argument 'pattern_dir'` | `PatternEngine.__init__` takes `tag_store`, not `pattern_dir`. CLI passes `pattern_dir=pdir`. | `cli/beads.py:594` vs `queries/patterns.py:504` |
| 4 | `beads generate` | `AttributeError: 'PatternEngine' object has no attribute 'run_all_patterns'` | Method doesn't exist. Engine has `.run(graph, patterns)` only. CLI calls `.run_all_patterns(graph)`. | `cli/beads.py:601` vs `queries/patterns.py:521` |
| 4 | `beads generate` | `AttributeError: 'PatternEngine' object has no attribute 'run_pattern'` | Same — `.run_pattern(graph, id)` doesn't exist. | `cli/beads.py:598` |
| 4 | `orchestrate resume` | Infinite loop | Router sends BUILD_GRAPH on every cycle; no state advancement | `orchestration/loop.py` + `orchestration/router.py` |
| 4 | `scaffold batch` | Same PatternEngine API mismatch | `main.py:905` also passes `pattern_dir=pdir` | `cli/main.py:905` |
| 4 | Handler `DetectPatternsHandler` | `store.load()` missing arg | `GraphStore.load()` requires a path arg, handler calls `store.load()` bare | `orchestration/handlers.py:378` |
| 4 | Handler `DetectPatternsHandler` | `PatternEngine(pattern_dir=...)` | Same API mismatch as beads CLI | `orchestration/handlers.py:389` |
| 4 | Handler `DetectPatternsHandler` | Accesses `m.pattern_id` on dict | `engine.run()` returns `list[dict]`, handler uses `.pattern_id` attribute access | `orchestration/handlers.py:396` |
| 4 | Handler `CreateBeadsHandler` | Mismatched `VulnerabilityBead` constructor | Passes `function_id`, `pattern_id`, `severity`, `pool_id` — but schema likely expects different args | `orchestration/handlers.py:462` |
| 5 | `SpawnAttackersHandler` | `from alphaswarm_sol.agents.attacker import AttackerAgent` | Module likely doesn't match expected interface | `orchestration/handlers.py:516` |
| 5 | `SpawnDefendersHandler` | `from alphaswarm_sol.agents.defender import DefenderAgent` | Same | `orchestration/handlers.py:633` |
| 6 | `DebateOrchestrator.run_debate()` | Signature mismatch | Called with `bead_id, evidence, attacker_context, defender_context` — likely wrong | `orchestration/handlers.py:842` |
| - | Pattern property gap | 337/485 properties don't exist | Patterns reference properties builder doesn't produce → silent no-match | `queries/patterns.py` + builder |
| - | VulnDocs validation | All 74 entries fail | Structural schema violations | `vulndocs/` |
| - | Skill frontmatter | 19 skills use `skill:` not `name:` | Claude Code requires v2 `name:` format | `.claude/skills/*.md` |

### Pipeline Break Points

```
Contract ──► build-kg ──► graph.json ──► PatternEngine ──► CRASH
  WORKS        WORKS         WORKS      ^^^^^^^^^^^^^^^^^^^
                                         API MISMATCH:
                                         1. __init__ takes wrong arg
                                         2. Methods don't exist
                                         3. No patterns loaded
                                         4. 69% of patterns are dead code
```

Everything after Stage 4 is **unreachable**. No bead, pool with verdicts, debate transcript, or audit report has EVER been produced.

---

## MVP Pipeline Design

### Design Principle

**Bypass the broken orchestration layer entirely.** The ExecutionLoop, Router, Handlers system is architecturally complex (13 handler classes, event replay, idempotency stores, work queues) but has never executed successfully. For MVP, we need a **direct pipeline** that Claude Code orchestrates step-by-step.

### MVP Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    /vrs-audit contracts/                  │
│                                                           │
│  Claude Code (THE ORCHESTRATOR) runs each step:          │
│                                                           │
│  Step 1: alphaswarm build-kg contracts/                  │
│     → .vrs/graphs/graph.json                             │
│                                                           │
│  Step 2: alphaswarm query "pattern:*" --graph ...        │
│     → JSON array of pattern matches                      │
│                                                           │
│  Step 3: Claude Code reads matches + source code         │
│     → Creates investigation beads (in-context)           │
│                                                           │
│  Step 4: Claude Code spawns attacker agent (Task tool)   │
│     → Attacker analyzes each finding                     │
│                                                           │
│  Step 5: Claude Code spawns defender agent (Task tool)   │
│     → Defender searches for guards                       │
│                                                           │
│  Step 6: Claude Code spawns verifier agent (Task tool)   │
│     → Verifier produces verdicts                         │
│                                                           │
│  Step 7: Claude Code generates report (markdown)         │
│     → .vrs/reports/audit-report.md                       │
│                                                           │
│  NO Python orchestration layer needed.                   │
│  Claude Code IS the orchestrator.                        │
└─────────────────────────────────────────────────────────┘
```

### Detailed Stage Design

#### Stage 1: Setup & Build Graph

**Tool:** `Bash(alphaswarm build-kg contracts/)`

```bash
# Build the knowledge graph
alphaswarm build-kg contracts/ --format toon

# Verify it worked
ls -la .vrs/graphs/
```

**Output:** `.vrs/graphs/graph.json` (or `.toon`)
**Failure handling:** If slither not installed, tell user to run `uv tool install slither-analyzer`
**What can go wrong:** Solc version mismatch, invalid Solidity. The builder handles this already.

#### Stage 2: Pattern Matching (FIX REQUIRED)

**Current crash point.** Two fixes needed:

**Fix A: Make `PatternEngine` accept patterns properly**

The engine's `.run(graph, patterns)` method works — it's the callers that are broken. The MVP path:

```python
# What WORKS today:
from alphaswarm_sol.queries.patterns import PatternEngine, PatternStore

# Load patterns from vulndocs
store = PatternStore(Path("vulndocs"))
patterns = store.load()

# Run engine
engine = PatternEngine()
matches = engine.run(graph, patterns)
# Returns: list[dict] with pattern_id, node_id, severity, etc.
```

**Fix B: Add convenience methods to PatternEngine**

```python
class PatternEngine:
    def __init__(self, pattern_dir=None, tag_store=None):
        self._tag_store = tag_store
        self._pattern_dir = pattern_dir
        self._tier_b_matcher = None

    def run_all_patterns(self, graph, **kwargs):
        """Load and run all patterns against graph."""
        patterns = self._load_patterns()
        return self.run(graph, patterns, **kwargs)

    def run_pattern(self, graph, pattern_id, **kwargs):
        """Run a single pattern by ID."""
        patterns = self._load_patterns()
        return self.run(graph, patterns, pattern_ids=[pattern_id], **kwargs)

    def _load_patterns(self):
        """Load patterns from configured directory."""
        if self._pattern_dir:
            store = PatternStore(self._pattern_dir)
        else:
            # Default: vulndocs in package
            vulndocs_path = Path(__file__).parent.parent / "vulndocs"
            if vulndocs_path.exists():
                return PatternStore.load_vulndocs_patterns(vulndocs_path)
            store = PatternStore(Path("vulndocs"))
        return store.load()
```

**Fix C: Fix all callers**

| Caller | Current (broken) | Fix |
|--------|-----------------|-----|
| `cli/beads.py:594` | `PatternEngine(pattern_dir=pdir)` | `PatternEngine(pattern_dir=pdir)` (works after Fix B) |
| `cli/beads.py:598` | `engine.run_pattern(graph, pattern)` | Works after Fix B |
| `cli/beads.py:601` | `engine.run_all_patterns(graph)` | Works after Fix B |
| `cli/main.py:905` | `PatternEngine(pattern_dir=pdir)` | Works after Fix B |
| `orchestration/runner.py:184` | `PatternEngine()` then `engine.run_all_patterns(graph)` | Works after Fix B |
| `orchestration/handlers.py:389` | `PatternEngine(pattern_dir=...)` then `engine.run_all_patterns(graph)` | Works after Fix B |

**Alternative for MVP:** Skip the CLI, have Claude Code use the `query` command:

```bash
# This WORKS today — queries patterns via NL interface
alphaswarm query "pattern:weak-access-control" --graph .vrs/graphs/graph.json
alphaswarm query "functions without access control" --graph .vrs/graphs/graph.json
```

**MVP Decision: Use `alphaswarm query` for initial pattern matching** (works today), then fix `PatternEngine` API for `beads generate` to work.

#### Stage 3: Create Beads (TWO OPTIONS)

**Option A (MVP - No code change):** Claude Code creates beads in-context.

After getting query results, Claude Code has enough context to reason about each finding without the beads system. It reads the source code, reads the pattern match, and passes it to the agents.

**Option B (Proper - Requires fix):** Fix `beads generate` to work.

Requires Fix B above plus fixing `BeadCreator.create_beads_from_findings` to accept the dict format from `engine.run()`.

**MVP Decision: Option A.** Claude Code reads query results + source code directly. Beads are an internal state management system — Claude Code doesn't need them to reason about findings.

#### Stage 4: Agent Investigation

**Claude Code IS the orchestrator.** It spawns Task subagents:

```
Claude Code:
  "Here is a finding: [match data + source code]
   You are the ATTACKER. Construct exploit path."
  → Task(subagent_type="vrs-attacker")

  "Here is a finding: [match data + source code]
   You are the DEFENDER. Find guards and mitigations."
  → Task(subagent_type="vrs-defender")
```

The agents DON'T need to call `alphaswarm query` (the tool permission issue noted in W1). Claude Code pre-loads all the context they need:
- Pattern match details (from stage 2)
- Source code (from Read tool)
- Graph properties (from query output)

**This solves the "agents can't run graph queries" problem** — the orchestrator provides the graph context, agents reason about it.

#### Stage 5: Verifier Synthesis

```
Claude Code:
  "Here is finding X.
   ATTACKER says: [attacker output]
   DEFENDER says: [defender output]
   You are the VERIFIER. Produce a verdict."
  → Task(subagent_type="vrs-verifier")
```

The verifier gets pre-digested context from both agents.

#### Stage 6: Report Generation

Claude Code generates a markdown report from the verdicts. No CLI tool needed.

```markdown
# Security Audit Report

## Findings

### [CRITICAL] Missing Access Control in setOwner()
**Location:** contracts/Vault.sol:42
**Verdict:** CONFIRMED (Confidence: 95%)
**Attack Path:** ...
**Recommendation:** ...
```

---

## Integration Fixes Needed

### Priority 1: Fix PatternEngine API (Enables `beads generate` and `query pattern:*`)

**File:** `src/alphaswarm_sol/queries/patterns.py`

**Changes:**
1. Add `pattern_dir` parameter to `PatternEngine.__init__`
2. Add `run_all_patterns(graph)` convenience method
3. Add `run_pattern(graph, pattern_id)` convenience method
4. Add `_load_patterns()` internal method

**Effort:** ~50 lines of code, ~2 hours
**Risk:** LOW — additive, doesn't break existing `.run()` method
**Test:** `uv run alphaswarm beads generate tests/contracts/NoAccessGate.sol`

### Priority 2: Fix DetectPatternsHandler (Enables orchestrate resume)

**File:** `src/alphaswarm_sol/orchestration/handlers.py`

**Changes:**
1. Line 378: `store.load()` → `store.load(graph_path / "graph.json")`
2. Line 389: Fixed by P1 above
3. Line 396: `m.pattern_id` → `m["pattern_id"]` (it's a dict, not object)

**Effort:** ~10 lines, ~30 minutes
**Risk:** LOW

### Priority 3: Fix `orchestrate resume` Infinite Loop

**File:** `src/alphaswarm_sol/orchestration/router.py` and/or `orchestration/loop.py`

**Root cause:** Router doesn't track which phases have completed. It keeps sending BUILD_GRAPH.

**Fix approach:** Router should check pool.metadata for phase completion markers (e.g., `graph_built`, `patterns_detected`) and route to the NEXT incomplete phase.

**Effort:** ~50-100 lines, ~4 hours
**Risk:** MEDIUM — needs careful state machine logic

### Priority 4: Fix CreateBeadsHandler (Enables bead creation from handlers)

**File:** `src/alphaswarm_sol/orchestration/handlers.py:462`

**Changes:** Match `VulnerabilityBead` constructor to actual schema.

**Effort:** ~20 lines, ~1 hour
**Risk:** LOW

### Priority 5: Curate Working Pattern Set

From the Pattern Audit (T2), only 172/557 patterns use real builder properties. Of those, only ~12 are proven.

**Action:** Create a `patterns/proven/` directory with the 6-12 patterns that are known to work. Use ONLY these for MVP.

**Known working patterns (from T2 report):**
- `vm-001` (weak-access-control — state modifying without access gate)
- `vm-002` (missing reentrancy guard)
- Various ordering lens patterns
- Oracle staleness patterns

**Effort:** ~4 hours (identify, copy, validate)
**Risk:** LOW

### Priority 6 (Post-MVP): Fix All Handler Agents

The SpawnAttackersHandler, SpawnDefendersHandler, RunDebateHandler all import agents that may not work. For MVP, Claude Code bypasses these entirely.

---

## The MVP Verification Test

### Test: `test_e2e_pipeline_mvp.py`

```python
"""
E2E test: Proves the MVP pipeline works end-to-end.

Input: NoAccessGate.sol (known vulnerable contract)
Expected: At least 1 finding about missing access control
"""
import json
import subprocess
from pathlib import Path

import pytest

from alphaswarm_sol.kg.builder import VKGBuilder
from alphaswarm_sol.kg.store import GraphStore
from alphaswarm_sol.queries.patterns import PatternEngine, PatternStore


# ================================================================
# STAGE 1: Build Graph (already works)
# ================================================================

def test_build_graph():
    """Build graph from known vulnerable contract."""
    target = Path("tests/contracts/NoAccessGate.sol")
    builder = VKGBuilder(target.parent)
    graph = builder.build(target)

    assert len(graph.nodes) > 0
    assert len(graph.edges) > 0

    # Save for next stages
    output_dir = Path("/tmp/vkg-e2e-test/graphs")
    output_dir.mkdir(parents=True, exist_ok=True)
    store = GraphStore(output_dir)
    store.save(graph, overwrite=True)


# ================================================================
# STAGE 2: Pattern Matching (requires Fix P1)
# ================================================================

def test_pattern_matching():
    """Run patterns against known vulnerable contract."""
    # Load graph
    store = GraphStore(Path("/tmp/vkg-e2e-test/graphs"))
    graph = store.load(Path("/tmp/vkg-e2e-test/graphs/graph.json"))

    # Load ONLY proven patterns
    # After P5, these will be in vulndocs/*/patterns/
    engine = PatternEngine()
    patterns = PatternStore.load_vulndocs_patterns(
        Path("vulndocs")
    )

    # Run matching
    matches = engine.run(graph, patterns, limit=100)

    # NoAccessGate.sol should match at least 1 access control pattern
    assert len(matches) > 0, "Expected at least 1 pattern match for NoAccessGate.sol"

    # Verify match structure
    match = matches[0]
    assert "pattern_id" in match
    assert "node_id" in match
    assert "severity" in match


# ================================================================
# STAGE 3: CLI Integration (requires Fix P1)
# ================================================================

def test_beads_generate_cli():
    """Test that `beads generate` CLI works."""
    result = subprocess.run(
        ["uv", "run", "alphaswarm", "beads", "generate",
         "tests/contracts/NoAccessGate.sol",
         "--vkg-dir", "/tmp/vkg-e2e-test/beads"],
        capture_output=True, text=True, timeout=120,
    )

    assert result.returncode == 0, f"beads generate failed: {result.stderr}"
    assert "Created" in result.stdout or "pattern matches" in result.stdout


# ================================================================
# STAGE 4: Query Integration (works today)
# ================================================================

def test_query_cli():
    """Test that query CLI finds vulnerabilities."""
    # Build graph first
    subprocess.run(
        ["uv", "run", "alphaswarm", "build-kg",
         "tests/contracts/NoAccessGate.sol",
         "--out", "/tmp/vkg-e2e-test/graphs"],
        capture_output=True, text=True, timeout=120,
    )

    # Query for access control issues
    result = subprocess.run(
        ["uv", "run", "alphaswarm", "query",
         "functions without access control",
         "--graph", "/tmp/vkg-e2e-test/graphs/graph.json"],
        capture_output=True, text=True, timeout=60,
    )

    assert result.returncode == 0, f"query failed: {result.stderr}"

    # Parse output
    output = json.loads(result.stdout)
    # Should find at least one function without access control
    assert output.get("results") or output.get("findings") or output.get("matches"), \
        f"Expected findings in output: {result.stdout[:500]}"


# ================================================================
# FULL PIPELINE: Complete E2E (requires all fixes)
# ================================================================

def test_full_pipeline_e2e():
    """Complete E2E: contract → graph → patterns → beads → report.

    This test proves the ENTIRE MVP pipeline works.
    Run with: pytest tests/test_e2e_pipeline.py::test_full_pipeline_e2e -v
    """
    import tempfile
    work_dir = Path(tempfile.mkdtemp(prefix="vkg-e2e-"))

    # 1. Build graph
    builder = VKGBuilder(Path("tests/contracts"))
    graph = builder.build(Path("tests/contracts/NoAccessGate.sol"))
    assert len(graph.nodes) > 0

    # 2. Run patterns
    engine = PatternEngine()
    patterns = PatternStore.load_vulndocs_patterns(Path("vulndocs"))
    matches = engine.run(graph, patterns)

    # 3. Verify at least one match for known vulnerable contract
    assert len(matches) >= 1, (
        f"NoAccessGate.sol should trigger at least 1 pattern. "
        f"Got {len(matches)} matches. "
        f"Patterns loaded: {len(patterns)}"
    )

    # 4. Verify match quality
    has_access_control_match = any(
        "access" in m.get("pattern_id", "").lower() or
        "auth" in m.get("pattern_id", "").lower() or
        "Ordering" in str(m.get("lens", []))
        for m in matches
    )
    assert has_access_control_match, (
        f"Expected an access control pattern match. "
        f"Got patterns: {[m.get('pattern_id') for m in matches]}"
    )

    print(f"\n✓ E2E PIPELINE PASSED")
    print(f"  Graph: {len(graph.nodes)} nodes, {len(graph.edges)} edges")
    print(f"  Matches: {len(matches)}")
    for m in matches[:5]:
        print(f"    - {m['pattern_id']} ({m['severity']}) on {m['node_label']}")
```

### Test Contract: `NoAccessGate.sol` (Already Exists)

This is the simplest possible vulnerable contract:
- Public function that modifies owner
- No access control modifier
- Should trigger `vm-001` (or similar) pattern

### CI Integration

```yaml
# In CI pipeline
- name: E2E Pipeline Test
  run: |
    uv run pytest tests/test_e2e_pipeline.py -v --timeout=300
```

---

## Updated /vrs-audit Skill

### What the Skill Should Actually Do

The skill should be a **step-by-step recipe for Claude Code**, not a wrapper around broken Python orchestration.

```markdown
# /vrs-audit — Step-by-Step Recipe

## Step 1: Validate Environment
- Check: `alphaswarm --version` works
- Check: `which slither` returns a path
- If either fails, tell user what to install

## Step 2: Build Knowledge Graph
- Run: `alphaswarm build-kg <contracts_path>`
- Read output to get graph path and stats
- If fails: report error, stop

## Step 3: Run Pattern Queries
- Run: `alphaswarm query "pattern:*" --graph .vrs/graphs/graph.json`
- Parse JSON output
- If no matches: report "no issues found", stop
- Count matches by severity

## Step 4: Read Source Code for Each Finding
- For each high/critical match:
  - Read the matched function source code
  - Read surrounding context (callers, state variables)
  - Build investigation context

## Step 5: Spawn Attacker Agent
- For each finding, use Task tool:
  - subagent_type: "vrs-attacker"
  - Provide: finding details + source code + graph properties
  - Ask: "Can this be exploited? Construct attack path."

## Step 6: Spawn Defender Agent
- For each finding, use Task tool:
  - subagent_type: "vrs-defender"
  - Provide: finding details + source code + graph properties
  - Ask: "What guards exist? Is this a false positive?"

## Step 7: Spawn Verifier Agent
- For findings with attacker/defender disagreement:
  - subagent_type: "vrs-verifier"
  - Provide: attacker opinion + defender opinion + evidence
  - Ask: "What's the verdict? Confidence level?"

## Step 8: Generate Report
- Aggregate all verdicts
- Generate markdown report
- Write to .vrs/reports/audit-report.md
- Display summary to user

## Step 9: Human Checkpoint
- List all findings that need review
- Ask user to confirm/reject each
```

### Claude Code Tools Used at Each Step

| Step | Claude Code Tool | What It Does |
|------|-----------------|--------------|
| 1 | `Bash(alphaswarm --version)` | Check installation |
| 1 | `Bash(which slither)` | Check slither |
| 2 | `Bash(alphaswarm build-kg ...)` | Build graph |
| 3 | `Bash(alphaswarm query ...)` | Pattern matching |
| 4 | `Read(source_file)` | Read vulnerable code |
| 5 | `Task(vrs-attacker)` | Spawn attacker agent |
| 6 | `Task(vrs-defender)` | Spawn defender agent |
| 7 | `Task(vrs-verifier)` | Spawn verifier agent |
| 8 | `Write(.vrs/reports/audit-report.md)` | Generate report |

### Failure Handling

| Failure | Recovery |
|---------|----------|
| alphaswarm not installed | Tell user: `uv tool install -e /path/to/alphaswarm` |
| slither not installed | Tell user: `uv tool install slither-analyzer` |
| build-kg fails | Check Solidity errors, solc version |
| No patterns match | Report: "No known vulnerability patterns detected" |
| Agent fails to spawn | Retry once, then skip agent and note in report |
| No findings | Report: "Clean — no issues found" (still a valid result) |

---

## Effort Estimate

### MVP (Contract → Report via Claude Code)

| Task | Effort | Priority | Blocks |
|------|--------|----------|--------|
| Fix PatternEngine API (P1) | 2 hours | P0 | Everything |
| Curate proven pattern set (P5) | 4 hours | P0 | Detection accuracy |
| Fix DetectPatternsHandler (P2) | 30 min | P1 | `orchestrate resume` |
| Write E2E test (this doc) | 3 hours | P0 | Proving it works |
| Rewrite /vrs-audit skill | 4 hours | P0 | User experience |
| Fix orchestrate resume loop (P3) | 4 hours | P1 | CLI flow |
| Fix CreateBeadsHandler (P4) | 1 hour | P2 | Bead persistence |
| **Total MVP** | **~18 hours** | | |

### Beyond MVP

| Task | Effort | Priority |
|------|--------|----------|
| Fix all handler agents (P6) | 8 hours | P2 |
| Property gap resolution (337 properties) | 40+ hours | P2 |
| VulnDocs validation fixes (74 entries) | 8 hours | P2 |
| Skill frontmatter migration (19 skills) | 2 hours | P1 |
| Real benchmark against known vulns | 16 hours | P1 |

---

## Key Insight: The MVP Doesn't Need Python Orchestration

The ExecutionLoop/Router/Handler system is ~6,400 LOC of orchestration infrastructure that has never worked. The MVP insight is:

**Claude Code already IS an orchestrator.** It can:
- Run CLI commands (Bash)
- Read/write files (Read/Write)
- Spawn subagents (Task)
- Manage state (task system)
- Coordinate multi-step workflows (skills)

We don't need Python to orchestrate Python-calling-agents. We need Python for what Python is good at: graph building, pattern matching, property computation. Let Claude Code handle the workflow.

### What Python Should Do
1. Build knowledge graphs (`build-kg`)
2. Run deterministic pattern matching (`query`)
3. Store beads and pools (persistence layer)
4. Generate reports (templates)

### What Claude Code Should Do
1. Orchestrate the pipeline (skill)
2. Spawn and coordinate agents (Task tool)
3. Synthesize findings (LLM reasoning)
4. Handle failures and human checkpoints

---

## Success Criteria

The MVP pipeline is **proven working** when:

1. `test_full_pipeline_e2e` passes
2. `NoAccessGate.sol` → at least 1 finding about missing access control
3. `ReentrancyClassic.sol` → at least 1 finding about reentrancy
4. A complete audit report is generated for a test contract
5. The `/vrs-audit` skill can be invoked and produces output

**Stretch goal:** Run against a real DeFi protocol (DamnVulnerableDeFi) and detect at least 3 known vulnerabilities.

---

*Plan completed: 2026-02-08*
