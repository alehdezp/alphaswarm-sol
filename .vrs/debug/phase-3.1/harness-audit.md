# Workflow Harness Audit for 3.1b Readiness

**Date:** 2026-02-11
**Plan:** 3.1-03
**Purpose:** Assess `tests/workflow_harness/` (12 files, 1810 LOC) for 3.1b infrastructure readiness

---

## File Inventory

| # | File | LOC | Purpose | Status |
|---|------|-----|---------|--------|
| 1 | `__init__.py` | 0 | Package marker | OK |
| 2 | `conftest.py` | 48 | Pytest fixtures (workspace_manager, event_stream_factory, transcript_parser_factory) | Functional, has a minor issue |
| 3 | `lib/__init__.py` | 13 | Library re-exports (ControllerEvent, EventStream, ToolCall, TranscriptParser, WorkspaceManager) | OK |
| 4 | `lib/assertions.py` | 241 | 7-category composable assertion functions | Functional |
| 5 | `lib/controller_events.py` | 159 | ControllerEvent dataclass + EventStream query class | Functional |
| 6 | `lib/transcript_parser.py` | 224 | JSONL transcript parser with tool call extraction | Functional |
| 7 | `lib/workspace.py` | 156 | Per-scenario workspace setup/teardown manager | Functional |
| 8 | `hooks/log_session.py` | 53 | Hook script for session metadata capture | Functional |
| 9 | `test_assertions.py` | 359 | Tests for all 7 assertion categories | Passing (91 tests total with other test files) |
| 10 | `test_controller_events.py` | 200 | Tests for ControllerEvent and EventStream | Passing |
| 11 | `test_transcript_parser.py` | 236 | Tests for TranscriptParser | Passing |
| 12 | `test_workspace.py` | 121 | Tests for WorkspaceManager | Passing |

**Total:** 12 files, 1810 LOC, 91 tests passing

---

## Per-File Assessment

### 1. `conftest.py` (48 LOC)

**Purpose:** Provides 3 fixtures: `workspace_manager`, `event_stream_factory`, `transcript_parser_factory`.

**Issue:** The `transcript_parser_factory` fixture has `import json` inside the factory closure (line 47) rather than at module top level. This is functional but unconventional. The `EXAMPLES_DIR` constant points to `examples/testing/` which currently has 11 project dirs.

**3.1b Relevance:** Fixtures will need expansion for controller bridge (3.1b-02) and scenario DSL (3.1b-04). The `run_scenario` fixture mentioned in the docstring is still a placeholder -- not yet implemented.

### 2. `lib/assertions.py` (241 LOC)

**Purpose:** 16 composable assertion functions across 7 categories.

**Categories:**
1. Agent Lifecycle (4): `assert_agent_spawned`, `assert_agent_exited_cleanly`, `assert_spawn_order`, `assert_min_agents`
2. Tool Sequence (3): `assert_tool_sequence`, `assert_tool_used`, `assert_bash_command_ran`
3. Graph-First Compliance (1): `assert_graph_first`
4. Evidence Validity (2): `assert_findings_have_locations`, `assert_findings_cite_graph_nodes`
5. Task State Machine (2): `assert_task_completed`, `assert_all_tasks_completed`
6. Performance Bounds (2): `assert_duration_between`, `assert_cost_nonzero`
7. Anti-Fabrication (1): `assert_not_fabricated` (composite)

**Assessment:** Well-structured, composable. Each assertion function takes the appropriate harness object (EventStream or TranscriptParser) as input and produces clear failure messages.

**Gap:** No assertion for evaluation-contract-aware validation. When 3.1c-06 defines capability contracts, the assertions library will need a `assert_capability_met(parser, contract)` function. Assign to **3.1b-06** or **3.1c-06**.

### 3. `lib/controller_events.py` (159 LOC)

**Purpose:** `ControllerEvent` dataclass with `from_dict()` class method + `EventStream` query class.

**Assessment:** Handles both camelCase and snake_case event keys (e.g., `agent_id` / `agentId`, `agent_type` / `agentType` / `subagent_type`). Good defensive design. Query methods cover all 7 controller event types.

**Methods:** `of_type`, `agents_spawned`, `agents_exited`, `messages`, `tasks_completed`, `results`, `errors`, `agent_ids`, `agent_types`, `agent_by_type`, `events_for_agent`, `events_between`, `duration_seconds`, `total_cost_usd`, `has_event`, `first_event`, `last_event` (17 methods).

**Gap:** No `SendMessage` content extraction method. 3.1b API contract specifies `SendMessage` content access for inter-agent message verification. Assign to **3.1b-02**.

### 4. `lib/transcript_parser.py` (224 LOC)

**Purpose:** Parses Claude Code JSONL transcripts, extracts `ToolCall` objects with tool names, inputs, and results.

**Assessment:** Core functionality is solid. Handles tool_use/tool_result correlation via `id_to_call` mapping. Result truncation at 500 chars.

**Methods:** `get_tool_calls`, `get_tool_sequence`, `get_bash_commands`, `has_tool_call`, `first_tool_call`, `tool_calls_matching`, `has_bskg_query`, `bskg_query_index`, `first_conclusion_index`, `record_count`, `total_chars` (11 methods).

**Gap:** Missing `get_tool_calls()` returning `ToolCall` with full result (not truncated). 3.1c evaluation needs full tool results for LLM-based grading. Also missing methods for extracting reasoning text between tool calls. Assign to **3.1b-02** (API contract: TranscriptParser extensibility).

### 5. `lib/workspace.py` (156 LOC)

**Purpose:** Per-scenario workspace management: hook installation, artifact cleanup, session info reading, transcript path mapping.

**Assessment:** Installs `log_session.py` hook into workspace's `.claude/hooks/`, writes `settings.json` with hook registrations. Uses `_ensure_hook` helper to avoid duplication.

**Methods:** `setup`, `install_hooks`, `get_session_info`, `get_transcript_paths`, `cleanup` (5 methods).

**Gap:** No `.claude/` sandbox copying from parent project. 3.1b API contract specifies that test scenarios need the project's skills and agent definitions copied into the sandbox workspace. Currently only hooks are copied. Assign to **3.1b-03**.

### 6. `hooks/log_session.py` (53 LOC)

**Purpose:** Hook script installed into test workspaces. Captures SubagentStop and Stop events, appends to `.vrs/testing/session.json`.

**Assessment:** Simple, correct. Reads stdin JSON, appends event with timestamp to session.json. Handles missing files and JSON decode errors gracefully.

**Gap:** Only captures `agent_id`, `agent_transcript_path`, and `session_id`. Does not capture `SendMessage` content or agent model used. For 3.1c debrief evaluation, richer event capture may be needed. Assign to **3.1b-05** (hooks).

### 7-10. Test Files

| Test File | LOC | Test Count (approx) | Coverage |
|-----------|-----|---------------------|----------|
| `test_assertions.py` | 359 | ~35 | All 16 assertion functions, positive and negative cases |
| `test_controller_events.py` | 200 | ~20 | ControllerEvent.from_dict, all EventStream query methods |
| `test_transcript_parser.py` | 236 | ~20 | JSONL parsing, tool extraction, graph-first helpers |
| `test_workspace.py` | 121 | ~16 | Setup, cleanup, hook install, session info, transcript paths |

**Assessment:** Test coverage is good for current functionality. Tests use in-memory fixtures (no real controller needed). All 91 tests pass.

**Gap:** No integration test that runs the full harness pipeline (workspace setup -> simulate controller events -> parse transcript -> run assertions). Only unit tests exist. This is acceptable for current Phase 3.1 but should be addressed in **3.1b-06** (integration testing).

---

## Identified Gaps Summary

| # | Gap | Severity | Assigned To |
|---|-----|----------|------------|
| 1 | No `run_scenario` fixture (controller bridge missing) | High | 3.1b-02 |
| 2 | No `SendMessage` content extraction in EventStream | Medium | 3.1b-02 |
| 3 | TranscriptParser result truncation (500 chars) prevents full eval | Medium | 3.1b-02 |
| 4 | No reasoning text extraction between tool calls | Medium | 3.1b-02 |
| 5 | No `.claude/` sandbox copying in WorkspaceManager | High | 3.1b-03 |
| 6 | No capability-contract-aware assertion function | Medium | 3.1c-06 |
| 7 | Hook captures limited event fields | Low | 3.1b-05 |
| 8 | No integration test for full harness pipeline | Medium | 3.1b-06 |
| 9 | `conftest.py` has misplaced `import json` in closure | Low | 3.1b-02 |

**Overall Assessment:** The harness provides a solid foundation (1810 LOC, 91 passing tests, 7 assertion categories, clean architecture). The primary gaps are all expected -- they correspond to infrastructure that 3.1b is explicitly designed to deliver. The harness is ready to be built upon, not ready to support real workflow testing as-is.
