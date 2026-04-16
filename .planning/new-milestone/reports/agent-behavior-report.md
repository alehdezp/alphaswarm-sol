# T3: Agent Behavior Assessment

## Executive Summary

**The multi-agent system exists as a well-designed ARCHITECTURE with real Python orchestration code, but has NEVER been executed as a coordinated multi-agent debate in a real audit.** There are detailed agent prompts, data structures, a debate orchestrator, and unit tests — but zero evidence of the attacker-defender-verifier pipeline ever running end-to-end against real contracts with real LLM agents. The system is **PARTIALLY FUNCTIONAL** at the Python library level (data structures, debate logic, schemas) but **THEORETICAL** at the Claude Code orchestration level (no real subagent spawning, no real debate transcripts, no real verdicts produced).

---

## Agent Inventory

### Defined Agents (Claude Code `.claude/agents/`)

| Agent File | Model | Tools | Has AGENT.md | Prompt Quality | Evidence of Use |
|------------|-------|-------|--------------|----------------|-----------------|
| `vrs-attacker.md` | opus | Read,Glob,Grep,Bash(uv run python*) | Yes (266 lines) | **High** — detailed schemas, attack framework, behavioral signatures | **NONE** |
| `vrs-defender.md` | sonnet | Read,Glob,Grep,Bash(uv run python*) | Yes (342 lines) | **High** — guard types, strength scoring, protocol context | **NONE** |
| `vrs-verifier.md` | opus | Read,Glob,Grep,Bash(uv run python*) | Yes (346 lines) | **High** — synthesis process, decision matrix, dissent recording | **NONE** |
| `vrs-supervisor.md` | sonnet | Read,Glob,Grep,Bash(uv run python*) | Yes (brief) | **Medium** — stuck work detection, handoff, escalation | **NONE** |
| `vrs-integrator.md` | sonnet | Read,Glob,Grep,Bash(uv run python*) | Yes (263 lines) | **High** — merge strategy, dedup, conflict resolution | **NONE** |
| `vrs-secure-reviewer.md` | sonnet-4.5 | N/A (AGENT.md) | Yes (482 lines) | **Excellent** — dual modes (creative/adversarial), evidence schemas | **NONE** |
| `vrs-pattern-architect.md` | N/A | Various | No | Medium | Used for pattern development (not audit) |
| `pattern-tester.md` | N/A | Various | No | Medium | Used for pattern testing (not audit) |
| `knowledge-aggregation-worker.md` | N/A | Various | No | Medium | Used for vulndocs (not audit) |
| `vrs-docs-curator.md` | N/A | Various | No | Medium | Documentation only |
| `vrs-claude-controller.md` | N/A | Bash(claude-code-agent-teams*) | No | Medium | Test execution only |
| `vrs-workflow-evaluator.md` | N/A | Read,Grep | No | Medium | Evaluation only |
| `vrs-self-improver.md` | N/A | Various | No | Medium | Self-improvement only |
| `vrs-real-world-auditor.md` | N/A | Various | No | Medium | Benchmarking only |
| `vrs-security-research.md` | N/A | Various | No | Medium | Research only |
| `vrs-test-builder.md` | N/A | Various | No | Medium | Test generation only |
| `solidity-security-tester.md` | N/A | Various | No | Medium | Test generation only |
| `skill-architect.md` | N/A | Various | No | Low | Skill design only |

**Total:** 18 agent definition files, 6 with full AGENT.md subdirectories.

### Agent Catalog (`catalog.yaml`)

The catalog claims **24 agents** (21 shipped, 3 dev-only). Categories:

| Category | Count | Examples | Status |
|----------|-------|----------|--------|
| Core Verification (attacker/defender/verifier) | 3 | vrs-attacker, vrs-defender, vrs-verifier | **Prompts exist, Python code exists, never run together** |
| Secure Reviewer | 1 | vrs-secure-reviewer | **Prompt exists, never run in audit** |
| Orchestration (supervisor, integrator) | 3 | vrs-supervisor, vrs-integrator | **Prompts exist, never orchestrated** |
| Pattern Agents (scout, verifier, composer) | 3 | vrs-pattern-scout, vrs-pattern-verifier | **Prompt-only, no shipped .md found** |
| Context/Evidence (packer, merger, synthesizer) | 4 | vrs-context-packer, vrs-finding-merger | **Prompt-only placeholders** |
| Contradiction Agent | 1 | vrs-contradiction | **Prompt-only placeholder** |
| Validation Pipeline (conductor, curator, etc.) | 5 | vrs-test-conductor, vrs-benchmark-runner | **Prompt-only placeholders** |
| Dev-only | 3 | skill-auditor, cost-governor, gsd-context-researcher | **Not shipped** |

### Functional vs Placeholder Assessment

| Tier | Count | Description |
|------|-------|-------------|
| **Tier 1: Full prompt + Python code + tests** | 3 | AttackerAgent, debate orchestrator, schemas |
| **Tier 2: Full prompt + no backing code** | 6 | defender (no DefenderAgent class!), verifier, supervisor, integrator, secure-reviewer, contradiction |
| **Tier 3: Catalog entry + shipped prompt only** | 9 | pattern-scout, pattern-verifier, pattern-composer, context-packer, finding-merger, finding-synthesizer, test-conductor, corpus-curator, benchmark-runner |
| **Tier 4: Catalog entry + no shipped prompt** | 3 | gap-finder-lite, mutation-tester, regression-hunter |
| **Tier 5: Dev-only** | 3 | skill-auditor, cost-governor, gsd-context-researcher |

**Critical finding:** Only `AttackerAgent` has a real Python class implementation (`src/alphaswarm_sol/agents/attacker.py`). No `DefenderAgent`, `VerifierAgent` (as orchestration-compatible Python classes), or `IntegratorAgent` exist. The debate orchestrator references `self.attacker.analyze()` and `self.defender.analyze()` but only the attacker side has a real implementation.

**Separate swarm system:** There's a completely separate agent system in `src/alphaswarm_sol/swarm/agents.py` with `ScannerAgent`, `AnalyzerAgent`, `ExploiterAgent`, `VerifierAgent`, and `ReporterAgent`. This is a different architecture from the Claude Code subagent system — it's Python-native with shared memory and task boards. It's unclear how (or whether) these two agent systems relate.

---

## Graph-First Enforcement

### What the Prompts Say

The AGENT.md files for attacker, defender, and verifier are **exceptionally detailed** about graph-first reasoning:

- **Anti-patterns explicitly listed:** "Manual code reading without BSKG queries first" is marked FORBIDDEN
- **Query commands provided:** Real VQL examples with `uv run alphaswarm query`
- **Required investigation steps:** BSKG Queries → Evidence Packet → Unknowns → Conclusion (all marked MANDATORY)
- **Evidence validation rules:** Penalties for missing graph node IDs

### Enforcement Reality

**There is NO enforcement mechanism.** The graph-first requirement is:
1. Documented in prompts (strong)
2. Not verifiable by any runtime check (weak)
3. Not tested with real execution (zero)

**The agent prompts say the right things, but:**
- There's no code that validates an agent's output included graph query results
- There's no mechanism to reject agent responses that skip graph queries
- The ConfidenceEnforcer (in `confidence.py`) checks verdict-level rules but NOT graph-first compliance
- The orchestration layer has no "did you query the graph?" gate

**Drift Risk:** HIGH. Without enforcement, LLM agents will reliably drift to generic code review when faced with complex contracts. The prompts are instructions, not constraints.

---

## Debate Protocol

### Architecture (Impressive)

The debate protocol is the best-designed part of the system:

- `src/alphaswarm_sol/orchestration/debate.py` — 803-line Python implementation
- `DebateOrchestrator` class with `run_debate()` method
- Proper phase sequencing: CLAIM → REBUTTAL(s) → SYNTHESIS → HUMAN FLAG
- Confidence assessment with delta thresholds
- Dissent recording for strong losing arguments
- Evidence anchoring requirements
- ConfidenceEnforcer integration

### Implementation Gaps

1. **Rebuttal logic is hardcoded, not agent-driven:** The `_get_attacker_rebuttal()` and `_get_defender_rebuttal()` methods (lines 479-583) contain hardcoded response templates, NOT real agent invocations. The comment on line 517 says `"In full implementation, would use attacker agent to check bypasses"`. This is a TODO, not implementation.

2. **Only the claim round uses real agents.** The claim round calls `self.attacker.analyze()` and `self.defender.analyze()`, but:
   - Only AttackerAgent has a real `analyze()` implementation
   - DefenderAgent doesn't exist as a Python class
   - The debate falls back to placeholder claims when agents aren't configured

3. **No verifier agent invocation.** The synthesis step (`_run_synthesis`) is pure Python logic — it calculates evidence strength and compares it. The verifier agent prompt exists but is never called during synthesis.

### Does Debate Actually Happen?

**At the Python level:** Partially. The DebateOrchestrator can run with an AttackerAgent and produce a verdict, but the defender and verifier are hardcoded responses.

**At the Claude Code level:** Never. The `/vrs-verify` and `/vrs-debate` skills describe spawning subagents, but no evidence exists of this ever executing.

---

## Execution Evidence

### Transcripts Found

| File | Content | Agent Debate? |
|------|---------|---------------|
| `vrs-demo-agentic-testing-20260204/transcript.txt` | Claude Code launch → "Unknown skill: vrs-agentic-testing" → blank | **NO** — skill not recognized |
| `vrs-demo-claude-code-agent-teams-runner-20260204/transcript.txt` | Claude Code launch → "Unknown skill: vrs-claude-code-agent-teams-runner" → blank | **NO** — skill not recognized |
| `vrs-demo-run-validation-20260204/transcript.txt` | Not read | Likely same pattern |
| `cli-install-*/transcript.txt` | CLI installation testing | **NO** — installation only |

**Critical observation:** The only transcripts that exist show skills failing with "Unknown skill" errors. There are ZERO transcripts showing:
- A real audit with agent spawning
- Attacker/defender/verifier debate
- A verdict being produced
- An evidence packet being generated

### State Directories

| Directory | Status |
|-----------|--------|
| `.vrs/beads/` | **EMPTY** — no beads ever created |
| `.vrs/pools/` | **EMPTY** — no pools ever created |
| `.vrs/evidence/self-improving/` | **EMPTY** — no evidence ever stored |
| `.vrs/ga-gate/` | **EMPTY** |
| `.vrs/ga-metrics/` | **EMPTY** |
| `.vrs/graphs/` | **EMPTY** — no graphs currently stored |

**This is devastating.** The state management system is implemented (YAML storage, schemas, etc.) but has never stored a single real artifact from an actual audit run.

### Test Evidence

Tests exist for the debate protocol (`test_debate_protocol.py`, `test_debate_flow.py`, etc.) but they:
- Use mocked/configured agent responses (`tester.configure_agent_response()`)
- Test Python data structure manipulation, not real LLM agent behavior
- Use `OrchestratorTester` which is a test harness, not real orchestration
- `conftest.py` provides `mock_claude_code_cli` — explicitly mocking the Claude Code subprocess

---

## The Two Agent Systems Problem

There are **two completely separate agent architectures** that don't connect:

### System 1: Claude Code Subagents (Prompt-based)
- Defined in `.claude/agents/*.md`
- Designed to be spawned by Claude Code via the `Task` tool
- Run as separate Claude Code processes
- Communicate via structured JSON output
- **No evidence of ever being spawned together**

### System 2: Python Swarm Agents (Code-based)
- Defined in `src/alphaswarm_sol/swarm/agents.py`
- `ScannerAgent`, `AnalyzerAgent`, `ExploiterAgent`, `VerifierAgent`, `ReporterAgent`
- Use shared memory (`SharedMemory`) and task boards (`TaskBoard`)
- Have abstract `process_task()` methods
- **Separate architecture from the Claude Code agents**

### System 3: Verification Agents (Code-based)
- Defined in `src/alphaswarm_sol/agents/base.py` and `agents/attacker.py`
- `VerificationAgent` base class with `analyze()` method
- `AttackerAgent` is the only concrete implementation
- Used by `DebateOrchestrator` for claim round
- **Only attacker is implemented; defender/verifier are not**

These three systems are NOT integrated. The CLAUDE.md and documentation present them as one coherent system, but they are three separate, incomplete implementations.

---

## Drift Risk Assessment

| Factor | Risk Level | Reasoning |
|--------|------------|-----------|
| **Graph-first enforcement** | HIGH | Documented but not enforced at runtime |
| **Agent prompt specificity** | LOW | Prompts are detailed and role-specific |
| **Evidence anchoring** | MEDIUM | Required in prompts, not validated |
| **Rebuttal quality** | CRITICAL | Hardcoded, not agent-driven |
| **Multi-agent coordination** | CRITICAL | Never tested end-to-end |
| **Token budget compliance** | HIGH | No budget tracking during agent runs |
| **Mode confusion (creative vs adversarial)** | MEDIUM | Clear in prompts, untested in practice |

**Overall drift risk: HIGH.** The system has excellent prompt engineering but zero execution-time guardrails. Real LLM agents will inevitably:
1. Skip graph queries when they seem slow or irrelevant
2. Produce generic Solidity security analysis instead of graph-anchored findings
3. Ignore the evidence schema when it's inconvenient
4. Not actually debate — the verifier will just agree with whatever seems most reasonable

---

## Honest Verdict

### PARTIALLY FUNCTIONAL / LARGELY THEORETICAL

**What works:**
- Detailed, high-quality agent prompt engineering (best-in-class for the domain)
- Python orchestration data structures (schemas, debate protocol, pool management)
- Unit tests for the Python layer (data flows, schema validation)
- Agent catalog with clear role definitions
- Skill definitions with invocation patterns

**What doesn't work:**
- No real multi-agent execution has ever occurred
- Only 1 of 3 core agents (attacker) has a Python implementation
- Debate rebuttals are hardcoded, not agent-driven
- State directories are empty — no beads, pools, or evidence ever produced
- Claude Code skill transcripts show "Unknown skill" errors
- The three agent systems (Claude Code subagents, Python swarm, verification agents) are disconnected
- Graph-first reasoning has zero runtime enforcement

**Confidence:** HIGH that this assessment is accurate. The evidence is unambiguous:
- Empty state directories
- Only 1/3 core Python agent classes implemented
- Hardcoded rebuttal logic with TODO comments
- Failed skill transcripts
- All debate tests use mocks

---

## Specific Gaps

1. **No DefenderAgent Python class** — The debate orchestrator calls `self.defender.analyze()` but DefenderAgent doesn't exist
2. **No VerifierAgent Python class** — Synthesis is pure Python math, not LLM reasoning
3. **Hardcoded rebuttals** — `_get_attacker_rebuttal()` and `_get_defender_rebuttal()` return templates, not real agent reasoning (line 517: "In full implementation, would use attacker agent to check bypasses")
4. **Three disconnected agent systems** — Claude Code subagents, Python swarm, and verification agents don't integrate
5. **Empty state management** — Pool, bead, evidence storage never used
6. **No graph-first enforcement** — Prompts say it, nothing checks it
7. **Skills fail to load** — Transcripts show "Unknown skill" for VRS workflow skills
8. **No end-to-end test** — Zero tests spawn real Claude Code subagents
9. **No shipped agent prompt verification** — `src/alphaswarm_sol/skills/shipped/agents/` has 21 `.md` files but no validation they load correctly as Claude Code agents

---

## Recommendations for Milestone 6.0

### Priority 1: Make ONE complete flow work end-to-end
1. Pick the simplest case: one vulnerable contract, one pattern match
2. Build a complete `DefenderAgent` Python class
3. Replace hardcoded rebuttals with real agent calls
4. Run `attacker → defender → verifier` on a real contract and capture the full output
5. Prove it works before expanding

### Priority 2: Unify agent architectures
1. Choose ONE agent architecture (recommend Claude Code subagents for production)
2. Deprecate or archive the Python swarm system
3. Ensure debate orchestrator uses the chosen architecture consistently

### Priority 3: Add graph-first enforcement
1. Add a `GraphQueryValidator` that checks agent outputs for graph node references
2. Reject or downgrade verdicts that lack graph evidence
3. Log compliance metrics per agent run

### Priority 4: Fix skill loading
1. Debug why VRS skills show "Unknown skill" in claude-code-agent-teams transcripts
2. Ensure all claimed skills are discoverable by Claude Code
3. Verify the skill registry matches actual file locations

### Priority 5: Create real execution evidence
1. Run at least 3 full audits against different contract types
2. Store beads, pools, and evidence in `.vrs/`
3. Capture complete transcripts with real agent debate
4. Use these as baselines for regression testing

### Priority 6: Stop claiming 24 agents
1. Only count agents that have: (a) a prompt, (b) a Python implementation or Claude Code invocation, (c) evidence of execution
2. Current honest count: ~3-4 functional agents, ~6 with full prompts, ~15 placeholder definitions
