# VRS Subagents - Development Directory

This directory contains **development-only** subagent definitions used for VRS internal development. These agents are NOT shipped to end users.

## Directory Structure

```
.claude/subagents/
├── README.md                           # This file
├── secure-solidity-reviewer.md         # Dev version (more verbose, examples)
├── skill-auditor.md                    # Quality audit for skills/agents
├── cost-governor.md                    # Budget-aware routing guidance
├── gsd-context-researcher.md           # Deep Exa research for phases
└── (other development agents...)
```

---

## Development vs Shipped

| Location | Purpose | Audience | Install Command |
|----------|---------|----------|----------------|
| `.claude/subagents/` | VRS development | VRS developers | N/A (in repo) |
| `src/alphaswarm_sol/skills/shipped/agents/` | Production distribution | VRS users | `alphaswarm init` |

---

## Agents in This Directory

### secure-solidity-reviewer.md

**Status:** Has shipped version (condensed)
**Role:** secure-reviewer
**Model:** claude-sonnet-4.5

Development version of the secure reviewer agent with:
- Extended workflow examples
- Detailed VQL query syntax
- Integration patterns with VRS workflows
- Verbose mode descriptions

**Shipped version:** `src/alphaswarm_sol/skills/shipped/agents/vrs-secure-reviewer.md`

---

### skill-auditor.md

**Status:** Dev-only (not shipped)
**Role:** auditor
**Model:** claude-sonnet-4.5

Audits skill and subagent quality:
- Schema compliance validation
- Cost analysis (token budgets, model tier)
- Guardrail effectiveness
- Evidence requirement enforcement
- Output contract completeness

**Usage:**
```
Load skill-auditor when reviewing new skills or agents during development.
```

---

### cost-governor.md

**Status:** Dev-only (not shipped)
**Role:** auditor
**Model:** claude-haiku-4.5

Provides budget-aware routing recommendations:
- Model tier selection (haiku vs sonnet vs opus)
- Cost estimation for agent workflows
- Token budget enforcement
- Escalation guidance (when to use opus)

**Usage:**
```
Load cost-governor before orchestrating multi-agent workflows to optimize cost/quality tradeoff.
```

---

### gsd-context-researcher.md

**Status:** Dev-only (not shipped)
**Role:** researcher
**Model:** claude-sonnet-4.5

Deep Exa search for roadmap phase context:
- Research phase technologies and patterns
- Discover best practices and examples
- Generate phase context documents
- Source validation and provenance tracking

**Usage:**
```
Load gsd-context-researcher when creating CONTEXT.md for new roadmap phases.
```

---

## When to Use Development Agents

### During VRS Development

- **Designing new skills:** Load `skill-auditor` to validate quality
- **Planning orchestration:** Load `cost-governor` for model tier guidance
- **Researching phases:** Load `gsd-context-researcher` for deep discovery
- **Testing reviewer modes:** Use verbose `secure-solidity-reviewer.md`

### NOT for End Users

End users should **never** load agents from this directory. They should only use shipped agents via:
```bash
alphaswarm init  # Installs shipped agents
```

---

## Catalog Integration

All agents (shipped and dev-only) are registered in:
```
src/alphaswarm_sol/agents/catalog.yaml
```

**Dev-only agents** have:
- `location.shipped: null`
- `location.dev: .claude/subagents/{agent-name}.md`

**Shipped agents** have:
- `location.shipped: src/alphaswarm_sol/skills/shipped/agents/{agent-name}.md`
- `location.dev: null` (or dev version path if both exist)

See `docs/reference/subagent-catalog.md` for full catalog documentation.

---

## Agent Design Principles

All agents in this directory follow Phase 07.1.2 design system:

### 1. Frontmatter (Skill Schema v2)

```yaml
---
name: agent-name
role: attacker|defender|verifier|auditor|researcher|triage|orchestrator|architect|curator|tester
model: claude-{tier}-{version}
description: One-line purpose
---
```

**Reference:** `docs/reference/skill-schema-v2.md`

### 2. Evidence-First Contracts

All analysis agents (attacker, defender, verifier, auditor) must:
- Link exact code locations
- Cite graph node IDs
- Execute BSKG queries before conclusions
- Track known unknowns explicitly

**Reference:** `docs/reference/graph-first-template.md`

### 3. Output Contracts

Agents with structured outputs must reference schemas:
- External schemas: `schemas/{schema-name}.json`
- Embedded contracts: Required fields documented in prompt

**Reference:** `docs/reference/secure-reviewer.md` for example

### 4. Tool Permissions

Minimal permissions only:
```yaml
allowed_tools:
  - Read
  - Bash(alphaswarm*)  # Scoped, not Bash(*)
```

### 5. Context Mode

- **fork:** Isolated execution (default for agents)
- **inline:** Fast, less isolated (only for quick checks)

---

## Creating New Development Agents

### Step 1: Design

1. Determine role (see catalog for role definitions)
2. Select model tier (haiku/sonnet/opus based on task complexity)
3. Define output contract (JSON schema or embedded)
4. Specify tool permissions (minimal)
5. Set evidence requirements (if analysis agent)

**Tool:** Load `/agent-skillcraft` skill for guided design

### Step 2: Author

1. Create `.claude/subagents/{agent-name}.md`
2. Add frontmatter with skill schema v2 fields
3. Document role and workflow
4. Specify output contract
5. Include examples and anti-patterns

**Reference:** Use existing agents as templates

### Step 3: Register

1. Add entry to `src/alphaswarm_sol/agents/catalog.yaml`
2. Set `location.shipped: null` for dev-only
3. Set `location.dev: .claude/subagents/{agent-name}.md`
4. Update catalog statistics

### Step 4: Document

1. Update `docs/reference/subagent-catalog.md`
2. Add agent to appropriate category
3. Document purpose and integration points
4. Update this README if needed

### Step 5: Test

1. Load agent in development session
2. Validate output contract compliance
3. Test evidence requirements enforcement
4. Run `skill-auditor` for quality check

---

## Quality Standards

All development agents must meet:

### Schema Compliance

- Valid frontmatter (skill schema v2)
- Required fields present
- Role in allowed enum
- Model tier valid

**Validator:** `python scripts/validate_skill_schema.py .claude/subagents/{agent-name}.md`

### Output Contracts

- Clear required fields
- Schema reference (if external)
- Example outputs
- Validation rules

### Evidence Requirements

Analysis agents must enforce:
- `must_link_code: true`
- `cite_graph_nodes: true`
- `graph_first: true`
- `min_evidence_items: N` (based on role)

### Documentation

- Purpose (one-line + extended)
- Workflow description
- Integration points
- Examples (good and bad)
- Anti-patterns

---

## Migration to Shipped

To promote a dev-only agent to shipped:

### 1. Condense Prompt

- Remove verbose examples
- Keep core workflow
- Remove development-specific notes
- Focus on essentials

### 2. Create Shipped Version

```bash
# Copy and condense
cp .claude/subagents/{agent}.md src/alphaswarm_sol/skills/shipped/agents/vrs-{agent}.md
# Edit for end users
```

### 3. Update Catalog

```yaml
location:
  shipped: src/alphaswarm_sol/skills/shipped/agents/vrs-{agent}.md
  dev: .claude/subagents/{agent}.md  # Keep dev version for reference
```

### 4. Update Documentation

- Add to shipped agents table in `src/alphaswarm_sol/skills/shipped/README.md`
- Update `docs/reference/subagent-catalog.md`
- Update `.planning/TOOLING.md` if workflow changes

### 5. Test Distribution

```bash
# Test that init copies agent
alphaswarm init --force
ls .claude/vrs/agents/vrs-{agent}.md
```

---

## References

### Primary Documentation

- **Catalog:** `docs/reference/subagent-catalog.md`
- **Skill Schema:** `docs/reference/skill-schema-v2.md`
- **Graph-First Template:** `docs/reference/graph-first-template.md`
- **Secure Reviewer:** `docs/reference/secure-reviewer.md`

### Development Guides

- **Skill Design:** Load `/agent-skillcraft` skill
- **Quality Audit:** Load `skill-auditor` agent
- **Cost Optimization:** Load `cost-governor` agent
- **Phase Research:** Load `gsd-context-researcher` agent

### Tooling

- **Agent Selection:** `.planning/TOOLING.md`
- **Shipped Agents:** `src/alphaswarm_sol/skills/shipped/README.md`
- **Orchestration:** `src/alphaswarm_sol/orchestration/`

---

**Maintained by:** VRS Core Team
**Phase:** 07.1.2-skill-subagent-design-system
**Status:** Production-ready catalog and design system
