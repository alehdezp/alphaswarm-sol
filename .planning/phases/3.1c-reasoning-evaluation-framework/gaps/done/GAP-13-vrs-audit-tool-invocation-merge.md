# GAP-13: Does /vrs-audit Actually Invoke Tools and Merge Findings?

**Created by:** improve-phase
**Source:** P7-IMP-18
**Priority:** HIGH
**Status:** resolved
**depends_on:** []

## Question

The `/vrs-audit` skill prompt's `allowed-tools` includes `Bash(alphaswarm*)` which permits `alphaswarm tools run`. The Python handler layer has no RunToolsHandler, but the CC orchestration layer COULD invoke tools if instructed. Is the tool+agent disconnect a Python architecture limitation, or simply a missing instruction in the skill prompt's 7-phase flow? What would it take to close the gap at the prompt level (not code level)?

## Reframed By: adversarial review (pass 1)

Original question: "Does /vrs-audit actually invoke external tools (Slither, Aderyn) AND merge their findings with agent investigation results?"

Reframe reason: The original research correctly found that Python handlers.py has no RUN_TOOLS action and the pipelines are disconnected at the code level. But the shipped product is Claude Code reading skill prompts. The skill's `allowed-tools` already permits `alphaswarm tools run`. The disconnect is a PROMPT-LEVEL OMISSION (no phase says "call tools"), not an architectural separation. Closing the gap may require ~10 lines in the skill prompt rather than a new RouteAction + RunToolsHandler. This changes planning implications for Plans 09-11 and evaluation contracts.

## Original Question

## Context

P7-IMP-18 notes that 32 scenario YAMLs exist but no scenario tests the full E2E pipeline: build KG → run tools → spawn agents → merge findings → produce deduplicated report. The merge step and deduplication are never verified. Before writing scenarios, we need to know whether the merge capability exists at all in the current `/vrs-audit` implementation.

Affects: Plans 09-11 (orchestrator testing), new scenarios UC-AUDIT-009/010.

## Research Approach

- Read the `/vrs-audit` skill: `src/alphaswarm_sol/shipping/skills/audit.md` or similar
- Read the orchestration module: `src/alphaswarm_sol/orchestration/`
- Check finding-merger or deduplication code: search for "merge", "deduplicate", "finding"
- Check if `alphaswarm tools run` output is consumed by the agent pipeline
- Determine: is the full pipeline implemented, partially implemented, or just planned?

## Findings (Pass 2 — Prompt-Level Analysis)

**Confidence: HIGH**

### Answer: It is a prompt-level omission, not an architecture limitation

The disconnect is fixable at the skill prompt level. No new Python code (no `RunToolsHandler`, no `RouteAction.RUN_TOOLS`) is required to have CC invoke tools during an audit. The gap has two layers: (1) the skill prompt never tells CC to run tools, and (2) CC would need to merge results in-context since the Python `SemanticDeduplicator` operates on `VKGFinding` objects that CC cannot easily produce from Bash output. Layer 1 is trivially fixable (~15 lines of prompt). Layer 2 requires CC to do its own synthesis, which it is fully capable of but which is unstructured/non-deterministic.

### Sub-Question Answers

**Q1: What does the /vrs-audit skill's `allowed-tools` field actually contain?**

From `src/alphaswarm_sol/shipping/skills/audit.md`, lines 24-28:
```yaml
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash(alphaswarm*)
```

The glob pattern `Bash(alphaswarm*)` permits ANY `alphaswarm` CLI subcommand, including `alphaswarm tools run slither ./contracts --json` and `alphaswarm tools analyze ./contracts`. This is not a tooling restriction -- CC is already authorized to call tools.

**Q2: Does the skill's 7-phase flow mention external tools at all?**

No. The 7 phases (INTAKE, CONTEXT, BEADS, EXECUTE, VERIFY, INTEGRATE, COMPLETE) make zero reference to Slither, Aderyn, or any `alphaswarm tools` command. The word "tool" appears only in:
- Line 266: Error handling table ("Check Slither installation with /vrs-health-check")
- The "Related Skills" table does NOT list `/vrs-tool-slither`, `/vrs-tool-aderyn`, or `/vrs-tool-coordinator`

This is a pure omission. The phases were designed around the agent pipeline (build-kg, pattern detection, agent spawn, debate, verdicts) and the tool pipeline was simply never wired in at the prompt level.

**Q3: Could CC simply call `alphaswarm tools run` via Bash during one of the existing phases?**

Yes, with one qualification. The CLI command `alphaswarm tools run` (`src/alphaswarm_sol/cli/tools.py`, line 384) exists and works:

```bash
alphaswarm tools run slither ./contracts --format json --output findings.json
```

It outputs structured JSON: findings count, per-finding severity/title/location, and writes a JSON file if `--output` is specified. The richer `alphaswarm tools analyze` command (line 460) runs the full pipeline: coordinate tool selection, execute in parallel, deduplicate, and optionally create beads. CC can read this output and synthesize it.

However, note that `audit.md` has `disable-model-invocation: true` (line 22) and `context: fork` (line 21). The `disable-model-invocation: true` flag means CC only executes this skill when the USER explicitly invokes `/vrs-audit` -- it cannot be auto-triggered. The `context: fork` means it runs in an isolated context fork. Neither of these prevents tool invocation.

**Q4: If tool invocation were added to the skill prompt, would CC need to merge results itself (in context), or does the Python code handle that?**

CC would need to merge in-context. Here is why:

- The Python `SemanticDeduplicator` (`src/alphaswarm_sol/orchestration/dedup.py`) takes `List[VKGFinding]` objects (from `tools/adapters/sarif.py`). These are Python data classes created by the tool executor, not by CC.
- The Python `GenerateReportHandler` (`src/alphaswarm_sol/orchestration/handlers.py`) iterates over `pool.verdicts` (agent verdicts). It does not reference `VKGFinding` or `DeduplicatedFinding`.
- There is no Python function that takes both tool JSON output and agent verdicts and merges them.

BUT: `alphaswarm tools analyze ./contracts --beads` already creates beads from tool findings (via `beads/from_tools.py`). If CC ran this command during Phase 2.5 (before agent investigation), the tool findings would become beads, and the agent pipeline would naturally investigate them alongside VKG-detected beads. This is the **simplest integration path** -- no Python merge code needed at all.

**Q5: What about the tool-specific skills (/vrs-tool-slither, /vrs-tool-aderyn) -- could /vrs-audit invoke those?**

Technically no, due to skill architecture. Claude Code skill invocation (`/vrs-tool-slither`) is a user-facing slash command. One skill cannot programmatically invoke another skill. However, CC executing `/vrs-audit` CAN run the same Bash commands that `/vrs-tool-slither` would run, because both use `Bash(alphaswarm*)`. The tool skills are just prompt wrappers around CLI commands.

The `/vrs-tool-coordinator` skill (`src/alphaswarm_sol/shipping/skills/tool-coordinator.md`) is useful conceptual guidance -- it defines which tools to run based on project characteristics and provides the decision matrix. But CC would have to internalize this logic, not call it as a skill.

### What Would It Take to Close the Gap

**Option A: Minimal prompt patch (~15 lines, lowest effort)**

Add a "Phase 2.5: Static Analysis" step to `audit.md` between CONTEXT and BEADS:

```markdown
### Phase 2.5: TOOLS
**Run static analysis tools and create beads from findings**

\`\`\`bash
# Run full tool analysis pipeline with bead creation
alphaswarm tools analyze contracts/ --beads --output .vrs/tool-results/
\`\`\`

This runs available static analysis tools (Slither, Aderyn, etc.) in parallel,
deduplicates their findings, and creates investigation beads from HIGH/CRITICAL
results. These beads join the VKG-detected beads in Phase 3 for agent investigation.

If tools are not installed, skip this phase (check with `alphaswarm tools status`).
```

Also add to the "Related Skills" table:
```markdown
| `/vrs-tool-slither` | Run Slither analysis independently |
| `/vrs-tool-aderyn` | Run Aderyn analysis independently |
| `/vrs-tool-coordinator` | Analyze project and plan tool strategy |
```

**Why this works:** `alphaswarm tools analyze --beads` creates beads from tool findings via the existing `beads/from_tools.py` module. These beads enter the bead pool. Phase 4 (EXECUTE) spawns agents to investigate ALL beads -- it does not distinguish VKG-detected from tool-detected beads. The agent pipeline naturally handles them.

**What is NOT handled:** The final report (Phase 7) would only show agent verdicts on beads. Tool findings that were LOW/MEDIUM (not converted to beads) would be lost. CC would need a prompt instruction in Phase 7 to also summarize `.vrs/tool-results/findings.json` for completeness.

**Option B: Full prompt integration (~40 lines, medium effort)**

Same as Option A, plus:
1. In Phase 7 (COMPLETE), add instruction: "Read `.vrs/tool-results/findings.json` and include a 'Static Analysis Supplement' section in the report for tool findings that were not promoted to beads."
2. In Phase 3 (BEADS), add instruction: "Cross-reference VKG-detected patterns against tool-created beads. If a VKG pattern and a tool finding point to the same location, annotate the bead with both sources."

**Option C: Python-level integration (not recommended for now)**

Add `RouteAction.RUN_TOOLS` and `RunToolsHandler` as described in the original (Pass 1) recommendation. This is the "proper" engineering solution but is unnecessary for the shipped product, where CC orchestrates via prompts, not via Python handlers.

### Architecture Diagram (Updated)

```
CURRENT STATE:                          WITH OPTION A (prompt patch):

  /vrs-audit skill                       /vrs-audit skill
      |                                      |
      v                                      v
  Phase 1: INTAKE                        Phase 1: INTAKE
  Phase 2: CONTEXT (build-kg)            Phase 2: CONTEXT (build-kg)
  Phase 3: BEADS (pattern detect)        Phase 2.5: TOOLS (analyze --beads) <-- NEW
  Phase 4: EXECUTE (spawn agents)        Phase 3: BEADS (pattern detect)
  Phase 5: VERIFY (debate)               Phase 4: EXECUTE (agents investigate ALL beads)
  Phase 6: INTEGRATE                     Phase 5: VERIFY (debate)
  Phase 7: COMPLETE (agent verdicts)     Phase 6: INTEGRATE
      |                                  Phase 7: COMPLETE (verdicts + tool supplement)
      v                                      |
  Agent-only verdicts                        v
                                         Combined verdicts (tool-seeded + VKG-seeded)

  ---SEPARATE, UNCONNECTED---           The `alphaswarm tools analyze --beads` command
                                        bridges the gap by converting tool findings into
  CLI: alphaswarm tools analyze         beads that the agent pipeline already handles.
      |
      v
  ToolRunner -> Dedup -> Beads
```

### Files Examined (Pass 2)

| File | Lines | What was checked |
|------|-------|-----------------|
| `src/alphaswarm_sol/shipping/skills/audit.md` | 1-279 | Full skill prompt: allowed-tools, 7-phase flow, related skills, error handling |
| `src/alphaswarm_sol/shipping/skills/tool-slither.md` | 1-206 | Skill structure, Bash commands used, output format, bead creation |
| `src/alphaswarm_sol/shipping/skills/tool-aderyn.md` | 1-219 | Same analysis as Slither skill |
| `src/alphaswarm_sol/shipping/skills/tool-coordinator.md` | 1-146 | Decision matrix, parallel groups, never-skip patterns, strategy output |
| `src/alphaswarm_sol/shipping/skills/investigate.md` | 1-50 | Confirms skills share `Bash(alphaswarm*)` pattern |
| `src/alphaswarm_sol/cli/tools.py` | 1-710 | CLI `run` command (line 384): output format, JSON structure. `analyze` command (line 460): full pipeline with `--beads` flag |
| `src/alphaswarm_sol/tools/runner.py` | 1-637 | `ToolResult` dataclass: `success`, `output` (text), `exit_code`, `runtime_ms` -- what CC would read from Bash |
| `src/alphaswarm_sol/orchestration/router.py` | 42-62 | Confirmed: no `RUN_TOOLS` in `RouteAction` enum |

## Recommendation

### Prescriptive Action

**The tool+agent disconnect is a prompt omission, not an architecture limit. Close it with Option A (minimal prompt patch).**

1. **Add Phase 2.5: TOOLS to `src/alphaswarm_sol/shipping/skills/audit.md`** between Phase 2 (CONTEXT) and Phase 3 (BEADS). The phase should call `alphaswarm tools analyze $CONTRACTS_PATH --beads --output .vrs/tool-results/`. This converts tool findings into beads that the existing agent pipeline naturally processes. Estimated: ~15 lines of prompt.

2. **Add a tool supplement instruction to Phase 7 (COMPLETE)** so CC reads `.vrs/tool-results/findings.json` and appends a "Static Analysis Supplement" section to the report for LOW/MEDIUM tool findings not promoted to beads. Estimated: ~5 lines of prompt.

3. **Add `/vrs-tool-slither`, `/vrs-tool-aderyn`, `/vrs-tool-coordinator` to the Related Skills table** in `audit.md`. Currently absent.

4. **Do NOT build Python-level `RunToolsHandler` / `RouteAction.RUN_TOOLS`** for this purpose. The CC orchestration model means the prompt IS the integration layer. Python handlers are for structured, deterministic operations; tool invocation via CC + bead creation via `--beads` flag is sufficient.

5. **For 3.1c evaluation contracts:** `orchestrator-full-audit.yaml` CAN expect tool findings in the audit output, but only after the prompt patch lands. Until then, evaluation contracts should test the two pipelines independently:
   - Agent pipeline: KG build -> pattern detection -> bead creation -> agent spawn -> debate -> verdicts
   - Tool pipeline: `alphaswarm tools analyze` -> deduplicate -> beads
   - Integration: beads from tool pipeline appear in agent verdicts (testable after prompt patch)

6. **Revise UC-AUDIT-009/010:** These are NOT blocked by a missing feature. They are blocked by a missing prompt instruction. After the prompt patch, they become testable. Reclassify from "blocked: feature not implemented" to "blocked: prompt patch needed (estimated: 1 hour)."

### Confidence Assessment

- That `allowed-tools: Bash(alphaswarm*)` permits tool invocation: **HIGH** (directly observed in YAML frontmatter)
- That `alphaswarm tools analyze --beads` creates beads from tool findings: **HIGH** (code path traced through `cli/tools.py` line 537 -> `beads/from_tools.py`)
- That the prompt patch is sufficient for basic integration: **HIGH** (beads are beads regardless of source; agent pipeline is source-agnostic)
- That CC will reliably follow the Phase 2.5 instruction: **MEDIUM** (depends on prompt quality, CC may skip if tools are not installed, may produce inconsistent output formatting)
- That no Python code changes are needed: **HIGH** for basic integration; **MEDIUM** if structured deduplication of tool+agent findings in the final report is required (CC in-context merge is non-deterministic)

### Plans Affected

| Plan | Impact | Change from Pass 1 |
|------|--------|---------------------|
| Plans 09-11 | Can test combined pipeline after prompt patch | Was: test separately. Now: test combined after ~1h prompt work. |
| UC-AUDIT-009 | Unblocked by prompt patch | Was: blocked by missing feature. Now: blocked by missing prompt (~15 lines). |
| UC-AUDIT-010 | Partially unblocked | Tool+agent beads merge via pool. Report dedup requires CC in-context synthesis. |
| Evaluation contracts | Update `orchestrator-full-audit.yaml` to optionally expect tool-sourced beads | Was: must NOT expect tool findings. Now: can expect them conditionally. |
| `/vrs-audit` skill | Prompt patch needed: Phase 2.5 + Phase 7 supplement + Related Skills | New action item, estimated 1 hour. |
