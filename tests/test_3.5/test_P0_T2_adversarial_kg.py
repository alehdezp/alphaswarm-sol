"""
Tests for P0-T2: Adversarial Knowledge Graph

Tests attack patterns, exploit database, and pattern matching.
"""

import pytest

from alphaswarm_sol.knowledge import (
    AdversarialKnowledgeGraph,
    AttackPattern,
    ExploitRecord,
    AttackCategory,
    Severity,
    load_builtin_patterns,
    load_exploit_database,
    ALL_PATTERNS,
    ALL_EXPLOITS,
)


# Test Fixtures

@pytest.fixture
def adv_kg():
    """Create adversarial KG with all patterns and exploits loaded."""
    kg = AdversarialKnowledgeGraph()
    load_builtin_patterns(kg)
    load_exploit_database(kg)
    return kg


@pytest.fixture
def mock_vulnerable_fn():
    """Mock vulnerable function node (reentrancy)."""
    return {
        "id": "fn_withdraw",
        "name": "withdraw",
        "properties": {
            "operations": ["READS_USER_BALANCE", "TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
            "behavioral_signature": "R:bal→X:out→W:bal",
            "state_write_after_external_call": True,
            "has_reentrancy_guard": False,
        }
    }


@pytest.fixture
def mock_safe_fn():
    """Mock safe function with reentrancy guard."""
    return {
        "id": "fn_safe_withdraw",
        "name": "withdraw",
        "properties": {
            "operations": ["READS_USER_BALANCE", "TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
            "behavioral_signature": "R:bal→W:bal→X:out",
            "has_reentrancy_guard": True,
        }
    }


# Core Data Structure Tests

class TestDataStructures:
    """Test core data structures."""

    def test_attack_pattern_creation(self):
        """Should create attack pattern with all fields."""
        pattern = AttackPattern(
            id="test-pattern",
            name="Test Pattern",
            category=AttackCategory.REENTRANCY,
            severity=Severity.CRITICAL,
            description="Test description",
            required_operations=["TRANSFERS_VALUE_OUT"],
            operation_sequence=r".*X:out.*W:bal.*",
            cwes=["CWE-841"],
        )

        assert pattern.id == "test-pattern"
        assert pattern.category == AttackCategory.REENTRANCY
        assert pattern.severity == Severity.CRITICAL
        assert len(pattern.required_operations) == 1

    def test_exploit_record_creation(self):
        """Should create exploit record."""
        exploit = ExploitRecord(
            id="test-exploit",
            name="Test Exploit",
            date="2024-01-01",
            loss_usd=1_000_000,
            chain="ethereum",
            category=AttackCategory.REENTRANCY,
            cwes=["CWE-841"],
            pattern_ids=["reentrancy_classic"],
            attack_summary="Test summary",
            attack_steps=["Step 1", "Step 2"],
        )

        assert exploit.id == "test-exploit"
        assert exploit.loss_usd == 1_000_000
        assert len(exploit.pattern_ids) == 1


# Adversarial KG Tests

class TestAdversarialKnowledgeGraph:
    """Test adversarial knowledge graph."""

    def test_initialization(self):
        """Should initialize empty graph."""
        kg = AdversarialKnowledgeGraph()

        assert len(kg.patterns) == 0
        assert len(kg.exploits) == 0

    def test_add_pattern(self):
        """Should add and index pattern."""
        kg = AdversarialKnowledgeGraph()

        pattern = AttackPattern(
            id="test-1",
            name="Test",
            category=AttackCategory.REENTRANCY,
            severity=Severity.HIGH,
            description="Test",
            required_operations=["TRANSFERS_VALUE_OUT"],
            cwes=["CWE-841"],
        )

        kg.add_pattern(pattern)

        assert "test-1" in kg.patterns
        assert len(kg._category_index[AttackCategory.REENTRANCY]) > 0
        assert len(kg._cwe_index["CWE-841"]) > 0

    def test_stats(self, adv_kg):
        """Should return statistics."""
        stats = adv_kg.stats()

        assert stats["total_patterns"] >= 20
        assert stats["total_exploits"] >= 9
        assert stats["unique_cwes"] >= 5


# Pattern Loading Tests

class TestPatternLoading:
    """Test pattern and exploit loading."""

    def test_load_builtin_patterns(self):
        """Should load all builtin patterns."""
        kg = AdversarialKnowledgeGraph()
        load_builtin_patterns(kg)

        assert len(kg.patterns) >= 20
        assert "reentrancy_classic" in kg.patterns
        assert "unprotected_privileged_function" in kg.patterns

    def test_load_exploit_database(self):
        """Should load all exploits."""
        kg = AdversarialKnowledgeGraph()
        load_exploit_database(kg)

        assert len(kg.exploits) >= 9
        assert "the_dao_2016" in kg.exploits
        assert "wormhole_2022" in kg.exploits

    def test_all_patterns_have_cwes(self, adv_kg):
        """All patterns should have CWE mappings."""
        for pattern in adv_kg.patterns.values():
            assert len(pattern.cwes) > 0, f"Pattern {pattern.id} missing CWE"


# Pattern Matching Tests

class TestPatternMatching:
    """Test pattern matching against function nodes."""

    def test_match_reentrancy_vulnerable(self, adv_kg, mock_vulnerable_fn):
        """Should match reentrancy pattern on vulnerable function."""
        matches = adv_kg.find_similar_patterns(mock_vulnerable_fn, min_confidence=0.5)

        # Should find reentrancy patterns
        reentrancy_matches = [m for m in matches if "reentrancy" in m.pattern.id]
        assert len(reentrancy_matches) > 0
        assert reentrancy_matches[0].confidence >= 0.6

    def test_no_match_with_reentrancy_guard(self, adv_kg, mock_safe_fn):
        """Should not match when reentrancy guard present."""
        matches = adv_kg.find_similar_patterns(mock_safe_fn, min_confidence=0.5)

        # Should have much lower confidence or be blocked
        reentrancy_matches = [m for m in matches if "reentrancy" in m.pattern.id]
        for match in reentrancy_matches:
            assert match.confidence < 0.5 or "has_reentrancy_guard" in match.blocked_by

    def test_match_access_control(self, adv_kg):
        """Should match access control pattern."""
        fn_node = {
            "id": "fn_setOwner",
            "properties": {
                "operations": ["MODIFIES_CRITICAL_STATE", "MODIFIES_OWNER"],
                "writes_privileged_state": True,
                "has_access_gate": False,
            }
        }

        matches = adv_kg.find_similar_patterns(fn_node, min_confidence=0.5)

        access_matches = [m for m in matches if m.pattern.category == AttackCategory.ACCESS_CONTROL]
        assert len(access_matches) > 0

    def test_match_oracle_manipulation(self, adv_kg):
        """Should match oracle manipulation pattern."""
        fn_node = {
            "id": "fn_swap",
            "properties": {
                "operations": ["READS_ORACLE", "TRANSFERS_VALUE_OUT", "PERFORMS_DIVISION"],
                "behavioral_signature": "R:orc→A:div→X:out",
                "reads_oracle_price": True,
                "uses_spot_price": True,
                "has_staleness_check": False,
            }
        }

        matches = adv_kg.find_similar_patterns(fn_node, min_confidence=0.5)

        oracle_matches = [m for m in matches if m.pattern.category == AttackCategory.ORACLE_MANIPULATION]
        assert len(oracle_matches) > 0

    def test_confidence_scoring(self, adv_kg, mock_vulnerable_fn):
        """Test confidence scoring components."""
        matches = adv_kg.find_similar_patterns(mock_vulnerable_fn, min_confidence=0.0)

        assert len(matches) > 0
        for match in matches:
            assert 0.0 <= match.confidence <= 1.0
            assert len(match.evidence) > 0


# Category and CWE Indexing Tests

class TestIndexing:
    """Test category and CWE indexing."""

    def test_get_patterns_by_category(self, adv_kg):
        """Should retrieve patterns by category."""
        reentrancy_patterns = adv_kg.get_patterns_by_category(AttackCategory.REENTRANCY)

        assert len(reentrancy_patterns) >= 3
        assert all(p.category == AttackCategory.REENTRANCY for p in reentrancy_patterns)

    def test_get_patterns_by_cwe(self, adv_kg):
        """Should retrieve patterns by CWE."""
        # CWE-841 = Improper Enforcement of Behavioral Workflow (reentrancy)
        patterns = adv_kg.get_patterns_by_cwe("CWE-841")

        assert len(patterns) > 0
        assert all("CWE-841" in p.cwes for p in patterns)

    def test_get_related_exploits(self, adv_kg):
        """Should retrieve exploits for a pattern."""
        exploits = adv_kg.get_related_exploits("reentrancy_classic")

        assert len(exploits) > 0
        assert any("dao" in e.name.lower() for e in exploits)


# Pattern Coverage Tests

class TestPatternCoverage:
    """Test pattern coverage across vulnerability classes."""

    def test_has_reentrancy_patterns(self, adv_kg):
        """Should have reentrancy patterns."""
        patterns = adv_kg.get_patterns_by_category(AttackCategory.REENTRANCY)
        assert len(patterns) >= 3

    def test_has_access_control_patterns(self, adv_kg):
        """Should have access control patterns."""
        patterns = adv_kg.get_patterns_by_category(AttackCategory.ACCESS_CONTROL)
        assert len(patterns) >= 4

    def test_has_oracle_patterns(self, adv_kg):
        """Should have oracle patterns."""
        patterns = adv_kg.get_patterns_by_category(AttackCategory.ORACLE_MANIPULATION)
        assert len(patterns) >= 4

    def test_has_economic_patterns(self, adv_kg):
        """Should have economic patterns."""
        patterns = adv_kg.get_patterns_by_category(AttackCategory.ECONOMIC)
        mev_patterns = adv_kg.get_patterns_by_category(AttackCategory.MEV)
        assert len(patterns) + len(mev_patterns) >= 3

    def test_has_upgrade_patterns(self, adv_kg):
        """Should have upgrade patterns."""
        patterns = adv_kg.get_patterns_by_category(AttackCategory.UPGRADE)
        assert len(patterns) >= 5


# Exploit Database Tests

class TestExploitDatabase:
    """Test historical exploit database."""

    def test_the_dao_exploit(self, adv_kg):
        """Should have The DAO exploit."""
        the_dao = adv_kg.exploits.get("the_dao_2016")

        assert the_dao is not None
        assert the_dao.category == AttackCategory.REENTRANCY
        assert "reentrancy" in the_dao.pattern_ids[0]
        assert the_dao.loss_usd == 60_000_000

    def test_wormhole_exploit(self, adv_kg):
        """Should have Wormhole exploit."""
        wormhole = adv_kg.exploits.get("wormhole_2022")

        assert wormhole is not None
        assert wormhole.category == AttackCategory.UPGRADE
        assert wormhole.loss_usd == 320_000_000

    def test_exploit_pattern_links(self, adv_kg):
        """All exploits should link to valid patterns."""
        for exploit in adv_kg.exploits.values():
            for pattern_id in exploit.pattern_ids:
                assert pattern_id in adv_kg.patterns, f"Invalid pattern {pattern_id} in {exploit.id}"


# Success Criteria Tests

class TestSuccessCriteria:
    """Validate P0-T2 success criteria."""

    def test_has_20_plus_patterns(self, adv_kg):
        """Should have 20+ attack patterns."""
        assert len(adv_kg.patterns) >= 20

    def test_all_patterns_have_metadata(self, adv_kg):
        """All patterns should have complete metadata."""
        for pattern in adv_kg.patterns.values():
            assert pattern.id
            assert pattern.name
            assert pattern.category
            assert pattern.severity
            assert pattern.description
            assert len(pattern.cwes) > 0

    def test_pattern_matching_works(self, adv_kg, mock_vulnerable_fn):
        """find_similar_patterns should work correctly."""
        matches = adv_kg.find_similar_patterns(mock_vulnerable_fn)

        assert len(matches) > 0
        for match in matches:
            assert 0.0 <= match.confidence <= 1.0
            assert len(match.evidence) > 0

    def test_cwe_coverage(self, adv_kg):
        """Should cover multiple CWEs."""
        unique_cwes = set()
        for pattern in adv_kg.patterns.values():
            unique_cwes.update(pattern.cwes)

        assert len(unique_cwes) >= 5

    def test_query_performance(self, adv_kg):
        """Pattern matching should be fast."""
        import time

        # Create test function nodes
        test_fns = []
        for i in range(100):
            test_fns.append({
                "id": f"fn_{i}",
                "properties": {
                    "operations": ["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
                }
            })

        start = time.time()
        for fn in test_fns:
            adv_kg.find_similar_patterns(fn, min_confidence=0.5)
        elapsed = time.time() - start

        # Should complete 100 functions in < 2 seconds (20ms each)
        assert elapsed < 2.0, f"Too slow: {elapsed:.2f}s for 100 functions"
