# PPR Algorithm Specification for VKG

**Task R9.1 Deliverable 1/3**
**Date:** 2026-01-08

---

## 1. Mathematical Foundation

### 1.1 Standard PageRank

PageRank computes a stationary distribution over nodes based on random walk:

```
PR(v) = (1-d)/N + d * Σ[PR(u) / out_degree(u)] for all u → v
```

Where:
- `d` = damping factor (probability of following an edge)
- `1-d` = teleport probability (probability of jumping to random node)
- `N` = total number of nodes
- `out_degree(u)` = number of outgoing edges from node u

### 1.2 Personalized PageRank (PPR)

PPR modifies the teleport distribution to favor specific "seed" nodes:

```
PPR(v, S) = (1-d) * p(v|S) + d * Σ[PPR(u, S) * w(u,v) / W_out(u)]
```

Where:
- `S` = set of seed nodes
- `p(v|S)` = personalization distribution (1/|S| if v ∈ S, else 0)
- `w(u,v)` = edge weight from u to v
- `W_out(u)` = sum of weights of all outgoing edges from u (normalization)

### 1.3 VKG-PPR Formulation

For BSKG security analysis, we use weighted PPR with security-aware edge weights:

```
PPR_VKG(v, seeds, α) = α * teleport(v, seeds) + (1-α) * propagate(v)
```

Where:
- `α` = teleport probability (higher = closer to seeds)
- `teleport(v, seeds)` = 1/|seeds| if v ∈ seeds, else 0
- `propagate(v)` = Σ[PPR_VKG(u) * normalized_weight(u, v)]

---

## 2. Algorithm Implementation

### 2.1 Power Iteration Method

```python
def vkg_ppr(graph, seeds, alpha=0.15, max_iter=50, epsilon=1e-4):
    """
    Compute Personalized PageRank for VKG.

    Args:
        graph: KnowledgeGraph with weighted edges
        seeds: List of seed node IDs
        alpha: Teleport probability (0.1-0.3)
        max_iter: Maximum iterations
        epsilon: Convergence threshold

    Returns:
        Dict[str, float]: PPR scores per node
    """
    nodes = list(graph.nodes.keys())
    n = len(nodes)

    # Initialize uniform distribution
    ppr = {node_id: 1.0 / n for node_id in nodes}

    # Compute personalization vector
    personalization = {node_id: 0.0 for node_id in nodes}
    for seed in seeds:
        if seed in personalization:
            personalization[seed] = 1.0 / len(seeds)

    # Precompute normalized weights
    out_weights = precompute_normalized_weights(graph)

    for iteration in range(max_iter):
        ppr_new = {}

        for v in nodes:
            # Teleport component
            teleport = alpha * personalization[v]

            # Propagation component
            propagate = 0.0
            for u in get_predecessors(graph, v):
                if u in ppr and (u, v) in out_weights:
                    propagate += ppr[u] * out_weights[(u, v)]
            propagate *= (1 - alpha)

            ppr_new[v] = teleport + propagate

        # Check convergence
        max_diff = max(abs(ppr_new[v] - ppr[v]) for v in nodes)
        if max_diff < epsilon:
            return ppr_new

        ppr = ppr_new

    return ppr
```

### 2.2 Weight Normalization

**CRITICAL**: Weights must be normalized per source node to ensure valid probability distribution:

```python
def precompute_normalized_weights(graph):
    """
    Normalize edge weights per source node.

    For each source node, weights of outgoing edges sum to 1.0.
    """
    out_weights = {}

    for edge_id, edge in graph.edges.items():
        source = edge.source
        target = edge.target
        weight = compute_edge_weight(edge)
        out_weights[(source, target)] = weight

    # Normalize per source
    for source in graph.nodes:
        total = sum(w for (s, t), w in out_weights.items() if s == source)
        if total > 0:
            for (s, t) in list(out_weights.keys()):
                if s == source:
                    out_weights[(s, t)] /= total

    return out_weights
```

---

## 3. Convergence Criteria

### 3.1 Standard Criterion

```
converged = max_i |PPR_new[i] - PPR_old[i]| < epsilon
```

### 3.2 Recommended Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `epsilon` | 1e-4 | Fast convergence, sufficient precision |
| `max_iter` | 50 | Safety limit, typically converges in 10-20 |

### 3.3 Early Termination

For performance, consider early termination when:
1. Top-k scores have stabilized
2. All scores in target set have converged

---

## 4. Sparse Matrix Optimization

For large graphs (>1000 nodes), use sparse matrix representation:

```python
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import spsolve

def ppr_sparse(adjacency_matrix, personalization, alpha=0.15):
    """
    Efficient PPR using sparse linear algebra.

    Solves: PPR = alpha * personalization + (1-alpha) * A^T * PPR
    Rearranged: (I - (1-alpha) * A^T) * PPR = alpha * personalization
    """
    n = adjacency_matrix.shape[0]
    I = sparse.eye(n)

    # Row-normalize adjacency matrix
    row_sums = np.array(adjacency_matrix.sum(axis=1)).flatten()
    row_sums[row_sums == 0] = 1  # Avoid division by zero
    D_inv = sparse.diags(1.0 / row_sums)
    A_norm = D_inv @ adjacency_matrix

    # Solve linear system
    M = I - (1 - alpha) * A_norm.T
    ppr = spsolve(M.tocsr(), alpha * personalization)

    return ppr
```

---

## 5. VKG-Specific Considerations

### 5.1 Handling Dangling Nodes

Nodes with no outgoing edges (dangling nodes) should distribute probability uniformly:

```python
if out_degree(u) == 0:
    # Distribute to all nodes uniformly
    propagate += ppr[u] / n
```

### 5.2 Bidirectional Edges

VKG graphs may have bidirectional relationships. Handle by:
1. Treating as separate directed edges
2. Weighting return edges lower (0.5x) to prefer forward exploration

### 5.3 Multi-Type Edges

VKG has multiple edge types (CALLS, WRITES_STATE, etc.). Handle by:
1. Computing separate PPR per edge type (for analysis)
2. Or combining with edge-type weights (for unified scoring)

---

## 6. Test Case Validation

### Test Case 1: Simple Chain

```
A --1.0--> B --1.0--> C
```

Seeds: [A], alpha=0.2

Manual calculation:
- PPR(A) = 0.2 * 1.0 + 0.8 * 0 = 0.20
- PPR(B) = 0.2 * 0 + 0.8 * PPR(A) = 0.16
- PPR(C) = 0.2 * 0 + 0.8 * PPR(B) = 0.128

(After convergence, scores will be higher due to normalization)

### Test Case 2: With Branching

```
    B
   /
A --
   \
    C
```

Seeds: [A], alpha=0.15, equal weights

PPR(B) should equal PPR(C) due to symmetry.

### Test Case 3: Cycle

```
A --> B --> C --> A
```

Seeds: [A], alpha=0.15

All nodes should have positive scores, with A highest.

---

## 7. Integration Points

### 7.1 Input from VKG

- Nodes from `graph.nodes`
- Edges from `graph.edges`
- Risk scores from `edge.properties.get('risk_score', 0.0)`

### 7.2 Output to Subgraph Extraction

- PPR scores used to rank nodes for inclusion
- Threshold: include nodes with PPR > 0.01 * max_ppr

### 7.3 Output to Context Optimization

- Higher PPR = more relevant to finding
- Used to prioritize which nodes get full vs. summary context

---

*PPR Algorithm Specification | Task R9.1 | 2026-01-08*
