# GAP-04: Graph fingerprint method — what is fingerprint_graph and what replaces it?

**Created by:** improve-phase
**Source:** P1-IMP-06
**Priority:** MEDIUM
**Status:** resolved
**depends_on:** []

## Question

What is the current `fingerprint_graph` function? What makes it "legacy"? Is there a replacement? The proposed fix in P1-IMP-06 (content-based fingerprint with sorted node properties hash) may conflict with the actual function signature or be superseded by a newer method.

Specific sub-questions:
1. Where is `fingerprint_graph` defined in the codebase?
2. What does it compute (hash type, what properties are included)?
3. Is it deterministic (sorted keys, no timestamps)?
4. Is there a newer/recommended fingerprinting approach?

## Context

Plan 01 includes "fingerprint verification" and "CORPUS drift check" to verify graph stability between baseline and re-run. Research flags "using legacy fingerprint_graph" as an anti-pattern. A false drift detection halts the experiment unnecessarily; a missed drift corrupts the delta measurement.

## Research Approach

1. Search the codebase for `fingerprint_graph` function definition
2. Check for any graph hashing or fingerprinting utilities
3. Look at how graph identity/equality is currently checked
4. Check if there are any comments marking it as deprecated/legacy

## Findings

**Confidence: HIGH** — both functions are clearly defined in the same file with distinct interfaces and purposes.

### Two functions exist in the same file

Both live in `src/alphaswarm_sol/kg/fingerprint.py`. The file is cleanly divided into two sections with explicit comments.

### 1. `graph_fingerprint(graph)` — the CURRENT function (lines 157-212)

**Location:** `src/alphaswarm_sol/kg/fingerprint.py:157`

- **Input:** `KnowledgeGraph` object (the OO schema type from `alphaswarm_sol.kg.schema`)
- **Output:** `str` — a 64-character SHA256 hex digest
- **Algorithm:**
  1. Optionally includes schema version prefix (`schema:2.0`)
  2. Iterates nodes in **sorted order by node ID**, hashes `node_id + label + JSON(properties, sort_keys=True)`
  3. Iterates edges in **sorted order by edge ID**, hashes `edge_id + source + target + type`
  4. Iterates rich_edges in **sorted order by ID**, hashes similarly
  5. Excludes unstable keys via `_UNSTABLE_KEYS` frozenset: `file_path`, `file`, `absolute_path`, `build_time`, `timestamp`, `line_start`, `line_end`
- **Determinism:** Yes — sorted keys, sorted iteration, no timestamps, explicit unstable-key exclusion
- **Section header comment on line 126:** `# Graph Fingerprinting (KnowledgeGraph objects)`

### 2. `fingerprint_graph(graph_data)` — the LEGACY function (lines 292-351)

**Location:** `src/alphaswarm_sol/kg/fingerprint.py:292`

- **Input:** `dict` — a raw dict-based graph representation (pre-OO schema)
- **Output:** `dict` — a dictionary with keys: `version`, `full_hash`, `node_count`, `edge_count`, `node_type_counts`, `semantic_summary`, `node_fingerprints` (first 10)
- **Algorithm:**
  1. Extracts `graph.nodes` and `graph.edges` from dict
  2. Per-node fingerprint via `fingerprint_node()` which only hashes a hardcoded list of 20 semantic property keys
  3. Per-edge fingerprint via `fingerprint_edge()` which hashes type/source/target/label
  4. Sorts node and edge fingerprints, then hashes the combined sorted lists
  5. Returns a rich dict with counts and semantic summary
- **Determinism:** Yes — uses sorted keys, `json.dumps(sort_keys=True)`, no timestamps
- **Section header comment on line 216:** `# Legacy Fingerprinting (dict-based graphs)`
- **Why it's "legacy":** It operates on raw dicts (the old graph format), not `KnowledgeGraph` objects. It also returns a dict instead of a simple hex string, making equality comparison less straightforward (`fp["full_hash"]` vs direct `==`).

### 3. Usage in the codebase

| Function | Where used | Import count |
|----------|-----------|--------------|
| `graph_fingerprint` (OO) | `tests/test_builder/test_integration.py` | 1 test file |
| `fingerprint_graph` (legacy) | `tests/test_fingerprint.py`, `tests/test_golden_snapshots.py`, `.github/workflows/determinism.yml` | 3 files |

The legacy function has **more** active consumers, including the CI determinism workflow. The OO function is only used in one integration test.

### 4. Companion functions

- `compare_fingerprints(fp1, fp2)` (line 354) — works with the **legacy** dict format only
- `verify_determinism(graph_data, runs=10)` (line 402) — calls `fingerprint_graph` (legacy), so also dict-based
- `save_fingerprint` / `load_fingerprint` — work with dict format (legacy)

### 5. Key difference summary

| Aspect | `graph_fingerprint` (OO) | `fingerprint_graph` (legacy) |
|--------|--------------------------|------------------------------|
| Input | `KnowledgeGraph` object | `dict` |
| Output | `str` (64-char hex) | `dict` (with `full_hash` key) |
| Equality check | `fp1 == fp2` | `fp1["full_hash"] == fp2["full_hash"]` |
| Properties included | ALL stable properties | 20 hardcoded semantic keys |
| Rich edges | Yes | No |
| Schema version | Yes (prefix) | No |
| Section label | "Graph Fingerprinting" | "Legacy Fingerprinting" |

## Recommendation

### For Phase 3.1e Plan 01: Use `graph_fingerprint` (the OO variant)

**Use:** `from alphaswarm_sol.kg.fingerprint import graph_fingerprint`

**Why:**
1. It operates on `KnowledgeGraph` objects, which is what `VKGBuilder().build()` returns — no conversion needed.
2. It returns a simple 64-char hex string, so drift comparison is `baseline_fp == rerun_fp` — no dict key access, no ambiguity.
3. It hashes ALL stable properties (not just 20 hardcoded ones), so it catches more kinds of graph drift.
4. It includes rich edges and schema version, making it a more complete fingerprint.
5. The file's own section header explicitly labels the other function as "Legacy."

**Prescriptive guidance for Plan 01 baseline scripts:**

```python
from alphaswarm_sol.kg.fingerprint import graph_fingerprint

# After building graph
graph = builder.build(contract_path)
fp = graph_fingerprint(graph)  # Returns 64-char hex string

# Store in baseline JSON
baseline_entry = {
    "contract": contract_name,
    "graph_fingerprint": fp,          # 64-char hex string
    "fingerprint_method": "graph_fingerprint",  # Record which method was used
    "node_count": len(graph.nodes),
    "edge_count": len(graph.edges),
}

# Drift check on re-run
assert rerun_fp == baseline_fp, f"Graph drift detected: {baseline_fp} != {rerun_fp}"
```

**Do NOT use:**
- `fingerprint_graph(graph_data)` — legacy dict-based, returns dict, misses rich edges
- `verify_determinism()` — calls the legacy function internally
- `compare_fingerprints()` — works with legacy dict format only

**Migration note:** The CI determinism workflow (`.github/workflows/determinism.yml`) and `tests/test_golden_snapshots.py` still use the legacy function. These should be migrated to `graph_fingerprint` in a future cleanup, but that is out of scope for 3.1e.
