# POST-FIX CRITIQUE: Gap Resolution Adversarial Review

**Date:** 2026-02-12
**Reviewer:** Adversarial Critic (Claude Code)
**Scope:** All 11 gap resolutions for Phase 3.1b
**Verdict:** 5 real problems found, 2 wrong fixes, 3.1b-02 overloaded

---

## 1. Cascading Impacts

### GAP-05: `modes: [single, team]` -- Missing Team Configuration

**Impact:** HIGH

The `modes` field tells the system WHAT to do (run as team) but not HOW. The original orchestration scenario had an `agent_team` block specifying roles, models per agent, coordination protocol, and max rounds. The revised `modes: [single, team]` approach deleted all of that.

When a scenario runs with `modes: [team]`, the system needs to know:
- Which agents to spawn (attacker/defender/verifier? or attacker/verifier only?)
- What model to use per agent (all Sonnet? Opus for verifier?)
- What coordination protocol (sequential? round-robin?)
- What task prompts per agent role

None of this is specified anywhere. The `ScenarioConfig` Pydantic model has `modes` but no `agent_team` block. The `TestScenario` dataclass has `modes` but no team configuration. The `get_team_evaluation_questions()` method auto-injects 3 generic questions, but who spawns the agents?

**The gap:** Someone or something must translate `modes: [team]` into an actual team configuration at runtime. This is not a 3.1c problem -- it is a schema problem. 3.1b-02 defines TeamObservation to OBSERVE teams but nothing in 3.1b defines how to CONFIGURE them from scenario YAML. The original GAP-05 design had this. The revision removed it and left a hole.

**Downstream cascade:** 3.1b-04 (Agent Teams framework) builds TeamManager but has no scenario-driven team configuration to consume. 3.1b-07 (smoke test) needs to spawn a team from a scenario but the scenario does not describe the team.

### GAP-01: TeamObservation Designed But Not Implemented

**Impact:** MEDIUM

The GAP-01-02 resolution document contains ~500 lines of Python code for `TeamObservation`, `AgentObservation`, `InboxMessage`, `OutputCollector`, `CollectedOutput`, `BSKGQuery`, plus 400+ lines of tests. This is a design document, not code. The file `tests/workflow_harness/lib/output_collector.py` does not exist yet.

When 3.1b-02 runs via `/gsd:plan-phase`, the planner will see context.md saying "Added to 3.1b-02 Part B: TeamObservation model" but must discover the full design from `gap-resolutions/GAP-01-02-resolution.md`. The design is thorough but:

1. The 3.1b-02 plan does not exist yet (file `3.1b-02-PLAN.md` was not found). The planner must generate it from context.md which now has a significantly expanded scope.
2. The design references `EventStream` constructor taking a `list[dict]` but the actual `EventStream.__init__` signature should be verified -- tests in the resolution use `EventStream(team_fixture["events"])` but this may not match the real constructor.
3. `AgentObservation.messages_sent` filters by `sender == self.agent_id or sender == self.agent_type`. But inbox file format shows `"from": "team-lead"` using agent NAME, not ID or type. If the attacker's name is "vuln-hunter" but agent_type is "attacker", neither filter matches.

### GAP-02: `cited_in_conclusion` Heuristic Fragility

**Impact:** MEDIUM

The `_check_citation()` method uses a heuristic: extract words > 5 chars from the result, remove common Solidity words, check if >= 2 "distinctive" terms appear in subsequent text. Problems:

1. **False positives on contract names:** If the query result mentions `VulnerableVault` and subsequent text also mentions `VulnerableVault` (because the agent is analyzing that contract), the citation check passes even if the agent is NOT citing the query result but just referring to the contract generally.

2. **False negatives on short results:** Results like "Found 0 nodes matching pattern" have very few distinctive terms. The heuristic returns `False` for empty or negative results, even though citing "no nodes found" IS citing the result.

3. **500-char truncation interaction:** The resolution acknowledges this (recommends 2000 chars for BSKG queries) but this change is recommended, not mandated. If forgotten, citation detection will be systematically biased against long query results.

4. **3.1c-04 dependency:** The Graph Value Scorer builds directly on `graph_citation_rate()`. If the rate is unreliable due to these heuristic issues, the entire scoring framework has a fragile foundation. The scorer would need its own citation detection logic, making `graph_citation_rate()` redundant.

### GAP-03: Wave 1 Parallelization Assumption

**Impact:** LOW

GAP-03 reordered execution so Wave 1 runs 02+03+06 in parallel. Plan 03 is already DONE. Plans 02 and 06 have no code-level dependency on each other. However:

GAP-06 and GAP-07 expanded 3.1b-06's scope to include adversarial scenarios and pattern-derived generation. The adversarial scenarios reference ground-truth schema fields like `adversarial_category`, `trick_applied`, `detection_difficulty`. Plan 02 defines `GroundTruth` in `config_schema.py` but that class does NOT include these adversarial fields. Are they ad-hoc YAML fields that bypass schema validation? Or should they be in the Pydantic model?

If the ground-truth schema is defined in 02 and the adversarial fields are expected by 06, there is an implicit dependency: 06 must either extend the schema from 02 or accept that its adversarial ground truth lives outside the validated schema.

**Verdict:** The parallelization is fine at the code level, but the schema consistency between ground truth formats needs explicit coordination. Currently it is implicit.

### GAP-11: `failure_notes` Deferred Classification

**Impact:** LOW

The revised approach (simple `failure_notes: str` instead of `FailureCategory` engine) is genuinely better for now. However, 3.1c-12 (regression baseline) plans to use failure triage to determine which failures are regressions vs flaky vs infrastructure. With only free-text notes, 3.1c-12 must either:

1. Parse natural language failure_notes to categorize failures (fragile, LLM-dependent)
2. Build the classifier itself (scope creep from 3.1b into 3.1c)
3. Do manual triage (defeats the purpose of automated regression)

The cost is acceptable now but the debt is real and will be paid in 3.1c.

---

## 2. New Gaps Identified

### NEW-GAP-01: Team Configuration Schema Missing (Severity: HIGH)

**Problem:** `modes: [team]` declares intent but provides no team configuration. No schema field exists for agent roles, models, tasks, or coordination protocol. The original GAP-05 `agent_team` block was removed but not replaced.

**Where it breaks:** Any code that tries to execute a scenario in team mode. The harness runner, the TeamManager, and the smoke test all need team configuration that does not exist in the scenario schema.

**Recommended fix:** Add an optional `team_config` field to both `ScenarioConfig` (Pydantic) and `TestScenario` (dataclass). This field is required when `"team"` is in `modes`. Minimal schema:

```yaml
team_config:
  roles: [attacker, defender, verifier]
  model: claude-sonnet-4  # or per-role overrides
  protocol: sequential
```

**Cost to fix:** ~30 LOC (schema) + ~20 LOC (validation: "if team in modes, team_config required"). Add to 3.1b-05 scope.

### NEW-GAP-02: `category` Field on catalog.yaml Is Dead Data (Severity: MEDIUM)

**Problem:** GAP-10 added `category` fields to all 24 agents in `catalog.yaml`. But `catalog.py` (the Python loader) does not parse the `category` field. The `SubagentEntry` dataclass has no `category` attribute. The `_load_catalog()` function ignores it. No `filter_by_category()` function exists.

Until Python code reads this field, it is documentation, not functionality. 3.1c's "smart selection matrix" cannot programmatically use `category` because the data is not accessible via the API.

**Recommended fix:** Add `category: str = "unknown"` to `SubagentEntry` dataclass. Add parsing in `_load_catalog()`. Add `filter_by_category()` convenience function. ~15 LOC total. Should be done in 3.1b-02 or as a separate micro-task before 3.1c begins.

### NEW-GAP-03: Dual Schema Drift Risk -- ScenarioConfig vs TestScenario (Severity: MEDIUM)

**Problem:** `modes` now exists on TWO separate classes:
- `ScenarioConfig` in `config_schema.py` (Pydantic model, line 143): `modes: list[Literal["single", "team"]]`
- `TestScenario` in `scenario_loader.py` (dataclass, line 125): `modes: list[str]`

These are NOT linked by inheritance or composition. They are independent data classes that happen to share field names. The Pydantic model validates `modes` against `Literal["single", "team"]`. The dataclass accepts any string and only filters at parse time (line 296-297 in `load_scenario()`).

If a new mode is added (e.g., `"parallel-team"`), it must be added in THREE places: the Pydantic model's Literal, the dataclass's default, and the loader's `valid_modes` set. No test enforces this consistency.

**Recommended fix:** Either:
- (A) Make `TestScenario` use `ScenarioConfig` internally (composition), or
- (B) Add a test that verifies the two classes accept the same modes set.

Option B is simpler. ~10 LOC test.

### NEW-GAP-04: Audit Script Produces Misleading Coverage Data (Severity: LOW)

**Problem:** The audit script (`audit-vulndocs-coverage.py`) inventories test coverage by keyword-matching `.sol` and `.yaml` file contents against category keywords. It found coverage for `access-control` because `src/` files contain the word "access". The "Scenarios" column lists "test, src" -- meaning it matched files in `examples/testing/test/` and `examples/testing/src/` directories, which are DamnVulnerableDeFi build artifacts, not real test scenarios with ground truth.

The script reports coverage that does not actually exist. A category showing "2 scenarios" might have zero scenarios with structured ground truth.

**Recommended fix:** The script should only count directories that contain a `ground-truth.yaml` file as "covered". Keyword matching is too loose. ~15 LOC change.

### NEW-GAP-05: `get_team_evaluation_questions()` Returns Generic Questions (Severity: LOW)

**Problem:** The 3 auto-injected team evaluation questions are identical for every scenario:
1. "Did the team find more than a single agent would?"
2. "Did evidence pass between agents via SendMessage?"
3. "Did debate improve finding confidence vs solo assessment?"

These are reasonable starting points but are not scenario-specific. An oracle manipulation scenario should ask "Did agents reason about price staleness?" not just "Did the team find more?". The original GAP-05 orchestration scenario had 6 detailed, scenario-specific questions.

**Verdict:** This is by design (generic questions, evaluator adapts). But the gap between "3 generic questions" and "6 specific questions" is the gap between useful orchestration testing and rubber-stamp orchestration testing. Flag as technical debt for 3.1c.

---

## 3. Wrong Fixes

### GAP-05: `modes` Field Does NOT Actually Test Coordination

**Problem statement:** "No scenario tests multi-agent coordination."
**Solution:** `modes: [single, team]` on any scenario.
**Does it solve the problem?** Partially, but critically incomplete.

The original problem was testing whether agents coordinate -- pass evidence, debate, synthesize. The `modes` approach tests whether the team produces a different OUTPUT than a single agent. This is a necessary but NOT sufficient condition for coordination testing.

Consider: A team where all 3 agents independently analyze the same contract and the leader picks the longest answer. The team output differs from single-agent output, but zero coordination occurred. The 3 generic questions from `get_team_evaluation_questions()` ask about evidence passing and debate, but these are evaluation questions for the evaluator brain, not structural guarantees.

**What is missing:**
- Team behavior ground truth (the original `expected_team_behavior` block) that specifies WHAT coordination must look like
- Per-agent task assignments that define each agent's role in the team
- Message flow expectations (attacker sends to verifier, not verifier sends to attacker)

**Recommendation:** The `modes` approach is fine as a lightweight mechanism, but at least ONE scenario should have explicit team behavior ground truth. This could be done by adding an optional `team_ground_truth` field to the scenario schema, used only when evaluating team mode output. The original GAP-05 `expected_team_behavior` YAML should be preserved as an optional schema extension, not deleted entirely.

### GAP-10: `category` on catalog.yaml Is Data Without Consumers

**Problem statement:** "3.1c's smart selection matrix depends on categorizing workflows."
**Solution:** Add `category` field to `catalog.yaml`.
**Does it solve the problem?** No.

The smart selection matrix needs to:
1. Given a scenario, determine which evaluation dimensions apply
2. Given a workflow category, determine which hooks to enable
3. Given an agent, determine which evaluation strategy to use

Adding `category` to YAML makes the data available for human readers but NO CODE reads it. The Python `SubagentEntry` dataclass does not have a `category` field. There is no `filter_by_category()` function. 3.1c would need to either:
- Modify `catalog.py` to parse `category` (should have been done in this gap)
- Read `catalog.yaml` directly (bypassing the existing loader, fragile)
- Hardcode the mapping (defeats the purpose of putting it in YAML)

The original GAP-10 proposal (a `workflow-categories.yaml` with evaluation dimensions, required hooks, and selection rules) was MORE functional because it was self-contained. The revised approach is simpler but also inert.

**Recommendation:** The `catalog.yaml` field is fine but MUST be accompanied by a 15-line Python change to make it programmatically accessible. Add `category: str` to `SubagentEntry` and parse it in `_load_catalog()`. This should be a blocking pre-requisite for closing GAP-10.

---

## 4. 3.1b-02 Scope Assessment

### Current Scope

3.1b-02 now includes:

| Component | Source | LOC Estimate |
|-----------|--------|-------------|
| ToolCall: 2 new fields (timestamp, duration_ms) | Original scope | ~20 |
| 3 new TranscriptParser methods (get_raw_messages, get_message_at, get_messages_between) | Original scope | ~60 |
| OutputCollector + CollectedOutput | Original scope | ~100 |
| BSKGQuery dataclass + 3 public methods + 3 private helpers | GAP-02 | ~200 |
| InboxMessage dataclass | GAP-01 | ~30 |
| AgentObservation dataclass | GAP-01 | ~60 |
| TeamObservation class (from_workspace, evidence_chain, agreement_depth, message_flow, per_agent_graph_usage) | GAP-01 | ~200 |
| OutputCollector team/single auto-detection | GAP-01 | ~50 |
| failure_notes migration to CollectedOutput | GAP-11 | ~10 |
| Extension mechanism documentation | GAP-04 | ~0 (docs only) |
| Tests for all of the above | All gaps | ~400 |
| **TOTAL** | | **~1,130 LOC** |

### Assessment: YES, Overloaded

The original 3.1b-02 was ~180 LOC of production code (2 fields + 3 methods + OutputCollector). After gap resolutions, it is ~730 LOC of production code plus ~400 LOC of tests.

This is a 4x scope increase. The risk is not just size but COHERENCE -- 3.1b-02 now spans three distinct concerns:

1. **TranscriptParser extensions** (text extraction, BSKG query parsing, citation detection)
2. **Multi-agent observation model** (TeamObservation, AgentObservation, inbox parsing)
3. **Output collection infrastructure** (OutputCollector, CollectedOutput, failure notes)

These can be implemented independently. A failure in TeamObservation testing should not block TranscriptParser extensions.

### Recommendation: Split into 02a and 02b

**3.1b-02a: TranscriptParser Extensions + BSKGQuery** (~280 LOC + ~200 LOC tests)
- ToolCall new fields
- get_raw_messages, get_message_at, get_messages_between
- BSKGQuery dataclass + extraction methods
- graph_citation_rate
- Extension mechanism documentation

**3.1b-02b: OutputCollector + TeamObservation** (~450 LOC + ~200 LOC tests)
- InboxMessage, AgentObservation, TeamObservation
- OutputCollector with team/single auto-detection
- CollectedOutput with failure_notes
- Summary method

**Benefits:**
- 02a and 02b can run in parallel (same wave)
- 02a failing does not block 02b (and vice versa)
- Each plan has a focused scope with clear exit criteria
- 02a is lower-risk (extending existing class); 02b is higher-risk (new classes + filesystem access)

---

## 5. Risk Matrix

| ID | Finding | Impact | Likelihood | Risk Score |
|----|---------|--------|------------|------------|
| NEW-GAP-01 | Team configuration schema missing | H | H | **CRITICAL** |
| WRONG-FIX-05 | `modes` does not test coordination | H | M | **HIGH** |
| WRONG-FIX-10 | `category` field has no Python consumer | M | H | **HIGH** |
| NEW-GAP-03 | ScenarioConfig vs TestScenario drift | M | M | **MEDIUM** |
| GAP-02-FRAGILE | cited_in_conclusion heuristic fragility | M | M | **MEDIUM** |
| NEW-GAP-02 | catalog.py ignores category field | M | H | **MEDIUM** |
| 02-OVERLOAD | 3.1b-02 is 4x original scope | M | M | **MEDIUM** |
| GAP-01-IMPL | TeamObservation designed but not code | L | M | **LOW** |
| NEW-GAP-04 | Audit script false coverage signals | L | M | **LOW** |
| GAP-03-SCHEMA | Wave 1 ground truth schema gap | L | L | **LOW** |
| GAP-11-DEBT | Classification deferred to 3.1c | L | L | **LOW** |
| NEW-GAP-05 | Generic team evaluation questions | L | L | **LOW** |

---

## 6. Recommendations (Prioritized)

### P0: Must Fix Before Plan Execution

1. **Add `team_config` to scenario schema (NEW-GAP-01)**
   Add optional `team_config` field to both `ScenarioConfig` and `TestScenario`. Validate: if `"team"` in modes, `team_config` is required. Without this, no team scenario can execute. ~50 LOC. Assign to 3.1b-05.

2. **Add `category` parsing to `catalog.py` (NEW-GAP-02 + WRONG-FIX-10)**
   Add `category: str` field to `SubagentEntry`, parse from YAML in `_load_catalog()`, add `filter_by_category()`. Without this, GAP-10 is cosmetic. ~15 LOC. Can be a standalone micro-task or added to 3.1b-02 scope.

### P1: Should Fix During Planning

3. **Split 3.1b-02 into 02a and 02b (02-OVERLOAD)**
   Reduce risk by splitting parser extensions from observation model. Enables parallel execution and independent failure. Update context.md wave ordering.

4. **Add at least 1 scenario with `team_ground_truth` (WRONG-FIX-05)**
   Preserve the original GAP-05 `expected_team_behavior` block as an optional schema field for scenarios that need explicit coordination testing. Apply to at least the reentrancy scenario. Without this, orchestration testing is "did the team run?" not "did the team coordinate?"

5. **Add schema consistency test (NEW-GAP-03)**
   Write a test that verifies `ScenarioConfig.modes` and `TestScenario.modes` accept the same values. Prevents future drift. ~10 LOC test.

### P2: Should Note, Fix Later

6. **Tune citation heuristic after real data (GAP-02-FRAGILE)**
   The >=2 distinctive terms threshold is a reasonable starting point. After running real transcripts in 3.1b-07, calibrate thresholds. Consider adding a `citation_threshold` parameter to `graph_citation_rate()` so 3.1c can tune it.

7. **Fix audit script false positives (NEW-GAP-04)**
   Add check for `ground-truth.yaml` presence before counting a directory as "covered". Low priority since the script is one-time.

8. **Add scenario-specific team questions (NEW-GAP-05)**
   Allow scenarios to define custom `team_evaluation_questions` in YAML, with the 3 generic questions as defaults. 3.1c can implement this when needed.

---

## Summary

The gap resolutions are well-reasoned and the revised approaches (modes field, failure_notes, inline categories) are generally simpler than the originals. However, two fixes are genuinely incomplete:

1. **`modes: [team]` without team configuration** is a schema hole that prevents team execution entirely. This is the most critical finding.

2. **`category` on catalog.yaml without Python parsing** makes GAP-10 inert -- the "fix" adds data that nothing reads.

The 3.1b-02 scope expansion to ~1,130 LOC is a concern but manageable if split into two parallel sub-plans.

The BSKGQuery citation heuristic is fragile but acceptable as a starting point if explicitly treated as v0 with planned calibration.

The overall gap resolution process was thorough and honest about trade-offs. These are real problems, not nitpicks.
