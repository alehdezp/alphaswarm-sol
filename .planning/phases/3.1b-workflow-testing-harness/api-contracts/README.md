# API Contracts: 3.1b -> 3.1c Interface Specifications

Phase 3.1b produces infrastructure that Phase 3.1c consumes. This directory
contains explicit Python type signatures for every 3.1c-facing API, ensuring
no ambiguity during implementation.

## Quick Reference

| Contract | File | Key Types | 3.1c Consumers | 3.1b Plan |
|----------|------|-----------|-----------------|-----------|
| Transcript Parser | [transcript-parser.md](transcript-parser.md) | `ToolCall`, `BSKGQuery`, `TranscriptParser` extensions | 3.1c-03, 3.1c-04, 3.1c-05, 3.1c-07, 3.1c-08 | 3.1b-02 |
| Observation Models | [observation-models.md](observation-models.md) | `AgentObservation`, `TeamObservation`, `CollectedOutput`, `OutputCollector`, `EvaluationGuidance` | 3.1c-01, 3.1c-03, 3.1c-07, 3.1c-08, 3.1c-10, 3.1c-11 | 3.1b-02, 3.1b-04, 3.1b-05 |
| Hooks & Workspace | [hooks-and-workspace.md](hooks-and-workspace.md) | `WorkspaceManager.install_hooks()`, `HookConfig`, `.vrs/observations/` convention, Jujutsu workspace API | 3.1c-02, 3.1c-05, 3.1c-12 | 3.1b-03, 3.1b-04 |
| Scenario DSL | [scenario-dsl.md](scenario-dsl.md) | `evaluation:` block, `evaluation_guidance:` block, `post_run_hooks:`, grader schemas | 3.1c-06, 3.1c-07, 3.1c-08, 3.1c-09, 3.1c-10, 3.1c-11 | 3.1b-05 |
| Dependency Matrix | [dependency-matrix.md](dependency-matrix.md) | N/A (mapping document) | All 3.1c plans | N/A |

## Parse vs Execute Boundary

A fundamental rule for all contracts:

- **3.1b PARSES and STORES** data structures (schema validation, loading, field access)
- **3.1c EXECUTES and INTERPRETS** the data (running evaluators, scoring, judging)

For example, the `evaluation:` block in scenario YAML is parsed and preserved by 3.1b's
scenario loader. 3.1c implements the execution logic that reads that block and triggers
the evaluation pipeline.

## Backward Compatibility Rules

1. **Existing `ToolCall` constructors must not break.** New fields (`timestamp`, `duration_ms`) must have defaults.
2. **`TranscriptParser._records` must remain accessible.** It is private but stable; 3.1c-04 reads it.
3. **`get_tool_calls()` return type must not change.** It returns `list[ToolCall]` with the same fields.
4. **`WorkspaceManager.install_hooks()` signature must remain compatible** with the current `extra_hooks` parameter.
5. **`ScenarioConfig` must accept new optional fields** without breaking existing YAML files.
6. **`EventStream` and `ControllerEvent`** must not change existing method signatures.

## Scoring Scale

All evaluation scores use **0-100 integer scale** (canonical). If any 3.1b code uses
0.0-1.0 float scale internally, the boundary conversion happens in 3.1c.

## Document Conventions

Each contract document includes:
1. Python type signature (dataclass or class definition)
2. Field descriptions with types
3. 3.1c consumer(s) that depend on this contract
4. Example usage snippet
5. Backward compatibility notes
6. Failure mode behavior (edge cases)
