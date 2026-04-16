# Edge Weight Strategy for VKG-PPR

**Task R9.1 Deliverable 2/3**
**Date:** 2026-01-08

---

## 1. Design Philosophy

Edge weights in VKG-PPR serve to bias the random walk toward security-relevant paths:

1. **Higher weight** = more likely to traverse = more security-relevant
2. **Lower weight** = less likely to traverse = less relevant or guarded
3. **All weights > 0** = ensures all paths are reachable

---

## 2. Base Weights by Edge Type

### 2.1 Edge Type Classification

| Edge Type | Category | Base Weight | Rationale |
|-----------|----------|-------------|-----------|
| **CALLS** | Neutral | 1.0 | Standard function call |
| **CALLS_EXTERNAL** | Security | 1.5 | External calls are attack vectors |
| **DELEGATECALL** | Security | 2.0 | High risk, storage context |
| **WRITES_STATE** | Security | 1.3 | State modification critical |
| **READS_STATE** | Context | 0.8 | Less direct security impact |
| **HAS_MODIFIER** | Guard | 0.5 | Reduces traversal to guards |
| **INHERITS** | Structure | 0.6 | Structural, not directly risky |
| **USES_VARIABLE** | Context | 0.7 | Variable access context |
| **EMITS_EVENT** | Context | 0.4 | Events are informational |
| **HAS_PARAMETER** | Structure | 0.5 | Parameter linkage |

### 2.2 Justification

**Why 1.5x for CALLS_EXTERNAL?**
- External calls enable reentrancy attacks
- They cross trust boundaries
- They're explicitly tracked in BSKG properties

**Why 2.0x for DELEGATECALL?**
- Executes code in caller's context
- Storage collisions possible
- Highest risk call pattern

**Why 0.5x for HAS_MODIFIER?**
- Modifiers typically enforce guards
- Walking to guards is informative but not attack-path
- Reduces noise in security context

---

## 3. Risk Score Integration

### 3.1 Risk Score Sources

VKG already computes risk scores (0.0-1.0) in `rich_edge.py`:

```python
def get_risk_score(edge):
    """Get existing risk score or compute."""
    if 'risk_score' in edge.properties:
        return edge.properties['risk_score']

    # Default computation
    return compute_default_risk(edge)
```

### 3.2 Weight Adjustment Formula

```python
def compute_edge_weight(edge, edge_type_weights):
    """
    Compute final edge weight.

    final_weight = base_weight * (1 + risk_score) * guard_penalty
    """
    # Get base weight for edge type
    base_weight = edge_type_weights.get(edge.type, 1.0)

    # Get risk score (0.0-1.0)
    risk_score = edge.properties.get('risk_score', 0.0)

    # Apply risk multiplier (1.0 - 2.0x range)
    weight = base_weight * (1.0 + risk_score)

    # Apply guard penalty if applicable
    if has_guard(edge):
        weight *= guard_penalty(edge)

    return weight
```

### 3.3 Risk Score Impact

| Risk Score | Multiplier | Effect |
|------------|------------|--------|
| 0.0 | 1.0x | No risk boost |
| 0.3 | 1.3x | Moderate risk |
| 0.5 | 1.5x | High risk |
| 0.8 | 1.8x | Critical risk |
| 1.0 | 2.0x | Maximum risk |

---

## 4. Guard Penalty Logic

### 4.1 What Counts as a Guard?

Based on BSKG properties:
- `has_reentrancy_guard = true`
- `has_access_gate = true`
- Edge target has `modifiers` containing guard keywords

### 4.2 Penalty Application

```python
def guard_penalty(edge):
    """
    Compute penalty for guarded edges.

    Returns multiplier < 1.0 to reduce weight.
    """
    source_node = graph.nodes[edge.source]
    target_node = graph.nodes[edge.target]

    penalty = 1.0

    # Reentrancy guard reduces path likelihood
    if source_node.properties.get('has_reentrancy_guard'):
        penalty *= 0.6

    # Access gate reduces unauthorized access paths
    if source_node.properties.get('has_access_gate'):
        penalty *= 0.7

    # Target modifier check
    target_modifiers = target_node.properties.get('modifiers', [])
    if any(is_guard_modifier(m) for m in target_modifiers):
        penalty *= 0.8

    return penalty

def is_guard_modifier(modifier_name):
    """Check if modifier is a guard."""
    guard_keywords = [
        'onlyOwner', 'onlyRole', 'nonReentrant',
        'whenNotPaused', 'authorized', 'restricted'
    ]
    return any(kw.lower() in modifier_name.lower() for kw in guard_keywords)
```

### 4.3 Guard Penalty Table

| Guard Type | Penalty | Final Multiplier |
|------------|---------|------------------|
| Reentrancy guard | 0.6 | 60% of base |
| Access gate | 0.7 | 70% of base |
| Guard modifier | 0.8 | 80% of base |
| Multiple guards | 0.6 * 0.7 = 0.42 | 42% of base |

---

## 5. Normalization Strategy

### 5.1 Why Normalize?

PPR requires edge weights to represent transition probabilities:
- Sum of outgoing weights must form valid distribution
- Without normalization, high-weight nodes dominate unfairly

### 5.2 Per-Source Normalization

```python
def normalize_weights(graph, edge_weights):
    """
    Normalize edge weights per source node.

    After normalization, for each source node:
    sum(weights of outgoing edges) = 1.0
    """
    normalized = {}

    # Group by source
    source_totals = {}
    for (source, target), weight in edge_weights.items():
        source_totals[source] = source_totals.get(source, 0) + weight

    # Normalize
    for (source, target), weight in edge_weights.items():
        total = source_totals[source]
        if total > 0:
            normalized[(source, target)] = weight / total
        else:
            normalized[(source, target)] = 0.0

    return normalized
```

### 5.3 Example

Before normalization:
```
A --2.0--> B
A --1.0--> C
A --1.0--> D
```

After normalization (total = 4.0):
```
A --0.50--> B
A --0.25--> C
A --0.25--> D
```

---

## 6. Complete Weight Computation

```python
# Default edge type weights
EDGE_TYPE_WEIGHTS = {
    'CALLS': 1.0,
    'CALLS_EXTERNAL': 1.5,
    'DELEGATECALL': 2.0,
    'WRITES_STATE': 1.3,
    'READS_STATE': 0.8,
    'HAS_MODIFIER': 0.5,
    'INHERITS': 0.6,
    'USES_VARIABLE': 0.7,
    'EMITS_EVENT': 0.4,
    'HAS_PARAMETER': 0.5,
}

def build_weight_matrix(graph):
    """
    Build normalized weight matrix for PPR.

    Returns:
        Dict[(source, target), weight] with normalized weights
    """
    raw_weights = {}

    for edge_id, edge in graph.edges.items():
        source = edge.source
        target = edge.target

        # Base weight
        base = EDGE_TYPE_WEIGHTS.get(edge.type, 1.0)

        # Risk adjustment
        risk = edge.properties.get('risk_score', 0.0)
        weight = base * (1.0 + risk)

        # Guard penalty
        penalty = compute_guard_penalty(graph, edge)
        weight *= penalty

        raw_weights[(source, target)] = weight

    # Normalize
    return normalize_weights(graph, raw_weights)
```

---

## 7. Tuning Recommendations

### 7.1 For Different Analysis Types

| Analysis Type | Adjust | Reason |
|---------------|--------|--------|
| Reentrancy | Boost CALLS_EXTERNAL | Focus on external calls |
| Access Control | Reduce guard penalty | Guards are relevant |
| DoS | Boost loop edges | Loops are attack surface |
| Oracle | Boost READ edges | Data flow matters |

### 7.2 Configuration Override

```python
class PPRConfig:
    def __init__(self, analysis_type='general'):
        self.edge_weights = EDGE_TYPE_WEIGHTS.copy()

        if analysis_type == 'reentrancy':
            self.edge_weights['CALLS_EXTERNAL'] = 2.0
            self.edge_weights['DELEGATECALL'] = 2.5
        elif analysis_type == 'access_control':
            self.guard_penalty_factor = 0.9  # Less penalty
```

---

## 8. Validation

### 8.1 Weight Sanity Checks

```python
def validate_weights(weights):
    """Validate weight matrix."""
    for (source, target), w in weights.items():
        assert w > 0, f"Non-positive weight: {source}->{target}: {w}"
        assert w <= 1.0, f"Weight exceeds 1.0: {source}->{target}: {w}"

    # Check normalization
    sources = set(s for s, t in weights.keys())
    for source in sources:
        total = sum(w for (s, t), w in weights.items() if s == source)
        assert abs(total - 1.0) < 1e-6, f"Unnormalized: {source}: {total}"
```

### 8.2 Test Scenarios

1. **High-risk external call**: Should have highest relative weight
2. **Guarded function**: Should have reduced weight
3. **Internal helper**: Should have neutral weight
4. **Event emission**: Should have lowest weight

---

*Edge Weight Strategy | Task R9.1 | 2026-01-08*
