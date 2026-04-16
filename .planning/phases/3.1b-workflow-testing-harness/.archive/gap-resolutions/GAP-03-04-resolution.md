# GAP-03 & GAP-04 Resolution

**Date:** 2026-02-12
**Investigator:** Claude Code (Opus 4.6)
**Status:** Resolution complete, ready for integration into context.md

---

## 1. Codebase Investigation

### Plan Files Found

All 3.1b plans are defined inline in `context.md` (not separate plan files), except:
- `.planning/phases/3.1b-workflow-testing-harness/01-PLAN.md` -- detailed execution plan for Companion bridge
- `.planning/phases/3.1b-workflow-testing-harness/01-EXPECTED.md` -- expected outcomes for Companion bridge

### Declared Dependencies Between 3.1b Plans

Extracted from `context.md` lines:

| Plan | Declared Dependencies | Actual Critical Path? |
|------|----------------------|----------------------|
| 3.1b-01 (Companion) | None | NO -- zero 3.1c BLOCKING consumers |
| 3.1b-02 (Parser+Collector) | None | YES -- 3.1c-03, 3.1c-04, 3.1c-07, 3.1c-08 all block on this |
| 3.1b-03 (Hooks) | None | YES -- 3.1c-02 blocks on this (already DONE) |
| 3.1b-04 (Agent Teams) | "Depends on 3.1b-01, 3.1b-02, 3.1b-03" | YES -- 3.1c-05, 3.1c-11 block on this |
| 3.1b-05 (DSL) | "Depends on 3.1b-04" | YES -- 3.1c-08 blocks on this |
| 3.1b-06 (Corpus) | "No 3.1b plan dependency" | YES -- 3.1c-09/10/11 block on this |
| 3.1b-07 (Smoke Test) | "Depends on 3.1b-01 through 3.1b-06" | YES -- 3.1c start gate |

### 3.1c Companion Dependency Analysis

Searched `.planning/phases/3.1c-reasoning-evaluation-framework/context.md` for "companion" and "Companion":

- Line 1304: Lists "companion bridge" as a 3.1b dependency in general terms
- Line 1323: Notes Companion as "secondary automation tool"
- **Line 1621: `Companion bridge (REST+WS) for secondary automation | 3.1c-12 Regression baseline N-trial runs | NICE-TO-HAVE`**

This is the critical finding: **Companion is explicitly marked NICE-TO-HAVE in the 3.1c exit gate requirements table.** Every other 3.1b deliverable is marked **YES** (blocking). Companion is the ONLY non-blocking item.

No 3.1c plan (01 through 12) declares a hard dependency on `CompanionBridge` or `CompanionSession`. The only consumer is 3.1c-12 (regression baseline), and even there it is optional -- CLI-based automation via `ClaudeOneShot` or direct Claude Code session management could substitute.

### 3.1b-04 False Dependency on 3.1b-01

The declared dependency chain is: `3.1b-04 depends on 3.1b-01, 3.1b-02, 3.1b-03`.

Examining what 3.1b-04 actually needs from 3.1b-01:
- `01-EXPECTED.md` line 78: "3.1b-04 | provides -> | CompanionSession for multi-turn team testing automation"
- But 3.1b-04's actual content is about Agent Teams (TeamCreate, SendMessage, TeamDelete) -- these are Claude Code native features, not Companion features
- TeamManager spawns teams via Claude Code's Agent Teams API, not via Companion sessions
- The Companion dependency appears to be about _automating_ team tests later, not about the team framework itself

**Conclusion:** 3.1b-04's dependency on 3.1b-01 is a NICE-TO-HAVE automation enhancement, not a hard technical prerequisite. The TeamManager can be built and tested interactively without Companion.

---

## 2. GAP-03 Resolution: Execution Ordering

### Current Order (from context.md)

```
01 -> 02 -> 03 -> 04 -> 05 -> 06 -> 07
                    ^
                    |
           04 depends on 01, 02, 03
           05 depends on 04
           07 depends on 01-06
```

### Problem

Plan 01 (Companion) is first but has ZERO blocking 3.1c consumers. If it hits issues:
- It delays 02 (critical -- parser/collector)
- It delays 04 (via false dependency)
- It blocks the entire critical path for no benefit

### Revised Dependency Graph

After removing the false 01 dependency from 04:

```
                    02 (parser+collector)  ---+
                                              |
03 (hooks) [DONE] -------------------------+--> 04 (Agent Teams)
                                              |       |
06 (corpus) [independent] ----+               |       v
                               |              |    05 (DSL)
                               |              |       |
01 (Companion) [independent] --+--------------+-------+
                               |                      |
                               +-------> 07 (smoke) <-+
```

### Proposed Wave Execution

#### Wave 1: Foundation (parallel, start immediately)

| Plan | Rationale | Risk | Status |
|------|-----------|------|--------|
| 3.1b-02 (Parser+Collector) | Highest 3.1c impact: 4 blocking consumers (3.1c-03, 04, 07, 08) | LOW -- well-defined scope, existing code to extend | Not started |
| 3.1b-03 (Hooks) | 1 blocking consumer (3.1c-02) | NONE -- already DONE (iterations 1-2 complete) | DONE |
| 3.1b-06 (Corpus) | 3 blocking consumers (3.1c-09, 10, 11), declared independent | MEDIUM -- Solidity compilation, ground truth authoring | Not started |

**Why parallel:** Zero inter-dependencies. 02 modifies `transcript_parser.py`, 03 modifies `workspace.py` (done), 06 creates new files in `examples/testing/`. No file conflicts.

**Wave 1 exit gate:** TranscriptParser extended (02), hooks verified (03, done), 10 scenarios compile (06).

#### Wave 2: Team Framework (sequential after Wave 1)

| Plan | Rationale | Actual Dependencies | Risk |
|------|-----------|-------------------|------|
| 3.1b-04 (Agent Teams) | 2 blocking consumers (3.1c-05, 3.1c-11) | 02 (parser for transcript analysis), 03 (hooks for observation) | MEDIUM -- live team spawning, SendMessage verification |

**Why sequential:** Needs TranscriptParser (from 02) for transcript analysis of team sessions. Needs hook infrastructure (from 03, done) for observation. Does NOT need Companion.

**Wave 2 exit gate:** TeamManager lifecycle works, SendMessage captured, debrief documented.

#### Wave 3: Scenario DSL (sequential after Wave 2)

| Plan | Rationale | Actual Dependencies | Risk |
|------|-----------|-------------------|------|
| 3.1b-05 (DSL) | 1 blocking consumer (3.1c-08) | 04 (team framework for team-aware scenarios) | LOW -- YAML schema extension |

**Why sequential:** EvaluationGuidance needs to reference team-aware fields from 04. Could potentially run in Wave 2 parallel with 04 if team-specific DSL fields are deferred, but the coupling is tight enough that sequential is safer.

**Wave 3 exit gate:** Scenarios load with EvaluationGuidance, `evaluation:` slot accepted.

#### Wave 4: Companion (parallel with Waves 2-3, or deferred)

| Plan | Rationale | Actual Dependencies | Risk |
|------|-----------|-------------------|------|
| 3.1b-01 (Companion) | 0 blocking 3.1c consumers (NICE-TO-HAVE for 3.1c-12 only) | None | MEDIUM -- external dependency (bun, Companion versions) |

**Why parallel/deferred:** Can start any time. Does not block anything. Can be executed alongside Waves 2-3 by a separate work session, or deferred entirely until 3.1c-12 needs it.

**Wave 4 exit gate:** Companion bridge importable, REST+WS verified (if executed).

#### Wave 5: Integration Smoke Test (sequential after all)

| Plan | Rationale | Actual Dependencies | Risk |
|------|-----------|-------------------|------|
| 3.1b-07 (Smoke Test) | 3.1c start gate | All prior plans | LOW -- integration only |

**Modification:** If Companion (01) is deferred, the smoke test should test infrastructure WITHOUT Companion and document what's missing. The smoke test exit gate should have a "with Companion" and "without Companion" variant.

**Wave 5 exit gate (minimum):** Interactive evaluation loop completes without Companion. All non-Companion infrastructure exercised.

### Visual Summary

```
Time --->

Wave 1:  [02: Parser+Collector] [06: Corpus]      [03: DONE]
Wave 2:          [04: Agent Teams]
Wave 3:                  [05: DSL]
Wave 4:  [01: Companion -------- optional, any time --------]
Wave 5:                          [07: Smoke Test]
```

### Fallback Plan: Companion Deferred Entirely

If Companion is deferred to post-3.1b:

1. **3.1b-07 smoke test** runs without Companion automation -- uses interactive Claude Code session + ClaudeOneShot CLI for simple verification
2. **3.1c-12 regression baseline** uses `ClaudeOneShot` for N-trial runs instead of `CompanionSession` multi-turn. Less capable (no multi-turn memory, no skill invocation) but functional for basic regression
3. **Companion bridge** becomes a 3.1c or Phase 4 enhancement when multi-turn automation is truly needed
4. **No blocking impact** on any 3.1c plan (confirmed by 3.1c exit gate table)

**Risk of deferral:** Regression runs in 3.1c-12 are slightly less capable. Multi-turn skill testing (e.g., running `/vrs-audit` via automation) requires Companion. But 3.1c-12 is the LAST plan in 3.1c, so there is ample time to build Companion before it is needed.

### Risk Assessment Per Wave

| Wave | Risk Level | Primary Risk | Mitigation |
|------|-----------|-------------|------------|
| 1 | LOW | Parser extension breaks existing 20 tests | Run existing test suite after every change; backward-compat is a hard gate |
| 1 | MEDIUM | Corpus Solidity compilation issues | Use solc 0.8.x for all contracts; verify compilation in CI |
| 2 | MEDIUM | Agent Teams behavior is underdocumented | Research spikes 02+03 are complete; empirical findings reduce risk |
| 3 | LOW | YAML schema extension is mechanical | Existing ScenarioLoader is well-tested |
| 4 | MEDIUM | Companion version mismatch, bun dependency | External dep -- isolate behind skip markers |
| 5 | LOW | Integration only -- components already tested | Run incrementally, not all-at-once |

---

## 3. GAP-04 Resolution: TranscriptParser Extension Mechanism

### Current State Analysis

**File:** `./tests/workflow_harness/lib/transcript_parser.py`

**Class structure:**
- `__init__` takes a `Path` to a JSONL file
- `_records: list[dict[str, Any]]` -- populated by `_load()`, stores raw parsed JSONL lines
- `_tool_calls: list[ToolCall] | None` -- lazy cache, populated by `_extract_tool_calls()`
- 12 public methods + 2 properties (see full list in context.md)
- No factory, no subclasses, no abstract methods, no plugin system

**Instantiation patterns (5 call sites):**
1. `tests/workflow_harness/test_transcript_parser.py` -- direct `TranscriptParser(path)` (13 times)
2. `tests/workflow_harness/test_assertions.py` -- direct `TranscriptParser(path)` (1 time)
3. `tests/workflow_harness/conftest.py` -- direct `TranscriptParser(jsonl_file)` in fixture (1 time)

All instantiation is direct constructor calls. No factory, no DI container, no configuration.

**Imports (5 files):**
1. `lib/__init__.py` -- re-exports `ToolCall, TranscriptParser`
2. `lib/assertions.py` -- imports `TranscriptParser`
3. `conftest.py` -- imports `TranscriptParser`
4. `test_assertions.py` -- imports `TranscriptParser`
5. `test_transcript_parser.py` -- imports `TranscriptParser, ToolCall`

**`_records` structure:**
Each record is a parsed JSON line from Claude Code's JSONL transcript format:
```python
{
    "type": "assistant" | "user" | "progress" | "file-history-snapshot",
    "message": {
        "content": [
            {"type": "text", "text": "..."},
            {"type": "tool_use", "id": "...", "name": "Bash", "input": {...}},
            {"type": "tool_result", "tool_use_id": "...", "content": "..."}
        ]
    }
}
```

### Extension Options Evaluated

#### Option A: Direct Method Addition (RECOMMENDED)

Add new methods directly to `TranscriptParser` class in the same file.

**Pros:**
- Simplest. Python-idiomatic. No new concepts.
- All callers already import `TranscriptParser` -- no import changes needed.
- `_records` access is trivial (same class).
- Existing lazy cache pattern (`_tool_calls`) is naturally extensible.
- 3.1c methods follow exact same pattern as existing methods.

**Cons:**
- File grows (currently 225 LOC, would grow to ~300-350 LOC).
- 3.1b and 3.1c changes are in the same file (merge risk if parallel development).
- No formal extension point -- just "add methods."

#### Option B: Subclass (TranscriptParserV2 or EvaluationParser)

Create a subclass in a new file that adds 3.1c methods.

**Pros:**
- Clean separation of 3.1b vs 3.1c code.
- Could use `super().__init__()` to inherit all existing behavior.
- 3.1c changes don't touch 3.1b files.

**Cons:**
- All existing callers would need to be updated to use the subclass -- OR callers stick with base class and miss new methods.
- Factory pattern needed to choose which class to instantiate.
- Conftest fixture would need to change.
- `_records` access works (inheritance), but feels over-engineered for adding 4 methods.
- Violates YAGNI -- there is no scenario requiring multiple parser variants.

#### Option C: Mixin (TranscriptParserGraphMixin, TranscriptParserDebriefMixin)

Define mixin classes that 3.1c composes into a combined class.

**Pros:**
- Clean separation by concern (graph analysis, debrief, observation).
- Composable -- pick which mixins you need.

**Cons:**
- Python mixin patterns are fragile (MRO issues, `_records` access requires careful `self` typing).
- Over-engineered for 4 methods.
- No precedent in this codebase.
- All callers would still need to change to the composed class.

### Recommendation: Option A (Direct Method Addition)

**Confidence: HIGH**

Rationale:
1. The class is 225 LOC with 12 methods -- adding 4 more is proportional, not bloating.
2. Every method follows the same pattern: iterate `_records` or `_tool_calls`, filter, return structured data.
3. Zero callers use a factory or DI -- all use `TranscriptParser(path)` directly.
4. No foreseeable need for multiple parser variants.
5. The file is in `tests/` (not shipped code), so API stability concerns are lower.
6. 3.1c explicitly says "3.1c will ADD the following extension methods" -- not "create a subclass."

### API Stability Contract for `_records`

#### Contract

```python
class TranscriptParser:
    # STABILITY CONTRACT (3.1b-02)
    #
    # _records is a STABLE internal attribute:
    # - Type: list[dict[str, Any]]
    # - Each dict is a parsed JSONL line from Claude Code transcript
    # - Records are in chronological order (same as file order)
    # - Records are read-only after __init__ completes
    # - Extension methods MAY read _records but MUST NOT mutate it
    #
    # If _records must change (type, structure, access pattern),
    # the change MUST be coordinated with 3.1c plans that depend on it.
    #
    # Guaranteed record fields:
    #   "type": str  -- "assistant", "user", "progress", "file-history-snapshot"
    #   "message": dict  -- contains "content" list of content blocks
    #
    # Content block types within message.content:
    #   "text": {"type": "text", "text": str}
    #   "tool_use": {"type": "tool_use", "id": str, "name": str, "input": dict}
    #   "tool_result": {"type": "tool_result", "tool_use_id": str, "content": str|list}

    _records: list[dict[str, Any]]
```

#### Accessor Alternative

If the team later wants to formalize access, add a read-only property:

```python
@property
def records(self) -> list[dict[str, Any]]:
    """Raw JSONL records (read-only). Stable API for extension methods."""
    return list(self._records)  # defensive copy
```

This is NOT recommended for now because:
- Every 3.1c extension is in the same class (direct `self._records` access)
- A defensive copy on every call wastes memory for large transcripts
- The private convention `_records` with documentation is sufficient

### Naming Conventions for New Methods

Follow existing patterns:

| Pattern | Examples (existing) | New methods (3.1c) |
|---------|-------------------|-------------------|
| `get_*()` returns data | `get_tool_calls()`, `get_tool_sequence()`, `get_bash_commands()` | `get_text_between_tools()`, `get_graph_queries()`, `get_messages()`, `get_raw_messages()` |
| `has_*()` returns bool | `has_tool_call()`, `has_bskg_query()` | (none planned) |
| `*_index()` returns int | `bskg_query_index()`, `first_conclusion_index()` | (none planned) |
| `first_*()` returns single | `first_tool_call()` | (none planned) |
| `*_matching()` returns filtered list | `tool_calls_matching()` | (none planned) |

New method naming rules:
1. Use `get_` prefix for data retrieval methods
2. Use `has_` prefix for boolean existence checks
3. Use `_index` suffix for position-returning methods
4. Return `list` for multi-item results, `T | None` for single-item results
5. No abbreviations -- full names (`get_text_between_tools`, not `get_txt_btwn`)

### Version Compatibility Approach

#### Recommendation: Docstring version tags, NOT a class attribute

Instead of `API_VERSION = "3.1b"` (which is fragile and requires coordination):

```python
class TranscriptParser:
    """Parse a Claude Code JSONL transcript for tool-level analysis.

    API Surface:
        Phase 3.1b (baseline): get_tool_calls, get_tool_sequence, get_bash_commands,
            has_tool_call, first_tool_call, tool_calls_matching, has_bskg_query,
            bskg_query_index, first_conclusion_index, get_raw_messages,
            get_message_at, get_messages_between, record_count, total_chars
        Phase 3.1c additions: get_text_between_tools, get_debrief_response,
            get_graph_queries, get_messages

    Extension contract:
        - _records (list[dict]) is stable and read-only after init
        - New methods follow get_*/has_*/*_index naming convention
        - All methods are additive (never remove or change existing signatures)
    """
```

**Why not a class attribute:**
- A version string implies semver-like compatibility guarantees that are overkill for a test infrastructure class
- No code should branch on parser version -- if a method exists, use it; if not, it hasn't been added yet
- `hasattr(parser, 'get_text_between_tools')` is a more Pythonic way to check for new methods than version comparison

#### Compatibility Testing

When 3.1c adds methods, run the full existing test suite:

```bash
uv run pytest tests/workflow_harness/test_transcript_parser.py -v
```

If all ~20 existing tests pass, backward compatibility is confirmed. This is already called out in 3.1b-02's exit gate and drift detection.

### Concrete 3.1b-02 Implementation Steps for Extension Readiness

1. **Add `_records` stability contract** as a docstring block (see contract above)
2. **Add the 3 planned 3.1b methods:** `get_raw_messages()`, `get_message_at()`, `get_messages_between()`
3. **Add 2 new fields to `ToolCall`:** `timestamp: float | None = None`, `duration_ms: float | None = None`
4. **Add docstring API surface listing** with phase tags
5. **Do NOT add 3.1c methods yet** -- those are added by 3.1c-04/05 following the same pattern
6. **Run all existing tests** after changes to verify backward compatibility

### What 3.1c Will Do (for reference, not 3.1b scope)

3.1c-04 will add to `TranscriptParser`:
```python
def get_text_between_tools(self) -> list[str]:
    """Extract reasoning text from assistant messages between tool_use blocks."""
    # Iterates self._records, extracts text blocks between tool_use blocks
    ...

def get_graph_queries(self) -> list[ToolCall]:
    """Filter tool calls for BSKG-related Bash commands."""
    # Wraps tool_calls_matching with alphaswarm command detection
    ...

def get_messages(self) -> list[dict]:
    """All assistant text content blocks."""
    # Iterates self._records where type=="assistant", extracts text blocks
    ...
```

3.1c-05 will add:
```python
def get_debrief_response(self) -> dict | None:
    """Parse structured debrief JSON from the last assistant message(s)."""
    # Scans tail of self._records for debrief JSON pattern
    ...
```

All follow the same pattern: iterate `_records`, filter, return structured data. No new infrastructure needed.

---

## 4. Integration Notes: How to Update context.md

### For GAP-03 (Plan Ordering)

1. **Update the dependency declaration in 3.1b-04** (context.md line 518):
   - FROM: "Depends on 3.1b-01 (Companion bridge), 3.1b-02 (parser/collector), 3.1b-03 (hooks)."
   - TO: "Depends on 3.1b-02 (parser/collector), 3.1b-03 (hooks). Companion (3.1b-01) is a NICE-TO-HAVE for automation."

2. **Update the dependency declaration in 3.1b-07** (context.md line 772):
   - FROM: "Depends on 3.1b-01 through 3.1b-06 -- all prior plans must be complete."
   - TO: "Depends on 3.1b-02 through 3.1b-06. Companion (3.1b-01) is optional -- smoke test has a with/without-Companion variant."

3. **Add a "Wave Execution Order" section** after the Plans heading (context.md line 214):
   ```markdown
   ### Execution Order (Revised per GAP-03)

   Wave 1 (parallel): 02 (parser+collector) + 03 (hooks, DONE) + 06 (corpus)
   Wave 2 (sequential): 04 (Agent Teams) -- needs 02, 03
   Wave 3 (sequential): 05 (DSL) -- needs 04
   Wave 4 (parallel/deferred): 01 (Companion) -- independent, 0 blocking 3.1c consumers
   Wave 5 (sequential): 07 (smoke test) -- needs 02-06, optionally 01
   ```

4. **Update 01-EXPECTED.md Cross-Plan Dependencies table** to mark the 3.1b-04 relationship as NICE-TO-HAVE.

### For GAP-04 (Extension Mechanism)

1. **Add `_records` stability contract** to the existing TranscriptParser docstring in `tests/workflow_harness/lib/transcript_parser.py`
2. **Add API surface listing** with phase tags to class docstring
3. **Add a paragraph to 3.1b-02 plan section** (context.md around line 366):
   ```markdown
   **Extension pattern:** Direct method addition to TranscriptParser class.
   3.1c adds methods following get_*/has_*/*_index naming conventions.
   _records is a stable internal attribute (documented contract in class docstring).
   No subclassing, no mixins, no factory pattern needed.
   ```

---

## 5. Confidence Assessment

| Item | Confidence | Rationale |
|------|-----------|-----------|
| GAP-03: Companion has 0 blocking 3.1c consumers | **HIGH** | Directly confirmed by 3.1c exit gate table (line 1621): "NICE-TO-HAVE" |
| GAP-03: 3.1b-04 false dependency on 3.1b-01 | **HIGH** | 3.1b-04 builds TeamManager using Claude Code Agent Teams API, not Companion. Companion is for scripted automation of known-good tests. |
| GAP-03: Proposed wave ordering is safe | **HIGH** | Verified each wave's dependencies are satisfied by prior waves. 03 is already done. 06 has no dependencies. |
| GAP-03: Companion can be deferred entirely | **HIGH** | 3.1c-12 (the only consumer) can use ClaudeOneShot as fallback. Cost: less capable regression runs. |
| GAP-04: Direct method addition is correct pattern | **HIGH** | All 5 call sites use direct construction. No factory, no subclasses exist. Class is 225 LOC -- proportional growth. 3.1c context explicitly says "add methods." |
| GAP-04: `_records` stability contract is sufficient | **HIGH** | `_records` is populated once in `_load()`, never mutated afterward. All methods read it. Documented contract + existing test coverage is sufficient. |
| GAP-04: No version attribute needed | **MEDIUM** | `hasattr` checks are more Pythonic than version comparison. But if teams want explicit version gating, the attribute is trivial to add later. |
| GAP-04: Naming conventions will be followed | **HIGH** | Existing 12 methods establish a clear pattern. 3.1c context already uses the correct names. |
