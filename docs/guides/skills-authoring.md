# Skills Authoring Guide

**Schema v2, orchestration triggers, and writing VRS skills.**

**Prerequisites:** [Skills Basics](skills-basics.md)

---

## Skill Schema v2

All VRS skills use **Skill Schema v2** for standardized frontmatter.

**Key features:**
- **Role contracts**: attacker/defender/verifier/orchestrator
- **Evidence requirements**: Must link code, cite graph nodes
- **Output contracts**: Structured, testable outputs
- **Token budgets**: 6k default budget
- **Failure modes**: Documented error conditions

**Schema reference:** [docs/reference/skill-schema-v2.md](../reference/skill-schema-v2.md)

### Validation

```bash
# Validate single skill
python scripts/validate_skill_schema.py skills/vrs-legacy/audit.md

# Validate all shipped skills
python scripts/validate_skill_schema.py src/alphaswarm_sol/shipping/skills/

# Strict mode
python scripts/validate_skill_schema.py --strict skills/
```

---

## Skill Registry

**Location:** `src/alphaswarm_sol/skills/registry.yaml`

**Features:**
- Version tracking (semantic versioning)
- Lifecycle status (active, experimental, deprecated, sunset)
- 180-day minimum sunset period
- `workflow_refs` links to workflow contracts

```bash
# Validate registry
uv run python -m alphaswarm_sol.skills.registry validate

# List deprecated
uv run python -m alphaswarm_sol.skills.registry list-deprecated
```

---

## Skill Locations (Source of Truth)

**Product skills (canonical):** `src/alphaswarm_sol/shipping/skills/`
**Dev skills:** `.claude/skills/` (real files, not shipped)
**Runtime install target:** `.claude/skills/` inside user projects (`alphaswarm init`)

**Rule:** Product skills are edited in `src/alphaswarm_sol/shipping/skills/` and symlinked into `.claude/skills/` for local development. Dev-only skills live directly in `.claude/skills/`.

---

## Orchestration Trigger Matrix

| Condition | `/vrs-context-pack` | `/vrs-pattern-batch` | `/vrs-pattern-verify` |
|-----------|---------------------|----------------------|-----------------------|
| No cached PCP | RUN | WAIT | WAIT |
| PCP cached + hash match | SKIP | RUN | RUN |
| Single pattern | RUN | SKIP | RUN |
| Budget exhausted | DEFER | DEFER | DEFER |

### Protocol Context Decision

| Scenario | Include? | Rationale |
|----------|----------|-----------|
| Pack < 500 tokens | YES | Low cost, high value |
| Pack 500-2000 tokens | YES (if budget) | Record cost |
| Pack > 2000 tokens | SUMMARIZE | Preserve budget |
| Pack missing | NO | Cannot fabricate |

### Unknown Handling Escalation

```
1. CHEAP PASS (Tier A graph-only)
   |
   +-- Match found? --> DONE
   |
   v (no match)
2. EXPAND SLICE (1-hop neighbors)
   |
   +-- Budget check
   |
   v (still unknown)
3. VERIFY PASS (spawn /vrs-pattern-verify)
   |
   v
4. EMIT UNKNOWN --> Human triage
```

---

## Context Isolation

Most skills run with `context: fork` for isolation:

**Forked context:**
- Tool output doesn't pollute main context
- Large outputs are summarized
- Agent conversations are isolated

**Skills with fork:** `/vrs-audit`, `/vrs-investigate`, `/vrs-verify`, `/vrs-bead-*`

**Skills with inline:** `/vrs-health-check`, `/vrs-orch-resume`

---

## Development vs Product Skills

### Product Skills (Shipped)

Installed via `alphaswarm init` into `.claude/skills/`:
- Core: audit, investigate, verify, debate, health-check
- Bead: bead-create, bead-update, bead-list
- Tool: tool-slither, tool-aderyn

**Target:** Users auditing Solidity code

### Development Skills

Only in alphaswarm repo (`skills/` directory):
- `/vrs-discover`, `/vrs-add-vulnerability`, `/vrs-refine`
- `/vrs-test-pattern`, `/vrs-research`, `/pattern-forge`

**Target:** VRS developers building the system

---

## User-Controlled vs Agent-Invocable

### User-Controlled (`disable-model-invocation: true`)

Only users can invoke:
- `/vrs-audit` - Users start audits manually
- `/vrs-health-check` - Users check installation
- `/vrs-orch-resume` - Users resume from checkpoints

### Agent-Invocable (`disable-model-invocation: false`)

Orchestrators can spawn:
- `/vrs-investigate`, `/vrs-verify`, `/vrs-debate`
- `/vrs-bead-*`, `/vrs-orch-spawn`, `/vrs-tool-*`

---

## Graph-First Reasoning Template

**CRITICAL:** All agents MUST follow `docs/reference/graph-first-template.md`.

### Required Workflow

1. **BSKG Queries (MANDATORY)** - Run queries before any analysis
2. **Evidence Packet (MANDATORY)** - Build with graph node IDs
3. **Unknowns/Gaps (MANDATORY)** - List what you don't know
4. **Conclusion (MANDATORY)** - Claims with evidence references

### Enforcement

- Claims without queries default to UNCERTAIN verdict
- Confidence rules (ORCH-09, ORCH-10) reject verdicts without evidence

**Query-first rule:** No manual code reading before BSKG queries run.

---

## Cache Key Format

```
{graph_hash}:{pcp_version}:{pattern_ids_hash}
```

- **graph_hash**: SHA256 of serialized graph
- **pcp_version**: Semantic version (e.g., "2.0")
- **pattern_ids_hash**: Sorted hash of pattern IDs

---

## Workflow And Debugging Links

- Workflow map: `docs/workflows/README.md`
- Testing contract: `docs/reference/testing-framework.md`
- Hook + task enforcement: `docs/reference/claude-code-orchestration.md`
- Debugging guide: `.planning/testing/guides/guide-agent-debugging.md`

If a skill is updated, update its referenced workflow doc first.

---

---

## Related Documentation

- [Skills Basics](skills-basics.md) - Getting started
- [Skill Schema v2](../reference/skill-schema-v2.md) - Full schema reference
- [Pattern Guide](patterns-basics.md) - Creating patterns

---

*Updated February 2026*
