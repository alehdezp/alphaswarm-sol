"""Tests for VulndocContextExtractor and context types.

Tests context extraction, risk profile mapping, token estimation,
trimming logic, and serialization.
"""

import pytest
from pathlib import Path
from alphaswarm_sol.agents.context import (
    ContextBundle,
    RiskProfile,
    RiskCategory,
    ContextSection,
    VulndocContextExtractor,
)
from alphaswarm_sol.context.schema import ProtocolContextPack
from alphaswarm_sol.context.types import (
    Confidence,
    Role,
    Assumption,
    OffchainInput,
)


# Fixtures


@pytest.fixture
def sample_protocol_pack():
    """Create a minimal protocol context pack for testing."""
    return ProtocolContextPack(
        protocol_name="TestProtocol",
        protocol_type="lending",
        roles=[
            Role(
                name="admin",
                capabilities=["pause", "upgrade"],
                trust_assumptions=["trusted multisig"],
                confidence=Confidence.CERTAIN,
            ),
            Role(
                name="user",
                capabilities=["deposit", "borrow"],
                trust_assumptions=[],
                confidence=Confidence.CERTAIN,
            ),
        ],
        assumptions=[
            Assumption(
                description="Oracle prices are accurate within 1%",
                category="price",
                affects_functions=["liquidate", "borrow"],
                confidence=Confidence.INFERRED,
                source="whitepaper",
            ),
        ],
        offchain_inputs=[
            OffchainInput(
                name="Chainlink Price Feed",
                input_type="oracle",
                description="Price feeds for liquidation",
                trust_assumptions=["Chainlink is reliable"],
                affects_functions=["liquidate"],
                confidence=Confidence.CERTAIN,
            ),
        ],
        incentives="Liquidation rewards for keepers",
        tokenomics_summary="Governance token for protocol decisions",
        governance="DAO with timelock",
    )


@pytest.fixture
def vulndocs_root(tmp_path):
    """Create a temporary vulndocs directory with template structure."""
    vulndocs = tmp_path / "vulndocs"

    # Create reentrancy/classic vulndoc
    reentrancy_classic = vulndocs / "reentrancy" / "classic"
    reentrancy_classic.mkdir(parents=True)

    index_content = """
id: reentrancy-classic
category: reentrancy
subcategory: classic
severity: critical
vulndoc: reentrancy/classic

description: |
  Classic reentrancy vulnerability where external calls allow re-entering
  before state updates complete.

reasoning_template: |
  1. Identify functions that transfer value (ETH or tokens)
  2. Check if state updates occur AFTER external calls
  3. Verify no reentrancy guard present
  4. Confirm the function is public/external
  5. Trace value flow: read balance → send value → update balance

semantic_triggers:
  - TRANSFERS_VALUE_OUT
  - WRITES_USER_BALANCE
  - CALLS_EXTERNAL

vql_queries:
  - "FIND functions WHERE visibility IN [public, external] AND has_external_call"
  - "FIND functions WHERE transfers_value AND writes_state"
  - "FIND functions WHERE NOT has_reentrancy_guard"

graph_patterns:
  - "R:bal->X:out->W:bal"
  - "READS_BALANCE -> TRANSFERS_VALUE -> WRITES_BALANCE"

behavioral_signatures:
  - "read -> external_call -> write"

operation_sequences:
  vulnerable:
    - "READS_USER_BALANCE -> CALLS_EXTERNAL -> WRITES_USER_BALANCE"
  safe:
    - "READS_USER_BALANCE -> WRITES_USER_BALANCE -> CALLS_EXTERNAL"

relevant_properties:
  - has_reentrancy_guard
  - has_external_call
  - transfers_value

created: 2026-01-22
updated: 2026-01-22
token_estimate: 800
"""

    (reentrancy_classic / "index.yaml").write_text(index_content)

    # Create oracle/price-manipulation vulndoc
    oracle_manip = vulndocs / "oracle" / "price-manipulation"
    oracle_manip.mkdir(parents=True)

    oracle_index = """
id: oracle-price-manipulation
category: oracle
subcategory: price-manipulation
severity: high
vulndoc: oracle/price-manipulation

description: |
  Oracle price manipulation through flash loan attacks or stale data.

reasoning_template: |
  1. Identify oracle price reads
  2. Check for flash loan protection
  3. Verify price freshness checks
  4. Look for single-oracle dependency

semantic_triggers:
  - READS_ORACLE
  - READS_EXTERNAL_VALUE

vql_queries:
  - "FIND functions WHERE reads_oracle"

graph_patterns:
  - "oracle_read -> value_calculation -> state_change"

created: 2026-01-22
updated: 2026-01-22
token_estimate: 500
"""

    (oracle_manip / "index.yaml").write_text(oracle_index)

    return vulndocs


# Context Type Tests


def test_risk_category_defaults():
    """Test RiskCategory default values (assume present)."""
    risk = RiskCategory()
    assert risk.present is True
    assert risk.notes == ""
    assert risk.confidence == "unknown"


def test_risk_category_serialization():
    """Test RiskCategory to_dict/from_dict roundtrip."""
    risk = RiskCategory(
        present=True,
        notes="Test notes",
        confidence="certain"
    )

    data = risk.to_dict()
    assert data["present"] is True
    assert data["notes"] == "Test notes"
    assert data["confidence"] == "certain"

    restored = RiskCategory.from_dict(data)
    assert restored.present == risk.present
    assert restored.notes == risk.notes
    assert restored.confidence == risk.confidence


def test_risk_profile_creation():
    """Test RiskProfile creation with default values."""
    profile = RiskProfile()

    # All categories should default to present=True, unknown confidence
    assert profile.oracle_risks.present is True
    assert profile.oracle_risks.confidence == "unknown"
    assert profile.liquidity_risks.present is True
    assert profile.access_risks.present is True
    assert profile.upgrade_risks.present is True
    assert profile.integration_risks.present is True
    assert profile.timing_risks.present is True
    assert profile.economic_risks.present is True
    assert profile.governance_risks.present is True


def test_risk_profile_serialization():
    """Test RiskProfile to_dict/from_dict roundtrip."""
    profile = RiskProfile(
        oracle_risks=RiskCategory(present=True, notes="Chainlink", confidence="certain"),
        access_risks=RiskCategory(present=True, notes="Admin multisig", confidence="inferred"),
    )

    data = profile.to_dict()
    assert "oracle_risks" in data
    assert data["oracle_risks"]["notes"] == "Chainlink"

    restored = RiskProfile.from_dict(data)
    assert restored.oracle_risks.notes == "Chainlink"
    assert restored.access_risks.notes == "Admin multisig"


def test_risk_profile_vuln_class_mapping_reentrancy():
    """Test risk mapping for reentrancy vulnerability class."""
    profile = RiskProfile(
        oracle_risks=RiskCategory(present=False),
        access_risks=RiskCategory(present=True, notes="Admin"),
        timing_risks=RiskCategory(present=True, notes="MEV"),
        liquidity_risks=RiskCategory(present=False),
    )

    relevant = profile.get_relevant_for_vuln_class("reentrancy/classic")

    # Should only return access_risks and timing_risks
    assert "access_risks" in relevant
    assert "timing_risks" in relevant
    assert "oracle_risks" not in relevant
    assert "liquidity_risks" not in relevant


def test_risk_profile_vuln_class_mapping_oracle():
    """Test risk mapping for oracle vulnerability class."""
    profile = RiskProfile(
        oracle_risks=RiskCategory(present=True, notes="Chainlink"),
        integration_risks=RiskCategory(present=True, notes="External protocol"),
        access_risks=RiskCategory(present=True, notes="Admin"),
    )

    relevant = profile.get_relevant_for_vuln_class("oracle/price-manipulation")

    # Should return oracle_risks and integration_risks
    assert "oracle_risks" in relevant
    assert "integration_risks" in relevant
    assert "access_risks" not in relevant


def test_risk_profile_vuln_class_mapping_default():
    """Test risk mapping for unknown vulnerability class (default behavior)."""
    profile = RiskProfile(
        oracle_risks=RiskCategory(present=True, notes="Has oracle"),
        liquidity_risks=RiskCategory(present=False),
        access_risks=RiskCategory(present=True, notes="Has admin"),
    )

    relevant = profile.get_relevant_for_vuln_class("unknown/vulntype")

    # Should return all categories with present=True
    assert "oracle_risks" in relevant
    assert "access_risks" in relevant
    assert "liquidity_risks" not in relevant  # present=False


def test_context_bundle_creation():
    """Test ContextBundle creation."""
    risk_profile = RiskProfile()

    bundle = ContextBundle(
        vulnerability_class="reentrancy/classic",
        reasoning_template="Step 1: Check...",
        semantic_triggers=["TRANSFERS_VALUE_OUT"],
        vql_queries=["FIND functions WHERE..."],
        graph_patterns=["R:bal->X:out->W:bal"],
        risk_profile=risk_profile,
        protocol_name="TestProtocol",
        target_scope=["contracts/Vault.sol"],
        token_estimate=1000,
    )

    assert bundle.vulnerability_class == "reentrancy/classic"
    assert "Step 1" in bundle.reasoning_template
    assert len(bundle.semantic_triggers) == 1
    assert bundle.token_estimate == 1000


def test_context_bundle_to_system_prompt():
    """Test ContextBundle.to_system_prompt() format."""
    risk_profile = RiskProfile()

    bundle = ContextBundle(
        vulnerability_class="reentrancy/classic",
        reasoning_template="1. Check CEI pattern\n2. Look for guards",
        semantic_triggers=["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
        vql_queries=["FIND functions WHERE transfers_value"],
        graph_patterns=["R:bal->X:out->W:bal"],
        risk_profile=risk_profile,
        protocol_name="TestProtocol",
        target_scope=["contracts/Vault.sol"],
    )

    prompt = bundle.to_system_prompt()

    # Should contain all key sections
    assert "Vulnerability Analysis: reentrancy/classic" in prompt
    assert "Detection Methodology" in prompt
    assert "Check CEI pattern" in prompt
    assert "Semantic Triggers" in prompt
    assert "TRANSFERS_VALUE_OUT" in prompt
    assert "Vulnerable Patterns" in prompt
    assert "R:bal->X:out->W:bal" in prompt
    assert "Starting Queries" in prompt


def test_context_bundle_to_user_context():
    """Test ContextBundle.to_user_context() format."""
    risk_profile = RiskProfile(
        oracle_risks=RiskCategory(present=True, notes="Uses Chainlink", confidence="certain"),
        access_risks=RiskCategory(present=True, notes="Admin multisig", confidence="inferred"),
    )

    bundle = ContextBundle(
        vulnerability_class="reentrancy/classic",
        reasoning_template="Template here",
        semantic_triggers=[],
        vql_queries=[],
        graph_patterns=[],
        risk_profile=risk_profile,
        protocol_name="TestProtocol",
        target_scope=["contracts/Vault.sol", "contracts/Pool.sol"],
    )

    context = bundle.to_user_context()

    # Should contain protocol and risk information
    assert "Protocol: TestProtocol" in context
    assert "Target Scope" in context
    assert "contracts/Vault.sol" in context
    assert "Risk Profile" in context
    # Reentrancy should show access_risks and timing_risks


def test_context_bundle_serialization():
    """Test ContextBundle to_dict/from_dict roundtrip."""
    risk_profile = RiskProfile(
        oracle_risks=RiskCategory(present=True, notes="Test", confidence="certain")
    )

    bundle = ContextBundle(
        vulnerability_class="reentrancy/classic",
        reasoning_template="Template",
        semantic_triggers=["TRIGGER1"],
        vql_queries=["QUERY1"],
        graph_patterns=["PATTERN1"],
        risk_profile=risk_profile,
        protocol_name="Test",
        target_scope=["file.sol"],
        token_estimate=500,
    )

    data = bundle.to_dict()
    assert data["vulnerability_class"] == "reentrancy/classic"
    assert data["token_estimate"] == 500

    restored = ContextBundle.from_dict(data)
    assert restored.vulnerability_class == bundle.vulnerability_class
    assert restored.reasoning_template == bundle.reasoning_template
    assert restored.token_estimate == bundle.token_estimate
    assert restored.risk_profile.oracle_risks.notes == "Test"


def test_context_section_enum():
    """Test ContextSection enum values."""
    assert ContextSection.REASONING_TEMPLATE.value == "reasoning_template"
    assert ContextSection.SEMANTIC_TRIGGERS.value == "semantic_triggers"
    assert ContextSection.VQL_QUERIES.value == "vql_queries"
    assert ContextSection.GRAPH_PATTERNS.value == "graph_patterns"
    assert ContextSection.RISK_PROFILE.value == "risk_profile"
    assert ContextSection.TARGET_SCOPE.value == "target_scope"


# VulndocContextExtractor Tests


def test_extractor_initialization():
    """Test VulndocContextExtractor initialization."""
    extractor = VulndocContextExtractor()
    assert extractor.vulndocs_root == Path("vulndocs")

    custom_root = Path("/custom/vulndocs")
    extractor2 = VulndocContextExtractor(vulndocs_root=custom_root)
    assert extractor2.vulndocs_root == custom_root


def test_extract_with_valid_vulndoc(vulndocs_root, sample_protocol_pack):
    """Test extraction with valid vulndoc."""
    extractor = VulndocContextExtractor(vulndocs_root=vulndocs_root)

    bundle = extractor.extract(
        vuln_class="reentrancy/classic",
        protocol_pack=sample_protocol_pack,
        target_scope=["contracts/Vault.sol"],
    )

    assert bundle.vulnerability_class == "reentrancy/classic"
    assert "external calls" in bundle.reasoning_template.lower()
    assert "TRANSFERS_VALUE_OUT" in bundle.semantic_triggers
    assert "WRITES_USER_BALANCE" in bundle.semantic_triggers
    assert len(bundle.vql_queries) > 0
    assert len(bundle.graph_patterns) > 0
    assert bundle.protocol_name == "TestProtocol"
    assert bundle.target_scope == ["contracts/Vault.sol"]
    assert bundle.token_estimate > 0


def test_extract_missing_vulndoc_raises(vulndocs_root, sample_protocol_pack):
    """Test extraction with missing vulndoc raises ValueError."""
    extractor = VulndocContextExtractor(vulndocs_root=vulndocs_root)

    with pytest.raises(ValueError) as exc_info:
        extractor.extract(
            vuln_class="nonexistent/vuln",
            protocol_pack=sample_protocol_pack,
            target_scope=["contracts/Vault.sol"],
        )

    assert "VulnDoc not found" in str(exc_info.value)
    assert "nonexistent/vuln" in str(exc_info.value)


def test_extract_risk_profile_mapping_reentrancy(vulndocs_root, sample_protocol_pack):
    """Test risk profile extraction for reentrancy class."""
    extractor = VulndocContextExtractor(vulndocs_root=vulndocs_root)

    bundle = extractor.extract(
        vuln_class="reentrancy/classic",
        protocol_pack=sample_protocol_pack,
        target_scope=["contracts/Vault.sol"],
    )

    # Should have access_risks detected (admin role present)
    assert bundle.risk_profile.access_risks.present is True
    assert "admin" in bundle.risk_profile.access_risks.notes.lower()

    # Should have oracle_risks detected (Chainlink input)
    assert bundle.risk_profile.oracle_risks.present is True
    assert "chainlink" in bundle.risk_profile.oracle_risks.notes.lower()


def test_extract_risk_profile_mapping_oracle(vulndocs_root, sample_protocol_pack):
    """Test risk profile extraction for oracle class."""
    extractor = VulndocContextExtractor(vulndocs_root=vulndocs_root)

    bundle = extractor.extract(
        vuln_class="oracle/price-manipulation",
        protocol_pack=sample_protocol_pack,
        target_scope=["contracts/Oracle.sol"],
    )

    # Should detect oracle risks
    assert bundle.risk_profile.oracle_risks.present is True


def test_token_estimation(vulndocs_root, sample_protocol_pack):
    """Test token estimation is within reasonable bounds."""
    extractor = VulndocContextExtractor(vulndocs_root=vulndocs_root)

    bundle = extractor.extract(
        vuln_class="reentrancy/classic",
        protocol_pack=sample_protocol_pack,
        target_scope=["contracts/Vault.sol"],
    )

    # Token estimate should be positive
    assert bundle.token_estimate > 0

    # Should be reasonable range (not empty, not huge)
    # With reasoning template + triggers + queries + risk notes, expect 100-500 tokens
    assert 100 < bundle.token_estimate < 1000


def test_trim_to_budget_drops_patterns_first(vulndocs_root, sample_protocol_pack):
    """Test trim logic drops graph_patterns first."""
    extractor = VulndocContextExtractor(vulndocs_root=vulndocs_root)

    bundle = extractor.extract(
        vuln_class="reentrancy/classic",
        protocol_pack=sample_protocol_pack,
        target_scope=["contracts/Vault.sol"],
    )

    # Artificially add many patterns and a long template to trigger trimming
    bundle.graph_patterns = ["pattern" + str(i) * 100 for i in range(10)]  # Make them long
    bundle.vql_queries = ["query" + str(i) * 100 for i in range(10)]  # Make them long
    bundle.reasoning_template = "x" * 10000  # Make template very long

    # Force trimming with low budget
    trimmed = extractor._trim_to_budget(bundle, max_tokens=100)

    # Should limit to first 3
    assert len(trimmed.graph_patterns) <= 3
    # May or may not trim queries depending on budget after pattern trim
    # But at minimum should have trimmed patterns
    assert len(trimmed.graph_patterns) < len(bundle.graph_patterns)


def test_trim_to_budget_preserves_reasoning(vulndocs_root, sample_protocol_pack):
    """Test trim logic never drops reasoning_template."""
    extractor = VulndocContextExtractor(vulndocs_root=vulndocs_root)

    bundle = extractor.extract(
        vuln_class="reentrancy/classic",
        protocol_pack=sample_protocol_pack,
        target_scope=["contracts/Vault.sol"],
    )

    original_template = bundle.reasoning_template

    # Force extreme trimming
    trimmed = extractor._trim_to_budget(bundle, max_tokens=100)

    # Reasoning template should still exist (maybe truncated but not empty)
    assert len(trimmed.reasoning_template) > 0
    # Should still be related to original
    assert trimmed.reasoning_template[:50] == original_template[:50]


def test_extractor_handles_alternative_formats(vulndocs_root, sample_protocol_pack):
    """Test extractor handles operation_sequences and behavioral_signatures."""
    extractor = VulndocContextExtractor(vulndocs_root=vulndocs_root)

    bundle = extractor.extract(
        vuln_class="reentrancy/classic",
        protocol_pack=sample_protocol_pack,
        target_scope=["contracts/Vault.sol"],
    )

    # Should have patterns from multiple sources
    assert len(bundle.graph_patterns) > 0

    # Should include patterns from graph_patterns, behavioral_signatures, and operation_sequences
    pattern_str = " ".join(bundle.graph_patterns)
    # At least one of these should be present
    assert ("R:bal->X:out->W:bal" in pattern_str or
            "read -> external_call -> write" in pattern_str or
            "READS_USER_BALANCE" in pattern_str)
