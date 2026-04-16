# T5: Workflow Validation Report

**Date:** 2026-02-08
**Methodology:** Actual command execution, frontmatter inspection, skill format audit, end-to-end flow testing
**Confidence:** HIGH — findings verified by running real commands and reading real files

---

## Executive Summary

**Can a user actually use this product?** No. Not end-to-end.

The CLI tooling has a solid foundation — `build-kg`, `query`, `tools status`, and pool creation all work. But the **core value proposition** — running `/vrs-audit contracts/` to get a security report — fails at multiple critical points:

1. **19 of 20 root-level skills use non-v2 frontmatter** (`skill:` instead of `name:`), which causes Claude Code to report "unknown skill" when invoked via slash command
2. **`beads generate` crashes** with `PatternEngine.__init__() got an unexpected keyword argument 'pattern_dir'`
3. **`orchestrate resume` infinite-loops**, rebuilding the graph endlessly without progressing through phases
4. **All 74 vulndocs entries fail validation** — the knowledge base that patterns depend on is structurally broken
5. **The master audit skill (`/vrs-audit`) describes a pipeline that cannot execute** — it references subskills, agents, and output files that the CLI can't produce

**Verdict: PARTIALLY FUNCTIONAL** — Individual CLI commands work; the integrated end-to-end workflow does not.

---

## Skill Inventory

### Skill Format Summary

| Location | Format | Count | Status |
|----------|--------|-------|--------|
| `.claude/skills/*.md` (root files) | `skill:` frontmatter (non-v2) | 19 | BROKEN for slash commands |
| `.claude/skills/*.md` (root files) | `name:` frontmatter (v2) | 1 (`vrs-self-test.md`) | WORKS |
| `.claude/skills/*/SKILL.md` (directories) | `name:` frontmatter (v2) | 20 | WORKS |
| `.claude/skills/vrs/*.md` (subdirectory) | `name:` frontmatter (v2) | 13 | WORKS |
| `src/.../skills/shipped/*.md` | `name:` frontmatter (v2) | 28 | NOT INSTALLED in `.claude/skills/` |

**Critical Issue:** Claude Code requires `name:` in frontmatter for skill registration. The 19 root-level `.md` files all use `skill:` instead. This was noted in STATE.md (2026-02-03): "/vrs-status failing due to non-standard frontmatter (`skill:` instead of `name:`)" — but was never fixed for any of the 19 affected skills.

### Valid Skills (invocable via slash command)

These use the v2 `name:` format in directory SKILL.md files:

| Skill Directory | name: value | Invocable |
|----------------|-------------|-----------|
| `vrs-audit/` | `vrs-audit` | Yes (but pipeline breaks) |
| `vrs-investigate/` | `vrs-investigate` | Yes |
| `vrs-verify/` | `vrs-verify` | Yes |
| `vrs-debate/` | `vrs-debate` | Yes |
| `vrs-health-check/` | `vrs-health-check` | Yes |
| `vrs-bead-create/` | `vrs-bead-create` | Yes |
| `vrs-bead-list/` | `vrs-bead-list` | Yes |
| `vrs-bead-update/` | `vrs-bead-update` | Yes |
| `vrs-orch-spawn/` | `vrs-orch-spawn` | Yes |
| `vrs-orch-resume/` | `vrs-orch-resume` | Yes |
| `vrs-slither/` | `vkg-slither` | Yes (legacy name) |
| `vrs-aderyn/` | `vkg-aderyn` | Yes (legacy name) |
| `vrs-mythril/` | `vkg-mythril` | Yes (legacy name) |
| `vrs-tool-slither/` | `vrs-tool-slither` | Yes |
| `vrs-tool-aderyn/` | `vrs-tool-aderyn` | Yes |
| `vrs-tool-coordinator/` | `vkg-tool-coordinator` | Yes (legacy name) |
| `pattern-forge/` | `pattern-forge` | Yes |
| `agent-skillcraft/` | `agent-skillcraft` | Yes |
| `test-builder/` | `test-builder` | Yes |
| `gsd-research-context/` | `gsd-research-context` | Yes |

### Broken Skills (non-v2 frontmatter, `skill:` instead of `name:`)

These 19 root-level `.md` files all fail invocation:

| File | `skill:` value | Why Broken |
|------|---------------|------------|
| `vrs-audit.md` | `vrs-audit` | Uses `skill:` not `name:` |
| `vrs-status.md` | `vrs-status` | Uses `skill:` not `name:` |
| `vrs-full-testing.md` | `vrs-full-testing` | Uses `skill:` not `name:` |
| `vrs-agentic-testing.md` | `vrs-agentic-testing` | Uses `skill:` not `name:` |
| `vrs-workflow-test.md` | `vrs-workflow-test` | Uses `skill:` not `name:` |
| `vrs-run-validation.md` | `vrs-run-validation` | Uses `skill:` not `name:` |
| `vrs-claude-code-agent-teams-testing.md` | `vrs-claude-code-agent-teams-testing` | Uses `skill:` not `name:` |
| `vrs-claude-code-agent-teams-runner.md` | `vrs-claude-code-agent-teams-runner` | Uses `skill:` not `name:` |
| `vrs-strict-audit.md` | `vrs-strict-audit` | Uses `skill:` not `name:` |
| `vrs-component.md` | `vrs-component` | Uses `skill:` not `name:` |
| `vrs-environment.md` | `vrs-environment` | Uses `skill:` not `name:` |
| `vrs-parallel.md` | `vrs-parallel` | Uses `skill:` not `name:` |
| `vrs-checkpoint.md` | `vrs-checkpoint` | Uses `skill:` not `name:` |
| `vrs-resume.md` | `vrs-resume` | Uses `skill:` not `name:` |
| `vrs-rollback.md` | `vrs-rollback` | Uses `skill:` not `name:` |
| `vrs-select.md` | `vrs-select` | Uses `skill:` not `name:` |
| `vrs-evaluate-workflow.md` | `vrs-evaluate-workflow` | Uses `skill:` not `name:` |
| `vrs-validate-phase.md` | `vrs-validate-phase` | Uses `skill:` not `name:` |
| `enforce-testing-rules.md` | `enforce-testing-rules` | Uses `skill:` not `name:` |

### Duplicate Skills (Conflicting Definitions)

| Skill Name | Directory SKILL.md | Root .md file | Conflict |
|-----------|-------------------|---------------|----------|
| `vrs-audit` | `.claude/skills/vrs-audit/SKILL.md` (279 lines, v2) | `.claude/skills/vrs-audit.md` (459 lines, non-v2) | Different content, different frontmatter |

The root `vrs-audit.md` (459 lines) is the more detailed "aspirational" version. The directory `SKILL.md` (279 lines) is the actually-invocable version. They describe the same pipeline differently.

### Legacy Skills (Not Migrated)

| File | `name:` value | Issue |
|------|--------------|-------|
| `vrs-legacy/audit.md` | `vkg-audit` | Old name, not cleaned up |
| `vrs-legacy/investigate.md` | `vkg-investigate` | Old name |
| `vrs-legacy/debate.md` | `vkg-debate` | Old name |
| `vrs-legacy/verify.md` | `vkg-verify` | Old name |

### Shipped Skills (Not Installed)

28 skills exist in `src/alphaswarm_sol/skills/shipped/` but are NOT deployed to `.claude/skills/`. These include: `context-pack`, `evidence-audit`, `graph-contract-validate`, `ordering-proof`, `slice-unify`, `taint-extend`, `taxonomy-migrate`, `track-gap`, `benchmark-model`, `mutate-contract`, `pattern-verify`, `pattern-batch`, `test-full`, `test-quick`, `test-component`, `validate-vulndocs`.

---

## CLI Functionality

### Working Commands

| Command | Status | Evidence |
|---------|--------|----------|
| `alphaswarm --help` | WORKS | Shows 28 subcommands |
| `alphaswarm --version` | WORKS | Shows version |
| `alphaswarm build-kg <file>` | WORKS | Successfully builds graph from .sol, produces .toon output |
| `alphaswarm query "<text>" --graph <path>` | WORKS | Returns structured JSON with nodes, properties, evidence |
| `alphaswarm tools status` | WORKS | Shows 3/3 core ready, 2/5 enhancement |
| `alphaswarm doctor` | WORKS | Shows health status |
| `alphaswarm vulndocs info` | WORKS | Shows 19 categories, 74 vulns, 59 patterns |
| `alphaswarm vulndocs list` | WORKS | Lists all 74 entries (all FAILED validation) |
| `alphaswarm orchestrate start <path>` | WORKS | Creates pool, returns pool ID |
| `alphaswarm orchestrate list` | WORKS | Lists pools |
| `alphaswarm beads list` | WORKS | Lists beads (empty) |
| `alphaswarm beads generate --help` | WORKS | Shows correct interface |

### Broken/Failing Commands

| Command | Failure | Evidence |
|---------|---------|----------|
| `alphaswarm orchestrate start ... --scope <path>` | CRASH: `No such option: --scope` | Documented interface doesn't match reality |
| `alphaswarm orchestrate resume <pool-id>` | INFINITE LOOP | Rebuilds graph 8+ times without advancing phase |
| `alphaswarm beads generate <project>` | CRASH: `PatternEngine.__init__() got an unexpected keyword argument 'pattern_dir'` | Core pattern matching is broken |
| `alphaswarm vulndocs validate vulndocs/` | ALL FAIL | 74/74 entries have validation errors |

### Deprecated Dependency Warning

Every CLI command emits: `FutureWarning: All support for the google.generativeai package has ended. Switch to google.genai.`

---

## Orchestration Layer

### Pool/Bead Management

- **Pool creation**: WORKS. Creates pool YAML in `.vrs/pools/`, tracks status, files, scope.
- **Pool resume**: BROKEN. The `orchestrate resume` command enters an infinite loop, rebuilding the knowledge graph over and over. It never reaches the beads/execute/verify phases.
- **Bead generation**: BROKEN. `beads generate` crashes on `PatternEngine` initialization. The pattern engine API has changed but the CLI entry point wasn't updated.
- **Bead storage**: EMPTY. The `.vrs/beads/` directory is empty. No beads have ever been successfully generated through the CLI.

### Orchestration Code Quality

The Python code in `src/alphaswarm_sol/orchestration/` is well-structured:
- `pool.py`: PoolStorage + PoolManager with budget-aware management
- `schemas.py`: Pool, Scope, Verdict schemas
- `debate.py`, `cross_verify.py`: Multi-agent debate infrastructure
- `runner.py`, `loop.py`: Execution loop management
- `workspace.py`: Jujutsu workspace integration (recently added)

The code exists and has tests. The problem is **integration** — the CLI entry points don't correctly wire up to the orchestration code.

---

## VulnDocs Status

### Claimed vs Actual

| Metric | Claimed (CLAUDE.md) | Actual |
|--------|-------------------|--------|
| Patterns | 556+ | 562 YAML files in pattern dirs |
| Categories | 18 | 19 actual directories |
| Validated | Not stated | 0/74 (ALL FAIL validation) |
| Patterns with no vulndoc | Not stated | 69 vulns without patterns |

### Validation Results

**100% failure rate on vulndocs validation.** Every single one of the 74 vulnerability entries fails the validate command. The specific errors aren't exposed in the list output, but the structural issue is that vulndocs entries don't pass their own validation schema.

### Pattern Count Reality

While there ARE 562 pattern YAML files, their distribution is extremely uneven:
- `access-control/`: 246 (44% of all patterns)
- `reentrancy/`: 99 (18%)
- `logic/`: 56 (10%)
- `dos/`: 49 (9%)
- `upgrade/`: 30 (5%)
- All others: 82 (14%)
- **5 categories have 0 patterns**: zk-rollup, restaking, precision-loss, categories, account-abstraction

---

## End-to-End Workflow Assessment

### Can `/vrs-audit contracts/` produce a vulnerability report?

**No.** Here's the pipeline and where it breaks:

| Stage | Action | Status | Detail |
|-------|--------|--------|--------|
| 1. Setup | Check tools installed | WORKS | `tools status` works |
| 2. Build Graph | `build-kg contracts/` | WORKS | Produces valid .toon graph |
| 3. Protocol Context | Exa research | UNTESTED | Depends on MCP being configured |
| 4. Pattern Matching | `beads generate` or `query "pattern:*"` | BROKEN | PatternEngine crash |
| 5. Agent Investigation | Spawn specialized agents | UNTESTED | Depends on stage 4 |
| 6. Multi-Agent Debate | Attacker/Defender/Verifier | UNTESTED | Depends on stage 5 |
| 7. Report | Generate audit report | UNTESTED | Depends on stage 6 |

**The pipeline breaks at Stage 4.** Without pattern matching producing beads, there's nothing for agents to investigate. The entire downstream pipeline (stages 5-7) is unreachable through the CLI.

### What DOES work end-to-end?

1. **Graph building**: `build-kg` → `.toon` file with rich properties (200+ per function)
2. **Natural language queries**: `query "text" --graph <path>` → structured JSON
3. **Pool lifecycle**: Create pool → list pools (resume doesn't work)
4. **Tool status checks**: Doctor, health check, tool status

### What would a user actually experience?

1. User runs `/vrs-audit contracts/` → Skill is loaded (directory SKILL.md has v2 format)
2. Claude Code reads the skill instructions → Tries to follow the pipeline
3. Stage 1-2 succeed (build-kg works)
4. Stage 3: Claude Code would try to use Exa MCP → May work if configured
5. Stage 4: Claude Code tries `beads generate` → CRASHES
6. Stage 4 alt: Claude Code tries `query "pattern:*"` → Returns results but no findings
7. Pipeline stalls. No beads. No agents. No report.

**The user would get a knowledge graph and some pattern query results, but no security findings, no multi-agent debate, and no audit report.**

---

## Documentation vs Reality

### CLAUDE.md Accuracy

| Claim | Reality | Verdict |
|-------|---------|---------|
| "556+ patterns" | 562 pattern YAMLs exist, but 0/74 vulndocs pass validation | MISLEADING |
| "84.6% DVDeFi Detection" | Claims in STATE.md, no evidence this runs through CLI | UNVERIFIABLE |
| "78.2% Gauntlet Detection" | Same — test metrics, not product metrics | UNVERIFIABLE |
| "`uv run alphaswarm build-kg contracts/`" | WORKS | ACCURATE |
| "`uv run alphaswarm query`" | WORKS | ACCURATE |
| "`uv run alphaswarm tools status`" | WORKS | ACCURATE |
| "`uv run alphaswarm orchestrate start pool-id --scope contracts/`" | `--scope` flag doesn't exist | WRONG |
| "47 skills" (registry.yaml) | 47 registered, but 19 broken frontmatter + 28 not installed | MISLEADING |
| "24 agents" | 17 agent .md files in `.claude/agents/` | INFLATED |
| "7 tool integrations" | `tools status` shows Slither+Foundry+LLM ready; Aderyn/Medusa/solc-select not installed | PARTIALLY TRUE |

### Skill Descriptions vs Reality

The `vrs-audit.md` root skill file (459 lines) describes an elaborate 7-stage pipeline with:
- Protocol context research via Exa
- Tier A/B/C pattern matching
- Specialized agents per vulnerability type
- Multi-agent debate with visual output
- Cost model ($0 via Claude Code subscription)

**None of this actually executes.** It's a specification document, not a working implementation.

### Settings Configuration Issues

1. `.claude/settings.json` (JSON): Only hooks + pyright plugin. This is what Claude Code reads.
2. `.claude/settings.yaml` (YAML): Extensive config for hooks, agents, skills, MCP tools, cost policies. **Claude Code does NOT read YAML settings files.** This entire configuration is aspirational.

The YAML file references features like:
- `schema_version: "2.1"` (Claude Code 2.1 features)
- SessionStart hooks
- PreToolUse/PostToolUse hooks
- Agent defaults
- Slash command registration
- Tool permissions

**None of this is active** because Claude Code only reads `.claude/settings.json`.

---

## Testing Infrastructure Assessment

### claude-code-agent-teams-Based Testing

The project has extensive claude-code-agent-teams testing documentation:
- `vrs-claude-code-agent-teams-testing.md` (skill)
- `vrs-claude-code-agent-teams-runner.md` (skill)
- `vrs-workflow-test.md` (skill)
- RULES-ESSENTIAL.md (testing rules)

**But:** All three claude-code-agent-teams testing skills use non-v2 frontmatter (`skill:` not `name:`) and are therefore broken as slash commands. The testing infrastructure cannot be invoked as designed.

### Agent Teams

17 agent definition files exist in `.claude/agents/`. These include specialized agents: `vrs-attacker`, `vrs-defender`, `vrs-verifier`, `vrs-integrator`, `vrs-supervisor`. They are properly configured as Claude Code custom agents and CAN be spawned via the Task tool. This is one of the stronger parts of the system.

---

## Honest Verdict

### PARTIALLY FUNCTIONAL

**What works:**
- CLI tool (`alphaswarm`) installs and runs
- Knowledge graph builder (`build-kg`) produces rich, detailed graphs with 200+ security properties per function
- Natural language queries work
- Pool creation works
- Tool status/health checks work
- Agent definitions are properly structured
- Python codebase is substantial (~260K LOC) with real architecture

**What doesn't work:**
- The core audit pipeline breaks at pattern matching (stage 4 of 7)
- 19/20 root-level skills have broken frontmatter
- All 74 vulndocs entries fail validation
- `orchestrate resume` infinite-loops
- `beads generate` crashes
- No end-to-end audit has ever been produced through the CLI
- The YAML settings file is not read by Claude Code
- 28 "shipped" skills are not installed

**Overall:** The project has invested enormously in planning, documentation, architecture, and individual component development. The graph builder and query system are genuinely impressive. But the **integration layer** — the glue that connects components into a working product — has critical failures that prevent end-to-end operation.

---

## Specific Gaps

### P0 (Blocking: Product Cannot Function)

1. **Fix PatternEngine API mismatch** — `beads generate` crashes because CLI passes `pattern_dir` kwarg that the engine doesn't accept
2. **Fix `orchestrate resume` infinite loop** — Pool processing gets stuck rebuilding graphs forever
3. **Fix skill frontmatter** — Change `skill:` to `name:` in all 19 broken root-level skills (mechanical 5-minute fix)
4. **Fix vulndocs validation** — 74/74 entries fail; patterns can't match if vulndocs are structurally invalid

### P1 (Important: Product Works But Poorly)

5. **Resolve skill duplication** — `vrs-audit` exists as both directory SKILL.md (279 lines) and root .md (459 lines) with different content
6. **Install shipped skills** — 28 skills in `src/.../shipped/` are not deployed to `.claude/skills/`
7. **Fix documented CLI flags** — `--scope` doesn't exist on `orchestrate start` but is documented
8. **Remove deprecated google.generativeai** — FutureWarning on every command

### P2 (Nice to Have)

9. **Clean up legacy skills** — 4 `vkg-*` legacy skills still present
10. **Consolidate settings** — `.claude/settings.yaml` is aspirational; merge needed config into `.claude/settings.json`
11. **Clean up tool name inconsistency** — Some skills use `vkg-*` names, others use `vrs-*`

---

## Recommendations for Milestone 6.0

### Before Planning 6.0

1. **Fix P0 items** — These take hours, not weeks. The product literally cannot produce an audit report without them.
2. **Run one actual end-to-end audit** — Build graph → Generate beads → Create pool → Spawn agents → Get verdicts → Generate report. Document every failure point.
3. **Define "MVP audit"** — What is the MINIMUM that `/vrs-audit contracts/` must produce? A markdown file with findings? A list of bead verdicts?

### Milestone 6.0 Focus

| Priority | Area | Why |
|----------|------|-----|
| 1 | Fix integration layer | The 4 P0 bugs prevent any E2E usage |
| 2 | Validate 1 complete audit flow | Prove the system works on one DeFi project |
| 3 | Ship only what works | Don't register 47 skills when 19 are broken |
| 4 | VulnDocs structural fix | Pattern matching depends on valid vulndocs |
| 5 | Settings consolidation | The YAML settings file is dead code |

### What NOT to Do in 6.0

- Don't add more skills before fixing existing ones
- Don't expand vulndocs categories before fixing validation
- Don't add more testing infrastructure before the product works
- Don't plan 7.3.5/7.3.6/7.4 before 7.3.1.6 P0 issues are resolved
