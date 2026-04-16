# Phase 20.F: Performance and Scalability

**Goal:** Validate BSKG performance under realistic load and large datasets.

---

## F.1 Benchmarks

- Knowledge build time per 100 docs
- Query latency per vuln
- KG build time per 1,000 LOC
- Memory usage under large repos
- Subagent concurrency stability
- Context packaging latency (PPR/TOON)

---

## F.2 Targets

| Metric | Target |
|--------|--------|
| KG build (1k LOC) | < 30s |
| Query latency | < 200ms |
| Knowledge merge | < 5s per subcategory |
| Memory peak | < 4GB |
| Subagent errors | 0% |
| Context packaging | < 80ms |

---

## F.3 Output Template

Store in `task/4.0/phases/phase-20/artifacts/PERFORMANCE_RESULTS.md`:

```
- test: build-kg
  input_size: <loc>
  time_seconds: <float>
  memory_peak_mb: <int>
```

---

## F.4 Failure Handling

- Performance regression over 2x baseline is **Critical**
- Memory leaks are **Blocker**
