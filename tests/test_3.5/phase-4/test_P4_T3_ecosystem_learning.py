"""
Phase 4 Task 3: Ecosystem Learning Tests

Tests ecosystem learning, exploit import, and pattern effectiveness tracking.
"""

import unittest
import tempfile
from pathlib import Path
from datetime import datetime
import json
import csv

from alphaswarm_sol.transfer import (
    ExploitRecord,
    PatternEffectiveness,
    EcosystemStats,
    EcosystemLearner,
)


class TestExploitRecord(unittest.TestCase):
    """Test ExploitRecord dataclass."""

    def test_exploit_creation(self):
        """Test creating an exploit record."""
        exploit = ExploitRecord(
            id="test_001",
            name="Test Exploit",
            date=datetime(2024, 1, 15),
            protocol="Test Protocol",
            vulnerability_type="reentrancy",
            loss_usd=1000000.0,
            source="manual",
        )

        self.assertEqual(exploit.id, "test_001")
        self.assertEqual(exploit.name, "Test Exploit")
        self.assertEqual(exploit.vulnerability_type, "reentrancy")
        self.assertEqual(exploit.loss_usd, 1000000.0)


class TestPatternEffectiveness(unittest.TestCase):
    """Test PatternEffectiveness dataclass."""

    def test_pattern_creation(self):
        """Test creating pattern effectiveness tracker."""
        stats = PatternEffectiveness(
            pattern_id="reentrancy_001",
            pattern_name="Classic Reentrancy",
        )

        self.assertEqual(stats.pattern_id, "reentrancy_001")
        self.assertEqual(stats.total_uses, 0)
        self.assertFalse(stats.deprecated)

    def test_metrics_calculation(self):
        """Test effectiveness metrics calculation."""
        stats = PatternEffectiveness(
            pattern_id="test",
            pattern_name="Test Pattern",
            true_positives=80,
            false_positives=20,
            false_negatives=10,
        )

        stats.update_metrics()

        # Precision = TP / (TP + FP) = 80 / 100 = 0.8
        self.assertAlmostEqual(stats.precision, 0.8)

        # Recall = TP / (TP + FN) = 80 / 90 = 0.888...
        self.assertAlmostEqual(stats.recall, 80/90, places=3)

        # F1 = 2 * (P * R) / (P + R)
        expected_f1 = 2 * (0.8 * (80/90)) / (0.8 + (80/90))
        self.assertAlmostEqual(stats.f1_score, expected_f1, places=3)

    def test_perfect_precision(self):
        """Test pattern with perfect precision."""
        stats = PatternEffectiveness(
            pattern_id="perfect",
            pattern_name="Perfect Pattern",
            true_positives=100,
            false_positives=0,
            false_negatives=5,
        )

        stats.update_metrics()

        self.assertEqual(stats.precision, 1.0)
        self.assertAlmostEqual(stats.recall, 100/105, places=3)


class TestEcosystemStats(unittest.TestCase):
    """Test EcosystemStats dataclass."""

    def test_stats_creation(self):
        """Test creating ecosystem statistics."""
        stats = EcosystemStats(
            total_exploits=100,
            total_loss_usd=50000000.0,
            exploits_by_type={"reentrancy": 30, "access_control": 25},
            patterns_active=15,
        )

        self.assertEqual(stats.total_exploits, 100)
        self.assertEqual(stats.total_loss_usd, 50000000.0)
        self.assertEqual(stats.exploits_by_type["reentrancy"], 30)


class TestEcosystemLearner(unittest.TestCase):
    """Test EcosystemLearner."""

    def setUp(self):
        """Set up test learner."""
        self.learner = EcosystemLearner()

    def test_import_custom_exploit(self):
        """Test manually importing an exploit."""
        exploit = self.learner.import_custom_exploit(
            name="Test Hack",
            date="2024-01-15",
            protocol="Test Protocol",
            vulnerability_type="reentrancy",
            loss_usd=1000000.0,
        )

        self.assertEqual(len(self.learner.exploits), 1)
        self.assertIn("custom_0", self.learner.exploits)
        self.assertEqual(exploit.name, "Test Hack")

    def test_import_from_solodit_csv(self):
        """Test importing from Solodit CSV format."""
        # Create temporary CSV file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=[
                'id', 'name', 'date', 'protocol', 'vulnerability_type', 'loss_usd', 'attack_vector', 'links'
            ])
            writer.writeheader()
            writer.writerow({
                'id': '001',
                'name': 'Uniswap Exploit',
                'date': '2024-01-15',
                'protocol': 'Uniswap',
                'vulnerability_type': 'reentrancy',
                'loss_usd': '10000000',
                'attack_vector': 'flash loan',
                'links': 'https://example.com;https://example2.com'
            })
            writer.writerow({
                'id': '002',
                'name': 'Aave Exploit',
                'date': '2024-02-20',
                'protocol': 'Aave',
                'vulnerability_type': 'oracle_manipulation',
                'loss_usd': '5000000',
                'attack_vector': 'price manipulation',
                'links': ''
            })
            temp_path = Path(f.name)

        try:
            imported = self.learner.import_from_solodit(temp_path)

            self.assertEqual(imported, 2)
            self.assertEqual(len(self.learner.exploits), 2)

            # Check first exploit
            exploit1 = self.learner.exploits["solodit_001"]
            self.assertEqual(exploit1.name, "Uniswap Exploit")
            self.assertEqual(exploit1.protocol, "Uniswap")
            self.assertEqual(exploit1.vulnerability_type, "reentrancy")
            self.assertEqual(exploit1.loss_usd, 10000000.0)
            self.assertEqual(len(exploit1.links), 2)
            self.assertEqual(exploit1.source, "solodit")

        finally:
            temp_path.unlink()

    def test_import_from_rekt_json(self):
        """Test importing from Rekt JSON format."""
        # Create temporary JSON file
        data = [
            {
                "id": "rekt_001",
                "name": "Protocol X Hack",
                "date": "2024-03-10",
                "protocol": "Protocol X",
                "loss_usd": 15000000,
                "category": "reentrancy",
                "description": "Classic reentrancy attack",
                "url": "https://rekt.news/protocol-x"
            },
            {
                "id": "rekt_002",
                "name": "Protocol Y Hack",
                "date": "2024-04-05",
                "protocol": "Protocol Y",
                "loss_usd": 8000000,
                "category": "access_control",
                "description": "Weak access control",
            }
        ]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(data, f)
            temp_path = Path(f.name)

        try:
            imported = self.learner.import_from_rekt(temp_path)

            self.assertEqual(imported, 2)
            self.assertEqual(len(self.learner.exploits), 2)

            # Check first exploit
            exploit1 = self.learner.exploits["rekt_rekt_001"]
            self.assertEqual(exploit1.name, "Protocol X Hack")
            self.assertEqual(exploit1.vulnerability_type, "reentrancy")
            self.assertEqual(exploit1.root_cause, "Classic reentrancy attack")
            self.assertEqual(exploit1.source, "rekt")

        finally:
            temp_path.unlink()

    def test_record_pattern_use_true_positive(self):
        """Test recording true positive pattern usage."""
        self.learner.record_pattern_use(
            pattern_id="reentrancy_001",
            pattern_name="Classic Reentrancy",
            is_true_positive=True,
        )

        stats = self.learner.get_pattern_stats("reentrancy_001")

        self.assertIsNotNone(stats)
        self.assertEqual(stats.total_uses, 1)
        self.assertEqual(stats.true_positives, 1)
        self.assertEqual(stats.false_positives, 0)
        self.assertEqual(stats.precision, 1.0)

    def test_record_pattern_use_false_positive(self):
        """Test recording false positive pattern usage."""
        self.learner.record_pattern_use(
            pattern_id="access_001",
            pattern_name="Weak Access Control",
            is_true_positive=False,
        )

        stats = self.learner.get_pattern_stats("access_001")

        self.assertEqual(stats.total_uses, 1)
        self.assertEqual(stats.true_positives, 0)
        self.assertEqual(stats.false_positives, 1)
        self.assertEqual(stats.precision, 0.0)

    def test_record_pattern_miss(self):
        """Test recording pattern false negative."""
        self.learner.record_pattern_miss(
            pattern_id="dos_001",
            pattern_name="DoS Pattern",
        )

        stats = self.learner.get_pattern_stats("dos_001")

        self.assertEqual(stats.false_negatives, 1)
        self.assertEqual(stats.recall, 0.0)

    def test_pattern_metrics_update(self):
        """Test that pattern metrics update correctly over time."""
        # Record multiple uses
        for _ in range(8):
            self.learner.record_pattern_use("test_pattern", "Test", True)

        for _ in range(2):
            self.learner.record_pattern_use("test_pattern", "Test", False)

        stats = self.learner.get_pattern_stats("test_pattern")

        self.assertEqual(stats.total_uses, 10)
        self.assertEqual(stats.true_positives, 8)
        self.assertEqual(stats.false_positives, 2)
        self.assertEqual(stats.precision, 0.8)

    def test_deprecate_pattern(self):
        """Test deprecating a pattern."""
        self.learner.record_pattern_use("old_pattern", "Old Pattern", True)

        self.learner.deprecate_pattern(
            pattern_id="old_pattern",
            reason="Replaced by improved pattern",
        )

        stats = self.learner.get_pattern_stats("old_pattern")

        self.assertTrue(stats.deprecated)
        self.assertEqual(stats.deprecation_reason, "Replaced by improved pattern")

    def test_get_low_performing_patterns(self):
        """Test finding low-performing patterns."""
        # Create high precision pattern
        for _ in range(15):
            self.learner.record_pattern_use("good_pattern", "Good", True)

        # Create low precision pattern
        for _ in range(5):
            self.learner.record_pattern_use("bad_pattern", "Bad", True)
        for _ in range(10):
            self.learner.record_pattern_use("bad_pattern", "Bad", False)

        low_performers = self.learner.get_low_performing_patterns(
            min_uses=10,
            max_precision=0.5,
        )

        self.assertEqual(len(low_performers), 1)
        self.assertEqual(low_performers[0].pattern_id, "bad_pattern")
        self.assertLess(low_performers[0].precision, 0.5)

    def test_get_high_performing_patterns(self):
        """Test finding high-performing patterns."""
        # Create excellent pattern (high precision and recall)
        for _ in range(18):
            self.learner.record_pattern_use("excellent", "Excellent", True)
        for _ in range(2):
            self.learner.record_pattern_use("excellent", "Excellent", False)
        self.learner.record_pattern_miss("excellent", "Excellent")

        high_performers = self.learner.get_high_performing_patterns(
            min_uses=10,
            min_precision=0.8,
            min_recall=0.7,
        )

        self.assertGreater(len(high_performers), 0)
        self.assertEqual(high_performers[0].pattern_id, "excellent")
        self.assertGreater(high_performers[0].precision, 0.8)
        self.assertGreater(high_performers[0].recall, 0.7)

    def test_get_ecosystem_stats(self):
        """Test getting aggregate ecosystem statistics."""
        # Add some exploits
        self.learner.import_custom_exploit("Exploit 1", "2024-01-01", "Protocol A", "reentrancy", 1000000)
        self.learner.import_custom_exploit("Exploit 2", "2024-01-02", "Protocol A", "reentrancy", 2000000)
        self.learner.import_custom_exploit("Exploit 3", "2024-01-03", "Protocol B", "access_control", 500000)

        # Add some patterns
        self.learner.record_pattern_use("p1", "Pattern 1", True)
        self.learner.record_pattern_use("p2", "Pattern 2", True)
        self.learner.deprecate_pattern("p1", "deprecated")

        stats = self.learner.get_ecosystem_stats()

        self.assertEqual(stats.total_exploits, 3)
        self.assertEqual(stats.total_loss_usd, 3500000.0)
        self.assertEqual(stats.exploits_by_type["reentrancy"], 2)
        self.assertEqual(stats.exploits_by_type["access_control"], 1)
        self.assertEqual(stats.exploits_by_protocol["Protocol A"], 2)
        self.assertEqual(stats.patterns_active, 1)
        self.assertEqual(stats.patterns_deprecated, 1)

    def test_generate_report(self):
        """Test generating ecosystem report."""
        # Add data
        self.learner.import_custom_exploit("Test Exploit", "2024-01-01", "Test Protocol", "reentrancy", 1000000)

        for _ in range(15):
            self.learner.record_pattern_use("good_pattern", "Good Pattern", True)
        for _ in range(2):
            self.learner.record_pattern_use("good_pattern", "Good Pattern", False)

        report = self.learner.generate_report()

        self.assertIn("Ecosystem Learning Report", report)
        self.assertIn("Total Exploits", report)
        self.assertIn("1", report)
        self.assertIn("reentrancy", report)
        self.assertIn("Good Pattern", report)

    def test_export_statistics(self):
        """Test exporting statistics to JSON."""
        # Add data
        self.learner.import_custom_exploit("Exploit", "2024-01-01", "Protocol", "reentrancy", 1000000)
        self.learner.record_pattern_use("pattern_1", "Pattern 1", True)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = Path(f.name)

        try:
            self.learner.export_statistics(temp_path)

            with open(temp_path) as f:
                data = json.load(f)

            self.assertIn("stats", data)
            self.assertIn("patterns", data)
            self.assertEqual(data["stats"]["total_exploits"], 1)
            self.assertIn("pattern_1", data["patterns"])

        finally:
            temp_path.unlink()


class TestSuccessCriteria(unittest.TestCase):
    """Test success criteria from P4-T3 spec."""

    def setUp(self):
        """Set up test learner."""
        self.learner = EcosystemLearner()

    def test_solodit_import_working(self):
        """✓ Solodit import working."""
        # Create test CSV
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=['id', 'name', 'date', 'protocol', 'vulnerability_type', 'loss_usd', 'attack_vector', 'links'])
            writer.writeheader()
            writer.writerow({
                'id': '001',
                'name': 'Test Exploit',
                'date': '2024-01-01',
                'protocol': 'Test',
                'vulnerability_type': 'reentrancy',
                'loss_usd': '1000000',
                'attack_vector': 'flash loan',
                'links': ''
            })
            temp_path = Path(f.name)

        try:
            imported = self.learner.import_from_solodit(temp_path)

            self.assertGreater(imported, 0)
            self.assertGreater(len(self.learner.exploits), 0)

        finally:
            temp_path.unlink()

    def test_pattern_extraction_from_audits(self):
        """✓ Pattern extraction from audits (manual import)."""
        # Simulate pattern extraction by importing custom exploit
        exploit = self.learner.import_custom_exploit(
            name="Audit Finding: Reentrancy in withdraw()",
            date="2024-01-15",
            protocol="Audited Protocol",
            vulnerability_type="reentrancy",
            loss_usd=0.0,  # From audit, not exploit
            vulnerable_function="withdraw",
            root_cause="External call before state update",
        )

        # Mark as having extracted pattern
        exploit.extracted_pattern_id = "reentrancy_001"
        self.learner.exploits[exploit.id] = exploit

        stats = self.learner.get_ecosystem_stats()
        self.assertEqual(stats.patterns_extracted, 1)

    def test_effectiveness_tracking(self):
        """✓ Effectiveness tracking."""
        # Record usage
        for _ in range(10):
            self.learner.record_pattern_use("test_pattern", "Test", True)
        for _ in range(2):
            self.learner.record_pattern_use("test_pattern", "Test", False)

        stats = self.learner.get_pattern_stats("test_pattern")

        # Should track all metrics
        self.assertIsNotNone(stats)
        self.assertEqual(stats.total_uses, 12)
        self.assertGreater(stats.precision, 0)
        self.assertIsNotNone(stats.first_seen)
        self.assertIsNotNone(stats.last_used)


if __name__ == "__main__":
    unittest.main()
