# AlphaSwarm.sol

Behavior-first Solidity security auditing with Claude Code orchestration.

AlphaSwarm.sol is a multi-agent security framework where **Claude Code is the primary orchestrator**. It combines a behavioral knowledge graph, pattern detection, and attacker/defender/verifier workflows to produce evidence-linked findings.

---

## Product Model

- **Primary interface:** Claude Code skills (`/vrs-*`), especially `/vrs-audit`.
- **Execution core:** Graph-first reasoning + task lifecycle + evidence contracts.
- **CLI role:** Subordinate tooling used by workflows, subagents, and CI.

See `docs/PHILOSOPHY.md` and `docs/claude-code-architecture.md` for the architecture contract.

---

## Current Status (Milestone 6.0)

- BSKG builder: working
- Active patterns: 466 (with archived/quarantined sets tracked)
- Workflow hardening: active in Phase 3 (`3.1 -> 3.1b -> 3.2`)
- Full end-to-end audit pipeline: in progress (being proven with strict gates)

Authoritative status: `.planning/STATE.md`

---

## Install (From Source)

```bash
git clone <repo-url>
cd alphaswarm
uv tool install -e .
```

Optional tool-level verification:

```bash
uv run alphaswarm --help
uv run alphaswarm --version
```

---

## Quick Start (Workflow-First)

```text
# Start Claude Code in your project
claude

# Run primary audit workflow
/vrs-audit contracts/
```

Common workflow skills:

- `/vrs-health-check`
- `/vrs-investigate <bead-id>`
- `/vrs-verify <bead-id>`
- `/vrs-debate <bead-id>`
- `/vrs-bead-create`, `/vrs-bead-update`, `/vrs-bead-list`

---

## Tool-Level Commands (Subordinate Surface)

Use these for development, debugging, and CI automation.

```bash
# Graph tooling
uv run alphaswarm build-kg contracts/
uv run alphaswarm query "pattern:weak-access-control"

# Tool orchestration
uv run alphaswarm tools status
uv run alphaswarm tools run contracts/ --tools slither,aderyn

# VulnDocs validation
uv run alphaswarm vulndocs validate vulndocs/
```

---

## Architecture Summary

```text
User
  -> Claude Code (/vrs-audit)
      -> build graph + context + tools + detection
      -> TaskCreate/TaskUpdate lifecycle
      -> attacker/defender/verifier verification
      -> report + evidence pack + saved state
```

Core docs:

- `docs/claude-code-architecture.md`
- `docs/PHILOSOPHY.md`
- `docs/architecture.md`
- `docs/workflows/README.md`

---

## Development and Testing

```bash
# Main test suite
uv run pytest tests/ -n auto --dist loadfile

# Focused workflow tests
uv run pytest tests/workflows/ -v
```

Advanced testing architecture and migration guidance:

- `docs/workflows/diagrams/05-testing-architecture.md`
- `docs/migrations/claude-code-workflow-migration.md`

---

## Documentation

- Getting started: `docs/getting-started/installation.md`, `docs/getting-started/first-audit.md`
- Skills and guides: `docs/guides/`
- References: `docs/reference/`
- Workflow contracts: `docs/workflows/`

---

## License

MIT License.
