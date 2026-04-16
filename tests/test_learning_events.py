"""Tests for learning events module.

Task 7.3: Learning event schema and storage.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from alphaswarm_sol.learning.events import (
    EventContext,
    EnrichedEvent,
    EventStore,
    generate_event_id,
    default_adjustment,
    create_event_from_finding,
)
from alphaswarm_sol.learning.types import (
    EventType,
    LearningEvent,
    SimilarityKey,
    SimilarityTier,
)


class TestEventContext(unittest.TestCase):
    """Test EventContext dataclass."""

    def test_create_basic(self):
        """Create basic context."""
        ctx = EventContext(
            function_signature="withdraw(uint256)",
            function_name="withdraw",
            contract_name="Vault",
            modifiers=["nonReentrant"],
            code_snippet="function withdraw() { ... }",
        )
        self.assertEqual(ctx.function_signature, "withdraw(uint256)")
        self.assertEqual(ctx.function_name, "withdraw")
        self.assertEqual(ctx.contract_name, "Vault")
        self.assertEqual(ctx.modifiers, ["nonReentrant"])
        self.assertNotEqual(ctx.context_hash, "")

    def test_context_hash_generated(self):
        """Context hash is auto-generated."""
        ctx = EventContext(
            function_signature="transfer(address,uint256)",
            function_name="transfer",
            contract_name="Token",
            modifiers=[],
            code_snippet="function transfer() { ... }",
        )
        self.assertTrue(len(ctx.context_hash) == 16)

    def test_context_hash_deterministic(self):
        """Same input produces same hash."""
        ctx1 = EventContext(
            function_signature="foo()",
            function_name="foo",
            contract_name="Test",
            modifiers=[],
            code_snippet="code",
        )
        ctx2 = EventContext(
            function_signature="foo()",
            function_name="foo",
            contract_name="Test",
            modifiers=[],
            code_snippet="code",
        )
        self.assertEqual(ctx1.context_hash, ctx2.context_hash)

    def test_different_code_different_hash(self):
        """Different code produces different hash."""
        ctx1 = EventContext(
            function_signature="foo()",
            function_name="foo",
            contract_name="Test",
            modifiers=[],
            code_snippet="code1",
        )
        ctx2 = EventContext(
            function_signature="foo()",
            function_name="foo",
            contract_name="Test",
            modifiers=[],
            code_snippet="code2",
        )
        self.assertNotEqual(ctx1.context_hash, ctx2.context_hash)

    def test_to_dict(self):
        """Convert to dict."""
        ctx = EventContext(
            function_signature="withdraw(uint256)",
            function_name="withdraw",
            contract_name="Vault",
            modifiers=["onlyOwner"],
            code_snippet="code",
            file_path="contracts/Vault.sol",
        )
        d = ctx.to_dict()
        self.assertEqual(d["function_signature"], "withdraw(uint256)")
        self.assertEqual(d["modifiers"], ["onlyOwner"])
        self.assertEqual(d["file_path"], "contracts/Vault.sol")

    def test_from_dict(self):
        """Create from dict."""
        data = {
            "function_signature": "test()",
            "function_name": "test",
            "contract_name": "Test",
            "modifiers": ["mod1", "mod2"],
            "code_snippet": "code here",
            "context_hash": "abc123",
            "file_path": "test.sol",
        }
        ctx = EventContext.from_dict(data)
        self.assertEqual(ctx.function_signature, "test()")
        self.assertEqual(ctx.modifiers, ["mod1", "mod2"])
        self.assertEqual(ctx.context_hash, "abc123")

    def test_round_trip(self):
        """Dict round-trip preserves data."""
        ctx = EventContext(
            function_signature="complex(address,uint256,bytes)",
            function_name="complex",
            contract_name="Complex",
            modifiers=["guard1", "guard2"],
            code_snippet="long code snippet here",
            file_path="src/Complex.sol",
        )
        restored = EventContext.from_dict(ctx.to_dict())
        self.assertEqual(restored.function_signature, ctx.function_signature)
        self.assertEqual(restored.modifiers, ctx.modifiers)
        self.assertEqual(restored.context_hash, ctx.context_hash)


class TestEnrichedEvent(unittest.TestCase):
    """Test EnrichedEvent dataclass."""

    def setUp(self):
        """Set up test data."""
        self.event = LearningEvent(
            id="evt-test-001",
            pattern_id="vm-001",
            event_type=EventType.CONFIRMED,
            timestamp=datetime.now(),
            similarity_key=SimilarityKey(
                pattern_id="vm-001",
                modifier_signature="nonReentrant",
                guard_hash="abc123",
            ),
            finding_id="VKG-001",
            verdict_source="llm",
            confidence_before=0.7,
            confidence_after=0.72,
        )
        self.context = EventContext(
            function_signature="withdraw(uint256)",
            function_name="withdraw",
            contract_name="Vault",
            modifiers=["nonReentrant"],
            code_snippet="function withdraw() { ... }",
        )

    def test_create_enriched(self):
        """Create enriched event."""
        enriched = EnrichedEvent(
            event=self.event,
            context=self.context,
            reason="Verified via PoC",
            adjustment=0.02,
        )
        self.assertEqual(enriched.event.pattern_id, "vm-001")
        self.assertEqual(enriched.reason, "Verified via PoC")
        self.assertEqual(enriched.adjustment, 0.02)

    def test_with_optional_fields(self):
        """Create with optional fields."""
        enriched = EnrichedEvent(
            event=self.event,
            context=self.context,
            reason="Human verified",
            auditor_id="auditor@example.com",
            bead_id="bead-123",
            adjustment=-0.05,
        )
        self.assertEqual(enriched.auditor_id, "auditor@example.com")
        self.assertEqual(enriched.bead_id, "bead-123")

    def test_to_dict(self):
        """Convert to dict."""
        enriched = EnrichedEvent(
            event=self.event,
            context=self.context,
            reason="Test reason",
            adjustment=0.02,
        )
        d = enriched.to_dict()
        self.assertIn("event", d)
        self.assertIn("context", d)
        self.assertEqual(d["reason"], "Test reason")
        self.assertEqual(d["adjustment"], 0.02)

    def test_from_dict(self):
        """Create from dict."""
        enriched = EnrichedEvent(
            event=self.event,
            context=self.context,
            reason="Original",
            auditor_id="test",
            adjustment=0.01,
        )
        restored = EnrichedEvent.from_dict(enriched.to_dict())
        self.assertEqual(restored.event.id, self.event.id)
        self.assertEqual(restored.reason, "Original")
        self.assertEqual(restored.auditor_id, "test")

    def test_round_trip(self):
        """Dict round-trip preserves all data."""
        enriched = EnrichedEvent(
            event=self.event,
            context=self.context,
            reason="Complete test",
            auditor_id="auditor",
            bead_id="bead-xyz",
            adjustment=-0.03,
        )
        d = enriched.to_dict()
        restored = EnrichedEvent.from_dict(d)
        self.assertEqual(restored.event.pattern_id, enriched.event.pattern_id)
        self.assertEqual(restored.context.function_name, enriched.context.function_name)
        self.assertEqual(restored.auditor_id, enriched.auditor_id)
        self.assertEqual(restored.bead_id, enriched.bead_id)
        self.assertEqual(restored.adjustment, enriched.adjustment)


class TestHelperFunctions(unittest.TestCase):
    """Test helper functions."""

    def test_generate_event_id_format(self):
        """Event ID has correct format."""
        event_id = generate_event_id("vm-001-classic")
        self.assertTrue(event_id.startswith("evt-vm-001-c"))
        # Format: evt-{pattern[:8]}-{timestamp}-{random}
        # With pattern "vm-001-classic" -> "vm-001-c", so:
        # evt-vm-001-c-20260108...-abc123
        self.assertTrue(event_id.startswith("evt-"))
        self.assertIn("vm-001-c", event_id)

    def test_generate_event_id_unique(self):
        """Event IDs are unique."""
        ids = [generate_event_id("pattern-123") for _ in range(100)]
        self.assertEqual(len(set(ids)), 100)

    def test_generate_event_id_handles_short_pattern(self):
        """Handle short pattern IDs."""
        event_id = generate_event_id("abc")
        self.assertTrue(event_id.startswith("evt-abc-"))

    def test_default_adjustment_confirmed(self):
        """Confirmed events get positive adjustment."""
        adj = default_adjustment(EventType.CONFIRMED)
        self.assertEqual(adj, 0.02)

    def test_default_adjustment_rejected(self):
        """Rejected events get negative adjustment."""
        adj = default_adjustment(EventType.REJECTED)
        self.assertEqual(adj, -0.05)

    def test_default_adjustment_escalated(self):
        """Escalated events get zero adjustment."""
        adj = default_adjustment(EventType.ESCALATED)
        self.assertEqual(adj, 0.0)

    def test_default_adjustment_rollback(self):
        """Rollback events get zero adjustment."""
        adj = default_adjustment(EventType.ROLLBACK)
        self.assertEqual(adj, 0.0)


class TestEventStore(unittest.TestCase):
    """Test EventStore class."""

    def setUp(self):
        """Set up test storage."""
        self.temp_dir = tempfile.mkdtemp()
        self.store = EventStore(Path(self.temp_dir))

    def tearDown(self):
        """Clean up temp directory."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_test_event(
        self,
        pattern_id: str = "vm-001",
        event_type: EventType = EventType.CONFIRMED,
    ) -> EnrichedEvent:
        """Create a test enriched event."""
        event = LearningEvent(
            id=generate_event_id(pattern_id),
            pattern_id=pattern_id,
            event_type=event_type,
            timestamp=datetime.now(),
            similarity_key=SimilarityKey(
                pattern_id=pattern_id,
                modifier_signature="",
                guard_hash="",
            ),
            finding_id=f"finding-{pattern_id}",
            verdict_source="test",
            confidence_before=0.7,
            confidence_after=0.72 if event_type == EventType.CONFIRMED else 0.65,
        )
        context = EventContext(
            function_signature="test()",
            function_name="test",
            contract_name="Test",
            modifiers=[],
            code_snippet="code",
        )
        return EnrichedEvent(
            event=event,
            context=context,
            reason="Test reason",
            adjustment=0.02 if event_type == EventType.CONFIRMED else -0.05,
        )

    def test_record_event(self):
        """Record a single event."""
        enriched = self._create_test_event()
        event_id = self.store.record(enriched)
        self.assertTrue(event_id.startswith("evt-"))

    def test_record_multiple_events(self):
        """Record multiple events."""
        for i in range(5):
            enriched = self._create_test_event(f"pattern-{i}")
            self.store.record(enriched)

        self.assertEqual(self.store.get_event_count(), 5)

    def test_get_events_for_pattern(self):
        """Get events filtered by pattern."""
        for i in range(3):
            self.store.record(self._create_test_event("vm-001"))
        for i in range(2):
            self.store.record(self._create_test_event("vm-002"))

        vm001_events = self.store.get_events_for_pattern("vm-001")
        self.assertEqual(len(vm001_events), 3)

        vm002_events = self.store.get_events_for_pattern("vm-002")
        self.assertEqual(len(vm002_events), 2)

    def test_get_events_empty_pattern(self):
        """Get events for pattern with no events."""
        events = self.store.get_events_for_pattern("nonexistent")
        self.assertEqual(len(events), 0)

    def test_get_recent_events(self):
        """Get recent events."""
        # Create events
        for i in range(3):
            self.store.record(self._create_test_event())

        recent = self.store.get_recent_events(days=30)
        self.assertEqual(len(recent), 3)

    def test_count_by_type(self):
        """Count events by type."""
        self.store.record(self._create_test_event("vm-001", EventType.CONFIRMED))
        self.store.record(self._create_test_event("vm-001", EventType.CONFIRMED))
        self.store.record(self._create_test_event("vm-001", EventType.REJECTED))

        counts = self.store.count_by_type("vm-001")
        self.assertEqual(counts["confirmed"], 2)
        self.assertEqual(counts["rejected"], 1)
        self.assertEqual(counts["escalated"], 0)

    def test_compute_effective_counts(self):
        """Compute decay-weighted counts."""
        # Add current events
        self.store.record(self._create_test_event("vm-001", EventType.CONFIRMED))
        self.store.record(self._create_test_event("vm-001", EventType.REJECTED))

        counts = self.store.compute_effective_counts("vm-001")
        self.assertGreater(counts["effective_confirmed"], 0)
        self.assertGreater(counts["effective_rejected"], 0)
        self.assertEqual(counts["total_events"], 2)

    def test_get_patterns_with_events(self):
        """Get list of patterns with events."""
        self.store.record(self._create_test_event("pattern-a"))
        self.store.record(self._create_test_event("pattern-b"))
        self.store.record(self._create_test_event("pattern-a"))

        patterns = self.store.get_patterns_with_events()
        self.assertEqual(set(patterns), {"pattern-a", "pattern-b"})

    def test_clear_pattern_events(self):
        """Clear events for a pattern."""
        self.store.record(self._create_test_event("vm-001"))
        self.store.record(self._create_test_event("vm-001"))
        self.store.record(self._create_test_event("vm-002"))

        cleared = self.store.clear_pattern_events("vm-001")
        self.assertEqual(cleared, 2)
        self.assertEqual(self.store.get_event_count(), 1)

    def test_persistence(self):
        """Events persist across store instances."""
        self.store.record(self._create_test_event("vm-001"))
        self.store.record(self._create_test_event("vm-002"))

        # Create new store pointing to same directory
        new_store = EventStore(Path(self.temp_dir))
        self.assertEqual(new_store.get_event_count(), 2)

    def test_create_and_record(self):
        """Use convenience create_and_record method."""
        similarity_key = SimilarityKey(
            pattern_id="vm-001",
            modifier_signature="nonReentrant",
            guard_hash="abc",
        )
        context = EventContext(
            function_signature="withdraw(uint256)",
            function_name="withdraw",
            contract_name="Vault",
            modifiers=["nonReentrant"],
            code_snippet="code",
        )

        event_id = self.store.create_and_record(
            event_type=EventType.CONFIRMED,
            pattern_id="vm-001",
            finding_id="VKG-001",
            similarity_key=similarity_key,
            context=context,
            reason="Verified",
            confidence_before=0.7,
            confidence_after=0.72,
            verdict_source="test",
        )

        self.assertTrue(event_id.startswith("evt-"))
        events = self.store.get_events_for_pattern("vm-001")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].reason, "Verified")


class TestSimilarityMatching(unittest.TestCase):
    """Test similarity-based event retrieval."""

    def setUp(self):
        """Set up test storage."""
        self.temp_dir = tempfile.mkdtemp()
        self.store = EventStore(Path(self.temp_dir))

    def tearDown(self):
        """Clean up."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_event_with_key(
        self,
        pattern_id: str,
        modifier_sig: str,
        guard_hash: str,
    ) -> EnrichedEvent:
        """Create event with specific similarity key."""
        event = LearningEvent(
            id=generate_event_id(pattern_id),
            pattern_id=pattern_id,
            event_type=EventType.CONFIRMED,
            timestamp=datetime.now(),
            similarity_key=SimilarityKey(
                pattern_id=pattern_id,
                modifier_signature=modifier_sig,
                guard_hash=guard_hash,
            ),
            finding_id="test-finding",
            verdict_source="test",
        )
        context = EventContext(
            function_signature="test()",
            function_name="test",
            contract_name="Test",
            modifiers=[],
            code_snippet="code",
        )
        return EnrichedEvent(event=event, context=context, reason="test")

    def test_exact_match(self):
        """Get events with exact similarity match."""
        # Add event
        enriched = self._create_event_with_key("vm-001", "nonReentrant", "hash1")
        self.store.record(enriched)

        # Query with exact match
        key = SimilarityKey(
            pattern_id="vm-001",
            modifier_signature="nonReentrant",
            guard_hash="hash1",
        )
        events = self.store.get_similar_events(key, SimilarityTier.EXACT)
        self.assertEqual(len(events), 1)

    def test_exact_match_fails_on_different_hash(self):
        """Exact match requires matching guard hash."""
        enriched = self._create_event_with_key("vm-001", "nonReentrant", "hash1")
        self.store.record(enriched)

        key = SimilarityKey(
            pattern_id="vm-001",
            modifier_signature="nonReentrant",
            guard_hash="hash2",  # Different hash
        )
        events = self.store.get_similar_events(key, SimilarityTier.EXACT)
        self.assertEqual(len(events), 0)

    def test_structural_match(self):
        """Structural match ignores guard hash."""
        enriched = self._create_event_with_key("vm-001", "nonReentrant", "hash1")
        self.store.record(enriched)

        key = SimilarityKey(
            pattern_id="vm-001",
            modifier_signature="nonReentrant",
            guard_hash="different",  # Different hash OK
        )
        events = self.store.get_similar_events(key, SimilarityTier.STRUCTURAL)
        self.assertEqual(len(events), 1)

    def test_pattern_match(self):
        """Pattern match only checks pattern_id."""
        self.store.record(self._create_event_with_key("vm-001", "mod1", "hash1"))
        self.store.record(self._create_event_with_key("vm-001", "mod2", "hash2"))
        self.store.record(self._create_event_with_key("vm-002", "mod1", "hash1"))

        key = SimilarityKey(
            pattern_id="vm-001",
            modifier_signature="different",
            guard_hash="different",
        )
        events = self.store.get_similar_events(key, SimilarityTier.PATTERN)
        self.assertEqual(len(events), 2)  # Both vm-001 events


class TestCreateEventFromFinding(unittest.TestCase):
    """Test create_event_from_finding function."""

    def test_create_from_full_finding(self):
        """Create event from complete finding dict."""
        finding = {
            "pattern_id": "vm-001",
            "finding_id": "VKG-001",
            "function_signature": "withdraw(uint256)",
            "function_name": "withdraw",
            "contract_name": "Vault",
            "modifiers": ["nonReentrant", "onlyOwner"],
            "code": "function withdraw(uint256 amount) { ... }",
            "file_path": "contracts/Vault.sol",
        }

        enriched = create_event_from_finding(
            finding=finding,
            event_type=EventType.CONFIRMED,
            reason="Verified via manual review",
            confidence_before=0.7,
            confidence_after=0.72,
        )

        self.assertEqual(enriched.event.pattern_id, "vm-001")
        self.assertEqual(enriched.event.finding_id, "VKG-001")
        self.assertEqual(enriched.context.function_name, "withdraw")
        self.assertEqual(enriched.context.contract_name, "Vault")
        self.assertEqual(enriched.reason, "Verified via manual review")
        self.assertAlmostEqual(enriched.adjustment, 0.02, places=4)

    def test_create_from_minimal_finding(self):
        """Create event from minimal finding dict."""
        finding = {
            "pattern_id": "oracle-001",
        }

        enriched = create_event_from_finding(
            finding=finding,
            event_type=EventType.REJECTED,
            reason="False positive - has staleness check",
            confidence_before=0.8,
            confidence_after=0.75,
        )

        self.assertEqual(enriched.event.pattern_id, "oracle-001")
        self.assertEqual(enriched.event.finding_id, "unknown")
        self.assertAlmostEqual(enriched.adjustment, -0.05, places=4)

    def test_create_with_custom_verdict_source(self):
        """Create event with custom verdict source."""
        finding = {"pattern_id": "dos-001", "id": "DOS-123"}

        enriched = create_event_from_finding(
            finding=finding,
            event_type=EventType.CONFIRMED,
            reason="Human verified",
            confidence_before=0.9,
            confidence_after=0.92,
            verdict_source="human",
        )

        self.assertEqual(enriched.event.verdict_source, "human")
        self.assertEqual(enriched.event.finding_id, "DOS-123")


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""

    def setUp(self):
        """Set up test storage."""
        self.temp_dir = tempfile.mkdtemp()
        self.store = EventStore(Path(self.temp_dir))

    def tearDown(self):
        """Clean up."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_empty_store(self):
        """Operations on empty store don't fail."""
        self.assertEqual(self.store.get_event_count(), 0)
        self.assertEqual(len(self.store.get_recent_events()), 0)
        self.assertEqual(len(self.store.get_patterns_with_events()), 0)

    def test_corrupted_line_handling(self):
        """Handle corrupted lines in events file."""
        # Write some valid data
        event = LearningEvent(
            id="test-1",
            pattern_id="vm-001",
            event_type=EventType.CONFIRMED,
            timestamp=datetime.now(),
            similarity_key=SimilarityKey("vm-001", "", ""),
            finding_id="f1",
        )
        ctx = EventContext(
            function_signature="test()",
            function_name="test",
            contract_name="Test",
            modifiers=[],
            code_snippet="code",
        )
        enriched = EnrichedEvent(event=event, context=ctx, reason="test")
        self.store.record(enriched)

        # Manually corrupt the file
        with open(self.store._events_file, "a") as f:
            f.write("invalid json line\n")
            f.write("{incomplete json\n")

        # Should still be able to read valid events
        events = self.store.get_events_for_pattern("vm-001")
        self.assertEqual(len(events), 1)

    def test_max_age_filter(self):
        """Test max age filter on event retrieval."""
        # Record an event
        event = LearningEvent(
            id="old-event",
            pattern_id="vm-001",
            event_type=EventType.CONFIRMED,
            timestamp=datetime.now() - timedelta(days=100),
            similarity_key=SimilarityKey("vm-001", "", ""),
            finding_id="f1",
        )
        ctx = EventContext(
            function_signature="test()",
            function_name="test",
            contract_name="Test",
            modifiers=[],
            code_snippet="code",
        )
        enriched = EnrichedEvent(event=event, context=ctx, reason="test")

        # Manually write to bypass timestamp
        with open(self.store._events_file, "a") as f:
            f.write(json.dumps(enriched.to_dict()) + "\n")

        # Query with max age filter
        events = self.store.get_events_for_pattern("vm-001", max_age_days=30)
        self.assertEqual(len(events), 0)

        # Without filter should find it
        events = self.store.get_events_for_pattern("vm-001")
        self.assertEqual(len(events), 1)


if __name__ == "__main__":
    unittest.main()
