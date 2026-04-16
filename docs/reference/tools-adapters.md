# Tool Adapters Reference

**Detector mappings, pattern skip logic, deduplication, and SARIF normalization.**

**For architecture and CLI commands, see [Tool Overview](tools-overview.md).**

---

## Detector-to-Pattern Mapping

**Location:** `src/alphaswarm_sol/tools/mapping.py` (1,850 LOC)

### Mapping Structure

```python
@dataclass
class DetectorMapping:
    vkg_pattern: str           # BSKG pattern ID
    category: str              # Vulnerability category
    confidence_boost: float    # Boost when detected
    tool_precision: float      # Tool's precision
```

### Coverage Statistics

| Tool | Detectors | Examples |
|------|-----------|----------|
| **Slither** | 90+ | reentrancy-eth, unprotected-upgrade |
| **Aderyn** | 30+ | reentrancy, centralization-risk |
| **Mythril** | 36 SWC | SWC-107 (reentrancy), SWC-115 (auth) |

### Slither Mappings (Sample)

| Detector | BSKG Pattern | Precision |
|----------|-------------|-----------|
| `reentrancy-eth` | reentrancy-classic | 0.95 |
| `unprotected-upgrade` | unprotected-upgrade | 0.92 |
| `arbitrary-send-erc20` | arbitrary-token-transfer | 0.88 |
| `tx-origin` | tx-origin-auth | 0.95 |

### Mythril SWC Mappings (Sample)

| SWC ID | BSKG Pattern | Precision |
|--------|-------------|-----------|
| SWC-101 | integer-overflow | 0.85 |
| SWC-107 | reentrancy-classic | 0.92 |
| SWC-115 | weak-access-control | 0.88 |

### Helper Functions

```python
def get_vkg_pattern(tool: str, detector: str) -> Optional[str]
def get_confidence_boost(tool: str, detector: str) -> float
def get_tools_for_pattern(pattern: str) -> List[Tuple[str, str, float]]
```

---

## Pattern Skip Logic

**Location:** `src/alphaswarm_sol/tools/coordinator.py`

### TOOL-07 Implementation

```python
SKIP_THRESHOLD = 0.80  # Skip patterns if tool precision >= 80%

def _calculate_pattern_skips(tools, patterns) -> List[str]:
    patterns_to_skip = []
    for pattern in patterns:
        if pattern in NEVER_SKIP_PATTERNS:
            continue
        tool_coverage = get_tools_for_pattern(pattern)
        max_precision = max(p for _, _, p in tool_coverage) if tool_coverage else 0
        if max_precision >= SKIP_THRESHOLD:
            patterns_to_skip.append(pattern)
    return patterns_to_skip
```

---

## Never-Skip Patterns

13 patterns that tools fundamentally cannot detect:

```python
NEVER_SKIP_PATTERNS = [
    # Business Logic
    "business-logic-violation",
    "economic-manipulation",
    "governance-attack",

    # Cross-Context Reentrancy
    "cross-function-reentrancy",
    "cross-contract-reentrancy",

    # Price/Oracle Manipulation
    "oracle-manipulation",
    "price-manipulation",
    "slippage-manipulation",

    # MEV/Timing
    "sandwich-attack",
    "flash-loan-attack",
    "front-running",

    # Access Control Complexity
    "privilege-escalation",
    "role-confusion",
]
```

---

## Deduplication

**Location:** `src/alphaswarm_sol/orchestration/dedup.py` (865 LOC)

### Two-Stage Process

```
Stage 1: Location Clustering
    +-- Group by file path
    +-- Group by line number (+/-5 lines)
    |
    v
Stage 2: Semantic Similarity (optional)
    +-- Generate embeddings (all-MiniLM-L6-v2)
    +-- Merge findings with similarity > 0.85
    |
    v
Confidence Boosting
    +-- 2 tools agree: +0.1 confidence
    +-- 3+ tools agree: +0.2 confidence
```

### API

```python
class SemanticDeduplicator:
    def deduplicate(findings: List[Finding]) -> Tuple[List[Finding], DeduplicationStats]
```

### CLI

```bash
uv run alphaswarm tools dedupe findings.json
uv run alphaswarm tools dedupe findings.json --no-embeddings
```

---

## SARIF Normalization

**Location:** `src/alphaswarm_sol/tools/sarif.py` (645 LOC)

### Unified Finding Format

```python
@dataclass
class Finding:
    id: str                    # Stable hash-based ID
    tool: str                  # Source tool
    detector: str              # Tool detector name
    vkg_pattern: Optional[str] # Mapped BSKG pattern
    severity: Severity         # Normalized severity
    confidence: float          # 0.0 - 1.0
    file_path: str             # Relative path
    line_start: int
    line_end: int
    code_snippet: Optional[str]
```

### Severity Normalization

| Tool Level | Normalized |
|------------|------------|
| Critical, Severity-4 | CRITICAL |
| High, Severity-3 | HIGH |
| Medium, Severity-2 | MEDIUM |
| Low, Severity-1 | LOW |
| Info, Note | INFO |

---

## Agent Skills for Tools

| Skill | Model | Purpose |
|-------|-------|---------|
| `/vrs-tool-coordinator` | sonnet | Create execution strategy |
| `/vrs-run-slither` | haiku | Run Slither analysis |
| `/vrs-run-mythril` | haiku | Run Mythril symbolic |
| `/vrs-run-aderyn` | haiku | Run Aderyn analysis |

---

## Confidence Mapping

```
Tool Precision >= 0.90 -> HIGH confidence
Tool Precision >= 0.75 -> MEDIUM confidence
Tool Precision >= 0.50 -> LOW confidence
Tool Precision < 0.50  -> Use BSKG pattern instead
```

---

## Related Documentation

- [Tool Overview](tools-overview.md) - Architecture and CLI
- [Pattern Guide](../guides/patterns-basics.md) - Pattern structure

---

*Last Updated: February 2026*
