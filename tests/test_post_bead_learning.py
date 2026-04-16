"""Tests for post-bead learning pipeline."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from alphaswarm_sol.beads.schema import (
    VulnerabilityBead,
    CodeSnippet,
    PatternContext,
    InvestigationGuide,
    TestContext,
)
from alphaswarm_sol.beads.types import Severity, InvestigationStep, Verdict, VerdictType
from alphaswarm_sol.learning.overlay import LearningOverlayStore
from alphaswarm_sol.learning.post_bead import PostBeadLearner, build_finding_stub


def _sample_graph_context(function_id: str) -> dict:
    return {
        "nodes": {
            function_id: {
                "id": function_id,
                "type": "Function",
                "label": "withdraw",
                "properties": {
                    "modifiers": ["nonReentrant"],
                    "signature": ["withdraw", ["uint256"], []],
                },
                "relevance_score": 1.0,
                "distance_from_focal": 0,
                "is_focal": True,
            }
        },
        "edges": {},
        "focal_node_ids": [function_id],
        "category": "reentrancy",
        "stats": {},
        "full_graph_available": True,
    }


def _sample_bead(function_id: str) -> VulnerabilityBead:
    return VulnerabilityBead(
        id="VKG-0001-abc123",
        vulnerability_class="reentrancy",
        pattern_id="vm-001",
        function_id=function_id,
        severity=Severity.CRITICAL,
        confidence=0.9,
        vulnerable_code=CodeSnippet(
            source="function withdraw(uint256 amount) public { msg.sender.call{value: amount}(\"\"); }",
            file_path="/contracts/Vault.sol",
            start_line=10,
            end_line=12,
            function_name="withdraw",
            contract_name="Vault",
        ),
        related_code=[],
        full_contract=None,
        inheritance_chain=["Ownable"],
        pattern_context=PatternContext(
            pattern_name="Basic Reentrancy",
            pattern_description="Detects external calls before state updates",
            why_flagged="External call before balance update",
            matched_properties=["state_write_after_external_call"],
            evidence_lines=[10, 11],
        ),
        investigation_guide=InvestigationGuide(
            steps=[
                InvestigationStep(
                    step_number=1,
                    action="Check for reentrancy guards",
                    look_for="nonReentrant modifier",
                    evidence_needed="No guard found",
                ),
            ],
            questions_to_answer=["Is there a reentrancy guard?"],
            common_false_positives=[],
            key_indicators=["External call before state write"],
            safe_patterns=["CEI pattern"],
        ),
        test_context=TestContext(
            scaffold_code="// test scaffold",
            attack_scenario="Re-enter withdraw",
            setup_requirements=[],
            expected_outcome="Funds drained",
        ),
        similar_exploits=[],
        fix_recommendations=["Use nonReentrant modifier"],
        graph_context=_sample_graph_context(function_id),
        graph_context_category="reentrancy",
    )


class TestPostBeadLearning(unittest.TestCase):
    """Tests for post-bead learning."""

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        config_path = self.temp_dir / "config.json"
        config_path.write_text(
            json.dumps(
                {
                    "overlay_enabled": True,
                    "events_enabled": False,
                    "fp_enabled": False,
                }
            )
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_overlay_label_recorded(self):
        """Overlay assertions are recorded when configured."""
        function_id = "function:abc123"
        bead = _sample_bead(function_id)
        bead.notes.append("LABEL:IS_REENTRANCY_GUARD:function:abc123:0.95")
        bead.set_verdict(
            Verdict(
                type=VerdictType.TRUE_POSITIVE,
                reason="Guard confirmed",
                confidence=0.9,
                evidence=[],
            )
        )

        learner = PostBeadLearner(learning_dir=self.temp_dir)
        learner.process(bead)

        store = LearningOverlayStore(self.temp_dir)
        labels = store.get_labels(function_id, category="reentrancy")
        self.assertEqual(len(labels), 1)
        self.assertEqual(labels[0].label, "IS_REENTRANCY_GUARD")

    def test_build_finding_stub_uses_modifiers(self):
        """Modifiers from graph context are used for similarity."""
        bead = _sample_bead("function:abc123")
        stub = build_finding_stub(bead)
        self.assertIn("nonReentrant", stub.modifiers)
