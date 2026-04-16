# [P0-T4] Knowledge Graph Persistence

**Phase**: 0 - Knowledge Foundation
**Task ID**: P0-T4
**Status**: NOT_STARTED
**Priority**: HIGH
**Estimated Effort**: 2-3 days
**Actual Effort**: -

---

## Executive Summary

Implement persistence layer for all three knowledge graphs (Domain, Adversarial, Cross-Graph edges). This enables caching knowledge graphs between sessions, sharing pre-built KGs, and incremental updates without full rebuilds.

---

## Dependencies

### Required Before Starting
- [ ] [P0-T1] Domain Knowledge Graph
- [ ] [P0-T2] Adversarial Knowledge Graph
- [ ] [P0-T3] Cross-Graph Linker

### Blocks These Tasks
- [P0-T5] Integration Test - Needs persistence for test fixtures
- All subsequent phases - Benefit from cached KGs

---

## Objectives

### Primary Objectives
1. JSON serialization/deserialization for all KG types
2. Version-controlled schema for forward compatibility
3. Incremental save/load (don't reload unchanged graphs)
4. Compression for large graphs

### Stretch Goals
1. SQLite backend for query-on-demand
2. Graph diff computation for incremental updates

---

## Technical Design

### File Format

```json
{
  "schema_version": "3.5.0",
  "graph_type": "domain|adversarial|cross_graph",
  "created_at": "2026-01-02T00:00:00Z",
  "metadata": {...},
  "content": {
    "specifications": [...],
    "primitives": [...],
    // or
    "patterns": [...],
    "exploits": [...],
    // or
    "edges": [...]
  }
}
```

### New Files
- `src/true_vkg/knowledge/persistence.py` - Main implementation
- `tests/test_3.5/test_persistence.py` - Tests

---

## Success Criteria

- [ ] All KG types serialize/deserialize correctly
- [ ] Round-trip preserves all data
- [ ] Version migration supported
- [ ] Compressed files < 50% of uncompressed
- [ ] Load time < 1s for typical graphs

---

## Validation Tests

```python
def test_round_trip_domain_kg():
    """Test Domain KG survives serialize/deserialize."""
    kg = DomainKnowledgeGraph()
    kg.load_all()

    # Save
    save_knowledge_graph(kg, "/tmp/domain_kg.json.gz")

    # Load
    kg2 = load_knowledge_graph("/tmp/domain_kg.json.gz")

    # Verify
    assert len(kg2.specifications) == len(kg.specifications)
    assert kg2.specifications["erc20"].invariants == kg.specifications["erc20"].invariants

def test_version_migration():
    """Test loading old schema version."""
    # Create v3.4 format file
    old_format = {"schema_version": "3.4.0", ...}

    # Should upgrade automatically
    kg = load_knowledge_graph(old_format)
    assert kg.schema_version == "3.5.0"
```

---

## Implementation Plan

### Phase 1: Basic Serialization (1 day)
- [ ] Implement `to_dict()` / `from_dict()` for all dataclasses
- [ ] Implement `save_knowledge_graph()` / `load_knowledge_graph()`
- [ ] Add gzip compression support

### Phase 2: Version Management (1 day)
- [ ] Define schema version constants
- [ ] Implement migration functions
- [ ] Add validation on load

### Phase 3: Optimization (0.5 days)
- [ ] Add incremental save (only changed portions)
- [ ] Add lazy loading support
- [ ] Performance benchmarks

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2026-01-02 | Created | Claude |
