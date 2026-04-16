"""Tests for VulnDocs Validators.

Task 18.2: Tests for IdeaCaptureValidator, CompletenessValidator, QualityScorer.
"""

import unittest

from alphaswarm_sol.vulndocs.knowledge_doc import (
    DetectionSection,
    DocMetadata,
    ExamplesSection,
    ExploitationSection,
    MergeResult,
    MitigationSection,
    PatternLinkage,
    PatternLinkageType,
    Prevalence,
    RealExploitRef,
    Severity,
    SourceSummary,
    UniqueIdea,
    VulnKnowledgeDoc,
)
from alphaswarm_sol.vulndocs.validators.idea_capture import (
    IdeaCaptureValidator,
    IdeaCapture,
    IdeaCaptureResult,
    IdeaLoss,
    IdeaLossType,
    validate_idea_capture,
)
from alphaswarm_sol.vulndocs.validators.completeness import (
    CompletenessValidator,
    CompletenessResult,
    SectionCompleteness,
    MissingSectionType,
    validate_completeness,
)
from alphaswarm_sol.vulndocs.validators.quality import (
    QualityScorer,
    QualityScore,
    QualityDimension,
    QualityResult,
    score_quality,
)
from alphaswarm_sol.vulndocs.validators.svr_sync import (
    SVRFieldSync,
    sync_svr_doc,
    sync_svr_summary,
)


def create_test_document(
    complete: bool = True,
    with_examples: bool = True,
    with_exploits: bool = True,
) -> VulnKnowledgeDoc:
    """Create a test document with varying completeness."""
    doc = VulnKnowledgeDoc(
        id="reentrancy/classic/state-after-call",
        name="Classic Reentrancy via State Write After External Call",
        category="reentrancy",
        subcategory="classic-reentrancy",
        severity=Severity.CRITICAL,
        prevalence=Prevalence.COMMON,
        one_liner="External call before state update allows recursive calls to drain funds.",
        tldr="An attacker can exploit the order of operations when a contract makes "
             "an external call before updating its state. The attacker's contract "
             "can recursively call back into the vulnerable function before state "
             "is updated, allowing multiple withdrawals.",
        detection=DetectionSection(
            graph_signals=["state_write_after_external_call", "no_reentrancy_guard"],
            vulnerable_sequence="R:bal -> X:out -> W:bal",
            safe_sequence="R:bal -> W:bal -> X:out",
            indicators=["External call before state update", "No reentrancy guard"],
            checklist=["Check call ordering", "Verify guard presence", "Review CEI pattern"],
        ) if complete else DetectionSection(),
        exploitation=ExploitationSection(
            attack_vector="Attacker deploys contract with malicious fallback that re-enters",
            prerequisites=["Target has payable function", "Target makes external call"],
            attack_steps=[
                "Deploy attack contract with reentrant fallback",
                "Call vulnerable withdraw function",
                "Fallback re-enters before state update",
                "Drain funds by repeating until empty",
            ],
            potential_impact="Complete loss of contract funds",
            monetary_risk="critical",
        ) if complete else ExploitationSection(),
        mitigation=MitigationSection(
            primary_fix="Implement Checks-Effects-Interactions (CEI) pattern",
            alternative_fixes=["Add ReentrancyGuard", "Use pull payment pattern"],
            safe_pattern="CEI",
            how_to_verify=["Verify state updated before calls", "Check guard presence"],
        ) if complete else MitigationSection(),
        examples=ExamplesSection(
            vulnerable_code="""function withdraw(uint amount) public {
    require(balances[msg.sender] >= amount);
    (bool ok, ) = msg.sender.call{value: amount}("");
    require(ok);
    balances[msg.sender] -= amount;
}""" if with_examples else "",
            vulnerable_code_explanation="Balance is updated after external call" if with_examples else "",
            fixed_code="""function withdraw(uint amount) public {
    require(balances[msg.sender] >= amount);
    balances[msg.sender] -= amount;
    (bool ok, ) = msg.sender.call{value: amount}("");
    require(ok);
}""" if with_examples else "",
            fixed_code_explanation="Balance updated before external call (CEI)" if with_examples else "",
            real_exploits=[
                RealExploitRef(
                    name="The DAO Hack",
                    date="2016-06-17",
                    loss="$60M",
                    protocol="The DAO",
                    brief="Classic reentrancy drained 3.6M ETH",
                    source_url="https://hackingdistributed.com/2016/06/18/analysis-of-the-dao-exploit/",
                ),
            ] if with_exploits else [],
        ),
        pattern_linkage=PatternLinkage(
            linkage_type=PatternLinkageType.EXACT_MATCH,
            pattern_ids=["reentrancy-001", "reentrancy-002"],
            coverage_pct=0.95,
        ) if complete else PatternLinkage(),
        metadata=DocMetadata(
            sources=["https://openzeppelin.com", "https://consensys.io"],
            source_authority=0.95,
            completeness_score=0.9,
            confidence_score=0.9,
        ),
    )
    return doc


def create_test_summary(
    source_name: str = "test-source",
    with_attack: bool = True,
    with_mitigation: bool = True,
) -> SourceSummary:
    """Create a test source summary."""
    return SourceSummary(
        source_url=f"https://{source_name}.com/article",
        source_name=source_name,
        category="reentrancy",
        subcategory="classic-reentrancy",
        key_points=[
            "Check call ordering is crucial",
            "Use CEI pattern for safety",
            "Reentrancy guards provide additional protection",
        ],
        attack_vector="Recursive callback exploits state update ordering" if with_attack else "",
        attack_steps=[
            "Deploy attacker contract",
            "Call target withdraw",
            "Recursively re-enter in fallback",
        ] if with_attack else [],
        mitigation="Implement CEI pattern" if with_mitigation else "",
        safe_patterns=["Checks-Effects-Interactions", "ReentrancyGuard"] if with_mitigation else [],
        vulnerable_code="function withdraw() { msg.sender.call(); balance[sender] = 0; }",
        incidents=[
            {"name": "DAO Hack", "brief": "Lost 60M USD in 2016"},
        ],
        source_authority=0.9,
    )


# =============================================================================
# IdeaCaptureValidator Tests
# =============================================================================


class TestIdeaCapture(unittest.TestCase):
    """Tests for IdeaCapture dataclass."""

    def test_auto_hash(self):
        """Hash should be computed automatically."""
        idea = IdeaCapture(
            id="test-1",
            content="Test content here",
            idea_type=IdeaLossType.ATTACK_VARIANT,
            source_url="https://test.com",
            source_name="test",
        )
        self.assertTrue(idea.content_hash)
        self.assertEqual(len(idea.content_hash), 12)

    def test_same_content_same_hash(self):
        """Same content should produce same hash."""
        idea1 = IdeaCapture(
            id="test-1",
            content="Test content",
            idea_type=IdeaLossType.ATTACK_VARIANT,
            source_url="https://test1.com",
            source_name="test1",
        )
        idea2 = IdeaCapture(
            id="test-2",
            content="Test content",
            idea_type=IdeaLossType.MITIGATION,
            source_url="https://test2.com",
            source_name="test2",
        )
        self.assertEqual(idea1.content_hash, idea2.content_hash)

    def test_to_dict(self):
        """Should serialize to dictionary."""
        idea = IdeaCapture(
            id="test-1",
            content="Test",
            idea_type=IdeaLossType.EDGE_CASE,
            source_url="https://test.com",
            source_name="test",
        )
        d = idea.to_dict()
        self.assertEqual(d["id"], "test-1")
        self.assertEqual(d["idea_type"], "edge_case")


class TestIdeaCaptureValidator(unittest.TestCase):
    """Tests for IdeaCaptureValidator."""

    def test_high_capture_rate(self):
        """Should achieve high capture rate when content matches."""
        doc = create_test_document(complete=True)

        # Create summary with content that matches the document
        summary = SourceSummary(
            source_url="https://test.com",
            source_name="test",
            category="reentrancy",
            subcategory="classic-reentrancy",
            # Key points that match document content
            key_points=[
                "External call before state update",
                "No reentrancy guard",
                "Check call ordering",
            ],
            attack_vector="Attacker deploys contract with malicious fallback",
            attack_steps=[
                "Deploy attack contract",
                "Call vulnerable withdraw",
                "Fallback re-enters before state update",
            ],
            mitigation="Implement CEI pattern",
            safe_patterns=["CEI", "ReentrancyGuard"],
        )

        validator = IdeaCaptureValidator()
        result = validator.validate([summary], doc)

        # Should have good capture rate when content matches
        self.assertGreater(result.capture_rate, 0.7)
        # Even with some minor losses, should generally succeed if no critical ones
        self.assertEqual(result.critical_losses, 0)

    def test_detects_missing_attack_vector(self):
        """Should detect missing attack information."""
        doc = create_test_document(complete=True)
        # Modify doc to remove attack info
        doc.exploitation.attack_vector = ""
        doc.exploitation.attack_steps = []

        summaries = [create_test_summary(with_attack=True)]

        validator = IdeaCaptureValidator()
        result = validator.validate(summaries, doc)

        # Should have some lost ideas
        attack_losses = [l for l in result.lost_ideas if l.idea.idea_type == IdeaLossType.ATTACK_VARIANT]
        self.assertGreater(len(attack_losses), 0)

    def test_detects_missing_mitigation(self):
        """Should detect missing mitigation."""
        doc = create_test_document(complete=True)
        doc.mitigation.primary_fix = ""
        doc.mitigation.alternative_fixes = []
        doc.mitigation.safe_pattern = ""

        summaries = [create_test_summary(with_mitigation=True)]

        validator = IdeaCaptureValidator()
        result = validator.validate(summaries, doc)

        mitigation_losses = [l for l in result.lost_ideas if l.idea.idea_type == IdeaLossType.MITIGATION]
        self.assertGreater(len(mitigation_losses), 0)

    def test_similarity_threshold(self):
        """Should use similarity threshold for partial matches."""
        doc = create_test_document(complete=True)

        # Create summary with slightly different wording
        summary = SourceSummary(
            source_url="https://test.com",
            source_name="test",
            category="reentrancy",
            subcategory="classic-reentrancy",
            key_points=["Check the ordering of calls is important"],  # Similar to doc
            mitigation="Use CEI pattern",  # Similar
        )

        # Low threshold should match
        validator_low = IdeaCaptureValidator(similarity_threshold=0.5)
        result_low = validator_low.validate([summary], doc)

        # High threshold might not match
        validator_high = IdeaCaptureValidator(similarity_threshold=0.95)
        result_high = validator_high.validate([summary], doc)

        # Low threshold should have better capture rate
        self.assertGreaterEqual(result_low.capture_rate, result_high.capture_rate)

    def test_empty_summaries(self):
        """Should handle empty summaries gracefully."""
        doc = create_test_document(complete=True)

        validator = IdeaCaptureValidator()
        result = validator.validate([], doc)

        self.assertTrue(result.success)
        self.assertEqual(result.total_ideas, 0)

    def test_multiple_summaries_deduplication(self):
        """Should deduplicate ideas across summaries."""
        doc = create_test_document(complete=True)

        # Two summaries with overlapping content
        summary1 = create_test_summary(source_name="source1")
        summary2 = create_test_summary(source_name="source2")

        validator = IdeaCaptureValidator()
        result = validator.validate([summary1, summary2], doc)

        # Should not count duplicates
        self.assertLess(result.total_ideas, 20)  # With dedup, should be reasonable

    def test_validate_merge_result(self):
        """Should validate against MergeResult."""
        doc = create_test_document(complete=True)
        summaries = [create_test_summary()]

        # Create merge result with unmerged idea
        merge_result = MergeResult(
            subcategory_id="reentrancy/classic",
            document=doc,
            unique_ideas=[
                UniqueIdea(
                    id="idea-1",
                    description="Cross-function reentrancy variant",
                    source_urls=["https://test.com"],
                    category="reentrancy",
                    idea_type="attack_variant",
                    merged=False,  # Not merged!
                ),
            ],
            conflicts=[],
            source_count=1,
        )

        validator = IdeaCaptureValidator()
        result = validator.validate_merge_result(merge_result, summaries)

        # Should detect the unmerged idea
        self.assertGreater(len(result.lost_ideas), 0)


class TestIdeaLoss(unittest.TestCase):
    """Tests for IdeaLoss classification."""

    def test_critical_severity(self):
        """Critical loss types should be marked critical."""
        idea = IdeaCapture(
            id="test",
            content="Attack variant",
            idea_type=IdeaLossType.ATTACK_VARIANT,
            source_url="https://test.com",
            source_name="test",
        )

        validator = IdeaCaptureValidator()
        doc = create_test_document(complete=False)
        loss = validator._create_loss_record(idea, doc)

        self.assertEqual(loss.severity, "critical")

    def test_important_severity(self):
        """Important loss types should be marked important."""
        idea = IdeaCapture(
            id="test",
            content="Code example",
            idea_type=IdeaLossType.CODE_EXAMPLE,
            source_url="https://test.com",
            source_name="test",
        )

        validator = IdeaCaptureValidator()
        doc = create_test_document(complete=False)
        loss = validator._create_loss_record(idea, doc)

        self.assertEqual(loss.severity, "important")

    def test_minor_severity(self):
        """Minor loss types should be marked minor."""
        idea = IdeaCapture(
            id="test",
            content="keyword",
            idea_type=IdeaLossType.KEYWORD,
            source_url="https://test.com",
            source_name="test",
        )

        validator = IdeaCaptureValidator()
        doc = create_test_document(complete=False)
        loss = validator._create_loss_record(idea, doc)

        self.assertEqual(loss.severity, "minor")


class TestValidateIdeaCaptureFunction(unittest.TestCase):
    """Tests for validate_idea_capture convenience function."""

    def test_convenience_function(self):
        """Should work as convenience function."""
        doc = create_test_document(complete=True)
        summaries = [create_test_summary()]

        result = validate_idea_capture(summaries, doc)

        self.assertIsInstance(result, IdeaCaptureResult)


# =============================================================================
# CompletenessValidator Tests
# =============================================================================


class TestSectionCompleteness(unittest.TestCase):
    """Tests for SectionCompleteness."""

    def test_to_dict(self):
        """Should serialize to dictionary."""
        sc = SectionCompleteness(
            section=MissingSectionType.DETECTION,
            is_complete=True,
            completion_pct=0.8,
            missing_fields=["checklist"],
        )
        d = sc.to_dict()
        self.assertEqual(d["section"], "detection")
        self.assertEqual(d["completion_pct"], 0.8)


class TestCompletenessValidator(unittest.TestCase):
    """Tests for CompletenessValidator."""

    def test_complete_document_passes(self):
        """Complete document should pass validation."""
        doc = create_test_document(complete=True, with_examples=True)

        validator = CompletenessValidator()
        result = validator.validate(doc)

        self.assertTrue(result.success)
        self.assertGreater(result.overall_score, 0.8)

    def test_incomplete_document_fails(self):
        """Incomplete document should fail validation."""
        doc = create_test_document(complete=False, with_examples=False)

        validator = CompletenessValidator()
        result = validator.validate(doc)

        self.assertFalse(result.success)
        self.assertLess(result.overall_score, 0.5)

    def test_missing_identification_is_critical(self):
        """Missing identification should be critical."""
        doc = create_test_document(complete=True)
        doc.id = ""
        doc.name = ""

        validator = CompletenessValidator()
        result = validator.validate(doc)

        self.assertIn("id", result.critical_missing)
        self.assertIn("name", result.critical_missing)

    def test_missing_detection_is_required(self):
        """Missing detection should be required."""
        doc = create_test_document(complete=True)
        doc.detection = DetectionSection()

        validator = CompletenessValidator()
        result = validator.validate(doc)

        # Should have detection-related missing fields
        detection_missing = [f for f in result.required_missing if "detection" in f]
        self.assertGreater(len(detection_missing), 0)

    def test_custom_min_completeness(self):
        """Should respect custom min completeness."""
        doc = create_test_document(complete=True, with_examples=False)

        # High threshold
        validator_high = CompletenessValidator(min_completeness=0.95)
        result_high = validator_high.validate(doc)

        # Low threshold
        validator_low = CompletenessValidator(min_completeness=0.5)
        result_low = validator_low.validate(doc)

        # Same score, different success
        self.assertFalse(result_high.success)
        self.assertTrue(result_low.success)

    def test_pattern_linkage_by_type(self):
        """Should check pattern linkage by type."""
        doc = create_test_document(complete=True)

        # EXACT_MATCH needs pattern_ids
        doc.pattern_linkage = PatternLinkage(
            linkage_type=PatternLinkageType.EXACT_MATCH,
            pattern_ids=[],  # Missing!
        )

        validator = CompletenessValidator()
        result = validator.validate(doc)

        linkage_section = result.sections.get("pattern_linkage")
        self.assertIsNotNone(linkage_section)
        self.assertFalse(linkage_section.is_complete)

    def test_theoretical_linkage(self):
        """Should check theoretical linkage differently."""
        doc = create_test_document(complete=True)

        # THEORETICAL needs why_no_pattern and manual_hints
        doc.pattern_linkage = PatternLinkage(
            linkage_type=PatternLinkageType.THEORETICAL,
            why_no_pattern="Requires business logic understanding",
            manual_hints=["Check invariants", "Review state transitions"],
        )

        validator = CompletenessValidator()
        result = validator.validate(doc)

        linkage_section = result.sections.get("pattern_linkage")
        self.assertTrue(linkage_section.is_complete)

    def test_summary_output(self):
        """Should generate readable summary."""
        doc = create_test_document(complete=True)

        validator = CompletenessValidator()
        result = validator.validate(doc)
        summary = result.to_summary()

        self.assertIn("Completeness Validation", summary)
        self.assertIn("Overall Score", summary)


class TestValidateCompletenessFunction(unittest.TestCase):
    """Tests for validate_completeness convenience function."""

    def test_convenience_function(self):
        """Should work as convenience function."""
        doc = create_test_document(complete=True)

        result = validate_completeness(doc)

        self.assertIsInstance(result, CompletenessResult)


# =============================================================================
# QualityScorer Tests
# =============================================================================


class TestQualityScore(unittest.TestCase):
    """Tests for QualityScore."""

    def test_to_dict(self):
        """Should serialize to dictionary."""
        score = QualityScore(
            dimension=QualityDimension.ACCURACY,
            score=0.85,
            notes=["High authority sources"],
        )
        d = score.to_dict()
        self.assertEqual(d["dimension"], "accuracy")
        self.assertEqual(d["score"], 0.85)


class TestQualityScorer(unittest.TestCase):
    """Tests for QualityScorer."""

    def test_high_quality_document(self):
        """High quality document should score well."""
        doc = create_test_document(complete=True, with_examples=True, with_exploits=True)

        scorer = QualityScorer()
        result = scorer.score(doc)

        self.assertGreater(result.overall_score, 0.7)
        self.assertIn(result.grade, ["A", "B"])

    def test_low_quality_document(self):
        """Low quality document should score poorly."""
        doc = create_test_document(complete=False, with_examples=False, with_exploits=False)
        doc.metadata.source_authority = 0.2
        doc.metadata.sources = []

        scorer = QualityScorer()
        result = scorer.score(doc)

        self.assertLess(result.overall_score, 0.5)
        self.assertIn(result.grade, ["D", "F"])

    def test_accuracy_dimension(self):
        """Should score accuracy based on sources."""
        doc = create_test_document(complete=True)

        # High authority
        doc.metadata.source_authority = 0.95
        doc.metadata.sources = ["source1", "source2", "source3"]
        doc.metadata.confidence_score = 0.9

        scorer = QualityScorer()
        result = scorer.score(doc)

        accuracy = result.dimensions[QualityDimension.ACCURACY]
        self.assertGreater(accuracy.score, 0.8)

    def test_completeness_dimension(self):
        """Should score completeness using validator."""
        doc = create_test_document(complete=True)

        scorer = QualityScorer()
        result = scorer.score(doc)

        completeness = result.dimensions[QualityDimension.COMPLETENESS]
        self.assertGreater(completeness.score, 0.7)

    def test_clarity_dimension(self):
        """Should score clarity based on content quality."""
        doc = create_test_document(complete=True, with_examples=True)

        scorer = QualityScorer()
        result = scorer.score(doc)

        clarity = result.dimensions[QualityDimension.CLARITY]
        self.assertGreater(clarity.score, 0.5)

    def test_actionability_dimension(self):
        """Should score actionability based on practical value."""
        doc = create_test_document(complete=True)

        scorer = QualityScorer()
        result = scorer.score(doc)

        actionability = result.dimensions[QualityDimension.ACTIONABILITY]
        self.assertGreater(actionability.score, 0.7)

    def test_evidence_dimension(self):
        """Should score evidence based on real-world support."""
        doc = create_test_document(complete=True, with_exploits=True)

        scorer = QualityScorer()
        result = scorer.score(doc)

        evidence = result.dimensions[QualityDimension.EVIDENCE]
        self.assertGreater(evidence.score, 0.6)

    def test_grade_assignment(self):
        """Should assign correct letter grades."""
        scorer = QualityScorer()

        self.assertEqual(scorer._score_to_grade(0.95), "A")
        self.assertEqual(scorer._score_to_grade(0.85), "B")
        self.assertEqual(scorer._score_to_grade(0.75), "C")
        self.assertEqual(scorer._score_to_grade(0.65), "D")
        self.assertEqual(scorer._score_to_grade(0.45), "F")

    def test_suggestions_generated(self):
        """Should generate improvement suggestions."""
        doc = create_test_document(complete=False, with_examples=False)

        scorer = QualityScorer()
        result = scorer.score(doc)

        self.assertGreater(len(result.suggestions), 0)

    def test_strengths_and_weaknesses(self):
        """Should identify strengths and weaknesses."""
        doc = create_test_document(complete=True)
        # Make accuracy strong
        doc.metadata.source_authority = 0.95
        doc.metadata.sources = ["s1", "s2", "s3"]
        doc.metadata.confidence_score = 0.9

        scorer = QualityScorer()
        result = scorer.score(doc)

        # Should have at least one strength
        self.assertGreater(len(result.strengths), 0)

    def test_custom_dimension_weights(self):
        """Should respect custom dimension weights."""
        doc = create_test_document(complete=True)

        # Weight accuracy heavily
        custom_weights = {
            QualityDimension.ACCURACY: 0.8,
            QualityDimension.COMPLETENESS: 0.05,
            QualityDimension.CLARITY: 0.05,
            QualityDimension.ACTIONABILITY: 0.05,
            QualityDimension.EVIDENCE: 0.05,
        }

        scorer = QualityScorer(dimension_weights=custom_weights)
        result = scorer.score(doc)

        # Score should be close to accuracy score
        accuracy_score = result.dimensions[QualityDimension.ACCURACY].score
        self.assertAlmostEqual(result.overall_score, accuracy_score, delta=0.15)

    def test_summary_output(self):
        """Should generate readable summary."""
        doc = create_test_document(complete=True)

        scorer = QualityScorer()
        result = scorer.score(doc)
        summary = result.to_summary()

        self.assertIn("Quality Score", summary)
        self.assertIn("Grade", summary)
        self.assertIn("Dimensions", summary)

    def test_theoretical_pattern_affects_actionability(self):
        """Theoretical patterns should reduce actionability score."""
        doc = create_test_document(complete=True)

        # EXACT_MATCH - high actionability
        doc.pattern_linkage = PatternLinkage(
            linkage_type=PatternLinkageType.EXACT_MATCH,
            pattern_ids=["test-001"],
            coverage_pct=0.95,
        )
        scorer = QualityScorer()
        result_exact = scorer.score(doc)

        # THEORETICAL - lower actionability
        doc.pattern_linkage = PatternLinkage(
            linkage_type=PatternLinkageType.THEORETICAL,
            why_no_pattern="Complex business logic",
            manual_hints=["Check invariants"],
        )
        result_theoretical = scorer.score(doc)

        exact_action = result_exact.dimensions[QualityDimension.ACTIONABILITY].score
        theoretical_action = result_theoretical.dimensions[QualityDimension.ACTIONABILITY].score

        self.assertGreater(exact_action, theoretical_action)


class TestScoreQualityFunction(unittest.TestCase):
    """Tests for score_quality convenience function."""

    def test_convenience_function(self):
        """Should work as convenience function."""
        doc = create_test_document(complete=True)

        result = score_quality(doc)

        self.assertIsInstance(result, QualityResult)


class TestSVRFieldSync(unittest.TestCase):
    """Tests for SVR field sync validator."""

    def test_sync_doc_complete(self):
        """Complete doc should have high SVR coverage."""
        doc = create_test_document(complete=True, with_examples=True, with_exploits=True)
        result = sync_svr_doc(doc)
        self.assertGreaterEqual(result.completeness_score, 0.7)
        self.assertEqual(result.total_fields, len(SVRFieldSync()._doc_checks))

    def test_sync_doc_missing_fields(self):
        """Incomplete doc should report missing fields."""
        doc = create_test_document(complete=False, with_examples=False, with_exploits=False)
        result = SVRFieldSync().sync_doc(doc)
        self.assertGreater(len(result.missing_fields), 0)
        self.assertLess(result.completeness_score, 0.6)

    def test_sync_summary_missing_fields(self):
        """Summary missing attack details should be flagged."""
        summary = create_test_summary(with_attack=False, with_mitigation=False)
        result = sync_svr_summary(summary)
        self.assertIn("attack_vector", result.missing_fields)
        self.assertIn("mitigation", result.missing_fields)


# =============================================================================
# Integration Tests
# =============================================================================


class TestValidatorIntegration(unittest.TestCase):
    """Integration tests for all validators."""

    def test_full_validation_workflow(self):
        """Should run complete validation workflow."""
        doc = create_test_document(complete=True, with_examples=True, with_exploits=True)

        # Create summary with matching content for realistic test
        summary = SourceSummary(
            source_url="https://test.com",
            source_name="test",
            category="reentrancy",
            subcategory="classic-reentrancy",
            key_points=[
                "External call before state update",
                "Check call ordering",
                "CEI pattern",
            ],
            attack_vector="Recursive callback exploits state ordering",
            mitigation="CEI pattern",
            safe_patterns=["CEI"],
        )

        # Run all validators
        idea_result = validate_idea_capture([summary], doc)
        completeness_result = validate_completeness(doc)
        quality_result = score_quality(doc)

        # Completeness and quality should pass for complete document
        self.assertTrue(completeness_result.success)
        self.assertGreater(quality_result.overall_score, 0.7)
        # Idea capture should have reasonable rate (may not be 100% due to wording)
        self.assertGreater(idea_result.capture_rate, 0.5)

    def test_validation_consistency(self):
        """Validators should be consistent."""
        doc = create_test_document(complete=False)

        completeness_result = validate_completeness(doc)
        quality_result = score_quality(doc)

        # Low completeness should correlate with low quality
        completeness_score = completeness_result.overall_score
        quality_completeness = quality_result.dimensions[QualityDimension.COMPLETENESS].score

        # Should be approximately equal (same validator used internally)
        self.assertAlmostEqual(completeness_score, quality_completeness, delta=0.1)


if __name__ == "__main__":
    unittest.main()
