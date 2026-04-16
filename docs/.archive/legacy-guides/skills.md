# VRS Skills Guide

VRS skills are Claude Code skills for Solidity security auditing. This guide covers all **47 skills** that are available for security analysis and validation.

**Skill Registry:** `src/alphaswarm_sol/skills/registry.yaml`

## Skill Schema v2

All VRS skills use **Skill Schema v2** for standardized frontmatter with evidence-first contracts.

**Key features:**
- **Role contracts**: attacker/defender/verifier/orchestrator/etc.
- **Evidence requirements**: Must link code, cite graph nodes, use BSKG queries
- **Output contracts**: Structured, testable outputs with schema validation
- **Token budgets**: Cost-aware execution with 6k default budget
- **Failure modes**: Documented error conditions and resolutions

**Schema reference:** [docs/reference/skill-schema-v2.md](../reference/skill-schema-v2.md)

**Validation:**
```bash
# Validate single skill
python scripts/validate_skill_schema.py .claude/skills/vrs/audit.md

# Validate all skills in directory
python scripts/validate_skill_schema.py src/alphaswarm_sol/skills/shipped/

# Strict mode (fail on missing frontmatter)
python scripts/validate_skill_schema.py --strict .claude/skills/

# Warn mode (report but don't fail)
python scripts/validate_skill_schema.py --warn .claude/skills/
```

**Migration guide:** Skills are gradually migrating from v1 to v2. See schema reference for migration checklist.

## Skill Registry

All VRS skills are tracked in the **Skill Registry** (`src/alphaswarm_sol/skills/registry.yaml`) with version, status, and deprecation metadata.

**Registry features:**
- **Version tracking** - Semantic versioning for all skills
- **Lifecycle status** - Active, experimental, deprecated, sunset
- **Deprecation policy** - 180-day minimum sunset period
- **Location tracking** - Shipped vs dev-only skills
- **Migration guidance** - Replacement skills and migration notes
- **Workflow refs** - `workflow_refs` links each skill to workflow contracts
- **Debug defaults** - `documentation_defaults` provides debugging references

**Registry reference:** [docs/reference/skill-registry.md](../reference/skill-registry.md)

**Validation:**
```bash
# Validate registry integrity
uv run python -m alphaswarm_sol.skills.registry validate

# List deprecated skills
uv run python -m alphaswarm_sol.skills.registry list-deprecated

# Show registry statistics
uv run python -m alphaswarm_sol.skills.registry stats
```

**Programmatic access:**
```python
from alphaswarm_sol.skills import list_registry, get_skill_entry

# List all skills
skills = list_registry()

# Get specific skill
audit = get_skill_entry("audit")
print(f"Version: {audit['version']}, Status: {audit['status']}")
```

## Skill Namespaces

All VRS skills use the `vrs-` namespace:

| Prefix | Purpose |
|--------|---------|
| `/vrs-audit` | Main audit orchestration |
| `/vrs-investigate` | Deep investigation |
| `/vrs-verify` | Multi-agent verification |
| `/vrs-debate` | Structured debate |
| `/vrs-health-check` | Installation validation |
| `/vrs-bead-*` | Bead management |
| `/vrs-orch-*` | Orchestration helpers |
| `/vrs-tool-*` | Tool execution |

## Workflow And Debugging Links

Every skill must be traceable to a workflow contract and a debugging path.

- Workflow map: `docs/workflows/README.md`
- Per-workflow contracts: `docs/workflows/workflow-*.md`
- Testing contract: `docs/reference/testing-framework.md`
- Hook + task enforcement: `docs/reference/claude-code-orchestration.md`
- Interactive testing: `.planning/testing/`
- Debugging guide: `.planning/testing/guides/guide-agent-debugging.md`
- Skill reviewer gate: `docs/reference/skill-reviewer.md`

If a skill is updated, update its referenced workflow doc first, then re-run claude-code-controller validation.

## Core Skills

### `/vrs-audit`

Run a full security audit on your contracts.

**Usage:**
```
/vrs-audit contracts/
```

**What it does:**
1. Builds knowledge graph with Slither
2. Loads protocol context (if available)
3. Detects vulnerability patterns
4. Creates beads for findings
5. Spawns multi-agent verification (attacker/defender/verifier)
6. Runs structured debate protocol
7. Flags all findings for human review
8. Produces final report with evidence

**Options:**
```
/vrs-audit --scope "Vault,Token" ./contracts/
/vrs-audit --resume audit-001
```

**Output:**
- Audit report with findings
- Beads for each potential vulnerability
- Evidence packets with code locations
- Confidence levels (CONFIRMED, LIKELY, UNCERTAIN, REJECTED)

**Note:** All findings require human review per PHILOSOPHY.md. No autonomous verdicts.

### `/vrs-investigate`

Deep-dive investigation of a specific finding.

**Usage:**
```
/vrs-investigate bd-a1b2c3d4
```

**What it does:**
1. Loads bead details
2. Analyzes vulnerability pattern
3. Constructs attack path
4. Identifies guards and mitigations
5. Updates bead with findings

**Options:**
```
/vrs-investigate bd-a1b2c3d4 --attack     # Focus on attack path
/vrs-investigate bd-a1b2c3d4 --defense    # Focus on mitigations
```

**Note:** This skill is spawnable by orchestrators. It runs in forked context for isolation.

### `/vrs-verify`

Multi-agent verification with attacker/defender/verifier roles.

**Usage:**
```
/vrs-verify bd-a1b2c3d4
```

**What it does:**
1. Spawns attacker agent to construct exploit
2. Spawns defender agent to find guards
3. Spawns verifier agent to synthesize verdict
4. Runs debate protocol if agents disagree
5. Returns verdict with evidence

**Options:**
```
/vrs-verify bd-a1b2c3d4 --skip-debate    # Skip debate, use direct verification
```

**Verdict confidence levels:**
- **CONFIRMED:** High confidence vulnerability exists
- **LIKELY:** Probable vulnerability, needs human review
- **UNCERTAIN:** Insufficient evidence, manual analysis needed
- **REJECTED:** Not a vulnerability

### `/vrs-debate`

Structured adversarial debate between attacker and defender.

**Usage:**
```
/vrs-debate bd-a1b2c3d4
```

**What it does:**
1. Loads attacker and defender claims
2. Runs claim/counterclaim rounds
3. Applies arbitration protocol
4. Produces debate record with verdict

**Options:**
```
/vrs-debate bd-a1b2c3d4 --max-rounds 3    # Extended debate
```

**Debate protocol:**
- Round 1: Attacker claim + Defender counterclaim
- Round 2: Attacker rebuts + Defender rebuts
- Arbitration: Verifier synthesizes verdict

### `/vrs-health-check`

Validate your VRS installation.

**Usage:**
```
/vrs-health-check
/vrs-health-check --verbose
/vrs-health-check --json
```

**What it checks:**
- CLI installation (alphaswarm)
- Core tools (Slither - required)
- Recommended tools (Aderyn, Mythril, Foundry)
- Optional tools (Echidna, Semgrep, Halmos)
- VulnDocs presence and validation
- Skills availability
- Configuration and permissions

**Output:**
```
VRS Health Check
================

✓ CLI Installation
  Version: 1.0.0
  Python: 3.11.5

✓ Core Tools (1/1)
  ✓ Slither 0.10.0

⚠ Recommended Tools (2/3)
  ✓ Aderyn 0.2.0
  ✓ Mythril 0.24.0
  ✗ Foundry (not installed)

Overall Status: READY (1 recommended tool missing)
```

## Bead Management Skills

### `/vrs-bead-create`

Create a new investigation bead.

**Usage:**
```
alphaswarm bead create "Check reentrancy in withdraw" --severity high
```

**Note:** Skills can also create beads programmatically. See [Beads Guide](beads.md).

### `/vrs-bead-update`

Update bead status.

**Usage:**
```
alphaswarm bead update bd-a1b2c3d4 --status in_progress
alphaswarm bead update bd-a1b2c3d4 --status complete
```

**Statuses:**
- `open` - Ready for work
- `in_progress` - Currently being investigated
- `blocked` - Waiting on dependency
- `complete` - Investigation finished

### `/vrs-bead-list`

List beads with filtering.

**Usage:**
```
alphaswarm bead list
alphaswarm bead list --status open
alphaswarm bead list --ready              # Open and not blocked
alphaswarm bead list --severity high
```

## Orchestration Skills

### `/vrs-orch-spawn`

Spawn worker agent for parallel investigation.

**Usage:**
```
# Used internally by orchestrators
# Not typically invoked directly by users
```

**What it does:**
1. Creates isolated agent context
2. Assigns work from bead
3. Monitors agent progress
4. Collects results

### `/vrs-orch-resume`

Resume interrupted work from checkpoint.

**Usage:**
```
/vrs-orch-resume audit-001
```

**What it does:**
1. Checks bead status
2. Prioritizes in-progress beads
3. Resumes work from last checkpoint
4. Continues audit workflow

## Tool Execution Skills

### `/vrs-tool-slither`

Run Slither static analysis.

**Usage:**
```
# Used internally by audit skill
# Can be invoked directly for testing
```

**What it does:**
1. Runs Slither on contracts
2. Normalizes output to SARIF
3. Deduplicates findings
4. Returns structured results

### `/vrs-tool-aderyn`

Run Aderyn static analysis (if installed).

**Usage:**
```
# Used internally by audit skill
# Can be invoked directly for testing
```

**What it does:**
1. Checks if Aderyn is installed
2. Runs Aderyn on contracts
3. Normalizes output to SARIF
4. Deduplicates with other tools
5. Returns structured results

## Orchestration Trigger Matrix

### Skill Invocation Rules

The following matrix defines when to run each batch-related skill and how to handle context:

| Condition | `/vrs-context-pack` | `/vrs-pattern-batch` | `/vrs-pattern-verify` |
|-----------|---------------------|----------------------|-----------------------|
| **No cached PCP** | RUN | WAIT (needs PCP) | WAIT (needs PCP) |
| **PCP cached + hash match** | SKIP (reuse) | RUN | RUN |
| **PCP cached + hash mismatch** | RUN (rebuild) | WAIT | WAIT |
| **Single pattern** | RUN | SKIP (use verify) | RUN |
| **Multi-pattern batch** | RUN (all) | RUN | DEFER (batch handles) |
| **Budget exhausted** | DEFER | DEFER | DEFER |

### Protocol Context Decision Rules

| Scenario | Include Protocol Context? | Rationale |
|----------|---------------------------|-----------|
| Protocol pack available, < 500 tokens | YES (always) | Low cost, high value |
| Protocol pack available, 500-2000 tokens | YES (if budget allows) | Record cost in metrics |
| Protocol pack available, > 2000 tokens | SUMMARIZE to 1500 | Preserve budget |
| Protocol pack missing | NO (flag "no_econ_context") | Cannot fabricate |
| Cached protocol pack, graph changed | REBUILD | Context may be stale |

### Unknown Handling Escalation Ladder

When a skill encounters missing signals, follow this escalation:

```
1. CHEAP PASS (Tier A graph-only)
   |
   +-- Match found? --> DONE (return matched)
   |
   v (no match or unknown signal)
2. EXPAND SLICE (semantic dilation, 1-hop neighbors)
   |
   +-- Budget check: if insufficient --> EMIT UNKNOWN
   |
   v (still unknown after expand)
3. VERIFY PASS (spawn /vrs-pattern-verify)
   |
   +-- Budget check: if insufficient --> EMIT UNKNOWN
   |
   v (still unknown after verify)
4. EMIT UNKNOWN --> Return status="unknown", require human triage
```

**Key rules:**
- NEVER downgrade "unknown" to "not_matched" - this loses information
- Budget enforcement happens BEFORE each escalation step
- Counter-signals must be explicitly checked, not assumed absent

### Cache Key Format

All caches use this key structure for deterministic invalidation:

```
{graph_hash}:{pcp_version}:{pattern_ids_hash}
```

- **graph_hash**: SHA256 of serialized graph (changes when source changes)
- **pcp_version**: Semantic version of PCP schema (e.g., "2.0")
- **pattern_ids_hash**: Sorted hash of pattern IDs in batch

## Context Isolation

Most skills run with `context: fork` for isolation:

**Why fork context?**
- Tool output doesn't pollute main context
- Each investigation gets fresh context
- Large outputs are summarized
- Agent conversations are isolated

**Skills with forked context:**
- `/vrs-audit` - Main orchestrator
- `/vrs-investigate` - Deep investigation
- `/vrs-verify` - Multi-agent verification
- `/vrs-debate` - Debate protocol
- `/vrs-bead-create`, `/vrs-bead-update`, `/vrs-bead-list` - Bead management
- `/vrs-orch-spawn` - Worker spawning
- `/vrs-tool-*` - Tool execution

**Skills with inline context:**
- `/vrs-health-check` - Quick validation
- `/vrs-orch-resume` - Resume coordination

## Development vs Product Skills

### Product Skills (Shipped)

These skills are installed via `alphaswarm init` into `.claude/vrs/`:

- Core skills: audit, investigate, verify, debate, health-check
- Bead skills: bead-create, bead-update, bead-list
- Orchestration skills: orch-spawn, orch-resume
- Tool skills: tool-slither, tool-aderyn

**Target audience:** Users auditing Solidity code

### Development Skills (VKG Contributors)

These skills are ONLY in the alphaswarm repo (`.claude/` directory):

- `/vrs-discover` - Vulnerability research with Exa
- `/vrs-add-vulnerability` - Add VulnDocs entries
- `/vrs-refine` - Pattern improvement
- `/vrs-test-pattern` - Pattern validation
- `/vrs-research` - Guided research
- `/vrs-merge-findings` - Consolidate VulnDocs
- `/vrs-generate-tests` - Test case generation
- `/pattern-forge` - Iterative pattern creation
- `/test-builder` - Test writing helper
- `/knowledge-aggregation-worker` - VulnDocs discovery

**Target audience:** VRS developers building the system

**Key distinction:** Development skills never leave the alphaswarm repo. Only assessment skills ship to users.

## User-Controlled vs Agent-Invocable

### User-Controlled Skills

Skills with `disable-model-invocation: true` that ONLY users can invoke:

- `/vrs-audit` - Users start audits manually
- `/vrs-health-check` - Users check installation
- `/vrs-orch-resume` - Users resume from checkpoints

### Agent-Invocable Skills

Skills with `disable-model-invocation: false` that orchestrators can spawn:

- `/vrs-investigate` - Spawned by audit orchestrator
- `/vrs-verify` - Spawned by audit orchestrator
- `/vrs-debate` - Spawned by verify orchestrator
- `/vrs-bead-*` - Spawned during workflow
- `/vrs-orch-spawn` - Spawned for parallelization
- `/vrs-tool-*` - Spawned for tool execution

## Agent Definitions

VRS includes 5 specialized agents:

| Agent | Purpose | Model |
|-------|---------|-------|
| **vrs-attacker** | Construct exploit paths | opus |
| **vrs-defender** | Find guards and mitigations | sonnet |
| **vrs-verifier** | Synthesize verdicts | opus |
| **vrs-supervisor** | Coordinate workflows | sonnet |
| **vrs-integrator** | Merge findings | sonnet |

These agents are invoked by the verification skills.

## Validation Skills (Phase 7.3)

Skills for GA validation and testing orchestration:

| Skill | Purpose |
|-------|---------|
| `/vrs-full-testing` | Super-orchestrator for all validation workflows |
| `/vrs-agentic-testing` | Agentic test orchestration with claude-code-agent-teams isolation |
| `/vrs-workflow-test` | Test specific workflow execution |
| `/vrs-claude-code-agent-teams-testing` | claude-code-agent-teams-based test isolation |
| `/vrs-run-validation` | Run validation suite |

These skills require claude-code-controller and follow `.planning/testing/rules/canonical/RULES-ESSENTIAL.md`.

## Write Boundaries

All VRS skills are restricted to writing in:

- `.claude/vrs/` - VRS working directory
- `.beads/` - Bead storage directory

All other directories are read-only to prevent accidental modifications.

## Philosophy

All VRS skills follow these principles from PHILOSOPHY.md:

1. **No Autonomous Verdicts** - All findings require human review
2. **Evidence-Linked Findings** - Every vulnerability has code locations
3. **Semantic Detection** - Detect operations, not function names
4. **Two-Tier Detection** - Tier A (deterministic) + Tier B (LLM-verified)
5. **Graph-First** - Use BSKG queries, not manual code reading

## Graph-First Reasoning Template

**CRITICAL:** All VRS agents and skills MUST follow the graph-first reasoning template.

**See:** `docs/reference/graph-first-template.md` for full specification.

### Required Investigation Workflow

Every vulnerability investigation follows this mandatory sequence:

1. **BSKG Queries (MANDATORY)** - Run queries before any analysis
2. **Evidence Packet (MANDATORY)** - Build evidence with graph node IDs and code locations
3. **Unknowns/Gaps (MANDATORY)** - Explicitly list what you don't know
4. **Conclusion (MANDATORY)** - Only after steps 1-3, make claims with evidence references

### Template Integration

The graph-first template is integrated into:
- **Attacker Agent** (`src/alphaswarm_sol/skills/shipped/agents/vrs-attacker.md`) - Query for attack vectors
- **Defender Agent** (`src/alphaswarm_sol/skills/shipped/agents/vrs-defender.md`) - Query for guards
- **Verifier Agent** (`src/alphaswarm_sol/skills/shipped/agents/vrs-verifier.md`) - Validate evidence quality
- **Graph Retrieve Skill** (`.claude/skills/vrs/graph-retrieve.md`) - Execute queries and build evidence packs

### Enforcement

- All agents must include BSKG query results in their outputs
- Evidence without graph node IDs is flagged by verifier
- Claims without queries default to UNCERTAIN verdict
- Confidence enforcement (ORCH-09, ORCH-10) rejects verdicts without evidence

**Query-first rule:** ❌ No manual code reading before BSKG queries run.

## Related Documentation

- [Installation Guide](installation.md) - Setup instructions
- [Beads Guide](beads.md) - Task tracking system
- [PHILOSOPHY.md](../../docs/PHILOSOPHY.md) - Vision and requirements
- [Pattern Authoring](patterns.md) - Creating vulnerability patterns

## Support

If skills are not working correctly:

1. Run `/vrs-health-check` to diagnose issues
2. Check that Slither is installed (required)
3. Verify `.claude/vrs/` directory exists and is writable
4. Check skill files have correct YAML frontmatter
5. Run `alphaswarm init --force` to reinstall

---

*Updated February 2026 | Milestone 5.0 (~98% complete)*
