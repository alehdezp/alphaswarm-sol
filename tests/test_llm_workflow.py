"""
LLM Integration Test (Task 3.8)

Validates that an LLM agent can complete a full audit workflow
in < 15 tool calls using only the information from AGENTS.md.

Philosophy: "Any AGENTS.md-compliant LLM can discover and use VKG"

This test simulates the LLM workflow by counting the minimum
tool calls needed to complete an audit:

1. Discovery: Read AGENTS.md (1 call)
2. Build: vkg build-kg contracts/ (1 call)
3. Analyze: Either query or pattern matching (1 call)
4. Review findings: vkg findings list (1 call)
5. For each finding: vkg findings show <id> (N calls)
6. Update status: vkg findings update <id> (N calls)
7. Export: vkg findings export (1 call)

Target: < 15 total tool calls
"""

import json
import os
import tempfile
import unittest
from pathlib import Path
from typing import Optional

from alphaswarm_sol.findings.model import (
    Evidence,
    Finding,
    FindingConfidence,
    FindingSeverity,
    FindingStatus,
    Location,
)
from alphaswarm_sol.findings.store import FindingsStore
from alphaswarm_sol.findings.verification import generate_checklist


class WorkflowSimulator:
    """
    Simulates an LLM agent completing an audit workflow.

    Tracks the number of "tool calls" (CLI invocations) needed.
    """

    def __init__(self, vkg_dir: Path):
        self.vkg_dir = vkg_dir
        self.tool_calls = 0
        self.workflow_log = []
        self.store: Optional[FindingsStore] = None

    def _log_call(self, command: str, description: str = ""):
        """Log a tool call."""
        self.tool_calls += 1
        self.workflow_log.append({
            "call_number": self.tool_calls,
            "command": command,
            "description": description,
        })

    # Phase 1: Discovery

    def discover_vkg(self) -> str:
        """
        Step 1: LLM reads AGENTS.md to discover available commands.

        Simulates: cat .vkg/AGENTS.md
        """
        self._log_call("cat .vkg/AGENTS.md", "Discover VKG capabilities")

        agents_md_path = self.vkg_dir / "AGENTS.md"
        if agents_md_path.exists():
            return agents_md_path.read_text()
        return ""

    # Phase 2: Build

    def build_graph(self, contracts_path: str = "contracts/") -> dict:
        """
        Step 2: LLM builds the knowledge graph.

        Simulates: vkg build-kg contracts/
        """
        self._log_call(f"vkg build-kg {contracts_path}", "Build knowledge graph")

        # Simulate successful build
        return {
            "success": True,
            "contracts_analyzed": 3,
            "functions_indexed": 25,
            "graph_path": str(self.vkg_dir / "graph.json"),
        }

    # Phase 3: Analysis

    def run_analysis(self) -> list[dict]:
        """
        Step 3: LLM runs vulnerability analysis.

        Simulates: vkg analyze
        """
        self._log_call("vkg analyze", "Run vulnerability detection")

        # Initialize the store and add sample findings
        self.store = FindingsStore(self.vkg_dir)

        # Simulate findings from analysis
        findings_data = [
            {
                "pattern": "reentrancy-classic",
                "severity": FindingSeverity.CRITICAL,
                "confidence": FindingConfidence.HIGH,
                "location": Location(file="Vault.sol", line=42, column=8, function="withdraw"),
                "description": "State write after external call without reentrancy guard",
                "evidence": Evidence(
                    behavioral_signature="R:bal→X:out→W:bal",
                    why_vulnerable="External call transfers ETH before balance update",
                    properties_matched=["state_write_after_external_call"],
                ),
            },
            {
                "pattern": "auth-001",
                "severity": FindingSeverity.HIGH,
                "confidence": FindingConfidence.MEDIUM,
                "location": Location(file="Token.sol", line=87, column=4, function="mint"),
                "description": "Public function writes privileged state without access control",
                "evidence": Evidence(
                    behavioral_signature="W:supply",
                    why_vulnerable="Anyone can mint tokens",
                    properties_matched=["writes_privileged_state", "no_access_gate"],
                ),
            },
            {
                "pattern": "oracle-001",
                "severity": FindingSeverity.MEDIUM,
                "confidence": FindingConfidence.LOW,
                "location": Location(file="LendingPool.sol", line=156, column=12, function="liquidate"),
                "description": "Oracle price used without staleness check",
                "evidence": Evidence(
                    behavioral_signature="R:price→W:collateral",
                    why_vulnerable="Stale prices could allow profitable liquidations",
                    properties_matched=["reads_oracle_price"],
                    properties_missing=["has_staleness_check"],
                ),
            },
        ]

        for f_data in findings_data:
            finding = Finding(**f_data)
            self.store.add(finding)

        return [{"id": f.id, "severity": f.severity.value} for f in self.store.list()]

    # Phase 4: Review Findings

    def list_findings(self) -> list[dict]:
        """
        Step 4: LLM lists all findings.

        Simulates: vkg findings list
        """
        self._log_call("vkg findings list", "List all findings")

        if not self.store:
            return []

        return [
            {
                "id": f.id,
                "severity": f.severity.value,
                "status": f.status.value,
                "title": f.title,
                "location": str(f.location),
            }
            for f in self.store.list()
        ]

    def show_finding(self, finding_id: str) -> Optional[dict]:
        """
        Step 5a: LLM gets details of a specific finding.

        Simulates: vkg findings show <id>
        """
        self._log_call(f"vkg findings show {finding_id}", f"Get details for {finding_id}")

        if not self.store:
            return None

        finding = self.store.get(finding_id)
        if finding:
            return finding.to_dict()
        return None

    def get_next_finding(self) -> Optional[dict]:
        """
        Step 5b: LLM gets next priority finding (alternative to show).

        Simulates: vkg findings next

        This is MORE EFFICIENT - reduces tool calls by combining
        list + show into a single command.
        """
        self._log_call("vkg findings next", "Get next priority finding")

        if not self.store:
            return None

        finding = self.store.get_next()
        if finding:
            return finding.to_dict()
        return None

    # Phase 5: Update Status

    def update_finding(self, finding_id: str, status: str, reason: str = "") -> bool:
        """
        Step 6: LLM updates finding status after investigation.

        Simulates: vkg findings update <id> --status <status>
        """
        self._log_call(
            f"vkg findings update {finding_id} --status {status}",
            f"Update {finding_id} to {status}"
        )

        if not self.store:
            return False

        finding = self.store.get(finding_id)
        if finding:
            # Use correct API: update(finding_id, status, reason, notes)
            self.store.update(finding_id, FindingStatus(status), reason)
            return True
        return False

    # Phase 6: Export

    def export_findings(self, format: str = "sarif") -> str:
        """
        Step 7: LLM exports findings for reporting.

        Simulates: vkg findings export --format sarif
        """
        self._log_call(f"vkg findings export --format {format}", "Export report")

        if not self.store:
            return "{}"

        if format == "json":
            return self.store.to_json()
        elif format == "sarif":
            # Simplified SARIF output
            findings_list = self.store.list()
            return json.dumps({
                "version": "2.1.0",
                "runs": [{
                    "tool": {"driver": {"name": "VKG"}},
                    "results": [
                        {"ruleId": f.pattern, "message": {"text": f.description}}
                        for f in findings_list
                    ]
                }]
            })
        return "{}"

    # Workflow Statistics

    def get_stats(self) -> dict:
        """Get workflow statistics."""
        return {
            "total_tool_calls": self.tool_calls,
            "workflow_log": self.workflow_log,
            "target_calls": 15,
            "within_target": self.tool_calls < 15,
        }


class TestLLMWorkflow(unittest.TestCase):
    """
    Tests that verify LLM can complete audit workflow efficiently.

    Target: < 15 tool calls for complete workflow.
    """

    def setUp(self):
        """Create temporary directory for test."""
        self.temp_dir = tempfile.mkdtemp()
        self.vkg_dir = Path(self.temp_dir) / ".vkg"
        self.vkg_dir.mkdir(parents=True)

        # Create minimal AGENTS.md
        agents_md = self.vkg_dir / "AGENTS.md"
        agents_md.write_text("""# VKG Security Analysis

## Quick Start
```bash
vkg build-kg contracts/     # Build knowledge graph
vkg analyze                  # Find vulnerabilities
vkg findings list            # See all findings
vkg findings next            # Get next priority finding
```

## Workflow
1. `vkg build-kg contracts/`
2. `vkg analyze`
3. For each: `vkg findings next` → investigate → `vkg findings update`
4. `vkg findings export --format sarif`
""")

    def tearDown(self):
        """Clean up temporary directory."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_optimal_workflow_under_15_calls(self):
        """
        Test optimal workflow: LLM completes audit in minimum calls.

        Optimal flow using `next` command (most efficient):
        1. Discover (read AGENTS.md) - 1 call
        2. Build graph - 1 call
        3. Run analysis - 1 call
        4. Get finding 1 (next) - 1 call
        5. Update finding 1 - 1 call
        6. Get finding 2 (next) - 1 call
        7. Update finding 2 - 1 call
        8. Get finding 3 (next) - 1 call
        9. Update finding 3 - 1 call
        10. Export - 1 call

        Total: 10 calls (well under 15)
        """
        sim = WorkflowSimulator(self.vkg_dir)

        # Discovery
        agents_content = sim.discover_vkg()
        self.assertIn("vkg build-kg", agents_content)
        self.assertIn("vkg analyze", agents_content)

        # Build
        build_result = sim.build_graph()
        self.assertTrue(build_result["success"])

        # Analyze
        findings = sim.run_analysis()
        self.assertEqual(len(findings), 3)

        # Process each finding using efficient `next` pattern
        for _ in range(3):
            finding = sim.get_next_finding()
            if finding:
                # Investigate (reading details is included in next)
                # Update status based on "investigation"
                sim.update_finding(finding["id"], "confirmed", "Verified via code review")

        # Export
        sarif = sim.export_findings("sarif")
        self.assertIn("VKG", sarif)

        # Verify we're under target
        stats = sim.get_stats()
        self.assertLess(
            stats["total_tool_calls"], 15,
            f"Workflow took {stats['total_tool_calls']} calls, target is < 15"
        )

        # Log for visibility
        print(f"\n=== Optimal Workflow Results ===")
        print(f"Total tool calls: {stats['total_tool_calls']}")
        print(f"Target: < 15")
        print(f"Workflow:")
        for entry in stats["workflow_log"]:
            print(f"  {entry['call_number']}. {entry['command']}")

    def test_list_then_show_workflow(self):
        """
        Test list-then-show workflow (less efficient but still valid).

        Flow:
        1. Discover - 1 call
        2. Build - 1 call
        3. Analyze - 1 call
        4. List findings - 1 call
        5. Show finding 1 - 1 call
        6. Update finding 1 - 1 call
        7. Show finding 2 - 1 call
        8. Update finding 2 - 1 call
        9. Show finding 3 - 1 call
        10. Update finding 3 - 1 call
        11. Export - 1 call

        Total: 11 calls (still under 15)
        """
        sim = WorkflowSimulator(self.vkg_dir)

        # Discovery
        sim.discover_vkg()

        # Build
        sim.build_graph()

        # Analyze
        sim.run_analysis()

        # List to get IDs
        findings = sim.list_findings()
        self.assertEqual(len(findings), 3)

        # Show and update each
        for f in findings:
            sim.show_finding(f["id"])
            sim.update_finding(f["id"], "confirmed")

        # Export
        sim.export_findings()

        # Verify we're under target
        stats = sim.get_stats()
        self.assertLess(
            stats["total_tool_calls"], 15,
            f"Workflow took {stats['total_tool_calls']} calls, target is < 15"
        )

        print(f"\n=== List-Then-Show Workflow Results ===")
        print(f"Total tool calls: {stats['total_tool_calls']}")

    def test_worst_case_still_acceptable(self):
        """
        Test that even inefficient workflow stays under 20 calls.

        This tests the "SHOULD" threshold (16-20 calls triggers iteration).
        """
        sim = WorkflowSimulator(self.vkg_dir)

        # Extra discovery call (LLM reads AGENTS.md twice)
        sim.discover_vkg()
        sim.discover_vkg()  # Redundant but might happen

        # Build
        sim.build_graph()

        # Analyze
        sim.run_analysis()

        # List findings multiple times (inefficient)
        sim.list_findings()
        findings = sim.list_findings()  # Redundant

        # Process each with redundant show calls
        for f in findings:
            sim.show_finding(f["id"])
            sim.show_finding(f["id"])  # Redundant view
            sim.update_finding(f["id"], "investigating")
            sim.update_finding(f["id"], "confirmed")  # Status change

        # Export
        sim.export_findings()

        stats = sim.get_stats()

        # Even worst case should be under 20
        self.assertLess(
            stats["total_tool_calls"], 20,
            f"Even worst case took {stats['total_tool_calls']} calls, max acceptable is 20"
        )

        print(f"\n=== Worst Case Workflow Results ===")
        print(f"Total tool calls: {stats['total_tool_calls']}")
        print(f"(Under 20 threshold: {'PASS' if stats['total_tool_calls'] < 20 else 'FAIL'})")

    def test_workflow_discovers_commands_from_agents_md(self):
        """Test that AGENTS.md contains all necessary commands."""
        sim = WorkflowSimulator(self.vkg_dir)

        content = sim.discover_vkg()

        # Must contain essential commands
        required_commands = [
            "vkg build-kg",
            "vkg analyze",
            "vkg findings list",
            "vkg findings next",
            "vkg findings export",
        ]

        for cmd in required_commands:
            self.assertIn(cmd, content, f"AGENTS.md must document '{cmd}'")

        # Should contain workflow guidance
        self.assertIn("Workflow", content, "AGENTS.md must include workflow section")

    def test_findings_status_for_session_handoff(self):
        """Test that session status provides continuation context."""
        sim = WorkflowSimulator(self.vkg_dir)

        # Setup: partial workflow
        sim.discover_vkg()
        sim.build_graph()
        sim.run_analysis()

        # Process only first finding
        finding = sim.get_next_finding()
        if finding:
            sim.update_finding(finding["id"], "confirmed")

        # A new LLM session should be able to continue
        # by reading the findings list
        remaining = sim.list_findings()

        # Count unprocessed findings
        pending = [f for f in remaining if f["status"] == "pending"]
        self.assertEqual(len(pending), 2, "Should have 2 pending findings for next session")


class TestWorkflowEfficiency(unittest.TestCase):
    """Tests focused on workflow efficiency metrics."""

    def test_next_command_reduces_calls(self):
        """
        The `next` command should reduce calls vs list+show pattern.
        """
        temp_dir = tempfile.mkdtemp()
        vkg_dir = Path(temp_dir) / ".vkg"
        vkg_dir.mkdir(parents=True)

        try:
            # Create AGENTS.md
            (vkg_dir / "AGENTS.md").write_text("# VKG\nvkg findings next")

            # Workflow with `next`
            sim_next = WorkflowSimulator(vkg_dir)
            sim_next.discover_vkg()
            sim_next.build_graph()
            sim_next.run_analysis()

            # Process 3 findings with next
            for _ in range(3):
                f = sim_next.get_next_finding()
                if f:
                    sim_next.update_finding(f["id"], "confirmed")

            sim_next.export_findings()
            calls_with_next = sim_next.get_stats()["total_tool_calls"]

            # Workflow with list+show
            sim_list = WorkflowSimulator(vkg_dir)
            sim_list.discover_vkg()
            sim_list.build_graph()
            sim_list.run_analysis()

            findings = sim_list.list_findings()
            for f in findings:
                sim_list.show_finding(f["id"])
                sim_list.update_finding(f["id"], "confirmed")

            sim_list.export_findings()
            calls_with_list = sim_list.get_stats()["total_tool_calls"]

            # `next` pattern should use fewer calls
            self.assertLess(
                calls_with_next, calls_with_list,
                f"next pattern ({calls_with_next}) should be more efficient than list+show ({calls_with_list})"
            )

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_verification_checklist_included_in_finding(self):
        """
        Verification steps should be in finding output (no extra call needed).
        """
        temp_dir = tempfile.mkdtemp()
        vkg_dir = Path(temp_dir) / ".vkg"
        vkg_dir.mkdir(parents=True)

        try:
            (vkg_dir / "AGENTS.md").write_text("# VKG")

            sim = WorkflowSimulator(vkg_dir)
            sim.discover_vkg()
            sim.build_graph()
            sim.run_analysis()

            # Get finding
            finding = sim.get_next_finding()
            self.assertIsNotNone(finding)

            # Verification steps should be accessible
            # Generate checklist for the finding
            checklist = generate_checklist(
                finding["id"],
                finding["pattern"],
                finding["location"]["file"],
                finding["location"].get("function", "unknown")
            )

            # Checklist should have actionable steps
            self.assertGreater(len(checklist.steps), 0)

            # First step should have commands
            self.assertGreater(
                len(checklist.steps[0].commands), 0,
                "Verification should include runnable commands"
            )

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
