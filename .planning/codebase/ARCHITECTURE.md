# Architecture

**Analysis Date:** 2026-02-04

## Pattern Overview

**Overall:** Multi-Agent Orchestration Framework for Security Analysis

**Key Characteristics:**
- Claude Code acts as the orchestrator, not a CLI tool consumer
- Knowledge graph-first reasoning with behavioral signatures
- Multi-agent verification through attacker/defender/verifier debate
- Evidence-linked findings with proof tokens
- Staged audit pipeline with orchestration markers

## Layers

**Orchestration Layer (Claude Code):**
- Purpose: Coordinate the 9-stage audit pipeline via skills and subagents
- Location: `.claude/skills/`, `.claude/agents/`
- Contains: Skills (WHAT to do), agent definitions (WHO does it), workflow contracts
- Depends on: TaskCreate/TaskUpdate tools, CLI via Bash, subagent spawn
- Used by: End users running `/vrs-audit` or other VRS skills

**Knowledge Graph Layer:**
- Purpose: Build and query Behavioral Security Knowledge Graph (BSKG)
- Location: `src/alphaswarm_sol/kg/`
- Contains: Graph builder (~9,500 LOC), query engine, operations, semantic labeling
- Depends on: Slither AST/IR, TOON serialization
- Used by: Pattern engine, agents, CLI query commands

**Pattern Detection Layer:**
- Purpose: Match 680+ vulnerability patterns (Tier A/B/C) against BSKG
- Location: `vulndocs/` (686 YAML patterns), `src/alphaswarm_sol/vulndocs/`
- Contains: Pattern definitions, matching engine, rating system
- Depends on: BSKG properties and operations
- Used by: Audit orchestrator, detection workflows

**Tool Integration Layer:**
- Purpose: Normalize and deduplicate findings from external static analyzers
- Location: `src/alphaswarm_sol/tools/`
- Contains: 7 tool adapters (Slither, Aderyn, Mythril, etc.), coordinator, SARIF normalization
- Depends on: External tool installations (Slither, Aderyn, etc.)
- Used by: Audit initialization, tool comparison workflows

**Agent Infrastructure Layer:**
- Purpose: Spawn and manage specialized investigation agents
- Location: `src/alphaswarm_sol/agents/`
- Contains: 24 agent definitions, runtime (multi-SDK execution), propulsion (routing), ranking
- Depends on: Anthropic API, OpenAI API, Google Gemini API
- Used by: Orchestrator via Task tool, multi-agent debate

**Investigation Layer (Beads & Pools):**
- Purpose: Package findings into trackable, evidence-linked work units
- Location: `src/alphaswarm_sol/beads/`, `src/alphaswarm_sol/orchestration/`
- Contains: Bead schemas, pool management, debate protocol, verdict synthesis
- Depends on: BSKG evidence, agent outputs
- Used by: Verification workflows, report generation

**Testing & Validation Layer:**
- Purpose: Self-test Claude Code orchestration via claude-code-controller
- Location: `src/alphaswarm_sol/testing/`, `.planning/testing/`
- Contains: claude-code-agent-teams harness, evidence packs, full testing orchestrator, validation rules
- Depends on: claude-code-controller, external ground truth (Code4rena, SmartBugs)
- Used by: Phase 7.3.* GA validation

**CLI & Commands Layer:**
- Purpose: Tools called BY Claude Code, not by users directly
- Location: `src/alphaswarm_sol/cli/`
- Contains: Command definitions (build-kg, query, vulndocs, tools, orchestrate)
- Depends on: All underlying layers
- Used by: Claude Code via Bash tool

## Data Flow

**Build Phase:**

1. User invokes Claude Code with `/vrs-audit contracts/`
2. Claude Code (orchestrator) emits `[PREFLIGHT_PASS]` after validating environment
3. Claude Code calls `alphaswarm build-kg contracts/` via Bash
4. Slither parses Solidity → AST, CFG, IR
5. VKGBuilder processes contracts → 50+ properties per function
6. Semantic operations extracted (TRANSFERS_VALUE_OUT, CHECKS_PERMISSION, etc.)
7. Behavioral signatures computed (R:bal -> X:out -> W:bal)
8. Graph serialized to `.vrs/graphs/*.toon` with TOON format
9. Graph hash computed for integrity verification
10. Claude Code emits `[GRAPH_BUILD_SUCCESS]` marker

**Context Phase:**

1. Claude Code uses Exa MCP to research protocol type
2. Protocol context pack created (economic incentives, trust boundaries, attack vectors)
3. Context stored in `.vrs/context/` directory
4. Claude Code emits `[CONTEXT_READY]` marker

**Detection Phase:**

1. Claude Code calls `alphaswarm tools run` for external analyzers
2. Tool adapters normalize findings to SARIF
3. Deduplication engine merges equivalent findings across tools
4. Claude Code emits `[TOOLS_COMPLETE]` marker
5. Pattern engine matches BSKG against 680+ patterns (Tier A/B/C)
6. Candidates filtered by confidence thresholds
7. TaskCreate called per candidate finding (creates bead)
8. Claude Code emits `[DETECTION_COMPLETE]` marker

**Verification Phase:**

1. Beads grouped into pools for batch processing
2. Claude Code spawns subagent (attacker) via Task tool
3. Attacker queries BSKG, constructs exploit path
4. Attacker returns evidence packet (graph node IDs, code locations)
5. Claude Code spawns defender subagent
6. Defender queries BSKG, finds guards/mitigations
7. Defender returns evidence packet
8. Claude Code spawns verifier subagent
9. Verifier cross-checks attacker vs defender evidence
10. Verifier returns verdict (confirmed/likely/uncertain/rejected)
11. TaskUpdate called with verdict and evidence
12. Verdict synthesized and bead status updated

**Report Phase:**

1. Verdicts aggregated by confidence bucket
2. Evidence chains validated (graph nodes → code locations → findings)
3. Report generated with file:line references
4. Claude Code emits `[REPORT_GENERATED]` marker
5. Progress state saved to `.vrs/state/current.yaml`
6. Claude Code emits `[PROGRESS_SAVED]` marker

**State Management:**
- BSKG graph persists across sessions (`.vrs/graphs/*.toon`)
- Progress state persists across sessions (`.vrs/state/current.yaml`)
- Beads and pools track work items across agents
- Worktrees isolate test runs with snapshots for resume

## Key Abstractions

**Behavioral Signature:**
- Purpose: Compact operation sequence representing function behavior
- Examples: `src/alphaswarm_sol/kg/operations.py`, pattern definitions in `vulndocs/`
- Pattern: Operation codes (R:bal, W:bal, X:out) ordered by execution flow

**Semantic Operation:**
- Purpose: Normalize function behavior independent of names
- Examples: TRANSFERS_VALUE_OUT, READS_USER_BALANCE, CHECKS_PERMISSION
- Pattern: Extracted during graph build, matched by patterns

**Evidence Packet:**
- Purpose: LLM-friendly bundle linking finding to graph nodes and code
- Examples: `src/alphaswarm_sol/beads/schemas.py`, agent outputs
- Pattern: Graph node IDs + properties + source locations + operation sequences

**Bead:**
- Purpose: Self-contained investigation package (atomic work unit)
- Examples: `src/alphaswarm_sol/beads/`, `src/alphaswarm_sol/orchestration/schemas.py`
- Pattern: ID, status, vulnerability class, location, evidence, verdict

**Pool:**
- Purpose: Batch of related beads for coordinated workflow
- Examples: `src/alphaswarm_sol/orchestration/pool.py`
- Pattern: Pool ID, bead list, routing state, debate protocol

**Proof Token:**
- Purpose: Non-fakeable evidence of actual execution
- Examples: `src/alphaswarm_sol/testing/proof_tokens.py`
- Pattern: Graph hash, timestamps, node counts, VQL queries executed, findings with evidence

**Skill:**
- Purpose: Guide Claude Code behavior (describes WHAT to do)
- Examples: `.claude/skills/vrs-audit/`, `.claude/skills/vrs-verify/`
- Pattern: Markdown with triggers, context, procedures, tools to use

**Subagent:**
- Purpose: Isolated Claude Code context for scope-limited investigation
- Examples: `.claude/agents/vrs-attacker/`, `.claude/agents/vrs-defender/`
- Pattern: Agent definition with role, scope, tools, termination conditions

## Entry Points

**User-Facing (via Claude Code):**
- Location: `.claude/skills/vrs-audit/SKILL.md`
- Triggers: User types `/vrs-audit contracts/` in Claude Code
- Responsibilities: Orchestrate 9-stage pipeline, spawn subagents, synthesize findings

**Developer-Facing (CLI called by Claude Code):**
- Location: `src/alphaswarm_sol/cli/main.py`
- Triggers: Claude Code calls `alphaswarm <command>` via Bash
- Responsibilities: Execute CLI commands (build-kg, query, vulndocs, tools, orchestrate)

**Graph Builder Entry:**
- Location: `src/alphaswarm_sol/kg/builder.py` (VKGBuilder class)
- Triggers: `alphaswarm build-kg` command
- Responsibilities: Parse Slither, extract properties, compute signatures, serialize graph

**Pattern Matcher Entry:**
- Location: `src/alphaswarm_sol/vulndocs/` (pattern engine)
- Triggers: Detection phase of audit
- Responsibilities: Match patterns against BSKG, rank candidates, filter by confidence

**Testing Orchestrator Entry:**
- Location: `src/alphaswarm_sol/testing/full_testing_orchestrator.py`
- Triggers: `/vrs-full-testing` skill or validation workflows
- Responsibilities: Run E2E validation via claude-code-controller, generate evidence packs

## Error Handling

**Strategy:** Evidence-first error capture with anti-fabrication checks

**Patterns:**
- Graph build failures → emit error marker, preserve partial graph for debugging
- Agent spawn failures → retry with exponential backoff, escalate to supervisor
- Tool execution failures → mark as TOOL_ERROR, continue with available tools
- Verdict conflicts → route to verifier for arbitration, default to `uncertain`
- Missing context → default to `uncertain` rather than fabricate evidence
- Perfect metrics (100%/100%) → trigger fabrication investigation

## Cross-Cutting Concerns

**Logging:** Structured logging via `structlog` with context propagation

**Validation:**
- Graph integrity checks (node/edge counts, property coverage)
- Evidence validation (graph node IDs exist, code locations valid)
- Transcript validation (markers present, duration > 5s, line count > 50)
- Anti-fabrication rules (realistic metrics, tool markers present)

**Authentication:**
- Anthropic API key via environment variable
- OpenAI/Google API keys for multi-provider support
- No auth for CLI (called by Claude Code in user's environment)

**Orchestration Markers (MANDATORY):**
- `[PREFLIGHT_PASS]` or `[PREFLIGHT_FAIL]` - Gate validation
- `[GRAPH_BUILD_SUCCESS]` - Graph construction complete
- `[CONTEXT_READY]` - Protocol context available
- `[TOOLS_COMPLETE]` - Static analysis done
- `[DETECTION_COMPLETE]` - Pattern matching done
- `TaskCreate(task-id)` - Task lifecycle start
- `TaskUpdate(task-id, verdict)` - Task lifecycle end
- `[REPORT_GENERATED]` - Report produced
- `[PROGRESS_SAVED]` - State persisted

## Core Philosophy (Behavioral Detection)

**Names Lie. Behavior Does Not.**

Traditional tools detect `withdraw()` by name. AlphaSwarm.sol detects:
```
R:bal -> X:out -> W:bal
(read balance, external call, write balance)
```

The function name is irrelevant. The behavioral pattern reveals vulnerability.

**Three-Tier Detection:**
- **Tier A:** Deterministic, graph-only, high confidence (no LLM)
- **Tier B:** LLM-verified, exploratory, complex logic bugs
- **Tier C:** Label-dependent, semantic role annotations

**Graph-First Rule:**
Agents MUST query BSKG before conclusions. No manual code reading before graph queries run.

**Multi-Agent Verification:**
Specialized roles debate findings:
- Attacker (opus): Construct exploit paths
- Defender (sonnet): Find guards, mitigations
- Verifier (opus): Cross-check evidence, arbitrate

Multiple models reduce correlated failures.

**Evidence Requirements:**
Every finding must link to:
- Graph node IDs (exact function/contract)
- Matched properties (has_access_gate=false)
- Operation sequences (behavioral signature)
- Source locations (file:line)

**Confidence Buckets:**
- `confirmed` - Verified by test or convergent multi-agent evidence
- `likely` - Strong behavioral evidence, no exploit proof
- `uncertain` - Weak or conflicting signals, needs human review
- `rejected` - Disproven or explained as benign

No "confirmed" without evidence + verification. Missing context defaults to `uncertain`.

## Recent Implementation: Phase 7.3.1.5/7.3.1.6

**7.3.1.5: Full Testing Orchestrator**
- claude-code-controller based testing framework (`src/alphaswarm_sol/testing/agent_teams_harness.py`)
- Evidence pack schema and generation
- Full testing orchestrator for E2E validation
- Proof token generation and validation
- Anti-fabrication rules (transcript quality, duration checks)

**7.3.1.6: Testing Hardening**
- Two-orchestrator split (init + task) with command router
- Parallel detection with configurable concurrency
- TaskCreate during detection with `pending_dedup` → `ready` lifecycle
- Deduplication workflow contract with merge markers
- Tool category mapping for intelligent dedup
- Bead organizer role clarified in task orchestration
- Coverage map and proof runs for all workflows
- Orchestration behavior proof (markers/tasks/agents present in transcripts)

See `.planning/phases/07.3.1.5-full-testing-orchestrator/` and `.planning/phases/07.3.1.6-full-testing-hardening/` for details.

---

*Architecture analysis: 2026-02-04*
