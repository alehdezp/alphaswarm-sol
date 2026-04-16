# Phase 7: Documentation Honesty + Hooks

## Goal

Make docs strictly truthful and enforce graph-first/evidence-first behavior through runtime hooks and schema gates.

## Why This Phase Exists

Documentation and guardrails can drift from implementation. This phase closes that gap with test-backed hook enforcement and claim auditing.

## Critical Gaps to Close

1. Hook enforcement for graph-first is not fully wired in current runtime settings.
2. Evidence completeness checks do not consistently block incomplete outputs.
3. Docs and skill claims still risk overstating what is proven.
4. Graph-usage metrics are documented but inconsistently produced in reports.

## Dependencies

- Phase 3.1 and 3.2 produce stable workflow signals.
- Phase 4 provides debate artifacts for evidence-policy validation.
- Phase 6 adds live test harness that can validate hooks and docs claims.
- Core hook enforcement begins earlier (Phase 3.x); Phase 7 hardens and audits enforcement quality.
- Phase 5 benchmark publication is blocked until Phase 7 hook/schema gates pass.

## Key Files

- `.claude/settings.json`
- `.claude/settings.yaml`
- `docs/PHILOSOPHY.md`
- `docs/reference/graph-first-template.md`
- `docs/reference/claude-code-orchestration.md`
- `docs/guides/testing-advanced.md`
- `src/alphaswarm_sol/skills/guardrails.py`
- `src/alphaswarm_sol/orchestration/handlers.py`

## Plans (Reordered, Test-First)

### 7-01: Create Hook Test Harness First

- Add tests for pre-tool graph-first gating and task-completion evidence checks.
- Add tests for audit-mode toggling and fail-open/fail-closed policy behavior.

#### Reasoning

The hook test harness must exist before any hook implementation code is written, because untested hooks default to fail-open in practice -- the most dangerous state for an anti-vanity gate. Writing both BLOCKING and ALLOWING tests for each of the 6 hooks (PreToolUse, PostToolUse, Stop, SubagentStop, plus audit-mode on/off variants) ensures that a broken hook is caught immediately rather than silently permitting unbacked findings. This is the test-first foundation that makes all subsequent Phase 7 work trustworthy.

#### Expected Outputs

- `tests/hooks/test_pretool_graph_gate.py` -- BLOCKING test (rejects tool call without prior graph query) and ALLOWING test (passes when graph query precedes tool call)
- `tests/hooks/test_posttool_evidence_check.py` -- BLOCKING test (rejects output missing evidence fields) and ALLOWING test (passes with complete evidence)
- `tests/hooks/test_stop_marker_chain.py` -- BLOCKING test (rejects stop without required marker chain) and ALLOWING test (passes with full marker chain)
- `tests/hooks/test_subagent_stop.py` -- BLOCKING test (rejects subagent stop without verdict) and ALLOWING test (passes with verdict + evidence)
- `tests/hooks/test_audit_mode_toggle.py` -- Tests that audit-mode ON enables strict fail-closed and audit-mode OFF uses normal policy
- `tests/hooks/test_fail_policy.py` -- Confirms fail-closed is default; fail-open requires explicit opt-in flag
- Hook test fixture in `tests/conftest.py` providing mock hook event payloads for all 6 hook types
- CI job in `.github/workflows/` that runs hook tests on every PR

#### Testing Strategy

| Output | Method 1 | Method 2 |
|--------|----------|----------|
| PreToolUse gate test | pytest: inject tool-call event without graph query, assert exit code != 0 | Workflow harness: scenario DSL fires PreToolUse, capture verifies BLOCK |
| PostToolUse evidence test | pytest: inject output missing `graph_nodes`, assert rejection | JSON Schema validation against `schemas/secure_reviewer_output.json` |
| Stop marker chain test | pytest: inject stop event with incomplete marker list, assert BLOCK | Transcript validator: check `required_markers_present == false` triggers fail |
| SubagentStop verdict test | pytest: inject subagent stop without verdict field, assert BLOCK | Evidence pack builder: `EvidencePackBuilder.validate()` returns `False` |
| Audit-mode toggle test | pytest: parameterized test with mode ON/OFF, assert policy switch | Integration test in `jj` workspace with `.claude/settings.json` toggle |
| Fail-closed default test | pytest: no config provided, assert default behavior is BLOCK | Grep `.claude/hooks/` scripts for `except Exception: pass` -- must find zero matches |

#### Drift Detection

| Expected Behavior | Bypass Indicators | Enforcement |
|-------------------|-------------------|-------------|
| Every hook has both BLOCK and ALLOW tests | Test file has only `test_allow_*` functions, no `test_block_*` | CI lint: count BLOCK vs ALLOW tests per hook, fail if ratio < 1:1 |
| Fail-closed is the default policy | Hook script contains `except Exception: pass` or `except Exception: sys.exit(0)` | Grep-based CI check: zero tolerance for silent exception swallowing in hook scripts |
| Tests use real hook event payloads | Tests mock the entire hook dispatcher instead of just the event | conftest fixtures provide event payloads, not dispatcher mocks |
| All 6 hook types are covered | Test directory has fewer than 6 test files | CI gate: `ls tests/hooks/test_*.py | wc -l` must be >= 6 |

### 7-02: Implement and Wire Hooks

- Implement `.claude/hooks` scripts with deterministic command hooks.
- Wire hooks in settings and validate with integration tests.

#### Reasoning

With the test harness from 7-01 already enforcing BLOCK/ALLOW expectations, hook implementation becomes a fill-in-the-tests exercise rather than speculative coding. Each hook script in `.claude/hooks/` must be a deterministic shell or Python script that reads the hook event from stdin, applies a policy check, and exits non-zero to block or zero to allow. Wiring these in `.claude/settings.json` under the `hooks` key makes them active for every Claude Code session, which is the prerequisite for Phase 5 benchmark integrity.

#### Expected Outputs

- `.claude/hooks/pre_tool_use.py` -- Reads tool call event, checks graph-query-before-code-read policy, exits 1 to block
- `.claude/hooks/post_tool_use.py` -- Reads tool output, validates evidence fields present, exits 1 if missing
- `.claude/hooks/stop.py` -- Reads stop event, validates required marker chain completeness, exits 1 if incomplete
- `.claude/hooks/subagent_stop.py` -- Reads subagent stop event, validates verdict + evidence attachment, exits 1 if missing
- Updated `.claude/settings.json` with `hooks` section referencing all 4 scripts
- Integration test `tests/hooks/test_hooks_integration.py` proving hooks fire in a real (non-mocked) agent session using `jj` workspace isolation
- `.vrs/debug/phase-7/hook-fire-log.jsonl` -- Append-only log written by each hook script recording every invocation for audit

#### Testing Strategy

| Output | Method 1 | Method 2 |
|--------|----------|----------|
| `pre_tool_use.py` correctness | Run 7-01 BLOCK/ALLOW tests -- all must pass | Manual: `echo '{"tool":"Read","args":{}}' | python .claude/hooks/pre_tool_use.py; echo $?` returns 1 |
| `post_tool_use.py` correctness | Run 7-01 PostToolUse tests -- all must pass | Feed output missing `graph_nodes` via stdin, confirm exit 1 |
| `stop.py` correctness | Run 7-01 Stop tests -- all must pass | Feed stop event with empty `marker_list`, confirm exit 1 |
| `subagent_stop.py` correctness | Run 7-01 SubagentStop tests -- all must pass | Feed event without `verdict` key, confirm exit 1 |
| Settings wiring | `jq '.hooks' .claude/settings.json` returns all 4 hook paths | Integration test spawns agent, triggers tool call, confirms hook log entry in `hook-fire-log.jsonl` |
| Hook fire in real session | Workflow harness scenario with capture: hook log has >= 1 entry per hook type | `jj` workspace: run `/vrs-audit` on test contract, inspect hook-fire-log for all 4 types |

#### Drift Detection

| Expected Behavior | Bypass Indicators | Enforcement |
|-------------------|-------------------|-------------|
| Hooks block on policy violation (exit 1) | Hook contains `except Exception: sys.exit(0)` -- silently allows on error | CI grep: zero matches for `sys.exit(0)` in any `except` block within `.claude/hooks/` |
| Hooks log every invocation | Hook script has no write to `hook-fire-log.jsonl` | CI check: each hook script contains `hook-fire-log` write path |
| Hooks are wired in settings.json | `hooks` key missing or references non-existent paths | CI: `jq '.hooks'` must return 4 entries; each path must `test -f` |
| Hooks are deterministic (no LLM calls) | Hook script imports `anthropic` or calls any API | CI grep: zero matches for `anthropic`, `openai`, `requests.post` in hook scripts |

### 7-03: Add Evidence Schema Gates

- Enforce required fields in evidence packs and report artifacts.
- Add failing tests for missing graph IDs/code locations/operation traces.
- Missing proof-token fields or missing marker chain must hard-fail.

#### Reasoning

Evidence schema gates are the structural enforcement layer that prevents findings without graph backing from reaching any report or benchmark. The existing `schemas/secure_reviewer_output.json` already requires `graph_queries` and `evidence` as top-level fields, and `schemas/testing/evidence_manifest.schema.json` requires `required_markers_present` and `marker_list`. This plan hardens those schemas by making `graph_nodes` required (not optional) for confirmed/likely findings and adding `proof_token` chain validation to the evidence pack manifest. Without these gates, Phase 5 benchmarks could report detection rates based on findings that never touched the graph.

#### Expected Outputs

- Updated `schemas/secure_reviewer_output.json` -- `graph_node_id` or `code_location` required (not optional) for evidence items with confidence >= `medium`
- Updated `schemas/testing/evidence_manifest.schema.json` -- `proof_tokens` array required, each entry must have `stage`, `nonce`, `transcript_hash`
- New `schemas/finding_output.json` -- Schema for individual findings requiring `graph_nodes: []` (minItems: 1) for severity >= MEDIUM
- `tests/schemas/test_evidence_schema_gates.py` -- Parameterized tests: valid payloads pass, payloads missing `graph_nodes`/`proof_tokens`/`marker_list` hard-fail
- `tests/schemas/test_finding_schema.py` -- Confirmed finding without graph_nodes fails; informational finding without graph_nodes passes
- `src/alphaswarm_sol/testing/schema_validator.py` -- Thin wrapper: `validate_finding(payload) -> (bool, list[str])` using jsonschema against the schemas
- CI integration: schema validation runs on every evidence pack produced by any test

#### Testing Strategy

| Output | Method 1 | Method 2 |
|--------|----------|----------|
| `graph_nodes` required for confirmed findings | pytest: submit finding with severity=HIGH and empty `graph_nodes`, assert validation fails | jsonschema CLI: `jsonschema -i bad_finding.json schemas/finding_output.json` exits 1 |
| `proof_tokens` required in manifest | pytest: submit manifest without `proof_tokens`, assert validation fails | `EvidencePackBuilder.build()` raises when no proof tokens added |
| `marker_list` completeness | pytest: submit manifest with `required_markers_present: false`, assert hard-fail | Transcript validator rejects manifest where marker count < expected |
| Informational findings exempt from graph_nodes | pytest: submit informational finding with empty `graph_nodes`, assert validation passes | Schema allows `minItems: 0` when severity is INFORMATIONAL or LOW |
| Schema validator wrapper | pytest: `validate_finding()` returns `(False, ["missing graph_nodes"])` for bad input | `validate_finding()` returns `(True, [])` for complete input |
| CI enforcement | `.github/workflows/` job runs schema validation on all `.vrs/` output artifacts | Pre-merge check: any new evidence pack in PR must pass schema validation |

#### Drift Detection

| Expected Behavior | Bypass Indicators | Enforcement |
|-------------------|-------------------|-------------|
| `graph_nodes` is required for severity >= MEDIUM | Schema has `graph_nodes` as optional or missing `minItems` | CI: parse schema JSON, assert `graph_nodes` has `minItems: 1` in confirmed/likely branch |
| Proof-token chain is validated end-to-end | `ProofTokenCollector.complete_stage()` skips `transcript_hash` check | Unit test: provide mismatched transcript, assert `token.validate()` returns errors |
| Validators FAIL (not warn) on missing fields | Validator function returns `(True, warnings)` instead of `(False, errors)` | Test asserts return value is `(False, ...)` not `(True, ...)` for known-bad inputs |
| Schema changes are backwards-compatible only in the strict direction | New schema version removes a required field | CI diff check: required field count in new schema >= required field count in previous |

### 7-04: Docs Honesty Sweep

- Convert claims into `working`, `experimental`, or `planned` tags.
- Remove or downgrade claims without supporting artifacts.
- Add scoring-policy documentation for LLM-judge consistency and bias controls.

#### Reasoning

The codebase documentation currently contains claims that range from accurately describing working functionality to aspirationally describing planned features as if they exist. The 17 false claims identified in CLAUDE.md (and similar issues across PHILOSOPHY.md, skill descriptions, and architecture docs) erode trust and create confusion about what actually works. This sweep applies a strict evidence standard: every claim gets tagged `working` (demonstrated with artifact), `experimental` (code exists, not validated), or `planned` (design only), and claims without any supporting artifact are either downgraded or removed. This must happen before Phase 5 benchmarks so that benchmark results are not conflated with aspirational documentation.

#### Expected Outputs

- Updated `CLAUDE.md` with all 17 identified false claims addressed: each tagged, downgraded, or removed with a changelog entry
- Updated `docs/PHILOSOPHY.md` with claim tags on every capability statement
- Updated `docs/reference/claude-code-orchestration.md` with status tags on each orchestration feature
- Updated skill descriptions in `src/alphaswarm_sol/shipping/skills/` with `status:` field per capability claim
- New `docs/reference/claim-evidence-index.md` -- Table mapping every `working` claim to its supporting artifact (test, demo transcript, or CI output)
- New `docs/reference/scoring-policy.md` -- LLM-judge scoring rubric, bias controls, calibration set requirements
- `.vrs/debug/phase-7/honesty-sweep-changelog.md` -- Log of every claim change with before/after and rationale

#### Testing Strategy

| Output | Method 1 | Method 2 |
|--------|----------|----------|
| All claims tagged | Grep all docs for capability statements, verify each has `[working]`/`[experimental]`/`[planned]` | `vrs-docs-curator` subagent reviews each tagged claim against artifact existence |
| False claims addressed | Diff `CLAUDE.md` before/after, verify all 17 items changed | Changelog has exactly >= 17 entries with before/after |
| `working` claims have artifacts | For each `[working]` tag, `claim-evidence-index.md` references a real file that exists | CI: parse index, `test -f` each referenced artifact path |
| No aspirational language unmarked | Grep for phrases like "enables", "provides", "supports" without adjacent tag | `vrs-secure-reviewer` scans docs for untagged capability claims |
| Scoring policy is actionable | Scoring rubric has concrete numeric thresholds (not "good"/"bad") | Calibration set exists with >= 10 pre-scored examples |
| Changelog is complete | Changelog has entry for every modified file | `git diff --name-only` for docs matches changelog file list |

#### Drift Detection

| Expected Behavior | Bypass Indicators | Enforcement |
|-------------------|-------------------|-------------|
| Every capability claim has a status tag | New docs added without `[working]`/`[experimental]`/`[planned]` tags | CI: grep docs for untagged capability verbs, fail if count > 0 |
| `[working]` tag requires artifact proof | `claim-evidence-index.md` references files that don't exist or are empty | CI: parse index, verify each path exists and has > 0 bytes |
| Sections are corrected, not deleted wholesale | Large doc sections disappear without replacement | CI: compare line counts before/after; flag if any doc shrinks by > 40% without corresponding growth elsewhere |
| Scoring policy has calibration set | `scoring-policy.md` references calibration examples that don't exist | CI: parse scoring policy, verify calibration set path exists with >= 10 entries |

### 7-05: Skill/Registry Consistency Pass

- Align shipped skills, registry status, and docs references.
- Remove dead references and obsolete legacy assumptions from production claims.

#### Reasoning

The skill registry (`src/alphaswarm_sol/skills/registry.yaml`) lists 47 skills with `status: active`, but the actual shipped skills in `src/alphaswarm_sol/shipping/skills/` and their symlinks in `.claude/skills/` may not match. Dead references -- skills marked active that have no corresponding file, or shipped skills not in the registry -- create false confidence about what the product can actually do. Legacy assumptions (session labels, pane IDs in evidence schemas) also need to be reconciled with the current Agent Teams + claude-code-controller (npm v0.6.1) model. This pass ensures that `registry.yaml`, the filesystem, and documentation are in strict agreement.

#### Expected Outputs

- Updated `src/alphaswarm_sol/skills/registry.yaml` -- Every entry with `status: active` has a corresponding file at its `location.shipped` or `location.dev` path
- Removed or marked `status: deprecated` for any skill whose file does not exist
- Updated `CLAUDE.md` skill table to match registry (no skills listed that are not in registry with `active` status)
- Removed legacy-specific fields from `schemas/testing/evidence_manifest.schema.json` or marked them as legacy-optional with migration path
- Updated `src/alphaswarm_sol/shipping/skills/` -- Dead symlinks removed, all remaining symlinks resolve
- `.vrs/debug/phase-7/registry-audit.json` -- Machine-readable audit: `{skill_id, registry_status, file_exists, symlink_resolves, docs_referenced}`
- CI job: registry consistency check runs on every PR that modifies skills or registry

#### Testing Strategy

| Output | Method 1 | Method 2 |
|--------|----------|----------|
| Registry-filesystem alignment | pytest: parse `registry.yaml`, for each `active` skill, assert file at `location` path exists | CI script: `for f in $(yq '.skills[].location.shipped' registry.yaml); do test -f "$f"; done` |
| Dead symlinks removed | `find .claude/skills/ -type l ! -exec test -e {} \; -print` returns empty | pytest: `Path.resolve()` on each symlink, assert target exists |
| CLAUDE.md matches registry | pytest: parse CLAUDE.md skill table, compare against registry `active` entries, assert exact match | Diff: extract skill names from both, assert symmetric difference is empty |
| Legacy fields reconciled | Schema validation: manifest without `pane_id`/`session_label` passes if using hooks model | pytest: submit hook-based manifest without legacy fields, assert validation passes |
| Registry audit artifact | `registry-audit.json` exists and has entry for every skill in registry | pytest: parse audit JSON, assert length equals registry skill count |
| No non-functional skills marked shipped | For each `shipped` skill, invoke its help/validation command and assert success | Integration test: `uv run alphaswarm skills validate --shipped-only` exits 0 |

#### Drift Detection

| Expected Behavior | Bypass Indicators | Enforcement |
|-------------------|-------------------|-------------|
| Registry matches filesystem | New skill file added without registry entry, or registry entry added without file | CI: bidirectional check -- files without registry entries AND registry entries without files both fail |
| Dead symlinks are removed, not hidden | Symlink target changed to `/dev/null` or empty file | CI: each symlink target has > 0 bytes of content |
| Deprecated skills are not silently re-activated | `status: deprecated` changed to `status: active` without new file | CI: git diff on registry checks that `deprecated -> active` transitions include file creation in same PR |
| Legacy assumptions don't leak into new code | New test or schema references `session_id` or `pane_id` without legacy guard | CI grep: new files (not in legacy paths) containing `session_id` or `pane_id` must be zero |

## Hard Delivery Protocol Hardening (Added 2026-02-10)

Phase 7 turns earlier debate-era uncertainty and policy decisions into enforceable production contracts.

### HDG-09 Hardening: Uncertainty Protocol + Reason Codes (Primary owner: 7-03)

**Why this is critical**
- "Needs human review" is only useful when it is deterministic and reason-coded.
- Without reason codes, uncertainty becomes a vague escape hatch that cannot be triaged or audited.

**Implementation contract**
- Extend finding/report schemas with:
  - `human_review_required` (bool)
  - `reason_codes` (enum array, minItems: 1 when review required)
  - `blocked_actions` (array of `{tool, reason_code, timestamp}`)
- Enforce reason-code taxonomy in `schemas/` and `schema_validator.py`.
- Add docs contract in `docs/reference/scoring-policy.md` mapping each reason code to operator action.

**Hard validation**
- Any finding marked `human_review_required=true` without `reason_codes` fails schema.
- Any `confirmed` finding with unresolved reason code (e.g., `VERIFIER_DISAGREEMENT`) fails schema.
- Hook logs and finding artifacts must agree on reason codes for blocked actions.

**Expected strict result**
- Uncertainty is actionable, machine-readable, and auditable across runs.

### HDG-06 Hardening: Permission Denial Provenance (Primary owner: 7-02)

**Why this is critical**
- Blocking is not enough; the system must prove what was blocked and why.
- Auditors need denial provenance to distinguish malicious prompts from policy misconfiguration.

**Implementation contract**
- Standardize hook-denial record shape:
  - `event_id`, `session_id`, `agent_role`, `tool_name`, `reason_code`, `policy_rule_id`, `artifact_ref`
- Persist append-only denial logs at `.vrs/debug/phase-7/policy-denials.jsonl`.
- Cross-link denial records to scenario/test IDs from Phase 4.1 permission abuse drills.

**Hard validation**
- Every blocked call must have a policy rule ID and reason code.
- Any blocked call without persisted denial provenance fails hook integration tests.
- Denial logs must be append-only (hash chain or monotonic record ID).

**Expected strict result**
- Policy enforcement gains forensic-grade traceability, not just pass/fail outcomes.

## Interactive Validation Method (Agent Teams + JJ Workspace)

- Hook validation runs execute in isolated `jj` workspaces.
- Use `vrs-secure-reviewer` + `vrs-verifier` to audit claim-evidence consistency.
- Include teammate idleness and premature-stop checks for team sessions.

## Non-Vanity Metrics

- Graph-first compliance rate from hook logs.
- Evidence completeness pass rate.
- Docs claim coverage ratio (claims with proof artifact / total claims).
- Task lifecycle marker compliance rate.
- Judge consistency and false-accept rate on calibration sets.

## Recommended Subagents

- `vrs-docs-curator`
- `vrs-test-conductor`
- `vrs-integrator`
- `vrs-secure-reviewer`
- `vrs-verifier`

## Exit Gate

Hooks are active and fail-closed, docs are evidence-backed, runtime behavior matches published workflow claims, HDG-09/HDG-06 hardening gates pass, and benchmark publication is unblocked only after these checks pass.

## Research Inputs

- `.planning/new-milestone/reports/w2-docs-hooks-plan.md`
- `docs/reference/claude-code-orchestration.md`
- `docs/reference/graph-first-template.md`
- External: LLM-as-judge bias and consistency guidance (late 2025 to early 2026)

## 2026-02-09 Reordering Audit Context

### Global Sequence

Execution order after Phase 2.1 is now fixed:
`3.1 -> 3.1b -> 3.2 -> 4 -> 4.1 -> 6 -> 7 -> 5 -> 8`

### Iteration Notes (1 -> 3)

1. Iteration 1: hooks/docs phase was useful but not treated as a benchmark blocker.
2. Iteration 2: enforcement-first ordering was adopted (hooks and schema before claims).
3. Iteration 3: strict review moved benchmark execution after this phase to prevent vanity metrics.

### This Phase's Role

Phase 7 is the anti-vanity gate: it enforces fail-closed behavior and claim-evidence consistency before any benchmark results can be published.

### Mandatory Carry-Forward Gates

- Graph-first hook compliance.
- Evidence schema and proof-token completeness hard-fail.
- Required orchestration marker chain checks.
- Claim-to-artifact linkage in docs and skill descriptions.
- Uncertainty protocol reason-code enforcement for all `needs-human-review` findings.
- Permission denial provenance logs with policy rule IDs for all blocked actions.

### Debug/Artifact Contract

- Any gate failure writes `.vrs/debug/phase-7/repro.json`.
- Repro includes failing hook event, schema validator output, and marker coverage output.

### Assigned Research Subagent

- `vrs-docs-curator` for claim-evidence alignment audits

### Research Sources Used

- https://arxiv.org/abs/2601.06112
- https://arxiv.org/abs/2510.07614
