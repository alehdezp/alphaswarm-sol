# External Integrations

**Analysis Date:** 2026-02-04

## APIs & External Services

**LLM Providers:**
- Anthropic Claude - Primary orchestration model for multi-agent workflow
  - SDK/Client: `anthropic` 0.34.0+
  - Auth: `ANTHROPIC_API_KEY`
  - Models: claude-opus-4.5, claude-sonnet-4.5, claude-3-5-haiku-latest
  - Features: Prompt caching (90% cost reduction), tool calling
  - Cost tracking: $0.25/1M input, $1.25/1M output (Haiku)
  - Implementation: `src/alphaswarm_sol/llm/providers/anthropic.py`, `src/alphaswarm_sol/agents/runtime/anthropic.py`

- Google Gemini - Bulk work, cheapest provider
  - SDK/Client: `google-generativeai` 0.8.0+
  - Auth: `GEMINI_API_KEY`
  - Models: gemini-2.0-flash-exp
  - Cost: $0.10/1M input, $0.40/1M output
  - Implementation: `src/alphaswarm_sol/llm/providers/google.py`

- OpenAI - Fallback provider
  - SDK/Client: `openai` 1.54.0+
  - Auth: `OPENAI_API_KEY`
  - Models: gpt-4o-mini
  - Cost: $0.15/1M input, $0.60/1M output
  - Implementation: `src/alphaswarm_sol/llm/providers/openai.py`

- xAI Grok - Code-focused alternative
  - SDK/Client: `httpx` with custom client
  - Auth: `XAI_API_KEY`
  - Base URL: https://api.x.ai/v1
  - Models: grok-2
  - Implementation: `src/alphaswarm_sol/llm/providers/xai.py`

- Ollama - Local inference (optional)
  - Client: httpx to http://localhost:11434/api/tags
  - Auth: None (local service)
  - Implementation: `src/alphaswarm_sol/llm/config.py` availability check

**Research Tools:**
- Exa Search - Vulnerability research, real-world exploit discovery
  - Auth: `EXA_API_KEY`
  - Used for: VulnDocs corpus expansion, pattern validation

**Static Analysis Tools:**
- Slither - Core Solidity analysis (Tier 0, required)
  - Client: `slither-analyzer` 0.10.4+ (Python package)
  - Invocation: `src/alphaswarm_sol/tools/runner.py` via subprocess
  - Output: JSON AST, control flow, data flow
  - Registry: `src/alphaswarm_sol/tools/registry.py`
  - Adapter: `src/alphaswarm_sol/tools/adapters/`

- Aderyn - Rust-based Solidity analyzer (Tier 1, recommended)
  - Binary: `aderyn` (cargo install)
  - Output: SARIF format
  - Adapter: `src/alphaswarm_sol/tools/adapters/aderyn_adapter.py`

- Mythril - Symbolic execution (Tier 2, optional)
  - Client: `mythril` (pip install)
  - Use: Deep path exploration, formal verification

- Semgrep - Pattern-based analysis (Tier 1)
  - Client: `semgrep` 1.64.0+
  - Auth: `SEMGREP_APP_TOKEN` (optional)
  - Adapter: `src/alphaswarm_sol/tools/adapters/semgrep_adapter.py`

**Tool Coordination:**
- Model tier for tool execution: Haiku 4.5 (fast, cheap)
- Model tier for coordination: Sonnet 4.5 (balanced)
- Parallel execution via ThreadPoolExecutor
- Timeout handling: Default 120s per tool
- Implementation: `src/alphaswarm_sol/tools/executor.py`, `src/alphaswarm_sol/tools/coordinator.py`

## Data Storage

**Databases:**
- Neo4j - Behavioral Smart Contract Knowledge Graph (BSKG)
  - Connection: `TRUE_VKG_NEO4J_URI` (default: bolt://localhost:7687)
  - Auth: `TRUE_VKG_NEO4J_USER`, `TRUE_VKG_NEO4J_PASSWORD`
  - Client: `neo4j` 5.23.0+
  - Use: Graph storage for functions, contracts, operations, edges
  - Optional: System works without Neo4j, uses local JSON storage

- ChromaDB - Vector embeddings for semantic similarity
  - Connection: `TRUE_VKG_CHROMA_HOST:TRUE_VKG_CHROMA_PORT` (default: localhost:8000)
  - Client: `chromadb` 0.5.5+
  - Use: Pattern similarity, vulnerability clustering
  - Optional: System works without ChromaDB

**File Storage:**
- Local filesystem only
- Storage root: `.vrs/` directory
- Structure:
  - `.vrs/graphs/` - Knowledge graphs in TOON format
  - `.vrs/beads/` - Investigation packages
  - `.vrs/pools/` - Audit pools and verdicts
  - `.vrs/evidence/` - Evidence packets with proofs
  - `.vrs/context/` - Protocol context packs
  - `.vrs/metrics/` - Performance metrics, benchmarks
  - `.vrs/corpus/` - Ground truth vulnerability corpus

**Caching:**
- LLM prompt caching via Anthropic API (automatic, 90% cost reduction)
- Tool output caching in `src/alphaswarm_sol/cache/`
- Graph caching for test suite in `tests/graph_cache.py`

## Authentication & Identity

**Auth Provider:**
- Custom (environment variable based)
  - Implementation: API keys read from environment via `src/alphaswarm_sol/config.py`
  - Per-provider key management in `src/alphaswarm_sol/llm/config.py`
  - Validation: `ProviderConfig.is_available()` checks for keys
  - No centralized identity service

## Monitoring & Observability

**Error Tracking:**
- structlog 24.1.0+ - Structured logging with context
  - Configuration: `src/alphaswarm_sol/config.py` (configure_logging)
  - Log level: `TRUE_VKG_LOG_LEVEL` (default: INFO)

**Telemetry:**
- OpenTelemetry - Distributed tracing (Phase 7.1.5)
  - API: `opentelemetry-api` 1.28.0+
  - SDK: `opentelemetry-sdk` 1.28.0+
  - Exporter: `opentelemetry-exporter-otlp-proto-http` 1.28.0+
  - Implementation: `src/alphaswarm_sol/observability/tracer.py`
  - Spans: `src/alphaswarm_sol/observability/spans.py`
  - Events: `src/alphaswarm_sol/observability/events.py`
  - Audit trail: `src/alphaswarm_sol/observability/audit.py`
  - Lineage tracking: `src/alphaswarm_sol/observability/lineage.py`

**Logs:**
- Console output via structlog processors
- ISO timestamps, log levels, stack traces, exception formatting
- No external log aggregation service

**Metrics:**
- Local storage in `.vrs/metrics/`
- Retention: 90 days (configurable in `config.py`)
- Collection interval: Daily
- Alert thresholds: Critical only (no warning alerts)

## CI/CD & Deployment

**Hosting:**
- Local development: Python package installed via uv/pip
- No hosted service (tool runs locally or in user's environment)

**CI Pipeline:**
- None (internal development uses git workflow)
- Testing: `pytest -n auto --dist loadfile` (local execution)

**Package Distribution:**
- PyPI (future): `pip install alphaswarm-sol`
- uv tool: `uv tool install alphaswarm-sol` or `uv tool install -e .` (dev)
- Entry points: `alphaswarm` and `aswarm` commands

## Environment Configuration

**Required env vars:**
- At least one LLM provider API key (ANTHROPIC_API_KEY, GEMINI_API_KEY, OPENAI_API_KEY, or XAI_API_KEY)
- Provider priority: google,anthropic,openai,xai,ollama (configurable via `LLM_PROVIDER_PRIORITY`)

**Optional env vars:**
- `TRUE_VKG_NEO4J_URI`, `TRUE_VKG_NEO4J_USER`, `TRUE_VKG_NEO4J_PASSWORD` - Graph DB
- `TRUE_VKG_CHROMA_HOST`, `TRUE_VKG_CHROMA_PORT` - Vector DB
- `TRUE_VKG_LOG_LEVEL` - Logging verbosity
- `EXA_API_KEY` - Research tool
- `SEMGREP_APP_TOKEN` - Semgrep Pro features
- `SNYK_TOKEN` - Dependency scanning
- `LLM_MAX_BUDGET_USD` - Budget limit per session
- `LLM_CACHE_ENABLED` - Enable/disable caching (default: true)

**Secrets location:**
- `.env` file in project root (not committed, see `.env.example`)
- Environment variables with `TRUE_VKG_` prefix
- Per-provider API key environment variables (no secrets in code)

## Webhooks & Callbacks

**Incoming:**
- None (CLI tool, no server)

**Outgoing:**
- ntfy.sh notifications - Claude Code hooks for permission/idle prompts
  - Endpoint: https://ntfy.sh/alesito-de-las-eras
  - Configured in: `.claude/settings.json`
  - Triggers: `permission_prompt`, `idle_prompt`
  - Includes: macOS osascript notifications + ntfy.sh HTTP push

**Internal Callbacks:**
- Tool execution callbacks for success/error handling
  - Implementation: `src/alphaswarm_sol/tools/timeout.py`
  - Used for: Async tool timeout handling, result streaming

## Claude Code Orchestration

**Orchestrator Integration:**
- Claude Code (external, not part of this codebase) acts as the orchestrator
- Skills defined in `.claude/skills/` (47 skills, YAML frontmatter + Markdown)
- Agents defined in `.claude/agents/` (24 agents, YAML frontmatter + Markdown)
- Skill invocation: Slash commands (e.g., `/vrs-audit contracts/`)
- Agent spawning: Via Claude Code's Task tool with `subagent_type` parameter

**Master Skill:**
- `/vrs-audit` - Full audit execution loop
  - Location: `.claude/skills/vrs-audit/SKILL.md`
  - Orchestrates: Graph build → Context load → Pattern detect → Bead create → Multi-agent debate → Report

**Tool Invocation by Claude Code:**
- `Bash` tool: Execute `alphaswarm` CLI commands
- `Task` tool: Spawn subagents (attacker, defender, verifier)
- `Read/Write` tools: Manage state, evidence, reports
- `Glob/Grep` tools: Codebase navigation

**Testing Harness:**
- claude-code-agent-teams-based isolation for orchestration testing
  - Implementation: `src/alphaswarm_sol/testing/agent_teams_harness.py`
  - Unique socket per run: `/tmp/vrs-{run_id}.sock`
  - Panes: controller (orchestrator), subject (Claude Code), monitor (transcript)
  - Transcript capture with SHA-256 hashing for diffing

---

*Integration audit: 2026-02-04*
