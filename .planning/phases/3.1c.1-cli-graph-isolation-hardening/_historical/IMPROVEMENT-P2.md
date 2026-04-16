# Improvement Pass 2

**Date:** 2026-03-01
**Phase:** 3.1c.1
**Status:** complete

## Pipeline Status

| Stage | Pending | Done | Blockers |
|-------|---------|------|----------|
| Prerequisites | 0 | 0 | — |
| Research | 0 | 1 | — |
| ADV validation | 0 | 5 | — |
| Merge-ready | 22 | 0 | — |

**Pipeline:** [discuss] ✓ → [improve] ✓ → [pre-impl] ✓ → [research] ✓ → [implement] ~ → [plan] ✓ → [execute] —
**Next:** /msd:implement-improvements 3.1c.1 — 22 merge-ready

| Status | Count | Items |
|--------|-------|-------|
| confirmed | 8 | IMP-02, 03, 07, 09, 10, 12, 15, 16 |
| enhanced | 13 | IMP-01, 04, 08, 11, 13, 14, 17, 19, SYN-01, CSC-01, CSC-02, CSC-03, CSC-04 |
| researched | 1 | IMP-06 |
| rejected | 2 | IMP-05, 18 |

## Adversarial Lenses

| Lens | Brief | Items | Attack Vector |
|------|-------|-------|---------------|
| Resolution & Packaging Determinism | You are the executor reading Plan 01. The resolution module uses `importlib.resources.files()` but the spec doesn't distinguish editable vs wheel installs. For each item: if you encounter this instruction for the first time, what specifically would confuse, block, or mislead you? | IMP-01, 02, 03, 04, 05 | Does the resolution spec survive cross-environment deployment (editable, wheel, conda, zipapp)? |
| Cross-Plan Interface Integrity | You are the executor reading Plans 02-03. Plan 02's GraphStore writes meta.json; Plan 03's query reads it. Neither plan specifies the atomic write contract, exit code semantics, or stdout/stderr channel assignment. For each item: what interface assumption would you make that the other plan contradicts? | IMP-06, 07, 08, 09, 10, 11, 12, 13 | Do Plan 02's write contracts and Plan 03's read contracts agree on schema, atomicity, and I/O channels? |
| Testing Criteria Falsifiability | You are the executor reading Plan 04's smoke tests. The concurrent build test says "all agents pass CLI confirmation" — but CLI confirmation can't distinguish correct-graph from wrong-graph queries. For each item: would this test catch the specific Batch 1 failure it claims to target? | IMP-14, 15, 16, 17, 18, 19 | Do the smoke test criteria actually falsify the failure modes they target, or do they test presence without testing correctness? |

## Improvements

### P2-IMP-01: Read/Write Path Divergence After Partial Upgrade Is Not Detectable At Runtime
**Target:** CONTEXT (PLAN-01 spec)
**What:** Add a VulndocsPathConflict guard that detects when BOTH a package-installed vulndocs tree AND an editable-install vulndocs tree exist simultaneously in the same environment and both contain YAML files, producing a startup error rather than silent wrong-results.
**Why:** `uv tool install` into an existing editable venv can install a wheel alongside the editable source tree, giving two populated vulndocs roots. importlib.resources.files() will resolve to whichever one Python's import machinery finds first — the "loser" is silently ignored. A developer updating patterns in the editable source tree will get stale results from the wheel without any indication. This is not a misconfiguration that fails loudly; it fails silently with old data.
**How:**
1. Implement `_assert_single_vulndocs_root()` in the resolution module: compute both `importlib.resources.files(...)` path and `Path(__file__).resolve().parent / "vulndocs"`; if both resolve to existing directories that contain at least one `.yaml` file AND they are not the same path (via `.resolve()`), raise `VulndocsPathConflict` with both paths in the message.
2. Call `_assert_single_vulndocs_root()` once at module import time (not per-call), guarded by an env var `ALPHASWARM_SKIP_VULNDOCS_CONFLICT_CHECK=1` for CI environments that intentionally test both paths.
3. Done criterion: "In a venv with editable install, `pip install dist/*.whl` places a second vulndocs tree; `import alphaswarm_sol.vulndocs` raises `VulndocsPathConflict`."
4. Done criterion: "In a venv with editable install only, no exception raised at import."
**Impacts:** PLAN-01 scope grows slightly (one additional guard + two tests). No impact on Plans 02-05.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — this divergence scenario would be invisible from reading CONTEXT.md alone without reasoning about the interaction between the two resolution modes across different install types. It does not appear in Pass 1 items.

### P2-IMP-02: `importlib.resources.files()` Traversal Breaks for Namespace Packages and Zip Imports
**Target:** CONTEXT (PLAN-01 spec)
**What:** The spec states `vulndocs_read_path()` uses `importlib.resources.files()`. This API returns a `Traversable` object, not a `pathlib.Path`. The critical gap: the spec also states "All downstream vulndocs consumers (category traversal, pattern loaders, sub-path constructions) verified to use absolute paths anchored to the resolved root." But `importlib.resources.files()` returns a `Traversable`, not a real filesystem path. Code that does `Path(vulndocs_read_path()) / "reentrancy"` will fail when the package is loaded from a zip (e.g., zipapp, certain conda packaging, or `PYTHONPATH` pointing at a zip archive) because `Path(Traversable)` requires `__fspath__` which `Traversable` objects from zip backends do not implement.
**Why:** The spec explicitly says "zero bare relative `Path()` constructions outside of `__file__`-anchored roots" — this is addressing the wrong problem. The real risk is `Path(importlib.resources.files(...))` which looks absolute but is not path-safe in zip contexts. Conda packages, zipapp deployments, and some PyInstaller configurations all hit this. The spec needs to either: (a) explicitly require extracting to a temp directory for zip contexts (using `importlib.resources.as_file()`), or (b) require that all traversal of `vulndocs_read_path()` results use the `Traversable` API consistently (`.iterdir()`, `.open()`) never casting to `Path`. Current spec does not distinguish between these.
**How:** 
1. In PLAN-01 spec, add an explicit constraint: "Consumers of `vulndocs_read_path()` MUST NOT cast the result to `pathlib.Path` directly. They must either: (a) use `Traversable` methods (`.iterdir()`, `.open()`, `.joinpath()`), or (b) use `importlib.resources.as_file()` context manager to extract to a real filesystem path for operations that require `os.stat()`, `glob()`, or YAML loading from path." Flag which operations fall into (b).
2. Add a done criterion: run the existing category traversal and pattern loader code with the `vulndocs_read_path()` return value replaced by a `zipimport`-backed `Traversable` mock. If any `Path()` cast or `os.stat()` call surfaces, the criterion fails. This is checkable with a `unittest.mock.patch` on `importlib.resources.files` that returns a custom `Traversable` that raises `TypeError` on `__fspath__`.
**Impacts:** PLAN-01 implementation scope. May require refactoring pattern loaders to use `Traversable` API or wrapping with `as_file()`.
**Research needed:** no — `importlib.resources` Traversable behavior is documented in PEP 451 and Python 3.9+ stdlib docs
**Confidence:** HIGH
**Prior art:** 3 — The Traversable/Path distinction is known; applying it specifically to vulndocs traversal is a composition of standard knowledge
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — Pass 1 noted "zip-safe edge cases for `__file__` resolution" (P1-IMP-05, implemented) but that addressed `__file__`-relative write paths. This is a distinct failure mode on the `importlib.resources` read path where `Traversable` objects are cast to `Path`. These are different code paths with different failure modes.

### P2-IMP-03: `package_data` Declaration Covers Only Top-Level — Nested YAML Subdirectories May Be Excluded
**Target:** CONTEXT (PLAN-01 spec)
**What:** The spec states "`pyproject.toml` includes vulndocs in `package_data` so non-editable `pip install` works." This is correct but underspecified. `package_data` (or `[tool.setuptools.package-data]`) must match recursively. The default `**` glob in setuptools only matches one level deep in some setuptools versions (< 67.x behavior), and `include_package_data = true` without a `MANIFEST.in` does not include data files that are not under version control. If vulndocs has deep nesting (e.g., `vulndocs/reentrancy/patterns/high-confidence/*.yaml`), a `package_data = {"alphaswarm_sol": ["vulndocs/*.yaml"]}` declaration silently omits everything at depth 2+.
**Why:** The failure mode is silent: `pip install` succeeds, `importlib.resources.files("alphaswarm_sol").joinpath("vulndocs")` resolves, but many patterns are simply absent. The agent queries return no results and the operator has no indication whether this is because no vulnerabilities exist or because patterns were not bundled. A correct recursive declaration (`["vulndocs/**/*.yaml", "vulndocs/**/*.json"]`) must be specified explicitly and verified as part of the plan's done criteria.
**How:** 
1. In PLAN-01 spec, replace the vague "includes vulndocs in `package_data`" with a concrete required declaration: `[tool.setuptools.package-data] → {"alphaswarm_sol": ["vulndocs/**"]}` (or equivalent `recursive_include` in MANIFEST.in if using legacy setuptools). Specify that this must use `**` glob, not `*`.
2. Add a done criterion: after building a wheel (`python -m build --wheel`) and installing it into a clean venv, verify that `importlib.resources.files("alphaswarm_sol").joinpath("vulndocs/reentrancy").iterdir()` returns at least one `.yaml` file. This is a disk-observable check, not just a declaration check.
**Impacts:** PLAN-01 done criteria tighten. Potentially catches a packaging bug that would have survived all other verification steps.
**Research needed:** no — setuptools package_data glob semantics are documented
**Confidence:** HIGH
**Prior art:** 4 — standard setuptools packaging pattern; the `**` glob requirement is documented in setuptools docs
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — Pass 1 item P1-IMP-02 addressed "package layout divergence — editable vs installed" but that was about whether vulndocs is in `site-packages` at all, not about whether the glob pattern captures nested subdirectories. These are different failure modes at different layers.

### P2-IMP-04: Spec Does Not Define Behavior When `ALPHASWARM_VULNDOCS_DIR` Points at a Stale or Missing Directory
**Target:** CONTEXT (PLAN-01 spec)
**What:** Define a complete contract for `ALPHASWARM_VULNDOCS_DIR`: what it overrides, when validation fires, what error is raised, and whether missing vs. non-directory vs. empty-directory are distinct failure modes.
**Why:** Current spec mentions the env var only as a write-path override for installed packages. An implementer reading the spec cannot determine: (a) whether it also overrides read paths, (b) whether to validate eagerly or lazily, (c) whether a directory that exists but contains no YAML is valid. Two implementers produce incompatible behavior. A user who sets the var to a path they haven't populated yet gets a different error than one who sets it to a nonexistent path.
**How:**
1. Add a Decision D-1a subsection: "When `ALPHASWARM_VULNDOCS_DIR` is set, it overrides BOTH `vulndocs_read_path()` and `vulndocs_write_path()`. The package-bundled vulndocs are completely bypassed."
2. Specify validation contract: "Validated on first call to either path function. If the path does not exist: raises `VulndocsConfigError('ALPHASWARM_VULNDOCS_DIR={path} does not exist')`. If the path exists but is not a directory: raises `VulndocsConfigError('... is not a directory')`. If the directory exists and is empty of YAML files: logs a WARNING but does not raise — empty override is a valid bootstrap state."
3. Done criterion: "Set `ALPHASWARM_VULNDOCS_DIR=/nonexistent` and call `vulndocs_read_path()` — raises `VulndocsConfigError`."
4. Done criterion: "Set `ALPHASWARM_VULNDOCS_DIR` to an empty directory — no exception, warning emitted."
**Impacts:** PLAN-01 scope (minor: error type + message contract). Aligns with P2-IMP-01's consistency guard (when env var is set, no divergence is possible).
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — The env var fallback was introduced in Pass 1 (P1-CSC-02 / write path separation) but the behavioral contract of the var itself (validation timing, read vs write, error type) was never specified. This is a spec gap in the implementation contract, not a derivative of any prior improvement.

### P2-IMP-05: Spec Assumes `importlib.resources.files()` Is Available — Python 3.8 Compatibility Not Addressed
**Target:** CONTEXT (PLAN-01 spec)
**What:** `importlib.resources.files()` was added in Python 3.9. The spec uses it as the canonical read-path mechanism without stating the minimum Python version required. If the project supports Python 3.8 (common in security tooling targeting older infrastructure), this function does not exist and the implementation fails at import time with `AttributeError: module 'importlib.resources' has no attribute 'files'`. The spec also does not state a fallback for Python 3.8 (the `importlib_resources` backport exists on PyPI).
**Why:** This is a prerequisite gap. The resolution mechanism specified in PLAN-01 is only correct if Python >= 3.9 is guaranteed. If the project's `pyproject.toml` does not enforce `requires-python = ">=3.9"`, the spec is broken for a subset of target environments. The plan must either (a) add `requires-python = ">=3.9"` as a done criterion, or (b) specify the `importlib_resources` backport as a conditional dependency for Python < 3.9, or (c) use `pkg_resources.resource_filename()` as a compat shim (not recommended but widely used).
**How:** 
1. Check whether the project's current `pyproject.toml` specifies `requires-python`. If it specifies `>=3.9`, add this as an explicit assumption in PLAN-01 spec ("Assumes Python >= 3.9 for `importlib.resources.files()`"). If it specifies `>=3.8` or is unset, add a task to either bump `requires-python` to `>=3.9` or add `importlib_resources` backport as a conditional dependency.
2. Add a done criterion: verify `pyproject.toml` has `requires-python = ">=3.9"` (or backport dependency exists). This is a single-line grep check on `pyproject.toml`.
**Impacts:** PLAN-01 prerequisite clarity. May surface a project-wide Python version constraint decision.
**Research needed:** no — Python version compatibility for `importlib.resources.files()` is documented
**Confidence:** MEDIUM — the project may already enforce Python >= 3.9 (Slither and other dependencies likely require it), making this a documentation gap rather than a real gap. But without checking `pyproject.toml`, the spec is underspecified.
**Prior art:** 5 — standard Python compatibility concern
**Prerequisite:** no
**Status:** rejected
**Origin:** NOVEL — Not addressed in Pass 1. Pass 1-IMP-05 addressed zip-safe edge cases for `__file__` resolution but not the Python version floor for `importlib.resources.files()`.
**Rejection reason:** Resolvable by reading pyproject.toml (< 5 min). Codebase uses `match` statements (Python 3.10+), making importlib.resources.files() a non-issue. MEDIUM confidence correctly signaled deducibility. (Lens: Resolution & Packaging Determinism)

### P2-IMP-06: External Dependency Files Break Canonical Identity Across Environments
**Target:** CONTEXT
**What:** Identity hash must exclude machine-local paths. Filter compilation unit to only `.sol` files whose `os.path.realpath()` is prefixed by the project root. Project root is resolved via `git rev-parse --show-toplevel`; fallback is the common ancestor directory of all CLI-specified inputs.
**Why:** Slither resolves imports to virtualenv or npm cache paths. These are machine-local and workspace-local. Without the filter, two agents in different worktrees building the same contract produce different hashes — defeating coordination without triggering cross-contamination. The current spec says "all files in compilation unit" which explicitly includes these machine-local paths.
**How:**
1. In Plan 02, replace "sorted realpaths for multi-file" with: "sorted realpaths of CLI-specified `.sol` inputs only — compiled dependency paths from Slither's source_mapping are excluded from identity."
2. Add `_resolve_project_root(inputs: List[Path]) -> Path` utility: `git rev-parse --show-toplevel` from input[0].parent, fallback to `Path(os.path.commonpath([str(p) for p in inputs]))`.
3. Add assertion in `contract_identity()`: all included paths must be under project root; log a WARNING (not error) for any excluded dependency path.
4. Research task: confirm by running `build-kg` in a fresh virtualenv and inspecting `source_mapping.filename_absolute` for one OpenZeppelin import — verify it resolves to virtualenv path vs project path.
**Impacts:** Affects Plan 02 confidence HIGH → MEDIUM until filter rule confirmed. Plan 03 stem-based lookup indirectly affected.
**Research needed:** no — RESOLVED (GAP-03): Confirmed. `filename_absolute` produces absolute machine-local paths via `os.path.abspath()` in crytic-compile. Dependencies resolved to `node_modules/` or `lib/` paths. Use `source_mapping.is_dependency` flag as primary filter, project-root prefix as fallback.
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Status:** implemented
**research_summary:** Slither's `filename_absolute` IS an absolute machine-local path. crytic-compile resolves imports to their actual filesystem locations (node_modules, lib). The `is_dependency` flag on `source_mapping` provides platform-specific dependency detection. Plan 02 identity hash MUST filter dependencies.
**Origin:** NOVEL — This edge case exists in the original CONTEXT.md spec regardless of Pass 1 improvements. Pass 1 specified realpath normalization (IMP-06) but did not address the project-root filter problem.

### P2-IMP-07: Grep-Zero Done Criterion Misses Dynamic Path Construction
**Target:** CONTEXT
**What:** The done criterion states: "grep for '.vrs/graphs' hardcoded strings returns zero results outside of GraphStore itself." This criterion fails to catch dynamic path construction patterns such as: `base_dir / "graphs" / identity`, `os.path.join(vrs_root, "graphs", contract_id)`, `f"{workspace}/.vrs/graphs/{stem}"`, and config-object-mediated access like `settings.graph_dir / contract_hash`. These patterns contain no string `.vrs/graphs` and pass the grep check while still bypassing GraphStore.
**Why:** If the done criterion passes but callers still bypass GraphStore via dynamic construction, the migration is incomplete. The criterion gives false confidence. In a codebase with ~27,800 LOC across `kg/`, `tools/`, and `orchestration/`, indirect references through config objects or path-joining variables are likely. A future agent build step that constructs the path dynamically will cross-contaminate silently without triggering the criterion.
**How:** 
1. Replace the grep-based done criterion with a two-part criterion: (a) grep for `'graphs'` (broader — catches dynamic construction fragments) with human review of each match, AND (b) "The read-path inventory at `.planning/phases/3.1c.1-cli-graph-isolation-hardening/read-path-inventory.md` lists every callsite; each callsite is marked MIGRATED or VERIFIED-USES-GRAPHSTORE." This makes migration completeness an explicit artifact, not a negative-space grep.
2. Add a second enforcement check to the done criteria: "Run `python -c 'import alphaswarm_sol; print("no_import_error")'` and confirm no module in `kg/`, `tools/`, or `orchestration/` constructs a `.vrs/graphs` path without going through `GraphStore`. Verify by adding a `GraphStore._validate_no_bypass()` classmethod that raises if called from outside the module — or document why this check is deferred."
**Impacts:** Plan 02 done criteria need revision. Read-path inventory (P1-SYN-02) gains additional specificity requirements.
**Research needed:** no
**Confidence:** HIGH — Static grep for a literal string is an unreliable completeness check for path construction. This is a documentation-level structural gap.
**Prior art:** 4 — Standard code audit practice: literal grep is insufficient for path construction patterns; symbol-level analysis is required.
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — The done criterion gap exists in the original CONTEXT.md spec. Pass 1 added the read-path inventory requirement (SYN-02) but the done criterion was not updated to reference it as the completeness check.

### P2-IMP-08: Concurrent Write Race — Two Builds, Same Hash, Different Graph State
**Target:** CONTEXT
**What:** GraphStore.save() must use atomic write semantics (write to `.tmp` then `os.replace()`). Separately, the build command must define its overwrite policy: default is skip-if-exists (idempotent re-runs), with `--force` flag to overwrite.
**Why:** `.vrs/graphs/` is a shared artifact store accessed by concurrent agent builds. Without atomic writes, a partial `.toon` file left by a killed build will corrupt subsequent loads. The overwrite policy affects Plan 03's auto-select behavior — if skip-if-exists is the default, agents can safely run `build-kg` as a preflight without fear of invalidating a concurrent peer's graph.
**How:**
1. In Plan 02 spec: "GraphStore.save() writes to `{hash_dir}/graph.toon.tmp`, then calls `os.replace()` to atomically rename. If `graph.toon` already exists, skip unless `force=True`."
2. In Plan 02 done criteria: "Verify atomic write: kill a running build mid-write, confirm `.tmp` file is present or absent but `.toon` is never partial. GraphStore.load() must raise `CorruptGraphError` if `.tmp` exists without `.toon`."
3. In build-kg CLI spec: add `--force` flag that propagates `force=True` to GraphStore.save(). Default: skip-if-exists with INFO log "Graph already exists for {stem}, skipping. Use --force to rebuild."
4. Note in Plan 03: auto-select behavior for single-graph case applies only when graph.toon exists and `.tmp` is absent.
**Impacts:** Plan 02 implementation spec needs atomic write requirement. Plan 03 auto-select behavior clarified.
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 4
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — Concurrent write atomicity is not addressed in the original spec or in Pass 1 items.

### P2-IMP-09: meta.json Schema Is Underspecified for Plan 03 stem-Based Lookup
**Target:** CONTEXT
**What:** Plan 03's stem-based lookup relies on `meta.json` containing a `source_contract` field that Plan 02 must write. The current Plan 02 description does not mention `meta.json` at all — it only specifies `GraphStore.save()` writing to `.vrs/graphs/{identity}/graph.toon`. The schema of `meta.json` (what fields, their types, whether it's required or optional) is entirely absent from Plan 02's spec. Plan 03 then performs stem-based lookup against this file in a plan it controls, but the producer of `meta.json` is Plan 02.
**Why:** This is a producer-consumer interface gap across two plans. If Plan 02 is implemented without `meta.json`, Plan 03's stem lookup fails at runtime. The done criteria for Plan 02 do not include "meta.json is written with the expected schema" — meaning Plan 02 can be marked DONE while Plan 03 cannot execute. Separately: if two compilation units have the same stem (e.g., `contracts/v1/Token.sol` and `contracts/v2/Token.sol`), stem-based lookup is ambiguous. This ambiguity needs resolution at the Plan 02 level (what does meta.json contain to disambiguate?) not deferred to Plan 03.
**How:** 
1. Add a `meta.json` schema specification to Plan 02's CONTEXT description: `{ "identity": "<12-char hex>", "source_contract": "<stem>", "source_paths": ["<absolute_path>", ...], "build_timestamp": "<ISO-8601>", "slither_version": "<version>" }`. This makes Plan 02 the authoritative producer and Plan 03 a consumer with a defined contract.
2. Add to Plan 02 done criteria: "`.vrs/graphs/{identity}/meta.json` exists alongside `graph.toon` after every build. `jq .source_contract .vrs/graphs/*/meta.json` returns one entry per graph directory."
3. Add a disambiguation note: "When multiple graphs share a `source_contract` stem, Plan 03 MUST return an error listing all matching identity hashes (not silently pick the newest). This is enforced at the Plan 03 level, but Plan 02 must provide sufficient `meta.json` fields (specifically `source_paths`) to make the error message actionable."
**Impacts:** Plan 02 done criteria require `meta.json` writing. Plan 03's stem lookup becomes implementable without guessing the schema. Cross-plan dependency is now explicit.
**Research needed:** no
**Confidence:** HIGH — The producer-consumer gap is certain: Plan 02 description mentions no `meta.json`, Plan 03 description relies on `source_contract` field that must come from somewhere.
**Prior art:** 4 — Sidecar metadata files alongside binary artifacts is standard practice (pip wheel metadata, Maven POM, npm package.json). Minor adaptation needed.
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — The meta.json schema omission is in the original CONTEXT.md. Pass 1 did not address the Plan 02 side of this producer-consumer interface.

### P2-IMP-10: Contract Name Collision — Stem-Based Lookup Has No Disambiguation Strategy
**Target:** CONTEXT (Plan 03 description)
**What:** Plan 03 specifies that `--graph <stem>` matches against `source_contract` in per-graph `meta.json`. The spec says nothing about what happens when two contracts share a stem — e.g., `contracts/Token.sol` and `legacy/Token.sol` both produce graphs with stem `Token`. The current spec would either: (a) silently pick one arbitrarily, (b) crash, or (c) error — none of these behaviors are specified.
**Why:** This is not a theoretical edge case. In audit contexts, codebases routinely have identically-named contracts in different directories (proxy and implementation, v1 and v2). The mtime-based selection that Plan 03 explicitly rejects for the multi-graph case is implicitly present again in the stem collision case if the implementation just takes the first match. The spec must either (a) require `source_contract` in `meta.json` to store the full realpath (not just stem), making `--graph contracts/Token.sol` the disambiguation form, or (b) specify that stem collision triggers the same multi-graph error with the full paths shown. Option (b) is simpler and consistent with Plan 03's existing error philosophy.
**How:** 
1. In the Plan 03 spec section on stem-based lookup, add: "If multiple graphs match the same stem, error with exit code 1: `Error: ambiguous --graph 'Token' matches multiple graphs — use full path: contracts/Token.sol, legacy/Token.sol`. Available paths are read from `meta.json`.`source_contract_path` (full realpath stored by Plan 02 builder)."
2. Verify that Plan 02's `meta.json` schema includes `source_contract_path` (full realpath) in addition to the stem. If Plan 02 only stores the stem, note a cross-plan dependency: Plan 02 must store realpath for Plan 03's disambiguation to work. Add this as an explicit dependency note in Plan 03's `depends_on`.
**Impacts:** Plan 02 (meta.json schema must include full path), Plan 03 (stem lookup spec incomplete)
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 — standard CLI disambiguation pattern (e.g., `git checkout` branch/tag collision handling)
**Prerequisite:** no — this is a spec gap, not a missing infrastructure item
**Status:** implemented
**Origin:** NOVEL — stem collision is not addressed by any of the 30 Pass 1 items. IMP-13 addressed resolution strategy generally but did not specify the collision sub-case.

### P2-IMP-11: Zero-Results vs Broken-Graph Ambiguity — Agents Cannot Distinguish Failure Modes
**Target:** CONTEXT (Plan 03 description)
**What:** Plan 03 must specify machine-readable output protocol for query results: a structured header line on stdout, separate exit codes for valid-empty vs graph-corruption, and no overlap with routing error exit codes.
**Why:** Batch 1 failure: agents saw zero stdout lines, could not distinguish "query returned nothing" from "graph never loaded," and fell back to Python imports. Plan 03's error messages fix routing errors but don't address the zero-vs-broken ambiguity that is the direct failure cause.
**How:**
1. Add to Plan 03 spec: first stdout line for every successful query is `# result: graph_nodes={N} matches={M}` (even for M=0). This is always present when graph loaded successfully.
2. Exit code semantics: 0 = query executed (M may be 0); 1 = routing/argument error (no graph found, ambiguous stem); 2 = graph load failure (file corrupt, missing, `.tmp` present without `.toon`).
3. Done criterion: agent recovery test — invoke `query --graph NonExistent` and verify exit code 1 with `Available:` list on stderr, stdout empty. Invoke `query --graph ValidContract` on a valid empty result and verify exit code 0 with `# result: graph_nodes=N matches=0` on stdout.
4. Explicitly document that M=0 on a valid graph is NOT an error — agents must use the header line to confirm graph loaded, not treat zero matches as failure.
**Impacts:** Plan 03 (new exit code semantic), Plan 04 (smoke tests should test this exit code path)
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — directly addresses the Batch 1 failure mechanism (agents can't distinguish empty result from broken routing) which is not covered by any Pass 1 items. IMP-14 addressed error message format for routing errors but not the empty-result ambiguity.

### P2-IMP-12: Non-Existent Stem Passed to --graph — Failure Mode Not Specified
**Target:** CONTEXT (Plan 03 description)
**What:** Plan 03 says `--graph` accepts a stem matched against `source_contract` in `meta.json`. It does not specify what happens when the stem does not match any known graph. The current spec has three error paths (no `--graph` with multiple graphs, vulndocs not found) but is silent on `--graph unknown_contract`. This is the most common user/agent error: typo in contract name, or querying before the graph was built.
**Why:** Without a specified failure mode, implementations will vary. One implementation returns an unhelpful `KeyError` traceback; another silently falls through to query against no graph and returns empty results (reproducing the zero-results failure). The spec must explicitly require: exit code 1, message format that includes what stems ARE available (parallel to the multi-graph error message's "Available: Token, Vault, MasterChef" list).
**How:** 
1. Add a third error path to Plan 03's spec: "If `--graph <stem>` is provided but no graph in `.vrs/graphs/` has a matching `source_contract`, exit 1 with: `Error: no graph found for '--graph Token' — available graphs: Vault, MasterChef. Run 'alphaswarm build-kg contracts/Token.sol' to build.`"
2. Note that "available graphs" must be derived from `meta.json` files in all subdirs of `.vrs/graphs/` — this is the same listing logic as the multi-graph error path, so it should be a shared utility function. Specify this in the implementation notes to avoid duplication.
**Impacts:** Plan 03 (missing error path)
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5 — standard CLI error pattern. Every `git checkout <nonexistent-branch>` shows available branches.
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — the area brief explicitly flags this: "What happens when --graph receives a non-existent stem — does it error or silently fall through?" Pass 1 did not address this sub-case.

### P2-IMP-13: CLI I/O Channel Contract Unspecified — Agents Cannot Reliably Parse Query Results vs Diagnostics
**Target:** CONTEXT (Plan 03 description)
**What:** Plan 03 must specify machine-readable output protocol for query results: a structured header line on stdout, separate exit codes for valid-empty vs graph-corruption, and no overlap with routing error exit codes.
**Why:** Batch 1 failure: agents saw zero stdout lines, could not distinguish "query returned nothing" from "graph never loaded," and fell back to Python imports. Plan 03's error messages fix routing errors but don't address the zero-vs-broken ambiguity that is the direct failure cause.
**How:**
1. Add to Plan 03 spec a "CLI I/O Contract" section: "stdout: query result rows only (plus the `# result:` header line). stderr: all errors, warnings, and informational messages including `Available:` lists."
2. Add to Plan 03 spec: first stdout line for every successful query is `# result: graph_nodes={N} matches={M}` (even for M=0). This is always present when graph loaded successfully.
3. Exit code semantics: 0 = query executed (M may be 0); 1 = routing/argument error (no graph found, ambiguous stem); 2 = graph load failure (file corrupt, missing, `.tmp` present without `.toon`).
4. Add done criterion: pipe stdout of a failed `query --graph Unknown` to a file, verify file is empty. Pipe stderr of a successful `query --graph Token "reentrancy"` with 0 matches to a file, verify it contains `# result:` (confirming header goes to stdout not stderr).
5. Add done criterion: agent recovery test — invoke `query --graph NonExistent` and verify exit code 1 with `Available:` list on stderr, stdout empty. Invoke `query --graph ValidContract` on a valid empty result and verify exit code 0 with `# result: graph_nodes=N matches=0` on stdout.
6. Explicitly document that M=0 on a valid graph is NOT an error — agents must use the header line to confirm graph loaded, not treat zero matches as failure.
7. Show all available stems, no truncation. If count exceeds 20, add "... and N more. Run `alphaswarm list-graphs` for full list" note — but do NOT block Plan 03 on implementing list-graphs.
**Impacts:** Plan 03 (output channel specification, exit code semantics), Plan 04 (smoke tests need to check stderr specifically)
**Research needed:** no
**Confidence:** MEDIUM — the stdout/stderr channel ambiguity is a real implementation risk; the header line protocol is the key addition
**Prior art:** 4 — POSIX convention: stdout = data, stderr = diagnostics. Standard practice.
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — area brief explicitly flags this: "is the 'Available: Token, Vault, MasterChef' list format specified precisely enough?" Pass 1 IMP-14 specified message content but not output channel or format robustness.
**Adversarial note:** Enhanced by Cross-Plan Interface Integrity lens — merged P2-IMP-11's structured header line and exit code semantics into this item. Dropped N≤5/N>5 truncation rule as over-specified.

### P2-IMP-14: Concurrent Same-Contract Build Race Condition Not Addressed
**Target:** CONTEXT (Plan 04 section)
**What:** Add second concurrent smoke scenario — same contract, two simultaneous `alphaswarm build-kg` calls — and assert meta.json integrity as the observable outcome, independent of Plan 02's implementation mechanism.
**Why:** The dangerous failure mode from Batch 1 was cross-contamination within shared graph directories. Two builds of the same contract share the same output path; different-contract builds never collide there. The existing scenario validates non-collision (trivially true), not the actual race surface. The item must not block on Plan 02 guaranteeing atomicity — the test itself determines whether Plan 02 delivered it.
**How:**
1. In Plan 04's smoke test definition, add: "Scenario 2B — same contract, concurrent builds: launch two `alphaswarm build-kg <same-contract>` calls simultaneously from different workspace paths; wait for both to exit."
2. Assertion (disk-observable, no agent required): `cat <graph-dir>/meta.json | python3 -m json.tool` exits 0 (valid JSON) and contains exactly one `contract_name` field. If meta.json is a zero-byte file or contains partial JSON, scenario fails.
3. If Plan 02 uses atomic rename, this passes automatically. If it does not, this surfaces the bug. The test does NOT assume the fix.
4. Store result in `.vrs/observations/plan04/concurrent-same-contract.json` with fields: `exit_code_a`, `exit_code_b`, `meta_json_valid`, `meta_json_corrupt`, `root_cause_hypothesis`.
5. Remove "Prerequisite: yes — Plan 02 must guarantee atomic writes" — replace with "Prerequisite: no — this test reveals whether Plan 02 delivers it."
**Impacts:** Plan 04 done criteria need expansion. Plan 02 atomic writes tested by this scenario, not assumed.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 2 — file-level locking and atomic rename are well-known patterns, but applying them to this specific agent-driven concurrent build scenario is novel combination
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — Plan 02's hash storage design is unchanged from Pass 1; this gap exists independently of prior improvement passes
**Adversarial note:** Enhanced by Testing Criteria Falsifiability lens — decoupled from Plan 02 prerequisite. The test reveals whether Plan 02 delivered atomic writes rather than blocking on it.

### P2-IMP-15: ObservationRecord Field Coupling Creates Schema Drift Risk
**Target:** CONTEXT (Plan 04 section)
**What:** Plan 04 states: "Diagnostic JSON files should include `ObservationRecord`-compatible fields (`session_id`, `event_type`, `timestamp`, `phase_id`) where practical. This is NOT a scope change — it's a field format choice." This claim is incorrect. Adding ObservationRecord-compatible fields to Plan 04 diagnostic artifacts creates an implicit schema contract between Plan 04 and Phase 3.1c.2/3.1c.3's intelligence modules. If ObservationRecord's schema evolves (new required fields, renamed fields, changed types), Plan 04 artifacts silently become incompatible. The context justifies this as "makes Plan 04 artifacts readable by future Tier 2 intelligence modules without transformation" — but this benefit is speculative (3.1c.3 is PLANNED, not designed) and the cost is a hidden dependency that will manifest as a silent data-quality failure, not a hard error.
**Why:** The phrase "NOT a scope change" is a rationalization, not a technical argument. Schema coupling is a scope change by definition — it adds a maintenance obligation. If Plan 04 artifacts use ObservationRecord fields, they are implicitly part of the ObservationRecord contract. The correct approach is one of: (a) fully commit — define ObservationRecord schema in 3.1c.2 FIRST, then Plan 04 writes conformant artifacts (explicit contract), or (b) don't use ObservationRecord fields in diagnostic artifacts — let 3.1c.3 write a transform. Option (b) is better because Plan 04's goal is CLI smoke testing, not observation infrastructure.
**How:** 
1. In the Plan 04 "ObservationRecord bridge" paragraph, replace the current text with one of two explicit choices: either (a) "Plan 04 diagnostic JSON uses its own schema: `{session_id, attempt, timestamp, contract_name, command_run, exit_code, stdout_excerpt, stderr_excerpt, root_cause_hypothesis}`. ObservationRecord compatibility is NOT a Plan 04 concern — 3.1c.3 will define transforms if needed" OR (b) "Plan 04 DEFERS diagnostic JSON field definition until 3.1c.2 publishes the ObservationRecord schema. Plan 04's storage path is `.vrs/observations/plan04/debug-<session-id>-<attempt>.json` but field names are TBD pending 3.1c.2."
2. Remove the word "practical" from the current text — "where practical" makes the coupling conditional and untestable, which is worse than either explicit option.
**Impacts:** Plan 04 diagnostic output contract becomes self-contained. 3.1c.3 plans need no change (they were always speculative consumers).
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 — schema-first vs. schema-later coupling is a well-documented API design decision
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — Pass 1 added the ObservationRecord bridge language (P1-IMP-19 "failure information contract"). This item challenges that addition's correctness, but the coupling problem exists in the current CONTEXT.md text regardless of how it got there. A reader of the original CONTEXT would not have seen this text — it was added by Pass 1. However, the coupling problem is a genuine structural issue that would cause execution failure if 3.1c.3 assumes Plan 04 artifacts conform to a schema that was never formally defined. Treating as NOVEL under the DERIVATIVE exception (would cause silent data-quality failure, requires schema design knowledge not present in the file).

### P2-IMP-16: Phase-Type Taxonomy Has No Mixed-Type Protocol — 3.1c.1 Is Both CODE and FRAMEWORK
**Target:** CONTEXT (Plan 05a section)
**What:** Plan 05a defines four phase types: CODE, EVALUATION, FRAMEWORK, SYNTHESIS. Each type has distinct testing requirements. But 3.1c.1 itself is simultaneously: CODE (fixes CLI Python code in Plans 01-03) and FRAMEWORK (Plans 04-05 modify the testing infrastructure via the smoke test harness and governance documents). The taxonomy as stated has no rule for mixed-type phases. The context says nothing about this case. This is not a hypothetical — it affects the CURRENT phase. If 3.1c.1 applies CODE requirements (Agent Teams + AgentExecutionValidator all 12 checks + at least 1 red-path session), that's Plan 04's scope. If it applies FRAMEWORK requirements (snapshot-before/after diff + regression on prior baselines), that's Plan 05a/05b's scope. If BOTH apply, the acceptance bar doubles and is never stated explicitly anywhere.
**Why:** Without a mixed-type protocol, phase authors will either (a) pick the type with lower requirements (scope creep downward), or (b) be paralyzed by ambiguity at acceptance time. The taxonomy is designed to create unambiguous gates — a taxonomy with no rule for its own first real-world application is not fit for purpose. The area brief flags this explicitly.
**How:** 
1. In Plan 05a's "Phase type taxonomy" deliverable, add a "Mixed-type phases" rule: "A phase may declare multiple types separated by `+` (e.g., `type: CODE+FRAMEWORK`). The acceptance bar is the UNION of requirements for all declared types. The primary type (listed first) determines which team owns the acceptance decision."
2. Retroactively annotate 3.1c.1 in Plan 05b's CONTEXT.md update list as `type: CODE+FRAMEWORK` so it becomes the first test of the mixed-type rule.
3. Add a done criterion to Plan 05a's task: "The mixed-type rule has been applied to at least one existing phase (3.1c.1) and the resulting requirement list has been verified as non-contradictory."
**Impacts:** Plan 05a's taxonomy design is structurally incomplete without this. Plan 05b's rollout to 3.1c.2/3.1f/3.2 may discover additional mixed-type phases.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 1 — agile Definition of Done handles single-type work items; multi-type phase classification for AI testing phases has no direct prior art
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — the mixed-type problem is visible from reading CONTEXT.md and the four phase types in isolation; it does not depend on prior passes

### P2-IMP-17: Bootstrap Exception Is Mechanically Undefined — "Snapshot" Has No Implementation
**Target:** CONTEXT (Plan 05a section)
**What:** Define "snapshot" mechanically for the bootstrap exception: record the jj change ID (or git SHA) immediately before any framework-modifying task begins, and specify the exact commands needed to both record and restore that state when running prior baselines.
**Why:** An unrecorded or unrestorable snapshot is indistinguishable from no snapshot. The exception currently instructs executors to do something they cannot reproduce deterministically.
**How:**
1. In Plan 05a's FRAMEWORK phase definition, add a "Snapshot Protocol" subsection:
   - Before first framework-modifying task: run `jj log -r @ --no-graph -T change_id` and write output to `.vrs/snapshots/{phase}/pre-change-id.txt`.
   - Alternative (if jj unavailable): `git rev-parse HEAD > .vrs/snapshots/{phase}/pre-change-sha.txt`.
2. Specify restoration command for prior-baseline runs: `jj co $(cat .vrs/snapshots/{phase}/pre-change-id.txt)` in a separate workspace (never in the active workspace); run baselines from that workspace; exit workspace without committing.
3. Add a one-line verification: after recording, `cat .vrs/snapshots/{phase}/pre-change-id.txt` must be non-empty and match current jj log output. If empty, abort phase — snapshot not captured.
4. Update bootstrap exception text: replace "use pre-modification snapshot" with "use snapshot recorded per Snapshot Protocol above; if `.vrs/snapshots/{phase}/pre-change-id.txt` is absent, the exception is void and standard FRAMEWORK requirements apply."
5. In Plan 05b, add a task: "Verify the snapshot mechanism works for 3.1c.2 by recording its pre-change ID and confirming prior Plan 12 baselines can run against it."
**Impacts:** Plan 05a done criteria become verifiable. Plan 05b gains one concrete task.
**Research needed:** no — both `jj log` and `git rev-parse` are standard; the application to this specific context is novel but implementable
**Confidence:** HIGH
**Prior art:** 2 — snapshot-based acceptance testing exists in database migration testing and semantic versioning, but applying it to AI testing framework phases with Jujutsu is novel
**Prerequisite:** no (jj colocated repo is already a prerequisite per Plan 04 workspace isolation)
**Status:** implemented
**Origin:** NOVEL — bootstrap exception language was added in Pass 1 (P1-IMP-25 addressed the 3.1c.2 recursion problem). The mechanical implementation gap exists in the current CONTEXT.md independently — any executor reading this would immediately ask "how do I snapshot?" This item addresses the implementation gap, not the logical addition.
**Adversarial note:** Enhanced by Testing Criteria Falsifiability lens — added explicit jj co restoration command and verification step. Closed the record-but-can't-restore gap.

### P2-IMP-18: Pre-Validation Partial Failure Has No Recovery Path
**Target:** CONTEXT (Plan 04 section)
**What:** Plan 04 defines a "framework pre-validation step" with three checks: (a) WorkspaceManager: create workspace, verify directory, tear down; (b) TeamManager: create team with echo agent, verify parseable observation; (c) EvaluationRunner: run pipeline on synthetic transcript. It states: "Only proceed to agent spawning if all three pass. This disambiguates 'CLI is broken' from 'WorkspaceManager is broken.'" But the plan specifies no recovery path when exactly ONE or TWO of the three checks fail. A developer who sees "WorkspaceManager passes, TeamManager fails, EvaluationRunner passes" needs to know: (1) is this a hard stop?, (2) can they fix TeamManager in isolation and re-run only that check?, (3) does fixing TeamManager require re-running WorkspaceManager first? Without this, the "disambiguates" claim is aspirational — the developer knows WHAT failed but not WHAT TO DO.
**Why:** Binary smoke tests without recovery guidance produce the same outcome as no smoke tests: the developer escalates to manual debugging. The pre-validation step's value is proportional to how actionable its failure output is. The current design identifies the failing component (good) but leaves the executor without a defined next step (bad). This is particularly important for Plan 04 because it is the TESTING FRAMEWORK ITSELF being validated — a confusing failure here cascades to confusion in all downstream phases.
**How:** 
1. In Plan 04's "framework pre-validation step" section, add a recovery table after the three checks: "| Failed component | Recovery action | Re-run required | ... WorkspaceManager | Verify `jj` installed and repo is jj-colocated; run `jj status` | Re-run WorkspaceManager check only | ... TeamManager | Verify Claude Code version freshness (session binary check from MEMORY.md); restart session if stale | Re-run TeamManager + EvaluationRunner | ... EvaluationRunner | Run `uv run pytest tests/workflow_harness/ -k synthetic` to isolate | Re-run EvaluationRunner only |"
2. Add a done criterion: "If any pre-validation check fails, the failure message includes the component name, the exact command that failed, and the recovery action from the recovery table."
**Impacts:** Plan 04 failure handling becomes actionable. No other plans affected.
**Research needed:** no
**Confidence:** MEDIUM — the three specific recovery actions above are inferred from the component designs; actual failure modes may differ
**Prior art:** 3 — pre-flight check patterns with recovery tables are standard in CI/CD tooling and DevOps runbooks
**Prerequisite:** no
**Status:** rejected
**Origin:** NOVEL — pre-validation was added in Pass 1 (P1-IMP-18 "circular dependency fix"). The recovery path gap exists in the current text and is discoverable on first read by anyone executing Plan 04.
**Rejection reason:** Pre-validation already names three scoped components. Developer who sees "WorkspaceManager: FAIL" has enough context to proceed to jujutsu debugging. Recovery table restates component-to-domain mapping already implicit. Documentation alignment, not falsifiability gap. (Lens: Testing Criteria Falsifiability)

### P2-IMP-19: Concurrent Build Verification Criterion Is Not Disk-Observable
**Target:** CONTEXT (Plan 04 section)
**What:** Replace the concurrent build acceptance criterion from "all agents pass CLI confirmation" to a graph-identity assertion: after concurrent builds of contracts X and Y, each agent must query a pattern known to exist ONLY in its assigned contract and get the correct result.
**Why:** CLI confirmation (did agent use bash? non-empty results?) cannot detect cross-contamination because contaminated graphs return non-empty results. The Batch 1 failure mode — agents querying the wrong graph — passes all four CLI confirmation checks. A regression test that cannot detect the regression it was written for is not a regression test.
**How:**
1. Before the concurrent test, establish ground truth: build X and Y sequentially in isolation. Run `alphaswarm query "<pattern>" --graph X` — record which patterns return non-empty. Do same for Y. Identify at least one pattern that is non-empty in X and empty in Y, and vice versa. Store as `.vrs/observations/plan04/ground-truth-patterns.json` with fields `x_only_pattern`, `y_only_pattern`.
2. After concurrent builds, acceptance criterion becomes: Agent A (assigned to X) runs `alphaswarm query "<x_only_pattern>"` → non-empty; Agent B (assigned to Y) runs the same query → empty. If B returns non-empty, contamination confirmed.
3. Add symmetric check: Agent B queries `<y_only_pattern>` → non-empty; Agent A queries same → empty.
4. If ground-truth step finds no X-only or Y-only patterns (contracts too similar), use different test contracts. Document this selection criterion in Plan 04 scope: "Test contracts must have at least one discriminating pattern each."
5. Replace current criterion text with: "Concurrent isolation confirmed: each agent returns non-empty for its contract's unique pattern and empty for the other contract's unique pattern."
**Impacts:** Plan 04's done criteria become genuinely falsifiable for the cross-contamination regression. Requires selecting test contract pairs carefully (coordination with test contract selection in Plan 04's setup).
**Research needed:** no — `tests/contracts/` already contains both vulnerable and safe variants per the CLAUDE.md
**Confidence:** HIGH
**Prior art:** 3 — differential testing (A vs. B expected difference) is a standard pattern in regression test design
**Prerequisite:** no (test contracts with known differentials already exist)
**Status:** implemented
**Origin:** NOVEL — this gap exists in the original CONTEXT.md specification of the concurrent build scenario. Pass 1 added the binary CLI confirmation criteria (P1-IMP-17) but did not address cross-query verification for graph isolation.
**Adversarial note:** Enhanced by Testing Criteria Falsifiability lens — added ground-truth pattern selection step so cross-query assertion is deterministic, not dependent on agent knowing which patterns are contract-specific.

## Post-Review Synthesis
**Items created:** P2-SYN-01, P2-CSC-01, P2-CSC-02, P2-CSC-03, P2-CSC-04
**Key insight:** The meta.json sidecar is referenced by both Plan 02 (write) and Plan 03 (read/route), but its schema, write timing, and path-encoding rules are fragmented across three separate items with no single authoritative specification — leaving Plan 03 implementers dependent on implicit assumptions about what Plan 02 will produce. Additionally, IMP-08's skip-if-exists cache behavior has no staleness signal, leaving agents with no way to detect or recover from stale graph state.

---

### P2-SYN-01: meta.json Schema Is a Cross-Plan Contract With No Authoritative Spec
**Target:** CONTEXT
**What:** IMP-06, IMP-09, and IMP-10 each modify what goes into meta.json, when it is written, and what fields it must contain — but these items target Plan 02 and Plan 03 separately. No single item defines the complete meta.json schema that Plan 03 must read.
**Why:** When a data structure is written by one plan and read by another, the schema must be the authoritative interface contract. Without a canonical field list, Plan 02 and Plan 03 can be implemented independently in subtly incompatible ways. This creates latent incompatibility when IMP-06, IMP-09, IMP-10 are implemented in isolation.
**How:**
1. Add canonical meta.json schema block to CONTEXT decisions section. Fields required: `schema_version` (int), `built_at` (ISO-8601), `graph_hash` (sha256 hex, repo-relative inputs only), `contract_paths` (list of repo-relative strings), `stem` (string, derived from last path component without extension). Include validation rules: all fields mandatory, string lengths bounded, no extra fields allowed.
2. Add validation test in Plan 04 smoke tests: load meta.json, assert all required fields present and types correct, assert schema_version matches expected value.
3. Document in Plan 03: "Query router must validate meta.json schema_version at load time; fail fast with `[error] meta.json schema version mismatch` if version does not match expected."
**Impacts:** PLAN-02, PLAN-03, PLAN-04 (smoke test for schema validation)
**Components:** P2-IMP-06, P2-IMP-09, P2-IMP-10
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 2
**Prerequisite:** no
**Status:** implemented
**Source:** Post-review synthesis (cross-cutting)
**Origin:** genuine
**Adversarial note:** Enhanced by ADV Validation — separated CONTEXT schema definition from CODE validation tasks. Validation steps belong in Plan 03/04, not conflated with schema spec.

---

### P2-CSC-01: skip-if-exists Cache Has No Staleness Signal for Agents
**Target:** CONTEXT (Plan 02 description)
**What:** IMP-08 introduces skip-if-exists as default. If a contract file changes on disk after graph build, subsequent build-kg calls silently return the old graph. Agent Teams smoke tests modifying contracts between builds receive stale graphs undetected.
**Why:** Agent Teams smoke tests build graphs, modify contracts, and rebuild — without a staleness signal, they receive stale graphs undetected. This is exactly the class of silent correctness failure IMP-08 was introduced to prevent for concurrency.
**How:**
1. Add `--check-fresh` flag to `build-kg`. Implementation: compute SHA256 of current contract files (same algorithm as IMP-06 graph_hash), compare to `meta.json.graph_hash`. Emit to stderr: `[graph-cache] skipped: <stem> (hash match) — use --force to rebuild` if match (fresh), or `[WARNING] cache mismatch: <stem> has changed on disk (hash differs). Use --force to rebuild.` if hash differs (stale).
2. Return exit code 0 on fresh, non-zero (suggest 42) on stale (so callers can detect via shell).
3. Add Plan 04 smoke test: build contract, modify file, run build-kg --check-fresh, assert exit code 42 and stale warning emitted.
**Impacts:** PLAN-02, PLAN-04
**Trigger:** P2-IMP-08
**Depends on plans:** IMP-06 (hash algorithm must be defined first)
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Status:** implemented
**Source:** Post-review synthesis (cascade)
**Adversarial note:** Enhanced by ADV Validation — added hash algorithm specificity, exit code for programmatic detection, explicit test scenario.

---

### P2-CSC-02: git rev-parse Fallback Undefined for Non-Git or Bare-Repo Contexts
**Target:** CONTEXT (Plan 02 description)
**What:** IMP-06 requires `git rev-parse --show-toplevel` to identify project root. No fallback specified when this fails (non-git directories, bare repos, submodules). CLI is intended to work in any directory; unhandled errors break the "work from any directory" goal and break Agent Teams isolation testing in temp directories.
**Why:** Smoke tests in Plan 04 run inside the project's git repo, so this failure is invisible during testing. A user running `build-kg` outside a git repo gets an unhandled subprocess error rather than a usable graph.
**How:**
1. In Plan 02 code: wrap git command in try/except. On CalledProcessError, log to stderr: `[warning] not a git repo, using cwd as project_root` and set project_root = os.getcwd(). Store in meta.json as `project_root_type: "git_toplevel" | "fallback_cwd"` for diagnostics.
2. In Plan 04 smoke test: add "non-git directory build" — create temp dir, run build-kg, assert exit 0 and warning logged, assert meta.json contains `project_root_type: "fallback_cwd"`.
**Impacts:** PLAN-02, PLAN-04
**Trigger:** P2-IMP-06
**Depends on plans:** PLAN-02 (modifies Plan 02 implementation)
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 2
**Prerequisite:** no
**Status:** implemented
**Source:** Post-review synthesis (cascade)
**Adversarial note:** Enhanced by ADV Validation — added project_root_type diagnostic field in meta.json, explicit depends_on_plans.

---

### P2-CSC-03: Structured Query Header Requires Consumer-Side Parsing Contract Not Specified
**Target:** CONTEXT (Plan 03 description)
**What:** IMP-11 introduces `# result: graph_nodes=N matches=M` header on stdout alongside data. No parsing contract specified: agents piping query output to JSON parsers or LLM contexts will treat the header as unexpected data.
**Why:** Without a parsing contract, consumers must guess: is header always first? Only line with `#`? Can data lines contain `#`? Plan 04 smoke tests using CLI confirmation as an observable outcome may falsely reject valid output if they don't strip the header.
**How:**
1. Add to Plan 03 CONTEXT decisions: "Query stdout contract: first line always matches `^# result: graph_nodes=\d+ matches=\d+$`, followed by JSON array (one object per line). No other lines begin with `#`. This is the authoritative parsing rule for all consumers."
2. In Plan 03 code: document in docstring: "Print header to stdout only, never to stderr. Header is always first output."
3. In Plan 04 smoke test: add "query output parsing" — run query, capture stdout, verify first line matches header regex, verify all subsequent lines are valid JSON or empty, verify no line except first begins with `#`.
**Impacts:** PLAN-03, PLAN-04
**Trigger:** P2-IMP-11
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 2
**Prerequisite:** no
**Status:** implemented
**Source:** Post-review synthesis (cascade)
**Adversarial note:** Enhanced by ADV Validation — specified JSON output format for data lines, moved contract location to CONTEXT decisions, clarified header-only-on-stdout rule.

---

### P2-CSC-04: Snapshot Protocol in Plan 05a Not Propagated to Plan 05b Rollout Scope
**Target:** CONTEXT (Plan 05a section)
**What:** IMP-17 defines jj Snapshot Protocol for Plan 05a (change ID recording, rollback procedure). Plan 05b covers governance rollout to 3.1c.2, 3.1f, 3.2. If downstream phases don't adopt the same convention, cross-phase state restoration becomes inconsistent and rollback/resume logic breaks.
**Why:** The Snapshot Protocol exists precisely because safe improvement requires reproducible state restoration. Different snapshot formats across phases make automated restoration impossible.
**How:**
1. In Plan 05b CONTEXT (frontmatter section), add governance requirement: "Snapshot Protocol Inheritance: All downstream phases (3.1c.2, 3.1f, 3.2) must adopt jj Snapshot Protocol from Plan 05a. Protocol definition: [link to 3.1c.1-CONTEXT.md jj section]. Each phase planner must include snapshot change ID recording in their own Plan frontmatter."
2. In Plan 05b governance checkpoint task: add verify step "Check 3.1c.2-CONTEXT.md, 3.1f-CONTEXT.md frontmatter — both must reference Snapshot Protocol and include change ID recording instructions. Fail if missing."
3. Mark depends_on_plans: PLAN-05a (to ensure IMP-17 is implemented before 05b execution).
**Impacts:** PLAN-05a, PLAN-05b (and downstream: 3.1c.2, 3.1f)
**Trigger:** P2-IMP-17
**Depends on plans:** PLAN-05a
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 1
**Prerequisite:** no
**Status:** implemented
**Source:** Post-review synthesis (cascade)
**Adversarial note:** Enhanced by ADV Validation — added explicit depends_on_plans, reframed downstream CONTEXT files as verify-when-scoped rather than pre-existing deliverables.

## Convergence

Pass 2: 0% cosmetic (0/22)
Structural: 22 | Cosmetic: 0
Threshold: 80% (novelty: some novel combinations)
Signal: ACTIVE
