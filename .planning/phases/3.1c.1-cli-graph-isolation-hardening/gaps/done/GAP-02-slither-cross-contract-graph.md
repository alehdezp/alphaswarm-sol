# GAP-02: Slither output model for cross-contract graph construction

**Created by:** improve-phase
**Source:** P1-CSC-01
**Priority:** HIGH
**Status:** active
**depends_on:** []

## Question

When Slither analyzes a multi-file Solidity project with cross-contract imports (e.g., Token.sol imports IERC20.sol), does the Slither output model:
1. Include metadata identifying which edges cross file boundaries?
2. Support per-contract subgraph extraction with explicit external-call edges?
3. Treat the compilation unit as atomic, or can it produce separate analyses per file?

This determines whether per-file graph identity (SHA-256 of individual .sol file) is viable, or whether the identity must be based on the compilation unit (sorted paths of all files in the compilation).

## Context

Plan 02 proposes hash-based per-contract graph storage. P1-IMP-10 established file-level granularity as the identity model. But Slither resolves imports into a unified compilation — splitting its output into per-file graphs would lose cross-contract edges (external calls between contracts). A unified graph needs a single identity, which contradicts pure file-level hashing.

Without this decision:
- Plan 02 may produce incomplete per-file graphs missing cross-contract vulnerabilities
- OR silently fall back to directory-level hashing, reintroducing ambiguity

The proposed resolution is: treat the compilation unit (all files needed for one entry-point contract) as the atomic identity unit, with `Identity = SHA-256(sorted_absolute_paths_of_compilation_unit)`.

## Research Approach

- Query Slither documentation for its compilation model and output structure
- Check Slither's Python API (`slither.core.slither_core.SlitherCore`) for compilation unit metadata
- Search for Slither's handling of multi-file projects and import resolution
- Check this project's existing `kg/builder/` code for how Slither output is currently consumed
- Look at Slither GitHub issues about per-file analysis
- Authoritative sources: Slither official docs, crytic/slither GitHub, existing builder code

## Findings

**Confidence: HIGH** (official Slither API docs + codebase analysis + multiple corroborating sources)

### 1. Slither's compilation model is ATOMIC per compilation unit

**Source:** Official Slither API docs (https://secure-contracts.com/program-analysis/slither/docs/src/api/api.html), crytic/slither GitHub, Slither Python API docs (https://crytic.github.io/slither/slither/slither.html)

Slither's architecture has 6 layers: `Slither` -> `SlitherCompilationUnit` -> `Contract` -> `Function` -> `Node` -> `SlithIR`. The key object is `SlitherCompilationUnit`:

> "`SlitherCompilationUnit` - group of files used by one call to solc"
> "Most targets have 1 compilation, but not always true"

When Slither is initialized with `Slither('/path/to/project')` or `Slither('file.sol')`, it delegates to `crytic-compile` which runs `solc`. The Solidity compiler resolves all imports and produces a **single compilation**. Slither then wraps this as a `SlitherCompilationUnit` containing ALL contracts from ALL files in the compilation.

### 2. Cross-contract edges are INTRINSIC to the compilation unit

Each `Contract` object has:
- `functions: list[Function]` -- all functions in this contract
- `inheritance: list[Contract]` -- inherited contracts (c3 linearization order)
- `derived_contracts: list[Contract]` -- contracts derived from it

Each `Function` has:
- `all_state_variables_read` -- includes variables read through internal calls across contracts
- `slithir_operations` -- includes `HighLevelCall` operations that reference OTHER contracts

The SlithIR intermediate representation captures cross-contract calls as `HighLevelCall` with a `destination` attribute pointing to the target contract. These edges are available ONLY within the same compilation unit. Splitting into per-file subgraphs would lose them.

### 3. Slither does NOT support per-file subgraph extraction

GitHub issue #731 (crytic/slither) -- "Add support for multiple compilation units" -- was specifically about allowing Slither to handle codebases with DIFFERENT solc versions (requiring separate compilation runs). It was NOT about splitting a single compilation into per-file subgraphs. The issue confirms that Slither's fundamental unit of analysis is the compilation unit.

### 4. How this project currently consumes Slither output

From `src/alphaswarm_sol/kg/builder/core.py`:
```python
slither_instance = Slither(str(target), **slither_kwargs)
# ...
contracts = sorted(
    getattr(slither, "contracts", []),
    key=lambda c: getattr(c, "name", "")
)
```

The builder iterates `slither.contracts` (all contracts from all files in the compilation) and processes each contract via specialized processors. The `CallTracker` captures cross-contract calls via `get_external_call_contracts()`. The `source_mapping` attribute on each Slither object provides the file path (`filename_absolute` or `filename`) -- this IS per-file metadata.

### 5. `contracts_derived` vs `contracts` provides useful filtering

Slither provides `contracts_derived` -- contracts NOT inherited by another contract. This filters out inherited base contracts (like `Ownable`, `ERC20`) and shows only "leaf" contracts. However, this is per-compilation-unit, not per-file.

### 6. Source mapping DOES identify which file each contract lives in

Each Slither object (Contract, Function, Node) has a `source_mapping` attribute with `filename_absolute` and `filename`. This means we CAN identify which file each contract is defined in, even within a unified compilation. But the cross-contract edges (inheritance, external calls) span files.

### Sources
- Slither API docs: https://secure-contracts.com/program-analysis/slither/docs/src/api/api.html (HIGH)
- Slither Python API: https://crytic.github.io/slither/slither/slither.html (HIGH)
- crytic/slither issue #731: https://github.com/crytic/slither/issues/731 (HIGH)
- This project's builder code: `src/alphaswarm_sol/kg/builder/core.py` L148-162 (VERIFIED)
- Ethereum.org Slither tutorial: https://ethereum.org/developers/tutorials/how-to-use-slither-to-find-smart-contract-bugs (MEDIUM-HIGH)

## Recommendation

**Use compilation-unit-level identity, not per-file identity.** The proposed resolution in P1-CSC-01 is correct.

Specifically:
1. **Graph identity = SHA-256(sorted absolute paths of ALL files in the compilation unit).** When Slither compiles `Token.sol` which imports `IERC20.sol`, the identity is `SHA-256(sort([abs_path(IERC20.sol), abs_path(Token.sol)]))`. This preserves cross-contract edges and is deterministic.

2. **Extract file list from Slither source mappings.** After Slither analysis, iterate all contracts and collect `source_mapping.filename_absolute` into a sorted set. This is the compilation unit's file list for identity computation.

3. **For single-file contracts (the common case), the identity degenerates to SHA-256 of that one file's absolute path.** This is backward-compatible with the simple per-file model. The complex case only activates for multi-file projects with cross-contract imports.

4. **Do NOT add `--entry-point` flag at this stage.** The P1-CSC-01 suggestion of an `--entry-point` flag adds unnecessary complexity. Slither already determines the compilation unit based on the target path. When `build-kg contracts/Token.sol` is run, Slither resolves imports automatically. The identity should simply capture what Slither actually compiled.

5. **Add to CONTEXT.md Decisions:** "Graph identity uses compilation-unit-level hashing: `SHA-256(sorted_absolute_paths_of_all_files_in_compilation)`. For single-file contracts, this is equivalent to per-file hashing. For multi-file projects, it preserves cross-contract edges (inheritance, external calls). File list extracted from Slither source mappings after analysis."

**Plans affected:** Plan 02 (graph identity storage) -- the identity utility function signature should be `contract_identity(source_files: list[Path]) -> str` where source_files comes from Slither source mappings. Plan 03 (query routing) -- queries target a specific compilation-unit graph, not per-file graphs.
