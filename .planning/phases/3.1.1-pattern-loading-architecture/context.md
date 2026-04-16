# Phase 3.1.1: Pattern Loading Architecture Fix

## Planning Status

- This phase is **ACTIVE** — inserted as an emergency fix between Phase 3.1 (COMPLETE) and Phase 3.1b.
- Plans: **4** (3 core + 1 triage)
- Root cause is fully understood and the fix is straightforward. Confidence: HIGH.

**Inserted after:** Phase 3.1 (Testing Audit & Cleanup) — COMPLETE
**Blocks:** Phase 3.1b (Workflow Testing Harness) — cannot build on a broken test suite

---

## Honest Assessment: What Happened and Why

### The Root Cause (Brutally Honest)

During v5.0 development, the `patterns/` directory was renamed to `vulndocs/`. Nobody updated the code that loaded from it. **This is a textbook "silent failure" antipattern.** The `PatternStore.load()` method returns `[]` when given a nonexistent path instead of raising an error. This means:

- 891 tests were loading 0 patterns and testing nothing
- Tests asserting "should NOT find vulnerability X" passed vacuously (0 findings always passes a "not found" check)
- **Nobody noticed for months** because the return type was valid (`[]`)

### What Phase 3.1 Did (Emergency Sed Fix)

A mechanical `sed` replacement was applied:
- `PatternStore(Path("patterns")).load()` → `PatternStore.load_vulndocs_patterns(Path("vulndocs"))` across 82 occurrences in 21 test files
- `Path("patterns")` → `Path("vulndocs")` in 6 source files
- **Result:** 891 → 333 failures (558 fixed, 63% reduction)

### What the Sed Fix Missed

The sed targeted `PatternStore(Path("patterns")).load()` specifically. It missed:
- **`tests/test_schema_snapshot.py`** — 16 occurrences of `pattern_dir=Path("patterns")` passed as keyword argument to `build_schema_snapshot()`. Different call pattern, same bug.
- **`scripts/run_label_evaluation.py`** — 1 occurrence: `default=Path("patterns")` in argparse

These are **still broken** and testing against 0 patterns.

### Should We Rollback? NO.

**The sed fix is correct.** It replaced a broken path with a working one. The problem is not what it did, but HOW:

1. It created 82 identical `PatternStore.load_vulndocs_patterns(Path("vulndocs"))` calls — pure copy-paste
2. If `vulndocs/` ever moves again, we have the exact same problem in 82+ places
3. It didn't fix the root antipattern: `PatternStore` silently returning `[]` for missing paths
4. It switched from one API (`load()`) to another (`load_vulndocs_patterns()`) without understanding why two APIs exist

**Rollback would reintroduce 891 broken tests.** The fix is right; the architecture is wrong.

---

## Architectural Debt Analysis

### Problem 1: Two Incompatible Loading APIs

`PatternStore` has two public loading methods with different semantics:

| Method | What it does | When it breaks |
|--------|-------------|----------------|
| `PatternStore(dir).load()` | Recursively loads ALL yaml/json in directory tree | Crashes on vulndocs `index.yaml` files (missing required `id` field) |
| `PatternStore.load_vulndocs_patterns(dir)` | Only loads `**/patterns/*.yaml` files | Never crashes on index files, but silently returns `[]` on missing path |

Both return `[]` silently on nonexistent paths. **Both are wrong.** A function that loads configuration should fail loudly when the configuration doesn't exist. This is Python 101.

### Problem 2: No Single Source of Truth

Pattern loading is scattered across 8 source files and 21+ test files. Each independently:
1. Decides which path to use (`Path("patterns")`, `Path("vulndocs")`, `self.pattern_dir`)
2. Decides which API to call (`load()` vs `load_vulndocs_patterns()`)
3. Does NOT validate that patterns were actually loaded

**Enterprise Python practice:** There should be ONE function — `get_patterns()` — that every caller uses. Change the path in one place, everything works.

### Problem 3: Tests Duplicate Infrastructure Logic

Every test file's `setUp()` independently calls:
```python
self.patterns = PatternStore.load_vulndocs_patterns(Path("vulndocs"))
```

This is 80+ copies of the same line. The `graph_cache.py` module already shows the correct pattern: a shared `@lru_cache` function that loads once and caches.

### Problem 4: Silent Failure is the Actual Bug

The real bug is not "wrong path." The real bug is that `PatternStore.load()` treats a missing directory as "zero patterns" instead of an error. In any well-designed system:
- Missing config file → `FileNotFoundError`
- Empty config file → empty result (this is fine)
- Nonexistent directory → `FileNotFoundError`

### Problem 5: No Exception Hierarchy (Python Anti-Pattern)

The emergency fix and original code use raw stdlib exceptions or no exceptions at all. Python best practice (PEP 8, custom exception hierarchy pattern) is to define domain-specific exceptions so callers can handle pattern loading errors distinctly from other `FileNotFoundError`s or `RuntimeError`s in the system.

### Problem 6: No Deprecation Path for `load()`

The old `PatternStore.load()` API is broken for vulndocs directories but still publicly accessible. Without a `@deprecated` decorator, nothing warns callers. They'll keep using it, and it'll keep silently breaking on `index.yaml` files.

---

## Goal

Fix the systemic pattern loading failure by establishing a single source of truth for pattern discovery, making failures loud and immediate, and triaging all remaining test failures into actionable categories — so Phase 3.1b builds on a trustworthy test suite with a known baseline.

## What This Phase Delivers

1. **Exception hierarchy** — `PatternLoadError` → `PatternDirectoryNotFoundError` / `EmptyPatternStoreError` with `.path` attribute and `from e` chaining
2. **Canonical loader** — `get_patterns()` as THE single entry point for all pattern loading
3. **PatternStore hardening** — `__init__` validation, `@deprecated` on `load()`, strict path checks
4. **Shared test loader** — `tests/pattern_loader.py` with `@lru_cache`, dogfooding `get_patterns()`
5. **All callers migrated** — 8 source files + 21 test files + 2 missed files
6. **Regression tests** — 10+ tests preventing this class of bug forever
7. **Failure triage** — 333 remaining failures categorized as PATTERN_GAP / MISSING_ID / STALE_CODE / EXTERNAL_DEP

## What This Phase Does NOT Do

- **Not converting unittest.TestCase to pytest** — The `@lru_cache` pattern works with unittest
- **Not adding env var / config resolution** — YAGNI. `Path("vulndocs")` is always relative to project root
- **Not running the full test suite** — Only affected files, spot-checked
- **Not over-abstracting** — No `PatternSource` protocol, no plugin system, no loader registry
- **Not modifying `builder_legacy.py`** — Legacy constraint
- **Not changing pattern YAML schema** — Out of scope
- **Not changing vulndocs directory structure** — Out of scope

---

## Python Patterns Applied to This Phase

This section maps the proposed fixes to specific Pythonic idioms and PEP 8 best practices. Every code block in the plans below follows these patterns.

### Pattern: Custom Exception Hierarchy

**Reference:** "Custom Exception Hierarchy" — domain exceptions with chaining.
**Anti-pattern we're fixing:** Raw `FileNotFoundError` / `RuntimeError` or silent `return []`.

```python
# src/alphaswarm_sol/queries/errors.py (NEW FILE)

class PatternLoadError(Exception):
    """Base exception for all pattern loading failures.

    Callers can catch this to handle any pattern loading issue,
    or catch specific subtypes for fine-grained handling.
    """

class PatternDirectoryNotFoundError(PatternLoadError):
    """Pattern directory does not exist on disk."""

    def __init__(self, path: Path) -> None:
        self.path = path
        super().__init__(
            f"Pattern directory not found: {path}. "
            f"Expected vulndocs/ in project root."
        )

class EmptyPatternStoreError(PatternLoadError):
    """Valid directory exists but contains no loadable patterns."""

    def __init__(self, path: Path, glob_pattern: str = "**/patterns/*.yaml") -> None:
        self.path = path
        self.glob_pattern = glob_pattern
        super().__init__(
            f"No patterns matching '{glob_pattern}' found in {path}"
        )
```

**Why:** Callers can `except PatternLoadError` broadly or `except PatternDirectoryNotFoundError` specifically. Exception instances carry `.path` for programmatic handling. The `from e` chaining preserves tracebacks.

### Pattern: Exception Chaining (`from e`)

**Reference:** "Exception Chaining" — preserve tracebacks when wrapping.

```python
# Good — chain the cause:
try:
    patterns = PatternStore.load_vulndocs_patterns(pdir)
except OSError as e:
    raise PatternDirectoryNotFoundError(pdir) from e

# Bad — lose the original traceback:
if not pdir.exists():
    raise FileNotFoundError(f"...")  # Original error context lost
```

### Pattern: Explicit > Implicit + EAFP

**Reference:** "Explicit is Better Than Implicit" + "EAFP style."

```python
# Current (LBYL + implicit failure):
def load(self) -> list[PatternDefinition]:
    if not self.root.exists():
        return []  # Implicit: caller has no idea this failed

# Fixed (EAFP + explicit failure):
def load(self) -> list[PatternDefinition]:
    if not self.root.exists():
        raise PatternDirectoryNotFoundError(self.root)
    ...
```

### Pattern: `@deprecated` Decorator

**Reference:** "Function Decorators" — `@functools.wraps`.

```python
import functools
import warnings

def deprecated(reason: str):
    """Mark a callable as deprecated with migration instructions."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            warnings.warn(
                f"{func.__qualname__} is deprecated: {reason}",
                DeprecationWarning,
                stacklevel=2,
            )
            return func(*args, **kwargs)
        return wrapper
    return decorator
```

Applied to `PatternStore.load()`:
```python
@deprecated("Use get_patterns() instead. load() crashes on vulndocs index.yaml files.")
def load(self) -> list[PatternDefinition]:
    ...
```

**Why now, not Phase 6:** It's 10 lines. It warns every caller at runtime. Zero breakage. Waiting means more code silently uses the broken API.

### Pattern: Test Loader Dogfoods the Canonical API

**Reference:** "Explicit is Better Than Implicit" — don't bypass your own abstractions.

```python
# Anti-pattern — tests bypass get_patterns():
@lru_cache(maxsize=1)
def load_all_patterns() -> tuple[PatternDefinition, ...]:
    patterns = PatternStore.load_vulndocs_patterns(Path("vulndocs"))  # Bypasses!
    ...

# Correct — tests USE the canonical function:
from alphaswarm_sol.queries.patterns import get_patterns

@lru_cache(maxsize=1)
def load_all_patterns() -> tuple[PatternDefinition, ...]:
    """Cached pattern loader for tests. Dogfoods get_patterns()."""
    patterns = get_patterns()  # Single source of truth, everywhere
    assert len(patterns) >= 400, f"Expected >=400 patterns, got {len(patterns)}"
    return tuple(patterns)
```

### Pattern: `__init__` Validation (Fail Fast)

```python
# Current — accepts garbage silently:
class PatternStore:
    def __init__(self, root: Path) -> None:
        self.root = root  # Could be int, str, None — nobody checks

# Fixed — validate at construction:
class PatternStore:
    def __init__(self, root: Path) -> None:
        if not isinstance(root, Path):
            raise TypeError(
                f"PatternStore requires Path, got {type(root).__name__}"
            )
        self.root = root
```

### Pattern: Module `__all__` Exports

The `queries/__init__.py` already exports `PatternStore`. Add `get_patterns` and `PatternLoadError` hierarchy:

```python
# queries/__init__.py additions:
from alphaswarm_sol.queries.patterns import get_patterns
from alphaswarm_sol.queries.errors import (
    PatternLoadError,
    PatternDirectoryNotFoundError,
    EmptyPatternStoreError,
)
```

---

## Plans (4)

### Plan 1: Exception Hierarchy + Canonical Loader + PatternStore Hardening

**Goal:** Establish the exception hierarchy, create the single canonical `get_patterns()` entry point, harden `PatternStore` with strict validation, deprecate `load()`, and update all 8 source files.

**New file: `src/alphaswarm_sol/queries/errors.py`**
```python
"""Pattern loading exceptions.

Exception hierarchy:
    PatternLoadError (base)
    ├── PatternDirectoryNotFoundError  — path doesn't exist
    └── EmptyPatternStoreError         — path exists, no patterns found
"""
from __future__ import annotations

from pathlib import Path


class PatternLoadError(Exception):
    """Base exception for all pattern loading failures."""


class PatternDirectoryNotFoundError(PatternLoadError):
    """Pattern directory does not exist on disk."""

    def __init__(self, path: Path) -> None:
        self.path = path
        super().__init__(
            f"Pattern directory not found: {path}. "
            f"Expected vulndocs/ in project root."
        )


class EmptyPatternStoreError(PatternLoadError):
    """Valid directory exists but contains no loadable patterns."""

    def __init__(self, path: Path, glob_pattern: str = "**/patterns/*.yaml") -> None:
        self.path = path
        self.glob_pattern = glob_pattern
        super().__init__(f"No patterns matching '{glob_pattern}' found in {path}")
```

**Changes to `src/alphaswarm_sol/queries/patterns.py`:**

```python
import functools
import logging
import warnings
from pathlib import Path

from alphaswarm_sol.queries.errors import (
    PatternDirectoryNotFoundError,
    EmptyPatternStoreError,
)

logger = logging.getLogger(__name__)

_DEFAULT_VULNDOCS = Path("vulndocs")


def _deprecated(reason: str):
    """Mark a callable as deprecated with migration instructions."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            warnings.warn(
                f"{func.__qualname__} is deprecated: {reason}",
                DeprecationWarning,
                stacklevel=2,
            )
            return func(*args, **kwargs)
        return wrapper
    return decorator


def get_patterns(pattern_dir: Path | None = None) -> list[PatternDefinition]:
    """Load patterns from vulndocs directory — THE canonical entry point.

    All production code and tests should call this function.
    Raises PatternDirectoryNotFoundError if directory doesn't exist.
    Raises EmptyPatternStoreError if no patterns found.
    """
    pdir = pattern_dir or _DEFAULT_VULNDOCS
    try:
        patterns = PatternStore.load_vulndocs_patterns(pdir)
    except PatternDirectoryNotFoundError:
        raise  # Already the right exception type
    except OSError as e:
        raise PatternDirectoryNotFoundError(pdir) from e
    if not patterns:
        raise EmptyPatternStoreError(pdir)
    return patterns


class PatternStore:
    """Load patterns from a directory tree."""

    def __init__(self, root: Path) -> None:
        if not isinstance(root, Path):
            raise TypeError(f"PatternStore requires Path, got {type(root).__name__}")
        self.root = root

    @classmethod
    def load_vulndocs_patterns(cls, vulndocs_root: Path) -> list[PatternDefinition]:
        """Load patterns from VulnDocs **/patterns/ directories only.

        Raises PatternDirectoryNotFoundError if path doesn't exist.
        Returns [] only if path exists but has no matching files.
        """
        if not vulndocs_root.exists():
            raise PatternDirectoryNotFoundError(vulndocs_root)

        store = cls(vulndocs_root)
        patterns: list[PatternDefinition] = []
        for path in sorted(vulndocs_root.glob("**/patterns/*.yml")):
            patterns.extend(store._load_file(path))
        for path in sorted(vulndocs_root.glob("**/patterns/*.yaml")):
            patterns.extend(store._load_file(path))
        return patterns

    @_deprecated("Use get_patterns() instead. load() crashes on vulndocs index.yaml files.")
    def load(self) -> list[PatternDefinition]:
        if not self.root.exists():
            raise PatternDirectoryNotFoundError(self.root)
        patterns: list[PatternDefinition] = []
        for path in sorted(self.root.rglob("*")):
            if path.is_dir():
                continue
            if path.suffix.lower() not in {".yaml", ".yml", ".json"}:
                continue
            patterns.extend(self._load_file(path))
        return patterns
```

**Changes to `PatternEngine._load_patterns()` (lenient, with logging):**
```python
def _load_patterns(self) -> list[PatternDefinition]:
    """Load patterns — lenient wrapper for engine use.

    Unlike get_patterns(), this returns [] on missing dirs with a warning.
    Only used internally by PatternEngine where patterns are optional.
    """
    pdir = self._pattern_dir or Path("vulndocs")
    if not pdir.exists():
        logger.warning("Pattern directory not found: %s — returning empty", pdir)
        return []
    has_vulndocs_structure = any(pdir.glob("**/patterns/*.yml")) or any(
        pdir.glob("**/patterns/*.yaml")
    )
    if has_vulndocs_structure:
        return PatternStore.load_vulndocs_patterns(pdir)
    # Suppress deprecation warning for this internal fallback
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        try:
            return PatternStore(pdir).load()
        except (yaml.YAMLError, KeyError, ValueError) as e:
            logger.warning(
                "Failed to parse patterns from %s (flat-dir fallback): %s",
                pdir, e,
            )
            return []
```

**Update all 8 source files** to replace inline `PatternStore.load_vulndocs_patterns(pattern_dir or Path("vulndocs"))` with `get_patterns(pattern_dir)`:

| File | Line(s) | Current Code | Proposed Change |
|------|---------|-------------|-----------------|
| `queries/executor.py` | 65 | `self.pattern_dir or Path("vulndocs")` | Use `get_patterns()` |
| `queries/executor.py` | 273-280 | Auto-detects vulndocs vs flat, calls both APIs | Simplify to `get_patterns(self.pattern_dir)` |
| `queries/report.py` | 19 | `PatternStore.load_vulndocs_patterns(pattern_dir or Path("vulndocs"))` | `get_patterns(pattern_dir)` |
| `queries/schema_snapshot.py` | 39 | `PatternStore.load_vulndocs_patterns(pattern_dir or Path("vulndocs"))` | `get_patterns(pattern_dir)` |
| `queries/schema_hints.py` | 68 | `PatternStore.load_vulndocs_patterns(pattern_dir or Path("vulndocs"))` | `get_patterns(pattern_dir)` |
| `queries/intent.py` | 221 | `PatternStore.load_vulndocs_patterns(pattern_dir or Path("vulndocs"))` | `get_patterns(pattern_dir)` |
| `queries/patterns.py` | 539-548 | `PatternEngine._load_patterns()` with fallback | Keep lenient (log warning on missing) |
| `vql2/executor.py` | 41, 80, 95, 358 | `self.pattern_dir or Path("vulndocs")` + `load_vulndocs_patterns()` | `get_patterns(self.pattern_dir)` |
| `vql2/guidance.py` | 25, 42 | `self.pattern_dir or Path("vulndocs")` + `load_vulndocs_patterns()` | `get_patterns(self.pattern_dir)` |
| `testing/mutations.py` | 480 | `load_vulndocs_patterns(Path("vulndocs"))` inside try/except | Keep as-is — already handles errors. Optional: migrate to `get_patterns()` |

> **Behavior Change:** `build_schema_snapshot()` currently returns `SchemaSnapshot` with empty
> pattern-derived fields when `pattern_dir` is invalid. After migration to `get_patterns()`,
> it will raise `PatternDirectoryNotFoundError`. Callers that rely on graceful degradation
> (e.g., building a schema snapshot without patterns) must catch `PatternLoadError` or pass
> a valid path. This is intentional — silent empty snapshots masked the loading bug.

**Update `queries/__init__.py`** to export `get_patterns`, `PatternLoadError`, `PatternDirectoryNotFoundError`, `EmptyPatternStoreError`.

**Verification:**
```bash
uv run pytest tests/test_patterns.py -x -q                    # Core pattern matching
uv run pytest tests/test_schema_snapshot.py -x -q               # The 16 missed occurrences
uv run pytest tests/test_authority_lens.py -x -q                # Representative lens test
```

### Plan 2: Shared Test Loader + Fix All Test Files

**Goal:** Replace 80+ duplicate calls with a single cached loader that dogfoods `get_patterns()`.

**New file: `tests/pattern_loader.py`**
```python
"""Shared pattern loader for all tests.

Uses @lru_cache to load patterns once per process (same pattern as graph_cache.py).
Dogfoods get_patterns() — the canonical API — instead of bypassing it.
Works with unittest.TestCase (no pytest fixture dependency).
"""
from __future__ import annotations

from functools import lru_cache

from alphaswarm_sol.queries.patterns import PatternDefinition, get_patterns


# Minimum expected pattern count. As of 2026-02, vulndocs/ contains 466 patterns.
# This threshold catches catastrophic loading failures (wrong directory, broken glob)
# while allowing normal pattern additions/removals.
_MIN_EXPECTED_PATTERNS = 400


@lru_cache(maxsize=1)
def load_all_patterns() -> tuple[PatternDefinition, ...]:
    """Load all vulndocs patterns with caching and validation.

    Returns tuple (not list) for lru_cache hashability.
    Asserts >= _MIN_EXPECTED_PATTERNS patterns on first load as smoke check.
    """
    patterns = get_patterns()  # Uses canonical API — fails loud on bad path
    assert len(patterns) >= _MIN_EXPECTED_PATTERNS, (
        f"Expected >= {_MIN_EXPECTED_PATTERNS} patterns, got {len(patterns)}. "
        f"Pattern loading may be broken."
    )
    return tuple(patterns)
```

**Mechanical replacement in all 21 test files:**
```python
# BEFORE (80+ occurrences across 21 files):
from alphaswarm_sol.queries.patterns import PatternEngine, PatternStore
# ...
self.patterns = PatternStore.load_vulndocs_patterns(Path("vulndocs"))

# AFTER:
from alphaswarm_sol.queries.patterns import PatternEngine
from tests.pattern_loader import load_all_patterns
# ...
self.patterns = list(load_all_patterns())
```

**Fix `test_schema_snapshot.py` (16 missed occurrences):**
```python
# BEFORE:
snapshot = build_schema_snapshot(graph, pattern_dir=Path("patterns"))  # BROKEN!

# AFTER: remove keyword arg, let it default to vulndocs
snapshot = build_schema_snapshot(graph)
```

**Confirmed:** `build_schema_snapshot()` at `schema_snapshot.py:37-39` defaults to `Path("vulndocs")` when `pattern_dir` is None:
```python
def build_schema_snapshot(
    graph: KnowledgeGraph | None, *, pattern_dir: Path | None = None
) -> SchemaSnapshot:
    patterns = PatternStore.load_vulndocs_patterns(pattern_dir or Path("vulndocs"))
```

**Fix `tests/pattern_test_framework.py` (1 occurrence):**
```python
# BEFORE:
PatternStore(Path("patterns")).load()

# AFTER:
list(load_all_patterns())
```

**Fix `tests/test_vm_002_semantic.py` (8 occurrences):**
These reference subdirectories (`Path("patterns/semantic")`, `Path("patterns/core")`), not the root.
Check if `vulndocs/` has equivalent subdirectories. If not, these tests should be deleted as stale code.

**Fix `scripts/run_label_evaluation.py`:**
This needs BOTH a path fix (`Path("patterns")` → `Path("vulndocs")`) AND an API migration (`store.load()` → `get_patterns()`).
```python
# BEFORE:
default=Path("patterns"),

# AFTER:
default=Path("vulndocs"),
```

**Verification:**
```bash
uv run pytest tests/test_token_lens.py -x -q                   # Large lens test
uv run pytest tests/test_arithmetic_lens.py -x -q               # Another lens
uv run pytest tests/test_queries_dos.py -x -q                   # Query test
uv run pytest tests/test_schema_snapshot.py -x -q               # Fixed 16 occurrences
```

### Plan 3: Regression Tests

**Goal:** Prevent this class of bug forever. Uses custom exception hierarchy for assertions.

```python
# tests/test_pattern_loading_regression.py
"""Regression tests for pattern loading architecture.

Prevents the silent-failure bug where PatternStore returned []
for nonexistent directories, causing 891 tests to test nothing.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from alphaswarm_sol.queries.errors import (
    PatternDirectoryNotFoundError,
    EmptyPatternStoreError,
    PatternLoadError,
)
from alphaswarm_sol.queries.patterns import PatternStore, get_patterns
from tests.pattern_loader import _MIN_EXPECTED_PATTERNS


class TestPatternDiscovery:
    """Verify the canonical pattern loading path works."""

    def test_vulndocs_directory_exists(self) -> None:
        assert Path("vulndocs").exists(), "vulndocs/ directory must exist in project root"

    def test_get_patterns_returns_non_empty(self) -> None:
        patterns = get_patterns()
        assert len(patterns) >= _MIN_EXPECTED_PATTERNS, (
            f"Expected >= {_MIN_EXPECTED_PATTERNS} patterns, got {len(patterns)}"
        )

    def test_get_patterns_default_matches_explicit(self) -> None:
        default = get_patterns()
        explicit = get_patterns(Path("vulndocs"))
        assert len(default) == len(explicit)


class TestLoudFailure:
    """Verify pattern loading raises on bad paths — never silently returns []."""

    def test_get_patterns_raises_on_missing_dir(self) -> None:
        with pytest.raises(PatternDirectoryNotFoundError) as exc_info:
            get_patterns(Path("nonexistent_dir"))
        assert exc_info.value.path == Path("nonexistent_dir")

    def test_load_vulndocs_patterns_raises_on_missing_dir(self) -> None:
        with pytest.raises(PatternDirectoryNotFoundError):
            PatternStore.load_vulndocs_patterns(Path("nonexistent_dir"))

    def test_pattern_store_load_raises_on_missing_dir(self) -> None:
        with pytest.raises(PatternDirectoryNotFoundError):
            PatternStore(Path("nonexistent_dir")).load()

    def test_exception_hierarchy(self) -> None:
        """All pattern exceptions inherit from PatternLoadError."""
        with pytest.raises(PatternLoadError):
            get_patterns(Path("nonexistent_dir"))

    def test_pattern_store_rejects_non_path(self) -> None:
        with pytest.raises(TypeError):
            PatternStore("not_a_path")  # type: ignore[arg-type]


class TestNoLegacyPaths:
    """Ensure no code references the old 'patterns' directory."""

    def test_no_legacy_patterns_path_in_tests(self) -> None:
        """No test file should reference Path('patterns') — the old broken path."""
        violations: list[str] = []
        for test_file in sorted(Path("tests").glob("test_*.py")):
            source = test_file.read_text()
            if 'Path("patterns")' in source or "Path('patterns')" in source:
                violations.append(test_file.name)
        assert not violations, f"Legacy Path('patterns') found in: {violations}"

    def test_no_legacy_patterns_path_in_source(self) -> None:
        """No source file should default to Path('patterns')."""
        violations: list[str] = []
        for src_file in sorted(Path("src").rglob("*.py")):
            source = src_file.read_text()
            if 'Path("patterns")' in source or "Path('patterns')" in source:
                violations.append(str(src_file))
        assert not violations, f"Legacy Path('patterns') found in: {violations}"
```

**Verification:**
```bash
uv run pytest tests/test_pattern_loading_regression.py -v       # New regression tests
```

### Plan 4: Triage Remaining 333 Failures

**Goal:** Categorize every remaining test failure so downstream phases have a clean regression baseline.

**Why included (not deferred):** Without triage, Phase 3.1b inherits a test suite where 333 tests fail for unknown reasons. Any change in 3.1b that causes a test to fail could be dismissed as "probably one of the existing 333." This destroys the regression signal. 3.1b/3.1c need to know which failures are expected (XFAIL) vs unexpected (real regressions).

**Approach:** Run each affected test file individually, categorize each failure:

| Category | Estimated Count | Action | Marker |
|----------|----------------|--------|--------|
| PATTERN_GAP | ~120 | `@pytest.mark.xfail(reason="Known pattern quality gap: [id]")` | Track for 3.1c evaluation |
| MISSING_PATTERN_ID | ~50 | Delete tests — reference deprecated `ext-001..ext-072` numbering | Dead code |
| STALE_CODE | ~72 | Fix or delete — reference removed infrastructure | Dead code or simple fix |
| EXTERNAL_DEP | ~10 | `@pytest.mark.skipUnless(...)` with availability check | Skip when tool absent |
| OTHER | ~81 | Triage individually — fix if quick, xfail with reason if not | Case-by-case |

**Time-box:** Maximum 2 execution sessions. If not complete, create a follow-up phase.

**Priority order:** STALE_CODE (delete dead code first) → MISSING_PATTERN_ID (delete deprecated refs) → EXTERNAL_DEP (add skip markers) → PATTERN_GAP (xfail with tracking ID) → OTHER (case-by-case).

**Stopping criterion:** Phase is complete when every failure has a category label AND the triage report exists. Fixing all failures is NOT required — categorization IS.

**Output:** Failure triage report at `.vrs/debug/phase-3.1.1/failure-triage.md` with per-file breakdown.

**Verification:** `uv run pytest tests/ --tb=no -q` should show only XFAIL/SKIP markers for known issues. Zero unexplained failures.

---

## Execution Order

```
Plan 1 (exception hierarchy + canonical loader + source files)
  └──► Plan 2 (shared test loader + fix all test files)
        └──► Plan 3 (regression tests)
              └──► Plan 4 (triage remaining 333 failures)
```

Plans are sequential — each depends on the previous.

---

## Specific Tests to Run (NOT the Full Suite)

### After Plan 1 (source code changes):
```bash
uv run pytest tests/test_patterns.py -x -q                    # Core pattern matching
uv run pytest tests/test_schema_snapshot.py -x -q               # The 16 missed occurrences
uv run pytest tests/test_authority_lens.py -x -q                # Representative lens test
```

### After Plan 2 (test file changes):
```bash
uv run pytest tests/test_token_lens.py -x -q                   # Large lens test
uv run pytest tests/test_arithmetic_lens.py -x -q               # Another lens
uv run pytest tests/test_queries_dos.py -x -q                   # Query test
```

### After Plan 3 (regression tests):
```bash
uv run pytest tests/test_pattern_loading_regression.py -v       # New regression tests
```

---

## Decisions Required

### Decision 1: `executor.py` Modification (BLOCKING — Resolution Protocol)

**Constraint:** CLAUDE.md says "Never modify `executor.py` without explicit permission."
**Reality:** `executor.py` lines 65 and 273-280 must use `get_patterns()` for single source of truth.

**Resolution protocol:**
1. Before executing Plan 1, the executor MUST present the exact diff to the user and ask:
   "executor.py lines 65 and 273-280 need to call get_patterns(). This is a 2-line change. Approve?"
2. If approved → proceed with migration.
3. If denied → skip executor.py. Add `# TODO(3.1.1): migrate to get_patterns() when permitted` comments at both call sites. Document in drift log. Phase still passes (executor.py is 1 of 9 source files).

**Fallback path:** executor.py already defaults to `Path("vulndocs")` and uses the correct API (`load_vulndocs_patterns`). The only loss from skipping is that it doesn't use the canonical `get_patterns()` wrapper. This is acceptable — it's a style inconsistency, not a bug.

### Decision 2: Triage Scope (Plan 4) — RESOLVED

**Resolved: Option B (include Plan 4).** Triage is included because 3.1b needs a clean regression baseline. Without it, mystery failures mask new regressions.

### Decision 3: `PatternStore.load()` Strictness — RESOLVED

**Resolved:** `PatternDirectoryNotFoundError` on nonexistent path + `@deprecated` decorator. Clean, Pythonic, domain-specific exception hierarchy. No `strict=True` parameter complexity.

---

## Technical Details

### New Files

| File | Purpose | LOC (est.) |
|------|---------|------------|
| `src/alphaswarm_sol/queries/errors.py` | Custom exception hierarchy | ~30 |
| `tests/pattern_loader.py` | Shared `@lru_cache` test loader | ~20 |
| `tests/test_pattern_loading_regression.py` | Regression tests | ~60 |

### Modified Files (Source — 8 files)

| File | Change |
|------|--------|
| `src/alphaswarm_sol/queries/patterns.py` | Add `get_patterns()`, `_deprecated()`, harden `PatternStore` |
| `src/alphaswarm_sol/queries/executor.py` | Replace inline loading with `get_patterns()` (requires permission) |
| `src/alphaswarm_sol/queries/report.py` | Replace inline loading with `get_patterns()` |
| `src/alphaswarm_sol/queries/schema_snapshot.py` | Replace inline loading with `get_patterns()` |
| `src/alphaswarm_sol/queries/schema_hints.py` | Replace inline loading with `get_patterns()` |
| `src/alphaswarm_sol/queries/intent.py` | Replace inline loading with `get_patterns()` |
| `src/alphaswarm_sol/vql2/executor.py` | Replace inline loading with `get_patterns()` |
| `src/alphaswarm_sol/vql2/guidance.py` | Replace inline loading with `get_patterns()` |
| `src/alphaswarm_sol/queries/__init__.py` | Export `get_patterns` + exception hierarchy |

### All Pattern Loading Call Sites (Tests — 21+ files, 80+ occurrences)

Every one of these becomes `list(load_all_patterns())`:

- `tests/test_token_lens.py` (6 classes x setUp)
- `tests/test_external_influence_lens.py` (9 classes x setUp)
- `tests/test_upgradeability_lens.py` (5 classes x setUp)
- `tests/test_authority_lens.py` (2 classes x setUp)
- `tests/test_mev_lens.py` (2 classes x setUp)
- `tests/test_crypto_lens.py` (2 classes x setUp)
- `tests/test_arithmetic_lens.py` (2 classes x setUp)
- `tests/test_value_movement_lens.py` (2 classes x setUp)
- `tests/test_liveness_lens.py` (2 classes x setUp)
- `tests/test_patterns.py` (1 class x setUp)
- `tests/test_full_coverage_patterns.py` (1 class x setUp)
- `tests/test_defi_infrastructure_patterns.py` (1 class x setUp)
- `tests/test_queries_dos.py` (1 function)
- `tests/test_queries_dos_comprehensive.py` (7 functions)
- `tests/test_queries_crypto.py` (1 class x setUp)
- `tests/test_queries_liveness.py` (1 function)
- `tests/test_queries_proxy.py` (5 functions)
- `tests/test_ordering_upgradability_lens.py` (12 functions + 1 class x setUp)
- `tests/test_renamed_contracts.py` (3 classes x setUpClass)
- `tests/test_schema_snapshot.py` (16 occurrences — **also fixes Path("patterns") bug**)
- `tests/test_semgrep_parity.py` (17 functions)
- `tests/analyze_vm001_metrics.py` (1 function)

### Still Broken Files (Sed Missed)

| File | Issue | Occurrences |
|------|-------|-------------|
| `tests/test_schema_snapshot.py` | `pattern_dir=Path("patterns")` | 16 |
| `scripts/run_label_evaluation.py` | `default=Path("patterns")` in argparse | 1 |
| `tests/pattern_test_framework.py` | `PatternStore(Path("patterns")).load()` at line 165 | 1 |
| `tests/test_vm_002_semantic.py` | `Path("patterns/semantic")`, `Path("patterns/core")` (subdirectories) | 8 |

### Other Modified Files

| File | Change |
|------|--------|
| `scripts/run_label_evaluation.py` | `default=Path("patterns")` → `default=Path("vulndocs")` |

---

## Downstream Readiness Analysis

### Phase 3.1b Readiness

| Requirement | How 3.1.1 Satisfies It |
|-------------|------------------------|
| Trustworthy test suite | Pattern loading is loud-fail; no silent `[]` returns |
| Known regression baseline | Plan 4 triages all 333 failures into XFAIL/SKIP/DELETE |
| Shared test infrastructure | `tests/pattern_loader.py` establishes the caching pattern that 3.1b can build on |
| Clean imports | `get_patterns()` is the canonical API; 3.1b test infrastructure calls it |

### Phase 3.1c Readiness

| Requirement | How 3.1.1 Satisfies It |
|-------------|------------------------|
| Evaluation contracts reference patterns by ID | `get_patterns()` reliably loads all 466 patterns |
| Per-pattern evaluation tests | Pattern IDs are stable; loading is deterministic |
| Regression detection | Baseline failure count is known and categorized |

### Phase 3.2 Readiness

| Requirement | How 3.1.1 Satisfies It |
|-------------|------------------------|
| `build-kg → query patterns → create beads` pipeline | `get_patterns()` is the entry point for pattern queries |
| Pattern matching produces real findings | Silent `[]` returns eliminated; loading failures are immediate |

---

## Exit Gate

### Machine Checks (Automated)

| Check | Command | Pass Condition |
|-------|---------|----------------|
| Exception hierarchy exists | `python -c "from alphaswarm_sol.queries.errors import PatternLoadError, PatternDirectoryNotFoundError, EmptyPatternStoreError"` | No ImportError |
| `get_patterns()` works | `python -c "from alphaswarm_sol.queries.patterns import get_patterns; p = get_patterns(); assert len(p) >= 400"` | Returns >= 400 patterns (uses `_MIN_EXPECTED_PATTERNS` in code) |
| `get_patterns()` exported | `python -c "from alphaswarm_sol.queries import get_patterns"` | No ImportError |
| Loud failure on bad path | `python -c "from alphaswarm_sol.queries.patterns import get_patterns; from pathlib import Path; get_patterns(Path('nonexistent'))"` | Raises `PatternDirectoryNotFoundError` |
| No legacy `Path("patterns")` in tests | `grep -rn 'Path("patterns")' tests/test_*.py` | Zero matches |
| No legacy `Path("patterns")` in source | `grep -rn 'Path("patterns")' src/` | Zero matches |
| Regression tests pass | `uv run pytest tests/test_pattern_loading_regression.py -v` | All pass |
| Shared loader works | `python -c "from tests.pattern_loader import load_all_patterns; assert len(load_all_patterns()) >= 400"` | Returns >= 400 patterns |
| Existing tests still pass | Spot-check 5 representative test files | No new failures vs pre-3.1.1 baseline |
| Pattern loading < 2s | Timed `get_patterns()` call | < 2000ms |

### Human Checkpoint

| Check | Pass Condition |
|-------|----------------|
| Failure triage complete | `.vrs/debug/phase-3.1.1/failure-triage.md` exists with per-file breakdown |
| No unexplained failures | Every failure in the suite has a category label |
| `executor.py` change reviewed | If modification approved, confirm minimal + correct |

---

## Phase-Wide Strict Validation Contract

No plan is complete unless all artifacts below exist for that plan:

1. **Machine Gate Report**: `.vrs/debug/phase-3.1.1/gates/<plan-id>.json`
2. **Drift Log Entry**: `.vrs/debug/phase-3.1.1/drift-log.jsonl` (append-only)

Required machine gate fields:
- `plan_id`, `tests_run[]`, `tests_passed`, `tests_failed`, `duration_ms`
- `artifacts[]` (path + SHA256 hash for new files)
- `status` (`pass` / `fail`) with explicit failure reason if fail

---

## Anti-Patterns (Do NOT)

1. **Do NOT convert unittest.TestCase to pytest classes** — Massive refactor for zero value
2. **Do NOT add env var / config file for pattern paths** — YAGNI
3. **Do NOT run the full test suite** — Only affected files
4. **Do NOT over-abstract** — No `PatternSource` protocol, no plugin system, no loader registry
5. **Do NOT attempt to fix all 333 failures** — Categorize them; fix only STALE_CODE and MISSING_PATTERN_ID (deletions/simple fixes). PATTERN_GAP stays as xfail.

---

## Constraints

- Do NOT modify `builder_legacy.py` (legacy constraint)
- Do NOT modify `executor.py` without explicit permission (Decision 1 — **BLOCKING**)
- Do NOT change pattern file locations (`vulndocs/` structure is canonical)
- Do NOT change pattern YAML schema
- Do NOT convert `unittest.TestCase` to pytest-style classes
- Do NOT run the full test suite — only affected files
- Do NOT over-abstract (no Protocol, no plugin system, no loader registry)
- Tests that pass today must continue to pass

---

## Success Criteria

- [ ] `errors.py` exists with `PatternLoadError` → `PatternDirectoryNotFoundError` / `EmptyPatternStoreError`
- [ ] `get_patterns()` function exists as the single canonical entry point
- [ ] `get_patterns()` raises domain exceptions with `.path` attribute and `from e` chaining
- [ ] `PatternStore.__init__` validates `root` is `Path`
- [ ] `PatternStore.load()` has `@deprecated` decorator with migration message
- [ ] `PatternStore.load()` and `load_vulndocs_patterns()` raise `PatternDirectoryNotFoundError` on nonexistent paths
- [ ] `PatternEngine._load_patterns()` remains lenient but logs `WARNING` on missing dir
- [ ] All 8 source files use `get_patterns()` instead of direct `PatternStore` calls
- [ ] `queries/__init__.py` exports `get_patterns` and exception hierarchy
- [ ] `tests/pattern_loader.py` exists with `@lru_cache`, dogfoods `get_patterns()`
- [ ] All 21+ test files use `load_all_patterns()` instead of inline calls
- [ ] `test_schema_snapshot.py` fixed (16 occurrences of `Path("patterns")` removed)
- [ ] `scripts/run_label_evaluation.py` fixed (1 occurrence)
- [ ] Regression tests pass (10+ tests: directory exists, patterns load, no legacy paths, exceptions fire)
- [ ] No legacy `Path("patterns")` references in tests/ or src/
- [ ] All currently-passing tests still pass
- [ ] Pattern loading performance unchanged (< 2s for 466 patterns)
- [ ] 333 remaining failures categorized with per-file triage report
- [ ] Zero unexplained test failures in the suite

---

## Phase Dependencies

```
Phase 3.1 (COMPLETE)
  └──► Phase 3.1.1 (THIS — Pattern Loading Architecture Fix)
        └──► Phase 3.1b (Workflow Testing Harness — needs trustworthy test suite)
              └──► Phase 3.1c (Reasoning Evaluation — needs reliable pattern loading)
                    └──► Phase 3.2 (First Working Audit — needs get_patterns() pipeline)
```

**From prior phases:** Phase 3.1 sed fix (82 occurrences corrected), 466 active patterns from Phase 2.1 triage.
**External dependencies:** None. Pure Python stdlib + existing codebase.
**Feeds into:** 3.1b (clean test baseline), 3.1c (reliable pattern IDs for evaluation), 3.2 (pattern query pipeline).

---

## Research

See: `.planning/phases/3.1.1-pattern-loading-architecture/3.1.1-RESEARCH.md`

**Confidence:** HIGH — root cause fully understood, fix is straightforward, all call sites identified.

---

*Context created: 2026-02-11*
*Based on: root cause analysis, assumptions review, downstream readiness gap analysis*
