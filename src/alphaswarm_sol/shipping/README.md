# VRS Skills

These skills are installed in your project by `alphaswarm init`. They provide the user-facing interface for security audits using the VRS (Vulnerability Research System).

## Skills Overview

| Skill | Command | Purpose | User-only |
|-------|---------|---------|-----------|
| audit.md | `/vrs-audit` | Main audit orchestration | Yes |
| investigate.md | `/vrs-investigate` | Deep investigation | No |
| verify.md | `/vrs-verify` | Multi-agent verification | No |
| debate.md | `/vrs-debate` | Structured debate | No |
| health-check.md | `/vrs-health-check` | Validate installation | Yes |
| validate-vulndocs.md | `/vrs-validate-vulndocs` | Mandatory VulnDocs validation pipeline | Yes |
| bead-create.md | `/vrs-bead-create` | Create investigation bead | No |
| bead-update.md | `/vrs-bead-update` | Update bead status | No |
| bead-list.md | `/vrs-bead-list` | List beads | No |
| orch-spawn.md | `/vrs-orch-spawn` | Spawn worker agent | No |
| orch-resume.md | `/vrs-orch-resume` | Resume interrupted work | Yes |
| tool-slither.md | `/vrs-tool-slither` | Run Slither | No |
| tool-aderyn.md | `/vrs-tool-aderyn` | Run Aderyn | No |
| context-pack.md | `/vrs-context-pack` | Build deterministic PCP context | No |
| pattern-batch.md | `/vrs-pattern-batch` | Batch pattern discovery | No |
| pattern-verify.md | `/vrs-pattern-verify` | Verify Tier B/C matches | No |
| graph-contract-validate.md | `/vrs-graph-contract-validate` | Validate v2 contract compliance | No |
| ordering-proof.md | `/vrs-ordering-proof` | Dominance-based ordering proof | No |
| taint-extend.md | `/vrs-taint-extend` | Taint source/sink analysis | No |
| taxonomy-migrate.md | `/vrs-taxonomy-migrate` | Ops registry migration and validation | No |
| slice-unify.md | `/vrs-slice-unify` | Unified slicing pipeline | No |
| evidence-audit.md | `/vrs-evidence-audit` | Deterministic evidence ID validation | No |

**User-only:** Skills with `disable-model-invocation: true` that only users can invoke.

## Skill Categories

### Core Skills

The main workflow skills users interact with:

- **audit** - Full security audit orchestration
- **investigate** - Deep-dive into specific findings
- **verify** - Multi-agent verification with attacker/defender/verifier
- **debate** - Structured adversarial debate protocol
- **health-check** - Installation and configuration validation
- **validate-vulndocs** - Mandatory VulnDocs validation pipeline (Phase 7.2)

### Bead Skills

Task tracking and investigation management:

- **bead-create** - Create new investigation bead
- **bead-update** - Update bead status and fields
- **bead-list** - List and filter beads

### Orchestration Skills

Workflow coordination and agent management:

- **orch-spawn** - Spawn isolated worker agents
- **orch-resume** - Resume work from checkpoints

### Tool Skills

External tool execution:

- **tool-slither** - Run Slither static analysis
- **tool-aderyn** - Run Aderyn static analysis

### Pattern Batch Skills

Deterministic context + batch discovery:

- **context-pack** - Build Pattern Context Packs (PCP)
- **pattern-batch** - Run patterns in batch using shared context
- **pattern-verify** - Evidence gates for Tier B/C results

### Graph Interface Skills (Phase 5.9)

LLM-facing graph interface hardening:

- **graph-contract-validate** - Validate outputs against Graph Interface Contract v2
- **ordering-proof** - Dominance-based path-qualified ordering verification
- **taint-extend** - Taint source/sink/sanitizer analysis with availability
- **taxonomy-migrate** - Ops registry validation, migration, and SARIF compatibility
- **slice-unify** - Unified slicing pipeline with role-based budgets and debug mode
- **evidence-audit** - Deterministic evidence IDs, build hash verification, completeness audit

## Agent Definitions

The `agents/` subdirectory contains agent definitions for multi-agent verification. All agents are registered in the **canonical subagent catalog**:

**Catalog Location:** `src/alphaswarm_sol/agents/catalog.yaml`
**Catalog Reference:** `docs/reference/subagent-catalog.md`

| Agent | Purpose | Model |
|-------|---------|-------|
| **vrs-attacker.md** | Exploit path construction | claude-opus-4 |
| **vrs-defender.md** | Guard/mitigation search | claude-sonnet-4 |
| **vrs-verifier.md** | Evidence cross-check and verdict synthesis | claude-opus-4 |
| **vrs-secure-reviewer.md** | Creative attack thinking + adversarial skepticism with evidence-first reasoning | claude-sonnet-4.5 |
| **vrs-supervisor.md** | Workflow coordination | claude-sonnet-4 |
| **vrs-integrator.md** | Verdict merging and report generation | claude-sonnet-4 |
| **vrs-pattern-scout.md** | Fast pattern triage | claude-haiku-4.5 |
| **vrs-pattern-verifier.md** | Tier B/C verification | claude-sonnet-4 |
| **vrs-context-packer.md** | Pattern context pack assembly | claude-sonnet-4 |
| **vrs-finding-merger.md** | Deterministic merge worker | claude-sonnet-4 |
| **vrs-contradiction.md** | Refutation-only adversarial review | claude-sonnet-4 |
| **vrs-pattern-composer.md** | Composite vulnerabilities via op-signature algebra | claude-sonnet-4 |
| **vrs-finding-synthesizer.md** | Convergent evidence merging with confidence bounds | claude-sonnet-4 |

These agents are invoked by the verification skills during multi-agent workflows. See the catalog for complete agent metadata including evidence requirements, output contracts, and tool permissions.

### Batch Discovery Agents (Phase 5.10)

The following agents support batch pattern discovery orchestration:

| Agent | Role | Description |
|-------|------|-------------|
| **vrs-contradiction** | Adversarial review | Challenges findings with evidence-backed counterarguments. Never confirms; only refutes. |
| **vrs-pattern-composer** | Creative composition | Proposes composite vulnerabilities using sequence, parallel, amplification, and gating operators on semantic operations. |
| **vrs-finding-synthesizer** | Evidence synthesis | Merges convergent evidence from multiple findings, establishes confidence boundaries, and flags conflicts for human review. |

### Validation Pipeline Agents (Phase 7.2)

These agents support the mandatory VulnDocs validation pipeline:

| Agent | Role | Model | Description |
|-------|------|-------|-------------|
| **vrs-test-conductor** | Orchestration | claude-opus-4 | Coordinates validation pipeline, enforces quality gates |
| **vrs-corpus-curator** | Corpus validation | claude-sonnet-4 | Validates corpus integrity, ground truth, composition balance |
| **vrs-benchmark-runner** | Metrics | claude-haiku-4 | Executes benchmarks, collects precision/recall metrics |
| **vrs-mutation-tester** | Robustness | claude-haiku-4 | Generates contract variants for pattern robustness testing |
| **vrs-regression-hunter** | Regression | claude-sonnet-4 | Detects accuracy degradation, bisects to find root cause |
| **vrs-gap-finder** | Deep analysis | claude-opus-4 | Comprehensive coverage gap analysis with root cause |
| **vrs-prevalidator** | Fast gate | claude-haiku-4.5 | URL provenance, schema sanity, duplicate detection |
| **vrs-gap-finder-lite** | Quick scan | claude-sonnet-4.5 | Fast coverage scan with escalation flag |

The validation pipeline runs in order: prevalidator -> corpus-curator -> pattern-verifier -> benchmark-runner -> mutation-tester (conditional) -> regression-hunter (conditional) -> gap-finder-lite (escalates to gap-finder if needed).

## Usage

In Claude Code, type `/vrs-` to see available skills.

### Starting an Audit

```
/vrs-audit contracts/
```

This triggers the full execution loop:
1. Build knowledge graph
2. Detect patterns
3. Create beads
4. Spawn verification agents
5. Run debate protocol
6. Flag findings for human review

### Checking Installation

```
/vrs-health-check
```

Validates CLI, tools, vulndocs, and skills.

### Managing Beads

```
# List ready beads
/vrs-bead-list --ready

# Show bead details
alphaswarm bead show bd-a1b2c3d4

# Update status
alphaswarm bead update bd-a1b2c3d4 --status complete
```

### Resuming Work

```
/vrs-orch-resume audit-001
```

Resumes from last checkpoint after human review.

## Context Modes

### Forked Context (`context: fork`)

Skills that run in isolated context:
- **audit** - Prevents audit context pollution
- **investigate** - Isolates investigation work
- **verify** - Isolates multi-agent work
- **debate** - Isolates debate protocol
- **bead-*** - Isolates bead operations
- **tool-*** - Isolates tool output

### Inline Context

Skills that run in main context:
- **health-check** - Quick inline validation
- **orch-resume** - Coordination only
- **validate-vulndocs** - Validation pipeline orchestration

## Write Boundaries

All skills are restricted to writing in:
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

## Architecture

```
User invokes:
  /vrs-audit
      |
      v
  Audit Orchestrator (forked context)
      |
      +-- Build KG with Slither
      |
      +-- Load protocol context
      |
      +-- Detect patterns
      |
      +-- Create beads
      |
      +-- Spawn verification agents
      |       |
      |       +-- /vrs-investigate (forked)
      |       |
      |       +-- /vrs-verify (forked)
      |       |       |
      |       |       +-- vrs-attacker agent
      |       |       +-- vrs-defender agent
      |       |       +-- vrs-verifier agent
      |       |       |
      |       |       +-- /vrs-debate (forked)
      |       |
      |       +-- Collect verdicts
      |
      +-- Flag for human review
      |
      v
  Report with checkpoints
```

## Installation

These skills are automatically installed when you run:

```bash
alphaswarm init
```

This copies the skills and agent definitions to your project's `.claude/vrs/` directory.

To update or reinstall:

```bash
alphaswarm init --force
```

## Development vs Product

These are the **shipped** skills that go to end users. Development skills for VRS itself are located in the alphaswarm repository's `.claude/` directory.

| Location | Purpose | Audience |
|----------|---------|----------|
| `alphaswarm/.claude/` | VRS development | VRS developers |
| `src/alphaswarm_sol/shipping/` | VRS product distribution | VRS users |

**Development skills** (never shipped):
- `/vrs-discover` - Vulnerability research with Exa
- `/vrs-add-vulnerability` - Add VulnDocs entries
- `/vrs-refine` - Pattern improvement
- `/vrs-test-pattern` - Pattern validation
- `/pattern-forge` - Iterative pattern creation
- `/test-builder` - Test writing helper
- `/knowledge-aggregation-worker` - VulnDocs discovery

## Deferred Features

The following features are planned for Milestone 0.5.1:

- Foundry test execution skills
- Testnet deployment verification
- Web-based test skills
- Local testnet management

These are tracked under ORCH2-06 and deferred from Phase 5.6. Current VRS focuses on static analysis, pattern detection, and multi-agent verification without execution testing.

## Documentation

See the full documentation:
- [Installation Guide](../../../docs/getting-started/installation.md) - Setup instructions
- [Skills Basics](../../../docs/guides/skills-basics.md) - Skills fundamentals
- [Skills Authoring](../../../docs/guides/skills-authoring.md) - Schema v2, authoring
- [Beads Guide](../../../docs/guides/beads.md) - Task tracking system
- [PHILOSOPHY.md](../../../docs/PHILOSOPHY.md) - Vision and requirements
- [Pattern Basics](../../../docs/guides/patterns-basics.md) - Pattern fundamentals
- [Pattern Advanced](../../../docs/guides/patterns-advanced.md) - Tier A+B, PCP v2
- [VulnDocs Basics](../../../docs/guides/vulndocs-basics.md) - Vulnerability knowledge base
- [VulnDocs Authoring](../../../docs/guides/vulndocs-authoring.md) - Validation pipeline

## Support

If skills are not working correctly:

1. Run `/vrs-health-check` to diagnose issues
2. Check that Slither is installed (required): `slither --version`
3. Verify `.claude/vrs/` directory exists and is writable
4. Check skill files have correct YAML frontmatter
5. Run `alphaswarm init --force` to reinstall

For skill-specific issues:
- **Audit fails:** Check Slither installation and contract syntax
- **Tool skills fail:** Verify tool installation with health check
- **Beads not found:** Check `.beads/index.jsonl` exists and is valid
- **Agent spawn fails:** Check Claude API access and model availability

## License

Part of the VRS (Vulnerability Research System) for Solidity security analysis.
