# Skill Schema v2 Reference

Canonical schema for AlphaSwarm.sol skills and subagents with evidence-first contracts.

## Purpose

Skill Schema v2 standardizes frontmatter for skills used in Claude Code and Codex orchestration. It enforces:

- **Evidence-first reasoning**: Skills must link claims to exact code locations
- **Graph-first analysis**: Skills must query BSKG before manual code reading
- **Role contracts**: Clear boundaries for attacker/defender/verifier/orchestrator roles
- **Output contracts**: Structured, testable outputs with schema validation
- **Token budgets**: Cost-aware execution with 6k default budget

## Schema Location

**Canonical source:** `schemas/skill_schema_v2.json`

**Validation:** `python scripts/validate_skill_schema.py`

## Required Fields

### Core Identification

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Unique skill identifier (kebab-case, e.g., `vrs-audit`) |
| `description` | string | Human-readable description of skill purpose |
| `slash_command` | string | Slash command trigger (e.g., `vrs-audit`) |
| `version` | string | Semantic version (e.g., `1.0.0`) |

### Runtime Configuration

| Field | Type | Values | Description |
|-------|------|--------|-------------|
| `context` | enum | `fork`, `inline` | Context isolation mode |
| `role` | enum | `attacker`, `defender`, `verifier`, `auditor`, `researcher`, `triage`, `orchestrator`, `architect`, `curator`, `tester` | Primary role in workflows |
| `model_tier` | enum | `haiku`, `sonnet`, `opus`, `adaptive` | Recommended model tier |

**Context modes:**
- **`fork`**: Isolated execution, tool output doesn't pollute main context (default for most skills)
- **`inline`**: Direct execution, fast but less isolated (for quick checks)

**Model tiers:**
- **`haiku`**: Fast, cost-efficient (filtering, mechanical extraction)
- **`sonnet`**: Balanced quality/cost (most skills)
- **`opus`**: Creative, adversarial thinking (attacker, verifier)
- **`adaptive`**: Runtime decision based on task complexity

### Tool Permissions

| Field | Type | Description |
|-------|------|-------------|
| `tools` | array[string] | Allowed tool permissions |

**Examples:**
```yaml
tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash(alphaswarm*)
  - mcp__exa-search__web_search_exa
```

**Principles:**
- Minimal permissions (only what skill needs)
- Use glob patterns for scoped bash commands (e.g., `Bash(alphaswarm*)`)
- Avoid overly broad permissions like `Bash(*)`

### Evidence Requirements

| Field | Type | Description |
|-------|------|-------------|
| `evidence_requirements` | object | Evidence contract for skill outputs |

**Required subfields:**

| Field | Type | Description |
|-------|------|-------------|
| `must_link_code` | boolean | Requires exact code locations (file, line, function) |
| `min_evidence_items` | integer | Minimum evidence items per finding (0+ allowed) |
| `cite_graph_nodes` | boolean | Requires BSKG node references (function IDs, contract names) |

**Optional subfields:**

| Field | Type | Description |
|-------|------|-------------|
| `graph_first` | boolean | Must query BSKG before reading code manually |
| `require_behavioral_signature` | boolean | Requires semantic operation signatures (e.g., `R:bal→X:out→W:bal`) |

**Example (strict evidence contract):**
```yaml
evidence_requirements:
  must_link_code: true
  min_evidence_items: 3
  cite_graph_nodes: true
  graph_first: true
  require_behavioral_signature: true
```

**Example (relaxed contract for research):**
```yaml
evidence_requirements:
  must_link_code: false
  min_evidence_items: 0
  cite_graph_nodes: false
  graph_first: false
```

### Output Contract

| Field | Type | Description |
|-------|------|-------------|
| `output_contract` | object | Structured output contract for skill results |

**Required subfields:**

| Field | Type | Values | Description |
|-------|------|--------|-------------|
| `format` | enum | `json`, `yaml`, `markdown`, `toon` | Output format |
| `schema` | string or object | Path to schema or inline schema | Output structure |

**Optional subfields:**

| Field | Type | Description |
|-------|------|-------------|
| `fields` | array[string] | Required output fields |

**Example (external schema reference):**
```yaml
output_contract:
  format: json
  schema: schemas/verdict_output.json
  fields:
    - confidence
    - evidence_packet
    - attack_path
```

**Example (inline schema):**
```yaml
output_contract:
  format: yaml
  schema:
    type: object
    required: [status, findings, metadata]
    properties:
      status:
        type: string
        enum: [complete, partial, blocked]
      findings:
        type: array
        items:
          type: object
          required: [id, severity, evidence]
      metadata:
        type: object
  fields:
    - status
    - findings
```

### Failure Modes

| Field | Type | Description |
|-------|------|-------------|
| `failure_modes` | array[object] | Known failure modes and resolutions |

**Required subfields per failure mode:**

| Field | Type | Description |
|-------|------|-------------|
| `condition` | string | Failure condition description |
| `resolution` | string | How to resolve the failure |

**Optional subfields:**

| Field | Type | Description |
|-------|------|-------------|
| `recoverable` | boolean | Whether failure is automatically recoverable |

**Example:**
```yaml
failure_modes:
  - condition: "No Solidity files found"
    resolution: "Verify path contains .sol files"
    recoverable: false
  - condition: "Graph build failed"
    resolution: "Check Slither installation with /vrs-health-check"
    recoverable: false
  - condition: "Agent spawn failed"
    resolution: "Check model availability and retry"
    recoverable: true
```

## Optional Fields

### Token Budget

| Field | Type | Default | Range | Description |
|-------|------|---------|-------|-------------|
| `max_token_budget` | integer | 6000 | 1000-10000 | Maximum token budget for skill execution |

**Rationale for 6k default:**
- Fits comfortably within 8k model context window
- Leaves 2k buffer for system prompts and tool outputs
- Prevents runaway token consumption
- Most skills complete well under 6k

**When to override:**
- **< 6k**: Quick checks, filtering tasks (e.g., 2000 for health checks)
- **> 6k**: Complex orchestration, multi-round debates (e.g., 8000 for full audits)
- **Never exceed 10k** without explicit justification

### Deprecation Fields

| Field | Type | Description |
|-------|------|-------------|
| `deprecated` | boolean | Whether skill is deprecated (default: false) |
| `replaces` | string | Name of skill this one replaces |
| `deprecates` | array[string] | List of skills this one deprecates |
| `sunset_date` | string | Removal date (YYYY-MM-DD) |

**Example (deprecation):**
```yaml
name: vrs-audit-v1
deprecated: true
replaces: vrs-audit-legacy
sunset_date: 2026-06-01
```

### Invocation Control

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `disable_model_invocation` | boolean | false | If true, only users can invoke (not agents) |

**Use cases for `disable_model_invocation: true`:**
- User-facing orchestrators (e.g., `/vrs-audit`)
- Installation validators (e.g., `/vrs-health-check`)
- Resume coordinators (e.g., `/vrs-orch-resume`)

**Use cases for `disable_model_invocation: false` (default):**
- Worker skills (e.g., `/vrs-investigate`)
- Tool wrappers (e.g., `/vrs-tool-slither`)
- Subagents (e.g., attacker/defender/verifier)

### Metadata Fields

| Field | Type | Description |
|-------|------|-------------|
| `tags` | array[string] | Searchable tags for skill discovery |
| `references` | array[string] | External docs or context files |
| `write_boundaries` | array[string] | Directories skill can write to |

**Example:**
```yaml
tags:
  - security
  - audit
  - orchestration
references:
  - skills/vrs/references/debate-protocol.md
  - docs/guides/patterns-basics.md
write_boundaries:
  - .claude/vrs/
  - .beads/
```

## Complete Example

**Production skill with strict evidence contract:**

```yaml
---
name: vrs-verify
description: |
  Multi-agent verification with attacker/defender/verifier roles.
  Spawns agents to construct exploits, find guards, and synthesize verdicts.
slash_command: vrs-verify
context: fork
role: verifier
model_tier: opus
tools:
  - Read
  - Glob
  - Grep
  - Bash(alphaswarm*)
evidence_requirements:
  must_link_code: true
  min_evidence_items: 3
  cite_graph_nodes: true
  graph_first: true
  require_behavioral_signature: true
output_contract:
  format: json
  schema: schemas/verdict_output.json
  fields:
    - confidence
    - evidence_packet
    - attack_path
    - defense_claims
    - verdict_summary
failure_modes:
  - condition: "Attacker spawn failed"
    resolution: "Check model availability and retry"
    recoverable: true
  - condition: "Insufficient evidence"
    resolution: "Return UNCERTAIN verdict with human flag"
    recoverable: false
  - condition: "Debate timeout"
    resolution: "Escalate to human arbitration"
    recoverable: false
version: 1.0.0
max_token_budget: 8000
disable_model_invocation: false
tags:
  - security
  - verification
  - multi-agent
references:
  - skills/vrs/references/debate-protocol.md
write_boundaries:
  - .claude/vrs/
  - .beads/
---

# VRS Verify Skill
...
```

**Research skill with relaxed contract:**

```yaml
---
name: knowledge-aggregation-worker
description: |
  Automated VulnDocs discovery via Exa search.
  Finds vulnerability sources, extracts patterns, validates against corpus.
slash_command: vrs-discover
context: fork
role: researcher
model_tier: sonnet
tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - mcp__exa-search__web_search_exa
evidence_requirements:
  must_link_code: false
  min_evidence_items: 0
  cite_graph_nodes: false
  graph_first: false
output_contract:
  format: yaml
  schema:
    type: object
    required: [sources, patterns_found, next_steps]
  fields:
    - sources
    - patterns_found
failure_modes:
  - condition: "Exa search failed"
    resolution: "Retry with adjusted query"
    recoverable: true
  - condition: "No relevant sources found"
    resolution: "Refine search query and retry"
    recoverable: true
version: 1.0.0
max_token_budget: 4000
tags:
  - research
  - discovery
  - vulndocs
write_boundaries:
  - vulndocs/
  - .planning/research/
---

# Knowledge Aggregation Worker
...
```

## Validation

**Validate skill frontmatter against schema v2:**

```bash
# Validate single skill
python scripts/validate_skill_schema.py skills/vrs-legacy/audit.md

# Validate all shipped skills
python scripts/validate_skill_schema.py src/alphaswarm_sol/shipping/skills/

# Validate all repo skills
python scripts/validate_skill_schema.py skills/

# Strict mode (fail on warnings)
python scripts/validate_skill_schema.py --strict skills/

# Warn mode (report violations but don't fail)
python scripts/validate_skill_schema.py --warn skills/
```

## Migration from Schema v1

**Schema v1 → v2 changes:**

| v1 Field | v2 Equivalent | Action |
|----------|---------------|--------|
| `allowed-tools` | `tools` | Rename |
| N/A | `role` | Add (required) |
| N/A | `model_tier` | Add (required) |
| N/A | `evidence_requirements` | Add (required) |
| N/A | `output_contract` | Add (required) |
| N/A | `failure_modes` | Add (required) |
| N/A | `version` | Add (required) |

**Migration checklist:**
1. Rename `allowed-tools` to `tools`
2. Add `role` field (choose from enum)
3. Add `model_tier` (haiku/sonnet/opus/adaptive)
4. Add `evidence_requirements` object
5. Add `output_contract` object
6. Document `failure_modes` array
7. Add semantic `version` (start with `1.0.0`)
8. Review and set `max_token_budget` if non-default
9. Validate with `scripts/validate_skill_schema.py`

**Example migration:**

**Before (v1):**
```yaml
---
name: vrs-audit
description: Main VRS audit skill
slash_command: vrs-audit
context: fork
allowed-tools:
  - Read
  - Bash(alphaswarm*)
---
```

**After (v2):**
```yaml
---
name: vrs-audit
description: Main VRS audit skill
slash_command: vrs-audit
context: fork
role: orchestrator
model_tier: sonnet
tools:
  - Read
  - Bash(alphaswarm*)
evidence_requirements:
  must_link_code: true
  min_evidence_items: 2
  cite_graph_nodes: true
  graph_first: true
output_contract:
  format: json
  schema: schemas/audit_report.json
  fields:
    - findings
    - verdicts
failure_modes:
  - condition: "No Solidity files found"
    resolution: "Verify path contains .sol files"
version: 1.0.0
max_token_budget: 8000
---
```

## Role Definitions

| Role | Purpose | Typical Model | Evidence Contract |
|------|---------|---------------|-------------------|
| `attacker` | Construct exploit paths | opus | Strict (code + behavioral) |
| `defender` | Find guards/mitigations | sonnet | Strict (code + graph nodes) |
| `verifier` | Synthesize verdicts | opus | Strict (code + evidence packet) |
| `auditor` | Full audit orchestration | sonnet | Moderate (findings + verdicts) |
| `researcher` | Discover vulnerabilities | sonnet | Relaxed (sources + patterns) |
| `triage` | Filter/prioritize findings | haiku | Minimal (category + severity) |
| `orchestrator` | Coordinate workflows | sonnet | Moderate (status + metadata) |
| `architect` | Design skills/patterns | sonnet | Minimal (structure + contracts) |
| `curator` | Validate/merge knowledge | sonnet | Moderate (provenance + quality) |
| `tester` | Validate patterns | haiku/sonnet | Strict (metrics + coverage) |

## Output Contract Patterns

### Pattern 1: Structured Verdict

```yaml
output_contract:
  format: json
  schema: schemas/verdict_output.json
  fields:
    - confidence
    - evidence_packet
    - attack_path
    - defense_claims
```

**Use for:** Verification skills, debate outcomes

### Pattern 2: Finding List

```yaml
output_contract:
  format: json
  schema: schemas/findings_list.json
  fields:
    - findings
    - metadata
    - summary
```

**Use for:** Audit results, pattern detection

### Pattern 3: Research Synthesis

```yaml
output_contract:
  format: yaml
  schema:
    type: object
    required: [sources, insights, next_steps]
  fields:
    - sources
    - insights
    - patterns_found
```

**Use for:** Discovery, research tasks

### Pattern 4: Status Report

```yaml
output_contract:
  format: markdown
  schema: schemas/status_report.json
  fields:
    - status
    - progress
    - blockers
```

**Use for:** Orchestration checkpoints, health checks

## Common Failure Modes

### Tool Availability

```yaml
- condition: "Tool not installed (Slither, Aderyn, etc.)"
  resolution: "Run /vrs-health-check to validate installation"
  recoverable: false
```

### Input Validation

```yaml
- condition: "No Solidity files found"
  resolution: "Verify path contains .sol files"
  recoverable: false

- condition: "Invalid contract scope"
  resolution: "Check contract names exist in codebase"
  recoverable: false
```

### Agent Failures

```yaml
- condition: "Agent spawn failed"
  resolution: "Check model availability and retry"
  recoverable: true

- condition: "Debate timeout"
  resolution: "Escalate to human arbitration"
  recoverable: false
```

### Evidence Gaps

```yaml
- condition: "Insufficient evidence"
  resolution: "Return UNCERTAIN verdict with human flag"
  recoverable: false

- condition: "Graph query failed"
  resolution: "Rebuild graph and retry"
  recoverable: true
```

## Schema Versioning

**Current version:** 2.0.0

**Version history:**
- **1.0.0**: Initial schema (Phase 5.6)
- **2.0.0**: Added evidence_requirements, output_contract, failure_modes (Phase 7.1.2)

**Breaking changes (1.x → 2.x):**
- Added required fields: `role`, `model_tier`, `evidence_requirements`, `output_contract`, `failure_modes`, `version`
- Renamed `allowed-tools` → `tools`

**Migration guide:** See "Migration from Schema v1" section above

## Best Practices

### Evidence Requirements

**Do:**
- Set `must_link_code: true` for security skills
- Require `cite_graph_nodes: true` for pattern detection
- Enable `graph_first: true` to prevent manual code reading hallucinations
- Use `require_behavioral_signature: true` for operation-based detection

**Don't:**
- Set all fields to `false` for security skills (defeats purpose)
- Over-constrain research skills (blocks exploration)
- Mix strict and relaxed contracts in same workflow (inconsistent standards)

### Output Contracts

**Do:**
- Reference external schemas for reusable structures
- Document required fields explicitly
- Use TOON format for token efficiency with uniform arrays
- Validate outputs against schema in tests

**Don't:**
- Inline complex schemas (hard to maintain)
- Omit required fields from contract
- Use unstructured markdown for critical outputs

### Failure Modes

**Do:**
- Document all known failure conditions
- Provide actionable resolutions
- Mark recoverable failures for retry logic
- Test failure paths in skill tests

**Don't:**
- Leave failure modes empty (skills always have failure cases)
- Provide vague resolutions ("fix it")
- Assume all failures are recoverable

### Token Budgets

**Do:**
- Profile skill token usage in tests
- Set budget 20% above average usage
- Document why non-default budgets are needed
- Monitor budget violations in production

**Don't:**
- Set arbitrarily high budgets (10k+)
- Ignore budget overruns
- Use same budget for all skills

## Tooling Integration

**Validation in CI:**
```bash
# .github/workflows/skill-validation.yml
- name: Validate skill schemas
  run: |
    python scripts/validate_skill_schema.py --strict src/alphaswarm_sol/shipping/skills/
    python scripts/validate_skill_schema.py --strict skills/
```

**Pre-commit hook:**
```bash
# .git/hooks/pre-commit
#!/bin/bash
python scripts/validate_skill_schema.py --strict $(git diff --cached --name-only | grep -E '\.md$')
```

**Skill linting:**
```bash
# Check all skills for schema compliance
uv run pytest tests/skills/test_skill_schema_v2.py -v

# Check specific skill
python scripts/validate_skill_schema.py skills/vrs-legacy/audit.md
```

## Related Documentation

- [Skills Basics](../guides/skills-basics.md) - Using VRS skills
- [Skills Authoring](../guides/skills-authoring.md) - Advanced skill topics
- [PHILOSOPHY.md](../PHILOSOPHY.md) - Evidence-first principles
- [TOOLING.md](../../.planning/TOOLING.md) - Tool selection guide

## Support

**Schema validation errors:**
1. Run `python scripts/validate_skill_schema.py <skill-file>` for details
2. Check required fields are present
3. Verify enum values match schema
4. Validate nested objects (evidence_requirements, output_contract)

**Schema questions:**
- Open issue with `skill-schema` label
- Tag @skill-architect for design questions
- Refer to examples in `src/alphaswarm_sol/shipping/skills/`
