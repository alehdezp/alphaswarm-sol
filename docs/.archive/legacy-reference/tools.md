# Tool Integration Reference

**Purpose:** Complete documentation of tool adapters, detector mappings, skip logic, and deduplication.
**Last Updated:** 2026-01-22

---

## Table of Contents

1. [Tool Architecture](#tool-architecture)
2. [Supported Tools](#supported-tools)
3. [Tool Tiers](#tool-tiers)
4. [Detector-to-Pattern Mapping](#detector-to-pattern-mapping)
5. [Pattern Skip Logic](#pattern-skip-logic)
6. [Never-Skip Patterns](#never-skip-patterns)
7. [Deduplication](#deduplication)
8. [SARIF Normalization](#sarif-normalization)
9. [VKG-Optimized Defaults](#vkg-optimized-defaults)
10. [CLI Commands](#cli-commands)

---

## Tool Architecture

```
External Tools                    BSKG Integration
     |                                 |
     v                                 v
+---------------------------------------------------------+
|                    ToolRegistry                          |
|  - Tool discovery and health checks                      |
|  - Version detection and compatibility                   |
|  - Configuration management                              |
+------------------------+--------------------------------+
                         |
                         v
+---------------------------------------------------------+
|                   ToolCoordinator                        |
|  - Strategy creation per project                         |
|  - Pattern skip logic (TOOL-07)                          |
|  - Parallel execution orchestration                      |
+------------------------+--------------------------------+
                         |
          +--------------+--------------+
          v              v              v
     +---------+   +---------+   +---------+
     | Adapter |   | Adapter |   | Adapter |   (7 adapters)
     | Slither |   | Aderyn  |   | Mythril |   ...
     +----+----+   +----+----+   +----+----+
          |              |              |
          +--------------+--------------+
                         v
+---------------------------------------------------------+
|                  SARIF Normalizer                        |
|  - Unified finding format                                |
|  - Location normalization                                |
|  - Severity mapping                                      |
+------------------------+--------------------------------+
                         |
                         v
+---------------------------------------------------------+
|               SemanticDeduplicator                       |
|  - Stage 1: Location clustering                          |
|  - Stage 2: Embedding similarity                         |
|  - Confidence boosting on agreement                      |
+------------------------+--------------------------------+
                         |
                         v
                  Unified Findings
```

---

## Supported Tools

**Location:** `src/alphaswarm_sol/tools/adapters/`

### 7 Tool Adapters

| Tool | Type | Language | Adapter File | LOC |
|------|------|----------|--------------|-----|
| **Slither** | Static Analysis | Python | `slither.py` | ~600 |
| **Aderyn** | Static Analysis | Rust | `aderyn.py` | ~450 |
| **Mythril** | Symbolic Execution | Python | `mythril.py` | ~550 |
| **Echidna** | Fuzzing | Haskell | `echidna.py` | ~500 |
| **Foundry** | Testing Framework | Rust | `foundry.py` | ~400 |
| **Semgrep** | Pattern Matching | OCaml | `semgrep.py` | ~450 |
| **Halmos** | Symbolic Testing | Python | `halmos.py` | ~400 |

### Tool Capabilities

| Tool | Reentrancy | Access Control | Integer Issues | Oracle | Flash Loan |
|------|------------|----------------|----------------|--------|------------|
| Slither | High | High | Medium | No | No |
| Aderyn | Medium | Medium | Medium | No | No |
| Mythril | High | Medium | High | No | No |
| Echidna | High | Medium | High | Low | Low |
| Foundry | High | High | High | Medium | Medium |
| Semgrep | Medium | Medium | Low | No | No |
| Halmos | Medium | Low | High | No | No |

---

## Tool Tiers

**Location:** `src/alphaswarm_sol/tools/config.py`

### ToolTier Enum

```python
class ToolTier(str, Enum):
    CORE = "core"           # Always run
    RECOMMENDED = "recommended"  # Run by default
    OPTIONAL = "optional"   # Run on request
```

### Tool Classification

| Tier | Tools | Rationale |
|------|-------|-----------|
| **CORE** | Slither | Fast, comprehensive, Foundry-native |
| **RECOMMENDED** | Aderyn, Mythril | Good coverage, reasonable speed |
| **OPTIONAL** | Echidna, Foundry, Semgrep, Halmos | Specialized, slower, or require setup |

### Default Execution

```python
# Default tools run
DEFAULT_TOOLS = ["slither", "aderyn"]

# Full analysis
FULL_TOOLS = ["slither", "aderyn", "mythril", "semgrep"]

# Comprehensive (slow)
COMPREHENSIVE_TOOLS = ["slither", "aderyn", "mythril", "echidna", "foundry", "halmos"]
```

---

## Detector-to-Pattern Mapping

**Location:** `src/alphaswarm_sol/tools/mapping.py` (1,850 LOC)

### Mapping Structure

```python
@dataclass
class DetectorMapping:
    vkg_pattern: str           # BSKG pattern ID
    category: str              # Vulnerability category
    confidence_boost: float    # Confidence boost when detected
    tool_precision: float      # Tool's precision for this detector
    notes: Optional[str]       # Additional context
```

### Coverage Statistics

| Tool | Detectors Mapped | Example Detectors |
|------|------------------|-------------------|
| **Slither** | 90+ | reentrancy-eth, unprotected-upgrade, arbitrary-send-erc20 |
| **Aderyn** | 30+ | reentrancy, unprotected-initializer, centralization-risk |
| **Mythril** | 36 SWC IDs | SWC-107 (reentrancy), SWC-115 (authorization) |
| **Semgrep** | 20+ | decurity.reentrancy, decurity.delegatecall |
| **Echidna** | Property prefixes | property_*, assertion_*, invariant_* |
| **Foundry** | Test prefixes | test_*, testFail_*, testFuzz_* |
| **Halmos** | Assertion types | assert_*, check_* |

### Slither Mappings (Sample)

| Detector | BSKG Pattern | Precision |
|----------|-------------|-----------|
| `reentrancy-eth` | reentrancy-classic | 0.95 |
| `reentrancy-no-eth` | reentrancy-read-only | 0.90 |
| `reentrancy-benign` | reentrancy-classic | 0.60 |
| `unprotected-upgrade` | unprotected-upgrade | 0.92 |
| `arbitrary-send-erc20` | arbitrary-token-transfer | 0.88 |
| `arbitrary-send-eth` | arbitrary-eth-transfer | 0.90 |
| `suicidal` | unprotected-selfdestruct | 0.95 |
| `locked-ether` | locked-ether | 0.85 |
| `unchecked-transfer` | unchecked-return-value | 0.80 |
| `tx-origin` | tx-origin-auth | 0.95 |

### Mythril SWC Mappings (Sample)

| SWC ID | Name | BSKG Pattern | Precision |
|--------|------|-------------|-----------|
| SWC-101 | Integer Overflow | integer-overflow | 0.85 |
| SWC-104 | Unchecked Call | unchecked-return-value | 0.90 |
| SWC-107 | Reentrancy | reentrancy-classic | 0.92 |
| SWC-110 | Assert Violation | assert-violation | 0.80 |
| SWC-113 | DoS Gas Limit | unbounded-loop | 0.75 |
| SWC-115 | Authorization | weak-access-control | 0.88 |
| SWC-120 | Weak Randomness | weak-randomness | 0.90 |

### Helper Functions

```python
def get_vkg_pattern(tool: str, detector: str) -> Optional[str]:
    """Get BSKG pattern for a tool detector."""

def get_category(tool: str, detector: str) -> Optional[str]:
    """Get vulnerability category for detector."""

def get_confidence_boost(tool: str, detector: str) -> float:
    """Get confidence boost when detector fires."""

def get_tool_precision(tool: str, detector: str) -> float:
    """Get tool's precision for this detector."""

def get_patterns_covered_by_tools(tools: List[str]) -> Dict[str, float]:
    """Get coverage scores for patterns by tool set."""

def get_tools_for_pattern(pattern: str) -> List[Tuple[str, str, float]]:
    """Get (tool, detector, precision) tuples for a pattern."""

def validate_mapping() -> List[str]:
    """Find BSKG patterns not covered by any tool."""
```

---

## Pattern Skip Logic

**Location:** `src/alphaswarm_sol/tools/coordinator.py`

### TOOL-07 Implementation

```python
SKIP_THRESHOLD = 0.80  # Skip patterns if tool precision >= 80%

def _calculate_pattern_skips(
    self,
    tools: List[str],
    patterns: List[str]
) -> List[str]:
    """Determine which patterns can be skipped."""
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

### Skip Decision Flow

```
Pattern "reentrancy-classic"
    |
    +-- Is it in NEVER_SKIP_PATTERNS?
    |   +-- NO -> Continue
    |
    +-- Get tool coverage:
    |   +-- Slither: reentrancy-eth, precision=0.95
    |   +-- Mythril: SWC-107, precision=0.92
    |   +-- Aderyn: reentrancy, precision=0.88
    |
    +-- Max precision = 0.95
    |
    +-- 0.95 >= 0.80 (SKIP_THRESHOLD)?
        +-- YES -> Skip this pattern (tools will catch it)
```

---

## Never-Skip Patterns

**Location:** `src/alphaswarm_sol/tools/coordinator.py`

### 13 Protected Patterns

These patterns represent vulnerabilities that static analysis tools fundamentally cannot detect:

```python
NEVER_SKIP_PATTERNS = [
    # Business Logic (requires protocol understanding)
    "business-logic-violation",
    "economic-manipulation",
    "governance-attack",

    # Cross-Context Reentrancy (requires cross-function/contract analysis)
    "cross-function-reentrancy",
    "cross-contract-reentrancy",

    # Price/Oracle Manipulation (requires economic modeling)
    "oracle-manipulation",
    "price-manipulation",
    "slippage-manipulation",

    # MEV/Timing (requires mempool analysis)
    "sandwich-attack",
    "flash-loan-attack",
    "front-running",

    # Access Control Complexity (requires role graph analysis)
    "privilege-escalation",
    "role-confusion",
]
```

### Why These Can't Be Skipped

| Pattern | Reason Tools Fail |
|---------|-------------------|
| business-logic-violation | Requires understanding intended behavior |
| economic-manipulation | Requires economic modeling |
| governance-attack | Requires governance flow analysis |
| cross-function-reentrancy | Requires inter-function dataflow |
| cross-contract-reentrancy | Requires inter-contract analysis |
| oracle-manipulation | Requires external price feed modeling |
| price-manipulation | Requires liquidity pool modeling |
| slippage-manipulation | Requires trade execution modeling |
| sandwich-attack | Requires mempool simulation |
| flash-loan-attack | Requires multi-step attack modeling |
| front-running | Requires transaction ordering analysis |
| privilege-escalation | Requires role transition graph |
| role-confusion | Requires role capability analysis |

---

## Deduplication

**Location:** `src/alphaswarm_sol/orchestration/dedup.py` (865 LOC)

### Two-Stage Deduplication

```
Stage 1: Location Clustering
    |
    +-- Group by file path
    +-- Group by line number (+/-5 lines tolerance)
    +-- Create initial clusters
    |
    v
Stage 2: Semantic Similarity (optional)
    |
    +-- Load sentence-transformers model (all-MiniLM-L6-v2)
    +-- Generate embeddings for finding descriptions
    +-- Compute cosine similarity within clusters
    +-- Merge findings with similarity > 0.85
    |
    v
Confidence Boosting
    |
    +-- 2 tools agree: +0.1 confidence
    +-- 3+ tools agree: +0.2 confidence
```

### SemanticDeduplicator API

```python
class SemanticDeduplicator:
    def __init__(
        self,
        line_tolerance: int = 5,
        similarity_threshold: float = 0.85,
        enable_embeddings: bool = True
    ):
        # Lazy-load embedding model

    def deduplicate(
        self,
        findings: List[Finding]
    ) -> Tuple[List[Finding], DeduplicationStats]:
        """Deduplicate findings, return unique + stats."""

    def _stage1_location_cluster(
        self,
        findings: List[Finding]
    ) -> List[List[Finding]]:
        """Cluster by file + approximate line number."""

    def _stage2_semantic_similarity(
        self,
        cluster: List[Finding]
    ) -> List[Finding]:
        """Dedupe within cluster by embedding similarity."""

    def _merge_findings(
        self,
        findings: List[Finding]
    ) -> Finding:
        """Merge duplicate findings, boost confidence."""
```

### DeduplicationStats Dataclass

```python
@dataclass
class DeduplicationStats:
    original_count: int
    final_count: int
    reduction_percent: float
    clusters_formed: int
    embeddings_used: bool
    confidence_boosts: int
```

### Confidence Boosting Rules

| Condition | Boost | Rationale |
|-----------|-------|-----------|
| 2 tools agree on same finding | +0.1 | Independent corroboration |
| 3+ tools agree on same finding | +0.2 | Strong multi-tool consensus |
| Same tool, different detectors | +0.05 | Multiple detection paths |

### Graceful Fallback

```python
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    # Falls back to location-only deduplication
```

---

## SARIF Normalization

**Location:** `src/alphaswarm_sol/tools/sarif.py` (645 LOC)

### SARIF (Static Analysis Results Interchange Format)

Standard format for static analysis tool output (OASIS standard).

### Normalization Process

```
Tool Output (varies)
    |
    +-- Slither JSON
    +-- Aderyn JSON
    +-- Mythril JSON
    +-- Semgrep SARIF
    +-- ...
    |
    v
+---------------------------------------------------------+
|                  SARIF Normalizer                        |
|                                                          |
|  1. Parse tool-specific format                           |
|  2. Map severity levels                                  |
|  3. Normalize file paths (relative to project root)     |
|  4. Extract code snippets                                |
|  5. Map detector to BSKG pattern                          |
|  6. Generate stable finding ID                           |
+------------------------+--------------------------------+
                         |
                         v
              Unified Finding Format
```

### Unified Finding Dataclass

```python
@dataclass
class Finding:
    id: str                          # Stable hash-based ID
    tool: str                        # Source tool
    detector: str                    # Tool detector name
    vkg_pattern: Optional[str]       # Mapped BSKG pattern
    severity: Severity               # Normalized severity
    confidence: float                # 0.0 - 1.0
    title: str                       # Finding title
    description: str                 # Detailed description
    file_path: str                   # Relative path
    line_start: int                  # Start line
    line_end: int                    # End line
    code_snippet: Optional[str]      # Source code context
    metadata: Dict[str, Any]         # Tool-specific data
```

### Severity Normalization

| Tool Level | Normalized Severity |
|------------|-------------------|
| Critical, Severity-4 | CRITICAL |
| High, Severity-3, Impact-High | HIGH |
| Medium, Severity-2, Impact-Medium | MEDIUM |
| Low, Severity-1, Impact-Low | LOW |
| Info, Note, Optimization | INFO |

---

## VKG-Optimized Defaults

**Location:** `.vrs/tools.yaml`

### Excluded Detectors (Noisy)

```yaml
slither:
  exclude:
    # Naming conventions (not security)
    - naming-convention
    - constable-states
    - immutable-states

    # Pragma/compiler (not runtime security)
    - pragma
    - solc-version
    - incorrect-solc

    # Gas optimizations (not security)
    - costly-loop
    - dead-code
    - external-function

    # Too many false positives
    - similar-names
    - too-many-digits
    - assembly
```

### Detector Severity Overrides

```yaml
severity_overrides:
  # Upgrade from tool defaults
  reentrancy-eth: critical
  unprotected-upgrade: critical
  arbitrary-send-erc20: high

  # Downgrade from tool defaults
  reentrancy-benign: info
  missing-zero-check: low
```

### Tool Timeouts

```yaml
timeouts:
  slither: 300      # 5 minutes
  aderyn: 120       # 2 minutes
  mythril: 900      # 15 minutes (symbolic execution is slow)
  echidna: 1800     # 30 minutes (fuzzing)
  foundry: 600      # 10 minutes
  semgrep: 180      # 3 minutes
  halmos: 1200      # 20 minutes
```

---

## CLI Commands

### Tool Status

```bash
# Check installed tools
uv run alphaswarm tools status

# Output:
# Tool      Version   Status    Tier
# slither   0.10.0    OK        CORE
# aderyn    0.3.0     OK        RECOMMENDED
# mythril   0.24.0    OK        RECOMMENDED
# echidna   2.2.0     CONFIG    OPTIONAL
# foundry   0.2.0     OK        OPTIONAL
# semgrep   1.50.0    OK        OPTIONAL
# halmos    0.1.0     MISSING   OPTIONAL
```

### Run Tools

```bash
# Run default tools (slither + aderyn)
uv run alphaswarm tools run path/to/contracts/

# Run specific tools
uv run alphaswarm tools run path/to/contracts/ --tools slither,mythril

# Run all available tools
uv run alphaswarm tools run path/to/contracts/ --tools all

# With custom config
uv run alphaswarm tools run path/to/contracts/ --config custom-tools.yaml

# Verbose output
uv run alphaswarm tools run path/to/contracts/ -v
```

### Deduplicate Findings

```bash
# Deduplicate existing findings file
uv run alphaswarm tools dedupe findings.json

# With embeddings disabled
uv run alphaswarm tools dedupe findings.json --no-embeddings

# Custom line tolerance
uv run alphaswarm tools dedupe findings.json --line-tolerance 10

# Output to specific file
uv run alphaswarm tools dedupe findings.json -o deduplicated.json
```

### Explain Strategy

```bash
# Show what tools will run and why
uv run alphaswarm tools explain path/to/contracts/

# Output:
# Strategy for: contracts/
#
# Tools to run: slither, aderyn
# Patterns to skip: 15 (covered by tools with precision >= 80%)
# Protected patterns: 13 (NEVER_SKIP_PATTERNS)
#
# Skip rationale:
# - reentrancy-classic: Slither (0.95), Mythril (0.92)
# - unprotected-upgrade: Slither (0.92)
# ...
#
# Will run BSKG patterns:
# - business-logic-violation (no tool coverage)
# - cross-function-reentrancy (no tool coverage)
# ...
```

---

## Agent Skills for Tools

### /vrs-tool-coordinator

Creates optimal tool execution strategy for a project.

```markdown
Invocation: /vrs-tool-coordinator

Model: sonnet (requires reasoning about tool capabilities)

Inputs:
- Project path
- Available tools (optional)
- Analysis depth (quick/normal/deep)

Outputs:
- ExecutionStrategy with tools, order, timeouts
- Skip rationale for patterns
- Protected patterns list
```

### /vrs-run-slither

Runs Slither with VKG-optimized configuration.

```markdown
Invocation: /vrs-run-slither

Model: haiku (mechanical execution)

Inputs:
- Contract path
- Detector exclusions (optional)

Outputs:
- SARIF-normalized findings
- Detector statistics
```

### /vrs-run-mythril

Runs Mythril symbolic execution.

```markdown
Invocation: /vrs-run-mythril

Model: haiku (mechanical execution)

Inputs:
- Contract path
- Timeout (default: 900s)
- Transaction depth (default: 3)

Outputs:
- SARIF-normalized findings
- SWC mappings
```

### /vrs-run-aderyn

Runs Aderyn static analysis.

```markdown
Invocation: /vrs-run-aderyn

Model: haiku (mechanical execution)

Inputs:
- Contract path
- Foundry project root (optional)

Outputs:
- SARIF-normalized findings
- Detector statistics
```

---

## Quick Reference

### Tool Selection Decision Tree

```
Is project Foundry-based?
+-- YES -> Include Aderyn (Foundry-optimized)
+-- NO -> Slither only for static

Need deep symbolic analysis?
+-- YES -> Include Mythril
+-- NO -> Skip (too slow for quick scans)

Need fuzzing?
+-- YES -> Include Echidna
+-- NO -> Skip (requires property setup)

Have existing test suite?
+-- YES -> Include Foundry tests
+-- NO -> Skip

Need custom patterns?
+-- YES -> Include Semgrep
+-- NO -> Skip
```

### Confidence Mapping

```
Tool Precision >= 0.90 -> HIGH confidence
Tool Precision >= 0.75 -> MEDIUM confidence
Tool Precision >= 0.50 -> LOW confidence
Tool Precision < 0.50  -> Use BSKG pattern instead
```

---

*Reference: tools.md*
*Last Updated: 2026-01-22*
