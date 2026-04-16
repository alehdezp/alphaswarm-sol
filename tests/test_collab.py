"""
Tests for Collaborative Audit Network (Novel Solution 5)

Tests the decentralized audit knowledge sharing system including:
- Finding submission and storage
- Reputation tracking
- Consensus-based validation
- Bounty system
"""

import unittest
from datetime import datetime, timedelta

from alphaswarm_sol.collab import (
    # Findings
    AuditFinding,
    FindingStatus,
    FindingVote,
    FindingSubmission,
    FindingRegistry,
    # Reputation
    AuditorProfile,
    ReputationSystem,
    ReputationAction,
    ReputationLevel,
    # Consensus
    ConsensusResult,
    ConsensusValidator,
    ValidationRequest,
    ValidationVote,
    # Network
    CollaborativeNetwork,
    NetworkConfig,
    NetworkStatistics,
    # Bounty
    Bounty,
    BountyStatus,
    BountySubmission,
    BountyManager,
)
from alphaswarm_sol.collab.consensus import ValidationStatus, ValidatorSelector
from alphaswarm_sol.collab.bounty import RewardStructure, BountyScope


class TestAuditFinding(unittest.TestCase):
    """Test audit finding functionality."""

    def test_finding_creation(self):
        """Test creating an audit finding."""
        finding = AuditFinding(
            finding_id="",
            contract_hash="abc123",
            vulnerability_type="reentrancy",
            severity="high",
            title="Reentrancy in withdraw",
            description="State change after external call",
            auditor_id="auditor-1",
        )

        self.assertTrue(finding.finding_id.startswith("FIND-"))
        self.assertEqual(finding.severity, "high")
        self.assertEqual(finding.status, FindingStatus.PENDING)

    def test_finding_voting(self):
        """Test adding votes to a finding."""
        finding = AuditFinding(
            finding_id="FIND-TEST",
            contract_hash="abc123",
            vulnerability_type="reentrancy",
            severity="high",
            title="Test",
            description="Test desc",
            auditor_id="auditor-1",
            required_validators=3,
        )

        # Add votes
        finding.add_vote(FindingVote(
            validator_id="val-1",
            agrees=True,
            reasoning="Valid finding",
            confidence=0.9,
        ))

        self.assertEqual(finding.status, FindingStatus.VALIDATING)
        self.assertEqual(len(finding.votes), 1)

    def test_finding_consensus_reached(self):
        """Test consensus calculation."""
        finding = AuditFinding(
            finding_id="FIND-TEST",
            contract_hash="abc123",
            vulnerability_type="reentrancy",
            severity="high",
            title="Test",
            description="Test desc",
            auditor_id="auditor-1",
            required_validators=3,
        )

        # Add agreeing votes (>60%)
        for i in range(3):
            finding.add_vote(FindingVote(
                validator_id=f"val-{i}",
                agrees=True,
                reasoning="Valid",
                confidence=0.8,
            ))

        self.assertEqual(finding.status, FindingStatus.CONFIRMED)

    def test_finding_rejected(self):
        """Test finding rejection when <20% agree."""
        finding = AuditFinding(
            finding_id="FIND-TEST",
            contract_hash="abc123",
            vulnerability_type="reentrancy",
            severity="high",
            title="Test",
            description="Test desc",
            auditor_id="auditor-1",
            required_validators=5,
        )

        # Add mostly disagreeing votes
        for i in range(5):
            finding.add_vote(FindingVote(
                validator_id=f"val-{i}",
                agrees=(i == 0),  # Only first agrees
                reasoning="Test",
                confidence=0.8,
            ))

        self.assertEqual(finding.status, FindingStatus.REJECTED)

    def test_finding_signing(self):
        """Test cryptographic signing of findings."""
        finding = AuditFinding(
            finding_id="FIND-TEST",
            contract_hash="abc123",
            vulnerability_type="reentrancy",
            severity="high",
            title="Test",
            description="Test desc",
            auditor_id="auditor-1",
        )

        signature = finding.sign("private-key-123")
        self.assertIsNotNone(signature)
        self.assertEqual(len(signature), 64)  # SHA256 hex

    def test_consensus_summary(self):
        """Test consensus summary generation."""
        finding = AuditFinding(
            finding_id="FIND-TEST",
            contract_hash="abc123",
            vulnerability_type="reentrancy",
            severity="high",
            title="Test",
            description="Test",
            auditor_id="auditor-1",
            required_validators=3,
        )

        finding.add_vote(FindingVote(
            validator_id="val-1", agrees=True, reasoning="OK", confidence=0.9
        ))
        finding.add_vote(FindingVote(
            validator_id="val-2", agrees=True, reasoning="OK", confidence=0.8
        ))

        summary = finding.get_consensus_summary()
        self.assertEqual(summary["votes_for"], 2)
        self.assertEqual(summary["votes_against"], 0)
        self.assertEqual(summary["total_votes"], 2)


class TestFindingRegistry(unittest.TestCase):
    """Test finding registry functionality."""

    def setUp(self):
        self.registry = FindingRegistry()

    def test_submit_finding(self):
        """Test submitting a finding to registry."""
        finding = AuditFinding(
            finding_id="",
            contract_hash="contract-123",
            vulnerability_type="reentrancy",
            severity="high",
            title="Test Finding",
            description="Description",
            auditor_id="auditor-1",
        )

        finding_id = self.registry.submit(finding)
        self.assertIsNotNone(finding_id)
        self.assertEqual(self.registry.get(finding_id), finding)

    def test_get_by_contract(self):
        """Test getting findings by contract."""
        contract_hash = "contract-abc"

        for i in range(3):
            finding = AuditFinding(
                finding_id=f"FIND-{i}",
                contract_hash=contract_hash,
                vulnerability_type="reentrancy",
                severity="medium",
                title=f"Finding {i}",
                description="Desc",
                auditor_id="auditor-1",
            )
            self.registry.submit(finding)

        results = self.registry.get_for_contract(contract_hash)
        self.assertEqual(len(results), 3)

    def test_get_by_auditor(self):
        """Test getting findings by auditor."""
        auditor_id = "auditor-alice"

        for i in range(2):
            finding = AuditFinding(
                finding_id=f"FIND-A{i}",
                contract_hash=f"contract-{i}",
                vulnerability_type="overflow",
                severity="high",
                title=f"Finding {i}",
                description="Desc",
                auditor_id=auditor_id,
            )
            self.registry.submit(finding)

        results = self.registry.get_by_auditor(auditor_id)
        self.assertEqual(len(results), 2)

    def test_registry_statistics(self):
        """Test registry statistics."""
        # Add some findings
        finding = AuditFinding(
            finding_id="FIND-1",
            contract_hash="contract-1",
            vulnerability_type="reentrancy",
            severity="high",
            title="Test",
            description="Desc",
            auditor_id="auditor-1",
        )
        self.registry.submit(finding)

        stats = self.registry.get_statistics()
        self.assertEqual(stats["total_findings"], 1)
        self.assertEqual(stats["unique_auditors"], 1)


class TestReputationSystem(unittest.TestCase):
    """Test reputation system functionality."""

    def setUp(self):
        self.reputation = ReputationSystem()

    def test_register_auditor(self):
        """Test registering a new auditor."""
        profile = self.reputation.register_auditor("auditor-1", "Alice")

        self.assertEqual(profile.auditor_id, "auditor-1")
        self.assertEqual(profile.name, "Alice")
        self.assertEqual(profile.reputation_score, 50)
        self.assertEqual(profile.level, ReputationLevel.CONTRIBUTOR)

    def test_confirmed_finding_reputation(self):
        """Test reputation increase for confirmed finding."""
        profile = self.reputation.register_auditor("auditor-1")
        initial_score = profile.reputation_score

        self.reputation.record_finding_confirmed(
            "auditor-1",
            "FIND-123",
            is_first=True,
            is_high=True
        )

        # Should have increased
        self.assertGreater(profile.reputation_score, initial_score)
        self.assertEqual(profile.findings_confirmed, 1)
        self.assertEqual(profile.current_streak, 1)

    def test_rejected_finding_reputation(self):
        """Test reputation decrease for rejected finding."""
        profile = self.reputation.register_auditor("auditor-1")
        profile.reputation_score = 100  # Start higher

        self.reputation.record_finding_rejected("auditor-1", "FIND-123")

        self.assertLess(profile.reputation_score, 100)
        self.assertEqual(profile.findings_rejected, 1)
        self.assertEqual(profile.current_streak, 0)

    def test_validation_reputation(self):
        """Test reputation for validation participation."""
        profile = self.reputation.register_auditor("auditor-1")
        initial = profile.reputation_score

        # Correct validation
        self.reputation.record_validation("auditor-1", True, "FIND-123")
        self.assertGreater(profile.reputation_score, initial)
        self.assertEqual(profile.validations_correct, 1)

        # Wrong validation
        mid_score = profile.reputation_score
        self.reputation.record_validation("auditor-1", False, "FIND-456")
        self.assertLess(profile.reputation_score, mid_score)

    def test_level_progression(self):
        """Test reputation level progression."""
        profile = self.reputation.register_auditor("auditor-1")

        # Set to different levels
        profile.reputation_score = 30
        profile._update_level()
        self.assertEqual(profile.level, ReputationLevel.NEWCOMER)

        profile.reputation_score = 75
        profile._update_level()
        self.assertEqual(profile.level, ReputationLevel.CONTRIBUTOR)

        profile.reputation_score = 150
        profile._update_level()
        self.assertEqual(profile.level, ReputationLevel.TRUSTED)

        profile.reputation_score = 300
        profile._update_level()
        self.assertEqual(profile.level, ReputationLevel.EXPERT)

        profile.reputation_score = 600
        profile._update_level()
        self.assertEqual(profile.level, ReputationLevel.MASTER)

    def test_trust_weight(self):
        """Test trust weight calculation."""
        profile = self.reputation.register_auditor("auditor-1")

        # Newcomer
        profile.reputation_score = 30
        profile._update_level()
        self.assertEqual(profile.get_trust_weight(), 0.5)

        # Master
        profile.reputation_score = 600
        profile._update_level()
        self.assertEqual(profile.get_trust_weight(), 3.0)

    def test_leaderboard(self):
        """Test leaderboard generation."""
        for i in range(5):
            profile = self.reputation.register_auditor(f"auditor-{i}")
            profile.reputation_score = (i + 1) * 100

        leaderboard = self.reputation.get_leaderboard(3)
        self.assertEqual(len(leaderboard), 3)
        self.assertEqual(leaderboard[0].reputation_score, 500)  # Highest first

    def test_streak_tracking(self):
        """Test finding streak tracking."""
        profile = self.reputation.register_auditor("auditor-1")

        # Build streak
        for i in range(5):
            self.reputation.record_finding_confirmed("auditor-1", f"FIND-{i}")

        self.assertEqual(profile.current_streak, 5)
        self.assertEqual(profile.best_streak, 5)

        # Break streak
        self.reputation.record_finding_rejected("auditor-1", "FIND-BAD")
        self.assertEqual(profile.current_streak, 0)
        self.assertEqual(profile.best_streak, 5)  # Best preserved


class TestConsensusValidation(unittest.TestCase):
    """Test consensus validation functionality."""

    def setUp(self):
        self.reputation = ReputationSystem()
        self.validator = ConsensusValidator(self.reputation)

        # Register some validators
        for i in range(10):
            profile = self.reputation.register_auditor(f"validator-{i}")
            profile.reputation_score = 150 + i * 10  # 150-240

    def test_create_validation_request(self):
        """Test creating a validation request."""
        request = self.validator.create_validation_request(
            finding_id="FIND-123",
            contract_hash="contract-abc",
            vulnerability_type="reentrancy",
            severity="high",
            description="Test finding",
            submitter_id="submitter-1",
            min_validators=5,
        )

        self.assertTrue(request.request_id.startswith("VAL-"))
        self.assertGreater(len(request.selected_validators), 0)

    def test_submit_vote(self):
        """Test submitting a validation vote."""
        request = self.validator.create_validation_request(
            finding_id="FIND-123",
            contract_hash="contract-abc",
            vulnerability_type="reentrancy",
            severity="high",
            description="Test finding",
            submitter_id="submitter-1",
            min_validators=3,
        )
        self.validator.start_validation(request.request_id)

        # Submit votes from selected validators
        for validator_id in request.selected_validators[:2]:
            vote = self.validator.submit_vote(
                request_id=request.request_id,
                validator_id=validator_id,
                is_valid=True,
                confidence=0.9,
                reasoning="Looks valid",
            )
            self.assertIsNotNone(vote)

        self.assertEqual(len(request.votes), 2)

    def test_consensus_reached(self):
        """Test reaching consensus."""
        request = self.validator.create_validation_request(
            finding_id="FIND-123",
            contract_hash="contract-abc",
            vulnerability_type="reentrancy",
            severity="high",
            description="Test finding",
            submitter_id="submitter-1",
            min_validators=5,
        )
        self.validator.start_validation(request.request_id)

        # Submit votes
        for i, validator_id in enumerate(request.selected_validators[:5]):
            self.validator.submit_vote(
                request_id=request.request_id,
                validator_id=validator_id,
                is_valid=(i < 4),  # 4 yes, 1 no
                confidence=0.8,
                reasoning="Test",
            )

        result = self.validator.get_result(request.request_id)
        self.assertIsNotNone(result)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.total_votes, 5)

    def test_consensus_rejected(self):
        """Test consensus resulting in rejection."""
        request = self.validator.create_validation_request(
            finding_id="FIND-123",
            contract_hash="contract-abc",
            vulnerability_type="reentrancy",
            severity="high",
            description="Test finding",
            submitter_id="submitter-1",
            min_validators=5,
        )
        self.validator.start_validation(request.request_id)

        # Submit mostly negative votes
        for i, validator_id in enumerate(request.selected_validators[:5]):
            self.validator.submit_vote(
                request_id=request.request_id,
                validator_id=validator_id,
                is_valid=(i == 0),  # Only 1 yes
                confidence=0.8,
                reasoning="Test",
            )

        result = self.validator.get_result(request.request_id)
        self.assertIsNotNone(result)
        self.assertFalse(result.is_valid)

    def test_duplicate_vote_rejected(self):
        """Test that duplicate votes are rejected."""
        request = self.validator.create_validation_request(
            finding_id="FIND-123",
            contract_hash="contract-abc",
            vulnerability_type="reentrancy",
            severity="high",
            description="Test finding",
            submitter_id="submitter-1",
            min_validators=3,
        )
        self.validator.start_validation(request.request_id)

        validator_id = request.selected_validators[0]

        # First vote should succeed
        vote1 = self.validator.submit_vote(
            request_id=request.request_id,
            validator_id=validator_id,
            is_valid=True,
            confidence=0.9,
            reasoning="Valid",
        )
        self.assertIsNotNone(vote1)

        # Second vote should fail
        vote2 = self.validator.submit_vote(
            request_id=request.request_id,
            validator_id=validator_id,
            is_valid=False,
            confidence=0.5,
            reasoning="Changed mind",
        )
        self.assertIsNone(vote2)

    def test_pending_validations(self):
        """Test getting pending validations for a validator."""
        # Create multiple requests
        for i in range(3):
            request = self.validator.create_validation_request(
                finding_id=f"FIND-{i}",
                contract_hash="contract-abc",
                vulnerability_type="reentrancy",
                severity="high",
                description="Test",
                submitter_id="submitter-1",
                min_validators=5,
            )
            self.validator.start_validation(request.request_id)

        # Check pending for a validator
        validator_id = "validator-0"
        pending = self.validator.get_pending_for_validator(validator_id)
        # May or may not be selected for all
        self.assertIsInstance(pending, list)


class TestValidatorSelector(unittest.TestCase):
    """Test validator selection functionality."""

    def setUp(self):
        self.reputation = ReputationSystem()
        self.selector = ValidatorSelector(self.reputation)

        # Register validators with varying reputation
        for i in range(10):
            profile = self.reputation.register_auditor(f"validator-{i}")
            profile.reputation_score = 100 + i * 50

    def test_select_validators(self):
        """Test selecting validators."""
        validators = self.selector.select_validators(
            vulnerability_type="reentrancy",
            exclude_auditor="submitter-1",
            count=5,
            min_reputation=100,
        )

        self.assertEqual(len(validators), 5)
        self.assertNotIn("submitter-1", validators)

    def test_exclude_low_reputation(self):
        """Test that low reputation validators are excluded."""
        # Add low rep validator
        low_profile = self.reputation.register_auditor("low-rep")
        low_profile.reputation_score = 50

        validators = self.selector.select_validators(
            vulnerability_type="reentrancy",
            exclude_auditor="submitter-1",
            count=10,
            min_reputation=100,
        )

        self.assertNotIn("low-rep", validators)

    def test_expertise_bonus(self):
        """Test expertise affects selection."""
        # Register expertise
        self.selector.register_expertise("validator-0", ["reentrancy", "overflow"])

        expertise = self.selector.get_expertise("validator-0")
        self.assertIn("reentrancy", expertise)
        self.assertIn("overflow", expertise)


class TestCollaborativeNetwork(unittest.TestCase):
    """Test collaborative network functionality."""

    def setUp(self):
        self.network = CollaborativeNetwork()

    def test_register_auditor(self):
        """Test registering an auditor."""
        profile = self.network.register_auditor(
            "auditor-1",
            name="Alice",
            expertise=["reentrancy", "access-control"]
        )

        self.assertEqual(profile.auditor_id, "auditor-1")
        self.assertEqual(profile.name, "Alice")

    def test_submit_finding(self):
        """Test submitting a finding to the network."""
        self.network.register_auditor("auditor-1")

        # Add some validators
        for i in range(10):
            profile = self.network.register_auditor(f"validator-{i}")
            profile.reputation_score = 200

        submission = FindingSubmission(
            contract_code="contract Test { function withdraw() { ... } }",
            vulnerability_type="reentrancy",
            severity="high",
            title="Reentrancy in withdraw",
            description="State not updated before external call",
            function_name="withdraw",
        )

        finding = self.network.submit_finding("auditor-1", submission)

        self.assertIsNotNone(finding)
        self.assertEqual(finding.vulnerability_type, "reentrancy")
        self.assertEqual(finding.status, FindingStatus.VALIDATING)

    def test_submit_validation(self):
        """Test submitting a validation vote."""
        self.network.register_auditor("auditor-1")

        # Add validators
        for i in range(10):
            profile = self.network.register_auditor(f"validator-{i}")
            profile.reputation_score = 200

        submission = FindingSubmission(
            contract_code="contract Test {}",
            vulnerability_type="reentrancy",
            severity="high",
            title="Test",
            description="Test",
        )

        finding = self.network.submit_finding("auditor-1", submission)

        # Submit validations
        result = self.network.submit_validation(
            finding_id=finding.finding_id,
            validator_id="validator-0",
            is_valid=True,
            confidence=0.9,
            reasoning="Valid finding",
        )

        # May or may not reach consensus yet
        self.assertTrue(result is None or isinstance(result, ConsensusResult))

    def test_get_leaderboard(self):
        """Test getting leaderboard."""
        for i in range(5):
            profile = self.network.register_auditor(f"auditor-{i}")
            profile.reputation_score = (i + 1) * 50

        leaderboard = self.network.get_leaderboard(3)
        self.assertEqual(len(leaderboard), 3)

    def test_get_statistics(self):
        """Test getting network statistics."""
        self.network.register_auditor("auditor-1")

        stats = self.network.get_statistics()

        self.assertIsInstance(stats, NetworkStatistics)
        self.assertEqual(stats.total_auditors, 1)

    def test_search_findings(self):
        """Test searching findings."""
        self.network.register_auditor("auditor-1")

        # Add validators for submission
        for i in range(10):
            profile = self.network.register_auditor(f"validator-{i}")
            profile.reputation_score = 200

        # Submit a finding
        submission = FindingSubmission(
            contract_code="contract Token {}",
            vulnerability_type="reentrancy",
            severity="high",
            title="Classic Reentrancy Attack",
            description="Vulnerable to reentrancy",
        )
        self.network.submit_finding("auditor-1", submission, auto_validate=False)

        # Search
        results = self.network.search_findings("reentrancy")
        self.assertGreaterEqual(len(results), 1)

    def test_event_emission(self):
        """Test that events are emitted."""
        events_received = []

        from alphaswarm_sol.collab.network import NetworkEventType

        def handler(event):
            events_received.append(event)

        self.network.on_event(NetworkEventType.AUDITOR_JOINED, handler)
        self.network.register_auditor("auditor-1")

        self.assertEqual(len(events_received), 1)
        self.assertEqual(events_received[0].data["auditor_id"], "auditor-1")


class TestBountySystem(unittest.TestCase):
    """Test bounty system functionality."""

    def setUp(self):
        self.manager = BountyManager()

    def test_create_bounty(self):
        """Test creating a bounty."""
        bounty = self.manager.create_bounty(
            title="Test Protocol Audit",
            description="Find vulnerabilities in test protocol",
            sponsor_id="sponsor-1",
            total_pool=50000.0,
            min_reputation=50,
        )

        self.assertTrue(bounty.bounty_id.startswith("BOUNTY-"))
        self.assertEqual(bounty.status, BountyStatus.DRAFT)
        self.assertEqual(bounty.total_pool, 50000.0)

    def test_activate_bounty(self):
        """Test activating a bounty."""
        bounty = self.manager.create_bounty(
            title="Test Bounty",
            description="Test",
            sponsor_id="sponsor-1",
            total_pool=10000.0,
        )

        result = self.manager.activate_bounty(bounty.bounty_id)
        self.assertTrue(result)
        self.assertEqual(bounty.status, BountyStatus.ACTIVE)
        self.assertIsNotNone(bounty.start_time)

    def test_join_bounty(self):
        """Test joining a bounty."""
        bounty = self.manager.create_bounty(
            title="Test Bounty",
            description="Test",
            sponsor_id="sponsor-1",
            total_pool=10000.0,
            min_reputation=50,
        )
        self.manager.activate_bounty(bounty.bounty_id)

        result = self.manager.join_bounty(bounty.bounty_id, "hunter-1", 100)
        self.assertTrue(result)
        self.assertIn("hunter-1", bounty.participants)

    def test_join_bounty_reputation_check(self):
        """Test that low reputation can't join."""
        bounty = self.manager.create_bounty(
            title="Test Bounty",
            description="Test",
            sponsor_id="sponsor-1",
            total_pool=10000.0,
            min_reputation=100,
        )
        self.manager.activate_bounty(bounty.bounty_id)

        result = self.manager.join_bounty(bounty.bounty_id, "hunter-1", 50)
        self.assertFalse(result)

    def test_submit_finding_to_bounty(self):
        """Test submitting a finding to a bounty."""
        bounty = self.manager.create_bounty(
            title="Test Bounty",
            description="Test",
            sponsor_id="sponsor-1",
            total_pool=10000.0,
        )
        self.manager.activate_bounty(bounty.bounty_id)
        self.manager.join_bounty(bounty.bounty_id, "hunter-1", 100)

        finding = AuditFinding(
            finding_id="FIND-123",
            contract_hash="contract-abc",
            vulnerability_type="reentrancy",
            severity="high",
            title="Found vuln",
            description="Desc",
            auditor_id="hunter-1",
        )

        submission = self.manager.submit_finding(bounty.bounty_id, "hunter-1", finding)
        self.assertIsNotNone(submission)
        self.assertEqual(submission.auditor_id, "hunter-1")

    def test_bounty_scope(self):
        """Test bounty scope checking."""
        scope = BountyScope(
            contract_hashes=["contract-1", "contract-2"],
            in_scope_vulns=["reentrancy", "overflow"],
            out_of_scope_vulns=["gas-optimization"],
        )

        self.assertTrue(scope.is_in_scope("contract-1", "withdraw", "reentrancy"))
        self.assertFalse(scope.is_in_scope("contract-3", "withdraw", "reentrancy"))
        self.assertFalse(scope.is_in_scope("contract-1", "withdraw", "gas-optimization"))

    def test_reward_structure(self):
        """Test reward calculation."""
        rewards = RewardStructure(
            critical=10000,
            high=5000,
            medium=1000,
            low=250,
        )

        self.assertEqual(rewards.get_reward("critical"), 10000)
        self.assertEqual(rewards.get_reward("high", is_first=True), 7500)  # 1.5x
        self.assertEqual(rewards.get_reward("medium", is_unique=True), 1200)  # 1.2x

    def test_end_bounty(self):
        """Test ending a bounty."""
        bounty = self.manager.create_bounty(
            title="Test Bounty",
            description="Test",
            sponsor_id="sponsor-1",
            total_pool=10000.0,
        )
        self.manager.activate_bounty(bounty.bounty_id)

        summary = self.manager.end_bounty(bounty.bounty_id)

        self.assertIsNotNone(summary)
        self.assertEqual(bounty.status, BountyStatus.COMPLETED)
        self.assertEqual(summary["status"], "completed")

    def test_cancel_bounty(self):
        """Test cancelling a bounty."""
        bounty = self.manager.create_bounty(
            title="Test Bounty",
            description="Test",
            sponsor_id="sponsor-1",
            total_pool=10000.0,
        )
        self.manager.activate_bounty(bounty.bounty_id)

        result = self.manager.cancel_bounty(bounty.bounty_id)
        self.assertTrue(result)
        self.assertEqual(bounty.status, BountyStatus.CANCELLED)

    def test_get_active_bounties(self):
        """Test getting active bounties."""
        for i in range(3):
            bounty = self.manager.create_bounty(
                title=f"Bounty {i}",
                description="Test",
                sponsor_id="sponsor-1",
                total_pool=10000.0,
            )
            if i < 2:
                self.manager.activate_bounty(bounty.bounty_id)

        active = self.manager.get_active_bounties()
        self.assertEqual(len(active), 2)

    def test_bounty_time_remaining(self):
        """Test time remaining calculation."""
        bounty = self.manager.create_bounty(
            title="Test Bounty",
            description="Test",
            sponsor_id="sponsor-1",
            total_pool=10000.0,
            end_time=datetime.now() + timedelta(hours=48),
        )
        self.manager.activate_bounty(bounty.bounty_id)

        remaining = bounty.get_time_remaining()
        self.assertIsNotNone(remaining)
        self.assertGreater(remaining.total_seconds(), 0)

    def test_bounty_leaderboard(self):
        """Test bounty leaderboard."""
        bounty = self.manager.create_bounty(
            title="Test Bounty",
            description="Test",
            sponsor_id="sponsor-1",
            total_pool=50000.0,
        )
        self.manager.activate_bounty(bounty.bounty_id)

        # Add participants and submissions
        for i in range(3):
            self.manager.join_bounty(bounty.bounty_id, f"hunter-{i}", 100)

            finding = AuditFinding(
                finding_id=f"FIND-{i}",
                contract_hash="contract-abc",
                vulnerability_type="reentrancy",
                severity="medium",
                title=f"Finding {i}",
                description="Desc",
                auditor_id=f"hunter-{i}",
            )
            submission = self.manager.submit_finding(bounty.bounty_id, f"hunter-{i}", finding)

            # Evaluate submission
            self.manager.evaluate_submission(
                submission.submission_id,
                is_valid=True,
                is_duplicate=False,
            )

        leaderboard = self.manager.get_leaderboard(bounty.bounty_id)
        self.assertEqual(len(leaderboard), 3)

    def test_bounty_statistics(self):
        """Test bounty manager statistics."""
        for i in range(3):
            bounty = self.manager.create_bounty(
                title=f"Bounty {i}",
                description="Test",
                sponsor_id="sponsor-1",
                total_pool=10000.0,
            )
            self.manager.activate_bounty(bounty.bounty_id)

        stats = self.manager.get_statistics()
        self.assertEqual(stats["total_bounties"], 3)
        self.assertEqual(stats["active_bounties"], 3)
        self.assertEqual(stats["total_pool"], 30000.0)


class TestIntegration(unittest.TestCase):
    """Integration tests for the full collaborative workflow."""

    def test_full_finding_lifecycle(self):
        """Test complete finding submission → validation → consensus."""
        network = CollaborativeNetwork()

        # Register auditor and validators
        network.register_auditor("alice", name="Alice", expertise=["reentrancy"])

        for i in range(10):
            profile = network.register_auditor(f"validator-{i}")
            profile.reputation_score = 200

        # Submit finding
        submission = FindingSubmission(
            contract_code="contract Vault { function withdraw() external { ... } }",
            vulnerability_type="reentrancy",
            severity="high",
            title="Reentrancy in Vault.withdraw()",
            description="External call before state update",
            function_name="withdraw",
            recommended_fix="Use ReentrancyGuard or CEI pattern",
        )

        finding = network.submit_finding("alice", submission)
        self.assertIsNotNone(finding)
        self.assertEqual(finding.status, FindingStatus.VALIDATING)

        # Get the validation request
        pending = network.consensus.get_pending_for_validator("validator-0")

        if pending:
            request = pending[0]

            # Submit votes
            for i, validator_id in enumerate(request.selected_validators[:5]):
                network.consensus.submit_vote(
                    request_id=request.request_id,
                    validator_id=validator_id,
                    is_valid=True,
                    confidence=0.85,
                    reasoning="Valid reentrancy vulnerability",
                )

            # Check result
            result = network.consensus.get_result(request.request_id)
            if result:
                self.assertTrue(result.is_valid)

    def test_full_bounty_workflow(self):
        """Test complete bounty lifecycle."""
        manager = BountyManager()

        # Create and activate bounty
        bounty = manager.create_bounty(
            title="DeFi Protocol Audit",
            description="Find critical vulnerabilities",
            sponsor_id="protocol-team",
            total_pool=100000.0,
            min_reputation=50,
            end_time=datetime.now() + timedelta(days=7),
        )
        manager.activate_bounty(bounty.bounty_id)

        # Hunters join
        hunters = ["hunter-alice", "hunter-bob", "hunter-charlie"]
        for hunter in hunters:
            manager.join_bounty(bounty.bounty_id, hunter, 100)

        self.assertEqual(len(bounty.participants), 3)

        # Hunters submit findings
        for i, hunter in enumerate(hunters):
            finding = AuditFinding(
                finding_id=f"FIND-{hunter}",
                contract_hash="protocol-v2",
                vulnerability_type="reentrancy" if i == 0 else "overflow",
                severity="high" if i < 2 else "medium",
                title=f"Vulnerability by {hunter}",
                description="Description",
                auditor_id=hunter,
            )
            submission = manager.submit_finding(bounty.bounty_id, hunter, finding)

            # Evaluate
            manager.evaluate_submission(
                submission.submission_id,
                is_valid=True,
                is_duplicate=(i == 1),  # Bob's is duplicate
                duplicate_of="FIND-hunter-alice" if i == 1 else None,
            )

        # End bounty
        summary = manager.end_bounty(bounty.bounty_id)

        self.assertEqual(summary["total_participants"], 3)
        self.assertEqual(summary["total_submissions"], 3)
        self.assertEqual(summary["valid_findings"], 2)  # Bob's was duplicate


if __name__ == "__main__":
    unittest.main()
