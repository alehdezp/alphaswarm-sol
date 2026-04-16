# GAP-03: Slither source_mapping.filename_absolute Path Resolution for Imports

**Created by:** improve-phase
**Source:** P2-IMP-06
**Priority:** HIGH
**Status:** active
**depends_on:** []

## Question

Does Slither's `source_mapping.filename_absolute` for import resolution (e.g., OpenZeppelin imports) produce absolute machine-local paths (pointing to node_modules, virtualenv, or npm cache) or project-relative paths? Specifically, when a contract imports `@openzeppelin/contracts/token/ERC20/ERC20.sol`, what does the `filename_absolute` field contain for the resolved import source?

## Context

This determines whether the canonical contract identity hash (Plan 02) must filter out external dependency paths. If Slither resolves imports to machine-local absolute paths (e.g., `/Users/alice/.cache/npm/...` or `/path/to/node_modules/...`), then two agents in different worktrees building the same contract would produce different hashes — defeating coordination without triggering cross-contamination detection.

The current Plan 02 spec says "all files in compilation unit" for the identity hash, which would include these machine-local paths if they appear in `source_mapping.filename_absolute`. P2-IMP-06 proposes filtering to only CLI-specified `.sol` inputs under the project root.

Affected plans: Plan 02 (hash algorithm), Plan 03 (stem-based lookup indirectly).

## Research Approach

1. **Primary: Examine Slither source code** — Look at how `source_mapping.filename_absolute` is populated. Check the Slither compilation/parsing pipeline.
2. **Secondary: Examine existing codebase** — This project already uses Slither. Check the `kg/builder/` module to see what `source_mapping` data is actually received.
3. **Tertiary: Web search** — Slither documentation on source mappings and file resolution.
4. **Validation criteria:** A clear answer on whether `filename_absolute` for import-resolved files contains: (a) absolute paths to node_modules/virtualenv, (b) paths relative to project root, or (c) something else.

## Findings

**Confidence: HIGH** (direct source code inspection of crytic-compile 0.3.11 + Slither installed in project venv + corroborating GitHub issues)

### 1. `filename_absolute` IS a true absolute machine-local filesystem path

**Source:** Direct inspection of `crytic_compile/utils/naming.py` (installed at `.venv/lib/python3.11/site-packages/crytic_compile/utils/naming.py`)

The `convert_filename()` function (line 125-198) constructs the `Filename` dataclass with four fields: `absolute`, `used`, `relative`, `short`. The critical line is **line 171**:

```python
absolute = Path(os.path.abspath(filename))
```

This means `filename.absolute` is ALWAYS a resolved absolute filesystem path, produced by `os.path.abspath()`. There is no project-relative or virtual path -- it is a real filesystem location.

### 2. Import-resolved files resolve to their actual filesystem location (node_modules, lib, etc.)

**Source:** `_verify_filename_existence()` in the same file (lines 82-124)

When crytic-compile encounters an import, it searches for the file using these heuristics (in order):
1. Direct path (`filename.exists()`)
2. `contracts/FILENAME`
3. `cwd/FILENAME`
4. `node_modules/FILENAME`
5. Walk up parent directories looking for `node_modules/FILENAME`

Once found, the path is resolved via `os.path.abspath()`. So for `@openzeppelin/contracts/token/ERC20/ERC20.sol`, the `filename_absolute` would be something like:
```
/Users/alice/project/node_modules/@openzeppelin/contracts/token/ERC20/ERC20.sol
```

For Foundry projects using `lib/`:
```
/Users/alice/project/lib/openzeppelin-contracts/contracts/token/ERC20/ERC20.sol
```

### 3. Slither's `SourceMapping` passes through crytic-compile's `Filename` directly

**Source:** `slither/core/source_mapping/source_mapping.py` (lines 185-198)

The source mapping resolution code calls:
```python
filename: Filename = compilation_unit.core.crytic_compile.filename_lookup(filename_used)
```

And stores the result as `new_source.filename = filename`. The `filename_absolute` field in Slither's JSON output (line 41) is:
```python
"filename_absolute": self.filename.absolute,
```

This is the same `absolute` field from crytic-compile's `Filename` -- a machine-local absolute path.

### 4. Crytic-compile ALREADY has dependency detection that uses these paths

**Source:** Platform-specific `is_dependency()` implementations:
- **Hardhat** (`hardhat.py:233`): `"node_modules" in Path(path).parts`
- **Foundry** (`foundry.py:218`): `"lib" in Path(path).parts or "node_modules" in Path(path).parts`
- **Solc direct** (`solc.py:201-210`): Always returns `False` (no dependency concept for raw solc)

Slither itself stores `is_dependency` on every `Source` object (line 191):
```python
is_dependency = compilation_unit.core.crytic_compile.is_dependency(filename.absolute)
```

### 5. Implications for this project

This project's builder code (`kg/builder/helpers.py:31`, `kg/builder/contracts.py:1248`, etc.) accesses `source_mapping.filename_absolute` but does NOT check `source_mapping.is_dependency`. It treats all files equally. This means the compilation unit file list for identity hashing would include paths like:
```
/Users/alice/project/node_modules/@openzeppelin/contracts/token/ERC20/ERC20.sol
/Users/bob/worktree-1/node_modules/@openzeppelin/contracts/token/ERC20/ERC20.sol
```

These produce DIFFERENT hashes for the same logical contract, confirming P2-IMP-06's concern.

### 6. Confirmed: GitHub issue #205 documents this exact problem

**Source:** https://github.com/crytic/slither/issues/205 ("Slither should attempt to standardize source mapping filenames")

The issue explicitly states: "files within nodejs modules (such as OpenZeppelin) will have their paths returned as they were imported: `openzeppelin-solidity/contracts/token/ERC20/IERC20.sol`" -- and that the behavior varies by compilation platform.

### Sources
- crytic-compile 0.3.11 source code: `naming.py` L125-198 (VERIFIED - installed in project venv)
- crytic-compile 0.3.11 source code: `hardhat.py` L222-235, `foundry.py` L207-220 (VERIFIED)
- Slither source mapping: `source_mapping.py` L185-199 (VERIFIED)
- Slither issue #205: https://github.com/crytic/slither/issues/205 (CORROBORATING)
- Solidity import path resolution docs: https://docs.soliditylang.org/en/v0.8.33/path-resolution.html (REFERENCE)

## Recommendation

**Filter the compilation unit file list to ONLY project-local files when computing the canonical identity hash.** P2-IMP-06's proposal is correct and NECESSARY. Specifically:

1. **Use Slither's built-in `is_dependency` flag as the primary filter.** After Slither analysis, when collecting `source_mapping.filename_absolute` paths for identity computation, EXCLUDE any file where `source_mapping.is_dependency == True`. This is more robust than path-based filtering because crytic-compile already implements platform-specific dependency detection (Hardhat checks `node_modules`, Foundry checks `lib` and `node_modules`, etc.).

2. **Fallback: project-root prefix filter.** For platforms where `is_dependency` always returns `False` (raw solc), fall back to P2-IMP-06's proposed filter: only include files whose `os.path.realpath()` is prefixed by the project root. Resolve project root via `git rev-parse --show-toplevel` with `commonpath()` fallback.

3. **Update Plan 02 CONTEXT.md** to replace "sorted realpaths of all files in compilation unit" with: "sorted realpaths of NON-DEPENDENCY files in compilation unit (filtered by `source_mapping.is_dependency` with project-root prefix fallback)."

4. **The `contract_identity()` function signature should be:** `contract_identity(source_files: list[Path], dependency_flags: list[bool]) -> str` or preferably accept Slither `Source` objects directly to access the `is_dependency` field without manual parallel arrays.

5. **Log excluded dependencies** at DEBUG level (not WARNING as P2-IMP-06 proposed) -- excluding dependencies is the NORMAL case, not an anomaly. Only log at WARNING if the filter excludes ALL files (which indicates a misconfigured project root).

**Plans affected:**
- **Plan 02:** Identity hash algorithm MUST add dependency filtering. This is a specification change, not just an implementation detail. The current spec as written would produce environment-dependent hashes.
- **Plan 03:** No direct change, but stem-based lookup benefits from accurate identity (fewer false hash mismatches).
