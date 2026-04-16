# W2-1: P0 Bug Fixes Plan

> **Status:** Investigation Complete
> **Confidence:** HIGH — All 4 bugs confirmed with exact root causes identified
> **Date:** 2026-02-08

---

## Bug 1: PatternEngine API Mismatch

### Root Cause

**Double API mismatch** between PatternEngine's actual signature and how 3 callers use it.

**Definition:** `src/alphaswarm_sol/queries/patterns.py:504`
```python
def __init__(self, tag_store: "TagStore | None" = None):
```

**Broken callers pass `pattern_dir=` which doesn't exist:**
| File | Line | Call |
|------|------|------|
| `src/alphaswarm_sol/orchestration/handlers.py` | 389 | `PatternEngine(pattern_dir=pattern_dir)` |
| `src/alphaswarm_sol/cli/main.py` | 905 | `PatternEngine(pattern_dir=pdir)` |
| `src/alphaswarm_sol/cli/beads.py` | 594 | `PatternEngine(pattern_dir=pdir)` |

**Additionally**, these callers invoke methods that don't exist on PatternEngine:
- `engine.run_all_patterns(graph)` — **does not exist** on PatternEngine
- `engine.run_pattern(graph, pattern)` — **does not exist** on PatternEngine

PatternEngine only has `engine.run(graph, patterns, ...)` which takes an explicit `list[PatternDefinition]`.

**Working callers** (for comparison) instantiate correctly:
- `src/alphaswarm_sol/orchestration/runner.py:184` — `PatternEngine()` (no kwargs)
- `src/alphaswarm_sol/queries/executor.py:274` — `PatternEngine().run(...)` (correct API)
- `src/alphaswarm_sol/beads/types.py:646` — `PatternEngine()` (no kwargs)

### Fix

**Option A (Recommended): Update PatternEngine to accept `pattern_dir`**
Add `pattern_dir` parameter to `__init__` and implement `run_all_patterns()` and `run_pattern()` methods. These methods should load patterns from the directory and delegate to `run()`.

```python
# patterns.py:504
def __init__(self, tag_store: "TagStore | None" = None, pattern_dir: Path | None = None):
    self._tag_store = tag_store
    self._pattern_dir = pattern_dir

def run_all_patterns(self, graph: KnowledgeGraph) -> list[dict]:
    patterns = load_patterns(self._pattern_dir)  # Load from dir or default
    return self.run(graph, patterns)

def run_pattern(self, graph: KnowledgeGraph, pattern_id: str) -> list[dict]:
    patterns = load_patterns(self._pattern_dir)
    matching = [p for p in patterns if p.id == pattern_id]
    return self.run(graph, matching)
```

**Option B:** Fix callers to use the existing API. This requires pattern loading logic in each caller, duplicating code.

**Recommendation:** Option A. Centralizes pattern loading in the engine where it belongs.

### Test

```bash
# 1. Unit test PatternEngine with pattern_dir
uv run pytest tests/ -k "test_pattern_engine" -v

# 2. Integration test via CLI
uv run alphaswarm beads generate tests/contracts/Vault.sol --dry-run

# 3. Integration test via orchestrate handlers
# (Requires orchestrate resume fix first)
```

### Effort
2-3 hours (includes implementing `run_all_patterns`, `run_pattern`, `load_patterns`, and tests)

---

## Bug 2: Orchestrate Resume Infinite Loop

### Root Cause

**Fundamental state machine design flaw:** Handlers don't advance pool status, and the completion check mechanism can never detect phase completion for INTAKE phase.

**The infinite loop sequence:**

1. Pool starts in `PoolStatus.INTAKE`
2. Router (`router.py:131-132`) maps `INTAKE → BUILD_GRAPH`
3. `BuildGraphHandler.__call__()` (`handlers.py:198-266`) builds the graph successfully
4. Handler sets `pool.metadata["graph_built"] = True` but **never changes pool.status** (line 252-256)
5. Handler returns `PhaseResult(success=True, phase=LoopPhase.INTAKE)` — no checkpoint
6. Queue-based execution path (`loop.py:752-781`) processes the item and calls `continue`
7. Loop reloads pool — status still `INTAKE`
8. Router returns `BUILD_GRAPH` again → **infinite loop**

**Why _try_advance_phase can't help:**
- `_try_advance_phase` calls `_phase_complete()` (line 896)
- `_phase_complete()` (line 908-921) calls `router.route(pool)` and checks if action is `WAIT`
- Router always returns `BUILD_GRAPH` for `INTAKE` status — it never checks metadata
- So `_phase_complete` always returns `False` for INTAKE → never advances

**The deeper issue:** The router is purely status-based (line 131 `PHASE_ROUTES` dict). It doesn't check metadata like `graph_built`. So even after a handler succeeds, the router gives the same routing decision.

### Fix

**Two-part fix required:**

**Part 1: Router must check handler completion metadata**

```python
# router.py, in route() method, before the PHASE_ROUTES fallback
# Add metadata-aware routing for simple phases:
if pool.status == PoolStatus.INTAKE:
    if pool.metadata.get("graph_built"):
        return RouteDecision(action=RouteAction.WAIT, reason="Graph built, ready to advance")
    return RouteDecision(action=RouteAction.BUILD_GRAPH, reason="Need to build graph")

if pool.status == PoolStatus.CONTEXT:
    if pool.metadata.get("context_loaded"):
        return RouteDecision(action=RouteAction.WAIT, reason="Context loaded, ready to advance")
    return RouteDecision(action=RouteAction.LOAD_CONTEXT, reason="Need context")

if pool.status == PoolStatus.BEADS:
    if pool.metadata.get("beads_created"):
        return RouteDecision(action=RouteAction.WAIT, reason="Beads created, ready to advance")
    return RouteDecision(action=RouteAction.CREATE_BEADS, reason="Need beads")
```

**Part 2: Each handler must set a completion flag in metadata** (most already do, but verify all).

**Affected files:**
- `src/alphaswarm_sol/orchestration/router.py:143-181` — route() method
- `src/alphaswarm_sol/orchestration/handlers.py` — all handlers (verify metadata flags)

### Test

```bash
# 1. Unit test: Router returns WAIT after BUILD_GRAPH completes
# Create pool with metadata["graph_built"]=True, verify router returns WAIT

# 2. Integration test: Full loop advances through phases
# Create pool → run loop → verify it advances INTAKE→CONTEXT→BEADS→...

# 3. Regression test: Loop doesn't exceed N iterations for same phase
# Add assertion: same phase action should not repeat > 2 times
```

### Effort
4-6 hours (router changes + verify all handlers set flags + integration tests)

---

## Bug 3: 19 Skills with Broken Frontmatter

### Root Cause

19 skill files in `.claude/skills/` use `skill:` as the frontmatter key instead of `name:`. Claude Code requires `name:` in YAML frontmatter for skill registration.

**Working examples** (in subdirectories) use `name:`:
```yaml
---
name: vrs-audit
description: ...
---
```

**Broken files** use `skill:`:
```yaml
---
skill: vrs-audit
description: ...
---
```

### All 19 Broken Files

| # | File | Current `skill:` value |
|---|------|----------------------|
| 1 | `.claude/skills/vrs-run-validation.md` | `vrs-run-validation` |
| 2 | `.claude/skills/vrs-workflow-test.md` | `vrs-workflow-test` |
| 3 | `.claude/skills/vrs-audit.md` | `vrs-audit` |
| 4 | `.claude/skills/vrs-environment.md` | `vrs-environment` |
| 5 | `.claude/skills/vrs-checkpoint.md` | `vrs-checkpoint` |
| 6 | `.claude/skills/vrs-full-testing.md` | `vrs-full-testing` |
| 7 | `.claude/skills/vrs-strict-audit.md` | `vrs-strict-audit` |
| 8 | `.claude/skills/vrs-validate-phase.md` | `vrs-validate-phase` |
| 9 | `.claude/skills/vrs-rollback.md` | `vrs-rollback` |
| 10 | `.claude/skills/vrs-component.md` | `vrs-component` |
| 11 | `.claude/skills/vrs-claude-code-agent-teams-testing.md` | `vrs-claude-code-agent-teams-testing` |
| 12 | `.claude/skills/enforce-testing-rules.md` | `enforce-testing-rules` |
| 13 | `.claude/skills/vrs-claude-code-agent-teams-runner.md` | `vrs-claude-code-agent-teams-runner` |
| 14 | `.claude/skills/vrs-agentic-testing.md` | `vrs-agentic-testing` |
| 15 | `.claude/skills/vrs-parallel.md` | `vrs-parallel` |
| 16 | `.claude/skills/vrs-resume.md` | `vrs-resume` |
| 17 | `.claude/skills/vrs-status.md` | `vrs-status` |
| 18 | `.claude/skills/vrs-select.md` | `vrs-select` |
| 19 | `.claude/skills/vrs-evaluate-workflow.md` | `vrs-evaluate-workflow` |

**Note:** Some of these are duplicates of skills that also exist in subdirectories (e.g., `vrs-audit.md` flat file vs `vrs-audit/SKILL.md` directory). These flat-file versions may be legacy and should be checked for content parity.

### Fix

Simple sed replacement across all 19 files:
```bash
for f in .claude/skills/vrs-run-validation.md \
         .claude/skills/vrs-workflow-test.md \
         .claude/skills/vrs-audit.md \
         .claude/skills/vrs-environment.md \
         .claude/skills/vrs-checkpoint.md \
         .claude/skills/vrs-full-testing.md \
         .claude/skills/vrs-strict-audit.md \
         .claude/skills/vrs-validate-phase.md \
         .claude/skills/vrs-rollback.md \
         .claude/skills/vrs-component.md \
         .claude/skills/vrs-claude-code-agent-teams-testing.md \
         .claude/skills/enforce-testing-rules.md \
         .claude/skills/vrs-claude-code-agent-teams-runner.md \
         .claude/skills/vrs-agentic-testing.md \
         .claude/skills/vrs-parallel.md \
         .claude/skills/vrs-resume.md \
         .claude/skills/vrs-status.md \
         .claude/skills/vrs-select.md \
         .claude/skills/vrs-evaluate-workflow.md; do
    sed -i '' 's/^skill:/name:/' "$f"
done
```

**Follow-up investigation needed:** Check if these 19 flat files are duplicates of the subdirectory versions (e.g., `.claude/skills/vrs-audit.md` vs `.claude/skills/vrs-audit/SKILL.md`). If duplicates, consider removing the flat files entirely.

### Test

```bash
# 1. Grep to verify no remaining `skill:` frontmatter
grep -r "^skill:" .claude/skills/*.md  # Should return empty

# 2. Verify Claude Code sees the skills
# In Claude Code session: type "/vrs-" and check autocomplete shows all skills

# 3. Invoke one to verify it loads
# /vrs-audit or /vrs-run-validation
```

### Effort
0.5 hours (mechanical find-and-replace + verification)

---

## Bug 4: VulnDocs Validation — All 74 Entries Fail

### Root Cause

**Schema-data mismatch.** The pydantic schema `VulnDocIndex` (`schema.py:841-960`) requires fields that don't exist in any `index.yaml` entry, and the entries use different field names than the schema expects.

**Schema requires (all mandatory with `...`):**

| Required Field | Schema Location | Present in Entries? |
|---------------|-----------------|---------------------|
| `id` | schema.py:866 | YES |
| `category` | schema.py:867 | NO — entries use `parent_category` |
| `subcategory` | schema.py:868 | NO — not present at all |
| `severity` | schema.py:869 | NO — entries have `severity_range` (list) instead |
| `vulndoc` | schema.py:870-872 | NO — not present at all |

**Example entry** (`vulndocs/reentrancy/classic/index.yaml`):
```yaml
id: classic
name: Classic Reentrancy           # Not in schema
parent_category: reentrancy        # Schema expects: category
# Missing: subcategory, severity, vulndoc
severity_range:                    # Schema expects: severity (single value)
  - high
  - critical
```

**Pydantic raises ValidationError** for every entry due to 4 missing required fields. All 74 entries have this exact same structural mismatch.

**Additional failure mode:** Some entries (e.g., `access-control/delegatecall-control`, `arithmetic/incorrect-overflow-check`) have multiple `---` YAML document separators, which causes `yaml.safe_load()` to fail with "expected a single document in the stream" before pydantic even runs.

### Fix

**Option A (Recommended): Update schema to match existing data format**

The entries are actually well-structured and contain valuable information. The schema should be updated to match reality:

```python
class VulnDocIndex(BaseModel):
    # Keep required
    id: str = Field(...)

    # Rename to match entries
    parent_category: str = Field(..., alias="parent_category")  # was: category
    name: str | None = Field(None)

    # Make severity flexible
    severity_range: list[Severity] = Field(default_factory=list)  # was: severity (required)

    # Remove vulndoc requirement (can be derived from path)
    vulndoc: str | None = Field(None)  # was: required

    # Remove subcategory requirement (derived from folder name)
    subcategory: str | None = Field(None)

    # Keep category as alias for parent_category for backward compat
    category: str | None = Field(None)

    @model_validator(mode="after")
    def normalize_category(self) -> "VulnDocIndex":
        """Accept both parent_category and category."""
        if not self.category and self.parent_category:
            self.category = self.parent_category
        return self
```

**Option B:** Update all 74 index.yaml files to match the schema. This is higher effort and risks breaking other consumers.

**Recommendation:** Option A. The entries are the ground truth. Fix the schema to match.

### Test

```bash
# 1. Run validation after fix
uv run alphaswarm vulndocs validate vulndocs/

# Expected: majority of entries should reach at least MINIMAL level

# 2. Unit test the schema with a real entry
# Parse reentrancy/classic/index.yaml through VulnDocIndex.model_validate()

# 3. Integration test: validate full framework
uv run pytest tests/ -k "test_vulndocs_validation" -v
```

### Effort
3-4 hours (schema update + validator adjustments + testing)

---

## Additional P0 Issues Found

### P0-5: `--scope` Flag Documented But Missing

**Location:** CLAUDE.md documents `uv run alphaswarm orchestrate start pool-id --scope contracts/`

**Reality:** `orchestrate start` command (`cli/orchestrate.py:386-488`) takes a **positional `path` argument**, not `--scope`:
```
def start_audit(
    path: str = typer.Argument(..., help="Path to Solidity project"),
```

**Additionally, the documented syntax is wrong in two ways:**
1. `pool-id` is the first positional arg in docs but in CLI it's `path` — pool-id is optional `--pool-id`
2. `--scope` doesn't exist — the path IS the scope

**Correct usage:** `uv run alphaswarm orchestrate start ./contracts --pool-id my-audit`

**Fix:** Update CLAUDE.md Quick Commands section. Replace:
```
uv run alphaswarm orchestrate start pool-id --scope contracts/
```
With:
```
uv run alphaswarm orchestrate start contracts/             # Start audit
uv run alphaswarm orchestrate start contracts/ --pool-id my-audit  # With custom pool ID
uv run alphaswarm orchestrate resume <pool-id>             # Resume from checkpoint
```

**Effort:** 15 minutes

### P0-6: Deprecated `google-generativeai` Dependency

**Location:** `pyproject.toml:23` — `"google-generativeai>=0.8.0"` (top-level dependency)

**Used by:** `src/alphaswarm_sol/llm/providers/google.py:7` — `import google.generativeai as genai`

**Issue:** The library uses the deprecated `google.generativeai` module which triggers a `FutureWarning` on every import. The warning fires on **every CLI command** because Python processes the dependency graph at import time.

**This is NOT a P0 but a P1** — it's annoying but doesn't break functionality. The warning appears even for commands that don't use the Google provider.

**Fix options:**
1. **Lazy import** — Move the `import google.generativeai` inside the GoogleProvider class methods instead of module-level. This prevents the warning for commands that don't use Google.
2. **Migrate to `google-genai`** — The new official package that replaces `google-generativeai`.
3. **Suppress warning** — `warnings.filterwarnings("ignore", category=FutureWarning, module="google")` — band-aid.

**Recommendation:** Option 1 (lazy import) for now, migrate to `google-genai` in a later milestone.

**Effort:** 30 minutes

### P0-7: Handlers Call Nonexistent PatternEngine Methods (Broader Impact)

The PatternEngine API mismatch (Bug 1) also affects:

- `orchestration/handlers.py:389-390` — `DetectPatternsHandler` (same area as BuildGraph)
- The `run_all_patterns()` method doesn't exist, meaning the entire CONTEXT phase after graph building would also crash

This means **even if Bug 2 (infinite loop) were fixed, the pipeline would crash immediately at the CONTEXT/BEADS phase** when it tries to detect patterns. Bugs 1 and 2 are thus compounding — fixing only one won't unblock the pipeline.

---

## Implementation Order

```
Priority  Bug   Reasoning                                  Blocks
────────  ────  ─────────────────────────────────────────  ──────────
1st       #3    Fastest fix, immediate user impact          Nothing
2nd       #1    Unblocks pattern detection for pipeline     #2
3rd       #2    Unblocks full audit pipeline                #1, #4
4th       #4    Unblocks knowledge base for patterns        #2
5th       #5    Docs fix (CLAUDE.md)                       Nothing
6th       #6    Quality of life (lazy import)              Nothing
```

**Rationale:**
- **Bug 3 first** — 19 broken skills is the most visible user-facing breakage. 15 minutes to fix, immediate impact.
- **Bug 1 second** — PatternEngine API mismatch blocks both `beads generate` CLI and the orchestrate pipeline handlers.
- **Bug 2 third** — Router infinite loop prevents the entire orchestrate workflow. Depends on Bug 1 being fixed (otherwise it would advance to the next phase and crash on patterns).
- **Bug 4 fourth** — VulnDocs validation affects the knowledge base that patterns reference. Can be done in parallel with Bug 2.
- **Bugs 5-6** — Docs and warnings. Low effort, do alongside other fixes.

---

## Total Effort Estimate

| Bug | Effort | Complexity |
|-----|--------|-----------|
| #1: PatternEngine API | 2-3 hours | Medium — API design + implementation |
| #2: Infinite Loop | 4-6 hours | High — State machine redesign |
| #3: Skill Frontmatter | 0.5 hours | Trivial — Find and replace |
| #4: VulnDocs Schema | 3-4 hours | Medium — Schema redesign + migration |
| #5: CLAUDE.md docs | 0.25 hours | Trivial — Text edit |
| #6: Google warning | 0.5 hours | Trivial — Lazy import |
| **Total** | **10.25-14.25 hours** | |

**Critical path:** Bug 3 → Bug 1 → Bug 2 → Bug 4 (serial dependency for pipeline)

**Parallel opportunity:** Bug 4 (schema fix) can run in parallel with Bug 2 (router fix) since they touch different subsystems. Bugs 5 and 6 can happen anytime.

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| PatternEngine API change breaks existing callers | The 8 callers that use `PatternEngine()` correctly (no args) will still work. New `pattern_dir` param is optional. |
| Router metadata checks miss edge cases | Add explicit tests for every phase transition. Add a max-same-action counter as safety net. |
| Schema change breaks downstream consumers | The schema change makes fields optional, so any code that already handles None will work. Run full test suite. |
| Duplicate skill files (flat + directory) cause confusion | Investigate content parity and remove duplicates after frontmatter fix. |
