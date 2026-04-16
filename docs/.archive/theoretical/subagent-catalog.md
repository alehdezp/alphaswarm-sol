# Subagent Catalog Reference

Canonical registry of all VRS agents with roles, models, output contracts, and evidence requirements.

**Catalog Location:** `src/alphaswarm_sol/agents/catalog.yaml`

**Version:** 1.0.0
**Last Updated:** 2026-01-29

---

## Purpose

The subagent catalog serves as the **single source of truth** for:

1. **Agent metadata** - Role, model tier, purpose
2. **Output contracts** - Required fields and schema references
3. **Tool permissions** - Allowed tools per agent
4. **Evidence requirements** - Graph-first and evidence-first enforcement
5. **Location tracking** - Shipped vs development agent paths

---

## Catalog Structure

Each agent entry contains:

| Field | Description |
|-------|-------------|
| `id` | Unique agent identifier (e.g., `vrs-attacker`) |
| `name` | Human-readable agent name |
| `role` | Agent role in workflows (attacker, defender, verifier, etc.) |
| `model_tier` | Recommended model (haiku, sonnet, opus, adaptive) |
| `purpose` | One-line description of agent's function |
| `output_contract` | Expected output structure and schema |
| `allowed_tools` | Tool permissions (Read, Write, Bash, etc.) |
| `default_context` | Context mode (fork or inline) |
| `evidence_requirements` | Evidence-first and graph-first enforcement rules |
| `location` | File paths for shipped and dev versions |

---

## Agent Categories

### Core Verification Agents (3)

The primary agents for vulnerability verification via attacker/defender/verifier debate protocol.

| Agent | Role | Model | Purpose |
|-------|------|-------|---------|
| **vrs-attacker** | attacker | opus | Constructs exploit paths and attack vectors |
| **vrs-defender** | defender | sonnet | Searches for guards and mitigations |
| **vrs-verifier** | verifier | opus | Cross-checks evidence and synthesizes verdicts |

**Evidence Requirements:** All require `graph_first: true`, `must_link_code: true`, `cite_graph_nodes: true`

---

### Secure Reviewer Agent (1)

Hybrid agent combining creative attack thinking with adversarial skepticism.

| Agent | Role | Model | Purpose |
|-------|------|-------|---------|
| **vrs-secure-reviewer** | secure-reviewer | sonnet | Creative attack + adversarial refutation with evidence-first reasoning |

**Output Contract:** `schemas/secure_reviewer_output.json` (JSON schema)

**Modes:**
- **Creative:** Generates attack hypotheses
- **Adversarial:** Challenges and refutes claims

---

### Orchestration & Coordination Agents (2)

Workflow management and verdict integration.

| Agent | Role | Model | Purpose |
|-------|------|-------|---------|
| **vrs-supervisor** | orchestrator | sonnet | Coordinates multi-agent workflows and debate protocol |
| **vrs-integrator** | orchestrator | sonnet | Merges verdicts and generates audit reports |

**Evidence Requirements:** `graph_first: false` (coordination only, not analysis)

---

### Pattern & Discovery Agents (3)

Pattern triage, verification, and composite vulnerability discovery.

| Agent | Role | Model | Purpose |
|-------|------|-------|---------|
| **vrs-pattern-scout** | triage | haiku | Fast pattern triage for candidate findings |
| **vrs-pattern-verifier** | verifier | sonnet | Verifies Tier B/C matches with evidence gates |
| **vrs-pattern-composer** | architect | sonnet | Discovers composite vulnerabilities via semantic operation algebra |

**Pattern Composer Specialization:** Requires `require_behavioral_signature: true` for operation sequences

---

### Context & Evidence Agents (3)

Evidence synthesis, deduplication, and context packing.

| Agent | Role | Model | Purpose |
|-------|------|-------|---------|
| **vrs-context-packer** | curator | sonnet | Assembles Pattern Context Packs (PCP) for batch discovery |
| **vrs-finding-merger** | curator | sonnet | Merges duplicate findings deterministically |
| **vrs-finding-synthesizer** | curator | sonnet | Merges convergent evidence with confidence bounds |

**Context Packer Output:** `schemas/pattern_context_pack_v2.json`

---

### Adversarial Agent (1)

Refutation-only adversarial review.

| Agent | Role | Model | Purpose |
|-------|------|-------|---------|
| **vrs-contradiction** | adversarial | sonnet | Challenges findings with counter-evidence, never confirms |

**Specialization:** Only generates refutations, no confirmations

---

### Validation Pipeline Agents (8)

Quality gates and validation orchestration for VulnDocs changes (Phase 7.2).

| Agent | Role | Model | Purpose |
|-------|------|-------|---------|
| **vrs-test-conductor** | orchestrator | opus | Orchestrates validation pipeline, enforces quality gates |
| **vrs-corpus-curator** | curator | sonnet | Validates corpus integrity and ground truth |
| **vrs-benchmark-runner** | tester | haiku | Executes benchmarks, computes precision/recall |
| **vrs-mutation-tester** | tester | haiku | Generates contract variants for robustness testing |
| **vrs-regression-hunter** | tester | sonnet | Detects accuracy degradation, finds root cause |
| **vrs-gap-finder** | auditor | opus | Comprehensive coverage gap analysis |
| **vrs-gap-finder-lite** | auditor | sonnet | Fast coverage scan with escalation flag |
| **vrs-prevalidator** | triage | haiku | Fast gate: provenance, schema, duplicates |

**Pipeline Order:**
1. prevalidator (fast gate)
2. corpus-curator (integrity)
3. pattern-verifier (Tier B/C)
4. benchmark-runner (metrics)
5. mutation-tester (conditional)
6. regression-hunter (conditional)
7. gap-finder-lite (escalates to gap-finder if needed)

---

### Development-Only Agents (3)

Internal agents for VRS development, not shipped to end users.

| Agent | Role | Model | Purpose |
|-------|------|-------|---------|
| **skill-auditor** | auditor | sonnet | Audits skill/subagent quality, cost, guardrails |
| **cost-governor** | auditor | haiku | Budget-aware routing recommendations |
| **gsd-context-researcher** | researcher | sonnet | Deep Exa research for roadmap phase context |

**Location:** `.claude/subagents/` (not in `src/alphaswarm_sol/skills/shipped/`)

---

## Role Definitions

| Role | Purpose | Evidence Requirements |
|------|---------|----------------------|
| **attacker** | Constructs exploit paths | High (graph-first, code links, 3+ items) |
| **defender** | Finds guards/mitigations | High (graph-first, code links, 2+ items) |
| **verifier** | Synthesizes verdicts | Very High (graph-first, code links, 5+ items) |
| **secure-reviewer** | Creative + adversarial | High (graph-first, code links, 1+ items) |
| **orchestrator** | Workflow coordination | None (coordination only) |
| **triage** | Fast filtering | Low-Medium (1+ item, graph-first) |
| **architect** | Pattern design | High (behavioral signatures required) |
| **curator** | Evidence management | Medium (2+ items, graph-first) |
| **adversarial** | Refutation only | High (counter-evidence, graph-first) |
| **tester** | Validation execution | None (executes tests) |
| **auditor** | Quality analysis | Medium (1+ item for gap-finder) |
| **researcher** | Knowledge discovery | None (external research) |

---

## Model Tier Guidelines

| Tier | Models | Use Case | Cost |
|------|--------|----------|------|
| **haiku** | claude-haiku-4.5 | Filtering, mechanical extraction, fast gates | Lowest |
| **sonnet** | claude-sonnet-4.5 | Most agents, balanced quality/cost | Medium |
| **opus** | claude-opus-4.5 | Creative reasoning, adversarial thinking, verdict synthesis | Highest |
| **adaptive** | Runtime decision | Complex orchestration (not used yet) | Variable |

**Cost Optimization:** Use cost-governor agent for routing recommendations.

---

## Output Contracts

### JSON Schema References

Agents with external schema files:

| Agent | Schema | Location |
|-------|--------|----------|
| vrs-secure-reviewer | secure_reviewer_output.json | `schemas/secure_reviewer_output.json` |
| vrs-context-packer | pattern_context_pack_v2.json | `schemas/pattern_context_pack_v2.json` |

### Embedded Contracts

Most agents have output contracts embedded in their prompt files with required fields documented inline.

**Common Required Fields:**
- **Verification agents:** verdict, confidence, evidence_quality, rationale
- **Triage agents:** triage_decision, confidence, quick_rationale
- **Validation agents:** gate results, issues, recommendations

---

## Evidence Requirements

All verification agents enforce evidence-first reasoning:

### Required for Analysis Agents

```yaml
evidence_requirements:
  must_link_code: true          # Exact code locations required
  min_evidence_items: 3         # Minimum evidence items (varies by agent)
  cite_graph_nodes: true        # Graph node IDs required
  graph_first: true             # BSKG queries before manual reading
  require_behavioral_signature: false  # Operation sequences (pattern-composer only)
```

### Disabled for Coordination Agents

Orchestrators, testers, and triagers have relaxed requirements since they coordinate rather than analyze.

---

## Tool Permissions

### Common Patterns

**Analysis agents (attacker, defender, verifier):**
```yaml
allowed_tools:
  - Read
  - Grep
  - Glob
  - Bash(alphaswarm*)
```

**Curation agents (context-packer, finding-merger):**
```yaml
allowed_tools:
  - Read
  - Write
  - Bash(alphaswarm*)
```

**Research agents:**
```yaml
allowed_tools:
  - Read
  - mcp__exa-search__web_search_exa
```

**Principle:** Minimal permissions, scoped Bash access via glob patterns.

---

## Location Tracking

### Shipped Agents (21)

Located in `src/alphaswarm_sol/skills/shipped/agents/` and distributed to end users via `alphaswarm init`.

### Development Agents (3)

Located in `.claude/subagents/` and used only for VRS internal development.

**Dual-Location Agents:**
- **vrs-secure-reviewer** has both shipped and dev versions (different levels of detail)

---

## Catalog Statistics

- **Total Agents:** 24
- **Shipped:** 21
- **Dev-Only:** 3

**By Role:**
- Attacker: 1
- Defender: 1
- Verifier: 2
- Orchestrator: 3
- Triage: 3
- Architect: 1
- Curator: 4
- Adversarial: 1
- Tester: 3
- Auditor: 3
- Researcher: 1

**By Model Tier:**
- Opus: 3
- Sonnet: 14
- Haiku: 4
- Adaptive: 0

---

## Update Policy

### When to Update Catalog

1. **New agent added** - Add entry with all required fields
2. **Agent role changes** - Update role and evidence requirements
3. **Model tier changes** - Update model_tier after testing
4. **Output contract changes** - Update schema_ref or required_fields
5. **Tool permissions change** - Update allowed_tools
6. **Agent deprecated** - Add deprecation notice, don't remove (for history)

### Update Procedure

1. Edit `src/alphaswarm_sol/agents/catalog.yaml`
2. Update catalog statistics at bottom
3. Validate catalog schema (see below)
4. Update this reference doc
5. Commit both files together

### Validation

```bash
# Validate catalog schema (TODO: implement validator)
python scripts/validate_agent_catalog.py

# List all agents
python -c "from alphaswarm_sol.agents.catalog import list_subagents; print(list_subagents())"

# Get specific agent
python -c "from alphaswarm_sol.agents.catalog import get_subagent; print(get_subagent('vrs-attacker'))"
```

---

## Usage in Code

### Load Catalog

```python
from alphaswarm_sol.agents.catalog import list_subagents, get_subagent

# List all agents
agents = list_subagents()

# Get specific agent
attacker = get_subagent("vrs-attacker")
print(attacker.role)  # "attacker"
print(attacker.model_tier)  # "opus"
print(attacker.evidence_requirements.graph_first)  # True
```

### Filter by Role

```python
from alphaswarm_sol.agents.catalog import list_subagents

# Get all verifiers
verifiers = [a for a in list_subagents() if a.role == "verifier"]

# Get all opus-tier agents
opus_agents = [a for a in list_subagents() if a.model_tier == "opus"]
```

### Validate Agent Config

```python
from alphaswarm_sol.agents.catalog import validate_catalog

# Validate all entries
issues = validate_catalog()
if issues:
    print("Catalog validation failed:", issues)
```

---

## Integration Points

### Orchestration Layer

The orchestration layer (`src/alphaswarm_sol/orchestration/`) uses the catalog to:
- Select appropriate agents for workflow steps
- Validate agent output against contracts
- Enforce evidence requirements
- Route based on model tier and cost

### Skills

Skills reference catalog entries to:
- Spawn agents with correct configuration
- Validate agent responses
- Document agent usage

### Documentation

Documentation references catalog for:
- Agent capability tables
- Model tier recommendations
- Cost estimation

---

## Future Enhancements

### Planned (Not Yet Implemented)

1. **JSON schema validation** - Validate catalog.yaml against schema
2. **Output contract validation** - Validate agent responses against contracts
3. **Cost tracking** - Track token usage per agent
4. **Performance metrics** - Track agent execution time and quality
5. **A/B testing** - Compare different model tiers for same role
6. **Adaptive routing** - Runtime model selection based on task complexity

### Under Consideration

- **Versioning** - Track agent version history
- **Deprecation** - Formal agent deprecation process
- **Aliases** - Allow multiple IDs for same agent
- **Teams** - Group agents for complex workflows

---

## References

- **Skill Schema v2:** `docs/reference/skill-schema-v2.md`
- **Graph-First Template:** `docs/reference/graph-first-template.md`
- **Secure Reviewer:** `docs/reference/secure-reviewer.md`
- **Pattern Context Packs:** `schemas/pattern_context_pack_v2.json`
- **TOOLING Guide:** `.planning/TOOLING.md`

---

**Maintained by:** VRS Core Team
**Questions/Issues:** See `.planning/TOOLING.md` for agent selection guidance
