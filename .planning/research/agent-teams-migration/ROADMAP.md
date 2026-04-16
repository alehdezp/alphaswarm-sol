# Agent Teams Migration Roadmap: Legacy Infrastructure -> Claude Code Agent Teams

**Date:** 2026-02-06
**Status:** MIGRATION COMPLETE — Legacy infrastructure fully removed (2026-02-09)
**Source:** 7 research reports from 7-agent team (2 researchers, 2 codebase analyzers, 1 blog writer, 1 iteration analyst, 1 web patterns researcher)

> **NOTE (2026-02-09):** The legacy testing infrastructure referenced throughout this document has been fully deprecated and removed. All workflows now use Agent Teams + `claude-code-controller` (npm v0.6.1). This document is retained as historical research context.

> **NOTE (2026-02-11):** Phase 3.1c now includes the debrief protocol (3.1c-05) and multi-agent evaluation pipeline (3.1c-11) that build on Agent Teams SendMessage for interactive agent debugging. See `.planning/phases/3.1c-reasoning-evaluation-framework/context.md`.

---

## Terminology

> **IMPORTANT:** This roadmap uses Claude Code primitives precisely. For the canonical taxonomy (teammate vs subagent vs skill vs hook vs agent definition), see `.planning/research/CLAUDE-CODE-PRIMITIVES.md`.

---

## Decision

**Replace legacy infrastructure with Claude Code Agent Teams (teammates) for ALL workflows.**
**Programmatic testing uses `claude-code-controller` (npm v0.6.1) — no legacy infrastructure dependency remains.**

---

## What We're Replacing

### Production (MIGRATE to Agent Teams)

| Component | Type | Current Usage |
|-----------|------|---------------|
| `/vrs-workflow-test` | Skill | legacy infrastructure-based workflow testing |
| `/vrs-legacy infrastructure-runner` | Skill | legacy infrastructure session management |
| `/vrs-full-testing` | Skill | Super-orchestrator using legacy infrastructure |
| `/vrs-validate-phase` | Skill | Phase validation via legacy infrastructure |
| `/vrs-agentic-testing` | Skill | Agentic test orchestration |
| `vrs-claude-controller` | Agent | Critical legacy infrastructure-based orchestrator |
| `legacy infrastructure_controller.py` | Python | legacy infrastructure process control (~900 LOC) |
| `legacy infrastructure_harness.py` | Python | Test harness (~1000 LOC) |
| `full_testing_orchestrator.py` | Python | Full testing loop (~1000 LOC) |

**Total production code to migrate:** ~2900 LOC -> ~1500 LOC (50% reduction)

### Self-Test (DEPRECATED — replaced by Agent Teams + controller)

| Component | Action |
|-----------|--------|
| legacy infrastructure-cli infrastructure | **DELETE** — replaced by `claude-code-controller` (npm v0.6.1) |
| RULES-ESSENTIAL.md legacy infrastructure rules | **REWRITE** for Agent Teams |
| legacy infrastructure transcript capture | **DELETE** — replaced by controller event capture |

### Documentation (UPDATE references)

~100+ files with legacy infrastructure references in .planning/, docs/, .claude/

---

## Migration Phases

### Phase 1: Prove the Debate (Week 1-2)

**Goal:** Prove attacker/defender/verifier debate works with Agent Teams DMs.

**Tasks:**
1. Enable `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in settings
2. Create new skill `/vrs-team-verify` that uses TeamCreate + teammates
3. Spawn attacker, defender, verifier as teammates (not subagents)
4. Attacker DMs defender with exploit evidence
5. Defender responds with guards found
6. Verifier reads both, renders verdict
7. Compare results to current subagent-based `/vrs-verify`

**Team Configuration:**
```yaml
team_name: vrs-verification
lead: orchestrator (delegate mode)
teammates:
  - name: attacker
    agent_type: vrs-attacker
    model: opus
  - name: defender
    agent_type: vrs-defender
    model: sonnet
  - name: verifier
    agent_type: vrs-verifier
    model: opus
```

**Success Criteria:**
- Debate produces correct verdict on 3 known-vulnerable contracts
- Evidence packets include code locations and graph node IDs
- Inter-agent DMs show real challenge/response (not scripted)
- Total time < 5 minutes per bead

**Files to Create:**
- `.claude/skills/vrs-team-verify.md` (new skill)
- `src/alphaswarm_sol/orchestration/team_controller.py` (new)

**Files to Modify:**
- `.claude/settings.json` (enable Agent Teams)
- `CLAUDE.md` (add Agent Teams quick reference)

---

### Phase 2: Full Audit Pipeline (Week 3-4)

**Goal:** Convert `/vrs-audit` to team-based orchestration with parallel specialists.

**Tasks:**
1. Create `/vrs-team-audit` skill using Agent Teams
2. Lead spawns parallel specialist attackers (authorization, value-flow, external-calls)
3. Each specialist investigates in parallel (no sequential bottleneck)
4. Defender validates all findings simultaneously
5. Verifier arbitrates disputed findings via DM debate
6. Shared task list tracks beads as tasks with dependencies

**Team Configuration:**
```yaml
team_name: vrs-audit-{contract}
lead: audit-orchestrator (delegate mode)
teammates:
  - name: auth-attacker (authorization lens)
  - name: value-attacker (value flow lens)
  - name: external-attacker (external calls lens)
  - name: defender (validates all findings)
  - name: verifier (arbitrates disputes)
```

**Success Criteria:**
- Parallel execution: 3 attackers work simultaneously
- Wall-clock time: 10min -> ~2min for single contract
- Finding quality: >= current subagent results
- Task list shows complete bead lifecycle

**Files to Create:**
- `.claude/skills/vrs-team-audit.md`
- `.claude/agents/audit-orchestrator.md`

**Files to Modify:**
- `.claude/skills/vrs-audit.md` (update to use team orchestration)

---

### Phase 3: Self-Testing Infrastructure (Week 5-6)

**Goal:** Replace legacy infrastructure-based testing with Agent Teams self-validation.

**Five Self-Testing Patterns to Implement:**

#### Pattern 1: Skill Quality Validation
```
Team: skill-test-{skill-name}
  executor: Runs skill on test contract
  evaluator: Scores against ground truth (precision/recall/F1)
  improver: Proposes pattern changes if quality < threshold
```

#### Pattern 2: Debate Quality Assessment
```
Team: debate-quality-test
  attacker, defender, verifier: Normal debate
  quality-judge: Evaluates evidence anchoring, logical coherence, verdict correctness
```

#### Pattern 3: Self-Improving Iteration Loop
```
Team: self-improvement-loop
  auditor: Runs audit on corpus
  scorer: Computes metrics
  analyzer: Identifies gaps
  applier: Applies fixes
  convergence-checker: Decides continue/stop
  Loop until: F1 >= 0.85 OR plateau OR max_iterations
```

#### Pattern 4: Shipping Confidence Gate
```
Team: pre-release-gate
  stress-tester: Runs on 10+ diverse contracts
  metrics-collector: Aggregates quality metrics
  edge-case-hunter: Adversarial inputs
  performance-monitor: Duration, token usage
  gate-keeper: APPROVE or REJECT release
```

#### Pattern 5: Cross-Skill Integration Testing
```
Team: integration-test-pipeline
  auditor: /vrs-audit -> findings
  investigator: /vrs-investigate -> deep dive
  verifier: /vrs-verify -> verdicts
  debater: /vrs-debate -> disputed findings
  integration-checker: Validates interoperability
```

**Success Criteria:**
- All 5 patterns working
- No legacy infrastructure dependency in any test paths
- Quality metrics computed automatically
- Self-improvement loop demonstrates convergence

**Files to Create:**
- `.claude/skills/vrs-self-test.md`
- `.claude/agents/testing-lead.md`
- `src/alphaswarm_sol/testing/team_validator.py`
- `src/alphaswarm_sol/testing/quality_gates.py`

**Files to Modify:**
- `.planning/testing/rules/canonical/RULES-ESSENTIAL.md` (add Agent Teams testing pattern)

---

### Phase 4: Novel Features (Week 7-8)

**Goal:** Unlock capabilities unique to Agent Teams.

**Tasks:**
1. **Red vs Blue Teams:** Competing attacker teams, best exploit wins
2. **Agent Memory:** Attacker/defender learn across projects via MEMORY.md
3. **User-as-Teammate:** Security expert joins team, guides AI agents
4. **Plan Approval:** Pattern changes require lead approval before apply
5. **Delegate Mode:** Audit orchestrator only coordinates, never implements

**Files to Create:**
- `.claude/agents/vrs-attacker.md` (add memory: user)
- `.claude/agents/vrs-defender.md` (add memory: user)

---

### Phase 5: GA Hardening (Week 9-10)

**Goal:** Production-ready, documentation complete, GA release.

**Tasks:**
1. Delete all legacy infrastructure-based skills and infrastructure
2. Update CLAUDE.md with Agent Teams as primary execution model
3. Update all documentation references (100+ files)
4. Run full validation suite using Agent Teams self-testing
5. Publish blog post: "The Self-Testing Frontier"
6. Complete Phase 7.3.1.6 with Agent Teams

**Success Criteria:**
- Zero legacy infrastructure dependency in production paths
- All skills tested via Agent Teams self-validation
- Shipping confidence gate passes for 5.0 GA
- Blog post published

---

## Key Technical Details

### How Agent Teams Replaces legacy infrastructure

| legacy infrastructure Pattern | Agent Teams Replacement |
|-------------|------------------------|
| `legacy infrastructure new-session` | `TeamCreate(team_name=...)` |
| `legacy infrastructure split-window` | `Task(team_name=..., name=...)` |
| `legacy infrastructure send-keys` | `SendMessage(recipient=..., content=...)` |
| `legacy infrastructure capture-pane` | Task history + message logs |
| `legacy infrastructure wait-for` | Automatic idle notifications |
| `legacy infrastructure kill-session` | `SendMessage(type="shutdown_request")` + `TeamDelete()` |
| Transcript parsing | Direct message content |
| File-based state sync | Shared task list (DAG) |
| Manual coordination | Automatic message delivery |

### Cost Model

| Mode | Tokens/Audit | Cost | Wall-Clock |
|------|-------------|------|------------|
| Current (sequential subagents) | ~650K | ~$15 | ~10min |
| Agent Teams (parallel, model delegation) | ~905K | ~$7.50 | ~1min |

**40% more tokens, 50% cheaper (model delegation), 10x faster (parallelism)**

Model delegation strategy:
- **Haiku:** Setup tasks, metrics collection, convergence checking
- **Sonnet:** Core analysis, defense, pattern testing
- **Opus:** Attack construction, final verification, quality judgment

### Known Limitations (Feb 2026)

| Limitation | Impact | Mitigation |
|-----------|--------|------------|
| No session resumption | Multi-day audits restart | Design for single-session completion |
| One team per session | Must cleanup between teams | Structured team lifecycle |
| No nested teams | Can't have sub-debates | Flatten hierarchy, use subagents for sub-tasks |
| Task status lag | Blocks dependent tasks | Manual nudging, timeout handling |
| 2 teammates same file | Overwrites | Clear file ownership boundaries |

---

## Anti-Fabrication Rules for Self-Testing

| Rule | legacy infrastructure-Based | Agent Teams |
|------|-----------|-------------|
| **Authenticity** | Transcript min 50 lines | Task list min 5 tasks completed |
| **Duration** | Min 5s smoke, 120s E2E | Min 3 iterations for quality loop |
| **Markers** | `alphaswarm`, `slither` in transcript | TaskCreate/Update in task history |
| **Perfect metrics** | FORBIDDEN (100%/100%) | FORBIDDEN (convergence must show improvement, not perfection) |
| **External truth** | Required | Required (Code4rena, SmartBugs, CVE) |
| **Convergence** | N/A | Must show iteration history with deltas |

---

## Files Summary

### To Create (New)
```
.claude/skills/vrs-team-verify.md          # Phase 1
.claude/skills/vrs-team-audit.md           # Phase 2
.claude/skills/vrs-self-test.md            # Phase 3
.claude/agents/audit-orchestrator.md       # Phase 2
.claude/agents/testing-lead.md             # Phase 3
src/alphaswarm_sol/orchestration/team_controller.py  # Phase 1
src/alphaswarm_sol/testing/team_validator.py         # Phase 3
src/alphaswarm_sol/testing/quality_gates.py          # Phase 3
```

### To Modify
```
.claude/settings.json                      # Enable Agent Teams
CLAUDE.md                                  # Add Agent Teams section
.claude/skills/vrs-audit.md               # Update to team orchestration
.claude/agents/vrs-attacker.md            # Add memory: user
.claude/agents/vrs-defender.md            # Add memory: user
.planning/testing/rules/canonical/RULES-ESSENTIAL.md  # Add Agent Teams patterns
100+ documentation files                   # Update legacy infrastructure references
```

### To Delete (fully deprecated)
```
.claude/skills/vrs-legacy infrastructure-runner.md
.claude/skills/vrs-workflow-test.md (legacy infrastructure portions)
.claude/agents/vrs-claude-controller.md
src/alphaswarm_sol/testing/legacy infrastructure_controller.py
src/alphaswarm_sol/testing/legacy infrastructure_harness.py
```

---

## Research Artifacts

Research was conducted by a 7-agent team (4 initial + 3 second wave).
Full report contents are preserved in conversation context.

| Report | Author | Content |
|--------|--------|---------|
| External opinions & creative uses | researcher-1 | 8,500 words, 50+ sources, sentiment analysis |
| Technical architecture & migration | researcher-2 | 960 lines, 15 sections, code samples |
| legacy infrastructure inventory & categorization | analyzer-1 | 451 files audited, migration map |
| Workflow transformation analysis | analyzer-2 | Before/after for all major workflows |
| Blog post draft | blog-writer | 3,400 words, 19 sources, publication-ready |
| Self-validating iteration patterns | iteration-analyst | 5 concrete patterns, RULES-ESSENTIAL transform |
| 2026 AI QA patterns | research-web-patterns | 40+ sources, gap analysis |

---

## Status (2026-02-09)

**Migration complete.** Agent Teams is now the canonical orchestration model. All legacy testing infrastructure has been removed from the codebase. The phases described above have been superseded by the current roadmap in `.planning/ROADMAP.md`.

## Phase 3.1c Integration: Reasoning-Based Evaluation (2026-02-11)

The reasoning-based evaluation framework (Phase 3.1c) directly implements and extends several patterns from this migration research:

### Connection to Self-Testing Patterns

| Research Pattern | Phase 3.1c Implementation |
|---|---|
| Pattern 2: Debate Quality Assessment | LLM Reasoning Evaluator + per-agent debrief |
| Pattern 3: Self-Improving Iteration Loop | Improvement loop with safe sandboxing + regression detection |
| Pattern 5: Cross-Skill Integration Testing | Per-workflow evaluation contracts + orchestration evaluation |

### Interactive Debrief via Agent Teams

Phase 3.1c uses Agent Teams communication (SendMessage) to implement a novel debugging capability:
- After multi-agent workflows, the orchestrator sends targeted debrief questions to each teammate
- Teammates respond with their reasoning, choices, and identified gaps
- SubagentStop hook BLOCKS shutdown until debrief responses are found in the transcript
- Debrief responses feed the LLM evaluator for quality assessment

This was not envisioned in the original migration roadmap but naturally extends the Agent Teams communication model for evaluation purposes.

### Smart Selection Per Workflow

The evaluation framework applies different checks per workflow category (investigation, tool integration, orchestration, support), avoiding blanket application that would produce false negatives on workflows where certain checks are irrelevant.

### Safe Prompt Improvement

The improvement loop uses Agent Teams + test projects as sandboxes:
1. Copy production prompt to test project .claude/
2. Modify the copy with improvement suggestion
3. Re-run workflow — Claude Code picks up the local .claude/ version
4. Compare before/after scores
5. Human approves production prompt update

This extends the migration's "agent memory" concept with a structured improvement protocol.
