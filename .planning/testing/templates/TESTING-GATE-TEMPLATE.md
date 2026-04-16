# Testing Gate Template

**Purpose:** Copy-paste this template into your phase's CONTEXT.md to declare phase type and testing requirements. Fill in the `{placeholder}` fields using the phase-type taxonomy at `.planning/testing/rules/canonical/PHASE-TYPE-TAXONOMY.md`.

---

## Template

Copy the block below into your CONTEXT.md:

```markdown
### Testing Gate

**Phase type:** {CODE | EVALUATION | FRAMEWORK | SYNTHESIS | mixed with +, e.g. CODE+FRAMEWORK}

**Minimum sessions:** {number — derive from phase scope; CODE: at least 1 Agent Teams session + 1 red-path session; EVALUATION: at least 2 independent evaluator runs; FRAMEWORK: at least 1 snapshot-before/after comparison; SYNTHESIS: N/A}

**Required validator checks:**
{List from PHASE-TYPE-TAXONOMY.md per declared type. For mixed types, list the union.}
- {e.g., AgentExecutionValidator all 12 checks (CODE)}
- {e.g., Dual-Opus evaluator with disagreement threshold (EVALUATION)}
- {e.g., Snapshot-before/after diff (FRAMEWORK)}
- {e.g., Human review checklist (SYNTHESIS)}

**Acceptance criterion:**
{Specific, measurable outcome per phase type. Must be directly transcribable into a plan task's <done_criteria> block.}
- {e.g., All 12 AgentExecutionValidator checks pass on at least 1 session (CODE)}
- {e.g., No evaluation dimension regresses > 10 points vs baseline (EVALUATION)}
- {e.g., Snapshot diff shows no unintended behavioral changes (FRAMEWORK)}
- {e.g., Human review checklist has all items marked PASS (SYNTHESIS)}

**intelligence_contribution:** {optional: list of Tier 2 modules this phase feeds, e.g. coverage_radar, scenario_synthesis_engine — see PHASE-TYPE-TAXONOMY.md for the full module list}

**Snapshot Protocol (FRAMEWORK and mixed-type phases including FRAMEWORK only):**
Before first framework-modifying task:
1. Create snapshot directory:
   ```bash
   mkdir -p .vrs/snapshots/{phase}/
   ```
2. Record change ID (jj):
   ```bash
   jj log -r @ --no-graph -T change_id > .vrs/snapshots/{phase}/pre-change-id.txt
   ```
   Alternative (git):
   ```bash
   git rev-parse HEAD > .vrs/snapshots/{phase}/pre-change-sha.txt
   ```
3. Verification:
   ```bash
   cat .vrs/snapshots/{phase}/pre-change-id.txt
   # Must be non-empty
   jj log -r $(cat .vrs/snapshots/{phase}/pre-change-id.txt) --no-graph
   # Must show a valid commit
   ```
4. Restoration (jj — in separate workspace):
   ```bash
   jj co $(cat .vrs/snapshots/{phase}/pre-change-id.txt)
   ```
   Restoration (git):
   ```bash
   git worktree add .vrs/snapshots/{phase}/workspace $(cat .vrs/snapshots/{phase}/pre-change-sha.txt)
   ```

**Framework contribution:**
- Required artifacts: `.vrs/observations/{phase-id}/` with at least one session artifact
- Post-phase note: update `.vrs/evaluations/progress.json` with phase entry
```

---

## Filling Instructions

1. **Determine your phase type** from `.planning/testing/rules/canonical/PHASE-TYPE-TAXONOMY.md`
2. **Look up the testing requirements** for your type(s) in the taxonomy
3. **Fill in each field** — every field should have a concrete value, not a description of what should go there
4. **For mixed types:** list the union of requirements from all declared types. Mark each requirement with its source type in parentheses.
5. **Snapshot Protocol:** Include only if your phase type includes FRAMEWORK. Omit entirely for pure CODE, EVALUATION, or SYNTHESIS phases.
6. **intelligence_contribution:** Optional. Include if you know which Tier 2 intelligence modules your phase data feeds. Omit if unknown.
7. **Acceptance criterion:** Must be directly usable as plan task `<done_criteria>`. If you can't write a done criterion from it, the criterion is too vague.

---

## Enforcement

Testing gate fields become **done criteria in plan tasks** per `PLAN-PHASE-GOVERNANCE.md`. They are not advisory annotations. A plan task is not complete unless its testing gate requirements — derived from the phase-type taxonomy — are satisfied.

---

## Examples

### Example: SYNTHESIS Phase (e.g., VulnDocs documentation)

```markdown
### Testing Gate

**Phase type:** SYNTHESIS

**Minimum sessions:** N/A (no Agent Teams sessions required)

**Required validator checks:**
- Human review checklist with binary pass/fail items
- Pattern validation CLI pass: `uv run alphaswarm vulndocs validate vulndocs/` exits with zero errors

**Acceptance criterion:**
- Human review checklist completed with all items marked PASS
- `uv run alphaswarm vulndocs validate vulndocs/` exits 0
- Persistent artifacts in `.vrs/observations/{phase-id}/` with completed review checklist and validation output

**intelligence_contribution:** coverage_radar (new patterns expand coverage map)

**Framework contribution:**
- Required artifacts: `.vrs/observations/{phase-id}/` with at least one session artifact
- Post-phase note: update `.vrs/evaluations/progress.json` with phase entry
```

### Example: CODE+FRAMEWORK Phase (e.g., Phase 3.1c.1)

```markdown
### Testing Gate

**Phase type:** CODE+FRAMEWORK

**Minimum sessions:** 2 (at least 1 Agent Teams session + 1 red-path session)

**Required validator checks:**
- AgentExecutionValidator all 12 checks (CODE)
- At least 1 red-path session (CODE)
- Snapshot-before/after diff (FRAMEWORK)
- Regression on prior baselines (FRAMEWORK)

**Acceptance criterion:**
- All 12 AgentExecutionValidator checks pass on at least 1 session (CODE)
- Red-path session completes with expected error handling behavior (CODE)
- Snapshot diff shows no unintended behavioral changes in testing framework (FRAMEWORK)
- No evaluation dimension regresses > 10 points vs baseline (FRAMEWORK)
- Persistent artifacts in `.vrs/observations/3.1c.1/`

**intelligence_contribution:** behavioral_fingerprinting, coverage_radar

**Snapshot Protocol (FRAMEWORK):**
Before first framework-modifying task:
1. Create snapshot directory:
   ```bash
   mkdir -p .vrs/snapshots/3.1c.1/
   ```
2. Record change ID (jj):
   ```bash
   jj log -r @ --no-graph -T change_id > .vrs/snapshots/3.1c.1/pre-change-id.txt
   ```
3. Verification:
   ```bash
   cat .vrs/snapshots/3.1c.1/pre-change-id.txt
   jj log -r $(cat .vrs/snapshots/3.1c.1/pre-change-id.txt) --no-graph
   ```

**Framework contribution:**
- Required artifacts: `.vrs/observations/3.1c.1/` with at least one session artifact
- Post-phase note: update `.vrs/evaluations/progress.json` with phase entry
```

---

## References

- Phase-type taxonomy: `.planning/testing/rules/canonical/PHASE-TYPE-TAXONOMY.md`
- Plan governance: `.planning/testing/PLAN-PHASE-GOVERNANCE.md`
- Testing framework: `.planning/testing/rules/canonical/TESTING-FRAMEWORK.md`
