# Technology Stack

**Analysis Date:** 2026-02-04

## Languages

**Primary:**
- Python 3.11+ (requires >= 3.11, runtime uses 3.14.2)
- Solidity - Target analysis language for smart contracts

**Secondary:**
- YAML - Configuration, pattern definitions, skill/agent registry
- JSON - Graph storage (TOON format), schemas, evidence packets
- Shell (Bash/Zsh) - CLI invocation, testing harness

## Runtime

**Environment:**
- Python 3.14.2 (development), Python 3.11+ minimum requirement
- Virtual environment: `uv` managed venv at `.venv/`

**Package Manager:**
- `uv` - Primary package manager (lockfile-based, fast resolver)
- Lockfile: `uv.lock` (present)
- Build backend: Hatchling 1.25.0+

## Frameworks

**Core:**
- Slither 0.10.4+ - Solidity static analysis framework, AST extraction
- Pydantic 2.8.2+ - Data validation, settings management
- Typer 0.12.3+ - CLI framework for `alphaswarm` command
- TOONS 0.4.0+ - Compact serialization format (25-40% token savings)

**Testing:**
- pytest 9.0.2+ - Test runner
- pytest-asyncio 0.24.0+ - Async test support
- pytest-xdist 3.8.0+ - Parallel test execution (`-n auto --dist loadfile` gives 3.79x speedup)
- pytest-testmon 2.2.0+ - Test change detection

**Build/Dev:**
- Hatchling - Python build backend
- structlog 24.1.0+ - Structured logging with context

## Key Dependencies

**Critical:**
- `anthropic` 0.34.0+ - Claude API client for multi-agent orchestration
- `slither-analyzer` 0.10.4+ - Core Solidity analysis engine
- `neo4j` 5.23.0+ - Graph database driver for BSKG storage (bolt://localhost:7687)
- `chromadb` 0.5.5+ - Vector storage for semantic similarity (localhost:8000)
- `semgrep` 1.64.0+ - Pattern-based static analysis

**LLM Abstraction:**
- `anthropic` 0.34.0+ - Claude (Opus 4.5, Sonnet 4.5, Haiku 4.5)
- `openai` 1.54.0+ - GPT models
- `google-generativeai` 0.8.0+ - Gemini models
- `openai-agents` 0.6.9+ - Agent framework support
- `tiktoken` 0.8.0+ - Token counting

**Infrastructure:**
- `httpx` 0.27.0+ - Async HTTP client
- `z3-solver` 4.15.4.0+ - SMT solver for formal verification
- `pyyaml` 6.0.2+ - YAML parsing for patterns/config
- `pydantic-settings` 2.4.0+ - Environment-based configuration

**Observability:**
- `opentelemetry-api` 1.28.0+ - Tracing API
- `opentelemetry-sdk` 1.28.0+ - Tracing SDK
- `opentelemetry-exporter-otlp-proto-http` 1.28.0+ - OTLP export

**Validation:**
- `jsonschema` 4.20.0+ - Schema validation for evidence packs, scenarios

## Configuration

**Environment:**
- Configuration via `.env` file or environment variables with `TRUE_VKG_` prefix
- Pydantic settings loader in `src/alphaswarm_sol/config.py`
- Key environment variables:
  - `ANTHROPIC_API_KEY` - Claude API (primary orchestration model)
  - `GEMINI_API_KEY` - Google Gemini (bulk work, cheapest)
  - `OPENAI_API_KEY` - OpenAI GPT (fallback)
  - `XAI_API_KEY` - xAI Grok (code-focused alternative)
  - `EXA_API_KEY` - Exa search (vulnerability research)
  - `TRUE_VKG_NEO4J_URI` - Graph DB connection (default: bolt://localhost:7687)
  - `TRUE_VKG_NEO4J_USER` - Neo4j username (default: neo4j)
  - `TRUE_VKG_NEO4J_PASSWORD` - Neo4j password
  - `TRUE_VKG_CHROMA_HOST` - ChromaDB host (default: localhost)
  - `TRUE_VKG_CHROMA_PORT` - ChromaDB port (default: 8000)
  - `TRUE_VKG_LOG_LEVEL` - Logging level (default: INFO)

**Build:**
- `pyproject.toml` - PEP 621 project metadata, dependencies, tool config
- pytest configuration in `[tool.pytest.ini_options]`
- Default test args: `-n auto --dist loadfile` (parallel execution)

**Claude Code Integration:**
- `.claude/settings.json` - Claude Code hooks, LSP configuration
- pyright-lsp enabled for Python navigation/refactoring
- Custom hooks for notifications via ntfy.sh and macOS osascript

## Platform Requirements

**Development:**
- Python 3.11+ with venv support
- `uv` package manager
- Solidity compiler (solc) - auto-selected per contract via `alphaswarm_sol.kg.solc`
- Neo4j 5.23.0+ (optional, for graph persistence)
- ChromaDB (optional, for semantic search)
- claude-code-agent-teams - Required for isolated testing harness (multi-agent validation)

**Production:**
- CLI tool: `uv tool install alphaswarm-sol` or `pip install alphaswarm-sol`
- Entry points: `alphaswarm` and `aswarm` (aliases)
- Claude Code orchestrator: Skills loaded from `.claude/skills/` and `.claude/agents/`
- Storage: `.vrs/` directory for graphs, beads, pools, evidence
- External tools (optional but recommended):
  - Slither (pip, Tier 0 - core)
  - Aderyn (cargo, Tier 1 - recommended)
  - Mythril (pip, Tier 2 - optional)

## Multi-Agent Orchestration

**Execution Model:**
- **Orchestrator:** Claude Code (not part of this repo, invoked by user)
- **CLI:** `alphaswarm` command (tool called BY Claude Code via Bash)
- **Agents:** Spawned via Claude Code Task tool with `subagent_type` parameter
- **Skills:** Located in `.claude/skills/` (47 skills), invoked via slash commands (e.g., `/vrs-audit`)
- **Agent Catalog:** `src/alphaswarm_sol/agents/catalog.yaml` (24 agents)

**Agent Types:**
- `vrs-attacker` - Construct exploit paths (Opus model)
- `vrs-defender` - Find guards/mitigations (Sonnet model)
- `vrs-verifier` - Cross-check evidence, arbitrate (Opus model)
- `vrs-supervisor` - Workflow coordinator (Sonnet model)
- `vrs-secure-reviewer` - Evidence-first security review (Sonnet model)

**Model Delegation:**
| Tier | Model | Use Case |
|------|-------|----------|
| Fast/Cheap | Haiku 4.5 | URL filtering, tool running, mechanical extraction |
| Balanced | Sonnet 4.5 | Core authoring, pattern validation, coordination |
| Deep Reasoning | Opus 4.5 | Pattern refinement, complex reasoning, attack paths |

**Token Budget:**
- Default max: 6,000 tokens per agent
- Hard cap: 8,000 tokens (enforced in `config.py`)
- Role-specific budgets: classifier (2K), attacker (6K), defender (5K), verifier (4K)
- Progressive disclosure: SUMMARY (15%) → EVIDENCE (50%) → RAW (100%)

---

*Stack analysis: 2026-02-04*
