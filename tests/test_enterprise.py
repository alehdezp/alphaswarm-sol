"""Phase 20: Enterprise Features Tests.

Tests for configuration profiles, multi-project support, and report generation.
"""

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List

from alphaswarm_sol.kg.schema import KnowledgeGraph, Node, Edge
from alphaswarm_sol.enterprise.profiles import (
    ProfileLevel,
    PatternConfig,
    AnalysisConfig,
    PerformanceConfig,
    OutputConfig,
    ConfigProfile,
    ProfileManager,
    get_profile,
    FAST_PROFILE,
    STANDARD_PROFILE,
    THOROUGH_PROFILE,
)
from alphaswarm_sol.enterprise.multi_project import (
    ProjectInfo,
    CrossProjectQueryResult,
    CrossProjectQuery,
    MultiProjectManager,
)
from alphaswarm_sol.enterprise.reports import (
    ReportFormat,
    Severity,
    Finding,
    ReportSection,
    SecurityReport,
    ReportGenerator,
    generate_report,
)


class TestProfileLevel(unittest.TestCase):
    """Tests for ProfileLevel enum."""

    def test_levels_defined(self):
        """All profile levels are defined."""
        self.assertEqual(ProfileLevel.FAST.value, "fast")
        self.assertEqual(ProfileLevel.STANDARD.value, "standard")
        self.assertEqual(ProfileLevel.THOROUGH.value, "thorough")
        self.assertEqual(ProfileLevel.CUSTOM.value, "custom")


class TestConfigProfile(unittest.TestCase):
    """Tests for ConfigProfile dataclass."""

    def test_profile_creation(self):
        """ConfigProfile can be created with all fields."""
        profile = ConfigProfile(
            name="test",
            level=ProfileLevel.STANDARD,
            description="Test profile",
        )

        self.assertEqual(profile.name, "test")
        self.assertEqual(profile.level, ProfileLevel.STANDARD)
        self.assertIsNotNone(profile.patterns)
        self.assertIsNotNone(profile.analysis)

    def test_to_dict(self):
        """ConfigProfile serializes correctly."""
        profile = ConfigProfile(
            name="test",
            level=ProfileLevel.FAST,
        )

        d = profile.to_dict()
        self.assertEqual(d["name"], "test")
        self.assertEqual(d["level"], "fast")
        self.assertIn("patterns", d)
        self.assertIn("analysis", d)

    def test_from_dict(self):
        """ConfigProfile deserializes correctly."""
        d = {
            "name": "custom",
            "level": "thorough",
            "description": "Custom profile",
            "patterns": {
                "tier_b_enabled": False,
            },
            "analysis": {
                "max_path_depth": 10,
            },
        }

        profile = ConfigProfile.from_dict(d)
        self.assertEqual(profile.name, "custom")
        self.assertEqual(profile.level, ProfileLevel.THOROUGH)
        self.assertFalse(profile.patterns.tier_b_enabled)
        self.assertEqual(profile.analysis.max_path_depth, 10)


class TestPredefinedProfiles(unittest.TestCase):
    """Tests for predefined profiles."""

    def test_fast_profile(self):
        """FAST_PROFILE is configured for speed."""
        self.assertEqual(FAST_PROFILE.level, ProfileLevel.FAST)
        self.assertFalse(FAST_PROFILE.patterns.tier_b_enabled)
        self.assertFalse(FAST_PROFILE.analysis.enable_temporal)
        self.assertTrue(FAST_PROFILE.output.compact)

    def test_standard_profile(self):
        """STANDARD_PROFILE is balanced."""
        self.assertEqual(STANDARD_PROFILE.level, ProfileLevel.STANDARD)
        self.assertTrue(STANDARD_PROFILE.patterns.tier_b_enabled)
        self.assertTrue(STANDARD_PROFILE.analysis.enable_temporal)

    def test_thorough_profile(self):
        """THOROUGH_PROFILE is comprehensive."""
        self.assertEqual(THOROUGH_PROFILE.level, ProfileLevel.THOROUGH)
        self.assertTrue(THOROUGH_PROFILE.output.verbose)
        self.assertGreater(THOROUGH_PROFILE.analysis.max_path_depth, STANDARD_PROFILE.analysis.max_path_depth)


class TestProfileManager(unittest.TestCase):
    """Tests for ProfileManager class."""

    def test_get_profile(self):
        """ProfileManager retrieves profiles."""
        manager = ProfileManager()

        profile = manager.get_profile("fast")
        self.assertIsNotNone(profile)
        self.assertEqual(profile.level, ProfileLevel.FAST)

    def test_set_active_profile(self):
        """ProfileManager sets active profile."""
        manager = ProfileManager()

        self.assertTrue(manager.set_active_profile("fast"))
        self.assertEqual(manager.active_profile.level, ProfileLevel.FAST)

    def test_register_custom_profile(self):
        """ProfileManager registers custom profiles."""
        manager = ProfileManager()

        custom = ConfigProfile(name="my_profile", level=ProfileLevel.CUSTOM)
        manager.register_profile(custom)

        self.assertIn("my_profile", manager.list_profiles())

    def test_list_profiles(self):
        """ProfileManager lists all profiles."""
        manager = ProfileManager()

        profiles = manager.list_profiles()
        self.assertIn("fast", profiles)
        self.assertIn("standard", profiles)
        self.assertIn("thorough", profiles)


class TestGetProfile(unittest.TestCase):
    """Tests for get_profile function."""

    def test_get_profile(self):
        """get_profile convenience function works."""
        profile = get_profile("standard")
        self.assertIsNotNone(profile)
        self.assertEqual(profile.level, ProfileLevel.STANDARD)

    def test_get_profile_missing(self):
        """get_profile returns None for missing profile."""
        profile = get_profile("nonexistent")
        self.assertIsNone(profile)


class TestProjectInfo(unittest.TestCase):
    """Tests for ProjectInfo dataclass."""

    def test_project_creation(self):
        """ProjectInfo can be created."""
        project = ProjectInfo(
            id="proj1",
            name="Test Project",
            path="/path/to/project",
        )

        self.assertEqual(project.id, "proj1")
        self.assertEqual(project.name, "Test Project")
        self.assertFalse(project.is_loaded)

    def test_with_graph(self):
        """ProjectInfo with graph is loaded."""
        graph = KnowledgeGraph(nodes={}, edges={}, metadata={})
        project = ProjectInfo(
            id="proj1",
            name="Test",
            graph=graph,
        )

        self.assertTrue(project.is_loaded)

    def test_to_dict(self):
        """ProjectInfo serializes correctly."""
        project = ProjectInfo(
            id="proj1",
            name="Test",
            contracts=["A", "B"],
        )

        d = project.to_dict()
        self.assertEqual(d["id"], "proj1")
        self.assertEqual(d["contract_count"], 2)


class TestMultiProjectManager(unittest.TestCase):
    """Tests for MultiProjectManager class."""

    def test_add_project(self):
        """MultiProjectManager adds projects."""
        manager = MultiProjectManager()

        project = ProjectInfo(id="proj1", name="Test")
        manager.add_project(project)

        self.assertIsNotNone(manager.get_project("proj1"))

    def test_remove_project(self):
        """MultiProjectManager removes projects."""
        manager = MultiProjectManager()

        project = ProjectInfo(id="proj1", name="Test")
        manager.add_project(project)
        manager.remove_project("proj1")

        self.assertIsNone(manager.get_project("proj1"))

    def test_list_projects(self):
        """MultiProjectManager lists projects."""
        manager = MultiProjectManager()

        manager.add_project(ProjectInfo(id="proj1", name="Test1"))
        manager.add_project(ProjectInfo(id="proj2", name="Test2"))

        projects = manager.list_projects()
        self.assertEqual(len(projects), 2)

    def test_load_graph(self):
        """MultiProjectManager loads graphs."""
        manager = MultiProjectManager()
        project = ProjectInfo(id="proj1", name="Test")
        manager.add_project(project)

        graph = KnowledgeGraph(
            nodes={
                "contract1": Node(id="contract1", label="A", type="Contract"),
                "func1": Node(id="func1", label="f", type="Function", properties={"contract_name": "A"}),
            },
            edges={},
            metadata={},
        )

        manager.load_graph("proj1", graph)

        loaded_project = manager.get_project("proj1")
        self.assertTrue(loaded_project.is_loaded)
        self.assertIn("A", loaded_project.contracts)

    def test_get_total_stats(self):
        """MultiProjectManager calculates stats."""
        manager = MultiProjectManager()

        project = ProjectInfo(id="proj1", name="Test")
        manager.add_project(project)

        graph = KnowledgeGraph(
            nodes={
                "contract1": Node(id="contract1", label="A", type="Contract"),
                "func1": Node(id="func1", label="f", type="Function", properties={"contract_name": "A"}),
            },
            edges={},
            metadata={},
        )
        manager.load_graph("proj1", graph)

        stats = manager.get_total_stats()
        self.assertEqual(stats["total_projects"], 1)
        self.assertEqual(stats["loaded_projects"], 1)
        self.assertEqual(stats["total_contracts"], 1)
        self.assertEqual(stats["total_functions"], 1)


class TestCrossProjectQuery(unittest.TestCase):
    """Tests for CrossProjectQuery class."""

    def _create_test_projects(self) -> List[ProjectInfo]:
        """Create test projects with graphs."""
        project1 = ProjectInfo(id="proj1", name="Test1")
        project1.graph = KnowledgeGraph(
            nodes={
                "func1": Node(
                    id="func1",
                    label="withdraw",
                    type="Function",
                    properties={
                        "contract_name": "Vault",
                        "visibility": "external",
                        "state_write_after_external_call": True,
                        "has_reentrancy_guard": False,
                    }
                ),
            },
            edges={},
            metadata={},
        )

        project2 = ProjectInfo(id="proj2", name="Test2")
        project2.graph = KnowledgeGraph(
            nodes={
                "func2": Node(
                    id="func2",
                    label="withdrawAll",
                    type="Function",
                    properties={
                        "contract_name": "Safe",
                        "visibility": "external",
                        "state_write_after_external_call": True,
                        "has_reentrancy_guard": True,
                    }
                ),
            },
            edges={},
            metadata={},
        )

        return [project1, project2]

    def test_find_similar_functions(self):
        """CrossProjectQuery finds similar functions."""
        projects = self._create_test_projects()
        query = CrossProjectQuery(projects)

        result = query.find_similar_functions("withdraw")

        self.assertEqual(result.total_matches, 2)
        self.assertIn("proj1", result.results)
        self.assertIn("proj2", result.results)

    def test_find_vulnerable_patterns(self):
        """CrossProjectQuery finds vulnerable patterns."""
        projects = self._create_test_projects()
        query = CrossProjectQuery(projects)

        result = query.find_vulnerable_patterns("reentrancy")

        # Only proj1 has reentrancy vulnerability
        self.assertEqual(result.total_matches, 1)
        self.assertIn("proj1", result.results)
        self.assertNotIn("proj2", result.results)

    def test_find_by_property(self):
        """CrossProjectQuery finds by property."""
        projects = self._create_test_projects()
        query = CrossProjectQuery(projects)

        result = query.find_by_property("visibility", "external")

        self.assertEqual(result.total_matches, 2)


class TestFinding(unittest.TestCase):
    """Tests for Finding dataclass."""

    def test_finding_creation(self):
        """Finding can be created."""
        finding = Finding(
            id="REEN-001",
            title="Reentrancy",
            severity=Severity.CRITICAL,
            description="State modified after external call",
            location="Vault.withdraw",
        )

        self.assertEqual(finding.id, "REEN-001")
        self.assertEqual(finding.severity, Severity.CRITICAL)

    def test_to_dict(self):
        """Finding serializes correctly."""
        finding = Finding(
            id="TEST-001",
            title="Test Finding",
            severity=Severity.HIGH,
        )

        d = finding.to_dict()
        self.assertEqual(d["id"], "TEST-001")
        self.assertEqual(d["severity"], "high")


class TestSecurityReport(unittest.TestCase):
    """Tests for SecurityReport dataclass."""

    def test_report_creation(self):
        """SecurityReport can be created."""
        report = SecurityReport(
            title="Test Report",
            project_name="Test Project",
        )

        self.assertEqual(report.title, "Test Report")
        self.assertEqual(report.total_findings, 0)

    def test_add_finding(self):
        """SecurityReport adds findings."""
        report = SecurityReport(title="Test")

        report.add_finding(Finding(id="1", title="F1", severity=Severity.CRITICAL))
        report.add_finding(Finding(id="2", title="F2", severity=Severity.HIGH))

        self.assertEqual(report.total_findings, 2)
        self.assertEqual(report.critical_count, 1)
        self.assertEqual(report.high_count, 1)

    def test_to_dict(self):
        """SecurityReport serializes correctly."""
        report = SecurityReport(title="Test")
        report.add_finding(Finding(id="1", title="F1", severity=Severity.MEDIUM))

        d = report.to_dict()
        self.assertEqual(d["title"], "Test")
        self.assertEqual(d["stats"]["total"], 1)
        self.assertEqual(d["stats"]["medium"], 1)


class TestReportGenerator(unittest.TestCase):
    """Tests for ReportGenerator class."""

    def _create_test_graph(self) -> KnowledgeGraph:
        """Create a test graph with vulnerabilities."""
        return KnowledgeGraph(
            nodes={
                "func1": Node(
                    id="func1",
                    label="withdraw",
                    type="Function",
                    properties={
                        "contract_name": "Vault",
                        "visibility": "external",
                        "state_write_after_external_call": True,
                        "has_reentrancy_guard": False,
                    }
                ),
                "func2": Node(
                    id="func2",
                    label="setOwner",
                    type="Function",
                    properties={
                        "contract_name": "Vault",
                        "visibility": "public",
                        "writes_privileged_state": True,
                        "has_access_gate": False,
                    }
                ),
                "func3": Node(
                    id="func3",
                    label="safe",
                    type="Function",
                    properties={
                        "contract_name": "Vault",
                        "visibility": "public",
                    }
                ),
            },
            edges={},
            metadata={},
        )

    def test_generate_report(self):
        """ReportGenerator generates report."""
        graph = self._create_test_graph()
        generator = ReportGenerator(graph)

        report = generator.generate("Test Project")

        self.assertEqual(report.project_name, "Test Project")
        self.assertGreater(report.total_findings, 0)
        self.assertGreater(len(report.sections), 0)

    def test_extracts_reentrancy(self):
        """ReportGenerator finds reentrancy."""
        graph = self._create_test_graph()
        generator = ReportGenerator(graph)

        report = generator.generate()

        reentrancy_findings = [f for f in report.findings if "REEN" in f.id]
        self.assertGreater(len(reentrancy_findings), 0)

    def test_extracts_access_control(self):
        """ReportGenerator finds access control issues."""
        graph = self._create_test_graph()
        generator = ReportGenerator(graph)

        report = generator.generate()

        auth_findings = [f for f in report.findings if "AUTH" in f.id]
        self.assertGreater(len(auth_findings), 0)

    def test_to_markdown(self):
        """ReportGenerator generates Markdown."""
        graph = self._create_test_graph()
        generator = ReportGenerator(graph)
        report = generator.generate("Test")

        md = generator.to_markdown(report)

        self.assertIn("# ", md)
        self.assertIn("## ", md)
        self.assertIn("CRITICAL", md)

    def test_to_html(self):
        """ReportGenerator generates HTML."""
        graph = self._create_test_graph()
        generator = ReportGenerator(graph)
        report = generator.generate("Test")

        html = generator.to_html(report)

        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("<h1>", html)
        self.assertIn("class=\"finding", html)


class TestGenerateReport(unittest.TestCase):
    """Tests for generate_report function."""

    def test_generate_markdown(self):
        """generate_report produces Markdown."""
        graph = KnowledgeGraph(
            nodes={
                "func1": Node(
                    id="func1",
                    label="test",
                    type="Function",
                    properties={"contract_name": "Test"},
                ),
            },
            edges={},
            metadata={},
        )

        md = generate_report(graph, "Test", ReportFormat.MARKDOWN)
        self.assertIn("#", md)

    def test_generate_html(self):
        """generate_report produces HTML."""
        graph = KnowledgeGraph(nodes={}, edges={}, metadata={})

        html = generate_report(graph, "Test", ReportFormat.HTML)
        self.assertIn("<html>", html)

    def test_generate_json(self):
        """generate_report produces JSON."""
        graph = KnowledgeGraph(nodes={}, edges={}, metadata={})

        json_str = generate_report(graph, "Test", ReportFormat.JSON)
        data = json.loads(json_str)

        self.assertIn("title", data)
        self.assertIn("findings", data)


if __name__ == "__main__":
    unittest.main()
