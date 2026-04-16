# Phase 3.1b Philosophy: The Foundation That Makes Testing Possible

## One Sentence

Phase 3.1b builds the infrastructure plumbing so that Phase 3.1c can answer the only question that matters: "Is the product actually good?"

---

## Identity

Phase 3.1b is **infrastructure, not product**. It does not test anything. It does not evaluate anything. It does not ship anything. It builds the pipes, bridges, parsers, hooks, scenarios, and collectors that the real testing framework (3.1c) needs to exist.

Without 3.1b, 3.1c has nothing to work with.
Without 3.1c, 3.1b is a pile of unused tools.

This asymmetry is intentional. Infrastructure serves a purpose only when something uses it. Every artifact in 3.1b exists because a specific 3.1c plan depends on it. If a 3.1b deliverable has no downstream consumer in 3.1c, it should not exist.

---

## The Three Commandments

### 1. Build for 3.1c, Not for Yourself

Every component in 3.1b must answer: "Which 3.1c plan needs this, and what is the exact API contract?"

- The TranscriptParser extensions exist because 3.1c-03 (Observation Parser) and 3.1c-04 (Graph Value Scorer) need `timestamp`, `duration_ms`, `get_raw_messages()`, and `get_messages_between()`.
- The hook infrastructure exists because 3.1c-02 (Observation Hooks) needs `install_hooks()` to accept arbitrary hook lists without clobbering existing ones.
- The OutputCollector exists because 3.1c-08 (Evaluation Runner) needs a unified view of scenario artifacts.
- The scenario corpus exists because 3.1c-09/10/11 need real contracts with ground truth to test against.

If you cannot point to a specific 3.1c consumer, you are building the wrong thing.

### 2. Extend, Never Replace

The existing harness (3,745 LOC, 91+ passing tests) is the foundation. Nothing is deleted. Components are kept as-is, extended where needed, or adapted for new requirements.

- TranscriptParser: **add** 2 fields and 3 methods, **keep** all existing API
- WorkspaceManager: **extend** `install_hooks()` to accept arbitrary lists, **keep** default behavior
- ScenarioLoader: **extend** schema to accept `evaluation_guidance` and `evaluation` blocks, **keep** existing fields working
- All 91+ existing tests: **must still pass** after every 3.1b plan

Replacing working code is not extending. If all existing tests don't pass after your change, your change is wrong.

### 3. Prove It Works, Then Automate It

The interactive evaluation loop is primary. Automation is secondary.

1. **First**: I (Claude Code) run scenarios interactively, observe behavior, reason about quality
2. **Then**: Once I know what "good" looks like, Companion scripts automate known-good regressions

This order is non-negotiable. Automating before understanding produces tests that verify the wrong things. The interactive smoke test (3.1b-07) exists precisely to force this order.

---

## What "Done" Looks Like for Each Plan

Every plan in 3.1b has a single question that determines completion:

| Plan | The Question |
|------|-------------|
| 3.1b-01 | Can Python code talk to Companion's REST and WebSocket APIs? (Optional — Wave 4) |
| 3.1b-02 | Does the TranscriptParser expose all fields 3.1c needs (BSKGQuery, TeamObservation, timing), and does the OutputCollector produce a readable summary? |
| 3.1b-03 | Can I register N hooks per event type without clobbering, and does `.vrs/observations/` exist? |
| 3.1b-04 | Can I spawn a team, exchange messages, monitor lifecycle, shut down cleanly, AND isolate test runs via Jujutsu workspaces? |
| 3.1b-05 | Does the scenario DSL parse `evaluation_guidance`, `evaluation`, and `post_run_hooks` without error? |
| 3.1b-06a | Does the pattern catalog cover all 466+ patterns with generation-ready specs, and does the adversarial taxonomy cover 3 categories? |
| 3.1b-06a | Can the generation agent produce compilable, obfuscated, multi-pattern Solidity projects from pattern specs? |
| 3.1b-06b | Are 15-20 adversarial projects committed as Jujutsu fixtures, with ground truth validated and coverage thresholds met? |
| 3.1b-07 | Did I (Claude Code) run a complete interactive evaluation loop through all infrastructure (including Jujutsu isolation) and document my reasoning? |

If the answer is "yes" with evidence, the plan is done. If the answer requires caveats, the plan is not done.

---

## Alignment Rules for Every Plan

Every plan created for Phase 3.1b must satisfy ALL of the following:

### Rule A: Downstream Traceability

Every deliverable must trace to a specific 3.1c dependency. The plan document must include a table:

| Deliverable | 3.1c Consumer | API Contract |
|-------------|---------------|--------------|
| (what you're building) | (which 3.1c plan) | (exact method signatures, fields, schema) |

If a deliverable has no row in this table, remove it from the plan.

### Rule B: Backward Compatibility

Every change to existing code must:
1. Keep all existing tests passing
2. Keep all existing API signatures unchanged
3. Add new capabilities through new methods/fields, not by modifying existing ones

If an existing test fails after your change, fix your change, not the test.

### Rule C: Exit Gates Are Binary

Exit gates are pass/fail. There is no "mostly passes" or "passes with known issues." Each plan's exit gate is a checklist of concrete, observable conditions. All must be true.

### Rule D: Research Is Honest

Phase 3.1b-04 includes genuine research (debrief strategies). Research deliverables are:
- **Not guaranteed to succeed.** Document failures honestly.
- **Not allowed to fabricate.** If SendMessage debrief doesn't work, say so.
- **Required to document alternatives.** If the primary approach fails, what are the options?

Honest "it doesn't work, here's what we tried" is more valuable than optimistic "it works (with workarounds)" for 3.1c planning.

### Rule E: No Feature Creep

3.1b does NOT:
- Test skills, agents, or orchestrator flows (that's 3.1c)
- Evaluate reasoning quality (that's 3.1c)
- Build regression baselines (that's 3.1c-12)
- Create always-on observability (that's 3.1c)
- Modify production prompts (that's 3.1c-12's improvement loop)
- Build CI pipelines (too expensive, on-demand only)

If a plan starts doing any of these things, it has drifted from its purpose.

### Rule F: Validation Artifacts Are Mandatory

No plan is complete without:
1. **Machine Gate Report**: `.vrs/debug/phase-3.1b/gates/<plan-id>.json`
2. **Human Checkpoint Record**: `.vrs/debug/phase-3.1b/hitl/<plan-id>.md`
3. **Drift Log Entry**: `.vrs/debug/phase-3.1b/drift-log.jsonl`

These are not optional documentation. They are proof that the plan was executed correctly and that results are reproducible.

---

## The North Star

Phase 3.1b succeeds when Phase 3.1c can begin execution with zero infrastructure gaps. Every API contract fulfilled. Every extension point accessible. Every scenario compilable. Every hook registerable.

3.1c should never have to say "we need to go back to 3.1b to fix this." If that happens, 3.1b failed.

---

## Anti-Patterns

| Anti-Pattern | Why It's Wrong | What To Do Instead |
|---|---|---|
| Building infrastructure nobody needs | Wasted effort, increases maintenance | Trace every deliverable to a 3.1c consumer |
| Replacing existing code instead of extending | Breaks the 91+ test foundation | Add new methods/fields, keep existing ones |
| Automating before understanding | Tests verify the wrong things | Interactive first, automate second |
| Over-engineering the scenario DSL | DSL is a vehicle, not the product | Keep it simple enough that 3.1c can extend it |
| Skipping the interactive smoke test | Loses the "prove it works" step | 3.1b-07 is mandatory, not optional |
| Marking research as "success" when it isn't | Poisons 3.1c's planning with false assumptions | Document failures as clearly as successes |
| Gold-plating hooks or parser | Infrastructure should be minimal and reliable | Build the minimum that satisfies 3.1c contracts |

---

## Relationship to Testing Philosophy

This phase implements the **infrastructure layer** of the testing identity described in `TESTING-PHILOSOPHY.md`. Specifically:

- TESTING-PHILOSOPHY says "RUNS real workflows" -> 3.1b builds the Companion bridge + harness
- TESTING-PHILOSOPHY says "OBSERVES selectively" -> 3.1b builds the hook registration architecture
- TESTING-PHILOSOPHY says "Real Execution Only" -> 3.1b verifies CLI + Companion work with real sessions
- TESTING-PHILOSOPHY says "External Ground Truth Only" -> 3.1b creates the scenario corpus with ground truth

Phase 3.1b does not implement the intelligence layer (EVALUATES, IDENTIFIES, IMPROVES, DETECTS, REPORTS). That is exclusively Phase 3.1c's domain.
