# MSD Improve-Phase for Codex Parity (V5)

Date: 2026-02-23
Audience: MSD maintainers moving `~/.claude/my-shit-done` parity into Codex-native execution
Primary target: `~/.codex/skills/msd/commands/msd-improve-phase/SKILL.md`
Canonical source of intent: `~/.claude/my-shit-done/commands/msd/improve-phase.md`

## 1) Success contract (what parity means)

Parity is not "same words in markdown." Parity means:

1. Same state-machine outcomes per pass (`IMPROVEMENT-P{N}.md`, lens review, synthesis, convergence gate, auto-chain routing).
2. Same artifact invariants (ID schemes, status transitions, digest updates, prerequisite/research routing).
3. Same orchestration semantics (parallel area review, parallel adversarial lensing, post-review synthesis).
4. Same recovery semantics (pending review checkpoint, missing reviewer output warnings, resumable routing).
5. Same operator affordances (`--auto`, convergence override, deterministic next-step recommendations).
6. Same quality bar under Codex constraints (multi-agent experimental flags, non-interactive approvals, different slash/runtime model).

## 2) Current reality and highest-risk gaps

1. Codex-side MSD command and agent skills are thin wrappers that `@`-reference Claude source files.
2. Canonical `msd-improve-phase` relies on Claude-specific orchestration primitives (`Task(...)`, `Skill(...)`, `AskUserQuestion`) that are not 1:1 runtime primitives in Codex.
3. Canonical adversarial reviewer definition appears unresolved/self-referential in local source (`~/.claude/my-shit-done/agents/msd-adversarial-reviewer.md`), creating ambiguity for deterministic execution.
4. Claude hook model has rich lifecycle events (`PreToolUse`, `ConfigChange`, `WorktreeCreate`, `WorktreeRemove`) while Codex relies on different primitives (config, notify hooks, automations, worktree modes, policy/sandbox).
5. Codex multi-agent is experimental and requires explicit feature enablement; assuming always-on parity is unsafe.
6. Directly embedding Claude command markdown in Codex skill wrappers hides unimplemented semantics and weakens recoverability.

## 3) Feature crosswalk (Claude -> Codex)

| Claude MSD mechanism | Codex equivalent | Gap type | Required adaptation |
|---|---|---|---|
| `Task(subagent_type=...)` | Multi-agent (`spawn_agent` runtime / `multi_agent` feature in Codex CLI) | Partial | Capability gating + fallback to sequential runner |
| `Skill(skill=..., args=...)` chaining | Explicit `$skill-name` invocation + deterministic runner script | Partial | Build command dispatcher in shell/JSONL |
| `AskUserQuestion` inline choices | Interactive prompt or explicit branch policy in non-interactive mode | Partial | Branch-policy matrix (`--auto`, strict defaults, explicit human checkpoint) |
| Hook lifecycle (`PreToolUse` etc.) | Codex config + notify + automations + sandbox/approval policies | Non-equivalent | Policy wrapper layer + command allowlist/denylist scripts |
| Worktree lifecycle hooks | Codex worktree mode/automations + Git worktree commands | Partial | Worktree adapter with explicit create/remove/cleanup logs |
| Claude checkpoint rewind semantics | Codex fork/resume, exec resume, app worktree isolation | Partial | Session replay contract via `codex exec --json` event ledger |
| Slash command command-space | Codex slash (`/plan`, `/status`, `/mcp`, `/agent`, `/experimental`, `/compact`) | Similar | Slash compatibility map + unsupported command traps |
| Dynamic skill loading from `.claude/skills` | Codex skills in `.agents/skills` + `~/.agents/skills` + system | Different pathing | Skill mirror/symlink strategy with deterministic precedence |
| Metaprompted adversarial review | Codex multi-agent or external orchestrator with role prompts | Similar | Standardized lens prompt schema and merge validator |
| Exa-first research | MCP Exa tool in Codex runtime | Similar | Required-tool startup checks + fail-fast if unavailable |

## 4) Large improvement backlog (120 items)

### Track A — Parity contract and governance (10)

1. Add `PARITY-CONTRACT.md` with explicit semantic equivalence criteria for improve-phase.
2. Define non-goals (`cosmetic markdown parity`, `prompt-only parity`) to prevent fake completion.
3. Introduce `PARITY_LEVEL` enum: `L0-doc`, `L1-flow`, `L2-state`, `L3-behavioral`, `L4-production`.
4. Require each improvement item to declare parity level impact.
5. Add `PARITY_GATES.md` with hard gate checks per phase.
6. Add mandatory "unsupported-in-codex" register with owner and retirement plan.
7. Add compatibility matrix across Codex surfaces: CLI, IDE, App, Cloud task.
8. Add mandatory acceptance tests for every branch in convergence gate logic.
9. Add release checklist requiring at least `L3` before defaulting to auto-chain.
10. Add drift policy: if upstream Claude command changes, parity check fails closed.

### Track B — Runtime adapter layer (10)

11. Build `msd-runner` adapter translating canonical command steps into executable codex operations.
12. Implement capability probe at start: multi-agent availability, mcp availability, write access.
13. Add per-capability fallback modes with explicit warnings (not silent degradation).
14. Add execution context object persisted to `.vrs/msd-runtime/context.json`.
15. Add deterministic command registry for `init`, artifact scan, pass detection.
16. Normalize path resolution for padded phase naming and fallback scan.
17. Add safe parser for status lines and structural checks in CONTEXT files.
18. Add digest-first loader that ignores historical archived passes by policy.
19. Add robust error taxonomy (`phase_not_found`, `structural_invalid`, `review_missing`, `merge_incomplete`).
20. Add machine-readable exit codes for orchestration and CI.

### Track C — Instruction compiler and @-reference hygiene (10)

21. Replace direct wrapper-only invocation with compiled Codex-native instruction packs.
22. Build `compile_skill_refs.sh` to resolve `@` references into canonical absolute/relative paths.
23. Enforce max include depth and cycle detection to block recursive/self references.
24. Add lint rule that fails any skill file that references itself.
25. Add section pinning (`@file#anchor`) support for minimal context loads.
26. Add include cache with checksum to detect stale references.
27. Add reference smoke tests across all MSD commands/agents.
28. Add generated instruction manifest per command run.
29. Add explicit provenance block in outputs listing loaded instruction sources.
30. Add `--strict-references` mode that refuses unresolved includes.

### Track D — Metaprompting/template system hardening (10)

31. Define `LENS_PROMPT_SCHEMA.json` for lens name, tension, attack vector, bounds.
32. Define `AREA_BRIEF_SCHEMA.json` for metaprompted area briefings.
33. Add anti-generic checks to reject vague lenses lacking concrete attack question.
34. Add novelty-aware prompt modifiers from `<novelty_map>`.
35. Add pass-aware depth policy (P1 surface, P2 interactions, P3+ structural).
36. Add conflict-aware prompts that force cross-area contradiction hunting.
37. Add research-aware prompt slots to include distilled RESEARCH findings.
38. Add execution-feedback prompt slots for STOP/DRIFT carry-forward.
39. Add deterministic prompt serializer to remove accidental formatting variance.
40. Add prompt-level regression tests (same input -> stable scaffold output).

### Track E — Multi-agent orchestration kernel (10)

41. Add `spawn_plan` abstraction with agent role, model tier, tool budget, timeout.
42. Add per-agent workspace isolation policy (read-only explorer, write-enabled worker).
43. Add agent heartbeat and timeout escalation.
44. Add partial result salvage on timeout/failure.
45. Add deterministic wait/collect ordering independent of return timing.
46. Add explicit missing-output detection with affected-item impact report.
47. Add per-agent token and time budget accounting.
48. Add role templates for `improvement`, `adversarial`, `synthesis`.
49. Add configurable max concurrency by phase size.
50. Add forced sequential mode when multi-agent disabled.

### Track F — Improvement merge and state-machine correctness (10)

51. Implement parser for improvement items with strict field validation.
52. Implement ID renumbering that preserves cross-references and ADV/SYN namespaces.
53. Implement semantic dedupe by target+claim+action graph (not string similarity only).
54. Add deterministic tie-break rule with explainable logs.
55. Add verdict application engine with table-driven transitions.
56. Add REFRAME replacement validator requiring ADV CREATE backfill.
57. Add status transition audit log per item.
58. Add post-merge invariant checks (no orphaned pending-review status).
59. Add pipeline status recomputation from all active files + gaps.
60. Add merge dry-run mode producing diff preview and blast radius summary.

### Track G — Convergence gate and routing parity (10)

61. Implement classification engine (`structural`, `creative-structural`, `cosmetic`).
62. Add fallback heuristic when classification field missing.
63. Add novelty-sensitive convergence threshold logic (80/90 policy).
64. Add advisory/informational/hard-gate behavior by pass number.
65. Add prereq+research pending check before plan-phase routing.
66. Add route priorities aligning with resolve-blockers -> research-gap -> implement -> plan-phase.
67. Add stale-item detector (unchanged >=2 passes) and warning contract.
68. Add `--override-convergence` behavior test matrix.
69. Add non-auto branch chooser with deterministic options and logs.
70. Add early-exit commit/session-record equivalent in Codex execution mode.

### Track H — Hook/worktree equivalence and policy controls (10)

71. Build codex-side policy wrapper to emulate `PreToolUse` deny/allow semantics.
72. Add command allowlist and sensitive path denylist with explicit reason codes.
73. Add config-change detector to emulate `ConfigChange` safety checks.
74. Add worktree lifecycle manager (create/use/cleanup) with event logs.
75. Add automation-safe mode requiring worktree execution for scheduled tasks.
76. Add shutdown flush step for session metadata and transient files.
77. Add protected files policy mirror for `.planning`, `.claude`, security-sensitive paths.
78. Add network policy toggles per execution profile (`cached/live/disabled`).
79. Add preflight check for required MCP servers (`required=true` style behavior).
80. Add policy self-test suite that intentionally triggers blocked commands.

### Track I — Artifact contracts and observability (10)

81. Write JSON schemas for `IMPROVEMENT-P`, `DIGEST`, `LENS`, `SYNTHESIS` blocks.
82. Add event ledger capture via `codex exec --json` for replayable audits.
83. Add run manifest linking inputs, prompts, agents, outputs, and verdict applications.
84. Add provenance manifest for CONFIRM/ENHANCE/PREREQUISITE lineage.
85. Add structured warnings log with code+path+item linkage.
86. Add per-pass scorecard: created, dropped, reframed, confirmed, blocked.
87. Add timeline visualization artifact for long-running passes.
88. Add observability query scripts for unresolved items and route bottlenecks.
89. Add resume hints artifact for exact restart step.
90. Add stale temp-file sweeper with crash-safe retention policy.

### Track J — Skill layout and folder topology for Codex (10)

91. Mirror MSD command skills from `.codex/skills/msd` into `.agents/skills/msd` for Codex-native discovery.
92. Define precedence policy between user and repo skill scopes.
93. Add symlink-safe loader tests for skills and supporting assets.
94. Add metadata normalization in `agents/openai.yaml` (icons/policies/dependencies).
95. Declare explicit tool dependencies (Exa/MCP) in skill metadata.
96. Add per-skill enablement defaults in `.codex/config.toml`.
97. Split giant command files into referenced modules to control token cost.
98. Add command aliases table for slash and `$` triggers.
99. Add install/sync script from `~/.claude/my-shit-done` to Codex layout.
100. Add mismatch detector for missing command/agent parity across folders.

### Track K — CLI orchestration and automation (10)

101. Add `codex exec` wrappers for non-interactive improve-phase pipeline runs.
102. Add `--json` parser to collect item events and failure points.
103. Add structured-output schema mode for final run summary.
104. Add profile presets (`deep-review`, `fast-scan`, `safe-readonly`).
105. Add auto-resume on recoverable failure with bounded retries.
106. Add CI workflow for nightly shadow runs on selected phases.
107. Add automation templates for background improve-phase on worktrees.
108. Add cloud/local mode guardrails to prevent wrong environment assumptions.
109. Add branch/worktree naming conventions for concurrent runs.
110. Add PR comment bot template for parity run summaries.

### Track L — Verification, evals, and rollout safety (10)

111. Build golden transcript corpus from known Claude improve-phase runs.
112. Add step-level behavioral evaluator (invocation, merges, routing correctness).
113. Add rubric scoring: parity, correctness, cost, latency, operator trust.
114. Add anti-fabrication checks (suspiciously fast or invariant outputs).
115. Add chaos tests: missing agent output, malformed item, unresolved reference.
116. Add mutation tests for verdict mapping and convergence gates.
117. Add canary rollout: shadow mode, then read-only apply, then write mode.
118. Add rollback protocol for parity regressions.
119. Add monthly drift audit against upstream Claude command files.
120. Add release gate requiring eval pass thresholds before default enablement.

## 5) Metaprompting packs for adversarial lensing

### Lens pack A — Runtime realism breaker

Mission:
- Assume every non-deterministic step will fail in production.
- Identify where Codex feature mismatch causes hidden no-op behavior.

Attack questions:
- Which step depends on Claude-only semantics not guaranteed in Codex?
- Which fallback silently changes pipeline meaning?
- What artifacts become unverifiable when multi-agent is disabled?

### Lens pack B — Complexity minimizer and failure economics

Mission:
- Minimize moving parts while preserving parity semantics.
- Cut features that do not improve measurable parity outcomes.

Attack questions:
- Which 20% of components produce 80% of parity value?
- Where is orchestration overhead larger than benefit?
- Which abstractions hide bugs instead of reducing risk?

## 6) 60-day execution phasing

### Phase 1 (Days 1-10) — Prove execution substrate

1. Implement runtime adapter skeleton, reference compiler, self-ref guard.
2. Implement capability probe + fallback matrix.
3. Ship minimal single-agent deterministic improve-phase (no adversarial pass).

### Phase 2 (Days 11-25) — Restore core MSD mechanisms

1. Implement area split + metaprompt generation + parallel improvement runs.
2. Implement merge engine + invariant checks + pipeline status compute.
3. Implement adversarial pass with two lenses + deterministic verdict apply.

### Phase 3 (Days 26-40) — Convergence and routing parity

1. Implement convergence classification and thresholds.
2. Implement resolve-blockers/implement/plan-phase routing parity.
3. Add resume and crash-recovery contracts.

### Phase 4 (Days 41-60) — Harden and ship

1. Add eval corpus and parity score gates.
2. Run shadow mode on active phases.
3. Promote to write-enabled default after gate thresholds pass.

## 7) Hard acceptance gates

1. Behavioral parity score >= 0.98 on golden runs.
2. Zero unresolved self-reference / include-cycle failures.
3. Deterministic state transitions for all seven adversarial verdict types.
4. Convergence gate routing validated across pass bands (1-2, 3-5, 6+).
5. Recovery from interrupted review stage preserves pending semantics.
6. No hidden no-op fallbacks for unsupported features.

## 8) Immediate next actions

1. Fix/replace unresolved `msd-adversarial-reviewer` canonical definition before parity testing.
2. Implement include compiler + cycle guard to make wrappers trustworthy.
3. Build `msd-runner improve-phase` MVP in read-only mode with full artifact logging.
4. Run first parity shadow test on phase `3.1c` and produce mismatch report.

## 9) Adversarial challenge results (Round 2)

### Lens A — Runtime parity breaker (high risk findings integrated)

1. Multi-agent cannot be assumed available in Codex; runtime must probe and branch.
2. `Skill(...)` auto-chaining is not a native Codex primitive; requires dispatcher contract.
3. `AskUserQuestion` convergence choice must have deterministic non-interactive alternative.
4. Hook/worktree semantics are non-equivalent; policy wrapper must be explicit.
5. Self-referential `@` includes can make agent definitions non-materialized.
6. `gsd-tools.cjs` dependency must be preflighted; state persistence cannot be assumed.
7. Auto-mode cannot proceed with hidden degradation paths.

### Lens B — Complexity minimizer (scope compression integrated)

1. Preserve canonical step semantics first (Steps 1-17), defer non-essential architecture.
2. Prioritize smallest viable parity kernel before full observability/governance overlays.
3. Keep rollout in shadow/read-only until deterministic parity signals are demonstrated.

## 10) Canonical parity anchor (must mirror Claude behavior)

Behavioral equivalence target is the canonical flow in:
`~/.claude/my-shit-done/commands/msd/improve-phase.md`

Minimum parity kernel (non-negotiable):
1. Init + phase directory resolution + CONTEXT structural validation.
2. Artifact discovery (PLAN/RESEARCH) + pass detection + digest-first prior context loading.
3. Logical area split + per-area metaprompt briefing.
4. Improvement generation (parallel when available; deterministic sequential fallback otherwise).
5. Merge + renumber + dedupe + pipeline status computation.
6. Adversarial skip logic + dynamic lenses + reviewer verdict application (7 verdict mapping).
7. Pending-review recovery semantics + post-review synthesis.
8. Prerequisite invariant auto-fix + prerequisite summary.
9. Summary + convergence gate + route selection.
10. Auto-chain and state/commit recording with explicit failure checks.

## 11) New hard preflight gates (required before `--auto`)

1. `GATE-MA-01` Multi-agent capability probe:
   - Check Codex multi-agent feature enabled.
   - If disabled, force sequential mode; if sequential path unavailable, fail closed.
2. `GATE-REF-02` Reference integrity probe:
   - Resolve all `@` includes with cycle detection.
   - Fail on self-reference (current blocker: `~/.claude/my-shit-done/agents/msd-adversarial-reviewer.md`).
3. `GATE-INT-03` Interactive/Non-interactive branch policy:
   - If `AskUserQuestion` unavailable, require `--converge-choice` explicit default.
4. `GATE-STATE-04` State persistence probe:
   - Verify `node ~/.claude/get-shit-done/bin/gsd-tools.cjs` executes required commands.
   - If unavailable, disable write-mode and run shadow-only.
5. `GATE-POL-05` Policy wrapper probe:
   - Verify command allowlist/denylist and cleanup policies are active.
6. `GATE-ART-06` Artifact integrity probe:
   - Verify temp-file cleanup + reviewer completeness + unresolved-open item checks.
7. `GATE-NOOP-07` No hidden degradation:
   - Any fallback that changes semantics must log severity + block auto-route.

## 12) False-equivalence traps (explicitly forbidden)

1. Treating Claude `Task(...)` as guaranteed equivalent to Codex multi-agent.
2. Treating Claude `Skill(...)` calls as native Codex skill-to-skill dispatch.
3. Treating AskUser flows as always available in automation contexts.
4. Treating Claude hook lifecycle as 1:1 with Codex policies/automations.
5. Treating wrapper `@` references as safe without include compilation/cycle checks.

## 13) Prioritized cutline over the 120-item backlog

### P0 (must ship first; blocks parity)

1. B12 capability probe + fallback matrix.
2. C22-C24 include compiler + cycle/self-reference guards.
3. E50 forced sequential path.
4. F55-F59 verdict application + invariant checks + pipeline recompute.
5. G61-G66 convergence/routing engine with deterministic branch policy.
6. H71-H74 policy wrapper + worktree lifecycle logging.
7. K101-K103 `codex exec --json` orchestration + parser.
8. L111-L112 minimal golden transcript + step behavioral evaluator.

### P1 (stabilization)

1. D31-D40 prompt schema/serializer/regression tests.
2. E41-E49 orchestration hardening (timeouts, salvage, budgets).
3. G67-G70 stale-item warnings + override matrix + session record parity.
4. I81-I86 artifact schema + run manifest + structured warnings.
5. L114-L117 anti-fabrication + chaos + mutation + canary rollout.

### P2 (defer until parity stable)

1. Track A documentation governance overlays.
2. Heavy observability extras (I87-I90).
3. Topology polish and metadata normalization extras (J94-J100).
4. CI/PR bot and cloud automation extras (K106-K110).

## 14) Updated execution roadmap (compressed and measurable)

### Days 1-10 (Kernel-1)

1. Implement preflight gates `GATE-MA-01`..`GATE-REF-02`..`GATE-INT-03`.
2. Implement deterministic Steps 1-9 in read-only shadow mode.
3. Gate: produce valid `IMPROVEMENT-P{N}.md` for phase `3.1c` with pipeline section and clean temp artifacts.

### Days 11-20 (Kernel-2)

1. Implement Steps 10-13 (skip logic, lensing, verdict apply, synthesis, prereq invariant).
2. Gate: >3-item pass shows lens table, reviewer verdict mapping, synthesis output, and no orphan pending-review items.

### Days 21-30 (Kernel-3)

1. Implement Steps 14-17 (summary, convergence, routing, commit/state updates).
2. Add `--converge-choice` non-interactive policy.
3. Gate: deterministic routing output for `--auto` and interactive modes on replay.

### Days 31-45 (Stabilize)

1. Add policy wrapper/worktree manager and hard failure checks.
2. Add minimal behavior-eval corpus and parity scorer.
3. Gate: pass-rate >=95% across kernel scenarios; no hidden no-op fallbacks.

### Days 46-60 (Harden)

1. Add chaos tests (missing reviewer output, malformed item, ref cycle).
2. Run shadow mode across active phases and publish mismatch report.
3. Gate: behavioral parity >=0.98 and all hard gates green before default auto enablement.

## 15) Immediate blocking fix before any parity claim

1. Replace or repair canonical adversarial reviewer source currently self-referential:
   - `~/.claude/my-shit-done/agents/msd-adversarial-reviewer.md`
2. Until fixed, enforce `GATE-REF-02` failure in auto mode and run with explicit manual-review fallback only.


## 16) Latest-month (Jan-Feb 2026) source-backed deltas for Claude->Codex skill engineering

### A) Claude Code capability deltas that affect MSD parity

1. 2026-02-20: Claude Code `v2.1.50` adds `WorktreeCreate`/`WorktreeRemove` hooks and `isolation: worktree` for agents.
   - Implication: canonical MSD assumptions around worktree lifecycle are now stronger in Claude than in older Codex wrappers; Codex parity must emulate lifecycle logging explicitly.
2. 2026-02 (docs): Agent Teams remain experimental and disabled by default.
   - Implication: parity implementation must never assume team/multi-agent always available.
3. 2026-02 (docs): Skills and commands are merged semantics in Claude.
   - Implication: Codex wrappers that only include canonical markdown need explicit dispatch semantics to match chaining behavior.

### B) Codex capability deltas that affect MSD parity

1. 2026-02 (docs): Codex multi-agent is experimental and requires explicit feature enablement (`[features] multi_agent = true` / `/experimental`).
   - Implication: preflight capability gating is mandatory for improvement/adversarial parallel stages.
2. 2026-02 (docs): Codex skills use progressive disclosure; explicit invocation via `$` or `/skills` pathing.
   - Implication: keep skill descriptions precise and avoid giant always-loaded instruction bundles.
3. 2026-02 (docs): AGENTS.md is layered/merged by directory precedence.
   - Implication: parity runner must prevent accidental instruction overrides from deeper paths.
4. 2026-02 (docs): `codex exec` non-interactive mode is first-class for pipelines.
   - Implication: route auto-chain and parity replay through `codex exec --json` as canonical automation surface.
5. 2026-02 (docs): Config profiles are experimental.
   - Implication: treat profile-dependent behavior as non-critical; keep parity logic feature-flag aware.

### C) Metaprompting/template engineering implications

1. Prompt schema normalization must become a hard dependency for adversarial lensing in Codex because multi-agent and fallback branching add entropy.
2. Template compilation (`@` include resolution + cycle guard) is required before runtime to avoid recursive agent definitions.
3. Non-interactive branch policies must be first-class prompt variables (`--converge-choice`) rather than implicit UI decisions.
4. Subagent outputs must be validated structurally before merge (missing output detection + unresolved-open checks).

