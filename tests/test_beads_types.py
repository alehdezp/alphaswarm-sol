"""Tests for beads foundation types.

Task 6.0: Comprehensive tests for all foundation types.
"""

import json
import pytest
from datetime import datetime, timedelta
from typing import Any, Dict

from alphaswarm_sol.beads import (
    Severity,
    BeadStatus,
    VerdictType,
    CodeSnippet,
    InvestigationStep,
    ExploitReference,
    Verdict,
    Finding,
)


class TestSeverity:
    """Tests for Severity enum."""

    def test_all_severity_values_exist(self):
        """Verify all expected severity levels exist."""
        assert Severity.CRITICAL.value == "critical"
        assert Severity.HIGH.value == "high"
        assert Severity.MEDIUM.value == "medium"
        assert Severity.LOW.value == "low"
        assert Severity.INFO.value == "info"

    def test_from_string_lowercase(self):
        """Test from_string with lowercase input."""
        assert Severity.from_string("critical") == Severity.CRITICAL
        assert Severity.from_string("high") == Severity.HIGH
        assert Severity.from_string("medium") == Severity.MEDIUM
        assert Severity.from_string("low") == Severity.LOW
        assert Severity.from_string("info") == Severity.INFO

    def test_from_string_uppercase(self):
        """Test from_string with uppercase input."""
        assert Severity.from_string("CRITICAL") == Severity.CRITICAL
        assert Severity.from_string("HIGH") == Severity.HIGH
        assert Severity.from_string("MEDIUM") == Severity.MEDIUM

    def test_from_string_mixed_case(self):
        """Test from_string with mixed case input."""
        assert Severity.from_string("Critical") == Severity.CRITICAL
        assert Severity.from_string("HiGh") == Severity.HIGH

    def test_from_string_with_whitespace(self):
        """Test from_string with leading/trailing whitespace."""
        assert Severity.from_string("  critical  ") == Severity.CRITICAL
        assert Severity.from_string("\thigh\n") == Severity.HIGH

    def test_from_string_aliases(self):
        """Test from_string with common aliases."""
        assert Severity.from_string("crit") == Severity.CRITICAL
        assert Severity.from_string("hi") == Severity.HIGH
        assert Severity.from_string("med") == Severity.MEDIUM
        assert Severity.from_string("lo") == Severity.LOW
        assert Severity.from_string("informational") == Severity.INFO

    def test_from_string_invalid_raises(self):
        """Test from_string with invalid input raises ValueError."""
        with pytest.raises(ValueError):
            Severity.from_string("invalid")
        with pytest.raises(ValueError):
            Severity.from_string("")


class TestBeadStatus:
    """Tests for BeadStatus enum."""

    def test_all_status_values_exist(self):
        """Verify all expected status values exist."""
        assert BeadStatus.PENDING.value == "pending"
        assert BeadStatus.INVESTIGATING.value == "investigating"
        assert BeadStatus.CONFIRMED.value == "confirmed"
        assert BeadStatus.REJECTED.value == "rejected"
        assert BeadStatus.NEEDS_INFO.value == "needs_info"

    def test_status_workflow(self):
        """Test typical status workflow transitions."""
        status = BeadStatus.PENDING
        assert status == BeadStatus.PENDING

        status = BeadStatus.INVESTIGATING
        assert status == BeadStatus.INVESTIGATING

        status = BeadStatus.CONFIRMED
        assert status == BeadStatus.CONFIRMED


class TestVerdictType:
    """Tests for VerdictType enum."""

    def test_all_verdict_types_exist(self):
        """Verify all expected verdict types exist."""
        assert VerdictType.TRUE_POSITIVE.value == "true_positive"
        assert VerdictType.FALSE_POSITIVE.value == "false_positive"
        assert VerdictType.INCONCLUSIVE.value == "inconclusive"


class TestCodeSnippet:
    """Tests for CodeSnippet dataclass."""

    def test_basic_creation(self):
        """Test basic CodeSnippet creation."""
        snippet = CodeSnippet(
            source="function withdraw() { ... }",
            file_path="/path/to/Vault.sol",
            start_line=10,
            end_line=20,
        )
        assert snippet.source == "function withdraw() { ... }"
        assert snippet.file_path == "/path/to/Vault.sol"
        assert snippet.start_line == 10
        assert snippet.end_line == 20
        assert snippet.function_name is None
        assert snippet.contract_name is None

    def test_creation_with_optional_fields(self):
        """Test CodeSnippet creation with optional fields."""
        snippet = CodeSnippet(
            source="function withdraw() { ... }",
            file_path="/path/to/Vault.sol",
            start_line=10,
            end_line=20,
            function_name="withdraw",
            contract_name="Vault",
        )
        assert snippet.function_name == "withdraw"
        assert snippet.contract_name == "Vault"

    def test_to_dict(self):
        """Test to_dict serialization."""
        snippet = CodeSnippet(
            source="code",
            file_path="/path",
            start_line=1,
            end_line=5,
            function_name="fn",
            contract_name="Contract",
        )
        data = snippet.to_dict()
        assert data["source"] == "code"
        assert data["file_path"] == "/path"
        assert data["start_line"] == 1
        assert data["end_line"] == 5
        assert data["function_name"] == "fn"
        assert data["contract_name"] == "Contract"

    def test_from_dict(self):
        """Test from_dict deserialization."""
        data = {
            "source": "code",
            "file_path": "/path",
            "start_line": 1,
            "end_line": 5,
            "function_name": "fn",
            "contract_name": "Contract",
        }
        snippet = CodeSnippet.from_dict(data)
        assert snippet.source == "code"
        assert snippet.start_line == 1
        assert snippet.function_name == "fn"

    def test_round_trip_serialization(self):
        """Test full round-trip serialization."""
        original = CodeSnippet(
            source="function withdraw() { ... }",
            file_path="/path/to/Vault.sol",
            start_line=10,
            end_line=20,
            function_name="withdraw",
            contract_name="Vault",
        )
        data = original.to_dict()
        restored = CodeSnippet.from_dict(data)

        assert restored.source == original.source
        assert restored.file_path == original.file_path
        assert restored.start_line == original.start_line
        assert restored.end_line == original.end_line
        assert restored.function_name == original.function_name
        assert restored.contract_name == original.contract_name

    def test_json_serializable(self):
        """Test that to_dict output is JSON serializable."""
        snippet = CodeSnippet(
            source="code",
            file_path="/path",
            start_line=1,
            end_line=5,
        )
        # Should not raise
        json_str = json.dumps(snippet.to_dict())
        assert isinstance(json_str, str)

    def test_line_count_property(self):
        """Test line_count calculated property."""
        snippet = CodeSnippet(
            source="code",
            file_path="/path",
            start_line=10,
            end_line=15,
        )
        assert snippet.line_count == 6

    def test_line_count_single_line(self):
        """Test line_count for single line snippet."""
        snippet = CodeSnippet(
            source="code",
            file_path="/path",
            start_line=10,
            end_line=10,
        )
        assert snippet.line_count == 1

    def test_location_property(self):
        """Test location calculated property."""
        snippet = CodeSnippet(
            source="code",
            file_path="/path/to/Vault.sol",
            start_line=10,
            end_line=20,
        )
        assert snippet.location == "Vault.sol:10-20"

    def test_location_property_single_line(self):
        """Test location property for single line."""
        snippet = CodeSnippet(
            source="code",
            file_path="/path/to/Vault.sol",
            start_line=10,
            end_line=10,
        )
        assert snippet.location == "Vault.sol:10"


class TestInvestigationStep:
    """Tests for InvestigationStep dataclass."""

    def test_basic_creation(self):
        """Test basic InvestigationStep creation."""
        step = InvestigationStep(
            step_number=1,
            action="Check external calls",
            look_for="call, send, transfer",
            evidence_needed="External call found",
        )
        assert step.step_number == 1
        assert step.action == "Check external calls"
        assert step.look_for == "call, send, transfer"
        assert step.evidence_needed == "External call found"
        assert step.red_flag is None
        assert step.safe_if is None

    def test_creation_with_optional_fields(self):
        """Test InvestigationStep with optional fields."""
        step = InvestigationStep(
            step_number=1,
            action="Check external calls",
            look_for="call, send, transfer",
            evidence_needed="External call found",
            red_flag="Call before state update",
            safe_if="Has nonReentrant modifier",
        )
        assert step.red_flag == "Call before state update"
        assert step.safe_if == "Has nonReentrant modifier"

    def test_to_dict(self):
        """Test to_dict serialization."""
        step = InvestigationStep(
            step_number=1,
            action="Check",
            look_for="calls",
            evidence_needed="found",
            red_flag="before update",
            safe_if="has guard",
        )
        data = step.to_dict()
        assert data["step_number"] == 1
        assert data["action"] == "Check"
        assert data["red_flag"] == "before update"
        assert data["safe_if"] == "has guard"

    def test_from_dict(self):
        """Test from_dict deserialization."""
        data = {
            "step_number": 1,
            "action": "Check",
            "look_for": "calls",
            "evidence_needed": "found",
            "red_flag": "before update",
            "safe_if": "has guard",
        }
        step = InvestigationStep.from_dict(data)
        assert step.step_number == 1
        assert step.red_flag == "before update"

    def test_round_trip_serialization(self):
        """Test full round-trip serialization."""
        original = InvestigationStep(
            step_number=1,
            action="Check external calls",
            look_for="call, send, transfer",
            evidence_needed="External call found",
            red_flag="Call before state update",
            safe_if="Has nonReentrant modifier",
        )
        data = original.to_dict()
        restored = InvestigationStep.from_dict(data)

        assert restored.step_number == original.step_number
        assert restored.action == original.action
        assert restored.red_flag == original.red_flag

    def test_json_serializable(self):
        """Test that to_dict output is JSON serializable."""
        step = InvestigationStep(
            step_number=1,
            action="Check",
            look_for="calls",
            evidence_needed="found",
        )
        json_str = json.dumps(step.to_dict())
        assert isinstance(json_str, str)


class TestExploitReference:
    """Tests for ExploitReference dataclass."""

    def test_basic_creation(self):
        """Test basic ExploitReference creation."""
        exploit = ExploitReference(
            id="the-dao-2016",
            name="The DAO Hack",
            date="2016-06-17",
            loss="$60M",
            pattern_id="reentrancy-classic",
            vulnerable_code="function splitDAO() { ... }",
            exploit_summary="Recursive call attack",
            fix="Use nonReentrant modifier",
            source_url="https://example.com",
        )
        assert exploit.id == "the-dao-2016"
        assert exploit.name == "The DAO Hack"
        assert exploit.loss == "$60M"

    def test_to_dict(self):
        """Test to_dict serialization."""
        exploit = ExploitReference(
            id="test",
            name="Test",
            date="2024-01-01",
            loss="$1M",
            pattern_id="test-001",
            vulnerable_code="code",
            exploit_summary="summary",
            fix="fix",
            source_url="https://example.com",
        )
        data = exploit.to_dict()
        assert data["id"] == "test"
        assert data["loss"] == "$1M"
        assert data["source_url"] == "https://example.com"

    def test_from_dict(self):
        """Test from_dict deserialization."""
        data = {
            "id": "test",
            "name": "Test",
            "date": "2024-01-01",
            "loss": "$1M",
            "pattern_id": "test-001",
            "vulnerable_code": "code",
            "exploit_summary": "summary",
            "fix": "fix",
            "source_url": "https://example.com",
        }
        exploit = ExploitReference.from_dict(data)
        assert exploit.id == "test"
        assert exploit.loss == "$1M"

    def test_round_trip_serialization(self):
        """Test full round-trip serialization."""
        original = ExploitReference(
            id="the-dao-2016",
            name="The DAO Hack",
            date="2016-06-17",
            loss="$60M",
            pattern_id="reentrancy-classic",
            vulnerable_code="function splitDAO() { ... }",
            exploit_summary="Recursive call attack",
            fix="Use nonReentrant modifier",
            source_url="https://example.com",
        )
        data = original.to_dict()
        restored = ExploitReference.from_dict(data)

        assert restored.id == original.id
        assert restored.name == original.name
        assert restored.loss == original.loss

    def test_json_serializable(self):
        """Test that to_dict output is JSON serializable."""
        exploit = ExploitReference(
            id="test",
            name="Test",
            date="2024-01-01",
            loss="$1M",
            pattern_id="test-001",
            vulnerable_code="code",
            exploit_summary="summary",
            fix="fix",
            source_url="https://example.com",
        )
        json_str = json.dumps(exploit.to_dict())
        assert isinstance(json_str, str)


class TestVerdict:
    """Tests for Verdict dataclass."""

    def test_basic_creation(self):
        """Test basic Verdict creation."""
        verdict = Verdict(
            type=VerdictType.TRUE_POSITIVE,
            reason="Confirmed via PoC",
            confidence=0.99,
            evidence=["test passed"],
        )
        assert verdict.type == VerdictType.TRUE_POSITIVE
        assert verdict.reason == "Confirmed via PoC"
        assert verdict.confidence == 0.99
        assert verdict.evidence == ["test passed"]
        assert verdict.auditor_id is None
        assert isinstance(verdict.timestamp, datetime)

    def test_creation_with_optional_fields(self):
        """Test Verdict with optional fields."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        verdict = Verdict(
            type=VerdictType.TRUE_POSITIVE,
            reason="Confirmed",
            confidence=0.95,
            evidence=["evidence"],
            timestamp=timestamp,
            auditor_id="vkg-tier-b",
        )
        assert verdict.timestamp == timestamp
        assert verdict.auditor_id == "vkg-tier-b"

    def test_confidence_validation(self):
        """Test confidence must be in [0.0, 1.0] range."""
        # Valid values
        Verdict(
            type=VerdictType.TRUE_POSITIVE,
            reason="test",
            confidence=0.0,
            evidence=[],
        )
        Verdict(
            type=VerdictType.TRUE_POSITIVE,
            reason="test",
            confidence=1.0,
            evidence=[],
        )
        Verdict(
            type=VerdictType.TRUE_POSITIVE,
            reason="test",
            confidence=0.5,
            evidence=[],
        )

        # Invalid values
        with pytest.raises(ValueError):
            Verdict(
                type=VerdictType.TRUE_POSITIVE,
                reason="test",
                confidence=-0.1,
                evidence=[],
            )
        with pytest.raises(ValueError):
            Verdict(
                type=VerdictType.TRUE_POSITIVE,
                reason="test",
                confidence=1.1,
                evidence=[],
            )

    def test_to_dict(self):
        """Test to_dict serialization."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        verdict = Verdict(
            type=VerdictType.TRUE_POSITIVE,
            reason="Confirmed",
            confidence=0.95,
            evidence=["ev1", "ev2"],
            timestamp=timestamp,
            auditor_id="vkg",
        )
        data = verdict.to_dict()
        assert data["type"] == "true_positive"
        assert data["reason"] == "Confirmed"
        assert data["confidence"] == 0.95
        assert data["evidence"] == ["ev1", "ev2"]
        assert data["timestamp"] == "2024-01-01T12:00:00"
        assert data["auditor_id"] == "vkg"

    def test_from_dict(self):
        """Test from_dict deserialization."""
        data = {
            "type": "true_positive",
            "reason": "Confirmed",
            "confidence": 0.95,
            "evidence": ["ev1"],
            "timestamp": "2024-01-01T12:00:00",
            "auditor_id": "vkg",
        }
        verdict = Verdict.from_dict(data)
        assert verdict.type == VerdictType.TRUE_POSITIVE
        assert verdict.confidence == 0.95
        assert verdict.timestamp == datetime(2024, 1, 1, 12, 0, 0)
        assert verdict.auditor_id == "vkg"

    def test_round_trip_serialization(self):
        """Test full round-trip serialization."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        original = Verdict(
            type=VerdictType.FALSE_POSITIVE,
            reason="Safe pattern",
            confidence=0.88,
            evidence=["has guard", "CEI pattern"],
            timestamp=timestamp,
            auditor_id="manual",
        )
        data = original.to_dict()
        restored = Verdict.from_dict(data)

        assert restored.type == original.type
        assert restored.reason == original.reason
        assert restored.confidence == original.confidence
        assert restored.evidence == original.evidence
        assert restored.timestamp == original.timestamp
        assert restored.auditor_id == original.auditor_id

    def test_timestamp_serialization(self):
        """Test timestamp is serialized to ISO format."""
        verdict = Verdict(
            type=VerdictType.TRUE_POSITIVE,
            reason="test",
            confidence=0.9,
            evidence=[],
        )
        data = verdict.to_dict()
        assert "timestamp" in data
        # Should be ISO format parseable
        datetime.fromisoformat(data["timestamp"])

    def test_json_serializable(self):
        """Test that to_dict output is JSON serializable."""
        verdict = Verdict(
            type=VerdictType.TRUE_POSITIVE,
            reason="test",
            confidence=0.9,
            evidence=["ev"],
        )
        json_str = json.dumps(verdict.to_dict())
        assert isinstance(json_str, str)

    def test_is_positive_property(self):
        """Test is_positive property."""
        tp = Verdict(
            type=VerdictType.TRUE_POSITIVE,
            reason="test",
            confidence=0.9,
            evidence=[],
        )
        fp = Verdict(
            type=VerdictType.FALSE_POSITIVE,
            reason="test",
            confidence=0.9,
            evidence=[],
        )
        inc = Verdict(
            type=VerdictType.INCONCLUSIVE,
            reason="test",
            confidence=0.5,
            evidence=[],
        )
        assert tp.is_positive is True
        assert fp.is_positive is False
        assert inc.is_positive is False

    def test_is_negative_property(self):
        """Test is_negative property."""
        tp = Verdict(
            type=VerdictType.TRUE_POSITIVE,
            reason="test",
            confidence=0.9,
            evidence=[],
        )
        fp = Verdict(
            type=VerdictType.FALSE_POSITIVE,
            reason="test",
            confidence=0.9,
            evidence=[],
        )
        assert tp.is_negative is False
        assert fp.is_negative is True


class TestFinding:
    """Tests for Finding dataclass."""

    def test_basic_creation(self):
        """Test basic Finding creation."""
        finding = Finding(
            id="VKG-001",
            pattern_id="vm-001",
            function_id="func_123",
            contract_name="Vault",
            function_name="withdraw",
            file_path="/path/to/Vault.sol",
            line_number=45,
            severity=Severity.CRITICAL,
            confidence=0.95,
            vulnerability_class="reentrancy",
            description="State update after external call",
        )
        assert finding.id == "VKG-001"
        assert finding.pattern_id == "vm-001"
        assert finding.severity == Severity.CRITICAL
        assert finding.confidence == 0.95
        assert finding.evidence == []

    def test_creation_with_evidence(self):
        """Test Finding creation with evidence list."""
        finding = Finding(
            id="VKG-001",
            pattern_id="vm-001",
            function_id="func_123",
            contract_name="Vault",
            function_name="withdraw",
            file_path="/path/to/Vault.sol",
            line_number=45,
            severity=Severity.CRITICAL,
            confidence=0.95,
            vulnerability_class="reentrancy",
            description="State update after external call",
            evidence=["External call at line 48", "Balance write at line 52"],
        )
        assert len(finding.evidence) == 2

    def test_confidence_validation(self):
        """Test confidence must be in [0.0, 1.0] range."""
        # Valid values
        Finding(
            id="VKG-001",
            pattern_id="vm-001",
            function_id="func_123",
            contract_name="Vault",
            function_name="withdraw",
            file_path="/path",
            line_number=1,
            severity=Severity.MEDIUM,
            confidence=0.0,
            vulnerability_class="test",
            description="test",
        )
        Finding(
            id="VKG-001",
            pattern_id="vm-001",
            function_id="func_123",
            contract_name="Vault",
            function_name="withdraw",
            file_path="/path",
            line_number=1,
            severity=Severity.MEDIUM,
            confidence=1.0,
            vulnerability_class="test",
            description="test",
        )

        # Invalid values
        with pytest.raises(ValueError):
            Finding(
                id="VKG-001",
                pattern_id="vm-001",
                function_id="func_123",
                contract_name="Vault",
                function_name="withdraw",
                file_path="/path",
                line_number=1,
                severity=Severity.MEDIUM,
                confidence=-0.1,
                vulnerability_class="test",
                description="test",
            )
        with pytest.raises(ValueError):
            Finding(
                id="VKG-001",
                pattern_id="vm-001",
                function_id="func_123",
                contract_name="Vault",
                function_name="withdraw",
                file_path="/path",
                line_number=1,
                severity=Severity.MEDIUM,
                confidence=1.1,
                vulnerability_class="test",
                description="test",
            )

    def test_severity_enum(self):
        """Test severity is properly an enum."""
        finding = Finding(
            id="VKG-001",
            pattern_id="vm-001",
            function_id="func_123",
            contract_name="Vault",
            function_name="withdraw",
            file_path="/path/to/Vault.sol",
            line_number=45,
            severity=Severity.CRITICAL,
            confidence=0.95,
            vulnerability_class="reentrancy",
            description="test",
        )
        assert finding.severity == Severity.CRITICAL
        data = finding.to_dict()
        assert data["severity"] == "critical"

    def test_to_dict(self):
        """Test to_dict serialization."""
        finding = Finding(
            id="VKG-001",
            pattern_id="vm-001",
            function_id="func_123",
            contract_name="Vault",
            function_name="withdraw",
            file_path="/path/to/Vault.sol",
            line_number=45,
            severity=Severity.HIGH,
            confidence=0.85,
            vulnerability_class="access_control",
            description="Missing access check",
            evidence=["ev1"],
        )
        data = finding.to_dict()
        assert data["id"] == "VKG-001"
        assert data["severity"] == "high"
        assert data["confidence"] == 0.85
        assert data["evidence"] == ["ev1"]

    def test_from_dict(self):
        """Test from_dict deserialization."""
        data = {
            "id": "VKG-001",
            "pattern_id": "vm-001",
            "function_id": "func_123",
            "contract_name": "Vault",
            "function_name": "withdraw",
            "file_path": "/path",
            "line_number": 45,
            "severity": "critical",
            "confidence": 0.95,
            "vulnerability_class": "reentrancy",
            "description": "test",
            "evidence": ["ev1"],
        }
        finding = Finding.from_dict(data)
        assert finding.id == "VKG-001"
        assert finding.severity == Severity.CRITICAL
        assert finding.evidence == ["ev1"]

    def test_from_dict_severity_aliases(self):
        """Test from_dict handles severity aliases."""
        data = {
            "id": "VKG-001",
            "pattern_id": "vm-001",
            "function_id": "func_123",
            "contract_name": "Vault",
            "function_name": "withdraw",
            "file_path": "/path",
            "line_number": 45,
            "severity": "crit",
            "confidence": 0.95,
            "vulnerability_class": "reentrancy",
            "description": "test",
        }
        finding = Finding.from_dict(data)
        assert finding.severity == Severity.CRITICAL

    def test_round_trip_serialization(self):
        """Test full round-trip serialization."""
        original = Finding(
            id="VKG-001",
            pattern_id="vm-001",
            function_id="func_123",
            contract_name="Vault",
            function_name="withdraw",
            file_path="/path/to/Vault.sol",
            line_number=45,
            severity=Severity.CRITICAL,
            confidence=0.95,
            vulnerability_class="reentrancy",
            description="State update after external call",
            evidence=["ev1", "ev2"],
        )
        data = original.to_dict()
        restored = Finding.from_dict(data)

        assert restored.id == original.id
        assert restored.pattern_id == original.pattern_id
        assert restored.severity == original.severity
        assert restored.confidence == original.confidence
        assert restored.evidence == original.evidence

    def test_json_serializable(self):
        """Test that to_dict output is JSON serializable."""
        finding = Finding(
            id="VKG-001",
            pattern_id="vm-001",
            function_id="func_123",
            contract_name="Vault",
            function_name="withdraw",
            file_path="/path",
            line_number=1,
            severity=Severity.MEDIUM,
            confidence=0.5,
            vulnerability_class="test",
            description="test",
        )
        json_str = json.dumps(finding.to_dict())
        assert isinstance(json_str, str)

    def test_location_property(self):
        """Test location calculated property."""
        finding = Finding(
            id="VKG-001",
            pattern_id="vm-001",
            function_id="func_123",
            contract_name="Vault",
            function_name="withdraw",
            file_path="/path",
            line_number=45,
            severity=Severity.MEDIUM,
            confidence=0.5,
            vulnerability_class="test",
            description="test",
        )
        assert finding.location == "Vault.withdraw():45"

    def test_is_critical_property(self):
        """Test is_critical property."""
        critical = Finding(
            id="VKG-001",
            pattern_id="vm-001",
            function_id="func_123",
            contract_name="Vault",
            function_name="withdraw",
            file_path="/path",
            line_number=1,
            severity=Severity.CRITICAL,
            confidence=0.5,
            vulnerability_class="test",
            description="test",
        )
        high = Finding(
            id="VKG-002",
            pattern_id="vm-001",
            function_id="func_123",
            contract_name="Vault",
            function_name="withdraw",
            file_path="/path",
            line_number=1,
            severity=Severity.HIGH,
            confidence=0.5,
            vulnerability_class="test",
            description="test",
        )
        assert critical.is_critical is True
        assert high.is_critical is False

    def test_is_high_severity_property(self):
        """Test is_high_severity property."""
        critical = Finding(
            id="VKG-001",
            pattern_id="vm-001",
            function_id="func_123",
            contract_name="Vault",
            function_name="withdraw",
            file_path="/path",
            line_number=1,
            severity=Severity.CRITICAL,
            confidence=0.5,
            vulnerability_class="test",
            description="test",
        )
        high = Finding(
            id="VKG-002",
            pattern_id="vm-001",
            function_id="func_123",
            contract_name="Vault",
            function_name="withdraw",
            file_path="/path",
            line_number=1,
            severity=Severity.HIGH,
            confidence=0.5,
            vulnerability_class="test",
            description="test",
        )
        medium = Finding(
            id="VKG-003",
            pattern_id="vm-001",
            function_id="func_123",
            contract_name="Vault",
            function_name="withdraw",
            file_path="/path",
            line_number=1,
            severity=Severity.MEDIUM,
            confidence=0.5,
            vulnerability_class="test",
            description="test",
        )
        assert critical.is_high_severity is True
        assert high.is_high_severity is True
        assert medium.is_high_severity is False


class TestModuleImports:
    """Tests for module-level imports."""

    def test_import_from_package(self):
        """Test imports work from package level."""
        from alphaswarm_sol.beads import (
            Severity,
            BeadStatus,
            VerdictType,
            CodeSnippet,
            InvestigationStep,
            ExploitReference,
            Verdict,
            Finding,
        )

        # Should not raise
        assert Severity.CRITICAL.value == "critical"
        assert BeadStatus.PENDING.value == "pending"
        assert VerdictType.TRUE_POSITIVE.value == "true_positive"

    def test_import_from_types_module(self):
        """Test imports work from types module."""
        from alphaswarm_sol.beads.types import (
            Severity,
            BeadStatus,
            VerdictType,
            CodeSnippet,
            InvestigationStep,
            ExploitReference,
            Verdict,
            Finding,
        )

        # Should not raise
        assert Severity.CRITICAL.value == "critical"


class TestIntegrationWithAdversarialKG:
    """Tests for integration with adversarial_kg module."""

    def test_exploit_reference_from_exploit_record(self):
        """Test ExploitReference.from_exploit_record integration."""
        # Import the existing ExploitRecord from adversarial_kg
        from alphaswarm_sol.knowledge.adversarial_kg import ExploitRecord, AttackCategory

        record = ExploitRecord(
            id="test_exploit",
            name="Test Exploit",
            date="2024-01-01",
            loss_usd=1_000_000,
            chain="ethereum",
            category=AttackCategory.REENTRANCY,
            cwes=["CWE-841"],
            pattern_ids=["reentrancy_classic"],
            attack_summary="Test attack summary",
            attack_steps=["Step 1", "Step 2"],
            postmortem_url="https://example.com/postmortem",
        )

        ref = ExploitReference.from_exploit_record(
            record,
            pattern_id="vm-001",
            vulnerable_code="function withdraw() { ... }",
            fix="Use nonReentrant modifier",
        )

        assert ref.id == "test_exploit"
        assert ref.name == "Test Exploit"
        assert ref.loss == "$1,000,000"
        assert ref.pattern_id == "vm-001"
        assert ref.vulnerable_code == "function withdraw() { ... }"
        assert ref.exploit_summary == "Test attack summary"
        assert ref.fix == "Use nonReentrant modifier"
        assert ref.source_url == "https://example.com/postmortem"

    def test_exploit_reference_from_exploit_record_minimal(self):
        """Test ExploitReference.from_exploit_record with minimal data."""
        from alphaswarm_sol.knowledge.adversarial_kg import ExploitRecord, AttackCategory

        record = ExploitRecord(
            id="min_exploit",
            name="Minimal",
            date="2024-01-01",
            loss_usd=100,
            chain="ethereum",
            category=AttackCategory.ACCESS_CONTROL,
            cwes=[],
            pattern_ids=[],
            attack_summary="Brief",
            attack_steps=[],
        )

        ref = ExploitReference.from_exploit_record(record, pattern_id="auth-001")

        assert ref.id == "min_exploit"
        assert ref.loss == "$100"
        assert ref.vulnerable_code == ""
        assert ref.fix == "See postmortem for remediation guidance"
        assert ref.source_url == ""
