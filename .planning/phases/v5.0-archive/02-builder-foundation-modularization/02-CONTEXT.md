# Phase 2: Builder Foundation & Modularization - Context

**Gathered:** 2026-01-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Refactor builder.py (6,120 LOC) into modular architecture while adding proxy resolution, improved call tracking, determinism guarantees, and completeness reporting. Make the codebase easier to extend with Python best practices.

This phase combines the original Phase 2 (foundation features) and Phase 8 (modularization) into a single coherent effort - refactor AS we add features.

</domain>

<decisions>
## Implementation Decisions

### Proxy Resolution
- **Patterns supported:** All proxy patterns (EIP-1967 Transparent, EIP-2535 Diamond, UUPS, Beacon)
- **Unresolved proxies:** Best-effort with warning (don't fail, flag in completeness report)
- **Graph model:** Unified view - proxy node shows implementation's functions for simpler queries
- **Diamond facets:** Claude's discretion on handling multiple facets with same selector

### Call Tracking
- **Dynamic targets:** Try inference from context first, fall back to UNRESOLVED_TARGET
- **Library calls:** Claude's discretion on full resolution vs marking as library-mediated
- **Confidence scores:** Yes, per-edge confidence (HIGH=direct, MEDIUM=inferred, LOW=unresolved)
- **Callback patterns:** Bidirectional edges - track both outgoing call AND potential callback
- **Internal calls:** Full resolution required for all inter-contract calls within project
- **Inheritance:** Both representations - store inheritance explicitly, provide flattened view for queries

### Determinism
- **Stability requirements:** Full determinism - node IDs, edge ordering, graph fingerprint all stable
- **Schema versioning:** Claude's discretion on whether to include version in ID
- **Build manifests:** Claude's discretion on always vs optional flag

### Completeness Reporting
- **Report contents:** Comprehensive - unresolved references, coverage metrics, confidence breakdown
- **Output format:** YAML (user preference)
- **Failure thresholds:** Claude's discretion on warn-only vs configurable threshold

### Modularization
- **Module size:** Claude's discretion based on logical boundaries
- **Folder structure:** Claude's discretion based on codebase conventions
- **Best practices:** All modern Python practices required:
  - Type hints everywhere
  - Dataclasses/Pydantic models for structured data
  - Dependency injection for testability
- **API compatibility:** Clean slate preferred - redesign API from scratch, update all callers
- **Lazy loading:** Claude's discretion based on performance profiling
- **Caching strategy:** Claude's discretion based on common use cases

### Testing Strategy
- **Critical constraint:** Current test suite is slow - avoid bottleneck
- **Approach:** Granular, targeted tests (not slow comprehensive suites)
- **Focus:** Critical paths that ensure program doesn't break abruptly
- **Quality:** Easily verifiable tests that are still robust
- **Strategy:** Claude's discretion on snapshots vs property-based tests

### Claude's Discretion
The following areas are explicitly delegated to Claude during implementation:
- Diamond facet handling approach
- Library call resolution depth
- Schema versioning strategy
- Build manifest generation policy
- Completeness threshold behavior
- Module size and folder structure
- Lazy loading strategy
- Caching implementation
- Testing strategy (snapshots vs property-based)

</decisions>

<specifics>
## Specific Ideas

- User emphasized speed and efficiency for LLM orchestration context
- Testing should be smart and granular to avoid bottleneck
- Clean slate API redesign preferred over backwards compatibility hacks
- Full determinism is important for caching and testing reproducibility

</specifics>

<deferred>
## Deferred Ideas

- **Speed/efficiency optimization:** Noted for consideration, but primary focus is correct modular structure first. Performance optimization can follow in Phase 8 (Test Performance Research) or separate effort.

</deferred>

---

*Phase: 02-builder-foundation-modularization*
*Context gathered: 2026-01-20*
