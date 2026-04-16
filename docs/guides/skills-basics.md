# VRS Skills Basics

**Getting started with VRS skills for Solidity security auditing.**

**For advanced topics (schema v2, authoring, orchestration), see [Skills Authoring Guide](skills-authoring.md).**

---

## Overview

VRS skills are Claude Code skills for Solidity security auditing. There are **53 skills** in the registry (**30 shipped** and **23 dev/internal**) as of 2026-02-10.

**Skill Registry:** `src/alphaswarm_sol/skills/registry.yaml`

---

## Skill Namespaces

| Prefix | Purpose |
|--------|---------|
| `/vrs-audit` | Main audit orchestration |
| `/vrs-investigate` | Deep investigation |
| `/vrs-verify` | Multi-agent verification |
| `/vrs-health-check` | Installation validation |
| `/vrs-bead-*` | Bead management |
| `/vrs-orch-*` | Orchestration helpers |
| `/vrs-tool-*` | Tool execution |

---

## Core Skills

### `/vrs-audit`

Run a full security audit on your contracts.

```
/vrs-audit contracts/
```

**What it does:**
1. Builds knowledge graph with Slither
2. Loads protocol context (if available)
3. Detects vulnerability patterns
4. Spawns multi-agent verification
5. Produces final report with evidence

**Options:**
```
/vrs-audit --scope "Vault,Token" ./contracts/
/vrs-audit --resume audit-001
```

**Output:** Audit report with findings, confidence levels (CONFIRMED, LIKELY, UNCERTAIN, REJECTED)

### `/vrs-investigate`

Deep-dive investigation of a specific finding.

```
/vrs-investigate bd-a1b2c3d4
/vrs-investigate bd-a1b2c3d4 --attack   # Focus on attack path
/vrs-investigate bd-a1b2c3d4 --defense  # Focus on mitigations
```

### `/vrs-verify`

Multi-agent verification with attacker/defender/verifier roles.

```
/vrs-verify bd-a1b2c3d4
```

Spawns agents to construct exploits, find guards, and synthesize verdicts.

### `/vrs-health-check`

Validate your VRS installation.

```
/vrs-health-check
/vrs-health-check --verbose
```

**Checks:** Claude Code workflow readiness, tool availability (Slither required), and VulnDocs presence.

---

## Bead Management Skills

| Skill | Purpose | Usage |
|-------|---------|-------|
| `/vrs-bead-create` | Create investigation bead | `/vrs-bead-create "Check reentrancy" --severity high` |
| `/vrs-bead-update` | Update bead status | `/vrs-bead-update bd-xxx --status in_progress` |
| `/vrs-bead-list` | List beads with filtering | `/vrs-bead-list --status open` |

**Statuses:** `open`, `in_progress`, `blocked`, `complete`

---

## Tool Execution Skills

| Skill | Purpose |
|-------|---------|
| `/vrs-tool-slither` | Run Slither static analysis |
| `/vrs-tool-aderyn` | Run Aderyn static analysis |

These are used internally by audit skills and can be invoked directly for testing.

---

## Agent Definitions

VRS includes 5 core agents:

| Agent | Purpose | Model |
|-------|---------|-------|
| **vrs-attacker** | Construct exploit paths | opus |
| **vrs-defender** | Find guards and mitigations | sonnet |
| **vrs-verifier** | Synthesize verdicts | opus |
| **vrs-supervisor** | Coordinate workflows | sonnet |
| **vrs-integrator** | Merge findings | sonnet |

---

## Philosophy

All VRS skills follow these principles:

1. **No Autonomous Verdicts** - All findings require human review
2. **Evidence-Linked Findings** - Every vulnerability has code locations
3. **Semantic Detection** - Detect operations, not function names
4. **Graph-First** - Use BSKG queries, not manual code reading

---

## Write Boundaries

VRS skills are restricted to writing in:
- `skills/` - **canonical dev source** in this repo (symlink to `.claude/skills/`)
- `.claude/skills/` - runtime install target in user projects
- `.beads/` - Bead storage directory

**Registry:** `src/alphaswarm_sol/skills/registry.yaml` is the source-of-truth for skill locations.

---

## Support

If skills are not working:
1. Run `/vrs-health-check` to diagnose
2. Check Slither is installed (required)
3. Verify `.claude/skills/` directory exists
4. Run `uv run alphaswarm init --force` (tool-level reinstall)

---

## Related Documentation

- [Skills Authoring Guide](skills-authoring.md) - Schema v2, writing skills
- [Beads Guide](beads.md) - Task tracking system
- [PHILOSOPHY.md](../PHILOSOPHY.md) - Vision and requirements

---

*Updated February 2026*
