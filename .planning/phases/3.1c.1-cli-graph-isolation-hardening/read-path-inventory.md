# Read-Path Inventory — Phase 3.1c.1

**Created:** Task 1, Plan 01
**Shared by:** Plan 01 (vulndocs), Plan 02 (graph)
**Last updated:** Task 6, Plan 01 — post-migration status update

## vulndocs Callsites (Plan 01 ownership)

| File | Line | Current Assumption | Status | Migration Target |
|------|------|--------------------|--------|------------------|
| `src/alphaswarm_sol/queries/patterns.py` | 32 | `_DEFAULT_VULNDOCS = Path("vulndocs")` — cwd-relative | **MIGRATED** | Removed constant; `get_patterns()` now calls `vulndocs_read_path()` |
| `src/alphaswarm_sol/core/availability.py` | 454-487 | `Path("vulndocs")` — cwd-relative local project check | **MIGRATED** | `vulndocs_read_path()` via Traversable iterdir() |
| `src/alphaswarm_sol/learning/bootstrap.py` | 262 | `Path("vulndocs")` — docstring example, passed as default arg | **MIGRATED** | Docstring updated to show `vulndocs_read_path()` |
| `src/alphaswarm_sol/learning/bootstrap.py` | 303 | `Path("vulndocs")` — `__main__` default | **MIGRATED** | `vulndocs_read_path()` in `__main__` block |
| `src/alphaswarm_sol/investigation/loader.py` | 27-28 | `Path("vulndocs/...")` — docstring example | VERIFIED-OK | Docstring only |
| `src/alphaswarm_sol/investigation/loader.py` | 106 | `Path(__file__).parent.parent.parent.parent / "vulndocs"` — ad-hoc __file__-relative | **MIGRATED** | `vulndocs_read_path()` in `load_builtin()` |
| `src/alphaswarm_sol/agents/context/extractor.py` | 196 | `vulndocs_root: Path = Path("vulndocs")` — constructor default | **MIGRATED** | `vulndocs_root: Path | None = None`, resolves via `vulndocs_read_path()` |
| `src/alphaswarm_sol/agents/context/extractor.py` | 550 | `vulndocs_root: Path = Path("vulndocs")` — constructor default | **MIGRATED** | `vulndocs_root: Path | None = None`, resolves via `vulndocs_read_path()` |
| `src/alphaswarm_sol/agents/orchestration/sub_coordinator.py` | 116 | `vulndocs_root or Path("vulndocs")` — constructor fallback | **MIGRATED** | `vulndocs_read_path()` fallback |
| `src/alphaswarm_sol/vulndocs/ingestion/categorizer.py` | 156 | `vulndocs_root or Path("vulndocs")` — constructor fallback | **MIGRATED** | `vulndocs_write_path()` fallback |
| `src/alphaswarm_sol/vulndocs/ingestion/ingester.py` | 29 | `Path("vulndocs")` — IngestionConfig default | **MIGRATED** | `_default_write_path()` → `vulndocs_write_path()` |
| `src/alphaswarm_sol/vulndocs/ingestion/ingester.py` | 137 | `Path("vulndocs")` — docstring example | VERIFIED-OK | Docstring only |
| `src/alphaswarm_sol/vulndocs/ingestion/ingester.py` | 158 | `vulndocs_root or Path("vulndocs")` — URLIngester fallback | **MIGRATED** | `_default_write_path()` → `vulndocs_write_path()` |
| `src/alphaswarm_sol/vulndocs/ingestion/__init__.py` | 14 | `Path("vulndocs")` — docstring example | VERIFIED-OK | Docstring only |
| `src/alphaswarm_sol/testing/mutations.py` | 480 | `PatternStore.load_vulndocs_patterns(Path("vulndocs"))` — cwd-relative | **MIGRATED** | `vulndocs_read_path()` inline |
| `src/alphaswarm_sol/vulndocs/discovery.py` | 85 | `Path("vulndocs")` — docstring example | VERIFIED-OK | Docstring only |
| `src/alphaswarm_sol/vulndocs/discovery.py` | 133 | `Path("vulndocs")` — docstring example | VERIFIED-OK | Docstring only |

**Summary:** 12 **MIGRATED**, 5 VERIFIED-OK (docstrings only). Zero NEEDS-MIGRATION remaining.

## Graph Callsites (Plan 02 ownership)

| File | Line | Current Assumption | Status | Migration Target |
|------|------|--------------------|--------|------------------|
| `src/alphaswarm_sol/cli/main.py` | 576 | `Path(".vrs/graphs/graph.json")` — cwd-relative default | DEFERRED-TO-PLAN-02 | graph resolution |
| `src/alphaswarm_sol/cli/main.py` | 659 | `Path(".vrs/graphs/graph.json")` — cwd-relative default | DEFERRED-TO-PLAN-02 | graph resolution |
| `src/alphaswarm_sol/cli/main.py` | 771 | `Path(".vrs/graphs/graph.json")` — cwd-relative default | DEFERRED-TO-PLAN-02 | graph resolution |
| `src/alphaswarm_sol/cli/main.py` | 895 | `Path(".vrs/graphs/graph.json")` — cwd-relative default | DEFERRED-TO-PLAN-02 | graph resolution |
| `src/alphaswarm_sol/cli/doctor.py` | 105 | `self.vkg_dir / "graphs" / "graph.json"` — relative to vkg_dir | DEFERRED-TO-PLAN-02 | graph resolution |
| `src/alphaswarm_sol/kg/store.py` | 76-84 | `self.root / "graph.toon"` / `self.root / "graph.json"` — relative to store root | VERIFIED-OK | Root-based, not cwd |

**Summary:** 5 DEFERRED-TO-PLAN-02, 1 VERIFIED-OK

## Verification

Post-migration grep verification:
```
grep -rn 'Path("vulndocs")' src/  →  only docstrings and resolution.py module docstring
grep -rn "Path('vulndocs')" src/  →  zero matches
```
All production code paths now use `vulndocs_read_path()` or `vulndocs_write_path()`.
