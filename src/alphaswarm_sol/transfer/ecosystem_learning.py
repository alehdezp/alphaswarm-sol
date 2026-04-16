"""
Phase 4: Ecosystem Learning

Implements continuous learning from the Solidity ecosystem - new exploits,
audit reports, and CVEs. Keeps vulnerability knowledge up-to-date.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from pathlib import Path
from datetime import datetime
import json
import csv


@dataclass
class ExploitRecord:
    """Record of a real-world exploit."""
    id: str
    name: str
    date: datetime
    protocol: str
    vulnerability_type: str
    loss_usd: float = 0.0

    # Technical details
    attack_vector: Optional[str] = None
    vulnerable_function: Optional[str] = None
    root_cause: Optional[str] = None

    # References
    source: str = "unknown"  # "solodit", "rekt", "manual"
    links: List[str] = field(default_factory=list)

    # Pattern extraction
    extracted_pattern_id: Optional[str] = None


@dataclass
class PatternEffectiveness:
    """Tracks pattern detection effectiveness over time."""
    pattern_id: str
    pattern_name: str

    # Usage statistics
    total_uses: int = 0
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0

    # Effectiveness metrics
    precision: float = 0.0  # TP / (TP + FP)
    recall: float = 0.0     # TP / (TP + FN)
    f1_score: float = 0.0   # 2 * (precision * recall) / (precision + recall)

    # Temporal tracking
    first_seen: Optional[datetime] = None
    last_used: Optional[datetime] = None
    deprecated: bool = False
    deprecation_reason: Optional[str] = None

    def update_metrics(self):
        """Recalculate effectiveness metrics."""
        if self.true_positives + self.false_positives > 0:
            self.precision = self.true_positives / (self.true_positives + self.false_positives)

        if self.true_positives + self.false_negatives > 0:
            self.recall = self.true_positives / (self.true_positives + self.false_negatives)

        if self.precision + self.recall > 0:
            self.f1_score = 2 * (self.precision * self.recall) / (self.precision + self.recall)


@dataclass
class EcosystemStats:
    """Aggregate statistics about the ecosystem."""
    total_exploits: int = 0
    total_loss_usd: float = 0.0
    exploits_by_type: Dict[str, int] = field(default_factory=dict)
    exploits_by_protocol: Dict[str, int] = field(default_factory=dict)
    patterns_extracted: int = 0
    patterns_active: int = 0
    patterns_deprecated: int = 0


class EcosystemLearner:
    """
    Learns from the Solidity ecosystem.

    Imports exploits from public databases, extracts patterns from audit reports,
    and tracks pattern effectiveness over time.
    """

    def __init__(self):
        self.exploits: Dict[str, ExploitRecord] = {}
        self.pattern_effectiveness: Dict[str, PatternEffectiveness] = {}

    def import_from_solodit(self, data_path: Path) -> int:
        """
        Import exploits from Solodit export.

        Solodit format (CSV):
        id,name,date,protocol,vulnerability_type,loss_usd,attack_vector,links

        Args:
            data_path: Path to Solodit CSV export

        Returns:
            Number of exploits imported
        """
        if not data_path.exists():
            raise FileNotFoundError(f"Solodit data not found: {data_path}")

        imported = 0

        with open(data_path, 'r') as f:
            reader = csv.DictReader(f)

            for row in reader:
                exploit = ExploitRecord(
                    id=f"solodit_{row.get('id', '')}",
                    name=row.get('name', 'Unknown'),
                    date=self._parse_date(row.get('date', '')),
                    protocol=row.get('protocol', 'Unknown'),
                    vulnerability_type=row.get('vulnerability_type', 'Unknown'),
                    loss_usd=float(row.get('loss_usd', 0)),
                    attack_vector=row.get('attack_vector'),
                    source="solodit",
                    links=row.get('links', '').split(';') if row.get('links') else [],
                )

                self.exploits[exploit.id] = exploit
                imported += 1

        return imported

    def import_from_rekt(self, data_path: Path) -> int:
        """
        Import from Rekt.news database.

        Rekt format (JSON):
        [
            {
                "id": "...",
                "name": "Protocol X Hack",
                "date": "2024-01-15",
                "protocol": "Protocol X",
                "loss_usd": 10000000,
                "category": "reentrancy",
                "description": "..."
            }
        ]

        Args:
            data_path: Path to Rekt JSON export

        Returns:
            Number of exploits imported
        """
        if not data_path.exists():
            raise FileNotFoundError(f"Rekt data not found: {data_path}")

        with open(data_path, 'r') as f:
            data = json.load(f)

        imported = 0

        for item in data:
            exploit = ExploitRecord(
                id=f"rekt_{item.get('id', '')}",
                name=item.get('name', 'Unknown'),
                date=self._parse_date(item.get('date', '')),
                protocol=item.get('protocol', 'Unknown'),
                vulnerability_type=item.get('category', 'Unknown'),
                loss_usd=float(item.get('loss_usd', 0)),
                root_cause=item.get('description'),
                source="rekt",
                links=[item.get('url')] if item.get('url') else [],
            )

            self.exploits[exploit.id] = exploit
            imported += 1

        return imported

    def import_custom_exploit(
        self,
        name: str,
        date: str,
        protocol: str,
        vulnerability_type: str,
        loss_usd: float = 0.0,
        **kwargs
    ) -> ExploitRecord:
        """
        Manually import a custom exploit record.

        Useful for adding exploits from audit reports or custom sources.
        """
        exploit_id = f"custom_{len([e for e in self.exploits.values() if e.source == 'manual'])}"

        exploit = ExploitRecord(
            id=exploit_id,
            name=name,
            date=self._parse_date(date),
            protocol=protocol,
            vulnerability_type=vulnerability_type,
            loss_usd=loss_usd,
            source="manual",
            **{k: v for k, v in kwargs.items() if hasattr(ExploitRecord, k)}
        )

        self.exploits[exploit.id] = exploit
        return exploit

    def record_pattern_use(
        self,
        pattern_id: str,
        pattern_name: str,
        is_true_positive: bool,
    ):
        """
        Record usage of a pattern.

        Args:
            pattern_id: Pattern identifier
            pattern_name: Human-readable pattern name
            is_true_positive: Whether detection was accurate
        """
        if pattern_id not in self.pattern_effectiveness:
            self.pattern_effectiveness[pattern_id] = PatternEffectiveness(
                pattern_id=pattern_id,
                pattern_name=pattern_name,
                first_seen=datetime.now(),
            )

        stats = self.pattern_effectiveness[pattern_id]
        stats.total_uses += 1
        stats.last_used = datetime.now()

        if is_true_positive:
            stats.true_positives += 1
        else:
            stats.false_positives += 1

        stats.update_metrics()

    def record_pattern_miss(
        self,
        pattern_id: str,
        pattern_name: str,
    ):
        """
        Record that pattern failed to detect a known vulnerability.

        Args:
            pattern_id: Pattern identifier
            pattern_name: Human-readable pattern name
        """
        if pattern_id not in self.pattern_effectiveness:
            self.pattern_effectiveness[pattern_id] = PatternEffectiveness(
                pattern_id=pattern_id,
                pattern_name=pattern_name,
                first_seen=datetime.now(),
            )

        stats = self.pattern_effectiveness[pattern_id]
        stats.false_negatives += 1
        stats.update_metrics()

    def get_pattern_stats(self, pattern_id: str) -> Optional[PatternEffectiveness]:
        """Get effectiveness statistics for a pattern."""
        return self.pattern_effectiveness.get(pattern_id)

    def deprecate_pattern(
        self,
        pattern_id: str,
        reason: str,
    ):
        """
        Mark a pattern as deprecated.

        Deprecated patterns are kept for historical tracking but
        not used in new analyses.
        """
        if pattern_id in self.pattern_effectiveness:
            stats = self.pattern_effectiveness[pattern_id]
            stats.deprecated = True
            stats.deprecation_reason = reason

    def get_low_performing_patterns(
        self,
        min_uses: int = 10,
        max_precision: float = 0.5,
    ) -> List[PatternEffectiveness]:
        """
        Find patterns with poor performance.

        Useful for identifying patterns that need improvement or deprecation.
        """
        low_performers = []

        for stats in self.pattern_effectiveness.values():
            if stats.deprecated:
                continue

            if stats.total_uses >= min_uses and stats.precision <= max_precision:
                low_performers.append(stats)

        return sorted(low_performers, key=lambda s: s.precision)

    def get_high_performing_patterns(
        self,
        min_uses: int = 10,
        min_precision: float = 0.8,
        min_recall: float = 0.7,
    ) -> List[PatternEffectiveness]:
        """
        Find patterns with excellent performance.

        These are reliable patterns that can be trusted.
        """
        high_performers = []

        for stats in self.pattern_effectiveness.values():
            if stats.deprecated:
                continue

            if (stats.total_uses >= min_uses and
                stats.precision >= min_precision and
                stats.recall >= min_recall):
                high_performers.append(stats)

        return sorted(high_performers, key=lambda s: s.f1_score, reverse=True)

    def get_ecosystem_stats(self) -> EcosystemStats:
        """Get aggregate statistics about the ecosystem."""
        stats = EcosystemStats()

        stats.total_exploits = len(self.exploits)
        stats.total_loss_usd = sum(e.loss_usd for e in self.exploits.values())

        # Count by type
        for exploit in self.exploits.values():
            vuln_type = exploit.vulnerability_type
            stats.exploits_by_type[vuln_type] = stats.exploits_by_type.get(vuln_type, 0) + 1

            protocol = exploit.protocol
            stats.exploits_by_protocol[protocol] = stats.exploits_by_protocol.get(protocol, 0) + 1

        # Pattern statistics
        stats.patterns_extracted = len([e for e in self.exploits.values() if e.extracted_pattern_id])
        stats.patterns_active = len([p for p in self.pattern_effectiveness.values() if not p.deprecated])
        stats.patterns_deprecated = len([p for p in self.pattern_effectiveness.values() if p.deprecated])

        return stats

    def generate_report(self) -> str:
        """Generate ecosystem learning report."""
        stats = self.get_ecosystem_stats()

        lines = ["# Ecosystem Learning Report\n"]

        # Overall statistics
        lines.append("## Overall Statistics\n")
        lines.append(f"**Total Exploits**: {stats.total_exploits}")
        lines.append(f"**Total Loss**: ${stats.total_loss_usd:,.0f} USD")
        lines.append(f"**Patterns Active**: {stats.patterns_active}")
        lines.append(f"**Patterns Deprecated**: {stats.patterns_deprecated}")
        lines.append("")

        # Top vulnerability types
        if stats.exploits_by_type:
            lines.append("## Top Vulnerability Types\n")
            sorted_types = sorted(stats.exploits_by_type.items(), key=lambda x: x[1], reverse=True)
            for vuln_type, count in sorted_types[:10]:
                lines.append(f"- **{vuln_type}**: {count} exploit(s)")
            lines.append("")

        # Top affected protocols
        if stats.exploits_by_protocol:
            lines.append("## Most Affected Protocols\n")
            sorted_protocols = sorted(stats.exploits_by_protocol.items(), key=lambda x: x[1], reverse=True)
            for protocol, count in sorted_protocols[:10]:
                lines.append(f"- **{protocol}**: {count} exploit(s)")
            lines.append("")

        # High-performing patterns
        high_performers = self.get_high_performing_patterns(min_uses=5)
        if high_performers:
            lines.append("## High-Performing Patterns\n")
            for stats in high_performers[:10]:
                lines.append(f"### {stats.pattern_name}")
                lines.append(f"- **Precision**: {stats.precision:.1%}")
                lines.append(f"- **Recall**: {stats.recall:.1%}")
                lines.append(f"- **F1 Score**: {stats.f1_score:.1%}")
                lines.append(f"- **Uses**: {stats.total_uses}")
                lines.append("")

        # Low-performing patterns (candidates for deprecation)
        low_performers = self.get_low_performing_patterns(min_uses=5, max_precision=0.5)
        if low_performers:
            lines.append("## Low-Performing Patterns (Review Needed)\n")
            for stats in low_performers[:10]:
                lines.append(f"### {stats.pattern_name}")
                lines.append(f"- **Precision**: {stats.precision:.1%} ⚠️")
                lines.append(f"- **False Positives**: {stats.false_positives}")
                lines.append(f"- **Uses**: {stats.total_uses}")
                lines.append("")

        return "\n".join(lines)

    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string in various formats."""
        if not date_str:
            return datetime.now()

        # Try common formats
        formats = [
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%d-%m-%Y",
            "%d/%m/%Y",
            "%Y-%m-%d %H:%M:%S",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        # Fallback to now
        return datetime.now()

    def export_statistics(self, output_path: Path):
        """Export ecosystem statistics to JSON."""
        data = {
            "stats": {
                "total_exploits": len(self.exploits),
                "total_loss_usd": sum(e.loss_usd for e in self.exploits.values()),
                "by_type": {},
                "by_protocol": {},
            },
            "patterns": {},
        }

        # Aggregate by type
        for exploit in self.exploits.values():
            vuln_type = exploit.vulnerability_type
            data["stats"]["by_type"][vuln_type] = data["stats"]["by_type"].get(vuln_type, 0) + 1

            protocol = exploit.protocol
            data["stats"]["by_protocol"][protocol] = data["stats"]["by_protocol"].get(protocol, 0) + 1

        # Pattern effectiveness
        for pattern_id, stats in self.pattern_effectiveness.items():
            data["patterns"][pattern_id] = {
                "name": stats.pattern_name,
                "precision": stats.precision,
                "recall": stats.recall,
                "f1_score": stats.f1_score,
                "total_uses": stats.total_uses,
                "deprecated": stats.deprecated,
            }

        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
