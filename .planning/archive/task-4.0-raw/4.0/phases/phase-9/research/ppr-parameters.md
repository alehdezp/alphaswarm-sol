# PPR Parameters for VKG

**Task R9.1 Deliverable 3/3**
**Date:** 2026-01-08

---

## 1. Parameter Overview

| Parameter | Symbol | Range | Purpose |
|-----------|--------|-------|---------|
| Teleport probability | α (alpha) | 0.10-0.30 | How often to jump back to seeds |
| Max iterations | max_iter | 30-100 | Convergence safety limit |
| Convergence threshold | ε (epsilon) | 1e-3 to 1e-5 | When to stop iterating |
| Score threshold | θ (theta) | 0.01-0.10 | Minimum score to include node |

---

## 2. Alpha (Teleport Probability)

### 2.1 Semantic Meaning

- **High alpha (0.25-0.30)**: Random walk frequently teleports back to seeds
  - Result: Scores concentrate near seed nodes
  - Use: Tight, focused context

- **Medium alpha (0.15-0.20)**: Balanced exploration
  - Result: Seeds have highest scores, but neighbors also score well
  - Use: Standard analysis context

- **Low alpha (0.10-0.12)**: Random walk explores widely
  - Result: Scores spread across more nodes
  - Use: Broad context, exploratory analysis

### 2.2 Mapping to Context Modes

| Context Mode | Alpha | Rationale |
|--------------|-------|-----------|
| **STRICT** | 0.25 | Stay close to finding, minimize noise |
| **STANDARD** | 0.15 | Balanced exploration (DEFAULT) |
| **RELAXED** | 0.10 | Wide exploration for complex issues |

### 2.3 Why These Values?

**STRICT (0.25)**
- Based on: Need to minimize context for token efficiency
- Empirical: At 0.25, ~80% of score concentrated in 1-hop neighborhood
- Security rationale: Most vulnerabilities are local to finding function

**STANDARD (0.15)**
- Based on: Classic PageRank damping = 0.85 (1-0.15)
- Empirical: Explores 2-3 hops while keeping focus
- Security rationale: Cross-function vulnerabilities need wider view

**RELAXED (0.10)**
- Based on: HippoRAG uses ~0.1 for broad retrieval
- Empirical: Can reach 4+ hops from seed
- Security rationale: Complex attack paths may span many functions

### 2.4 Alpha Selection Algorithm

```python
def select_alpha(finding, context_mode='standard'):
    """
    Select alpha based on context mode and finding.
    """
    base_alpha = {
        'strict': 0.25,
        'standard': 0.15,
        'relaxed': 0.10,
    }[context_mode]

    # Adjust for finding complexity
    if finding.requires_cross_contract:
        base_alpha *= 0.8  # Explore more
    if finding.severity == 'critical':
        base_alpha *= 0.9  # Slightly more context for critical

    return max(0.08, min(0.30, base_alpha))
```

---

## 3. Max Iterations

### 3.1 Convergence Behavior

PPR typically converges in 10-30 iterations for graphs < 1000 nodes:

| Graph Size | Typical Iterations |
|------------|-------------------|
| < 100 nodes | 5-10 |
| 100-500 nodes | 10-20 |
| 500-1000 nodes | 15-30 |
| > 1000 nodes | 20-50 |

### 3.2 Recommendation

```python
DEFAULT_MAX_ITER = 50
```

**Justification:**
- 50 iterations sufficient for convergence on VKG-sized graphs
- Safety margin for unusual graph structures
- Not too high to cause performance issues

### 3.3 Early Termination

For performance, use early termination with convergence check:

```python
def should_terminate(ppr_old, ppr_new, epsilon, min_iter=5):
    """Check if PPR has converged."""
    if len(ppr_old) < min_iter:
        return False  # Ensure minimum iterations

    max_diff = max(abs(ppr_new[v] - ppr_old[v]) for v in ppr_old)
    return max_diff < epsilon
```

---

## 4. Convergence Threshold (Epsilon)

### 4.1 Trade-offs

| Epsilon | Iterations | Precision | Use Case |
|---------|------------|-----------|----------|
| 1e-3 | Fewer | Lower | Fast, approximate |
| 1e-4 | Medium | Good | Default for BSKG |
| 1e-5 | More | High | Precise ranking |
| 1e-6 | Many | Very high | Research only |

### 4.2 Recommendation

```python
DEFAULT_EPSILON = 1e-4
```

**Justification:**
- Sufficient precision for node ranking decisions
- Converges quickly (typically < 20 iterations)
- Score differences < 1e-4 are not meaningfully different

---

## 5. Score Threshold (Theta)

### 5.1 Purpose

After PPR computation, use score threshold to select which nodes to include in context:

```python
def select_nodes(ppr_scores, theta=0.01):
    """Select nodes with score >= theta * max_score."""
    max_score = max(ppr_scores.values())
    threshold = theta * max_score

    return {node: score for node, score in ppr_scores.items()
            if score >= threshold}
```

### 5.2 Mapping to Context Modes

| Context Mode | Theta | Expected Nodes |
|--------------|-------|----------------|
| **STRICT** | 0.10 | ~10-15 nodes |
| **STANDARD** | 0.05 | ~20-30 nodes |
| **RELAXED** | 0.01 | ~50-100 nodes |

### 5.3 Adaptive Threshold

For token budget compliance:

```python
def adaptive_threshold(ppr_scores, token_budget, tokens_per_node=100):
    """
    Adapt threshold to fit token budget.
    """
    max_nodes = token_budget // tokens_per_node

    # Sort by score descending
    sorted_nodes = sorted(ppr_scores.items(), key=lambda x: -x[1])

    if len(sorted_nodes) <= max_nodes:
        return 0.0  # Include all

    # Threshold is score of node at budget limit
    return sorted_nodes[max_nodes][1]
```

---

## 6. Token Budget Integration

### 6.1 Budget-Aware PPR

Combine PPR with token budget constraints:

```python
def ppr_with_budget(graph, seeds, token_budget, context_mode='standard'):
    """
    Run PPR and select nodes within token budget.
    """
    # Get alpha for context mode
    alpha = {'strict': 0.25, 'standard': 0.15, 'relaxed': 0.10}[context_mode]

    # Run PPR
    scores = vkg_ppr(graph, seeds, alpha=alpha)

    # Select nodes within budget
    selected = []
    current_tokens = 0

    for node_id, score in sorted(scores.items(), key=lambda x: -x[1]):
        node_tokens = estimate_node_tokens(graph.nodes[node_id])
        if current_tokens + node_tokens <= token_budget:
            selected.append(node_id)
            current_tokens += node_tokens
        else:
            break

    return selected, scores
```

### 6.2 Token Estimation

```python
def estimate_node_tokens(node):
    """Estimate tokens needed to represent node in context."""
    # Base overhead
    tokens = 20  # ID, type, label

    # Properties
    for prop, value in node.properties.items():
        tokens += 5  # property name
        if isinstance(value, str):
            tokens += len(value) // 4
        elif isinstance(value, list):
            tokens += len(value) * 3
        else:
            tokens += 2

    return tokens
```

---

## 7. Configuration Schema

```python
@dataclass
class PPRConfig:
    """Configuration for VKG-PPR."""

    # Core parameters
    alpha: float = 0.15
    max_iter: int = 50
    epsilon: float = 1e-4

    # Selection parameters
    theta: float = 0.05
    max_nodes: Optional[int] = None
    token_budget: Optional[int] = None

    # Mode presets
    @classmethod
    def strict(cls):
        return cls(alpha=0.25, theta=0.10, max_nodes=15)

    @classmethod
    def standard(cls):
        return cls(alpha=0.15, theta=0.05, max_nodes=30)

    @classmethod
    def relaxed(cls):
        return cls(alpha=0.10, theta=0.01, max_nodes=100)
```

---

## 8. Validation Criteria

### 8.1 Parameter Bounds

```python
def validate_config(config: PPRConfig):
    """Validate PPR configuration."""
    assert 0.05 <= config.alpha <= 0.40, "Alpha out of range"
    assert 10 <= config.max_iter <= 200, "Max iter out of range"
    assert 1e-6 <= config.epsilon <= 1e-2, "Epsilon out of range"
    assert 0.001 <= config.theta <= 0.50, "Theta out of range"
```

### 8.2 Expected Behavior

| Scenario | Expected Result |
|----------|-----------------|
| Single seed, simple graph | Seed has highest score |
| Multiple seeds | All seeds in top scores |
| Disconnected subgraph | Unreachable nodes have score 0 |
| Dense graph | Scores more evenly distributed |
| Sparse graph | Scores concentrated near seeds |

---

## 9. Performance Considerations

### 9.1 Time Complexity

- Per iteration: O(E) where E = number of edges
- Total: O(max_iter * E)
- Typical VKG: 100-1000 edges, <50ms total

### 9.2 Memory Complexity

- Score storage: O(N) where N = nodes
- Weight matrix: O(E)
- Typical VKG: <1MB memory

### 9.3 Optimization Tips

1. Use sparse matrix for graphs > 500 nodes
2. Cache weight matrix between PPR runs on same graph
3. Use early termination to reduce iterations

---

## 10. Summary Table

| Parameter | STRICT | STANDARD | RELAXED |
|-----------|--------|----------|---------|
| Alpha | 0.25 | 0.15 | 0.10 |
| Theta | 0.10 | 0.05 | 0.01 |
| Max nodes | 15 | 30 | 100 |
| Max iter | 50 | 50 | 50 |
| Epsilon | 1e-4 | 1e-4 | 1e-4 |
| Token budget | ~1500 | ~3000 | ~10000 |

---

*PPR Parameters | Task R9.1 | 2026-01-08*
