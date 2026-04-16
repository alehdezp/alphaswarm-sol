# Dependency Matrix: 3.1c Plans -> 3.1b API Contracts

Every 3.1c plan maps to specific 3.1b API contracts. No plan should have
unresolved "TBD" references. Implementers can look up exactly which APIs
they need.

## Matrix

| 3.1c Plan | Name | Required 3.1b Contract | API Surface | 3.1b Implementing Plan | Status |
|-----------|------|------------------------|-------------|------------------------|--------|
| 3.1c-01 | Assessment Data Structures | observation-models.md | `EvaluationGuidance` field names (for alignment), `CollectedOutput` field names | 3.1b-02, 3.1b-05 | stub |
| 3.1c-01 | Assessment Data Structures | scenario-dsl.md | `EvaluationConfig.run_gvs`, `EvaluationConfig.run_reasoning` (field name alignment) | 3.1b-05 | stub |
| 3.1c-02 | Observation Hooks + Writer | hooks-and-workspace.md | `WorkspaceManager.install_hooks(hook_configs=list[HookConfig])`, `_ensure_hook()`, `.vrs/observations/` convention, `ObservationRecord` JSONL schema | 3.1b-03 (DONE), 3.1b-04 | partial |
| 3.1c-03 | Observation Parser | transcript-parser.md | `ToolCall.timestamp`, `ToolCall.duration_ms`, `TranscriptParser.get_tool_calls()`, `TranscriptParser._records` | 3.1b-02 | stub |
| 3.1c-03 | Observation Parser | observation-models.md | `CollectedOutput.tool_sequence`, `CollectedOutput.duration_ms` | 3.1b-02 | stub |
| 3.1c-04 | Graph Value Scorer | transcript-parser.md | `BSKGQuery` dataclass, `TranscriptParser.get_bskg_queries()`, `TranscriptParser.graph_citation_rate()`, `TranscriptParser._records`, `TranscriptParser.get_raw_messages()`, `TranscriptParser.get_messages_between()` | 3.1b-02 | stub |
| 3.1c-05 | Debrief Protocol | hooks-and-workspace.md | `HookConfig` with `event_type="TeammateIdle"` and `event_type="TaskCompleted"`, `_ensure_hook()` exit code 2 semantics, `CapturedMessage.content` (full body) | 3.1b-03 (DONE), 3.1b-04 | partial |
| 3.1c-05 | Debrief Protocol | transcript-parser.md | `TranscriptParser.get_raw_messages()` (Layer 4 fallback — transcript analysis) | 3.1b-02 | stub |
| 3.1c-05 | Debrief Protocol | observation-models.md | `InboxMessage` dataclass, `AgentObservation.messages_sent`, `AgentObservation.messages_received` | 3.1b-02 | stub |
| 3.1c-06 | Evaluation Contracts | scenario-dsl.md | `EvaluationConfig` schema (to validate contract YAML structure), `modes`, `team_config` | 3.1b-05 | stub |
| 3.1c-06 | Evaluation Contracts | observation-models.md | `EvaluationGuidance` field names (for contract dimension alignment) | 3.1b-02 | stub |
| 3.1c-07 | Reasoning Evaluator | observation-models.md | `CollectedOutput` (full run data as evaluator input), `TeamObservation` (for team evaluation context), `EvaluationGuidance.reasoning_questions` | 3.1b-02 | stub |
| 3.1c-07 | Reasoning Evaluator | transcript-parser.md | `TranscriptParser.get_bskg_queries()` (for graph usage assessment), `BSKGQuery.cited_in_conclusion` | 3.1b-02 | stub |
| 3.1c-07 | Reasoning Evaluator | scenario-dsl.md | `EvaluationGuidanceConfig.reasoning_questions` (per-scenario evaluator prompting) | 3.1b-05 | stub |
| 3.1c-08 | Evaluation Runner | scenario-dsl.md | `ScenarioConfig.evaluation` (triggers evaluation pipeline), `ScenarioConfig.post_run_hooks` (invoked after run), `ScenarioConfig.graders` | 3.1b-05 | stub |
| 3.1c-08 | Evaluation Runner | observation-models.md | `OutputCollector.collect()` -> `CollectedOutput` (runner input), `TeamObservation` | 3.1b-02 | stub |
| 3.1c-08 | Evaluation Runner | hooks-and-workspace.md | `.vrs/observations/{session_id}.jsonl` (observation file path convention) | 3.1b-03 (DONE) | partial |
| 3.1c-09 | Skill Capability Tests | scenario-dsl.md | `ScenarioConfig` with `evaluation`, `evaluation_guidance`, `graders`, `trials` fields | 3.1b-05 | stub |
| 3.1c-09 | Skill Capability Tests | observation-models.md | `OutputCollector.collect()` -> `CollectedOutput`, `EvaluationGuidance` | 3.1b-02, 3.1b-05 | stub |
| 3.1c-09 | Skill Capability Tests | transcript-parser.md | `TranscriptParser` full API (tool calls, BSKG queries) | 3.1b-02 | stub |
| 3.1c-10 | Agent Capability Tests | observation-models.md | `AgentObservation`, `TeamObservation.get_agent_by_type()`, `InboxMessage` | 3.1b-02, 3.1b-04 | stub |
| 3.1c-10 | Agent Capability Tests | hooks-and-workspace.md | `CapturedMessage.content` (full SendMessage body for debrief), Jujutsu workspace isolation | 3.1b-04 | stub |
| 3.1c-10 | Agent Capability Tests | transcript-parser.md | `TranscriptParser.get_bskg_queries()` (graph-first compliance), `BSKGQuery` | 3.1b-02 | stub |
| 3.1c-11 | Orchestrator Flow Tests | observation-models.md | `TeamObservation.cross_agent_evidence_flow()`, `TeamObservation.debate_turns()`, `EvidenceFlowEdge`, `DebateTurn` | 3.1b-02, 3.1b-04 | stub |
| 3.1c-11 | Orchestrator Flow Tests | hooks-and-workspace.md | `CapturedMessage` (full SendMessage content), `SubagentStop` with `transcript_path` | 3.1b-04 | stub |
| 3.1c-11 | Orchestrator Flow Tests | scenario-dsl.md | `ScenarioConfig.modes: ["team"]`, `ScenarioConfig.team_config` | 3.1b-05 | exists |
| 3.1c-12 | Improvement Loop + Regression | hooks-and-workspace.md | `WorkspaceManager.create_workspace()`, `forget_workspace()`, `rollback()`, `list_workspaces()` (Jujutsu sandbox isolation) | 3.1b-04 | stub |
| 3.1c-12 | Improvement Loop + Regression | scenario-dsl.md | `ScenarioConfig.trials` (for pass@k computation), `ScenarioConfig.evaluation` | 3.1b-05 | stub |
| 3.1c-12 | Improvement Loop + Regression | observation-models.md | `CollectedOutput` (for baseline metrics), `EvaluationGuidance.hooks_if_failed` | 3.1b-02, 3.1b-05 | stub |

## Status Legend

| Status | Meaning |
|--------|---------|
| **stub** | API specified in contract but not yet implemented in code |
| **partial** | Some functionality exists (e.g., 3.1b-03 DONE), but extensions needed |
| **exists** | Already implemented in current codebase |

**Post-3.1b status (2026-02-13):** All APIs listed as "stub" or "partial" above are now
**implemented and tested** (280 passing tests, 25 contract stubs all PASS). The "stub"
labels reflect the status at contract creation time (3.1b-08, Wave 0), not current state.
See `3.1b-VERIFICATION.md` for evidence.

## Coverage Summary

All 12 3.1c plans have explicit API contract mappings:
- **3.1c-01:** 2 contracts (observation-models, scenario-dsl)
- **3.1c-02:** 1 contract (hooks-and-workspace)
- **3.1c-03:** 2 contracts (transcript-parser, observation-models)
- **3.1c-04:** 1 contract (transcript-parser)
- **3.1c-05:** 3 contracts (hooks-and-workspace, transcript-parser, observation-models)
- **3.1c-06:** 2 contracts (scenario-dsl, observation-models)
- **3.1c-07:** 3 contracts (observation-models, transcript-parser, scenario-dsl)
- **3.1c-08:** 3 contracts (scenario-dsl, observation-models, hooks-and-workspace)
- **3.1c-09:** 3 contracts (scenario-dsl, observation-models, transcript-parser)
- **3.1c-10:** 3 contracts (observation-models, hooks-and-workspace, transcript-parser)
- **3.1c-11:** 3 contracts (observation-models, hooks-and-workspace, scenario-dsl)
- **3.1c-12:** 3 contracts (hooks-and-workspace, scenario-dsl, observation-models)

**No 3.1c plan references an unspecified 3.1b API.**

## 3.1b Plan -> Contract Ownership

| 3.1b Plan | Contracts Owned | Key Types |
|-----------|-----------------|-----------|
| 3.1b-02 | transcript-parser.md, observation-models.md (core types) | `ToolCall`, `BSKGQuery`, `TranscriptParser` extensions, `AgentObservation`, `TeamObservation`, `CollectedOutput`, `OutputCollector` |
| 3.1b-03 | hooks-and-workspace.md (hook infrastructure) | `HookConfig`, `_ensure_hook()`, `.vrs/observations/` convention |
| 3.1b-04 | hooks-and-workspace.md (Jujutsu), observation-models.md (TeamObservation integration) | `create_workspace()`, `forget_workspace()`, `rollback()`, `InboxMessage` (canonical; `CapturedMessage` is deprecated alias) |
| 3.1b-05 | scenario-dsl.md, observation-models.md (EvaluationGuidance) | `EvaluationConfig`, `EvaluationGuidanceConfig`, `post_run_hooks`, `graders`, `trials`, `EvaluationGuidance` |
