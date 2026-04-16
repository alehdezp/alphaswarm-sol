# Milestone 6.0: From Theory to Reality

**Created:** 2026-02-08
**Status:** APPROVED FOR EXECUTION
**Philosophy:** Nothing ships until proven. Prove everything. Ship only what works.
**Research:** 14 agent reports (7 assessment + 7 gap resolution plans) totaling ~7,000 lines

---

## The Reality Check (Wave 1 Summary)

| Area | Claimed | Reality |
|------|---------|---------|
| Patterns | 556+ | 6 proven, 237 could work, 310 dead code |
| Detection rate | 84.6% DVDeFi | YAML annotation, ground truth is TODO |
| Agents | 24 | 3-4 functional, rest placeholders |
| Skills | 47 | 19 broken frontmatter, 28 not installed |
| E2E pipeline | Working | Crashes at Stage 4 (pattern matching) |
| Multi-agent debate | Core feature | Never executed; rebuttals hardcoded |
| Graph reasoning | Differentiator | Agents can't run graph queries |
| Benchmarks | Multiple | Zero benchmarks ever run |
| Competitive position | World's best | 5/10 — 6 patterns vs Slither's 90+ |

---

## Phase Structure

### Phase 1: Emergency Triage (1-2 days)
**Goal:** Fix the 4 P0 bugs so the product can function at all.

| Task | Fix | Effort | Source |
|------|-----|--------|--------|
| 1.1 | Fix PatternEngine API (add `pattern_dir`, `run_all_patterns`, `run_pattern`) | 2-3h | W2-1 Bug 1 |
| 1.2 | Fix `orchestrate resume` infinite loop (state advancement in router) | 3-4h | W2-1 Bug 2 |
| 1.3 | Fix 19 skill frontmatters (`skill:` → `name:`) | 1h | W2-1 Bug 3 |
| 1.4 | Fix vulndocs validation (74 entries) | 2-3h | W2-1 Bug 4 |
| 1.5 | Fix `--scope` flag on `orchestrate start` | 30m | W2-1 Additional |
| 1.6 | Fix deprecated google.generativeai warning | 30m | W2-1 Additional |

**Exit Gate:** `beads generate` works, `orchestrate resume` advances, all skills invocable.

---

### Phase 2: Property Gap Quick Wins (2-3 days)
**Goal:** Activate dead patterns by implementing missing properties.

| Task | What | Impact | Effort | Source |
|------|------|--------|--------|--------|
| 2.1 | Emit 37 computed-but-not-emitted properties | Rescues 51 patterns (~50 LOC) | 2h | W2-2 Phase 0 |
| 2.2 | Implement top-10 trivial orphan properties | Rescues ~40 more patterns | 4h | W2-2 Phase 1 |
| 2.3 | Add property validation CI gate | Prevents future drift | 2h | W2-2 |
| 2.4 | Triage patterns: delete 169 totally broken, quarantine 141 partially broken | Honest count | 4h | W2-2 |

**Exit Gate:** Property validation gate passes. Honest pattern count documented (~290 working).

---

### Phase 3: First Working Audit (3-5 days)
**Goal:** ONE complete audit from Solidity contract to vulnerability report.

| Task | What | Source |
|------|------|--------|
| 3.1 | Fix all integration points (12 identified in W2-3) | W2-3 |
| 3.2 | Fix handler API mismatches (DetectPatterns, CreateBeads, SpawnAttackers) | W2-3 |
| 3.3 | Run MVP pipeline on DVDeFi Challenge #1 (Unstoppable) | W2-3 |
| 3.4 | Capture full transcript of working pipeline | W2-3 |
| 3.5 | Create E2E regression test that runs full pipeline | W2-3 |

**MVP Pipeline:**
```
build-kg contract.sol → query patterns → create beads → simple verdict
```

**Exit Gate:** One DVDeFi challenge produces a finding with code location and graph evidence.

---

### Phase 4: Agent Teams Debate (5-7 days)
**Goal:** Real multi-agent debate using Claude Code Agent Teams.

| Task | What | Source |
|------|------|--------|
| 4.1 | Enable Agent Teams (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`) | W2-4 |
| 4.2 | Create `/vrs-team-verify` skill with TeamCreate | W2-4 |
| 4.3 | Write attacker/defender/verifier agent `.md` with proper tools (`Bash(uv run alphaswarm*)`) | W2-4 |
| 4.4 | Implement hook enforcement (graph-first, evidence completeness) | W2-7 |
| 4.5 | Run debate on 3 known-vulnerable contracts | W2-4 |
| 4.6 | Capture debate transcripts as baseline evidence | W2-4 |

**Team Structure:**
```yaml
team_name: vrs-audit-{contract}
lead: audit-orchestrator (delegate mode)
teammates:
  - name: attacker
    agent_type: vrs-attacker
    model: opus
    tools: Read, Grep, Glob, Bash(uv run alphaswarm*)
    skills: [graph-first-template, evidence-packet-format]
    memory: project
  - name: defender
    agent_type: vrs-defender
    model: sonnet
    tools: Read, Grep, Glob, Bash(uv run alphaswarm*)
    skills: [graph-first-template]
    memory: project
  - name: verifier
    agent_type: vrs-verifier
    model: opus
    tools: Read, Grep, Glob, Bash(uv run alphaswarm*)
    memory: project
```

**Exit Gate:** 3 real debates produce verdicts with evidence anchoring. Transcripts prove agents used graph queries.

---

### Phase 5: Benchmark Reality (3-5 days)
**Goal:** Honest metrics on real benchmarks.

| Task | What | Source |
|------|------|--------|
| 5.1 | DVDeFi end-to-end: run pipeline on all 13 challenges | W2-5 |
| 5.2 | Fill DVDeFi ground truth (replace TODO entries) | W2-5 |
| 5.3 | SmartBugs subset: run on 30 contracts with known vulnerabilities | W2-5 |
| 5.4 | Head-to-head: run Slither alone vs AlphaSwarm on same contracts | W2-5 |
| 5.5 | BSKG ablation: run with and without graph on 5 contracts | W2-5 |
| 5.6 | Publish honest results in `benchmarks/RESULTS.md` | W2-5 |

**Exit Gate:** Reproducible precision/recall/F1 numbers. Ablation study determines if graph adds value.

---

### Phase 6: Test Framework Overhaul (3-5 days)
**Goal:** Tests that prove real behavior, not implementation details.

| Task | What | Source |
|------|------|--------|
| 6.1 | Create 20 detection regression tests (contract → finding) | W2-6 |
| 6.2 | Create 5 E2E pipeline integration tests | W2-6 |
| 6.3 | Audit and classify existing 11K tests (sample 50 files) | W2-6 |
| 6.4 | Remove/rewrite worst mock-heavy tests (top 20 offenders) | W2-6 |
| 6.5 | Set up graph cache for test speed | W2-6 |

**Exit Gate:** Detection regression tests all pass. Mock ratio drops below 40%.

---

### Phase 7: Documentation Honesty + Hooks System (2-3 days)
**Goal:** Documentation reflects reality. Hooks enforce quality.

| Task | What | Source |
|------|------|--------|
| 7.1 | Rewrite CLAUDE.md with honest metrics | W2-7 |
| 7.2 | Update docs/ to separate working vs planned features | W2-7 |
| 7.3 | Implement 5 hook configurations (graph-first, evidence, anti-drift, quality, teammate) | W2-7 |
| 7.4 | Consolidate settings (kill aspirational YAML, update JSON) | W2-7 |
| 7.5 | Unify agent systems (deprecate Python swarm, keep Claude Code agents) | W2-7 |

**Exit Gate:** All docs audited. Hooks enforcing graph-first in live sessions.

---

### Phase 8: Ship What Works (2-3 days)
**Goal:** Package the working product for users.

| Task | What |
|------|------|
| 8.1 | Install all functional shipped skills to `.claude/skills/` |
| 8.2 | Clean up legacy skills (`vkg-*` → `vrs-*`) |
| 8.3 | Create demo: `/vrs-audit` on DVDeFi with recorded output |
| 8.4 | Write honest README with real capabilities and limitations |
| 8.5 | GA readiness dossier with benchmark results |

**Exit Gate:** A new user can run `/vrs-audit contracts/` and get a real vulnerability report.

---

## Dependencies

```
Phase 1 (P0 Fixes)
  ├──► Phase 2 (Property Gap)
  │     └──► Phase 5 (Benchmarks)
  ├──► Phase 3 (First Working Audit)
  │     ├──► Phase 4 (Agent Teams)
  │     │     └──► Phase 5 (Benchmarks)
  │     └──► Phase 6 (Test Framework)
  └──► Phase 7 (Docs + Hooks) ←── can start after Phase 1
        └──► Phase 8 (Ship)
```

**Critical path:** 1 → 3 → 4 → 5 → 8

---

## Success Criteria for Milestone 6.0

| Criterion | Measurable Target |
|-----------|------------------|
| E2E audit works | `/vrs-audit` produces findings on DVDeFi |
| Agent debate works | 3 real debates with evidence-anchored verdicts |
| Honest pattern count | N patterns rated, dead patterns removed |
| Benchmark results | SmartBugs precision/recall published |
| Graph value proven | Ablation study shows measurable improvement (or honest "no improvement") |
| Tests prove behavior | 20+ detection regression tests passing |
| Hooks enforce quality | Graph-first and evidence hooks active in production |
| Docs are honest | No unsupported claims in CLAUDE.md or docs/ |

---

## Anti-Patterns to Avoid

1. **NO planning without execution** — Phase 5.0 had 288 plans, 99% "complete", product doesn't work
2. **NO claims without evidence** — Every metric must be reproducible
3. **NO mock-only testing** — Detection tests must use real contracts
4. **NO feature expansion** — Fix what exists before adding new features
5. **NO aspirational documentation** — Only document what actually works
6. **NO theoretical capabilities** — If it hasn't been demonstrated, it doesn't exist

---

## Total Effort Estimate

| Phase | Days | Confidence |
|-------|------|------------|
| 1: P0 Fixes | 1-2 | High |
| 2: Property Gap | 2-3 | High |
| 3: First Audit | 3-5 | Medium |
| 4: Agent Teams | 5-7 | Medium |
| 5: Benchmarks | 3-5 | Medium |
| 6: Test Framework | 3-5 | Medium |
| 7: Docs + Hooks | 2-3 | High |
| 8: Ship | 2-3 | High |
| **Total** | **~21-33 days** | Medium |

With parallel execution (Phases 2+7 parallel after Phase 1, Phases 5+6 parallel after Phase 3):
**~15-22 working days** to a shippable, honest product.

---

## Research Artifacts

All reports in `.planning/new-milestone/reports/`:

| Report | Lines | Key Finding |
|--------|-------|-------------|
| `graph-reality-report.md` | 197 | Builder works, agents can't query it |
| `pattern-audit-report.md` | 257 | 69% patterns dead (orphan properties) |
| `agent-behavior-report.md` | 292 | 3 disconnected agent systems, never ran together |
| `workflow-validation-report.md` | 375 | Pipeline breaks at Stage 4, 19 broken skills |
| `competitive-reality-report.md` | 476 | 5/10 vs competition, zero benchmarks |
| `techniques-research-report.md` | 672 | Agent Teams + Hooks are the path forward |
| `w2-p0-fixes-plan.md` | 446 | Exact root causes for all 4 P0 bugs |
| `w2-property-gap-plan.md` | 451 | 37 properties just need emitting, rescues 51 patterns |
| `w2-e2e-pipeline-plan.md` | 668 | 12 integration break points identified |
| `w2-agent-teams-architecture.md` | 1,839 | Full team config, debate protocol, hook enforcement |
| `w2-benchmark-plan.md` | 637 | SmartBugs, DVDeFi, head-to-head, ablation designs |
| `w2-test-framework-plan.md` | 523 | Detection regression tests, mock reduction, speed optimization |
| `w2-docs-hooks-plan.md` | 1,209 | Complete hooks JSON, honest doc rewrites |

---

*Milestone 6.0 Roadmap created: 2026-02-08*
*Based on 14 agent assessments across 2 waves*
*Milestone 5.0 closed*
