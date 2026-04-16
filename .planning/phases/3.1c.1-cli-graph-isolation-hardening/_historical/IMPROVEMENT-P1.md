# Improvement Pass 1

**Date:** 2026-02-27
**Phase:** 3.1c.1
**Status:** complete

## Pipeline Status

| Stage | Pending | Done | Blockers |
|-------|---------|------|----------|
| Prerequisites | 0 | 0 | — (6 auto-fixed: CONTEXT targets) |
| Research | 0 | 2 | — (P1-IMP-05, P1-CSC-01 resolved by /msd:research-gap) |
| Gaps | 0 | 0 | — |
| Merge-ready | 28 | 0 | — |

**Total items:** 35 (29 IMP + 2 ADV + 2 SYN + 2 CSC) | Rejected: 3 | Reframed: 2 | Net actionable: 30
**Pipeline:** [discuss] ✓ → [improve] ✓ → [pre-impl] — → [research] ✓ → [implement] ~ → [plan] — → [execute] —
**Next:** /msd:implement-improvements 3.1c.1 — 30 items ready to merge

## Adversarial Lenses

| Lens | Brief | Items | Attack Vector |
|------|-------|-------|---------------|
| Path & Hash Determinism | You are the executor reading Plans 01 and 02. Plan 01 says "single file change" but 5+ failure modes exist beyond the default constant. Plan 02 says "standard storage pattern" but hash input ambiguity and backward compat gaps are structural. | P1-IMP-01 to P1-IMP-11 | If you are implementing Plan 01 or 02 for the first time, does each item identify a real execution blocker, or does it over-engineer a simple fix? |
| Agent Protocol Coherence | You are the executor reading Plans 03 and 04. "Clear error" is meaningless without specifying what the error says. "Interactive debugging" has no protocol: no interrogation template, no transcript criteria, no failure-info contract. | P1-IMP-12 to P1-IMP-22 | Does each item identify a genuine protocol gap that would block Plan 04 execution, or impose premature specificity on a protocol that should emerge from sessions? |
| Governance Architecture | You are the executor reading Plan 05. The mandate has no teeth, no taxonomy, creates a bootstrap paradox for 3.1c.2, targets undefined phases, and captures "use" but not "improve." | P1-IMP-23 to P1-IMP-29 | Does each item make the mandate genuinely stronger, or turn a straightforward requirement into an over-engineered governance framework? |

## Improvements

### P1-IMP-01: Partial fix — non-default vulndocs consumers not covered
**Target:** CONTEXT
**What:** The domain assumption "vulndocs/ (466 patterns) must be accessible from any cwd via __file__-relative paths" scopes the fix to `_DEFAULT_VULNDOCS` in `patterns.py L32`. But vulndocs consumers likely include category subdirectory traversal, pattern file loaders, and any code that constructs sub-paths like `Path(vulndocs_dir) / category / "*.yaml"`. If those sub-path constructions are relative or assume cwd, the same failure recurs after the default constant is fixed.
**Why:** Fixing the default constant is necessary but not sufficient. A caller that receives an absolute path for `_DEFAULT_VULNDOCS` but then resolves sub-patterns via a relative join still breaks. The stated fix resolves the entry point; the area brief explicitly warns about this. The failure mode: `get_patterns()` resolves correctly, but the pattern loader iterates categories and constructs `Path(base) / sub` — if `base` is already absolute this is fine, but if any intermediate step re-relativizes (e.g., `os.chdir`, relative symlink), it fails silently.
**How:** 
1. Audit all callers of `get_patterns()` and `PatternDirectory` (or equivalent) — use grep/LSP `find_references` on `_DEFAULT_VULNDOCS`, `get_patterns`, and any pattern-loading entry points — and list every place a path is constructed relative to a variable rather than anchored to `__file__`.
2. For each identified path construction, verify it is either (a) downstream of an already-absolute base, or (b) explicitly converted to absolute. Document findings in the plan's done criteria as: "grep for `Path(` in vulndocs-touching code finds zero relative constructions outside of __file__-anchored roots."
**Impacts:** Plan 01 confidence remains HIGH only if this audit passes; otherwise confidence drops to MEDIUM until all consumers are patched.
**Research needed:** no — code audit via existing LSP/grep tools
**Confidence:** HIGH
**Prior art:** 4 — standard practice: fix the root, audit all consumers (same pattern in Django's BASE_DIR, Flask's instance_path)
**Prerequisite:** no
**Status:** open
**Origin:** NOVEL — would exist reading only patterns.py; the brief confirms this risk but the CONTEXT doesn't resolve it
**Adversarial verdict:** ENHANCE (Path & Hash Determinism) — grep audit done criterion too weak; needs to specify what passing looks like. Enhanced What/Why/How: audit all Path() constructions in vulndocs loading stack, verify every loader is __file__-anchored or argument-driven, add "zero bare relative Path constructions" done criterion.
**Status:** implemented

### P1-IMP-02: Package layout divergence — editable vs installed
**Target:** CONTEXT
**What:** The domain assumption "vulndocs/ (466 patterns) must be accessible from any cwd via __file__-relative paths" does not distinguish between editable installs (where `__file__` resolves to the source tree and `vulndocs/` is a sibling directory) and non-editable pip installs (where `__file__` resolves inside `site-packages/` and `vulndocs/` must be declared as `package_data` in `pyproject.toml` or it won't be present at all).
**Why:** `__file__`-relative resolution is correct for editable installs and development. For production pip installs, if `vulndocs/` is not listed in `package_data` / `data_files`, it is simply absent from `site-packages/`, and `__file__.parent / "vulndocs"` resolves to a non-existent path. The canonical Python fix is `importlib.resources` (`importlib.resources.files("alphaswarm_sol") / "vulndocs"`) which works across both layouts. The concrete failure: a user runs `pip install alphaswarm-sol` into a clean virtualenv, invokes `alphaswarm build-kg`, and gets `PatternDirectoryNotFoundError` — same error, different root cause, NOT fixed by the Plan 01 approach.
**How:**
1. Check `pyproject.toml` for `[tool.setuptools.package-data]` or equivalent — verify `vulndocs/**/*.yaml` (and sub-pattern files) are declared. If absent, add them. Document in Plan 01 done criteria: "pyproject.toml includes vulndocs in package_data and `pip install --no-editable .` followed by `alphaswarm build-kg /tmp/test` succeeds."
2. Replace the proposed `Path(__file__).parent / "vulndocs"` constant with `importlib.resources.files("alphaswarm_sol").joinpath("vulndocs")` (Python 3.9+ API, returns a `Traversable`). Convert to `Path` only at the point of use. This is layout-agnostic. Add this as an explicit decision in Plan 01 task actions.
**Impacts:** Plan 01 done criteria need a non-editable install verification step. Without this, the fix works only in dev — which is where Jujutsu workspaces are used, but hides a production bug.
**Research needed:** no — importlib.resources is stdlib, well-documented
**Confidence:** HIGH
**Prior art:** 5 — importlib.resources.files() is the documented Python stdlib solution for this exact problem; PyPA packaging guide covers it
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — production install layout divergence is invisible from reading only the Jujutsu/cwd problem statement

### P1-IMP-03: Missing negative test — vulndocs absent entirely
**Target:** CONTEXT
**What:** The domain section states "clear test criteria" for Plan 01 without specifying what happens when `vulndocs/` is missing from the resolved path. The area brief asks "What happens when vulndocs/ doesn't exist in the package at all (partial installs)?" The context has no assumption or done criterion for this case.
**Why:** If the `__file__`-relative path resolves to a non-existent directory (partial install, corrupted package, path computation error), the user gets an opaque `PatternDirectoryNotFoundError` or `FileNotFoundError` — same symptom as the original bug, making diagnosis impossible. A clear, actionable error message ("vulndocs not found at {resolved_path}; ensure the package was installed with data files") is qualitatively different from an OS-level FileNotFoundError.
**How:** 
1. Add to Plan 01 task actions: "After computing the resolved path, assert it exists with an explicit ValueError that includes the resolved path and installation instructions." This should be a 3-line guard at the top of `get_patterns()`.
2. Add a done criterion: "Calling `get_patterns()` with a non-existent vulndocs path raises `ValueError` with the resolved absolute path in the message, not a raw `FileNotFoundError` or `PatternDirectoryNotFoundError` with an ambiguous relative path."
**Impacts:** Plan 01 done criteria need this negative-path verification.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5 — standard defensive programming; Django's settings validation, Flask's app.instance_path checks all do this
**Prerequisite:** no
**Status:** rejected
**Adversarial verdict:** REJECT (Path & Hash Determinism) — Missing error message is test coverage, not an execution blocker; conflates correctness with defensive programming
**Origin:** NOVEL — absent entirely from CONTEXT; not addressed by the fix description

### P1-IMP-04: Test code hardcoding `Path("vulndocs")` — silent regression risk
**Target:** CONTEXT
**What:** The area brief explicitly calls out: "does any test code hardcode `Path('vulndocs')` and would break?" The CONTEXT does not mention a test-code audit as part of Plan 01's scope or done criteria. If tests construct `Path("vulndocs")` directly (common in test fixtures that run from the project root in CI), they will pass in CI but fail in Jujutsu worktrees — exactly mirroring the original bug.
**Why:** Tests that pass in one context and fail in another are worse than no tests: they create false confidence. The Jujutsu isolation requirement is specifically to test from non-project cwds — if test setup code itself uses relative paths, the tests that should VERIFY the fix will fail for the wrong reason, masking whether the fix worked.
**How:** 
1. Run `grep -r 'Path("vulndocs")' tests/` and `grep -r "Path('vulndocs')" tests/` and `grep -rn '"vulndocs"' tests/` — list all matches. Each match is a potential regression point.
2. Add to Plan 01 done criteria: "grep for literal `Path(\"vulndocs\")` or `\"vulndocs\"` in test fixtures returns zero matches; all test references to vulndocs use the same `__file__`-anchored (or importlib.resources) helper used by production code."
**Impacts:** Plan 01 verification steps need this grep as an explicit check.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5 — standard practice when fixing path resolution: search for all instances of the old pattern in test code
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — area brief raises the question but CONTEXT does not answer it

### P1-IMP-05: Symlink and zip-safe edge cases for __file__ resolution
**Target:** CONTEXT
**What:** The CONTEXT proposes `__file__`-relative resolution as the fix. `__file__` for a symlinked package points to the symlink location, not the real file. `Path(__file__).parent` then resolves to the symlink's parent, not the source tree. For Jujutsu workspaces specifically, if the workspace uses symlinks for shared files, `__file__` may point into the workspace but `vulndocs/` lives only in the real tree. Additionally, if alphaswarm-sol is ever distributed as a wheel/zip (PEX, zipapp), `__file__` inside a zip archive has no real filesystem parent.
**Why:** The Jujutsu worktree model creates workspace directories with links back to the main tree. If Python resolves symlinks (it does NOT by default — `__file__` is the link path, not the real path), the path computation is correct. But if the user's environment has `PYTHONPATH` pointing into a symlinked location, `Path(__file__).parent.resolve()` vs `Path(__file__).parent` produces different results. Using `importlib.resources` (IMP-02) is the correct fix for the zip-safe case. For the symlink case: explicitly state in Plan 01 assumptions that the worktree structure does not use symlinks for the package directory itself (only for contracts being analyzed).
**How:** 
1. Add to Plan 01 assumptions section: "Jujutsu workspaces copy (not symlink) the Python package source; `__file__`-relative resolution is valid in this layout."
2. If the above cannot be guaranteed, switch to `importlib.resources.files()` as proposed in IMP-02, which is both symlink-safe and zip-safe.
**Impacts:** Plan 01 confidence HIGH -> MEDIUM if symlink behavior in Jujutsu worktrees is unverified.
**Research needed:** no — RESOLVED by /msd:research-gap (GAP-01)
**Research summary:** Jujutsu workspaces create real file copies (not symlinks). Empirically verified with jj 0.38.0. With editable install, __file__ resolves to main source tree regardless of workspace cwd. __file__-relative fix is safe. Plan 01 confidence stays HIGH.
**Confidence:** HIGH
**Prior art:** 3 — symlink behavior with `__file__` is documented; Jujutsu-specific behavior is not widely documented for Python packaging
**Prerequisite:** no
**Status:** implemented
**Adversarial verdict:** RESEARCH (Path & Hash Determinism) — RESEARCH — Jujutsu symlink vs copy behavior is genuinely unresolved
**Origin:** NOVEL — Jujutsu-specific layout assumption is not in CONTEXT; requires domain knowledge about jujutsu workspace structure

### P1-IMP-06: Path Normalization Must Use `os.path.realpath`, Not `os.path.abspath`
**Target:** CONTEXT
**What:** The domain assumption states "absolute resolved path" for hashing, but does not specify how resolution handles symlinks. `os.path.abspath` does NOT resolve symlinks — it only makes a path absolute from cwd. In Jujutsu workspaces, the same physical file is often accessed via a worktree symlink that produces a different absolute path than the canonical checkout. If two agents build graphs for the same contract but from different Jujutsu workspace symlinks, `abspath` produces different hashes → two separate graph subdirs → Plan 03's `--graph` flag cannot locate the right one.
**Why:** `os.path.realpath` follows all symlinks and produces a single canonical path. This is the standard fix for exactly this class of hash-divergence bug. Using `abspath` here is a latent correctness bug that will only manifest in the Jujutsu-isolated testing that Plan 04 exercises — i.e., the failure will be invisible until Plan 04 runs, which is the worst time to discover it.
**How:** 
1. In the CONTEXT assumptions section, replace "absolute resolved path" with "canonicalized real path via `os.path.realpath()`" and note explicitly that `abspath` is insufficient because it does not follow symlinks.
2. Add a note that hash input should be `os.path.realpath(contract_path)` encoded as UTF-8 before hashing, so the hash is reproducible regardless of the cwd or workspace from which the path was originally provided.
**Impacts:** Directly affects Plan 02 implementation. Also affects Plan 03 (--graph flag needs same resolution logic) and Plan 04 (Jujutsu workspace tests will catch this if it is wrong).
**Research needed:** no — `os.path.realpath` vs `os.path.abspath` is documented Python stdlib behavior.
**Confidence:** HIGH
**Prior art:** 5 — Standard Python path canonicalization; used in every package cache, build system, and test harness that needs stable hashes from paths.
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — Jujutsu workspace symlink divergence is not addressed anywhere in the context; the assumption "absolute resolved path" is ambiguous and this ambiguity survives without prior passes.

### P1-IMP-07: Hash Input Must Be Defined Precisely — Path String vs Normalized Bytes
**Target:** CONTEXT
**What:** The context says hash is `sha256(contract_path)[:12]` but does not specify: (a) whether `contract_path` is the raw string passed by the agent or the resolved canonical path, (b) the encoding (UTF-8? OS default?), (c) whether trailing slashes are stripped, (d) whether `.` passed to `build-kg` expands to the directory or is hashed as a literal dot. Any variation in these details causes hash divergence between the `build-kg` call and a later `query --graph` call if the two calls resolve the path differently.
**Why:** This is not a minor wording issue. The hash is the contract identity for the entire system. If the hash function is underspecified, every downstream caller (Plan 03 --graph, Plan 04 agents) may use a different computation and silently miss each other's graphs.
**How:** 
1. Add an explicit hash specification to the CONTEXT assumptions: `key = sha256(os.path.realpath(contract_path).encode('utf-8')).hexdigest()[:12]`. State this verbatim so plan authoring and implementation are aligned.
2. Add edge case: if `contract_path` is a directory (e.g., `build-kg .`), hash the directory's realpath, not an individual file — and document how `query` locates the graph in that case (directory-level key vs file-level key creates a scope mismatch).
**Impacts:** Plan 02 implementation, Plan 03 --graph flag lookup, Plan 04 validation.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 — Jenkins artifact caching, Bazel output hash computation — all specify exact hash input normalization. The pattern is established; the application here is straightforward.
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — Hash input underspecification is a structural gap in the current context independent of any prior pass.

### P1-IMP-08: Backward Compatibility Strategy Is Absent — Risk of Silent Read-Miss
**Target:** CONTEXT
**What:** The context notes "backward-compatible: existing `alphaswarm build-kg .` at project root still works" but this means build still *works*, not that existing `.vrs/graphs/graph.json` or `.vrs/graphs/graph.toon` flat files are found by `query`. After Plan 02 ships, `query` will look in `.vrs/graphs/{hash}/graph.toon`. Any pre-existing flat-file graph is silently invisible to `query`. Agents running in environments where the old flat graph exists but no hash-subdir exists will get zero results — exactly the failure mode that triggered Plan 3.1c-12 Batch 1.
**Why:** The context explicitly lists "generic CLI queries return 0 results" as a bug to fix. Introducing a new path where `query` silently finds nothing (because the flat graph is not at the expected hash path) recreates the same failure for any operator who has not re-run `build-kg` after upgrading. This is especially likely during Plan 04 testing where testers may have residual flat graphs from earlier runs.
**How:** 
1. Add a backward compatibility assumption to CONTEXT: define the fallback read order — if `{hash}/graph.toon` does not exist, fall back to `graph.toon` (root flat file), log a deprecation warning, and return. This prevents silent zero-result failures without requiring a migration.
2. OR explicitly state that backward compatibility is NOT required (flat graphs are invalid/discarded), add a `build-kg --migrate` sub-command or migration step to Plan 02 scope, and update assumption 4 to say "NOT backward-compatible with flat graph files."
**Impacts:** Plan 02 scope (migration or fallback logic), Plan 03 (query must respect same fallback), Plan 04 (test setup must ensure clean state or old graphs).
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 — Cache invalidation fallback patterns are standard in build systems (Gradle, Maven, pip). The "log and fall back" approach is well-established.
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — The backward compatibility assumption in the domain is logically incomplete (it addresses build, not read). This gap exists in the original context.

### P1-IMP-09: GraphStore Caller Audit Is Missing — Existing Readers Assume Flat Path
**Target:** CONTEXT
**What:** The area brief notes the existing `GraphStore` API at `store.py L52` writes `graph{ext}`. The context does not list or enumerate callers that READ from that path. Without a caller audit, Plan 02 implementation risks changing the write path while leaving readers pointed at the old flat location, producing zero results. The number of callers is non-trivial given the codebase has ~12,000 LOC in `tools/` and ~6,400 in `orchestration/`.
**Why:** This is a prerequisite gap. Plan 02 says "build-kg produces isolated graphs per contract" but the `query` command, any orchestration module that loads graphs, and any test fixture that reads `.vrs/graphs/graph.toon` are all potentially broken by the path change. Without naming these callers, the plan cannot verify correctness by inspecting callers post-implementation.
**How:** 
1. Add to CONTEXT assumptions: "Before implementing Plan 02, audit all callers of `GraphStore.save()` and `GraphStore.load()` (and any direct `.vrs/graphs/` path references in `kg/`, `tools/`, `orchestration/`) and list them explicitly in the plan. Each caller must be updated to use hash-based paths or the new `GraphStore.load(contract_path)` API."
2. Add a done-criteria gate to Plan 02 intent: "grep for `.vrs/graphs` hardcoded strings returns zero results outside of `GraphStore` itself."
**Impacts:** Plan 02 scope (caller update), Plan 03 (query is one of the callers), Plan 04 (validation will catch regressions if callers are missed).
**Research needed:** no — this is a code audit, not research.
**Confidence:** HIGH
**Prior art:** 5 — Standard refactor discipline: change the write path, find all readers, update them. No novelty.
**Prerequisite:** no (audit is part of Plan 02 preparation, not a separate phase)
**Status:** implemented
**Origin:** NOVEL — Caller audit gap exists in the original context; not introduced by any prior pass.

### P1-IMP-10: Directory-Level vs File-Level Contract Path Creates Scope Ambiguity
**Target:** CONTEXT
**What:** The context says `build-kg` can be called with `.` (current directory). If the hash key is derived from a directory path, the resulting graph subdirectory stores a graph that covers multiple contracts. But the `query --graph` flag in Plan 03 is designed to target a specific contract's graph. If an agent ran `build-kg .` (directory hash) and then runs `query --contract contracts/Token.sol`, there is no graph at the Token.sol hash — only at the directory hash. The agent gets zero results.
**Why:** The design conflates two distinct use cases: single-contract isolation (the primary goal) and multi-contract directory builds (existing behavior). These need explicit handling or the feature is broken for the existing `build-kg .` workflow.
**How:** 
1. Add an explicit decision to CONTEXT: either (a) directory-level builds produce one graph per discovered contract file (one hash-subdir per .sol file), or (b) directory builds produce a single graph with a directory-level hash key, and `query` must be called without `--graph` or with the same directory path. Document which approach is chosen.
2. If approach (a): plan must address how contract files are discovered and iterated. If approach (b): plan must specify that `query` with `--graph <file>` falls back to the parent-directory hash if no file-level hash exists.
**Impacts:** Plan 02 (implementation scope changes significantly), Plan 03 (--graph flag semantics), Plan 04 (test cases must cover both scenarios).
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 2 — Jenkins/Bazel handle directory vs file hashing differently; no direct analog for this exact multi-contract CLI pattern.
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — Directory vs file path scope mismatch is a structural ambiguity in the current design that exists independently of any prior pass.

### P1-IMP-11: No Graph Listing or Cleanup Command Creates Operational Blindness
**Target:** CONTEXT
**What:** The area brief explicitly flags this. After Plan 02 ships, `.vrs/graphs/` will contain hash-named subdirectories like `a3f9c21d8b4e/`. There is no human-readable mapping from hash to contract path. Operators (and agents) debugging "why did my query return zero results?" cannot tell what graphs exist or which contract each hash maps to.
**Why:** Hash-based storage without a manifest or listing command is a standard antipattern. Every serious build cache (npm, Gradle, pip) includes a command to list, inspect, and prune cached artifacts. This is not a nice-to-have — it is required for the "interrogate agent failures and let retry" goal stated in domain assumption 6.
**How:** 
1. Add to Plan 02 scope in CONTEXT: `GraphStore` should write a sidecar `manifest.json` alongside each `graph.toon` that records `{"contract_path": "<realpath>", "built_at": "<iso8601>", "hash": "<12-char>"}`. This makes the store human-readable without additional commands.
2. Add to CONTEXT domain or Plan 02 intent: `alphaswarm graphs list` command (or equivalent) that reads all `manifest.json` files and prints a table of hash → contract path → build timestamp. This is the diagnostic tool that Plan 04 and operators will need.
**Impacts:** Plan 02 scope (manifest write), Plan 03 (query error messages can name the contract instead of the hash), Plan 04 (agents and testers can diagnose failures).
**Research needed:** no
**Confidence:** MEDIUM — The manifest approach is clearly correct; the specific command name and output format are design choices.
**Prior art:** 4 — Package cache manifests (npm's `package-lock.json`, pip's wheel cache metadata) are standard. Straightforward adaptation.
**Prerequisite:** no
**Status:** rejected
**Adversarial verdict:** REJECT (Path & Hash Determinism) — Human-readable manifest is a usability feature, not an execution blocker
**Origin:** NOVEL — Manifest/listing gap exists in the original context design; the area brief flags it explicitly as a missing consideration.

### P1-IMP-12: mtime Auto-Discovery is Silent-Corruption Risk in Concurrent Agent Context
**Target:** CONTEXT
**What:** The Plan 03 description states "auto-discovery of most recent graph by default" using mtime ordering. In the Agent Teams scenario (Plan 04), multiple agents build graphs for different contracts concurrently. Agent A builds Token.sol at T=0; Agent B builds Vault.sol at T=1; Agent A then queries without `--graph` and gets Vault's graph silently. This is worse than 0 results — it produces plausible but wrong answers with no error signal.
**Why:** mtime-based selection is non-deterministic under concurrency. The Plan 12 failure post-mortem (MEMORY.md) already documents that "shared graph state — sequential builds overwrite, queries return wrong contract data." The auto-discovery default extends this to query-time. The correct default is: no `--graph` flag = error if multiple graphs exist, not "pick the most recent." This forces agents to be explicit, which is the behavior the `--graph` flag is designed to produce anyway.
**How:** 
1. In the CONTEXT.md Plan 03 description, change "auto-discovery of most recent graph by default" to "error when multiple graphs exist and `--graph` is not specified; only auto-selects when exactly one graph is present in `.vrs/graphs/`."
2. Document the rationale: in Agent Teams context, silent wrong-graph selection is a correctness failure, not a usability degradation. The `--graph` flag should be the NORMAL path for agents, not an optional convenience.
**Impacts:** Plan 03 design; Plan 04 agents must pass `--graph` explicitly in smoke tests
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 — "fail loudly when ambiguous" is standard CLI design (git refuses ambiguous ref resolution, jq errors on ambiguous selectors)
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — The mtime fragility exists independently of any prior pass; it's a structural flaw in the stated design that the area brief itself flags as a primary concern.

### P1-IMP-13: --graph Flag Resolution Strategy is Undefined and Path-Dependent
**Target:** CONTEXT
**What:** The Plan 03 description says the `--graph` flag accepts "a specific contract path or graph directory" but does not specify how the CLI differentiates between them, or how it resolves a contract path to a graph subdirectory. Two concrete failure scenarios:
- Agent runs `--graph contracts/Token.sol` from project root. Graph was built from Jujutsu worktree path `/tmp/jj-ws-abc/contracts/Token.sol`. The SHA-256 of these paths differs — the lookup returns "graph not found" even though the graph exists.
- Agent runs `--graph .vrs/graphs/abc123/` — this works. But agents don't know the hash, so they'd have to run a separate discovery command first.
This ambiguity means Plan 04's smoke tests cannot be specified concretely until this resolution strategy is defined.
**Why:** Without an explicit resolution contract, plan authors and agent prompt authors are guessing. The worktree path mismatch is guaranteed to occur — Plan 04 tests explicitly use Jujutsu-isolated workspaces, which have different absolute paths than the project root. If the hash is computed from the absolute path, worktree builds and project-root queries will never match.
**How:** 
1. Add to CONTEXT Plan 03 description: specify that `--graph` accepts EITHER (a) a graph subdirectory path (`.vrs/graphs/<hash>/`) used directly, OR (b) a contract filename stem (e.g., `Token`) that is matched against graph metadata (a `source_contract` field stored at build time in `.vrs/graphs/<hash>/meta.json`). The filename stem approach is path-agnostic and survives worktree moves.
2. Add to CONTEXT Plan 02 description (cross-area concern — note only): the `meta.json` written per graph subdirectory must include a `source_contract` field containing the filename stem (not the full path) so Plan 03's stem-based lookup works.
**Impacts:** Plan 03 design; Plan 02 deliverable (meta.json content); Plan 04 agent prompts
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3 — Package manager lockfiles store filename-based keys for exactly this reason (npm package names vs filesystem paths); this pattern is well-known but needs adaptation to the graph-hash context
**Prerequisite:** no — AUTO-FIX: CONTEXT items can always be written — Plan 02 must define meta.json structure before Plan 03's resolution strategy can be implemented
**Status:** implemented
**Origin:** NOVEL — The path-mismatch failure under Jujutsu worktrees would exist regardless of prior passes; it's a concrete gap between "accepts contract path" and "graphs built in worktrees."

### P1-IMP-14: Error Message Specification Gap — Agents Cannot Act on Unspecified Errors
**Target:** CONTEXT
**What:** The Plan 03 description says "clear error when patterns unavailable instead of silent degradation to raw node search." It does not specify: (a) what the error message text is, (b) what exit code is used, or (c) what command the agent should run to recover. The Plan 12 failure (MEMORY.md) documents that agents given 0 results fell back to raw Python imports. An error that says "Error: no patterns matched" without a recovery path produces the same outcome — agents will try something else (Python imports) rather than knowing to re-run with `--graph`.
**Why:** Agent prompts are written assuming specific CLI behavior. If the error message is unspecified at the CONTEXT level, the implementer will write something reasonable but not optimized for agent consumption. The recovery path ("run `alphaswarm query --graph <name> <query>` to target a specific contract") must be in the error message itself because agents cannot consult docs. This is a plan-level specification gap that will cause Plan 04's smoke tests to be underspecified too.
**How:** 
1. Add to CONTEXT Plan 03 description: specify the error message format for the two failure cases:
   - Multiple graphs exist, no `--graph` flag: `"Error: multiple graphs found in .vrs/graphs/ — use --graph <contract-name> to target one. Available: Token, Vault, MasterChef"`
   - Pattern query fails, patterns unavailable: `"Error: vulndocs patterns not found (run from project root or pass --vulndocs <path>). Raw node query: use --mode=raw flag to search without patterns."`
2. Specify that both error paths exit with code 1 (not 0), so agent orchestrators can detect failure without parsing stderr.
**Impacts:** Plan 03 implementation; Plan 04 agent prompt design (prompts can tell agents what errors to expect and how to respond)
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 — Actionable error messages with recovery commands are standard CLI UX (git's "did you mean X?", cargo's "try running Y")
**Prerequisite:** no
**Status:** implemented
**Adversarial verdict:** ENHANCE (Agent Protocol Coherence) — Core claim correct; errors must embed exact recovery command as executable text, not just prose
**Origin:** NOVEL — The gap between "clear error" and "agent-actionable error" exists in the original CONTEXT.md; no prior passes introduced it.

### P1-IMP-15: Missing Hard Dependency Declaration on Plans 01 and 02
**Target:** CONTEXT
**What:** The Plan 03 description notes "builds on Plan 01 + 02 deliverables" in the confidence line but does not declare these as hard sequential dependencies. Plan 03's pattern-based query fix is entirely useless if Plan 01 (vulndocs resolution) is not complete — queries will still fail silently because the patterns won't load. Plan 03's `--graph` targeting is meaningless if Plan 02 (per-contract graph subdirs) is not complete — there are no per-contract subdirs to target.
**Why:** A "confidence" annotation is not an execution dependency. If Plans 01-03 are assigned to parallel implementation waves, Plan 03 will be implemented against the old flat graph structure and the wrong vulndocs resolution. This is a sequencing risk. The dependency needs to be explicit in CONTEXT so the planner encodes it in the PLAN.md `depends_on` field.
**How:** 
1. In CONTEXT Plan 03 entry, add an explicit "depends_on: [Plan 01, Plan 02]" annotation (or equivalent language making the sequential requirement unambiguous).
2. Annotate specifically what each dependency provides: Plan 01 provides pattern loading that makes query routing meaningful; Plan 02 provides the graph directory structure that `--graph` targets.
**Impacts:** Plan 03 wave assignment; Plan 04 (which depends on 03, transitively on 01+02)
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5 — Sequential dependency declaration is standard planning practice
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — The implicit vs explicit dependency gap exists in the original CONTEXT.md.

### P1-IMP-16: Interrogation Protocol Is Completely Undefined
**Target:** CONTEXT
**What:** The domain section states the user's requirement: "Do NOT shut down failing
agents — interrogate them: ask WHY, what's broken, how to fix. Give them solutions,
let them retry." But nowhere in the Plan 04 description does the CONTEXT capture the
protocol for this. It is not specified WHO sends the interrogation message (the
orchestrator? a dedicated teammate?), WHAT the interrogation message contains (a
fixed template? dynamic based on error class?), WHERE the answer is stored (obs file?
inline in transcript?), WHEN to stop retrying (max attempts? specific signal from
agent?), and HOW the solution is delivered back to the agent (SendMessage? new task?).
Without this, any PLAN.md authored for Plan 04 will leave the executor to invent the
protocol at runtime — meaning every executor produces a different protocol, and Plan 05's
"mandate" propagates an undefined standard.
**Why:** The "interactive debugging" approach is the core value proposition of Plan 04.
It is also completely novel (prior art 2/5). If the protocol isn't captured in CONTEXT
before planning, the plan tasks will say things like "interrogate failing agents" with
no actionable specification. That makes done-criteria unverifiable: you cannot check
"interrogation happened correctly" without knowing what correct interrogation looks like.
This is a structural gap, not a cosmetic one — it will cause executor confusion and
protocol drift across downstream phases.
**How:** 
1. Add a subsection "Interrogation Protocol" under Plan 04's domain description in
   CONTEXT.md. Specify: (a) Orchestrator reads failure signal from `get_team_observation`
   output; (b) Orchestrator sends `SendMessage` with a fixed template covering: what
   command was attempted, what error appeared in transcript, and explicit question "what
   would you need to succeed?"; (c) Agent response is stored as a separate observation
   file `obs/interrogation-{agent_id}-{attempt}.json` alongside the original obs file;
   (d) Retry limit = 3 attempts per agent before escalating to orchestrator analysis;
   (e) Escalation means orchestrator documents the failure class and does NOT retry.
2. Add a "Failure Classes" taxonomy to the same subsection with at least: (a)
   CLI-not-found (agent cannot invoke alphaswarm binary), (b) zero-results (query
   returns empty), (c) wrong-graph (query returns data for a different contract),
   (d) python-fallback (agent imports Python modules directly). Each class should map
   to a distinct interrogation message template.
**Impacts:** Plan 04 confidence stays MEDIUM but becomes plannable. Plan 05 inherits
a concrete protocol to mandate across phases.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 1 — Interactive LLM agent interrogation loops have no established
protocol in the Agent Teams context. Some analogy to RLHF feedback loops but not
directly applicable.
**Prerequisite:** no
**Status:** reframed
**Adversarial verdict:** REFRAME (Agent Protocol Coherence) — Full protocol spec premature; minimum viable scaffold (3 questions + storage) is what blocks execution
**Origin:** NOVEL — this gap exists in the original CONTEXT.md independent of any
prior improvement passes.

### P1-IMP-17: Transcript Analysis Criteria Are Underspecified
**Target:** CONTEXT
**What:** The Plan 04 description says "transcript analysis confirming CLI usage" without
defining what "confirming" means. The area brief correctly identifies the ambiguity:
is it presence of `alphaswarm build-kg` in bash_tool_calls? Absence of
`from alphaswarm_sol` imports? Both? What about agents who find a third path (e.g.,
calling the binary via a shell script)? The CONTEXT says "read transcripts ALWAYS to
know exactly what agents are doing" but gives no criteria for what the reader is looking
for.
**Why:** Transcript analysis is the primary verification mechanism for Plan 04. If the
criteria are vague, the done-criterion "transcript analysis confirming CLI usage" is
unfalsifiable — an executor can read the transcript and claim confirmation regardless
of what they saw. This is a verification gap that makes Plan 04's done criteria
unobservable from disk artifacts.
**How:** 
1. Add a "CLI Usage Confirmation Criteria" definition to the Plan 04 section in
   CONTEXT.md with three binary checks: PASS requires ALL of: (a) at least one
   `bash` tool call containing the string `alphaswarm build-kg` or `alphaswarm query`,
   (b) zero occurrences of `from alphaswarm_sol` or `import alphaswarm_sol` in any
   bash tool call or code block, (c) the command's output contains a non-empty result
   (not just a 0-byte response or "No results found"). Agents passing all three = CLI
   CONFIRMED. Agents failing any = INTERROGATION TRIGGERED.
2. Add an explicit "anti-patterns to flag" list: (a) agent reads Python source directly
   via Read tool on .py files in the CLI package, (b) agent constructs KnowledgeGraph
   objects in Python code blocks, (c) agent says "I will use Python to query" before
   attempting CLI. These anti-patterns should also trigger interrogation even if the
   agent eventually uses CLI.
**Impacts:** Plan 04 PLAN.md verification tasks become disk-observable. Plan 05
inherits concrete pass/fail criteria for its mandate.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 2 — Static analysis of LLM tool call transcripts has precedent in the
existing AgentExecutionValidator (12-check system), but the specific CLI-vs-Python
discrimination criteria are not yet defined there.
**Prerequisite:** no
**Status:** implemented
**Adversarial verdict:** ENHANCE (Agent Protocol Coherence) — Three checks confirm CLI was called but not that RIGHT graph was queried; fourth check needed
**Origin:** NOVEL — this gap is in the original CONTEXT.md and would be visible on
first read.

### P1-IMP-18: Circular Dependency — Framework Infrastructure Validated by Agents It Manages
**Target:** CONTEXT
**What:** The Plan 04 description states this plan "validates both the CLI fixes AND
the interactive testing approach." But the testing approach relies on WorkspaceManager
(Jujutsu workspace creation), TeamManager (Agent Teams lifecycle), and EvaluationRunner
(8-stage pipeline). If WorkspaceManager fails to create a workspace, the agent never
starts. If TeamManager fails to spawn a teammate, there is no transcript to read. The
CONTEXT acknowledges these dependencies exist but does not acknowledge the failure modes:
what happens when the infrastructure being validated is itself broken? The plan has no
pre-validation step for the framework components before agent spawning begins.
**Why:** This is a concrete failure scenario: WorkspaceManager calls `jj workspace add`
which requires jujutsu to be installed. If jujutsu is not installed (or the version is
wrong, or the working directory is already a workspace), WorkspaceManager raises an
exception. The agent never spawns. The executor is now debugging infrastructure, not
CLI behavior. Without a pre-validation step, Plan 04 cannot distinguish "CLI is broken"
from "WorkspaceManager is broken" — both appear as "agent didn't run."
**How:** 
1. Add a "Framework Pre-Validation" step to the Plan 04 description in CONTEXT.md:
   before spawning any Agent Team, run a lightweight smoke test of each infrastructure
   component: (a) WorkspaceManager: create a workspace, verify the directory exists,
   immediately tear it down; (b) TeamManager: create a team with a single echo agent
   (agent that just returns "hello"), verify the observation is parseable; (c)
   EvaluationRunner: run the pipeline on a synthetic transcript with known properties,
   verify the pipeline produces expected stage outputs. Only proceed to CLI agent
   spawning if all three pass.
2. Add a "Framework vs CLI Failure Disambiguation" note: if the pre-validation step
   passes but agents fail, the failure is CLI/graph related. If pre-validation fails,
   the failure is infrastructure — stop, fix infrastructure, do not proceed to agent
   spawning. This distinction must be in the PLAN.md done criteria.
**Impacts:** Plan 04 gains a prerequisite verification step that prevents false negatives.
Plan 05's mandate is stronger because it can reference "pre-validate framework before
agent work" as a step.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 1 — No established pattern for self-validating testing framework
infrastructure in this Agent Teams context.
**Prerequisite:** no — AUTO-FIX: CONTEXT items can always be written — jujutsu must be installed and accessible in the PATH where
the orchestrator runs. This must be stated as an explicit prerequisite in the plan.
**Status:** implemented
**Origin:** NOVEL — the circular dependency is a structural property of Plan 04's
design and would be visible on first careful reading of the CONTEXT.

### P1-IMP-19: No Failure-Information Contract Between Agents and Orchestrator
**Target:** CONTEXT
**What:** The user's requirement is "agents help build a better testing framework and
improve CLI, tools, graph, everything — interactive improvement by self-debugging
teammates using reasoning." This implies agents produce structured diagnostic output
that the orchestrator can act on. But the CONTEXT has no definition of what that
diagnostic output looks like. An agent that fails to query the CLI could say "the
command failed" (useless) or it could say "I ran `alphaswarm query 'reentrancy'` from
`/tmp/workspace-abc` and got exit code 1 with stderr: `ModuleNotFoundError: No module
named vulndocs`" (actionable). The CONTEXT gives no guidance on what level of
diagnostic detail agents are expected to produce.
**Why:** The "self-debugging teammates using reasoning" model only works if agents
produce information-dense failure reports. If agents just report "it failed," the
orchestrator cannot distinguish Plan 01 failures (vulndocs resolution) from Plan 02
failures (graph cross-contamination) from Plan 03 failures (query routing). The
entire value proposition of interactive debugging — that agents help IDENTIFY what to
fix — collapses into "something is broken, we don't know what."
**How:** 
1. Add a "Diagnostic Output Contract" to Plan 04's domain section in CONTEXT.md:
   agents are expected to report failures using a minimum structure: (a) exact command
   attempted (full shell command with arguments), (b) working directory at time of
   command (output of `pwd`), (c) exit code, (d) full stderr, (e) first 500 chars of
   stdout, (f) agent's hypothesis about root cause. Orchestrator prompts for this
   structure if the agent's first failure report omits it.
2. Add an explicit note that agents should NOT try to "fix" the CLI themselves
   (e.g., by modifying Python source) — their role is diagnosis and reporting. The
   orchestrator takes the diagnostic output and decides whether to deliver a solution
   (which may include patching Plans 01-03 and retrying) or escalate.
**Impacts:** Plan 04's interrogation loop becomes concrete. Downstream phases that
use Agent Teams debugging know what diagnostic format to expect.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 0 — No prior art for a structured failure-information contract between
Agent Teams teammates and their orchestrator in this framework.
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — this is a fundamental gap in the interactive debugging model
described in the domain.

### P1-IMP-20: Jujutsu Workspace Isolation Has Unacknowledged Git Prerequisite
**Target:** CONTEXT
**What:** The domain section and Plan 04 description refer to "Jujutsu-isolated
workspaces" as the isolation mechanism. Jujutsu (`jj`) workspaces require the
underlying repository to be a jujutsu repository — not just a git repository. The
git status shows `Is directory a git repo: Yes` but does not indicate whether jujutsu
is co-located. If the repo is a standard git repo (not `jj git init --git-repo`),
then `jj workspace add` fails with "not a jujutsu repository." The CONTEXT and Plan 04
never state this prerequisite explicitly.
**Why:** This is a concrete failure scenario: executor runs Plan 04 in a git-only repo,
WorkspaceManager calls `jj workspace add`, gets "not a jujutsu repository," and the
entire workspace isolation strategy fails before a single agent is spawned. The CONTEXT
needs to either (a) state the jujutsu prerequisite explicitly with a check command,
or (b) acknowledge that the workspace isolation may need a git-worktree fallback if
jujutsu is unavailable.
**How:** 
1. Add a "Workspace Isolation Prerequisites" section to the Plan 04 description in
   CONTEXT.md: list (a) jujutsu must be installed (`jj --version` succeeds), (b) the
   repository must be a jujutsu co-located repo (`jj status` succeeds from the repo
   root), (c) if jujutsu is not available, the fallback is `git worktree add` with
   the same directory structure. The fallback must be noted as "reduced isolation"
   since git worktrees share the index.
2. Add a preflight check task to Plan 04's future PLAN.md: the first task must run
   `jj status` and verify it succeeds before any workspace creation. If it fails,
   the task must surface a clear error message directing the executor to either
   install jujutsu or use the git-worktree fallback path.
**Impacts:** Plan 04 becomes executable in repos that haven't been jujutsu-initialized.
Plan 03 and Plans 01-02 are unaffected (they don't use workspace isolation).
**Research needed:** no — jujutsu workspace semantics are well-documented.
**Confidence:** HIGH
**Prior art:** 4 — git worktree and jujutsu workspace semantics are well-established.
The gap is failure to state the prerequisite, not ignorance of the technology.
**Prerequisite:** no — AUTO-FIX: CONTEXT items can always be written — either jujutsu or git worktree support must be verified before
Plan 04 begins.
**Status:** implemented
**Origin:** NOVEL — this prerequisite gap exists in the original CONTEXT.md and is
not derivative of any prior improvement.

### P1-IMP-21: "Smoke Test" Scope Is Undefined — Success Threshold Not Stated
**Target:** CONTEXT
**What:** Plan 04 is called "CLI Isolation Smoke Tests." The description says agents
run `build-kg` + `query` on test contracts. But the CONTEXT does not define what
"smoke test passing" means: Does one agent succeeding on one contract count? All
agents on all contracts? Some minimum fraction? The description also does not name
which test contracts are used, nor specify whether the smoke tests must cover all
three failure classes from Plan 3.1c-12 Batch 1 (vulndocs resolution, graph
cross-contamination, query routing).
**Why:** A smoke test with an undefined pass/fail threshold is not a smoke test — it
is an observation session. Without a threshold, an executor can declare "smoke tests
passed" after one agent runs one successful query. The three failure classes from
Batch 1 are the MOTIVATION for this plan — if the smoke tests don't specifically
target those failure classes, the plan does not validate what it claims to validate.
**How:** 
1. Add a "Smoke Test Definition" to Plan 04's description: specify the minimum
   required coverage as: (a) at least 2 distinct test contracts (one simple, one
   complex), (b) at least 1 `build-kg` run per contract from within a Jujutsu
   workspace, (c) at least 3 distinct CLI queries per contract targeting known
   vulnerability patterns, (d) at least 1 concurrent build scenario (two agents
   building different contracts simultaneously) to validate Plan 02's graph isolation.
   All agents must pass CLI confirmation criteria (from IMP-02) for the smoke test to PASS.
2. Add a "Smoke Test Contracts" list: name the specific contracts to use (e.g.,
   `tests/contracts/reentrancy_simple.sol` and one complex contract with access
   control patterns). This prevents executor confusion about which contracts are
   appropriate for smoke testing.
**Impacts:** Plan 04's done criteria become falsifiable. Plan 05 can mandate a
specific smoke test standard for other phases.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3 — Smoke test pass/fail thresholds are a standard testing concept;
applying them to Agent Teams transcript analysis is the novel part.
**Prerequisite:** no
**Status:** implemented
**Adversarial verdict:** ENHANCE (Agent Protocol Coherence) — Scope reasonable but lacks regression coverage of Batch 1 concurrent-contamination failure class
**Origin:** NOVEL — the undefined threshold is present in the original CONTEXT.md
description.

### P1-IMP-22: Dependency on Plans 01-03 Is Sequential But Not Stated as a Hard Gate
**Target:** CONTEXT
**What:** The "other_areas" summary explicitly states Plan 04 depends on Plans 01, 02,
and 03 (agents need vulndocs resolved, isolated graphs, and working queries). However,
the CONTEXT's Plan 04 description does not state that Plans 01-03 must be COMPLETE
(not just started) before Plan 04 begins. The domain section frames this as a
validation phase, but does not make the dependency explicit enough to gate execution.
**Why:** Concrete failure scenario: an executor starts Plan 04 before Plan 01 is
merged, spawns agents, agents fail because vulndocs path is still broken, and the
executor now cannot distinguish "CLI still needs fixing" from "the fix regressed."
The smoke tests produce ambiguous results. The executor interrogates agents who report
a real bug that Plan 01 was supposed to fix — wasting an entire Agent Teams session
on already-known issues.
**How:** 
1. Add a "Hard Prerequisites" block to Plan 04's CONTEXT description: "Plans 01, 02,
   and 03 must be MERGED (not just drafted) before Plan 04 execution begins. Verify
   by running: (a) `alphaswarm build-kg tests/contracts/ --vulndocs auto` succeeds
   from a non-project directory, (b) two concurrent builds produce isolated graphs,
   (c) `alphaswarm query --graph <id> 'reentrancy'` returns results." If any of
   these pre-checks fail, stop and fix the upstream plan — do not proceed to agent
   spawning.
2. Add the dependency to Plan 04's metadata as `depends_on: [Plan-01, Plan-02, Plan-03]`
   to make the dependency machine-readable for the planning system.
**Impacts:** Plan 04 gains a concrete "ready to start" checklist. Prevents wasted
Agent Teams sessions on already-known bugs.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5 — Dependency gating is standard practice. The gap is the CONTEXT
not stating it explicitly.
**Prerequisite:** no
**Status:** rejected
**Adversarial verdict:** REJECT (Agent Protocol Coherence) — Redundant with IMP-15; accepting both creates maintenance overhead without enforcement gain
**Origin:** NOVEL — the missing hard dependency gate exists in the original CONTEXT.md.

### P1-IMP-23: Testing Exit Criteria Are Undefined — "Mandate" Has No Teeth
**Target:** CONTEXT
**What:** The domain section states "Every future phase MUST: Use Agent Teams in Jujutsu workspaces for validation, Read transcripts and verify tool usage, Treat agent failures as feedback not just errors, Reference the testing framework docs in their contexts" — but none of these are *measurable*. "Use Agent Teams" doesn't say how many sessions, what pass rate, what checks, or who verifies it before the phase gate closes. The plan says "testing requirements as exit criteria" but never defines what a passing exit criterion looks like. Without operational definitions, this mandate is a checklist that future Claude sessions will satisfy by running a single agent session and calling it done.
**Why:** The v5.0 anti-pattern the user explicitly named — "building without proving" — was not caused by *absence* of a testing requirement. It was caused by testing requirements that were vague enough to satisfy with minimal effort. Repeating "you must use the testing framework" without specifying a concrete threshold reproduces the same structural failure at the mandate level. A governance doc that can be satisfied trivially provides false assurance.
**How:** 
1. In the CONTEXT.md for this phase, add a "Cross-Phase Exit Gate Template" section that defines the minimum bar per phase type: (a) for code phases — N >= 3 Agent Team sessions in Jujutsu workspaces, AgentExecutionValidator passes all 12 checks, at least 1 red-path session (deliberate failure to confirm detection works); (b) for evaluation phases — dual-Opus evaluator scores must be logged, no 100% pass rate accepted without fabrication investigation trigger; (c) for framework/infrastructure phases — regression test shows no score degradation from prior baseline.
2. Require that every updated CONTEXT.md include a `### Testing Gate` section with: (i) phase type (code/eval/framework), (ii) minimum sessions, (iii) required validator checks, (iv) explicit acceptance criterion (not "tests pass" but "AgentExecutionValidator exits 0 on all 12 checks for all sessions").
**Impacts:** Plan 05 scope — currently undefined, would become defined
**Research needed:** no — the testing framework already specifies its checks; the work is choosing thresholds per phase type
**Confidence:** HIGH
**Prior art:** 1 — No direct prior art for cross-phase testing mandates in this framework; analogous to Definition of Done in mature agile teams but applied to AI agent evaluation phases
**Prerequisite:** no — Plan 04 demonstrates the protocol; Plan 05 just needs to codify minimum bars
**Status:** implemented
**Adversarial verdict:** ENHANCE (Governance Architecture) — Gate template correct but forward-depends on taxonomy (IMP-27); narrowed to min-sessions + score-threshold + verifier triad
**Origin:** NOVEL — this gap exists regardless of whether any prior improvement pass ran; the domain section defines a mandate without defining what compliance looks like

### P1-IMP-24: Future Phase CONTEXT.md Files Don't Exist — Plan Creates Documents for Phases That Are Vaporware
**Target:** CONTEXT
**What:** The plan lists these phases to update: 3.1c.2, 3.1f, 3.2, 4, 4.1, 5, 6, 7, 8. Of these, phases 4, 4.1, 5, 6, 7, 8 are described in ROADMAP as "PLANNED" — they have no CONTEXT.md files and their domains are not yet defined. The plan says "Updated CONTEXT.md files for phases 3.1c.2, 3.1f, 3.2, 4, 4.1, 6, 7, 5, 8 with testing framework requirements as exit criteria." Creating CONTEXT.md files for phases 4-8 requires knowing what those phases DO — which is not determined. The "mechanical" framing in the plan confidence note is incorrect for the far-future phases.
**Why:** Writing testing mandates into CONTEXT.md files for phases whose domain is undefined inverts the design process. The testing mandate for a phase should derive from what the phase builds. If phase 8 ends up being about documentation or benchmarking, the mandate for "N Agent Team sessions in Jujutsu workspaces" may be completely wrong. Creating placeholder CONTEXT.md files with testing mandates that were authored before the phase domain is known creates governance debt: future planners either ignore the mandate (it doesn't fit) or comply with it meaninglessly. Either outcome wastes the effort of this plan.
**How:** 
1. Split the target list into two tiers: Tier 1 (near-term, domain known) = 3.1c.2, 3.1f, 3.2; Tier 2 (far-future, domain unknown) = 4, 4.1, 5, 6, 7, 8. For Tier 1, do full CONTEXT.md updates with specific testing gates. For Tier 2, update ROADMAP.md only — add a "Testing Mandate Template" block that any future phase CONTEXT.md must include when it is first authored, rather than pre-creating placeholder files.
2. Add a ROADMAP.md section titled "Phase Authoring Requirements" that says: "Any new CONTEXT.md for phases 4+ MUST include a `### Testing Gate` section as defined in the 3.1c.1 testing mandate. The phase planner is responsible for adapting the gate to the phase domain before any plan is authored." This is enforcement without premature lock-in.
**Impacts:** Plan 05 scope reduced for far-future phases; ROADMAP.md becomes the enforcement point instead of pre-created files
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 2 — Definition of Done templates in project charters; pre-creating governance docs for unknown domains is an anti-pattern in PM practice
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — the phase list includes undefined phases; this structural problem is visible from the domain section alone

### P1-IMP-25: 3.1c.2 Is a Testing Infrastructure Phase — Mandating Testing for a Testing Phase Creates Unresolvable Recursion
**Target:** CONTEXT
**What:** Phase 3.1c.2 is "Agent Evaluation Harness Hardening." Its purpose is to improve the testing framework itself. The cross-phase mandate says this phase must "Use Agent Teams in Jujutsu workspaces for validation" and "Reference the testing framework docs." But if 3.1c.2 is modifying the EvaluationRunner, TeamManager, or AgentExecutionValidator, then running those same tools for validation creates a bootstrap problem: the tools being fixed are the tools used to prove the fix works. A broken intermediate state of AgentExecutionValidator cannot reliably validate itself. The plan does not acknowledge this.
**Why:** This is a concrete failure scenario, not a vague concern. Specific case: 3.1c.2 modifies the 12-check validation logic in AgentExecutionValidator to fix a false-positive in check #7. The exit criterion "AgentExecutionValidator passes all 12 checks" is now ambiguous — does it pass because the fix is correct, or because the check was relaxed? The mandate cannot distinguish these cases. Running the harness-under-repair as the validation tool for the harness-repair is circular.
**How:** 
1. Add an explicit exemption/adaptation clause to the cross-phase mandate in CONTEXT.md: "Phases that modify testing infrastructure (3.1c.2 and any future framework-improvement phases) MUST use a snapshot of the testing framework from BEFORE the phase's changes for their acceptance validation run — not the modified version. This snapshot run is the exit gate, not a run using the work-in-progress tools."
2. For 3.1c.2 specifically, the testing gate should be: run the PRE-3.1c.2 AgentExecutionValidator against 3 agent sessions to establish baseline, apply 3.1c.2 changes, run POST-3.1c.2 version against same sessions and diff results — both runs documented, no regression in any prior-passing check.
**Impacts:** Plan 05 — requires adding the adaptation clause before updating 3.1c.2's CONTEXT.md; Plan 04 (cross-area concern only, not proposing fix)
**Research needed:** no — this is a logical consequence of the phase's domain
**Confidence:** HIGH
**Prior art:** 1 — Analogous to "don't use the compiler under test to compile itself" (bootstrap problem in compiler construction); adapting this to AI evaluation harnesses is novel
**Prerequisite:** no
**Status:** implemented
**Adversarial verdict:** ENHANCE (Governance Architecture) — Bootstrap paradox real but snapshot unactionable without naming artifact; requires stored baseline.json
**Origin:** NOVEL — the recursion problem is inherent to 3.1c.2's domain and would be visible to any reviewer reading the phase list

### P1-IMP-26: No Enforcement Mechanism — Mandate Lives in Docs Claude Will Skip
**Target:** CONTEXT
**What:** The plan's delivery is "Updated CONTEXT.md files... with testing framework requirements as exit criteria" and "testing governance section in each phase boundary." Claude Code sessions load CONTEXT.md for planning, but there is no structural enforcement that prevents a future planning session from simply not running the testing gate. The CONTEXT.md of a future phase is read-only reference — if a planner (or the user under deadline pressure) decides to skip it, nothing stops them. The domain section acknowledges the user was "emphatic" — but emphasis in a comment does not prevent drift over a 6-month project timeline.
**Why:** The specific failure mode: Phase 3.2 planning session starts. Claude Code reads the updated CONTEXT.md. User says "let's just focus on getting the first audit working, we'll add testing later." Claude complies. The testing mandate in the CONTEXT.md is read but not enforced. The phase proceeds without the required Agent Team sessions. This is not a hypothetical — it's the exact pattern that produced the v5.0 anti-pattern. Governance documents without enforcement are aspirational, not operational.
**How:** 
1. Add a machine-readable enforcement hook: in each updated CONTEXT.md, include a `### Testing Gate` section in a structured format (YAML block or key-value) that the `/msd:plan` command (or equivalent) can check before approving a phase as complete. The format should be parseable by a simple grep or jq query — not free prose. Example: `testing_gate: {type: code, min_sessions: 3, required_checks: [AgentExecutionValidator-all-12], acceptance: validator_exit_0}`.
2. Update STATE.md or ROADMAP.md with a policy: "A phase is NOT complete until its Testing Gate section documents the actual run results — session IDs, validator output, and timestamp. Plans that skip this step are REJECTED at phase close." This makes the gate observable and auditable, not just aspirational.
**Impacts:** Plan 05 — adds structural format requirement to what was prose-only governance; also requires defining the STATE.md/ROADMAP.md policy update as part of Plan 05's deliverables
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 2 — CI/CD required status checks; pre-merge gates in GitHub; adapted here to Claude Code planning sessions which have no native gate mechanism
**Prerequisite:** no — ROADMAP.md and STATE.md already exist and are read by planning sessions
**Status:** reframed
**Adversarial verdict:** REFRAME (Governance Architecture) — Machine-readable CONTEXT.md is still advisory; real enforcement is in plan task done criteria
**Origin:** NOVEL — the enforcement gap exists regardless of how well the mandate is written

### P1-IMP-27: "Domain-Adaptive" Testing Is Claimed but Not Designed
**Target:** CONTEXT
**What:** The area brief correctly identifies that different phases have very different domains (code phases, evaluation phases, agent design phases, benchmarking phases) and that "the testing mandate must be domain-adaptive, not one-size-fits-all." The domain section lists the same four requirements for all phases with no adaptation. "Use Agent Teams in Jujutsu workspaces" is meaningful for a code implementation phase. For a phase that is about VulnDocs authoring or documentation, it is not meaningful at all. The plan offers no taxonomy of phase types or corresponding testing requirements.
**Why:** Concrete failure scenario: Phase 5 (in ROADMAP, labeled as a benchmarking/metrics phase based on surrounding phases). Its domain involves running the audit pipeline against known-vulnerable contracts and measuring detection rates. The testing mandate says "Use Agent Teams in Jujutsu workspaces." There are no agents to evaluate in a benchmarking run — the output IS the benchmark numbers. A planner for Phase 5 will either (a) create a fake Agent Team session to satisfy the mandate, (b) skip the mandate and note it doesn't apply, or (c) argue it's satisfied by the benchmark run itself. None of these produce the intended testing discipline. The mandate fails because it's not domain-adaptive.
**How:** 
1. Define a phase type taxonomy in CONTEXT.md with at minimum 3 types and their corresponding testing requirements: (a) CODE phases (implementing Python/Solidity) → Agent Teams + AgentExecutionValidator; (b) EVALUATION phases (running agent sessions and measuring quality) → dual-Opus evaluator + fabrication checks + baseline comparison; (c) FRAMEWORK phases (changing the testing infrastructure itself) → snapshot-before/after diff + regression on prior baselines. Each updated phase CONTEXT.md must declare its type.
2. Add a fourth type: SYNTHESIS phases (VulnDocs, documentation, patterns) → human review checklist + pattern validation CLI pass, no Agent Teams required. This prevents forcing an inappropriate mandate on documentation work while still requiring structured validation.
**Impacts:** Plan 05 — significantly expands the design work required (currently framed as "mechanical" updates); raises confidence concern about whether Plan 05 is sized correctly for one plan
**Research needed:** no — the taxonomy is derivable from the existing phase list in ROADMAP
**Confidence:** HIGH
**Prior art:** 1 — Test strategy adaptation per artifact type is a known concept (unit vs integration vs system) but applying it to AI evaluation phases with Jujutsu workspaces is novel
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — the absence of a phase type taxonomy is a structural gap in the mandate design, visible from the domain section's flat list of requirements

### P1-IMP-28: Plan 05 Is Undersized for Its Scope — Should Be Split
**Target:** CONTEXT
**What:** Plan 05 is described as a single plan that delivers: (1) updated CONTEXT.md for 9 phases, (2) updated ROADMAP.md, (3) testing governance section in each phase boundary, (4) a cross-phase testing policy. Given findings P1-IMP-01 through P1-IMP-05, the actual work is: define a phase type taxonomy (new design work), write the phase-specific testing gates per type (design + authoring), update 3 near-term CONTEXT.md files with specific gates (authoring), update ROADMAP.md with a template and policy (authoring), and explicitly handle the 3.1c.2 bootstrap exception (design). This is 2-3 distinct efforts: (a) governance design (what does compliance look like per phase type?) and (b) governance rollout (apply the design to existing phase files). Combining design and rollout in one plan means the plan executes before the design is validated.
**Why:** Concrete failure: Plan 05 executor starts updating 3.1f CONTEXT.md with testing requirements. Halfway through, the executor realizes the phase type taxonomy doesn't cover 3.1f's domain (it's a "proven loop closure" phase — partially code, partially evaluation). The plan has no guidance. The executor makes a judgment call, the output is inconsistent with 3.2's update, and the mandate has internal contradictions from day one. This is a sequencing failure caused by conflating design with execution.
**How:** 
1. Split Plan 05 into Plan 05a (Governance Design): define phase type taxonomy, write the Testing Gate Template, define minimum bars per type, handle the 3.1c.2 exception, define the ROADMAP.md "Phase Authoring Requirements" section. Deliverable: a single document (e.g., `.planning/testing/TESTING-MANDATE.md`) that all subsequent updates reference. Estimated size: focused, ~1 day of work.
2. Plan 05b (Mandate Rollout): apply Plan 05a's taxonomy and gates to the 3 near-term phases (3.1c.2, 3.1f, 3.2), update ROADMAP.md with the policy and template. Far-future phases (4+) get ROADMAP.md template only, not pre-created CONTEXT.md files. Estimated size: mechanical once 05a exists, ~half day.
**Impacts:** Requires adding Plan 05a and renaming current Plan 05 to Plan 05b; adds a dependency (05b depends on 05a); resolves the "design before execution" sequencing problem
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 2 — Design-then-implement sequencing is standard; the novel part is applying it to a cross-phase AI testing mandate
**Prerequisite:** no — AUTO-FIX: CONTEXT items can always be written — Plan 05a must complete before Plan 05b begins; Plan 05a itself has no prerequisites within this phase
**Status:** implemented
**Origin:** NOVEL — the plan's conflation of design and rollout is a structural problem visible from the scope description

### P1-IMP-29: "Improve the Testing Framework" Mandate Has No Direction — What Kind of Improvement?
**Target:** CONTEXT
**What:** The user stated: "every phase must use AND IMPROVE the fucking testing framework." The domain section captures "use" through the four requirements but does not capture "improve." The mandate as currently written requires phases to use the testing framework but does not require them to contribute improvements back. This is not a minor omission — the user's word "AND IMPROVE" was emphatic. The testing framework's adaptive tier system (coverage_radar, tier_manager, improvement.py, regression.py) is explicitly designed to accumulate knowledge across sessions. If phases only USE it without contributing observations, the intelligence layer starves.
**Why:** Concrete failure: Phase 3.2 (First Working Audit) runs 5 Agent Team sessions, satisfies the testing gate, but does not feed any evaluation transcripts back into the tier system, does not update coverage baselines, and does not file any framework improvement observations. The mandate is "satisfied" but the user's actual requirement — that the framework gets smarter as phases execute — is not. The testing framework's EvaluationRunner has an 8-stage pipeline specifically designed to produce persistent artifacts (`.vrs/evaluations/`, `.vrs/observations/`). The mandate must require these artifacts to exist after each phase.
**How:** 
1. Add a "Framework Contribution" requirement to the Testing Gate Template: each phase must produce (a) at least one `.vrs/observations/{phase-id}/` artifact from the EvaluationRunner, (b) a brief post-phase note in `.vrs/evaluations/progress.json` documenting any framework gaps or improvements discovered. This is not optional for any phase type except SYNTHESIS.
2. In CONTEXT.md, add language: "Using the testing framework means running it AND recording its outputs as persistent artifacts. A phase that runs Agent Teams but discards transcripts has NOT satisfied the testing mandate." This makes the "improve" dimension observable rather than aspirational.
**Impacts:** Plan 05 scope — adds "artifact persistence" as a required output to all Testing Gate definitions
**Research needed:** no — the artifact paths already exist from Plan 08/09 work
**Confidence:** MEDIUM — I'm inferring the user's "AND IMPROVE" intent; this interpretation could be wrong if "improve" meant "improve the quality of work" rather than "contribute feedback to the framework"
**Prior art:** 1 — Feedback loops in CI/CD (test results feeding next run configuration) exist but applying this to AI evaluation frameworks with persistent transcript archives is novel
**Prerequisite:** no — `.vrs/` structure already exists
**Status:** implemented
**Adversarial verdict:** ENHANCE (Governance Architecture) — Improve without pre-named metric is unfalsifiable; needs improvement_target field named before execution
**Origin:** NOVEL — the gap between "use" and "improve" in the mandate is visible from the domain's direct quote of the user


### P1-ADV-201: Minimum Viable Interrogation Protocol — 3 Questions + Storage Location
**Target:** CONTEXT
**What:** Define the minimum viable interrogation protocol for Plan 04: who asks, what three questions, where answers land. Leave taxonomy and retry limits to emerge from sessions.
**Why:** Without a storage location and a starting question set, the interrogation loop produces observations that can't be compared across sessions or fed back into framework improvements. The CONTEXT decision on "interactive debugging" presupposes these exist, but they don't yet. The full taxonomy should emerge from real sessions — this CREATE gives the scaffold, not the edifice.
**How:**
1. Define interrogation entry point: the human executor (or orchestrating agent) asks three structured questions when an agent fails: (a) "What command did you run and what was the exact output?", (b) "What did you expect vs what happened?", (c) "What would you try next given that output?"
2. Store responses in `.vrs/observations/plan04/debug-<session-id>-<attempt>.json` with fields: command, stdout, stderr, exit_code, agent_hypothesis, proposed_fix.
3. State explicitly in CONTEXT that taxonomy and retry limits are NOT defined yet — they emerge from Plan 04 sessions and feed into Plan 05.
4. Add a note to Plan 04 task: "If agent cannot answer question (a), escalate to pre-validation (IMP-18)."
**Impacts:** Plan 04 execution, observation artifact format, Plan 05 protocol refinement
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 2
**Prerequisite:** no
**Status:** implemented
**Origin:** ADVERSARIAL — reframed from P1-IMP-16; full protocol spec premature, minimum scaffold is what blocks execution

### P1-ADV-301: Enforcement via Plan Task Done Criteria, Not CONTEXT.md Sections
**Target:** CONTEXT
**What:** Encode Testing Gate compliance as explicit done criteria in every plan task that produces a phase deliverable, rather than as a standalone CONTEXT.md section. Each task's `done` field must include: "Testing Gate passed: `.vrs/observations/<phase>/session-<N>.json` exists with score above threshold."
**Why:** Done criteria are the only plan field that executors cannot skip without marking the task explicitly incomplete. A CONTEXT.md policy section and a STATE.md entry are advisory. A done criterion that requires a named artifact path is blocking — the executor must either produce the artifact or mark the task BLOCKED, making the gap visible rather than silently bypassed.
**How:**
1. In Plan 05b (the rollout plan that applies the mandate to near-term phases), add a standard done-criteria block to the CONTEXT.md update task for each phase: "Verify `.vrs/observations/<phase>/` directory exists with at least N session JSON files."
2. In PLAN-PHASE-GOVERNANCE.md, add a "Testing Gate Compliance" section that mandates all future plan templates include this done-criteria pattern.
3. Retire the proposal for a machine-readable CONTEXT.md section — it adds parsing complexity with no enforcement gain over done criteria.
**Impacts:** 3.1c.2 plan, 3.1f plan, 3.2 plan, PLAN-PHASE-GOVERNANCE.md
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Status:** implemented
**Origin:** ADVERSARIAL — reframed from P1-IMP-26; CONTEXT.md governance is advisory, done criteria are blocking

## Post-Review Synthesis
**Items created:** P1-SYN-01, P1-SYN-02, P1-CSC-01, P1-CSC-02
**Key insight:** Plans 02 and 03 both manipulate contract-to-graph mappings but share no canonical "contract identity" specification — IMP-06, IMP-07, IMP-10, and IMP-13 are four symptoms of the same missing abstraction. Separately, Plans 01-03 all change write-side paths without a coordinated read-path inventory, guaranteeing breakage at integration time.

### P1-SYN-01: Canonical Contract Identity Specification
**Target:** CONTEXT
**What:** IMP-06 (realpath vs abspath), IMP-07 (hash encoding), IMP-10 (directory vs file scope), and IMP-13 (--graph flag resolution) all fail because there is no single specification defining "contract identity" — the canonical input that maps a user's intent to a specific graph artifact. Each item patches one facet, but without a shared spec, the patches will use incompatible definitions (one normalizes to directory, another to file; one uses UTF-8, another OS encoding).
**Why:** Fixing these four items independently produces four locally-correct but mutually-inconsistent identity computations. The build command will hash one way, the query command another, and the --graph flag a third. This is the exact cross-contamination bug the phase exists to fix. A single spec costs ~30 minutes of design and prevents weeks of integration debugging.
**How:** 1. Add a `Contract Identity Specification` subsection to CONTEXT.md (or a standalone design note in the phase directory) defining: (a) canonical form = realpath of the primary .sol file, (b) encoding = UTF-8 normalized NFC, (c) hash algorithm = SHA-256 of canonical form, truncated to 12 hex chars, (d) directory input = enumerate .sol files, each gets its own identity. 2. Reference this spec from Plans 02 and 03 task descriptions so implementers use the same identity function. 3. Add a single-function utility `contract_identity(path: Path) -> str` in a shared module (e.g., `kg/storage/identity.py`) that all callers import — build-kg, query, --graph resolution.
**Impacts:** Plan 02 (graph storage paths), Plan 03 (query routing + --graph resolution)
**Components:** P1-IMP-06, P1-IMP-07, P1-IMP-10, P1-IMP-13
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no — AUTO-FIX: CONTEXT text changes are merge-ready; code components (utility function, inventory) are implementation tasks during plan execution
**Status:** implemented
**Adversarial note:** CONFIRM (ADV Validation) — All four checks pass. Concrete spec, correct flags, no duplication, all fields present. Execute first in Plan 01 context action phase.
**Source:** Post-review synthesis (cross-cutting)
**Origin:** genuine

### P1-SYN-02: Coordinated Read-Path Migration Inventory
**Target:** CONTEXT
**What:** IMP-09 (GraphStore caller audit), IMP-08 (backward compatibility), IMP-04 (test hardcoded paths), and IMP-12 (mtime auto-discovery risk) all reveal the same structural problem: Plans 01-03 change where artifacts are written but no plan audits where artifacts are read. Every reader that assumes the old flat layout will silently get empty results or stale data after Plans 01-02 execute.
**Why:** Addressing each reader ad-hoc during implementation means the first plan to merge breaks consumers that later plans haven't audited yet. A single coordinated inventory — performed once before any plan executes — ensures all readers are known and each plan's migration scope is bounded.
**How:** 1. Before Plan 01 implementation begins, grep the codebase for all Path constructions referencing `vulndocs/`, `.vrs/graphs/`, `graph.toon`, and `KnowledgeGraph.load`/`KnowledgeGraph.from_file`. Record each callsite with (file, line, current assumption, owning plan). Store as `.planning/phases/3.1c.1-cli-graph-isolation-hardening/read-path-inventory.md`. 2. For each callsite, annotate which plan is responsible for updating it and what the new path logic should be. 3. Add the inventory as a done-criteria artifact for the first plan that executes (Plan 01), ensuring it exists before Plans 02-03 begin modifying storage paths.
**Impacts:** Plan 01 (vulndocs paths), Plan 02 (graph storage), Plan 03 (query routing), Plan 04 (smoke tests must verify readers work)
**Components:** P1-IMP-04, P1-IMP-08, P1-IMP-09, P1-IMP-12
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 2
**Prerequisite:** no — AUTO-FIX: CONTEXT text changes are merge-ready; code components (utility function, inventory) are implementation tasks during plan execution
**Status:** implemented
**Adversarial note:** CONFIRM (ADV Validation) — All four checks pass. Concrete audit process, correct flags, complements IMP-09 systematically.
**Source:** Post-review synthesis (cross-cutting)
**Origin:** genuine

### P1-CSC-01: Cross-Contract Graph Construction Under File-Level Identity
**Target:** CONTEXT
**What:** When P1-IMP-10 is resolved by mandating file-level granularity (each .sol file gets its own graph identity and subdirectory), `build-kg contracts/` for a multi-file project with cross-contract imports (e.g., Token.sol imports IERC20.sol) must decide: does each file get an independent graph, or does the build produce a unified graph keyed to the "entry point" file? Slither already resolves imports into a unified compilation — splitting its output into per-file graphs would lose cross-contract edges (e.g., external calls between contracts). But a unified graph needs a single identity, which contradicts pure file-level hashing.
**Why:** Without this decision, Plan 02 implementation will either (a) produce incomplete per-file graphs that miss cross-contract vulnerabilities, or (b) silently fall back to directory-level hashing for multi-file builds, reintroducing the exact ambiguity IMP-10 fixes.
**How:** 1. **Research phase (Plan 01 research task):** Query Slither output model — does it include metadata identifying which edges cross file boundaries? If yes, can Slither be configured to produce per-contract subgraphs with explicit "external_calls" edges? 2. **Decision phase (Plan 01 context task):** Document in CONTEXT.md Decisions section: "When Slither resolves imports, we treat the resulting compilation unit (all files needed for one entry-point contract) as the atomic identity unit. Identity = SHA-256(sorted_absolute_paths_of_compilation_unit)." Add rationale: preserves cross-contract edges for detection while keeping hashing deterministic. 3. **User control (Plan 02 implementation task):** Add `--entry-point` flag to build-kg; if omitted, default to "all .sol files are entry points, generate separate graphs for each". 4. **Store decision in identity utility (Plan 02):** `contract_identity(paths: List[Path], entry_point: Optional[Path] = None) -> str` signature documents the three-parameter model.
**Impacts:** Plan 01 (research decision required), Plan 02 (graph identity storage), Plan 03 (query routing for multi-file projects)
**Trigger:** P1-IMP-10
**Research needed:** no — RESOLVED by /msd:research-gap (GAP-02)
**Research summary:** Slither treats compilation unit as atomic. Cross-contract edges (inheritance, HighLevelCall) exist only within a compilation unit. Graph identity should use SHA-256(sorted absolute paths of all files in compilation), extracted from Slither source_mapping.filename_absolute. Single-file contracts degenerate to per-file hashing. No --entry-point flag needed at this stage.
**Confidence:** HIGH
**Prior art:** 1
**Prerequisite:** no
**Depends on plans:** Plan 02 (decision must be documented before Plan 02 implementation)
**Status:** implemented
**Adversarial note:** ENHANCE (ADV Validation) — How field lacked specifics on entry-point resolution, Slither output model, and query routing. Rewritten with 4-step concrete plan. Prerequisite stays no (target is CONTEXT).
**Source:** Post-review synthesis (cascade)

### P1-CSC-02: importlib.resources Makes VulnDocs Read-Only — Breaks Write Skills
**Target:** CONTEXT
**What:** When P1-IMP-02 is implemented (switching vulndocs resolution from `__file__`-relative to `importlib.resources.files()`), the returned paths are `Traversable` objects that may be read-only (especially in installed/zipped packages). The skills `/vrs:add-vulnerability`, `/vrs:refine`, and `vulndocs validate --fix` all write to vulndocs files. After the switch, these write operations will fail with permission or type errors in any non-editable install.
**Why:** IMP-02 correctly identifies importlib.resources as the stdlib solution for reads, but the phase domain includes vulndocs as a read-write resource (skills create and modify patterns). Applying a read-only resolution uniformly breaks the write path. This must be addressed before or during Plan 01 implementation, not discovered during Plan 04 smoke tests.
**How:** 1. In Plan 01, distinguish two resolution modes: (a) `vulndocs_read_path()` using `importlib.resources.files()` for detection/query consumers, (b) `vulndocs_write_path()` using `__file__`-relative (editable) or a user-configurable `ALPHASWARM_VULNDOCS_DIR` env var (installed). 2. Add the env var to CLI --help and error messages (per IMP-14). 3. Add a test case in Plan 01 that verifies write-path resolution returns a writable directory.
**Impacts:** Plan 01 (vulndocs resolution must support writes), Plan 04 (smoke tests should include a vulndocs-write scenario)
**Trigger:** P1-IMP-02
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 2
**Prerequisite:** no
**Status:** implemented
**Adversarial note:** CONFIRM (ADV Validation) — All four checks pass. Concrete dual-resolution approach, correct flags, fills critical write-path gap IMP-02 leaves open.
**Source:** Post-review synthesis (cascade)

## Convergence

Pass 1: N/A (first pass — no convergence ratio computed)
Structural: 25 confirmed/enhanced | Research: 2 (IMP-05, CSC-01) | Prerequisites: 2 (SYN-01, SYN-02) | Rejected: 3
Signal: ACTIVE (first pass)


## Convergence Assessment

Pass 1 — no prior passes exist, so no filtering applied.

**Novel improvements:** 6
**Filtered observations (not proposed):** 0 (pass 1, no filtering active)
**Cosmetic (of novel):** 0
**Self-justification ratio:** 0%

All six items address structural gaps in the CONTEXT design that are independent of any prior improvement pass:

- IMP-01 and IMP-02 are tightly coupled (both about hash input specification) but distinct enough to be separate items — IMP-01 is about the resolution function, IMP-02 is about the full hash specification including encoding and edge cases. They could be merged if desired.
- IMP-03 (backward compatibility) and IMP-04 (caller audit) are prerequisites to IMP-02 being safely implementable.
- IMP-05 (directory vs file scope) is the highest-severity item — it is a silent failure scenario that recreates the exact Batch 1 failure mode.
- IMP-06 (manifest/listing) is operational but important for the Plan 04 debugging goal.

The most critical path: IMP-02 → IMP-05 → IMP-01 → IMP-03 → IMP-04 → IMP-06.
IMP-05 must be resolved before any implementation begins, as it changes the fundamental storage model.


## Convergence Assessment

Skip for passes 1-2.


## Convergence Assessment

(Pass 1 — convergence detection not active for passes 1-2. Included for completeness.)

**Novel improvements:** 7
**Filtered observations (not proposed):** N/A (pass 1)
**Cosmetic (of novel):** 0
**Self-justification ratio:** N/A (pass 1)

All 7 items are structural gaps in the CONTEXT.md description of Plan 04. None are
cosmetic. The most critical are IMP-01 (interrogation protocol), IMP-02 (transcript
analysis criteria), and IMP-03 (circular dependency), as these three together determine
whether Plan 04's done criteria are falsifiable at all. IMP-05 (jujutsu prerequisite)
is the most likely to cause a hard execution stop. IMP-06 (undefined smoke test scope)
is the most likely to cause a false-positive PASS verdict.

**Cross-area concerns (not proposed as items):**
- Plan 05's mandate cannot be precise until Plan 04's protocol is defined (IMP-01,
  IMP-02). Plan 05 reviewer should flag this dependency.
- The AgentExecutionValidator (12 checks from Plan 3.1c-12) should be extended to
  include the CLI confirmation criteria from IMP-02. This is a Plan 03/04 interaction
  that the AgentExecutionValidator area reviewer should address.


## Convergence Assessment

Passes 1-2: convergence classification not required per instructions. Noting structural findings summary for planner awareness:

**Summary:** All 7 items are structural. None are cosmetic. Plan 05 has a fundamental design problem: it is trying to write compliance documents before defining what compliance means (IMP-01, IMP-05), for phases whose domains don't yet exist (IMP-02), without handling the bootstrap case of testing-infrastructure phases (IMP-03), with no enforcement mechanism (IMP-04), and with the design and rollout work conflated into a single undersized plan (IMP-06). The "improve" half of the user's requirement is entirely missing (IMP-07).

The most actionable structural recommendation is IMP-06 (split Plan 05 into 05a design + 05b rollout), as it resolves the sequencing dependency that makes several other items harder to address.

**Cross-area note:** Plan 04 (CLI Isolation Smoke Tests) provides the testing protocol that Plan 05 is supposed to mandate across phases. Plan 05 depends on Plan 04 being complete and documented before the rollout phase (Plan 05b) begins — the dependency direction should be explicit in the phase plan structure.

