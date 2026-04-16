# [P0-T2] Adversarial Knowledge Graph

**Phase**: 0 - Knowledge Foundation
**Task ID**: P0-T2
**Status**: NOT_STARTED
**Priority**: CRITICAL
**Estimated Effort**: 5-7 days
**Actual Effort**: -

---

## Executive Summary

Build an Adversarial Knowledge Graph that captures **HOW CODE GETS BROKEN** - historical exploits, attack patterns, and vulnerability taxonomies. This enables "have we seen this before?" queries and transforms pattern matching from syntactic to semantic: instead of looking for `call{value:}` before state writes, we look for patterns similar to The DAO, Cream Finance, etc.

**Why This Matters**: Auditors learn from past exploits. This gives BSKG the same capability - recognizing when code resembles known vulnerable patterns.

---

## Dependencies

### Required Before Starting
- [ ] None - This is a foundational task (can run parallel with P0-T1)

### Blocks These Tasks
- [P0-T3] Cross-Graph Linker - Needs attack patterns to link against
- [P2-T2] Attacker Agent - Uses exploit DB for attack construction
- [P4-T2] Transfer Engine - Uses pattern similarity for cross-project learning

---

## Objectives

### Primary Objectives
1. Create data structures for exploit records and attack patterns
2. Implement 20+ core attack patterns covering major vulnerability classes
3. Build pattern similarity matching against BSKG semantic operations
4. Enable "similar to known exploit" queries
5. Map patterns to CWE taxonomy for standard classification

### Stretch Goals
1. Import 100+ patterns from Solodit/Rekt databases
2. Implement attack pattern composition (flash loan + oracle manipulation)
3. Create pattern extraction from natural language postmortems

---

## Success Criteria

### Must Have (Definition of Done)
- [ ] `AttackPattern` dataclass with semantic operation mapping
- [ ] `ExploitRecord` dataclass linking patterns to real exploits
- [ ] `AdversarialKnowledgeGraph` class with pattern matching
- [ ] 20+ attack patterns covering: reentrancy, access control, oracle, MEV, flash loan, upgrade, economic
- [ ] `find_similar_patterns(fn_node)` returns matching patterns with confidence
- [ ] Pattern-to-CWE mapping for all patterns
- [ ] 95%+ test coverage
- [ ] Documentation in docs/reference/adversarial-kg.md

### Should Have
- [ ] 50+ attack patterns
- [ ] Pattern similarity matching < 20ms per function
- [ ] Solodit data import capability

### Nice to Have
- [ ] Auto-pattern extraction from postmortem text
- [ ] Pattern evolution tracking (variants over time)

---

## Technical Design

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   ADVERSARIAL KNOWLEDGE GRAPH                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    EXPLOIT DATABASE                       │   │
│  │                                                           │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │   │
│  │  │  The DAO    │  │   Cream     │  │   Wormhole  │       │   │
│  │  │  2016-06    │  │   2021-10   │  │   2022-02   │       │   │
│  │  │  $60M       │  │   $130M     │  │   $320M     │       │   │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘       │   │
│  │         │                │                │              │   │
│  │         ▼                ▼                ▼              │   │
│  └─────────┼────────────────┼────────────────┼──────────────┘   │
│            │                │                │                   │
│  ┌─────────▼────────────────▼────────────────▼──────────────┐   │
│  │                    ATTACK PATTERNS                        │   │
│  │                                                           │   │
│  │  ┌───────────────────┐  ┌───────────────────┐            │   │
│  │  │ reentrancy_classic│  │ flash_loan_oracle │            │   │
│  │  │                   │  │                   │            │   │
│  │  │ ops: [X:out,W:bal]│  │ ops: [R:orc,X:out]│            │   │
│  │  │ sig: X:out.*W:bal │  │ preconds: [spot]  │            │   │
│  │  │ CWE: CWE-841      │  │ CWE: CWE-682      │            │   │
│  │  └───────────────────┘  └───────────────────┘            │   │
│  │                                                           │   │
│  │  ┌───────────────────┐  ┌───────────────────┐            │   │
│  │  │ first_depositor   │  │ governance_attack │            │   │
│  │  │                   │  │                   │            │   │
│  │  │ ops: [W:bal,A:div]│  │ ops: [M:own,X:out]│            │   │
│  │  │ preconds: [empty] │  │ preconds: [flash] │            │   │
│  │  │ CWE: CWE-682      │  │ CWE: CWE-863      │            │   │
│  │  └───────────────────┘  └───────────────────┘            │   │
│  │                                                           │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   PATTERN MATCHING                        │   │
│  │                                                           │   │
│  │  fn_node ──► extract_ops() ──► similarity_score() ──►    │   │
│  │             extract_sig()       for each pattern          │   │
│  │             check_preconds()                              │   │
│  │                                                           │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### New Files
- `src/true_vkg/knowledge/adversarial_kg.py` - Main implementation
- `src/true_vkg/knowledge/patterns/reentrancy.py` - Reentrancy patterns
- `src/true_vkg/knowledge/patterns/access_control.py` - Access control patterns
- `src/true_vkg/knowledge/patterns/oracle.py` - Oracle manipulation patterns
- `src/true_vkg/knowledge/patterns/economic.py` - Economic attack patterns
- `src/true_vkg/knowledge/patterns/upgrade.py` - Upgrade vulnerability patterns
- `src/true_vkg/knowledge/importers/solodit.py` - Solodit import
- `tests/test_3.5/test_adversarial_kg.py` - Tests

### Key Data Structures

```python
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from enum import Enum
import re


class AttackCategory(Enum):
    """High-level vulnerability categories."""
    REENTRANCY = "reentrancy"
    ACCESS_CONTROL = "access_control"
    ORACLE_MANIPULATION = "oracle_manipulation"
    FLASH_LOAN = "flash_loan"
    MEV = "mev"
    GOVERNANCE = "governance"
    ECONOMIC = "economic"
    UPGRADE = "upgrade"
    CRYPTOGRAPHIC = "cryptographic"
    DOS = "dos"
    TOKEN = "token"


class Severity(Enum):
    """Vulnerability severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


@dataclass
class AttackPattern:
    """
    Generalized attack pattern extracted from exploits.

    KEY DESIGN: Maps directly to VKG's semantic operations and
    behavioral signatures for precise matching.
    """
    id: str
    name: str
    category: AttackCategory
    severity: Severity
    description: str

    # === MATCHING CRITERIA ===

    # Required semantic operations (from BSKG operations.py)
    # Pattern matches if function has ALL of these
    required_operations: List[str]

    # Behavioral signature pattern (regex)
    # Matches against BSKG behavioral_signature property
    # e.g., ".*X:out.*W:bal.*" matches external call before balance write
    operation_sequence: Optional[str] = None

    # Additional operations that INCREASE confidence
    supporting_operations: List[str] = field(default_factory=list)

    # === PRECONDITIONS ===

    # Property checks that must be true for vulnerability
    # Maps to BSKG node properties
    preconditions: List[str] = field(default_factory=list)

    # Property checks that PREVENT this vulnerability
    # If ANY of these are true, pattern doesn't match
    false_positive_indicators: List[str] = field(default_factory=list)

    # === CONTEXT ===

    # What security properties this violates
    violated_properties: List[str] = field(default_factory=list)

    # Related CWE identifiers
    cwes: List[str] = field(default_factory=list)

    # Detection hints for auditors
    detection_hints: List[str] = field(default_factory=list)

    # Remediation guidance
    remediation: str = ""

    # === METADATA ===

    # Historical exploits that match this pattern
    known_exploits: List[str] = field(default_factory=list)

    # Related patterns (for pattern composition)
    related_patterns: List[str] = field(default_factory=list)

    # Minimum BSKG properties needed to evaluate this pattern
    required_properties: Set[str] = field(default_factory=set)


@dataclass
class ExploitRecord:
    """
    A historical exploit with extracted patterns.

    Links real-world incidents to abstract patterns.
    """
    id: str
    name: str  # "The DAO", "Cream Finance", "Wormhole"
    date: str  # ISO format
    loss_usd: int
    chain: str  # "ethereum", "bsc", "solana"

    # Classification
    category: AttackCategory
    cwes: List[str]

    # The extracted attack pattern
    pattern_ids: List[str]  # Links to AttackPattern.id

    # Attack details
    attack_summary: str
    attack_steps: List[str]

    # Source links
    postmortem_url: Optional[str] = None
    vulnerable_code_url: Optional[str] = None
    fixed_code_url: Optional[str] = None
    tx_hash: Optional[str] = None


@dataclass
class PatternMatch:
    """Result of matching a pattern against a function."""
    pattern: AttackPattern
    confidence: float  # 0.0 to 1.0
    matched_operations: List[str]  # Which ops matched
    matched_signature: bool  # Did sequence match
    matched_preconditions: List[str]  # Which preconditions matched
    blocked_by: List[str]  # Which FP indicators blocked (empty if vulnerable)
    evidence: List[str]  # Human-readable match explanations


class AdversarialKnowledgeGraph:
    """
    Knowledge graph of HOW THINGS GET BROKEN.

    Enables:
    1. "Have we seen similar vulnerable patterns before?"
    2. "What attack techniques apply to this code structure?"
    3. "What would an attacker try here?"
    """

    def __init__(self):
        self.patterns: Dict[str, AttackPattern] = {}
        self.exploits: Dict[str, ExploitRecord] = {}
        self._category_index: Dict[AttackCategory, List[str]] = {}
        self._cwe_index: Dict[str, List[str]] = {}
        self._ops_index: Dict[str, Set[str]] = {}  # op -> pattern_ids

    def add_pattern(self, pattern: AttackPattern) -> None:
        """Add pattern and index it for fast lookup."""
        self.patterns[pattern.id] = pattern

        # Index by category
        if pattern.category not in self._category_index:
            self._category_index[pattern.category] = []
        self._category_index[pattern.category].append(pattern.id)

        # Index by CWE
        for cwe in pattern.cwes:
            if cwe not in self._cwe_index:
                self._cwe_index[cwe] = []
            self._cwe_index[cwe].append(pattern.id)

        # Index by required operations for fast filtering
        for op in pattern.required_operations:
            if op not in self._ops_index:
                self._ops_index[op] = set()
            self._ops_index[op].add(pattern.id)

    def find_similar_patterns(
        self,
        fn_node,
        min_confidence: float = 0.5,
        categories: Optional[List[AttackCategory]] = None,
    ) -> List[PatternMatch]:
        """
        Find attack patterns similar to this function.

        Matching algorithm:
        1. Filter by category if specified
        2. Pre-filter by required operations (fast rejection)
        3. Score each candidate pattern
        4. Return matches above threshold

        Returns: List of PatternMatch sorted by confidence (descending)
        """

    def _score_pattern_match(
        self,
        fn_node,
        pattern: AttackPattern
    ) -> PatternMatch:
        """
        Score how well a function matches an attack pattern.

        Scoring components:
        1. Required operations overlap (40% weight)
        2. Behavioral signature match (30% weight)
        3. Precondition satisfaction (20% weight)
        4. Supporting operations (10% bonus)
        5. False positive indicators (subtract confidence)
        """

    def get_patterns_by_category(self, category: AttackCategory) -> List[AttackPattern]:
        """Get all patterns in a category."""
        return [self.patterns[pid] for pid in self._category_index.get(category, [])]

    def get_patterns_by_cwe(self, cwe: str) -> List[AttackPattern]:
        """Get patterns matching a CWE identifier."""
        return [self.patterns[pid] for pid in self._cwe_index.get(cwe, [])]

    def get_related_exploits(self, pattern_id: str) -> List[ExploitRecord]:
        """Get historical exploits matching a pattern."""
        return [e for e in self.exploits.values() if pattern_id in e.pattern_ids]
```

### Key Algorithms

1. **Pattern Similarity Scoring**:
   ```
   score = 0.0

   # Required operations (40% weight)
   fn_ops = set(fn_node.semantic_ops)
   required_overlap = len(fn_ops & set(pattern.required_ops)) / len(pattern.required_ops)
   score += 0.4 * required_overlap

   # Behavioral signature (30% weight)
   if pattern.operation_sequence:
       if re.match(pattern.operation_sequence, fn_node.behavioral_signature):
           score += 0.3

   # Preconditions (20% weight)
   matched_preconds = sum(1 for p in pattern.preconditions if check_precond(fn_node, p))
   if pattern.preconditions:
       score += 0.2 * (matched_preconds / len(pattern.preconditions))

   # Supporting operations (10% bonus)
   supporting_overlap = len(fn_ops & set(pattern.supporting_ops))
   if pattern.supporting_ops:
       score += 0.1 * (supporting_overlap / len(pattern.supporting_ops))

   # False positive penalties
   for fp in pattern.false_positive_indicators:
       if check_precond(fn_node, fp):
           score -= 0.2  # Each FP indicator reduces confidence significantly

   return max(0.0, min(1.0, score))
   ```

2. **Pre-filtering by Operations**:
   - Use inverted index: for each operation in function, get candidate patterns
   - Intersect candidate sets
   - Only score patterns in intersection
   - Complexity: O(ops * avg_patterns_per_op) vs O(all_patterns)

---

## Implementation Plan

### Phase 1: Core Data Structures (1.5 days)
- [ ] Create `adversarial_kg.py` with dataclasses
- [ ] Implement `AttackPattern` with all fields
- [ ] Implement `ExploitRecord`
- [ ] Implement `PatternMatch`
- [ ] Create `AdversarialKnowledgeGraph` shell
- [ ] Write unit tests for data structures
- **Checkpoint**: Can create and serialize patterns

### Phase 2: Core Attack Patterns (2.5 days)
- [ ] Create `patterns/reentrancy.py`:
  - [ ] `reentrancy_classic` (The DAO style)
  - [ ] `reentrancy_cross_function`
  - [ ] `reentrancy_read_only`
- [ ] Create `patterns/access_control.py`:
  - [ ] `unprotected_function`
  - [ ] `tx_origin_authentication`
  - [ ] `missing_zero_address_check`
- [ ] Create `patterns/oracle.py`:
  - [ ] `spot_price_manipulation`
  - [ ] `stale_oracle_data`
  - [ ] `missing_sequencer_check`
- [ ] Create `patterns/economic.py`:
  - [ ] `first_depositor_attack`
  - [ ] `sandwich_attack`
  - [ ] `flash_loan_governance`
- [ ] Create `patterns/upgrade.py`:
  - [ ] `uninitialized_proxy`
  - [ ] `storage_collision`
  - [ ] `missing_storage_gap`
- [ ] Map all patterns to CWEs
- **Checkpoint**: 20+ patterns defined with full metadata

### Phase 3: Pattern Matching Engine (2 days)
- [ ] Implement `_score_pattern_match()` algorithm
- [ ] Implement operation pre-filtering with indexes
- [ ] Implement `find_similar_patterns()` main method
- [ ] Implement precondition checking system
- [ ] Implement false positive indicator checking
- [ ] Add confidence calibration tests
- **Checkpoint**: Can match functions to patterns accurately

### Phase 4: Exploit Database & Integration (1 day)
- [ ] Add historical exploits (The DAO, Cream, Wormhole, etc.)
- [ ] Link exploits to patterns
- [ ] Implement `get_related_exploits()`
- [ ] Create integration tests with real BSKG nodes
- [ ] Performance benchmarks
- **Checkpoint**: Full adversarial KG operational

---

## Validation Tests

### Unit Tests

```python
# tests/test_3.5/test_adversarial_kg.py

import pytest
from true_vkg.knowledge.adversarial_kg import (
    AdversarialKnowledgeGraph,
    AttackPattern,
    AttackCategory,
    Severity,
    PatternMatch,
)


class TestAttackPattern:
    """Test AttackPattern dataclass."""

    def test_pattern_creation(self):
        """Test creating an attack pattern."""
        pattern = AttackPattern(
            id="reentrancy_classic",
            name="Classic Reentrancy",
            category=AttackCategory.REENTRANCY,
            severity=Severity.CRITICAL,
            description="State update after external call",
            required_operations=["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
            operation_sequence=r".*X:out.*W:bal.*",
            preconditions=["state_write_after_external_call"],
            false_positive_indicators=["has_reentrancy_guard"],
            cwes=["CWE-841"],
        )
        assert pattern.id == "reentrancy_classic"
        assert len(pattern.required_operations) == 2

    def test_pattern_with_false_positive_indicators(self):
        """Test pattern with FP indicators."""
        pattern = AttackPattern(
            id="test",
            name="Test",
            category=AttackCategory.REENTRANCY,
            severity=Severity.HIGH,
            description="Test",
            required_operations=["TRANSFERS_VALUE_OUT"],
            false_positive_indicators=[
                "has_reentrancy_guard",
                "call_to_trusted_only",
            ],
            cwes=[],
        )
        assert len(pattern.false_positive_indicators) == 2


class TestPatternMatching:
    """Test pattern matching against function nodes."""

    @pytest.fixture
    def adv_kg(self):
        """Create adversarial KG with test patterns."""
        kg = AdversarialKnowledgeGraph()
        kg.load_builtin_patterns()
        return kg

    def test_match_reentrancy_vulnerable(self, adv_kg):
        """Test matching classic reentrancy pattern."""
        # Function with external call before state update
        mock_fn = MockFunctionNode(
            name="withdraw",
            semantic_ops=["READS_USER_BALANCE", "TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
            behavioral_signature="R:bal→X:out→W:bal",
            properties={
                "state_write_after_external_call": True,
                "has_reentrancy_guard": False,
            }
        )

        matches = adv_kg.find_similar_patterns(mock_fn, min_confidence=0.5)

        # Should match reentrancy pattern
        reentrancy_matches = [m for m in matches if "reentrancy" in m.pattern.id]
        assert len(reentrancy_matches) > 0
        assert reentrancy_matches[0].confidence >= 0.7

    def test_no_match_with_reentrancy_guard(self, adv_kg):
        """Test that reentrancy guard blocks match."""
        # Same function but WITH reentrancy guard
        mock_fn = MockFunctionNode(
            name="withdraw",
            semantic_ops=["READS_USER_BALANCE", "TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
            behavioral_signature="R:bal→X:out→W:bal",
            properties={
                "state_write_after_external_call": True,
                "has_reentrancy_guard": True,  # Protected!
            }
        )

        matches = adv_kg.find_similar_patterns(mock_fn, min_confidence=0.5)

        # Should NOT match reentrancy pattern (or very low confidence)
        reentrancy_matches = [m for m in matches if "reentrancy" in m.pattern.id]
        for match in reentrancy_matches:
            assert match.confidence < 0.5, "Should be blocked by FP indicator"
            assert "has_reentrancy_guard" in match.blocked_by

    def test_match_oracle_manipulation(self, adv_kg):
        """Test matching oracle manipulation pattern."""
        mock_fn = MockFunctionNode(
            name="swap",
            semantic_ops=["READS_ORACLE", "TRANSFERS_VALUE_OUT", "PERFORMS_DIVISION"],
            behavioral_signature="R:orc→A:div→X:out",
            properties={
                "reads_oracle_price": True,
                "has_staleness_check": False,
                "uses_spot_price": True,
            }
        )

        matches = adv_kg.find_similar_patterns(mock_fn, min_confidence=0.5)

        # Should match oracle manipulation
        oracle_matches = [m for m in matches if m.pattern.category == AttackCategory.ORACLE_MANIPULATION]
        assert len(oracle_matches) > 0

    def test_match_first_depositor(self, adv_kg):
        """Test matching first depositor attack pattern."""
        mock_fn = MockFunctionNode(
            name="deposit",
            semantic_ops=["WRITES_USER_BALANCE", "PERFORMS_DIVISION"],
            behavioral_signature="W:bal→A:div",
            properties={
                "uses_share_calculation": True,
                "division_by_total_supply": True,
            }
        )

        matches = adv_kg.find_similar_patterns(mock_fn, min_confidence=0.5)

        # Should match first depositor pattern
        economic_matches = [m for m in matches if m.pattern.category == AttackCategory.ECONOMIC]
        assert len(economic_matches) > 0


class TestCWEMapping:
    """Test CWE taxonomy integration."""

    @pytest.fixture
    def adv_kg(self):
        kg = AdversarialKnowledgeGraph()
        kg.load_builtin_patterns()
        return kg

    def test_get_patterns_by_cwe(self, adv_kg):
        """Test looking up patterns by CWE."""
        # CWE-841 = Improper Enforcement of Behavioral Workflow (reentrancy)
        patterns = adv_kg.get_patterns_by_cwe("CWE-841")
        assert len(patterns) > 0
        assert any("reentrancy" in p.id for p in patterns)

    def test_all_patterns_have_cwe(self, adv_kg):
        """Test that all patterns have CWE mapping."""
        for pattern in adv_kg.patterns.values():
            assert len(pattern.cwes) > 0, f"Pattern {pattern.id} missing CWE mapping"


class TestExploitDatabase:
    """Test exploit record functionality."""

    @pytest.fixture
    def adv_kg(self):
        kg = AdversarialKnowledgeGraph()
        kg.load_builtin_patterns()
        kg.load_exploit_database()
        return kg

    def test_exploit_has_pattern_link(self, adv_kg):
        """Test that exploits link to patterns."""
        the_dao = adv_kg.exploits.get("the_dao_2016")
        assert the_dao is not None
        assert len(the_dao.pattern_ids) > 0
        assert any("reentrancy" in pid for pid in the_dao.pattern_ids)

    def test_get_related_exploits(self, adv_kg):
        """Test getting exploits for a pattern."""
        exploits = adv_kg.get_related_exploits("reentrancy_classic")
        assert len(exploits) > 0
        assert any("dao" in e.name.lower() for e in exploits)
```

### Integration Tests

```python
def test_integration_with_real_vkg():
    """Test adversarial KG with real BSKG nodes."""
    from tests.graph_cache import load_graph

    graph = load_graph("TokenVault")
    adv_kg = AdversarialKnowledgeGraph()
    adv_kg.load_builtin_patterns()

    vulnerable_found = 0
    total_functions = 0

    for node in graph.nodes.values():
        if node.type != "Function":
            continue
        total_functions += 1

        matches = adv_kg.find_similar_patterns(node, min_confidence=0.6)
        if matches:
            vulnerable_found += 1

    # Should find some matches but not flag everything
    assert vulnerable_found > 0, "Should find some vulnerable patterns"
    assert vulnerable_found < total_functions * 0.5, "Should not flag majority"
```

### Performance Tests

```python
def test_pattern_matching_performance():
    """Test that pattern matching is fast enough."""
    import time

    adv_kg = AdversarialKnowledgeGraph()
    adv_kg.load_builtin_patterns()

    # Create varied mock functions
    functions = []
    for i in range(100):
        ops = random.sample(ALL_OPS, random.randint(1, 5))
        functions.append(MockFunctionNode(
            name=f"fn_{i}",
            semantic_ops=ops,
            behavioral_signature="→".join(ops),
        ))

    start = time.time()
    for fn in functions:
        adv_kg.find_similar_patterns(fn, min_confidence=0.5)
    elapsed = time.time() - start

    # Should complete 100 functions in < 2 seconds (20ms each)
    assert elapsed < 2.0, f"Too slow: {elapsed:.2f}s for 100 functions"
```

### The Ultimate Test

```python
def test_ultimate_the_dao_detection():
    """
    Ultimate test: Should flag code similar to The DAO exploit.

    This proves the adversarial KG enables historical pattern recognition.
    """
    adv_kg = AdversarialKnowledgeGraph()
    adv_kg.load_builtin_patterns()
    adv_kg.load_exploit_database()

    # Recreate The DAO vulnerable pattern
    the_dao_fn = MockFunctionNode(
        name="splitDAO",
        semantic_ops=[
            "READS_USER_BALANCE",
            "VALIDATES_INPUT",
            "TRANSFERS_VALUE_OUT",  # Call before state update!
            "WRITES_USER_BALANCE",
        ],
        behavioral_signature="R:bal→V:in→X:out→W:bal",
        properties={
            "visibility": "public",
            "state_write_after_external_call": True,
            "has_reentrancy_guard": False,
            "transfers_eth": True,
        }
    )

    matches = adv_kg.find_similar_patterns(the_dao_fn, min_confidence=0.6)

    # MUST match reentrancy pattern
    assert len(matches) > 0, "Should find matching patterns"

    reentrancy_match = next(
        (m for m in matches if "reentrancy" in m.pattern.id),
        None
    )
    assert reentrancy_match is not None, "Must match reentrancy pattern"
    assert reentrancy_match.confidence >= 0.7, "Should have high confidence"

    # Should link to The DAO exploit
    related = adv_kg.get_related_exploits(reentrancy_match.pattern.id)
    dao_related = [e for e in related if "dao" in e.name.lower()]
    assert len(dao_related) > 0, "Should link to The DAO exploit"
```

---

## Metrics & Measurement

### Before Implementation (Baseline)
| Metric | Value | How Measured |
|--------|-------|--------------|
| Known vulnerability patterns | 0 | N/A |
| Pattern matching capability | 0% | N/A |
| Historical exploit linking | No | N/A |

### After Implementation (Results)
| Metric | Target | Actual | Pass/Fail |
|--------|--------|--------|-----------|
| Attack patterns defined | 20+ | - | - |
| Exploit records | 10+ | - | - |
| Pattern matching precision | 80%+ | - | - |
| Pattern matching recall | 70%+ | - | - |
| Match time (100 functions) | <2s | - | - |
| CWE coverage | 15+ CWEs | - | - |

---

## Risk Assessment

### Technical Risks
| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Pattern too specific | HIGH | MEDIUM | Use multiple variants per vulnerability class |
| Pattern too generic | MEDIUM | MEDIUM | Add discriminating preconditions |
| FP indicator gaps | HIGH | MEDIUM | Continuously refine from real-world testing |
| Operation mapping incomplete | MEDIUM | LOW | Map all patterns to available BSKG ops |

### Dependency Risks
| Risk | Impact | Mitigation |
|------|--------|------------|
| BSKG operations change | HIGH | Version operations, migration path |
| New vulnerability classes emerge | MEDIUM | Pattern addition workflow |

---

## Critical Self-Analysis

### What Could Go Wrong
1. **Patterns too rigid**: Only catch exact matches of known exploits
   - Detection: Test on variants of known vulnerabilities
   - Mitigation: Use fuzzy matching, regex patterns

2. **FP indicator coverage incomplete**: Real-world code has protections we don't know
   - Detection: High false positive rate on real audits
   - Mitigation: Continuous FP indicator refinement

3. **Operation mapping misalignment**: BSKG ops don't capture what patterns need
   - Detection: Patterns can't be expressed with available ops
   - Mitigation: Work with P0-T1 to ensure alignment

### Assumptions Being Made
1. **Semantic operations are sufficient**: Patterns can be expressed in terms of BSKG ops
   - Validation: Try expressing 10 known vulnerabilities

2. **Behavioral signatures are accurate**: CFG ordering is correct
   - Validation: Manual verification on test cases

### Questions to Answer During Implementation
1. Should patterns support inheritance/composition?
2. How to handle patterns that require cross-function analysis?
3. Should pattern confidence be calibrated empirically?

---

## Improvement Opportunities

### Discovered During Planning
- [ ] Pattern variant generation (auto-generate similar patterns)
- [ ] Confidence calibration from empirical testing

### To Explore During Implementation
- [ ] Can we extract patterns from audit report PDFs?
- [ ] Can patterns reference each other (composition)?

### For Future Phases
- [ ] Machine learning pattern discovery from code diffs
- [ ] Real-time pattern updates from Solodit/Rekt feeds
- [ ] Pattern effectiveness tracking

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
- [ ] Code: `src/true_vkg/knowledge/adversarial_kg.py`
- [ ] Code: `src/true_vkg/knowledge/patterns/*.py`
- [ ] Tests: `tests/test_3.5/test_adversarial_kg.py`
- [ ] Docs: `docs/reference/adversarial-kg.md`

---

## Retrospective

### What Went Well
[Fill after completion]

### What Could Be Improved
[Fill after completion]

### Lessons Learned
[Fill after completion]

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2026-01-02 | Created | Claude |
