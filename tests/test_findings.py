"""
Tests for Findings Data Model

Comprehensive tests for Finding, FindingsStore, and related classes.
"""

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from alphaswarm_sol.findings.model import (
    Evidence,
    EvidenceRef,
    Finding,
    FindingConfidence,
    FindingSeverity,
    FindingStatus,
    FindingTier,
    FINDING_SCHEMA_VERSION,
    Location,
)
from alphaswarm_sol.findings.store import FindingsStore


class TestLocation(unittest.TestCase):
    """Tests for Location dataclass."""

    def test_location_basic(self):
        """Test basic location creation."""
        loc = Location(file="Vault.sol", line=42)
        self.assertEqual(loc.file, "Vault.sol")
        self.assertEqual(loc.line, 42)
        self.assertEqual(loc.column, 0)
        self.assertIsNone(loc.function)
        self.assertIsNone(loc.contract)

    def test_location_full(self):
        """Test location with all fields."""
        loc = Location(
            file="src/Vault.sol",
            line=42,
            column=8,
            end_line=50,
            end_column=4,
            function="withdraw",
            contract="Vault",
        )
        self.assertEqual(loc.file, "src/Vault.sol")
        self.assertEqual(loc.function, "withdraw")
        self.assertEqual(loc.contract, "Vault")

    def test_location_to_dict(self):
        """Test location serialization."""
        loc = Location(
            file="Vault.sol", line=42, function="withdraw", contract="Vault"
        )
        d = loc.to_dict()
        self.assertEqual(d["file"], "Vault.sol")
        self.assertEqual(d["line"], 42)
        self.assertEqual(d["function"], "withdraw")

    def test_location_from_dict(self):
        """Test location deserialization."""
        data = {
            "file": "Vault.sol",
            "line": 42,
            "column": 8,
            "function": "withdraw",
        }
        loc = Location.from_dict(data)
        self.assertEqual(loc.file, "Vault.sol")
        self.assertEqual(loc.line, 42)
        self.assertEqual(loc.function, "withdraw")

    def test_location_str(self):
        """Test location string formatting (Task 3.11: always file:line:column)."""
        # Always includes column for IDE compatibility
        loc = Location(file="Vault.sol", line=42)
        self.assertEqual(str(loc), "Vault.sol:42:0")

        loc_with_col = Location(file="Vault.sol", line=42, column=8)
        self.assertEqual(str(loc_with_col), "Vault.sol:42:8")

    def test_location_format_range(self):
        """Test location range formatting (Task 3.11)."""
        loc = Location(
            file="Vault.sol", line=42, column=8,
            end_line=50, end_column=4
        )
        self.assertEqual(loc.format_range(), "Vault.sol:42:8-50:4")

        # Without end_column, defaults to 0
        loc2 = Location(file="Vault.sol", line=42, column=8, end_line=50)
        self.assertEqual(loc2.format_range(), "Vault.sol:42:8-50:0")

        # Without end_line, just returns base
        loc3 = Location(file="Vault.sol", line=42, column=8)
        self.assertEqual(loc3.format_range(), "Vault.sol:42:8")

    def test_location_format_compact(self):
        """Test compact location formatting (Task 3.11)."""
        loc = Location(file="Vault.sol", line=42, column=8)
        self.assertEqual(loc.format_compact(), "Vault.sol:42")

    def test_location_is_valid(self):
        """Test location validation (Task 3.11)."""
        # Valid locations
        self.assertTrue(Location(file="Vault.sol", line=42).is_valid())
        self.assertTrue(Location(file="Vault.sol", line=1).is_valid())

        # Invalid locations
        self.assertFalse(Location(file="", line=42).is_valid())
        self.assertFalse(Location(file="Vault.sol", line=0).is_valid())
        self.assertFalse(Location(file="Vault.sol", line=-1).is_valid())


class TestEvidence(unittest.TestCase):
    """Tests for Evidence dataclass."""

    def test_evidence_default(self):
        """Test evidence with default values."""
        ev = Evidence()
        self.assertEqual(ev.behavioral_signature, "")
        self.assertEqual(ev.properties_matched, [])
        self.assertEqual(ev.code_snippet, "")

    def test_evidence_full(self):
        """Test evidence with all fields."""
        ev = Evidence(
            behavioral_signature="R:bal→X:out→W:bal",
            properties_matched=["state_write_after_external_call"],
            properties_missing=["has_reentrancy_guard"],
            code_snippet="function withdraw() { ... }",
            operations=["READS_USER_BALANCE", "CALLS_EXTERNAL", "WRITES_USER_BALANCE"],
            explanation="State is modified after external call",
        )
        self.assertEqual(ev.behavioral_signature, "R:bal→X:out→W:bal")
        self.assertIn("state_write_after_external_call", ev.properties_matched)

    def test_evidence_round_trip(self):
        """Test evidence serialization round trip."""
        ev = Evidence(
            behavioral_signature="W:owner",
            properties_matched=["writes_privileged_state"],
        )
        d = ev.to_dict()
        ev2 = Evidence.from_dict(d)
        self.assertEqual(ev.behavioral_signature, ev2.behavioral_signature)
        self.assertEqual(ev.properties_matched, ev2.properties_matched)


class TestEvidenceRef(unittest.TestCase):
    """Tests for EvidenceRef dataclass (Task 3.14)."""

    def test_evidence_ref_basic(self):
        """Test basic EvidenceRef creation."""
        ref = EvidenceRef(
            type="code",
            ref="Vault.sol:45-52",
            value="function withdraw() { ... }",
            context="External call before state update"
        )
        self.assertEqual(ref.type, "code")
        self.assertEqual(ref.ref, "Vault.sol:45-52")

    def test_evidence_ref_to_dict(self):
        """Test EvidenceRef serialization."""
        ref = EvidenceRef(type="property", ref="state_write_after_external_call", value=True)
        d = ref.to_dict()
        self.assertEqual(d["type"], "property")
        self.assertEqual(d["value"], True)

    def test_evidence_ref_round_trip(self):
        """Test EvidenceRef round trip."""
        ref = EvidenceRef(
            type="operation",
            ref="TRANSFERS_VALUE_OUT",
            context="Line 47"
        )
        d = ref.to_dict()
        ref2 = EvidenceRef.from_dict(d)
        self.assertEqual(ref.type, ref2.type)
        self.assertEqual(ref.ref, ref2.ref)
        self.assertEqual(ref.context, ref2.context)


class TestEvidenceFirstOutput(unittest.TestCase):
    """Tests for Evidence-First Output (Task 3.14)."""

    def test_evidence_with_why_vulnerable(self):
        """Test evidence with why_vulnerable field."""
        ev = Evidence(
            behavioral_signature="R:bal→X:out→W:bal",
            why_vulnerable="External call transfers ETH before balance update, allowing reentrancy"
        )
        self.assertEqual(ev.why_vulnerable, "External call transfers ETH before balance update, allowing reentrancy")
        d = ev.to_dict()
        self.assertIn("why_vulnerable", d)

    def test_evidence_with_attack_scenario(self):
        """Test evidence with attack scenario."""
        ev = Evidence(
            behavioral_signature="R:bal→X:out→W:bal",
            attack_scenario=[
                "1. Attacker deposits funds",
                "2. Attacker calls withdraw()",
                "3. In receive(), attacker re-enters withdraw()",
                "4. Balance not yet decremented, full amount withdrawn again"
            ]
        )
        self.assertEqual(len(ev.attack_scenario), 4)
        d = ev.to_dict()
        self.assertEqual(len(d["attack_scenario"]), 4)

    def test_evidence_with_evidence_refs(self):
        """Test evidence with detailed refs."""
        ev = Evidence(
            evidence_refs=[
                EvidenceRef(type="code", ref="Vault.sol:45-52", value="payable(msg.sender).transfer(amount);"),
                EvidenceRef(type="property", ref="state_write_after_external_call", value=True),
            ]
        )
        self.assertEqual(len(ev.evidence_refs), 2)
        d = ev.to_dict()
        self.assertEqual(len(d["evidence_refs"]), 2)
        self.assertEqual(d["evidence_refs"][0]["type"], "code")

    def test_evidence_with_data_flow(self):
        """Test evidence with data flow path."""
        ev = Evidence(
            data_flow=[
                "msg.sender → withdrawAmount (user input)",
                "withdrawAmount → balances[msg.sender] (state read)",
                "withdrawAmount → transfer() (external call)",
            ]
        )
        self.assertEqual(len(ev.data_flow), 3)

    def test_evidence_with_guard_analysis(self):
        """Test evidence with guard analysis."""
        ev = Evidence(
            guard_analysis="No reentrancy guard (nonReentrant modifier) found. "
                          "No mutex pattern detected."
        )
        self.assertIn("nonReentrant", ev.guard_analysis)

    def test_evidence_has_behavioral_evidence(self):
        """Test has_behavioral_evidence check."""
        # With signature
        ev1 = Evidence(behavioral_signature="R:bal→X:out→W:bal")
        self.assertTrue(ev1.has_behavioral_evidence())

        # With operations
        ev2 = Evidence(operations=["READS_USER_BALANCE", "CALLS_EXTERNAL"])
        self.assertTrue(ev2.has_behavioral_evidence())

        # Without either
        ev3 = Evidence(code_snippet="some code")
        self.assertFalse(ev3.has_behavioral_evidence())

    def test_evidence_has_attack_context(self):
        """Test has_attack_context check."""
        # With why_vulnerable
        ev1 = Evidence(why_vulnerable="External call before state update")
        self.assertTrue(ev1.has_attack_context())

        # With attack_scenario
        ev2 = Evidence(attack_scenario=["Step 1", "Step 2"])
        self.assertTrue(ev2.has_attack_context())

        # Without either
        ev3 = Evidence(behavioral_signature="R:bal")
        self.assertFalse(ev3.has_attack_context())

    def test_evidence_is_complete(self):
        """Test is_complete check for Task 3.14 compliance."""
        # Complete evidence
        ev_complete = Evidence(
            behavioral_signature="R:bal→X:out→W:bal",
            why_vulnerable="State modified after external call",
            code_snippet="function withdraw() { ... }"
        )
        self.assertTrue(ev_complete.is_complete())

        # Missing behavioral
        ev_no_behavior = Evidence(
            why_vulnerable="Some reason",
            code_snippet="code"
        )
        self.assertFalse(ev_no_behavior.is_complete())

        # Missing attack context
        ev_no_attack = Evidence(
            behavioral_signature="R:bal",
            code_snippet="code"
        )
        self.assertFalse(ev_no_attack.is_complete())

        # Missing code
        ev_no_code = Evidence(
            behavioral_signature="R:bal",
            why_vulnerable="Some reason"
        )
        self.assertFalse(ev_no_code.is_complete())

        # Complete with evidence_refs instead of code_snippet
        ev_with_refs = Evidence(
            behavioral_signature="R:bal",
            why_vulnerable="Some reason",
            evidence_refs=[EvidenceRef(type="code", ref="Vault.sol:45")]
        )
        self.assertTrue(ev_with_refs.is_complete())

    def test_evidence_format_summary(self):
        """Test evidence summary formatting."""
        ev = Evidence(
            behavioral_signature="R:bal→X:out→W:bal",
            why_vulnerable="Reentrancy vulnerability",
            properties_matched=["state_write_after_external_call", "has_external_call"]
        )
        summary = ev.format_summary()
        self.assertIn("R:bal→X:out→W:bal", summary)
        self.assertIn("Reentrancy", summary)

    def test_evidence_round_trip_with_all_fields(self):
        """Test full evidence round trip with Task 3.14 fields."""
        ev = Evidence(
            behavioral_signature="R:bal→X:out→W:bal",
            properties_matched=["state_write_after_external_call"],
            code_snippet="function withdraw() { ... }",
            operations=["READS_USER_BALANCE", "CALLS_EXTERNAL", "WRITES_USER_BALANCE"],
            why_vulnerable="External call before state update",
            attack_scenario=["Deposit", "Withdraw", "Re-enter", "Profit"],
            evidence_refs=[
                EvidenceRef(type="code", ref="Vault.sol:45", value="transfer()")
            ],
            data_flow=["input → state → external"],
            guard_analysis="No guards found"
        )
        d = ev.to_dict()
        ev2 = Evidence.from_dict(d)

        self.assertEqual(ev.behavioral_signature, ev2.behavioral_signature)
        self.assertEqual(ev.why_vulnerable, ev2.why_vulnerable)
        self.assertEqual(ev.attack_scenario, ev2.attack_scenario)
        self.assertEqual(len(ev.evidence_refs), len(ev2.evidence_refs))
        self.assertEqual(ev.data_flow, ev2.data_flow)
        self.assertEqual(ev.guard_analysis, ev2.guard_analysis)


class TestFindingStatus(unittest.TestCase):
    """Tests for FindingStatus enum."""

    def test_status_values(self):
        """Test all status values exist."""
        self.assertEqual(FindingStatus.PENDING.value, "pending")
        self.assertEqual(FindingStatus.INVESTIGATING.value, "investigating")
        self.assertEqual(FindingStatus.CONFIRMED.value, "confirmed")
        self.assertEqual(FindingStatus.FALSE_POSITIVE.value, "false_positive")
        self.assertEqual(FindingStatus.ESCALATED.value, "escalated")
        self.assertEqual(FindingStatus.FIXED.value, "fixed")

    def test_status_from_string(self):
        """Test status creation from string."""
        status = FindingStatus("pending")
        self.assertEqual(status, FindingStatus.PENDING)


class TestFindingSeverity(unittest.TestCase):
    """Tests for FindingSeverity enum."""

    def test_severity_values(self):
        """Test all severity values exist."""
        self.assertEqual(FindingSeverity.CRITICAL.value, "critical")
        self.assertEqual(FindingSeverity.HIGH.value, "high")
        self.assertEqual(FindingSeverity.MEDIUM.value, "medium")
        self.assertEqual(FindingSeverity.LOW.value, "low")
        self.assertEqual(FindingSeverity.INFO.value, "info")


class TestFindingTier(unittest.TestCase):
    """Tests for FindingTier enum."""

    def test_tier_values(self):
        """Test tier values exist."""
        self.assertEqual(FindingTier.TIER_A.value, "tier_a")
        self.assertEqual(FindingTier.TIER_B.value, "tier_b")

    def test_tier_from_string(self):
        """Test tier creation from string."""
        tier_a = FindingTier("tier_a")
        tier_b = FindingTier("tier_b")
        self.assertEqual(tier_a, FindingTier.TIER_A)
        self.assertEqual(tier_b, FindingTier.TIER_B)


class TestSchemaVersion(unittest.TestCase):
    """Tests for schema versioning (Task 3.9)."""

    def test_schema_version_exists(self):
        """Test schema version constant exists."""
        self.assertIsNotNone(FINDING_SCHEMA_VERSION)
        self.assertTrue(FINDING_SCHEMA_VERSION.count(".") == 2)  # Semver format

    def test_schema_version_in_output(self):
        """Test schema version appears in finding output."""
        finding = Finding(
            pattern="test-001",
            severity=FindingSeverity.HIGH,
            confidence=FindingConfidence.HIGH,
            location=Location(file="Test.sol", line=42),
            description="Test finding",
        )
        d = finding.to_dict()
        self.assertIn("schema_version", d)
        self.assertEqual(d["schema_version"], FINDING_SCHEMA_VERSION)


class TestFinding(unittest.TestCase):
    """Tests for Finding dataclass."""

    def test_finding_minimal(self):
        """Test finding with minimal required fields."""
        finding = Finding(
            pattern="auth-001",
            severity=FindingSeverity.HIGH,
            confidence=FindingConfidence.HIGH,
            location=Location(file="Vault.sol", line=42),
            description="Missing access control",
        )
        self.assertEqual(finding.pattern, "auth-001")
        self.assertEqual(finding.severity, FindingSeverity.HIGH)
        self.assertTrue(finding.id.startswith("VKG-"))
        self.assertEqual(finding.status, FindingStatus.PENDING)
        # Default tier is TIER_A (deterministic)
        self.assertEqual(finding.tier, FindingTier.TIER_A)

    def test_finding_tier_label(self):
        """Test finding with explicit tier label (Task 3.10)."""
        finding_a = Finding(
            pattern="auth-001",
            severity=FindingSeverity.HIGH,
            confidence=FindingConfidence.HIGH,
            location=Location(file="Test.sol", line=42),
            description="Tier A finding",
            tier=FindingTier.TIER_A,
        )
        finding_b = Finding(
            pattern="logic-001",
            severity=FindingSeverity.MEDIUM,
            confidence=FindingConfidence.MEDIUM,
            location=Location(file="Test.sol", line=100),
            description="Tier B finding",
            tier=FindingTier.TIER_B,
        )

        self.assertEqual(finding_a.tier, FindingTier.TIER_A)
        self.assertEqual(finding_b.tier, FindingTier.TIER_B)

        # Verify tier appears in output
        d_a = finding_a.to_dict()
        d_b = finding_b.to_dict()
        self.assertEqual(d_a["tier"], "tier_a")
        self.assertEqual(d_b["tier"], "tier_b")

    def test_finding_id_generation(self):
        """Test unique ID generation."""
        finding1 = Finding(
            pattern="auth-001",
            severity=FindingSeverity.HIGH,
            confidence=FindingConfidence.HIGH,
            location=Location(file="Vault.sol", line=42),
            description="Missing access control",
        )
        finding2 = Finding(
            pattern="auth-001",
            severity=FindingSeverity.HIGH,
            confidence=FindingConfidence.HIGH,
            location=Location(file="Token.sol", line=100),
            description="Different location",
        )
        # Same pattern but different location = different IDs
        self.assertNotEqual(finding1.id, finding2.id)

    def test_finding_id_deterministic(self):
        """Test that same inputs produce same ID."""
        f1 = Finding(
            id="",  # Force regeneration
            pattern="auth-001",
            severity=FindingSeverity.HIGH,
            confidence=FindingConfidence.HIGH,
            location=Location(file="Vault.sol", line=42),
            description="Missing access control",
        )
        f2 = Finding(
            id="",
            pattern="auth-001",
            severity=FindingSeverity.HIGH,
            confidence=FindingConfidence.HIGH,
            location=Location(file="Vault.sol", line=42),
            description="Missing access control",
        )
        self.assertEqual(f1.id, f2.id)

    def test_finding_title_generation(self):
        """Test automatic title generation."""
        finding = Finding(
            pattern="auth-001",
            severity=FindingSeverity.HIGH,
            confidence=FindingConfidence.HIGH,
            location=Location(file="Vault.sol", line=42, function="withdraw"),
            description="Missing access control",
        )
        self.assertIn("Auth 001", finding.title)
        self.assertIn("withdraw", finding.title)

    def test_finding_update_status(self):
        """Test status update functionality."""
        finding = Finding(
            pattern="auth-001",
            severity=FindingSeverity.HIGH,
            confidence=FindingConfidence.HIGH,
            location=Location(file="Vault.sol", line=42),
            description="Missing access control",
        )
        original_updated = finding.updated_at

        finding.update_status(
            FindingStatus.CONFIRMED,
            reason="Verified exploitable",
            notes="Can drain all funds",
        )

        self.assertEqual(finding.status, FindingStatus.CONFIRMED)
        self.assertEqual(finding.status_reason, "Verified exploitable")
        self.assertEqual(finding.investigator_notes, "Can drain all funds")
        self.assertNotEqual(finding.updated_at, original_updated)

    def test_finding_priority_score_critical(self):
        """Test priority score for critical findings."""
        finding = Finding(
            pattern="reentrancy-001",
            severity=FindingSeverity.CRITICAL,
            confidence=FindingConfidence.HIGH,
            location=Location(file="Vault.sol", line=42),
            description="Reentrancy vulnerability",
        )
        # Critical (100) * High confidence (1.0) = 100
        self.assertEqual(finding.priority_score, 100)

    def test_finding_priority_score_medium(self):
        """Test priority score for medium findings."""
        finding = Finding(
            pattern="info-001",
            severity=FindingSeverity.MEDIUM,
            confidence=FindingConfidence.MEDIUM,
            location=Location(file="Vault.sol", line=42),
            description="Some issue",
        )
        # Medium (50) * Medium confidence (0.7) = 35
        self.assertEqual(finding.priority_score, 35)

    def test_finding_priority_score_escalated(self):
        """Test priority boost for escalated findings."""
        finding = Finding(
            pattern="auth-001",
            severity=FindingSeverity.HIGH,
            confidence=FindingConfidence.HIGH,
            location=Location(file="Vault.sol", line=42),
            description="Access control issue",
            status=FindingStatus.ESCALATED,
        )
        # High (80) * High (1.0) + Escalated boost (50) = 130
        self.assertEqual(finding.priority_score, 130)

    def test_finding_to_dict(self):
        """Test finding serialization."""
        finding = Finding(
            pattern="auth-001",
            severity=FindingSeverity.HIGH,
            confidence=FindingConfidence.HIGH,
            location=Location(file="Vault.sol", line=42, function="withdraw"),
            description="Missing access control",
            evidence=Evidence(behavioral_signature="W:owner"),
            verification_steps=["Check ownership", "Verify exploit"],
            recommended_fix="Add onlyOwner modifier",
            cwe="CWE-284",
        )
        d = finding.to_dict()
        self.assertEqual(d["pattern"], "auth-001")
        self.assertEqual(d["severity"], "high")
        self.assertEqual(d["location"]["file"], "Vault.sol")
        self.assertEqual(d["evidence"]["behavioral_signature"], "W:owner")
        self.assertEqual(d["cwe"], "CWE-284")

    def test_finding_from_dict(self):
        """Test finding deserialization."""
        data = {
            "id": "VKG-TEST123",
            "pattern": "auth-001",
            "severity": "high",
            "confidence": "high",
            "location": {"file": "Vault.sol", "line": 42},
            "description": "Missing access control",
            "status": "confirmed",
        }
        finding = Finding.from_dict(data)
        self.assertEqual(finding.id, "VKG-TEST123")
        self.assertEqual(finding.pattern, "auth-001")
        self.assertEqual(finding.status, FindingStatus.CONFIRMED)

    def test_finding_round_trip(self):
        """Test full serialization round trip."""
        finding = Finding(
            pattern="auth-001",
            severity=FindingSeverity.HIGH,
            confidence=FindingConfidence.HIGH,
            location=Location(file="Vault.sol", line=42, function="withdraw"),
            description="Missing access control",
            evidence=Evidence(
                behavioral_signature="W:owner",
                properties_matched=["writes_privileged_state"],
            ),
            verification_steps=["Step 1", "Step 2"],
            cwe="CWE-284",
            swc="SWC-105",
        )
        d = finding.to_dict()
        finding2 = Finding.from_dict(d)
        self.assertEqual(finding.id, finding2.id)
        self.assertEqual(finding.pattern, finding2.pattern)
        self.assertEqual(finding.evidence.behavioral_signature, finding2.evidence.behavioral_signature)

    def test_finding_format_summary(self):
        """Test summary formatting."""
        finding = Finding(
            pattern="auth-001",
            severity=FindingSeverity.HIGH,
            confidence=FindingConfidence.HIGH,
            location=Location(file="Vault.sol", line=42),
            description="Missing access control",
        )
        summary = finding.format_summary()
        self.assertIn("VKG-", summary)
        self.assertIn("HIGH", summary)

    def test_finding_format_detail(self):
        """Test detail formatting."""
        finding = Finding(
            pattern="auth-001",
            severity=FindingSeverity.HIGH,
            confidence=FindingConfidence.HIGH,
            location=Location(file="Vault.sol", line=42, function="withdraw"),
            description="Missing access control",
            evidence=Evidence(
                behavioral_signature="W:owner",
                code_snippet="function withdraw() public { owner = msg.sender; }",
            ),
            verification_steps=["Check ownership"],
            recommended_fix="Add onlyOwner modifier",
        )
        detail = finding.format_detail()
        self.assertIn("Pattern: auth-001", detail)
        self.assertIn("Severity: HIGH", detail)
        self.assertIn("Behavioral Signature: W:owner", detail)
        self.assertIn("```solidity", detail)
        self.assertIn("Verification Steps:", detail)
        self.assertIn("Recommended Fix:", detail)


class TestFindingsStore(unittest.TestCase):
    """Tests for FindingsStore class."""

    def setUp(self):
        """Create temp directory for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.vkg_dir = Path(self.temp_dir) / ".vkg"

    def tearDown(self):
        """Clean up temp directory."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _make_finding(self, pattern="auth-001", severity=FindingSeverity.HIGH, line=42):
        """Helper to create test findings."""
        return Finding(
            pattern=pattern,
            severity=severity,
            confidence=FindingConfidence.HIGH,
            location=Location(file="Vault.sol", line=line),
            description=f"Test finding for {pattern}",
        )

    def test_store_init_creates_dir(self):
        """Test store creates directory if needed."""
        store = FindingsStore(self.vkg_dir)
        store.save()
        self.assertTrue(self.vkg_dir.exists())

    def test_store_add_and_get(self):
        """Test adding and retrieving findings."""
        store = FindingsStore(self.vkg_dir)
        finding = self._make_finding()
        finding_id = store.add(finding)

        retrieved = store.get(finding_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.pattern, "auth-001")

    def test_store_get_nonexistent(self):
        """Test getting nonexistent finding returns None."""
        store = FindingsStore(self.vkg_dir)
        self.assertIsNone(store.get("VKG-NONEXISTENT"))

    def test_store_update_status(self):
        """Test updating finding status."""
        store = FindingsStore(self.vkg_dir)
        finding = self._make_finding()
        finding_id = store.add(finding)

        result = store.update(finding_id, status=FindingStatus.CONFIRMED, reason="Verified")
        self.assertTrue(result)

        updated = store.get(finding_id)
        self.assertEqual(updated.status, FindingStatus.CONFIRMED)
        self.assertEqual(updated.status_reason, "Verified")

    def test_store_update_nonexistent(self):
        """Test updating nonexistent finding returns False."""
        store = FindingsStore(self.vkg_dir)
        result = store.update("VKG-NONEXISTENT", status=FindingStatus.CONFIRMED)
        self.assertFalse(result)

    def test_store_delete(self):
        """Test deleting findings."""
        store = FindingsStore(self.vkg_dir)
        finding = self._make_finding()
        finding_id = store.add(finding)

        result = store.delete(finding_id)
        self.assertTrue(result)
        self.assertIsNone(store.get(finding_id))

    def test_store_delete_nonexistent(self):
        """Test deleting nonexistent finding returns False."""
        store = FindingsStore(self.vkg_dir)
        result = store.delete("VKG-NONEXISTENT")
        self.assertFalse(result)

    def test_store_clear(self):
        """Test clearing all findings."""
        store = FindingsStore(self.vkg_dir)
        store.add(self._make_finding(pattern="auth-001"))
        store.add(self._make_finding(pattern="auth-002", line=100))
        self.assertEqual(len(store), 2)

        store.clear()
        self.assertEqual(len(store), 0)

    def test_store_persistence(self):
        """Test findings persist across store instances."""
        # Create and save
        store1 = FindingsStore(self.vkg_dir)
        finding = self._make_finding()
        finding_id = store1.add(finding)
        store1.save()

        # Load in new instance
        store2 = FindingsStore(self.vkg_dir)
        retrieved = store2.get(finding_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.pattern, "auth-001")

    def test_store_get_next_priority(self):
        """Test get_next returns highest priority finding."""
        store = FindingsStore(self.vkg_dir)

        # Add findings with different severities
        low = self._make_finding(pattern="low-001", severity=FindingSeverity.LOW, line=1)
        critical = self._make_finding(pattern="critical-001", severity=FindingSeverity.CRITICAL, line=2)
        medium = self._make_finding(pattern="medium-001", severity=FindingSeverity.MEDIUM, line=3)

        store.add(low)
        store.add(critical)
        store.add(medium)

        next_finding = store.get_next()
        self.assertEqual(next_finding.severity, FindingSeverity.CRITICAL)

    def test_store_get_next_escalated(self):
        """Test escalated findings have higher priority."""
        store = FindingsStore(self.vkg_dir)

        high = self._make_finding(pattern="high-001", severity=FindingSeverity.HIGH, line=1)
        escalated_medium = self._make_finding(pattern="medium-001", severity=FindingSeverity.MEDIUM, line=2)
        escalated_medium.status = FindingStatus.ESCALATED

        store.add(high)
        store.add(escalated_medium)

        next_finding = store.get_next()
        # Escalated medium: 50*0.7 + 50 = 85, High: 80*1.0 = 80
        # But wait, the finding was created with HIGH confidence
        # Escalated medium with HIGH conf: 50*1.0 + 50 = 100
        # High with HIGH conf: 80*1.0 = 80
        self.assertEqual(next_finding.pattern, "medium-001")

    def test_store_get_next_skips_resolved(self):
        """Test get_next skips resolved findings."""
        store = FindingsStore(self.vkg_dir)

        confirmed = self._make_finding(pattern="confirmed-001", severity=FindingSeverity.CRITICAL, line=1)
        confirmed.status = FindingStatus.CONFIRMED
        pending = self._make_finding(pattern="pending-001", severity=FindingSeverity.LOW, line=2)

        store.add(confirmed)
        store.add(pending)

        next_finding = store.get_next()
        self.assertEqual(next_finding.pattern, "pending-001")

    def test_store_get_next_empty(self):
        """Test get_next returns None when no pending findings."""
        store = FindingsStore(self.vkg_dir)
        self.assertIsNone(store.get_next())

        # Add confirmed finding
        confirmed = self._make_finding()
        confirmed.status = FindingStatus.CONFIRMED
        store.add(confirmed)
        self.assertIsNone(store.get_next())

    def test_store_list_all(self):
        """Test listing all findings."""
        store = FindingsStore(self.vkg_dir)
        store.add(self._make_finding(pattern="auth-001", line=1))
        store.add(self._make_finding(pattern="auth-002", line=2))
        store.add(self._make_finding(pattern="auth-003", line=3))

        findings = store.list()
        self.assertEqual(len(findings), 3)

    def test_store_list_by_status(self):
        """Test listing findings filtered by status."""
        store = FindingsStore(self.vkg_dir)

        pending = self._make_finding(pattern="pending-001", line=1)
        confirmed = self._make_finding(pattern="confirmed-001", line=2)
        confirmed.status = FindingStatus.CONFIRMED

        store.add(pending)
        store.add(confirmed)

        pending_list = store.list(status=FindingStatus.PENDING)
        self.assertEqual(len(pending_list), 1)
        self.assertEqual(pending_list[0].pattern, "pending-001")

    def test_store_list_by_severity(self):
        """Test listing findings filtered by severity."""
        store = FindingsStore(self.vkg_dir)

        high = self._make_finding(pattern="high-001", severity=FindingSeverity.HIGH, line=1)
        low = self._make_finding(pattern="low-001", severity=FindingSeverity.LOW, line=2)

        store.add(high)
        store.add(low)

        high_list = store.list(severity=FindingSeverity.HIGH)
        self.assertEqual(len(high_list), 1)
        self.assertEqual(high_list[0].pattern, "high-001")

    def test_store_list_by_pattern(self):
        """Test listing findings filtered by pattern."""
        store = FindingsStore(self.vkg_dir)

        store.add(self._make_finding(pattern="auth-001", line=1))
        store.add(self._make_finding(pattern="auth-001", line=2))
        store.add(self._make_finding(pattern="reentrancy-001", line=3))

        auth_list = store.list(pattern="auth-001")
        self.assertEqual(len(auth_list), 2)

    def test_store_list_limit(self):
        """Test listing with limit."""
        store = FindingsStore(self.vkg_dir)
        for i in range(10):
            store.add(self._make_finding(pattern=f"auth-{i:03d}", line=i))

        limited = store.list(limit=5)
        self.assertEqual(len(limited), 5)

    def test_store_count(self):
        """Test counting findings."""
        store = FindingsStore(self.vkg_dir)
        store.add(self._make_finding(pattern="auth-001", line=1))
        store.add(self._make_finding(pattern="auth-002", line=2))

        self.assertEqual(store.count(), 2)

    def test_store_count_by_status(self):
        """Test counting findings by status."""
        store = FindingsStore(self.vkg_dir)

        pending = self._make_finding(pattern="pending-001", line=1)
        confirmed = self._make_finding(pattern="confirmed-001", line=2)
        confirmed.status = FindingStatus.CONFIRMED

        store.add(pending)
        store.add(confirmed)

        self.assertEqual(store.count(FindingStatus.PENDING), 1)
        self.assertEqual(store.count(FindingStatus.CONFIRMED), 1)

    def test_store_stats(self):
        """Test getting statistics."""
        store = FindingsStore(self.vkg_dir)

        store.add(self._make_finding(pattern="high-001", severity=FindingSeverity.HIGH, line=1))
        store.add(self._make_finding(pattern="high-002", severity=FindingSeverity.HIGH, line=2))
        store.add(self._make_finding(pattern="low-001", severity=FindingSeverity.LOW, line=3))

        stats = store.stats()
        self.assertEqual(stats["total"], 3)
        self.assertEqual(stats["by_severity"]["high"], 2)
        self.assertEqual(stats["by_severity"]["low"], 1)
        self.assertEqual(stats["by_status"]["pending"], 3)

    def test_store_len(self):
        """Test __len__ method."""
        store = FindingsStore(self.vkg_dir)
        self.assertEqual(len(store), 0)

        store.add(self._make_finding())
        self.assertEqual(len(store), 1)

    def test_store_iter(self):
        """Test __iter__ method."""
        store = FindingsStore(self.vkg_dir)
        store.add(self._make_finding(pattern="auth-001", line=1))
        store.add(self._make_finding(pattern="auth-002", line=2))

        patterns = [f.pattern for f in store]
        self.assertEqual(len(patterns), 2)
        self.assertIn("auth-001", patterns)
        self.assertIn("auth-002", patterns)

    def test_store_contains(self):
        """Test __contains__ method."""
        store = FindingsStore(self.vkg_dir)
        finding = self._make_finding()
        finding_id = store.add(finding)

        self.assertIn(finding_id, store)
        self.assertNotIn("VKG-NONEXISTENT", store)

    def test_store_to_json(self):
        """Test JSON export."""
        store = FindingsStore(self.vkg_dir)
        store.add(self._make_finding())

        json_str = store.to_json()
        data = json.loads(json_str)

        self.assertEqual(data["version"], "1.0.0")
        self.assertEqual(data["count"], 1)
        self.assertEqual(len(data["findings"]), 1)

    def test_store_corrupted_file(self):
        """Test store handles corrupted file gracefully."""
        self.vkg_dir.mkdir(parents=True)
        findings_file = self.vkg_dir / "findings.json"
        findings_file.write_text("not valid json {{{")

        store = FindingsStore(self.vkg_dir)
        self.assertEqual(len(store), 0)

    def test_store_from_analysis(self):
        """Test creating store from analysis results."""
        pattern_matches = [
            {
                "pattern_id": "auth-001",
                "severity": "high",
                "confidence": "high",
                "file": "Vault.sol",
                "line": 42,
                "function": "withdraw",
                "contract": "Vault",
                "description": "Missing access control",
                "behavioral_signature": "W:owner",
                "properties_matched": ["writes_privileged_state"],
            }
        ]

        store = FindingsStore.from_analysis(self.vkg_dir, pattern_matches)
        self.assertEqual(len(store), 1)

        finding = list(store)[0]
        self.assertEqual(finding.pattern, "auth-001")
        self.assertEqual(finding.severity, FindingSeverity.HIGH)
        self.assertEqual(finding.location.function, "withdraw")


if __name__ == "__main__":
    unittest.main()
