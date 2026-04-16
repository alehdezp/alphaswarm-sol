# Codebase Structure

**Analysis Date:** 2026-02-04

## Directory Layout

```
true-vkg/
├── .claude/                    # Claude Code integration
│   ├── agents/                 # Subagent definitions (attacker, defender, verifier)
│   ├── skills/                 # Skills that guide Claude Code behavior
│   └── settings.json           # Claude Code LSP and configuration
├── .planning/                  # Project planning and documentation
│   ├── codebase/               # Codebase analysis (this doc)
│   ├── phases/                 # 1,247 planning documents across phases
│   ├── research/               # Research reports and investigations
│   ├── testing/                # Testing documentation and rules
│   └── STATE.md                # Current progress and blockers
├── .vrs/                       # VRS runtime artifacts (gitignored)
│   ├── graphs/                 # BSKG graphs (*.toon)
│   ├── context/                # Protocol context packs
│   ├── state/                  # Progress state (current.yaml)
│   ├── testing/                # Test run evidence packs
│   └── corpus/                 # Ground truth contracts
├── benchmarks/                 # Benchmark suites (DvD, SmartBugs)
├── configs/                    # Configuration files (claude-code-agent-teams_cli_markers.yaml)
├── docs/                       # Documentation
│   ├── guides/                 # How-to guides (patterns, skills, testing)
│   ├── reference/              # API and technical references
│   └── workflows/              # Workflow documentation
├── examples/                   # Example contracts and usage
├── schemas/                    # JSON schemas for validation
├── scripts/                    # Automation scripts
│   ├── e2e/                    # E2E testing scripts
│   └── validate_*.py           # Validation scripts
├── src/                        # Source code
│   └── alphaswarm_sol/         # Main package (~309k LOC)
├── tests/                      # Test suite
│   ├── contracts/              # Test contracts (vulnerable/safe)
│   ├── fixtures/               # Test fixtures
│   └── integration/            # Integration tests
├── validation/                 # Validation ground truth
│   └── ground-truth/           # External ground truth (Code4rena, etc.)
├── vulndocs/                   # 686 vulnerability patterns (YAML)
│   ├── access-control/         # Access control patterns
│   ├── reentrancy/             # Reentrancy patterns
│   ├── oracle/                 # Oracle manipulation patterns
│   └── [16 other categories]
├── pyproject.toml              # Python package configuration
└── README.md                   # Project README
```

## Directory Purposes

**.claude/**
- Purpose: Claude Code orchestration framework
- Contains: Skills (WHAT to do), agents (WHO does it), settings
- Key files:
  - `.claude/skills/vrs-audit/SKILL.md` - Master audit orchestrator
  - `.claude/agents/vrs-attacker/AGENT.md` - Attacker agent definition
  - `.claude/agents/vrs-defender/AGENT.md` - Defender agent definition
  - `.claude/agents/vrs-verifier/AGENT.md` - Verifier agent definition
  - `.claude/settings.json` - LSP integration (pyright-lsp)

**.planning/**
- Purpose: Project management, documentation, and planning
- Contains: 1,247 planning documents, testing rules, phase specifications
- Key files:
  - `.planning/STATE.md` - Current progress (~98% complete, 266/270 plans)
  - `.planning/TOOLING.md` - Task → tool selection guide
  - `.planning/testing/rules/canonical/RULES-ESSENTIAL.md` - Testing rules
  - `.planning/testing/rules/canonical/VALIDATION-RULES.md` - Validation rules (A1-G3)
  - `.planning/phases/07.3.1.5-full-testing-orchestrator/` - Testing orchestrator spec
  - `.planning/phases/07.3.1.6-full-testing-hardening/` - Testing hardening plans

**src/alphaswarm_sol/**
- Purpose: Core implementation (~309k LOC)
- Contains: All Python source code organized by domain
- Key subdirectories:
  - `kg/` - Knowledge graph builder (~9,500 LOC)
  - `orchestration/` - Multi-agent orchestration (~6,400 LOC)
  - `tools/` - External tool integration (~12,000 LOC)
  - `agents/` - Agent infrastructure (~7,700 LOC)
  - `testing/` - Testing framework (~1,400 LOC)
  - `beads/` - Investigation packages
  - `vulndocs/` - VulnDocs pattern framework
  - `cli/` - CLI commands
  - `skills/` - Skill registry and validation

**vulndocs/**
- Purpose: Vulnerability pattern library (686 patterns)
- Contains: YAML pattern definitions organized by category
- Key files:
  - `vulndocs/reentrancy/*.yaml` - Reentrancy patterns
  - `vulndocs/access-control/*.yaml` - Access control patterns
  - `vulndocs/oracle/*.yaml` - Oracle manipulation patterns
  - [18 total vulnerability categories]

**tests/**
- Purpose: Test suite with contracts and fixtures
- Contains: Unit, integration, E2E tests
- Key files:
  - `tests/contracts/*.sol` - Test contracts (vulnerable/safe variants)
  - `tests/fixtures/` - Test fixtures and ground truth
  - `tests/graph_cache.py` - Graph caching for performance

**validation/**
- Purpose: External ground truth for validation
- Contains: Code4rena findings, SmartBugs corpus
- Key files:
  - `validation/ground-truth/code4rena/` - Code4rena findings
  - `validation/ground-truth/smartbugs/` - SmartBugs corpus

## Key File Locations

**Entry Points:**
- `src/alphaswarm_sol/cli/main.py` - CLI entry point (called by Claude Code)
- `.claude/skills/vrs-audit/SKILL.md` - User-facing skill entry point
- `pyproject.toml` - Package configuration and CLI aliases (alphaswarm, aswarm)

**Configuration:**
- `pyproject.toml` - Python package, dependencies, pytest config
- `.claude/settings.json` - Claude Code LSP and skill configuration
- `configs/claude_code_controller_markers.yaml` - claude-code-controller marker definitions

**Core Logic:**
- `src/alphaswarm_sol/kg/builder.py` - BSKG builder (285k LOC legacy + modular)
- `src/alphaswarm_sol/kg/builder/core.py` - VKGBuilder orchestration (787 LOC)
- `src/alphaswarm_sol/kg/builder/functions.py` - Function processor (1,194 LOC, 225 fields)
- `src/alphaswarm_sol/kg/operations.py` - Semantic operations (48k LOC)
- `src/alphaswarm_sol/orchestration/loop.py` - Execution loop (~500 LOC)
- `src/alphaswarm_sol/orchestration/debate.py` - Multi-agent debate (802 LOC)
- `src/alphaswarm_sol/orchestration/handlers.py` - Phase handlers (1,057 LOC)
- `src/alphaswarm_sol/tools/coordinator.py` - Tool orchestration (970 LOC)
- `src/alphaswarm_sol/testing/agent_teams_harness.py` - claude-code-controller testing (21k LOC)

**Testing:**
- `src/alphaswarm_sol/testing/full_testing_orchestrator.py` - E2E orchestrator (42k LOC)
- `src/alphaswarm_sol/testing/evidence_pack.py` - Evidence pack generation (24k LOC)
- `src/alphaswarm_sol/testing/proof_tokens.py` - Proof token validation (20k LOC)
- `.planning/testing/rules/canonical/TESTING-FRAMEWORK.md` - Testing architecture
- `.planning/testing/rules/canonical/TESTING-PHILOSOPHY.md` - Testing philosophy

## Naming Conventions

**Files:**
- Python modules: `snake_case.py` (e.g., `graph_hash.py`, `evidence_pack.py`)
- Test files: `test_*.py` (e.g., `test_builder.py`, `test_patterns.py`)
- Skill definitions: `SKILL.md` or `skill-name.md` (e.g., `vrs-audit.md`)
- Agent definitions: `AGENT.md` (e.g., `.claude/agents/vrs-attacker/AGENT.md`)
- Planning docs: `UPPERCASE.md` for specs (e.g., `PLAN.md`, `SUMMARY.md`)
- Pattern files: `kebab-case.yaml` (e.g., `reentrancy-classic.yaml`)

**Directories:**
- Package modules: `snake_case/` (e.g., `kg/`, `orchestration/`)
- Planning phases: `kebab-case/` (e.g., `07.3-ga-validation/`)
- Pattern categories: `kebab-case/` (e.g., `access-control/`, `flash-loan/`)

**Functions:**
- Python functions: `snake_case()` (e.g., `build_graph()`, `match_pattern()`)
- CLI commands: `kebab-case` (e.g., `build-kg`, `run-tools`)

**Variables:**
- Python variables: `snake_case` (e.g., `graph_hash`, `evidence_packet`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_TIMEOUT`, `MIN_CONFIDENCE`)

**Types:**
- Python classes: `PascalCase` (e.g., `VKGBuilder`, `EvidencePack`)
- Pydantic models: `PascalCase` (e.g., `BeadSchema`, `PoolConfig`)

## Where to Add New Code

**New Vulnerability Pattern:**
- Pattern definition: `vulndocs/[category]/[pattern-name].yaml`
- Tests: `tests/vulndocs/test_[category].py`
- Ground truth: `validation/ground-truth/internal/annotated/[pattern-name].yaml`

**New Semantic Operation:**
- Definition: `src/alphaswarm_sol/kg/operations.py`
- Extraction logic: `src/alphaswarm_sol/kg/builder/functions.py`
- Tests: `tests/kg/test_operations.py`

**New Tool Adapter:**
- Implementation: `src/alphaswarm_sol/tools/adapters/[tool]_adapter.py`
- Registration: `src/alphaswarm_sol/tools/registry.py`
- Tests: `tests/adapters/test_[tool]_adapter.py`

**New Skill:**
- Skill definition: `.claude/skills/[skill-name]/SKILL.md`
- Registry entry: `src/alphaswarm_sol/skills/registry.yaml`
- Tests: Use claude-code-controller to validate (see RULES-ESSENTIAL.md)

**New Subagent:**
- Agent definition: `.claude/agents/[agent-name]/AGENT.md`
- Catalog entry: `src/alphaswarm_sol/agents/catalog.yaml`
- Tests: Use claude-code-controller with agent spawn validation

**New CLI Command:**
- Implementation: `src/alphaswarm_sol/cli/[command].py`
- Registration: `src/alphaswarm_sol/cli/main.py` (typer app)
- Tests: `tests/cli/test_[command].py`

**New Workflow/Phase:**
- Planning: `.planning/phases/[phase-id]/`
- Implementation: Distributed across relevant modules
- Tests: `.planning/testing/workflows/workflow-[name].md`
- Validation: E2E test via claude-code-controller

**Utilities:**
- Shared helpers: `src/alphaswarm_sol/core/` or module-specific `helpers.py`
- Testing utilities: `src/alphaswarm_sol/testing/` or `tests/` (fixtures)

## Special Directories

**.vrs/**
- Purpose: Runtime artifacts (graphs, state, evidence)
- Generated: Yes (by CLI and orchestrator)
- Committed: No (gitignored)
- Contains:
  - `graphs/*.toon` - BSKG graphs
  - `state/current.yaml` - Progress state
  - `testing/runs/<run-id>/` - Test evidence packs
  - `corpus/` - Ground truth contracts

**.claude/skills/**
- Purpose: Skill definitions that guide Claude Code
- Generated: No (hand-authored)
- Committed: Yes
- Contains: Markdown skill definitions with triggers, procedures, tools

**.claude/agents/**
- Purpose: Subagent definitions for specialized investigation
- Generated: No (hand-authored)
- Committed: Yes
- Contains: Agent definitions with role, scope, tools, termination

**src/alphaswarm_sol/kg/builder/**
- Purpose: Modular graph builder components
- Generated: No
- Committed: Yes
- Contains:
  - `core.py` - VKGBuilder orchestration
  - `contracts.py` - Contract-level properties (1,377 LOC)
  - `functions.py` - Function-level properties (1,194 LOC)
  - `state_vars.py` - State variable analysis (317 LOC)
  - `calls.py` - Call tracking (1,160 LOC)
  - `proxy.py` - Proxy resolution (825 LOC)
  - `helpers.py` - Utility functions (551 LOC)
  - `completeness.py` - Build quality reports (489 LOC)

**src/alphaswarm_sol/testing/flexible/**
- Purpose: Flexible testing framework for agent workflows
- Generated: No
- Committed: Yes
- Contains: Test harnesses, evidence generation, claude-code-controller integration

**tests/contracts/**
- Purpose: Test contracts (vulnerable and safe variants)
- Generated: No (hand-authored or from SmartBugs/DvD)
- Committed: Yes
- Contains: Solidity contracts with known vulnerabilities for testing

**validation/ground-truth/**
- Purpose: External ground truth for validation
- Generated: No (sourced from Code4rena, SmartBugs, etc.)
- Committed: Yes
- Contains: Findings with provenance for validation

**benchmarks/**
- Purpose: Benchmark suites for performance and accuracy testing
- Generated: No (sourced externally)
- Committed: Yes (references only, not full corpora)
- Contains: DamnVulnerableDefi, SmartBugs subsets

**schemas/**
- Purpose: JSON schemas for validation
- Generated: No
- Committed: Yes
- Contains:
  - `testing/evidence_manifest.schema.json` - Evidence pack schema
  - `testing/scenario_manifest.schema.json` - Scenario schema

## Module Organization

**src/alphaswarm_sol/ (309k LOC total)**

| Module | LOC Range | Purpose |
|--------|-----------|---------|
| `kg/` | ~100k | Knowledge graph builder, queries, operations |
| `orchestration/` | ~30k | Multi-agent orchestration, pools, debate |
| `testing/` | ~45k | Testing framework, claude-code-agent-teams harness, evidence packs |
| `tools/` | ~25k | External tool integration, adapters, dedup |
| `agents/` | ~15k | Agent infrastructure, runtime, ranking |
| `vulndocs/` | ~12k | VulnDocs pattern framework |
| `beads/` | ~8k | Investigation packages (beads & pools) |
| `context/` | ~6k | Protocol context packs |
| `metrics/` | ~8k | Metrics, cost tracking, event recording |
| `cli/` | ~5k | CLI commands |
| `skills/` | ~3k | Skill registry and validation |
| `labels/` | ~4k | Semantic labeling |
| `findings/` | ~3k | Finding management |
| `queries/` | ~4k | Query engine |
| Other modules | ~41k | Various support modules |

## Import Patterns

**Top-Level Imports:**
```python
from alphaswarm_sol.kg.builder import VKGBuilder
from alphaswarm_sol.orchestration.loop import execute_loop
from alphaswarm_sol.tools.coordinator import ToolCoordinator
```

**Relative Imports (Within Module):**
```python
from .schemas import BeadSchema, PoolConfig
from .helpers import compute_graph_hash
```

**External Dependencies:**
```python
from anthropic import Anthropic
from slither.slither import Slither
from pydantic import BaseModel
```

## Configuration Files

**pyproject.toml:**
- Package metadata (name, version, dependencies)
- CLI entry points (`alphaswarm`, `aswarm`)
- Pytest configuration (parallel execution with `pytest-xdist`)

**configs/claude_code_controller_markers.yaml:**
- claude-code-controller marker definitions
- Session configuration
- Validation rules

**.claude/settings.json:**
- LSP configuration (pyright-lsp enabled)
- Skill and agent registration
- Claude Code integration settings

**src/alphaswarm_sol/config.py:**
- Runtime configuration
- Environment variable handling
- Default settings

## Graph-First Architecture

**Philosophy:** All investigation MUST query BSKG before conclusions.

**Query Flow:**
1. Agent receives investigation task
2. Agent constructs VQL query or natural language query
3. Query engine executes against BSKG
4. Results include graph node IDs, properties, evidence
5. Agent uses results to construct argument/finding
6. Evidence packet links back to graph nodes

**No Manual Code Reading:** Agents MUST NOT read source code directly before querying graph.

## Testing Architecture

**Three Testing Modes:**
1. **Unit Tests:** `tests/` with pytest (parallel execution)
2. **Integration Tests:** `tests/integration/` with real graph builds
3. **E2E Validation:** claude-code-controller based with evidence packs

**claude-code-controller Testing Pattern:**
```bash
# Controller (your active Claude Code session)
claude-code-controller launch "zsh"                           # 1. Launch shell
claude-code-controller send "claude" --pane=X                 # 2. Start Claude Code
claude-code-controller send "/vrs-audit contracts/" --pane=X  # 3. Execute skill
claude-code-controller wait_idle --pane=X --idle-time=15.0    # 4. Wait for completion
claude-code-controller capture --pane=X > transcript.txt      # 5. Capture transcript
claude-code-controller kill --pane=X                          # 6. Cleanup
```

**Evidence Pack Structure:**
```
.vrs/testing/runs/<run-id>/
├── manifest.json           # Run metadata (session_label, pane_id, duration)
├── transcript.txt          # Full claude-code-agent-teams transcript (>50 lines smoke, >200 E2E)
├── environment.json        # Tool versions, graph hash, ground truth
├── report.json             # Findings, verdicts, metrics
├── proofs/                 # Proof tokens
│   ├── proof-graph.json
│   └── proof-report.json
└── debug/                  # Debug artifacts
```

**Anti-Fabrication Rules:**
- Transcript min lines: 50 (smoke), 200 (E2E)
- Duration min: 5s (smoke), 30s (agent), 120s (E2E)
- Tool markers required: `alphaswarm`, `slither`, or agent names present
- Perfect metrics forbidden: 100%/100% = fabrication
- Realistic variance: Precision 60-85%, Recall 50-80%

---

*Structure analysis: 2026-02-04*
