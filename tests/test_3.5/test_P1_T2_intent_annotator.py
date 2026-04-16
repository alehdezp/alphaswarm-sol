"""
Tests for P1-T2: LLM Intent Annotator

Tests the LLM-powered annotator that infers business purpose,
trust assumptions, and invariants from Solidity functions.
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime

from alphaswarm_sol.intent import (
    IntentAnnotator,
    IntentCache,
    BusinessPurpose,
    TrustLevel,
    FunctionIntent,
)


# Mock Classes for Testing

class MockNode:
    """Mock VKG function node for testing."""

    def __init__(
        self,
        label: str,
        visibility: str = "external",
        modifiers: list = None,
        semantic_ops: list = None,
        behavioral_signature: str = "",
    ):
        self.label = label
        self.properties = {
            "visibility": visibility,
            "modifiers": modifiers or [],
            "semantic_ops": semantic_ops or [],
            "behavioral_signature": behavioral_signature,
        }


class MockLLMClient:
    """Mock LLM client for testing."""

    def __init__(self, response: str = None):
        self.response = response
        self.call_count = 0
        self.last_prompt = None

    def analyze(self, prompt: str, response_format: str = "text", temperature: float = 0.7) -> str:
        """Mock analyze method."""
        self.call_count += 1
        self.last_prompt = prompt

        if self.response:
            return self.response

        # Default response for withdrawal function
        return json.dumps({
            "business_purpose": "withdrawal",
            "purpose_confidence": 0.9,
            "purpose_reasoning": "Function transfers ETH based on balance mapping",
            "expected_trust_level": "depositor_only",
            "authorized_callers": ["depositor"],
            "trust_assumptions": [
                {
                    "id": "balance_accurate",
                    "description": "Balance mapping is accurate",
                    "category": "state",
                    "critical": True,
                }
            ],
            "inferred_invariants": [
                {
                    "id": "balance_decrease",
                    "description": "Caller balance decreases by amount",
                    "scope": "function",
                }
            ],
            "likely_specs": ["erc4626_withdraw"],
            "spec_confidence": {"erc4626_withdraw": 0.8},
            "risk_notes": ["External call before state update"],
            "complexity_score": 0.7,
        })


class MockDomainKG:
    """Mock Domain KG for testing."""

    def __init__(self):
        self.specifications = []
        self.primitives = []


# Test Fixtures

@pytest.fixture
def mock_llm():
    """Create mock LLM client."""
    return MockLLMClient()


@pytest.fixture
def mock_domain_kg():
    """Create mock domain KG."""
    return MockDomainKG()


@pytest.fixture
def annotator(mock_llm, mock_domain_kg):
    """Create annotator with mocks."""
    return IntentAnnotator(mock_llm, mock_domain_kg)


@pytest.fixture
def cached_annotator(mock_llm, mock_domain_kg, tmp_path):
    """Create annotator with cache."""
    return IntentAnnotator(mock_llm, mock_domain_kg, cache_dir=tmp_path)


@pytest.fixture
def withdrawal_node():
    """Create mock withdrawal function node."""
    return MockNode(
        label="withdraw",
        visibility="external",
        semantic_ops=["READS_USER_BALANCE", "TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
        behavioral_signature="R:bal→X:out→W:bal",
    )


@pytest.fixture
def withdrawal_code():
    """Sample withdrawal function code."""
    return """
    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient");
        balances[msg.sender] -= amount;
        payable(msg.sender).transfer(amount);
    }
    """


# IntentCache Tests

class TestIntentCache:
    """Test IntentCache functionality."""

    def test_cache_creation_memory_only(self):
        """Test creating memory-only cache."""
        cache = IntentCache()
        assert cache.cache_dir is None
        assert cache.memory_cache == {}

    def test_cache_creation_with_dir(self, tmp_path):
        """Test creating cache with directory."""
        cache = IntentCache(tmp_path)
        assert cache.cache_dir == tmp_path
        assert cache.cache_dir.exists()

    def test_cache_get_miss(self):
        """Test cache miss returns None."""
        cache = IntentCache()
        result = cache.get("nonexistent")
        assert result is None

    def test_cache_set_get_memory(self):
        """Test memory cache set/get."""
        cache = IntentCache()

        intent = FunctionIntent(
            business_purpose=BusinessPurpose.WITHDRAWAL,
            purpose_confidence=0.9,
            purpose_reasoning="Test",
            expected_trust_level=TrustLevel.DEPOSITOR_ONLY,
        )

        cache.set("test_key", intent)
        retrieved = cache.get("test_key")

        assert retrieved is not None
        assert retrieved.business_purpose == BusinessPurpose.WITHDRAWAL
        assert retrieved.purpose_confidence == 0.9

    def test_cache_set_get_disk(self, tmp_path):
        """Test disk cache set/get."""
        cache = IntentCache(tmp_path)

        intent = FunctionIntent(
            business_purpose=BusinessPurpose.DEPOSIT,
            purpose_confidence=0.85,
            purpose_reasoning="Test",
            expected_trust_level=TrustLevel.PERMISSIONLESS,
        )

        cache.set("test_key", intent)

        # Clear memory cache to force disk read
        cache.memory_cache.clear()

        retrieved = cache.get("test_key")

        assert retrieved is not None
        assert retrieved.business_purpose == BusinessPurpose.DEPOSIT
        assert retrieved.purpose_confidence == 0.85

    def test_cache_clear(self, tmp_path):
        """Test cache clear."""
        cache = IntentCache(tmp_path)

        intent = FunctionIntent(
            business_purpose=BusinessPurpose.SWAP,
            purpose_confidence=0.9,
            purpose_reasoning="Test",
            expected_trust_level=TrustLevel.PERMISSIONLESS,
        )

        cache.set("test_key", intent)
        assert cache.get("test_key") is not None

        cache.clear()
        assert cache.get("test_key") is None


# IntentAnnotator Tests

class TestIntentAnnotator:
    """Test IntentAnnotator functionality."""

    def test_annotator_creation(self, mock_llm, mock_domain_kg):
        """Test creating annotator."""
        annotator = IntentAnnotator(mock_llm, mock_domain_kg)
        assert annotator.llm == mock_llm
        assert annotator.domain_kg == mock_domain_kg
        assert annotator.cache is None

    def test_annotator_with_cache(self, mock_llm, mock_domain_kg, tmp_path):
        """Test creating annotator with cache."""
        annotator = IntentAnnotator(mock_llm, mock_domain_kg, cache_dir=tmp_path)
        assert annotator.cache is not None
        assert annotator.cache.cache_dir == tmp_path

    def test_annotate_withdrawal_function(self, annotator, withdrawal_node, withdrawal_code):
        """Test annotating withdrawal function."""
        intent = annotator.annotate_function(withdrawal_node, withdrawal_code)

        # Verify intent structure
        assert isinstance(intent, FunctionIntent)
        assert intent.business_purpose == BusinessPurpose.WITHDRAWAL
        assert intent.purpose_confidence == 0.9
        assert intent.expected_trust_level == TrustLevel.DEPOSITOR_ONLY
        assert len(intent.trust_assumptions) == 1
        assert len(intent.inferred_invariants) == 1
        assert len(intent.risk_notes) == 1

    def test_llm_called(self, annotator, mock_llm, withdrawal_node, withdrawal_code):
        """Test that LLM is called."""
        assert mock_llm.call_count == 0

        annotator.annotate_function(withdrawal_node, withdrawal_code)

        assert mock_llm.call_count == 1
        assert mock_llm.last_prompt is not None
        assert "withdraw" in mock_llm.last_prompt
        assert "READS_USER_BALANCE" in mock_llm.last_prompt

    def test_cache_key_computation(self, annotator, withdrawal_node, withdrawal_code):
        """Test cache key is stable."""
        key1 = annotator._compute_cache_key(withdrawal_node, withdrawal_code)
        key2 = annotator._compute_cache_key(withdrawal_node, withdrawal_code)

        assert key1 == key2
        assert len(key1) == 16  # First 16 chars of SHA256

    def test_caching_works(self, cached_annotator, mock_llm, withdrawal_node, withdrawal_code):
        """Test that caching avoids redundant LLM calls."""
        # First call
        intent1 = cached_annotator.annotate_function(withdrawal_node, withdrawal_code)
        call_count1 = mock_llm.call_count

        # Second call (should use cache)
        intent2 = cached_annotator.annotate_function(withdrawal_node, withdrawal_code)
        call_count2 = mock_llm.call_count

        assert call_count2 == call_count1  # No new LLM call
        assert intent1.business_purpose == intent2.business_purpose
        assert intent1.purpose_confidence == intent2.purpose_confidence

    def test_context_building(self, annotator, withdrawal_node, withdrawal_code):
        """Test context building from VKG properties."""
        context = annotator._build_context(withdrawal_node, withdrawal_code, None)

        assert context["function_name"] == "withdraw"
        assert context["visibility"] == "external"
        assert "READS_USER_BALANCE" in context["semantic_ops"]
        assert context["behavioral_signature"] == "R:bal→X:out→W:bal"

    def test_spec_hints_generation(self, annotator, withdrawal_node):
        """Test specification hint generation."""
        hints = annotator._get_spec_hints(withdrawal_node)

        assert "ERC-4626" in hints or "vault" in hints
        assert "reentrancy" in hints.lower()  # Should detect pattern

    def test_prompt_building(self, annotator, withdrawal_node, withdrawal_code):
        """Test prompt construction."""
        context = annotator._build_context(withdrawal_node, withdrawal_code, None)
        prompt = annotator._build_prompt(withdrawal_node, context)

        # Verify prompt structure
        assert "Business Purpose" in prompt
        assert "Trust Level" in prompt
        assert "Trust Assumptions" in prompt
        assert "Inferred Invariants" in prompt
        assert "withdraw" in prompt
        assert "READS_USER_BALANCE" in prompt

    def test_parse_valid_response(self, annotator, withdrawal_node):
        """Test parsing valid LLM response."""
        response = json.dumps({
            "business_purpose": "deposit",
            "purpose_confidence": 0.95,
            "purpose_reasoning": "Transfers tokens to contract",
            "expected_trust_level": "permissionless",
            "authorized_callers": ["anyone"],
            "trust_assumptions": [],
            "inferred_invariants": [],
            "likely_specs": ["erc20"],
            "spec_confidence": {"erc20": 0.9},
            "risk_notes": [],
            "complexity_score": 0.4,
        })

        intent = annotator._parse_response(response, withdrawal_node)

        assert intent.business_purpose == BusinessPurpose.DEPOSIT
        assert intent.purpose_confidence == 0.95
        assert intent.expected_trust_level == TrustLevel.PERMISSIONLESS

    def test_parse_invalid_response_fallback(self, annotator, withdrawal_node):
        """Test fallback for invalid LLM response."""
        response = "This is not valid JSON"

        intent = annotator._parse_response(response, withdrawal_node)

        # Should fallback to UNKNOWN
        assert intent.business_purpose == BusinessPurpose.UNKNOWN
        assert intent.purpose_confidence == 0.0
        assert "Failed to parse" in intent.purpose_reasoning

    def test_annotate_batch(self, annotator, withdrawal_node, withdrawal_code):
        """Test batch annotation."""
        functions = [
            (withdrawal_node, withdrawal_code, None),
            (withdrawal_node, withdrawal_code, None),
        ]

        intents = annotator.annotate_batch(functions)

        assert len(intents) == 2
        assert all(isinstance(i, FunctionIntent) for i in intents)


# Integration Tests

class TestIntentAnnotatorIntegration:
    """Test intent annotator integration scenarios."""

    def test_admin_function_annotation(self, mock_domain_kg):
        """Test annotating admin function."""
        llm = MockLLMClient(response=json.dumps({
            "business_purpose": "set_parameter",
            "purpose_confidence": 0.88,
            "purpose_reasoning": "Sets protocol parameter",
            "expected_trust_level": "owner_only",
            "authorized_callers": ["owner"],
            "trust_assumptions": [
                {
                    "id": "caller_is_owner",
                    "description": "Only owner can call",
                    "category": "caller",
                    "critical": True,
                    "validation_check": "msg.sender == owner",
                }
            ],
            "inferred_invariants": [
                {
                    "id": "param_in_range",
                    "description": "Parameter within safe range",
                    "scope": "function",
                }
            ],
            "likely_specs": ["ownable"],
            "spec_confidence": {"ownable": 0.9},
            "risk_notes": ["Critical parameter needs access control"],
            "complexity_score": 0.5,
        }))

        annotator = IntentAnnotator(llm, mock_domain_kg)

        node = MockNode(
            label="setFee",
            visibility="external",
            modifiers=["onlyOwner"],
            semantic_ops=["CHECKS_PERMISSION", "MODIFIES_CRITICAL_STATE"],
        )

        code = """
        function setFee(uint256 newFee) external onlyOwner {
            require(newFee <= MAX_FEE, "Fee too high");
            protocolFee = newFee;
        }
        """

        intent = annotator.annotate_function(node, code)

        assert intent.business_purpose == BusinessPurpose.SET_PARAMETER
        assert intent.expected_trust_level == TrustLevel.OWNER_ONLY
        assert intent.has_authorization_requirements()
        assert len(intent.get_critical_assumptions()) == 1

    def test_view_function_annotation(self, mock_domain_kg):
        """Test annotating view function."""
        llm = MockLLMClient(response=json.dumps({
            "business_purpose": "view_only",
            "purpose_confidence": 1.0,
            "purpose_reasoning": "View function, no state changes",
            "expected_trust_level": "permissionless",
            "authorized_callers": ["anyone"],
            "trust_assumptions": [],
            "inferred_invariants": [],
            "likely_specs": [],
            "spec_confidence": {},
            "risk_notes": [],
            "complexity_score": 0.1,
        }))

        annotator = IntentAnnotator(llm, mock_domain_kg)

        node = MockNode(
            label="getBalance",
            visibility="external",
            modifiers=["view"],
            semantic_ops=[],
        )

        code = """
        function getBalance(address user) external view returns (uint256) {
            return balances[user];
        }
        """

        intent = annotator.annotate_function(node, code)

        assert intent.business_purpose == BusinessPurpose.VIEW_ONLY
        assert intent.expected_trust_level == TrustLevel.PERMISSIONLESS
        assert not intent.has_authorization_requirements()
        assert not intent.is_high_risk()


# Success Criteria Tests

class TestSuccessCriteria:
    """Validate P1-T2 success criteria."""

    def test_llm_integration_works(self, annotator, withdrawal_node, withdrawal_code):
        """LLM integration should work."""
        intent = annotator.annotate_function(withdrawal_node, withdrawal_code)
        assert intent is not None
        assert isinstance(intent, FunctionIntent)

    def test_caching_reduces_calls(self, cached_annotator, mock_llm, withdrawal_node, withdrawal_code):
        """Caching should reduce redundant LLM calls."""
        # 10 identical calls
        for _ in range(10):
            cached_annotator.annotate_function(withdrawal_node, withdrawal_code)

        # Should only call LLM once
        assert mock_llm.call_count == 1  # 90% reduction (9/10 cached)

    def test_batch_annotation(self, annotator, withdrawal_node, withdrawal_code):
        """Batch annotation should work."""
        functions = [(withdrawal_node, withdrawal_code, None)] * 5
        intents = annotator.annotate_batch(functions)

        assert len(intents) == 5
        assert all(isinstance(i, FunctionIntent) for i in intents)

    def test_graceful_fallback(self, mock_domain_kg):
        """Should fallback gracefully when LLM fails."""
        llm = MockLLMClient(response="Invalid JSON!")
        annotator = IntentAnnotator(llm, mock_domain_kg)

        node = MockNode(label="test")
        code = "function test() {}"

        intent = annotator.annotate_function(node, code)

        # Should return UNKNOWN intent instead of crashing
        assert intent.business_purpose == BusinessPurpose.UNKNOWN
        assert intent.purpose_confidence == 0.0

    def test_timestamp_added(self, annotator, withdrawal_node, withdrawal_code):
        """Should add inference timestamp."""
        intent = annotator.annotate_function(withdrawal_node, withdrawal_code)

        assert intent.inferred_at is not None
        # Should be valid ISO format
        datetime.fromisoformat(intent.inferred_at)
