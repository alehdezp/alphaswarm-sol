# Phase 2: Builder Foundation & Modularization - Research

**Researched:** 2026-01-20
**Domain:** Python refactoring, Solidity proxy patterns, knowledge graph construction
**Confidence:** HIGH

## Summary

The builder.py file (6,120 LOC) is a monolithic class handling all aspects of knowledge graph construction from Slither analysis. The current implementation has several responsibility clusters that map well to independent modules: contract processing, function analysis, state variable analysis, call tracking, proxy detection, invariant extraction, and rich edge generation.

The existing codebase already demonstrates good patterns to follow: dataclasses for schema types (Evidence, Node, Edge), helper modules for specific concerns (heuristics.py, taint.py, classification.py), and the fingerprint module for determinism. The refactoring should extend these patterns.

**Primary recommendation:** Split builder.py into 6-8 focused modules organized by domain responsibility, using dependency injection via a `BuildContext` dataclass to share state across modules without tight coupling.

## Current State Analysis

### Builder.py Structure (6,120 LOC)

**Major Method Categories (identified from grep analysis):**

| Category | Line Range | Method Count | Purpose |
|----------|------------|--------------|---------|
| Contract Processing | 147-400 | 5+ | `_add_contract`, contract-level properties |
| Inheritance | 400-427 | 1 | `_add_inheritance` |
| State Variables | 427-458 | 1 | `_add_state_variables` |
| Modifiers | 458-485 | 1 | `_add_modifiers` |
| Events | 485-511 | 1 | `_add_events` |
| Functions | 511-1892 | 1 (massive) | `_add_functions` - the core monolith |
| Cross-Function Analysis | 1892-1985 | 1 | `_annotate_cross_function_signals` |
| Helper Methods | 1985-3332 | 60+ | Classification, detection, validation |
| Proxy Detection | 3332-3392 | 3 | `_detect_proxy_type`, `_storage_gap_info`, `_is_upgrade_function` |
| Deadline/Temporal | 3402-3470 | 4 | Deadline checks |
| Parameter Extraction | 3470-3520 | 4 | Parameter type helpers |
| Arithmetic Analysis | 5500-5800 | 30+ | Division, multiplication, overflow detection |
| Rich Edge Generation | 5849-6000 | 1 | `_generate_rich_edges` |

**Key Pain Points Identified:**

1. **`_add_functions` is ~1,400 LOC** - handles ALL function property computation in one method
2. **Helper methods mixed with core logic** - 60+ private methods with no clear organization
3. **No dependency injection** - VKGBuilder tightly coupled to Slither API
4. **Repeated patterns** - Similar loops over state vars, parameters appear many times
5. **Proxy detection is name-heuristic based** - Current `_detect_proxy_type` only checks names

### Existing Module Structure

The `kg/` folder already has 30 files with good separation:

| Module | LOC | Purpose | Quality |
|--------|-----|---------|---------|
| `schema.py` | 226 | Core types (Node, Edge, Evidence) | Good - dataclasses |
| `heuristics.py` | 159 | Name-based classification | Good - pure functions |
| `operations.py` | ~200 | Semantic operations | Good - functional |
| `classification.py` | 423 | Node role classification | Good - class-based |
| `fingerprint.py` | 226 | Deterministic hashing | Good - functional |
| `taint.py` | 81 | Dataflow modeling | Good - dataclasses |
| `rich_edge.py` | ~200 | Rich edge types | Good - enums + dataclasses |

### Determinism Status

The existing `fingerprint.py` provides graph-level fingerprinting but **node IDs are partially non-deterministic**:

```python
def _node_id(self, kind: str, name: str, file_path: str | None, line_start: int | None) -> str:
    raw = f"{kind}:{name}:{file_path}:{line_start}"
    return f"{kind}:{hashlib.sha1(raw.encode('utf-8')).hexdigest()[:12]}"
```

This depends on `file_path` and `line_start` which are stable within a build but could vary across environments (absolute vs relative paths). Edge IDs use the same pattern.

## Proxy Resolution Patterns

### EIP-1967 Transparent Proxy

**Standard storage slots (HIGH confidence):**
- Implementation: `bytes32(uint256(keccak256('eip1967.proxy.implementation')) - 1)` = `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc`
- Admin: `bytes32(uint256(keccak256('eip1967.proxy.admin')) - 1)`
- Beacon: `bytes32(uint256(keccak256('eip1967.proxy.beacon')) - 1)`

**Detection approach:**
1. Check for `fallback()` with `delegatecall`
2. Look for EIP-1967 storage slot access patterns
3. Check inheritance from known proxy bases (TransparentUpgradeableProxy, ERC1967Proxy)

Sources: [EIP-1967 Standard](https://eips.ethereum.org/EIPS/eip-1967), [OpenZeppelin Proxy Docs](https://docs.openzeppelin.com/contracts/4.x/api/proxy)

### UUPS (Universal Upgradeable Proxy Standard)

**Key characteristics (HIGH confidence):**
- Upgrade logic in implementation contract, not proxy
- `_authorizeUpgrade(address newImplementation)` hook for access control
- `upgradeTo(address)` and `upgradeToAndCall(address, bytes)` functions
- Uses EIP-1967 storage slots

**Detection approach:**
1. Check for inheritance from UUPSUpgradeable
2. Look for `_authorizeUpgrade` function
3. Check for `upgradeTo`/`upgradeToAndCall` in implementation

Source: [UUPS Explained](https://threesigma.xyz/blog/web3-security/upgradeable-smart-contracts-proxy-patterns-ethereum)

### EIP-2535 Diamond Proxy

**Key characteristics (HIGH confidence):**
- Multiple implementation contracts (facets)
- Function selector to facet address mapping
- `diamondCut` function for adding/removing/replacing facets
- Standard interfaces: IDiamondCut, IDiamondLoupe

**Detection approach:**
1. Check for `DiamondCutFacet` or `diamondCut(FacetCut[] calldata)` function
2. Look for `facetAddresses()`, `facetFunctionSelectors(address)` loupe functions
3. Check for struct `FacetCut { address facetAddress; FacetCutAction action; bytes4[] functionSelectors }`

Source: [Diamond Proxy Pattern Explained](https://rareskills.io/post/diamond-proxy)

### Beacon Proxy

**Key characteristics (HIGH confidence):**
- Shared implementation address across multiple proxy instances
- Beacon contract holds implementation address
- `UpgradeableBeacon.upgradeTo(address)` updates all proxies at once

**Detection approach:**
1. Check for `beacon()` function returning IBeacon
2. Look for inheritance from BeaconProxy
3. Check for EIP-1967 beacon slot access

### Slither API for Proxy Detection

**Available properties (MEDIUM confidence - based on Slither docs):**
```python
contract.is_proxy  # True if contract appears to be a proxy
contract.is_upgradeable_proxy  # True if implementation can be updated
contract._delegates_to  # Variable storing implementation address (if detected)
```

**Limitations:**
- Name-based detection (`"Proxy" in contract.name`) causes false positives
- Cannot distinguish minimal proxies from upgradeable proxies
- `_delegates_to` only returns storage variable, not Contract object

Source: [Slither Python API](https://crytic.github.io/slither/slither.html), [Slither GitHub](https://github.com/crytic/slither)

### Recommended Proxy Resolution Implementation

```python
@dataclass
class ProxyInfo:
    """Proxy detection result."""
    is_proxy: bool
    proxy_type: str  # "transparent", "uups", "diamond", "beacon", "minimal", "unknown", "none"
    implementation_slot: str | None  # Storage slot for implementation address
    admin_slot: str | None
    confidence: str  # "HIGH", "MEDIUM", "LOW"
    unresolved_reason: str | None  # Why resolution failed, if applicable
```

**Resolution strategy:**
1. Check Slither's `is_proxy` and `is_upgradeable_proxy` first
2. Analyze inheritance chain for known proxy base contracts
3. Check for EIP-1967 storage slot patterns in bytecode/source
4. Fall back to name heuristics with LOW confidence
5. For Diamond: enumerate facets via `facetAddresses()` if available
6. Return unified view with all facet functions for simpler queries

## Modularization Strategy

### Recommended Module Structure

```
src/true_vkg/kg/
├── builder/
│   ├── __init__.py          # Public API: VKGBuilder
│   ├── context.py           # BuildContext dataclass (shared state)
│   ├── core.py              # Main build orchestration
│   ├── contracts.py         # Contract-level processing
│   ├── functions.py         # Function analysis (the big one)
│   ├── state_vars.py        # State variable analysis
│   ├── calls.py             # Call tracking with confidence
│   ├── proxy.py             # Proxy resolution
│   ├── invariants.py        # Invariant extraction
│   ├── edges.py             # Rich edge generation
│   └── completeness.py      # Completeness reporting
├── schema.py                # Unchanged
├── operations.py            # Unchanged
├── heuristics.py            # Unchanged (or merge into builder/helpers.py)
├── fingerprint.py           # Enhanced for determinism
├── ...
```

### BuildContext Pattern

Dependency injection via a shared context dataclass:

```python
@dataclass
class BuildContext:
    """Shared context for all builder modules."""
    project_root: Path
    graph: KnowledgeGraph
    slither: Any  # Slither instance

    # Caches for cross-module access
    contract_cache: dict[str, Any] = field(default_factory=dict)
    function_cache: dict[str, Any] = field(default_factory=dict)

    # Configuration
    exclude_dependencies: bool = True
    include_internal_calls: bool = True

    # Completeness tracking
    unresolved_targets: list[UnresolvedTarget] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    # Determinism helpers
    def node_id(self, kind: str, name: str, contract: str, signature: str | None = None) -> str:
        """Generate stable node ID independent of file paths."""
        ...
```

### Module Responsibilities

| Module | Responsibility | Input | Output |
|--------|---------------|-------|--------|
| `core.py` | Orchestration, Slither invocation | Path | KnowledgeGraph |
| `contracts.py` | Contract nodes, inheritance edges | Contract | Contract Node |
| `functions.py` | Function nodes, 50+ properties | Function | Function Node |
| `state_vars.py` | State variable nodes, security tags | StateVar | StateVar Node |
| `calls.py` | Call edges, confidence scoring | Function calls | Edges |
| `proxy.py` | Proxy detection, implementation resolution | Contract | ProxyInfo |
| `invariants.py` | Invariant extraction from comments/config | Contract | Invariant Nodes |
| `edges.py` | Rich edge generation | Graph | Rich Edges |
| `completeness.py` | Build report generation | BuildContext | YAML Report |

Source: [Python Modularization Best Practices](https://best-practice-and-impact.github.io/qa-of-code-guidance/modular_code.html), [Hitchhiker's Guide Project Structure](https://docs.python-guide.org/writing/structure/)

## Python Best Practices

### Type Hints (Required)

All code should use comprehensive type hints:

```python
from typing import Any, Protocol, TypeVar
from collections.abc import Iterator, Sequence

def analyze_function(
    fn: Any,  # Slither Function (use Protocol for type safety)
    context: BuildContext,
) -> FunctionProperties:
    ...
```

### Dataclasses vs Pydantic

**Use dataclasses for:**
- Internal data structures
- Performance-critical paths
- Simple validation needs

**Use Pydantic for:**
- Configuration files
- External API boundaries
- Complex validation with error messages

**Recommendation:** Stick with dataclasses (already used) for schema types, consider Pydantic for completeness report schema.

Source: [Pydantic vs Dataclasses](https://www.speakeasy.com/blog/pydantic-vs-dataclasses)

### Dependency Injection

Use the BuildContext pattern to inject dependencies:

```python
# Instead of:
class FunctionAnalyzer:
    def __init__(self):
        self.slither = ...  # Hardcoded

# Do this:
class FunctionAnalyzer:
    def __init__(self, context: BuildContext):
        self.context = context
```

This enables:
- Easy testing with mock contexts
- Flexible configuration
- Shared caches

Source: [Dependency Injection with Pydantic](https://blog.naveenpn.com/advanced-python-dependency-injection-with-pydantic-and-fastapi)

### Module Size Guidelines

From best practices:
- Aim for 200-500 LOC per module
- Split if a module exceeds 800 LOC
- Each module should have single responsibility

The `functions.py` module may need further internal organization (e.g., property groups) but should remain one module for cohesion.

## Determinism Approach

### Stable Node IDs

**Problem:** Current IDs include file paths which vary across environments.

**Solution:** Use content-based hashing:

```python
def stable_node_id(kind: str, contract: str, name: str, signature: str | None = None) -> str:
    """Generate deterministic node ID from semantic content only."""
    components = [kind, contract, name]
    if signature:
        components.append(signature)
    raw = ":".join(components)
    return f"{kind}:{hashlib.sha256(raw.encode()).hexdigest()[:12]}"
```

### Edge Ordering

**Problem:** Dict iteration order depends on insertion order.

**Solution:**
1. Process contracts in sorted order (by name)
2. Process functions in sorted order (by signature)
3. Use sorted() when serializing to JSON

### Graph Fingerprint

The existing `fingerprint.py` already handles this well. Enhance with:
- Include schema version in fingerprint
- Exclude unstable properties (file paths, timestamps)
- Add build manifest with complete reproducibility info

### Build Manifest

```yaml
# build_manifest.yaml
version: "2.0.0"
fingerprint: "abc123..."
build_date: "2026-01-20T12:00:00Z"
inputs:
  contracts:
    - path: "contracts/Token.sol"
      hash: "sha256:..."
  dependencies:
    slither: "0.11.5"
    solc: "0.8.26"
determinism:
  node_count: 42
  edge_count: 87
  verified: true
```

## Call Tracking Strategy

### Confidence Levels

| Level | When Applied | Example |
|-------|--------------|---------|
| HIGH | Direct call to known target | `token.transfer(to, amount)` |
| MEDIUM | Inferred from context | Interface call with type hint |
| LOW | Cannot resolve | `address(x).call(data)` |

### Edge Structure

```python
@dataclass
class CallEdge(Edge):
    confidence: str  # "HIGH", "MEDIUM", "LOW"
    call_type: str   # "internal", "external", "delegatecall", "callback"
    target_type: str # "direct", "inferred", "unresolved"
    target_name: str | None  # For unresolved: "UNRESOLVED_TARGET"
```

### Callback Detection

For patterns like flash loans, add bidirectional edges:

```python
# When detecting: pool.flashLoan(receiver, token, amount, data)
# Add forward edge: caller -> flashLoan
# Add callback edge: flashLoan -> onFlashLoan (potential callback)
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Proxy slot detection | Custom bytecode parser | OpenZeppelin proxy patterns | Standardized slots |
| Control flow analysis | Custom CFG parser | Slither's CFG API | Already computed |
| Data dependency | Custom taint analysis | `slither.analyses.data_dependency` | Battle-tested |
| Storage layout | Custom parser | Slither's storage layout | Handles inheritance |
| Reentrancy detection | Custom detection | Existing CEI pattern check | Already implemented |

## Common Pitfalls

### Pitfall 1: Breaking Slither API Compatibility
**What goes wrong:** Slither updates change internal API, breaking builder
**Why it happens:** Direct access to internal Slither attributes
**How to avoid:** Wrap Slither access in adapter layer, use getattr with defaults
**Warning signs:** Tests break after Slither upgrade

### Pitfall 2: Over-Modularization
**What goes wrong:** Too many tiny modules with circular imports
**Why it happens:** Splitting every class into its own file
**How to avoid:** Keep cohesive concerns together, max 8-10 modules
**Warning signs:** More than 15 imports in any one file

### Pitfall 3: Losing Test Coverage During Refactor
**What goes wrong:** Refactoring breaks tests, tests get deleted
**Why it happens:** No incremental approach
**How to avoid:** Extract one module at a time, run tests after each extraction
**Warning signs:** Test count decreasing

### Pitfall 4: Non-Deterministic Dict Ordering
**What goes wrong:** Graph fingerprint changes between runs
**Why it happens:** Processing order depends on dict iteration
**How to avoid:** Always sort before iteration in critical paths
**Warning signs:** Flaky fingerprint tests

### Pitfall 5: Incomplete Proxy Resolution
**What goes wrong:** Missing functions in proxy view
**Why it happens:** Not following implementation through multiple layers
**How to avoid:** Recursive resolution with depth limit
**Warning signs:** Diamond proxies missing facet functions

## Code Examples

### Module Extraction Pattern

```python
# builder/functions.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

from .context import BuildContext
from ..schema import Node, Evidence
from ..operations import compute_semantic_ops

@dataclass
class FunctionProperties:
    """All computed properties for a function."""
    visibility: str
    payable: bool
    has_access_gate: bool
    # ... 50+ properties

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

class FunctionAnalyzer:
    """Analyzes functions and computes security properties."""

    def __init__(self, context: BuildContext):
        self.context = context

    def analyze(self, fn: Any, contract: Any) -> tuple[Node, FunctionProperties]:
        """Analyze a function and create its node."""
        props = self._compute_properties(fn, contract)
        node = self._create_node(fn, contract, props)
        return node, props

    def _compute_properties(self, fn: Any, contract: Any) -> FunctionProperties:
        # Extract all function properties
        ...
```

### Proxy Resolution Pattern

```python
# builder/proxy.py
from dataclasses import dataclass
from typing import Any
from enum import Enum

class ProxyType(Enum):
    TRANSPARENT = "transparent"
    UUPS = "uups"
    DIAMOND = "diamond"
    BEACON = "beacon"
    MINIMAL = "minimal"
    UNKNOWN = "unknown"
    NONE = "none"

@dataclass
class ProxyInfo:
    proxy_type: ProxyType
    implementation_slot: str | None = None
    implementation_contract: str | None = None
    facets: list[str] | None = None  # For Diamond
    confidence: str = "LOW"
    resolution_notes: list[str] = field(default_factory=list)

class ProxyResolver:
    """Resolves proxy patterns and implementation addresses."""

    # EIP-1967 slots
    IMPLEMENTATION_SLOT = "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"
    ADMIN_SLOT = "0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103"
    BEACON_SLOT = "0xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50"

    def __init__(self, context: BuildContext):
        self.context = context

    def resolve(self, contract: Any) -> ProxyInfo:
        """Detect proxy type and resolve implementation."""
        # 1. Check Slither's built-in detection
        if getattr(contract, 'is_upgradeable_proxy', False):
            return self._resolve_upgradeable(contract)

        # 2. Check inheritance for known bases
        proxy_type = self._check_inheritance(contract)
        if proxy_type != ProxyType.NONE:
            return self._resolve_by_type(contract, proxy_type)

        # 3. Check for Diamond pattern
        if self._is_diamond(contract):
            return self._resolve_diamond(contract)

        # 4. Fallback to name heuristics (LOW confidence)
        return self._heuristic_detection(contract)
```

### Completeness Report Pattern

```python
# builder/completeness.py
from dataclasses import dataclass, field
from typing import Any
import yaml

@dataclass
class CompletenessReport:
    """Build completeness and quality metrics."""

    # Coverage
    contracts_processed: int = 0
    functions_processed: int = 0

    # Unresolved items
    unresolved_call_targets: list[dict[str, Any]] = field(default_factory=list)
    unresolved_proxy_implementations: list[dict[str, Any]] = field(default_factory=list)

    # Confidence breakdown
    high_confidence_edges: int = 0
    medium_confidence_edges: int = 0
    low_confidence_edges: int = 0

    # Warnings
    warnings: list[str] = field(default_factory=list)

    def to_yaml(self) -> str:
        """Serialize to YAML format."""
        return yaml.dump(asdict(self), default_flow_style=False, sort_keys=True)
```

## Testing Strategy

### Granular Test Approach

Based on context decision to avoid slow test suites:

**Unit tests (fast, targeted):**
- Test each module in isolation
- Mock BuildContext for function/call analyzers
- Use small contract fixtures

**Integration tests (medium speed):**
- Test module interactions
- Use graph_cache for shared builds
- Focus on critical paths

**Snapshot tests (selective):**
- For completeness report format
- For determinism verification
- Update explicitly when format changes

### Test Structure

```
tests/
├── test_builder/
│   ├── test_context.py      # BuildContext unit tests
│   ├── test_functions.py    # Function analysis
│   ├── test_calls.py        # Call tracking
│   ├── test_proxy.py        # Proxy resolution
│   └── test_completeness.py # Report generation
├── test_integration/
│   ├── test_build_flow.py   # End-to-end build
│   └── test_determinism.py  # Fingerprint stability
└── contracts/
    ├── proxies/             # Proxy test contracts
    │   ├── TransparentProxy.sol
    │   ├── UUPSProxy.sol
    │   └── Diamond.sol
    └── ...
```

### Performance Targets

- Unit tests: < 0.1s each
- Module tests: < 1s each
- Full build test: < 30s for typical project
- Total test suite: < 60s

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing tests | HIGH | MEDIUM | Incremental extraction, run tests after each change |
| Slither API changes | MEDIUM | HIGH | Adapter layer with version detection |
| Performance regression | MEDIUM | MEDIUM | Benchmark before/after, lazy loading |
| Incomplete proxy support | MEDIUM | LOW | Best-effort with warnings, don't fail |
| Over-engineering | LOW | MEDIUM | Start simple, add complexity only when needed |

## Recommended Plan Structure

### Wave 1: Foundation (20h)
1. Create builder/ package structure
2. Extract BuildContext with DI pattern
3. Set up comprehensive type hints
4. Migrate tests incrementally

### Wave 2: Core Extraction (40h)
5. Extract contracts.py module
6. Extract state_vars.py module
7. Extract functions.py module (largest effort)
8. Extract calls.py with confidence scoring

### Wave 3: New Features (30h)
9. Implement proxy.py with all patterns
10. Enhanced call tracking with callbacks
11. Deterministic ID generation

### Wave 4: Completeness (20h)
12. Implement completeness.py reporter
13. YAML report format
14. Build manifest generation

### Wave 5: Polish (10h)
15. Performance optimization
16. Documentation
17. Final integration testing

## Open Questions

1. **Diamond facet selector collisions**
   - What we know: Multiple facets can have same selector (invalid)
   - What's unclear: How to handle in graph representation
   - Recommendation: Detect and warn, use first facet

2. **Library call resolution depth**
   - What we know: OpenZeppelin Address.functionCall() wraps call
   - What's unclear: How deep to trace through library layers
   - Recommendation: One level, mark as library-mediated

3. **Lazy loading implementation**
   - What we know: Full build can be slow for large projects
   - What's unclear: What properties to load lazily
   - Recommendation: Defer to Phase 8 optimization, build complete first

## Sources

### Primary (HIGH confidence)
- Slither GitHub: https://github.com/crytic/slither - Official source code
- OpenZeppelin Proxy Docs: https://docs.openzeppelin.com/contracts/4.x/api/proxy - Official documentation
- EIP-1967: https://eips.ethereum.org/EIPS/eip-1967 - Standard specification
- Existing codebase: `src/true_vkg/kg/` - Current implementation patterns

### Secondary (MEDIUM confidence)
- Pydantic vs Dataclasses: https://www.speakeasy.com/blog/pydantic-vs-dataclasses - Type safety comparison
- Diamond Proxy Explained: https://rareskills.io/post/diamond-proxy - Pattern details
- UUPS Explained: https://threesigma.xyz/blog/web3-security/upgradeable-smart-contracts-proxy-patterns-ethereum - Pattern details

### Tertiary (LOW confidence)
- Python Modularization: https://best-practice-and-impact.github.io/qa-of-code-guidance/modular_code.html - General guidance
- Hitchhiker's Guide: https://docs.python-guide.org/writing/structure/ - Project structure
- Slither API Tutorial: https://www.kayssel.com/post/web3-18/ - Community tutorial

## Metadata

**Confidence breakdown:**
- Current state analysis: HIGH - Direct codebase inspection
- Proxy patterns: HIGH - Official specifications and docs
- Modularization strategy: HIGH - Industry best practices + existing codebase patterns
- Testing strategy: MEDIUM - Depends on actual test runtime characteristics
- Python best practices: HIGH - Well-established patterns

**Research date:** 2026-01-20
**Valid until:** 2026-02-20 (30 days - stable domain)
