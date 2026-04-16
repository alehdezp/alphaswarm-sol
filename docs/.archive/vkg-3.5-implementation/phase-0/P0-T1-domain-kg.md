# [P0-T1] Domain Knowledge Graph

**Phase**: 0 - Knowledge Foundation
**Task ID**: P0-T1
**Status**: NOT_STARTED
**Priority**: CRITICAL
**Estimated Effort**: 5-7 days
**Actual Effort**: -

---

## Executive Summary

Build a Domain Knowledge Graph that captures **WHAT CODE SHOULD DO** - ERC standards, DeFi primitives, protocol specifications, and invariants. This is the foundational piece that enables business logic vulnerability detection by comparing actual code behavior against expected specifications.

**Why This Matters**: Without knowing what code SHOULD do, you can only detect syntactic patterns. With domain knowledge, you can detect semantic mismatches - the essence of business logic bugs.

---

## Dependencies

### Required Before Starting
- [ ] None - This is a foundational task

### Blocks These Tasks
- [P0-T3] Cross-Graph Linker - Needs domain specs to link against
- [P1-T2] LLM Intent Annotator - Uses specs for context
- [P2-T3] Defender Agent - Argues from specifications

---

## Objectives

### Primary Objectives
1. Create data structures for specifications, invariants, and DeFi primitives
2. Implement core ERC standard specifications (ERC-20, ERC-721, ERC-4626, ERC-1155)
3. Implement DeFi primitive definitions (AMM, lending, vault, flash loan)
4. Build query interface for finding matching specifications
5. Enable invariant violation detection

### Stretch Goals
1. Add 10+ additional ERC standards
2. Implement natural language invariant parsing
3. Create specification composition (e.g., "ERC-4626 vault using ERC-20 token")

---

## Success Criteria

### Must Have (Definition of Done)
- [ ] `Specification` dataclass with all required fields
- [ ] `DeFiPrimitive` dataclass with security model
- [ ] `DomainKnowledgeGraph` class with query methods
- [ ] ERC-20, ERC-721, ERC-4626 fully specified
- [ ] AMM, lending pool, vault primitives defined
- [ ] `find_matching_specs(fn_node)` returns relevant specs
- [ ] 95%+ test coverage on new code
- [ ] Documentation in docs/reference/domain-kg.md

### Should Have
- [ ] At least 10 ERC standards defined
- [ ] At least 5 DeFi primitives defined
- [ ] Query time < 10ms for 100 functions

### Nice to Have
- [ ] Specification composition support
- [ ] Import from external spec sources (OpenZeppelin docs, etc.)

---

## Technical Design

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    DOMAIN KNOWLEDGE GRAPH                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐     ┌──────────────────┐                  │
│  │  Specifications  │     │  DeFi Primitives │                  │
│  │                  │     │                  │                  │
│  │  ┌────────────┐  │     │  ┌────────────┐  │                  │
│  │  │   ERC-20   │  │     │  │    AMM     │  │                  │
│  │  ├────────────┤  │     │  ├────────────┤  │                  │
│  │  │  ERC-721   │  │     │  │  Lending   │  │                  │
│  │  ├────────────┤  │     │  ├────────────┤  │                  │
│  │  │  ERC-4626  │  │     │  │   Vault    │  │                  │
│  │  ├────────────┤  │     │  ├────────────┤  │                  │
│  │  │  ERC-1155  │  │     │  │ Flash Loan │  │                  │
│  │  └────────────┘  │     │  └────────────┘  │                  │
│  └────────┬─────────┘     └────────┬─────────┘                  │
│           │                        │                            │
│           └────────────┬───────────┘                            │
│                        │                                        │
│              ┌─────────▼─────────┐                              │
│              │  Query Interface  │                              │
│              │                   │                              │
│              │  find_matching()  │                              │
│              │  check_invariant()│                              │
│              │  get_violations() │                              │
│              └───────────────────┘                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### New Files
- `src/true_vkg/knowledge/__init__.py` - Package init
- `src/true_vkg/knowledge/domain_kg.py` - Main implementation
- `src/true_vkg/knowledge/specs/erc_standards.py` - ERC definitions
- `src/true_vkg/knowledge/specs/defi_primitives.py` - DeFi definitions
- `tests/test_3.5/test_domain_kg.py` - Tests

### Modified Files
- `src/true_vkg/__init__.py` - Export new module

### Key Data Structures

```python
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


class SpecType(Enum):
    """Types of specifications."""
    ERC_STANDARD = "erc_standard"
    DEFI_PRIMITIVE = "defi_primitive"
    SECURITY_PATTERN = "security_pattern"
    PROTOCOL_INVARIANT = "protocol_invariant"


@dataclass
class Invariant:
    """A property that should always hold."""
    id: str
    description: str  # Human readable
    formal: Optional[str]  # SMT-LIB or similar (future)
    scope: str  # "function", "contract", "transaction"

    # Semantic operation signature that would violate this
    violation_signature: Optional[str]  # e.g., "W:bal→X:out" violates CEI


@dataclass
class Specification:
    """
    A formal or semi-formal specification of expected behavior.

    This is the KEY data structure that enables business logic detection.
    """
    id: str
    spec_type: SpecType
    name: str
    description: str
    version: str  # e.g., "EIP-20" vs "EIP-20 (2017)"

    # Function signatures this spec applies to
    function_signatures: List[str]  # e.g., ["transfer(address,uint256)"]

    # Semantic operation patterns that indicate this spec
    expected_operations: List[str]  # ["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"]

    # What must be true
    invariants: List[Invariant]
    preconditions: List[str]  # Natural language for now
    postconditions: List[str]

    # Security considerations
    common_violations: List[str]  # Known ways this gets broken
    related_cwes: List[str]

    # For matching code to specs
    semantic_tags: List[str]  # ["value_transfer", "balance_update"]

    # Links to external documentation
    external_refs: Dict[str, str] = field(default_factory=dict)


@dataclass
class DeFiPrimitive:
    """
    A DeFi building block with known security properties.

    Primitives are higher-level than specs - they describe
    common patterns that combine multiple operations.
    """
    id: str
    name: str  # "flash_loan", "amm_swap", "lending_pool"
    description: str

    # Structural pattern
    entry_functions: List[str]  # Common function names
    callback_pattern: Optional[str]  # For flash loans, etc.

    # Related specs this primitive typically implements
    implements_specs: List[str]  # ["erc20", "erc4626"]

    # Security model
    trust_assumptions: List[str]
    attack_surface: List[str]
    known_attack_patterns: List[str]  # Links to adversarial KG

    # Invariants specific to this primitive
    primitive_invariants: List[Invariant]


class DomainKnowledgeGraph:
    """
    Knowledge graph of WHAT SHOULD BE TRUE.

    This enables detecting semantic/business logic bugs by
    comparing actual code behavior against specifications.
    """

    def __init__(self):
        self.specifications: Dict[str, Specification] = {}
        self.primitives: Dict[str, DeFiPrimitive] = {}
        self._semantic_index: Dict[str, List[str]] = {}  # tag -> spec_ids

    def add_specification(self, spec: Specification) -> None:
        """Add a specification and index it."""

    def add_primitive(self, primitive: DeFiPrimitive) -> None:
        """Add a DeFi primitive."""

    def find_matching_specs(
        self,
        fn_node,
        min_confidence: float = 0.5
    ) -> List[tuple[Specification, float]]:
        """
        Find specifications that might apply to a function.

        Matching strategies:
        1. Signature match (exact or fuzzy)
        2. Semantic operation match
        3. Semantic tag overlap

        Returns list of (spec, confidence) tuples.
        """

    def check_invariant(
        self,
        fn_node,
        spec: Specification,
        behavioral_signature: str
    ) -> List["InvariantViolation"]:
        """
        Check if function might violate specification invariants.

        Uses behavioral signature to detect operation ordering issues.
        """

    def get_relevant_primitives(
        self,
        contract_node
    ) -> List[DeFiPrimitive]:
        """Identify which DeFi primitives a contract implements."""
```

### Key Algorithms

1. **Specification Matching**: Multi-strategy matching
   - Strategy 1: Exact signature match (highest confidence)
   - Strategy 2: Semantic operation overlap (jaccard similarity)
   - Strategy 3: Semantic tag overlap
   - Combine scores with weighted average
   - Complexity: O(S * O) where S = specs, O = operations

2. **Invariant Checking**: Pattern-based violation detection
   - Parse spec's violation_signature patterns
   - Match against function's behavioral signature
   - Report matches as potential violations
   - Complexity: O(I * len(signature)) where I = invariants

---

## Implementation Plan

### Phase 1: Data Structures (2 days)
- [ ] Create `src/true_vkg/knowledge/__init__.py`
- [ ] Implement `Invariant` dataclass
- [ ] Implement `Specification` dataclass
- [ ] Implement `DeFiPrimitive` dataclass
- [ ] Create basic `DomainKnowledgeGraph` shell
- [ ] Write unit tests for data structures
- **Checkpoint**: Can create and serialize specs

### Phase 2: ERC Standards (2 days)
- [ ] Create `specs/erc_standards.py`
- [ ] Implement ERC-20 specification (complete)
- [ ] Implement ERC-721 specification
- [ ] Implement ERC-4626 specification
- [ ] Implement ERC-1155 specification
- [ ] Add invariants for each standard
- [ ] Write tests that validate invariants against known vulnerable code
- **Checkpoint**: Can query ERC specs and check invariants

### Phase 3: DeFi Primitives (1.5 days)
- [ ] Create `specs/defi_primitives.py`
- [ ] Implement AMM primitive
- [ ] Implement Lending Pool primitive
- [ ] Implement Vault primitive
- [ ] Implement Flash Loan primitive
- [ ] Link primitives to attack patterns
- **Checkpoint**: Can identify primitive types from contract structure

### Phase 4: Query Interface (1.5 days)
- [ ] Implement `find_matching_specs()` with multi-strategy matching
- [ ] Implement `check_invariant()` with signature pattern matching
- [ ] Implement `get_relevant_primitives()`
- [ ] Build semantic tag index for fast lookup
- [ ] Performance optimize for large spec databases
- [ ] Write integration tests with real BSKG nodes
- **Checkpoint**: Can query specs and check violations on real contracts

---

## Validation Tests

### Unit Tests

```python
# tests/test_3.5/test_domain_kg.py

import pytest
from true_vkg.knowledge.domain_kg import (
    DomainKnowledgeGraph,
    Specification,
    Invariant,
    SpecType,
)


class TestSpecificationDataStructure:
    """Test Specification dataclass."""

    def test_specification_creation(self):
        """Test basic spec creation."""
        spec = Specification(
            id="erc20",
            spec_type=SpecType.ERC_STANDARD,
            name="ERC-20 Token Standard",
            description="Fungible token interface",
            version="EIP-20",
            function_signatures=["transfer(address,uint256)"],
            expected_operations=["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
            invariants=[],
            preconditions=["sender.balance >= amount"],
            postconditions=["balances[to] += amount"],
            common_violations=["Missing zero-address check"],
            related_cwes=["CWE-190"],
            semantic_tags=["value_transfer"],
        )
        assert spec.id == "erc20"
        assert "TRANSFERS_VALUE_OUT" in spec.expected_operations

    def test_invariant_creation(self):
        """Test invariant with violation signature."""
        inv = Invariant(
            id="cei",
            description="Checks-Effects-Interactions pattern",
            formal=None,
            scope="function",
            violation_signature="X:out.*W:bal",  # External before write = violation
        )
        assert inv.violation_signature is not None


class TestDomainKnowledgeGraph:
    """Test DomainKnowledgeGraph class."""

    @pytest.fixture
    def domain_kg(self):
        """Create domain KG with test specs."""
        kg = DomainKnowledgeGraph()
        kg.load_erc_standards()
        kg.load_defi_primitives()
        return kg

    def test_find_matching_specs_by_signature(self, domain_kg):
        """Test finding specs by function signature."""
        # Create mock function node with transfer signature
        mock_fn = MockFunctionNode(
            name="transfer",
            signature="transfer(address,uint256)",
            semantic_ops=["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
        )

        matches = domain_kg.find_matching_specs(mock_fn)
        assert len(matches) > 0
        assert any(spec.id == "erc20" for spec, _ in matches)

    def test_find_matching_specs_by_operations(self, domain_kg):
        """Test finding specs by semantic operations even with different name."""
        # Function named 'send' that has ERC-20-like behavior
        mock_fn = MockFunctionNode(
            name="sendTokens",  # Non-standard name
            signature="sendTokens(address,uint256)",
            semantic_ops=["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
            semantic_tags=["value_transfer"],
        )

        matches = domain_kg.find_matching_specs(mock_fn)
        assert len(matches) > 0
        # Should still match ERC-20 based on operations
        erc20_match = [m for m in matches if m[0].id == "erc20"]
        assert len(erc20_match) > 0
        assert erc20_match[0][1] > 0.5  # Reasonable confidence

    def test_check_invariant_violation(self, domain_kg):
        """Test detection of CEI violation."""
        # Function with external call before state update
        mock_fn = MockFunctionNode(
            name="withdraw",
            behavioral_signature="R:bal→X:out→W:bal",  # Violates CEI
            semantic_ops=["READS_USER_BALANCE", "TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
        )

        erc20_spec = domain_kg.specifications["erc20"]
        violations = domain_kg.check_invariant(mock_fn, erc20_spec, mock_fn.behavioral_signature)

        assert len(violations) > 0
        assert any("CEI" in v.description or "reentrancy" in v.description.lower() for v in violations)

    def test_no_false_positive_on_safe_code(self, domain_kg):
        """Test that safe CEI-compliant code doesn't flag."""
        # Function with proper CEI pattern
        mock_fn = MockFunctionNode(
            name="withdraw",
            behavioral_signature="R:bal→W:bal→X:out",  # Correct CEI order
            semantic_ops=["READS_USER_BALANCE", "WRITES_USER_BALANCE", "TRANSFERS_VALUE_OUT"],
        )

        erc20_spec = domain_kg.specifications["erc20"]
        violations = domain_kg.check_invariant(mock_fn, erc20_spec, mock_fn.behavioral_signature)

        # Should have no CEI violations (might have other findings)
        cei_violations = [v for v in violations if "CEI" in v.description]
        assert len(cei_violations) == 0


class TestDeFiPrimitives:
    """Test DeFi primitive detection."""

    @pytest.fixture
    def domain_kg(self):
        kg = DomainKnowledgeGraph()
        kg.load_defi_primitives()
        return kg

    def test_identify_vault_primitive(self, domain_kg):
        """Test identification of vault contract."""
        # Contract with deposit/withdraw/shares
        mock_contract = MockContractNode(
            name="SimpleVault",
            functions=[
                MockFunctionNode(name="deposit", signature="deposit(uint256,address)"),
                MockFunctionNode(name="withdraw", signature="withdraw(uint256,address,address)"),
                MockFunctionNode(name="totalAssets", signature="totalAssets()"),
            ]
        )

        primitives = domain_kg.get_relevant_primitives(mock_contract)
        assert any(p.id == "vault" for p in primitives)

    def test_identify_flash_loan_primitive(self, domain_kg):
        """Test identification of flash loan pattern."""
        mock_contract = MockContractNode(
            name="FlashLender",
            functions=[
                MockFunctionNode(
                    name="flashLoan",
                    signature="flashLoan(address,address,uint256,bytes)",
                    has_callback=True,
                ),
            ]
        )

        primitives = domain_kg.get_relevant_primitives(mock_contract)
        assert any(p.id == "flash_loan" for p in primitives)
```

### Integration Tests

```python
def test_integration_with_real_vkg():
    """Test domain KG integration with actual VKG."""
    from tests.graph_cache import load_graph

    # Load a real test contract
    graph = load_graph("TokenVault")
    domain_kg = DomainKnowledgeGraph()
    domain_kg.load_erc_standards()
    domain_kg.load_defi_primitives()

    # Get all functions
    functions = [n for n in graph.nodes.values() if n.type == "Function"]

    # Find matching specs for each
    for fn in functions:
        matches = domain_kg.find_matching_specs(fn)
        # Should not crash, should return list
        assert isinstance(matches, list)

    # Check that withdraw-like functions match vault/erc4626 specs
    withdraw_fns = [f for f in functions if "withdraw" in f.label.lower()]
    for fn in withdraw_fns:
        matches = domain_kg.find_matching_specs(fn)
        spec_ids = [m[0].id for m in matches]
        assert "erc4626" in spec_ids or "vault" in spec_ids or len(matches) > 0
```

### Performance Tests

```python
def test_query_performance():
    """Test that spec queries are fast enough."""
    import time

    domain_kg = DomainKnowledgeGraph()
    domain_kg.load_erc_standards()
    domain_kg.load_defi_primitives()

    # Create 100 mock function nodes
    functions = [MockFunctionNode(name=f"fn_{i}") for i in range(100)]

    start = time.time()
    for fn in functions:
        domain_kg.find_matching_specs(fn)
    elapsed = time.time() - start

    # Should complete in < 1 second (10ms per function average)
    assert elapsed < 1.0, f"Query too slow: {elapsed:.2f}s for 100 functions"
```

### The Ultimate Test

**Real-World Validation**: The domain KG should correctly identify that a reentrancy-vulnerable withdrawal function violates ERC-4626 atomicity invariants.

```python
def test_ultimate_reentrancy_detection():
    """
    Ultimate test: Domain KG should flag reentrancy as spec violation.

    This proves the domain KG enables semantic vulnerability detection.
    """
    domain_kg = DomainKnowledgeGraph()
    domain_kg.load_all()

    # Vulnerable withdrawal (external call before state update)
    vulnerable_fn = MockFunctionNode(
        name="withdraw",
        signature="withdraw(uint256,address,address)",
        behavioral_signature="R:bal→X:out→W:bal",
        semantic_ops=["READS_USER_BALANCE", "TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
        properties={
            "visibility": "external",
            "state_write_after_external_call": True,
        }
    )

    # Find matching specs
    matches = domain_kg.find_matching_specs(vulnerable_fn)
    assert len(matches) > 0

    # Check for violations
    all_violations = []
    for spec, confidence in matches:
        violations = domain_kg.check_invariant(
            vulnerable_fn,
            spec,
            vulnerable_fn.behavioral_signature
        )
        all_violations.extend(violations)

    # MUST find at least one violation related to reentrancy/CEI/atomicity
    reentrancy_related = [
        v for v in all_violations
        if any(term in v.description.lower() for term in ["reentrancy", "cei", "atomicity", "ordering"])
    ]
    assert len(reentrancy_related) > 0, f"Failed to detect reentrancy. Violations found: {all_violations}"
```

---

## Metrics & Measurement

### Before Implementation (Baseline)
| Metric | Value | How Measured |
|--------|-------|--------------|
| Business logic detection | 0% | Manual count of BL vulns found |
| Spec matching accuracy | N/A | Not available |
| Invariant violation detection | 0% | Not available |

### After Implementation (Results)
| Metric | Target | Actual | Pass/Fail |
|--------|--------|--------|-----------|
| ERC standards defined | 4+ | - | - |
| DeFi primitives defined | 4+ | - | - |
| Spec matching precision | 80%+ | - | - |
| Invariant detection recall | 70%+ | - | - |
| Query time (100 functions) | <1s | - | - |

### Measurement Commands

```bash
# Run all domain KG tests
uv run pytest tests/test_3.5/test_domain_kg.py -v

# Run with coverage
uv run pytest tests/test_3.5/test_domain_kg.py --cov=src/true_vkg/knowledge --cov-report=html

# Performance benchmark
uv run python -c "
from true_vkg.knowledge.domain_kg import DomainKnowledgeGraph
import time

kg = DomainKnowledgeGraph()
kg.load_all()

# Benchmark
start = time.time()
for _ in range(1000):
    kg.find_matching_specs(mock_fn)
print(f'1000 queries: {time.time() - start:.3f}s')
"
```

---

## Risk Assessment

### Technical Risks
| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Spec matching too imprecise | HIGH | MEDIUM | Use multiple matching strategies, tune thresholds |
| Invariant patterns too rigid | MEDIUM | MEDIUM | Allow regex patterns, support fuzzy matching |
| ERC specs incomplete | MEDIUM | LOW | Start with core specs, expand iteratively |
| Performance degrades with many specs | LOW | LOW | Use indexing, cache results |

### Dependency Risks
| Risk | Impact | Mitigation |
|------|--------|------------|
| BSKG node structure changes | MEDIUM | Use adapter pattern for node access |

---

## Alternative Approaches

### Approach A: Declarative Specs (YAML/JSON) - Current Choice
- **Pros**: Easy to add specs, human-readable, versionable
- **Cons**: Limited expressiveness, can't capture complex invariants
- **Why chosen**: Simplicity for MVP, can enhance later

### Approach B: Formal Specification Language
- **Pros**: Precise, can prove properties, machine-verifiable
- **Cons**: Steep learning curve, harder to write specs
- **Why not chosen**: Too complex for initial implementation

### Approach C: LLM-Generated Specs from Documentation
- **Pros**: Could cover more specs automatically
- **Cons**: Quality concerns, may hallucinate invariants
- **Why not chosen**: Reliability risk, try in future phase

---

## Critical Self-Analysis

### What Could Go Wrong
1. **False positive specs**: Function matches wrong spec → misleading analysis
   - Detection: Track spec match accuracy in tests
   - Mitigation: Require multiple signals for high-confidence match

2. **Invariant patterns miss variants**: Different coding styles may not match patterns
   - Detection: Test with diverse coding styles
   - Mitigation: Support multiple pattern variants per invariant

3. **Specs become stale**: ERC standards evolve
   - Detection: Track spec versions, alert on old specs
   - Mitigation: Include version field, document update process

### Assumptions Being Made
1. **Semantic operations are correctly detected**: If BSKG misses an operation, spec matching fails
   - Validation: Cross-reference with Slither detectors

2. **Behavioral signatures capture ordering accurately**: If CFG traversal is wrong, CEI detection fails
   - Validation: Manual verification on test cases

### Questions to Answer During Implementation
1. How to handle specs that overlap (e.g., ERC-4626 extends ERC-20)?
2. Should spec confidence decay over code distance (inheritance)?
3. How to represent multi-function invariants (e.g., deposit + withdraw conservation)?

---

## Improvement Opportunities

### Discovered During Planning
- [ ] Consider spec inheritance hierarchy (ERC-4626 IS-A ERC-20)
- [ ] Add confidence decay for indirect matches

### To Explore During Implementation
- [ ] Can we auto-generate specs from OpenZeppelin interfaces?
- [ ] Can invariants be extracted from NatSpec comments?

### For Future Phases
- [ ] Formal verification integration (SMT-LIB invariants)
- [ ] Spec coverage metrics for audit reports
- [ ] Community-contributed spec library

---

## Blockers

| Date | Blocker | Resolution | Resolved Date |
|------|---------|------------|---------------|
| - | - | - | - |

---

## Results

### Outcomes
[Fill after completion]

### Metrics Achieved
[Fill after completion]

### Artifacts Produced
- [ ] Code: `src/true_vkg/knowledge/`
- [ ] Tests: `tests/test_3.5/test_domain_kg.py`
- [ ] Docs: `docs/reference/domain-kg.md`

---

## Retrospective

### What Went Well
[Fill after completion]

### What Could Be Improved
[Fill after completion]

### Lessons Learned
[Fill after completion]

### Recommendations for Similar Tasks
[Fill after completion]

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2026-01-02 | Created | Claude |
