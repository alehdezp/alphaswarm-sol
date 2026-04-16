# Tooling Guide (Condensed)

Use this file when planning or executing phases.

## Documentation Structure (45 docs)

```
docs/
├── index.md                   # Entry point, session starters
├── DOC-INDEX.md               # LLM-optimized routing
├── PHILOSOPHY.md              # 9-stage pipeline, proof tokens, gates
├── LIMITATIONS.md             # Known constraints
├── architecture.md            # System overview
├── getting-started/
│   ├── installation.md        # Setup
│   └── first-audit.md         # Tutorial
├── guides/
│   ├── patterns-basics.md     # Pattern fundamentals
│   ├── patterns-advanced.md   # Tier A+B, PCP v2
│   ├── skills-basics.md       # Skills fundamentals
│   ├── skills-authoring.md    # Schema v2, authoring
│   ├── testing-basics.md      # Pattern testing
│   ├── testing-advanced.md    # GA validation
│   ├── vulndocs-basics.md     # VulnDocs intro
│   ├── vulndocs-authoring.md  # Validation pipeline
│   ├── queries.md             # NL and VQL queries
│   ├── beads.md               # Investigation packages
│   └── safe-math.md           # SafeMath patterns
├── reference/
│   ├── agents.md              # 24-agent catalog
│   ├── tools-overview.md      # Tool architecture
│   ├── tools-adapters.md      # Detector mappings
│   ├── testing-framework.md   # Validation expectations
│   ├── operations.md          # 20 semantic operations
│   ├── properties.md          # 50+ properties
│   ├── cli.md                 # CLI commands
│   ├── graph-first-template.md
│   └── skill-schema-v2.md
├── workflows/                 # Workflow-specific docs (12 files)
│   ├── README.md              # Workflow index
│   ├── CONTEXT.md             # Minimal overview
│   ├── workflow-audit.md      # Main audit entrypoint
│   ├── workflow-graph.md      # Graph build/query
│   ├── workflow-context.md    # Protocol context
│   ├── workflow-tools.md      # Static analysis tools
│   └── ...                    # Other workflows
└── .archive/                  # Legacy/theoretical/oversized
```

**Key docs for agents:**
- Vision: `docs/PHILOSOPHY.md`
- Patterns: `docs/guides/patterns-basics.md`, `docs/guides/patterns-advanced.md`
- Queries: `docs/guides/queries.md`
- Skills: `docs/guides/skills-basics.md`, `docs/guides/skills-authoring.md`
- Agents: `docs/reference/agents.md`
- Graph-first: `docs/reference/graph-first-template.md`

## Research & Discovery
- **Primary**: `mcp__exa-search__web_search_exa` with `type: deep` (always for investigations)
- **Repositories**: GitHub via Exa results; prefer official docs/releases

## Graph-First Analysis (Required)
- Build graph: `uv run alphaswarm build-kg <contracts/>`
- Query: `uv run alphaswarm query "FIND ..."`
- Labeling: `uv run alphaswarm label <graph>`

**Graph-First Template (Mandatory for Subagents):**
- All vulnerability investigations MUST follow the graph-first reasoning template
- Template: `docs/reference/graph-first-template.md`
- Workflow: BSKG Queries → Evidence Packet → Unknowns → Conclusion
- Integrated into: vrs-attacker, vrs-defender, vrs-verifier, graph-retrieve skill
- Enforcement: No manual code reading before BSKG queries run
- Evidence requirement: All claims must include graph node IDs and code locations

## VulnDocs Workflow
- Discover: `/vrs-discover`
- Research: `/vrs-research`
- Ingest: `/vrs-ingest-url` or `/vrs-add-vulnerability`
- Validate patterns: `/vrs-test-pattern`
- Validate corpus: `uv run alphaswarm vulndocs validate vulndocs/`

## Orchestration & Agents
- Orchestrate pools: `uv run alphaswarm orchestrate ...`
- Use `vrs-supervisor` for handoffs and quality gates
- Use `vrs-secure-reviewer` for evidence-first code review (creative + adversarial modes)
- Use `skill-architect` for production skill/subagent design
- Use `gsd-research-context` for phase research/context generation

### Subagent Catalog (Phase 7.1.2)
- **Catalog location**: `src/alphaswarm_sol/agents/catalog.yaml`
- **Reference docs**: `docs/reference/subagent-catalog.md`
- **Usage**: List agents, filter by role/model, validate catalog
  ```python
  from alphaswarm_sol.agents.catalog import list_subagents, get_subagent
  agents = list_subagents()
  attacker = get_subagent("vrs-attacker")
  ```
- **CLI validation**: `python src/alphaswarm_sol/agents/catalog.py validate`
- **Agent categories**: 24 total (21 shipped, 3 dev-only)
  - Core verification: attacker, defender, verifier, secure-reviewer
  - Orchestration: supervisor, integrator
  - Pattern: scout, verifier, composer
  - Context: packer, merger, synthesizer, contradiction
  - Validation pipeline: 8 agents (test-conductor, curator, runner, tester, hunter, gap-finder, prevalidator)
  - Development: skill-auditor, cost-governor, gsd-context-researcher

### Secure Reviewer (Phase 7.1.2)
- **Agent**: `vrs-secure-reviewer` (claude-sonnet-4.5)
- **Purpose**: Evidence-first security review with creative and adversarial modes
- **Output contract**: `schemas/secure_reviewer_output.json`
- **Modes**:
  - Creative: Attack discovery, brainstorm vulnerabilities
  - Adversarial: Claim refutation, challenge findings
- **Required**: Graph-first BSKG queries, evidence anchoring, explicit uncertainty
- **Reference**: `docs/reference/secure-reviewer.md`

## Skill Design & Validation
- **Design**: Use `skill-architect` for production skill/subagent design
- **Audit**: Use `skill-auditor` to review skill quality, cost, and guardrails
- **Schema validation**: `python scripts/validate_skill_schema.py <path>`
  - Validate single skill: `python scripts/validate_skill_schema.py .claude/skills/vrs/audit.md`
  - Validate directory: `python scripts/validate_skill_schema.py src/alphaswarm_sol/shipping/skills/`
  - Strict mode: `--strict` (fail on missing frontmatter)
  - Warn mode: `--warn` (report violations but don't fail)
- **Schema reference**: `docs/reference/skill-schema-v2.md`
- **Tool policy validation**: `uv run python -m alphaswarm_sol.skills.guardrails <skill-path> --role <role>`
  - Validate tool usage: `uv run python -m alphaswarm_sol.skills.guardrails .claude/subagents/secure-solidity-reviewer.md --role verifier`
  - JSON output: `--json` (machine-readable validation result)
  - Strict mode: `--strict` (fail if no frontmatter)
  - Policy file: `configs/skill_tool_policies.yaml`
  - Policy reference: `docs/reference/skill-tool-policies.md`

### Skill Registry (Phase 7.1.2)
- **Registry location**: `src/alphaswarm_sol/skills/registry.yaml`
- **Reference docs**: `docs/guides/skills-basics.md`, `docs/guides/skills-authoring.md`
- **Registry validation**: `uv run python -m alphaswarm_sol.skills.registry validate`
  - Check duplicates: `uv run python -m alphaswarm_sol.skills.registry check-duplicates`
  - List deprecated: `uv run python -m alphaswarm_sol.skills.registry list-deprecated`
  - Show stats: `uv run python -m alphaswarm_sol.skills.registry stats`
- **Usage**:
  ```python
  from alphaswarm_sol.skills import list_registry, get_skill_entry
  skills = list_registry()
  audit = get_skill_entry("audit")
  ```
- **47 skills tracked** across 8 categories (orchestration, investigation, validation, discovery, pattern-development, tool-integration, context, development)
- **Deprecation policy**: 180-day minimum (announce → warn → sunset → removal)

### Golden Fixtures (Phase 7.1.2)
- **Location**: `tests/skills/goldens/`
- **Purpose**: Test fixtures for skill output validation
- **Validate goldens**: `uv run python scripts/update_skill_goldens.py --validate-only --verbose`
- **Update guide**: `uv run python scripts/update_skill_goldens.py --guide`
- **Test goldens**: `uv run pytest tests/skills/test_skill_goldens.py -v`
- **Test prompts**: `uv run pytest tests/skills/test_skill_prompts.py -v`
- **Available goldens**:
  - `secure_reviewer.json` - Evidence-first security review (schema: `schemas/secure_reviewer_output.json`)
  - `attacker.json` - Attack path construction
  - `defender.json` - Guard/mitigation discovery
  - `verifier.json` - Evidence cross-checking
- **Documentation**: `tests/skills/goldens/README.md`

## Testing & Validation (Mandatory Final Step)
- Run tests relevant to the change: `uv run pytest ...`
- Critique results with a subagent (e.g., `skill-auditor`)
- Document updates in `docs/` using doc-curation agent

## Testing & Validation

**Purpose:** Validate VRS workflows through automated test suites.

### When to Use

| Scenario | Tool |
|----------|------|
| Run all tests | `uv run pytest tests/ -n auto --dist loadfile` |
| Test specific module | `uv run pytest tests/test_module.py -v` |
| Benchmarks/metrics | `uv run pytest tests/metrics/` |

### Test Type Selection

| Condition | Test Type | Tool |
|-----------|-----------|------|
| Unit tests | Automated | `uv run pytest tests/` |
| Integration tests | Automated | `uv run pytest tests/integration/` |
| Benchmarks/metrics | Automated | `uv run pytest tests/metrics/` |
| Data aggregation | Automated | Direct Python |

### Output Locations

| Output Type | Location |
|-------------|----------|
| Test results | stdout / pytest reports |
| Validation reports | `.vrs/testing/reports/` |

## Planning Rule (All Phases)
- Every phase plan MUST include a **Skills/Subagents to Load** section.
- Every phase plan MUST include a **Tooling Update** step if new tools, skills, or agents are introduced.
- If tooling changes, update this file and mention it in the phase summary.

## Tool Selection Heuristics
- **Fast checks**: Haiku-tier agents or guardrails
- **Standard reasoning**: Sonnet-tier agents
- **Deep analysis**: Opus-tier agents (only when needed)
- Prefer retrieval-first and cached results over large context loads

## Model Routing (Phase 7.1.3)

**Policy:** Use tiered model routing to minimize costs while maintaining quality.

### Tier Routing Policy

- **Module**: `src/alphaswarm_sol/llm/routing_policy.py`
- **Guide**: `docs/guides/model-routing.md`
- **Tests**: `tests/test_model_routing.py`

**Quick usage:**
```python
from alphaswarm_sol.llm.routing_policy import TierRoutingPolicy, route_task
from alphaswarm_sol.llm.tiers import ModelTier

# Simple routing
decision = route_task(
    task_type="pattern_validation",
    risk_score=0.2,
    evidence_completeness=0.9,
)
# decision.tier == ModelTier.CHEAP

# High-risk routing (escalates)
decision = route_task(
    task_type="tier_b_verification",
    risk_score=0.85,
)
# decision.tier == ModelTier.PREMIUM
```

### Model Tiers

| Tier | Models | Use Case | Cost |
|------|--------|----------|------|
| CHEAP | Haiku, GPT-4o-mini | Simple validation | 0.1x |
| STANDARD | Sonnet, GPT-4o | Analysis, verification | 1.0x |
| PREMIUM | Opus, O1 | Complex reasoning | 10.0x |

### Escalation Rules

1. **Risk-based**: risk_score >= 0.5 -> STANDARD, >= 0.8 -> PREMIUM
2. **Evidence-based**: evidence_completeness < 0.3 -> escalate
3. **Severity-based**: critical/high severity -> escalate from CHEAP
4. **Pattern-based**: complex patterns (flash-loan, governance) -> PREMIUM
5. **Budget-based**: low budget forces downgrade

### Subagent Manager with Policy

```python
from alphaswarm_sol.llm.subagents import LLMSubagentManager, SubagentTask, TaskType

manager = LLMSubagentManager(budget_usd=10.0)

task = SubagentTask(
    type=TaskType.TIER_B_VERIFICATION,
    prompt="Verify this finding",
    risk_score=0.7,
    evidence_completeness=0.4,
)

result = await manager.dispatch(task)
print(result.tier_rationale)  # Why this tier was selected
```

### Configuration

Custom thresholds per pool/workflow:
```python
from alphaswarm_sol.llm.routing_policy import EscalationThresholds, TierRoutingPolicy

thresholds = EscalationThresholds(
    risk_score_standard=0.4,    # Escalate earlier
    budget_low_threshold_usd=3.0,  # Budget awareness
)
policy = TierRoutingPolicy(thresholds=thresholds)
```

## Prompt Linting & Tool Compression (Phase 7.1.3-05)

**Policy:** Lint prompts before expensive LLM calls to detect wasteful context.

### Prompt Linting

- **Module**: `src/alphaswarm_sol/llm/prompt_lint.py`
- **Guide**: `docs/guides/prompt-linting.md`
- **Tests**: `tests/test_prompt_lint.py`

**Quick usage:**
```python
from alphaswarm_sol.llm.prompt_lint import lint_prompt

report = lint_prompt(prompt_text, context={"max_tokens": 6000})

if report.has_warnings:
    print(report.summary())
    # Shows wasteful sections, duplicates, missing constraints
```

**Lint Rules:**

| Rule | Detects | Severity |
|------|---------|----------|
| `oversized-section` | Code blocks/metadata >2000 chars | WARN |
| `duplicate-context` | Repeated evidence IDs, file paths | WARN/INFO |
| `missing-constraint` | No evidence requirement, no schema | WARN/INFO |
| `unused-tool` | Tool refs not in allowed list | WARN |
| `prompt-size` | Exceeds token budget | ERROR/WARN |

**Integration:** Linting is automatic in `LLMSubagentManager._build_prompt()`. Results appear in `SubagentResult.prompt_lint_report`.

### Tool Description Compression

- **Module**: `src/alphaswarm_sol/tools/description_compress.py`
- **Tests**: `tests/test_tool_description_compress.py`

**Quick usage:**
```python
from alphaswarm_sol.tools.description_compress import compress_tool_description
from alphaswarm_sol.tools.registry import ToolRegistry

# Compress single tool
compressed = compress_tool_description(tool_info)

# Get compressed tools for LLM context
registry = ToolRegistry()
tools = registry.get_tools_for_context(max_tokens=500)

# Get minimal context string
context = registry.get_tools_context_string(max_chars=200)
# "Tools: slither(pip), aderyn(cargo), mythril(pip)"
```

**Compression Strategies:**
- Phrase abbreviations (e.g., "Static analyzer for Solidity" -> "Solidity static analyzer")
- Truncate long descriptions (80 chars default)
- Aggressive mode for tight budgets (50 chars, removes URLs)
- Minimal mode keeps only name/binary/install_hint

### When to Use

1. **Always lint before expensive model calls** (PREMIUM tier)
2. **Compress tool descriptions** when including in LLM context
3. **Monitor wasteful_tokens** in lint reports to identify patterns
4. **Use `get_tools_context_string()`** for inline tool references
