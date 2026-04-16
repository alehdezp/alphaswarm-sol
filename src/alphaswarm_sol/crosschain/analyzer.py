"""
Cross-Chain Vulnerability Analyzer

High-level interface for cross-chain vulnerability analysis.
Combines ontology, translators, and database for comprehensive analysis.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Set
from datetime import datetime
import logging

from alphaswarm_sol.crosschain.ontology import (
    Chain,
    AbstractOperation,
    OperationType,
    AbstractVulnerabilitySignature,
    InvariantType,
    UNIVERSAL_SIGNATURES,
)
from alphaswarm_sol.crosschain.translators import (
    TranslatorRegistry,
    TRANSLATOR_REGISTRY,
    ChainTranslator,
)
from alphaswarm_sol.crosschain.database import (
    CrossChainExploitDatabase,
    CrossChainMatch,
    MatchConfidence,
    CROSS_CHAIN_DATABASE,
)

logger = logging.getLogger(__name__)


@dataclass
class PortedVulnerability:
    """
    A vulnerability ported from another chain.
    """
    original_exploit: str               # Original exploit name
    original_chain: Chain               # Source chain
    target_chain: Chain                 # Target chain
    confidence: MatchConfidence
    similarity: float

    # Ported pattern for target chain
    target_pattern: Dict[str, Any]

    # Abstract representation
    behavioral_signature: str
    invariant_violated: InvariantType

    # Recommendations
    severity: str
    priority: str
    mitigation: str
    description: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "original_exploit": self.original_exploit,
            "original_chain": self.original_chain.value,
            "target_chain": self.target_chain.value,
            "confidence": self.confidence.value,
            "similarity": self.similarity,
            "behavioral_signature": self.behavioral_signature,
            "invariant_violated": self.invariant_violated.value,
            "severity": self.severity,
            "priority": self.priority,
            "mitigation": self.mitigation,
        }


@dataclass
class CrossChainAnalysisResult:
    """
    Result of cross-chain vulnerability analysis.
    """
    target_chain: Chain
    target_operations: List[str]

    # Matches found
    cross_chain_matches: List[PortedVulnerability]
    universal_signature_matches: List[AbstractVulnerabilitySignature]

    # Summary
    total_matches: int
    critical_matches: int
    high_matches: int

    # Analysis metadata
    analysis_timestamp: str
    analysis_duration_ms: float

    def get_critical_findings(self) -> List[PortedVulnerability]:
        """Get critical priority findings."""
        return [m for m in self.cross_chain_matches if m.priority == "critical"]

    def get_high_findings(self) -> List[PortedVulnerability]:
        """Get high priority findings."""
        return [m for m in self.cross_chain_matches if m.priority in ("critical", "high")]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "target_chain": self.target_chain.value,
            "total_matches": self.total_matches,
            "critical_matches": self.critical_matches,
            "high_matches": self.high_matches,
            "cross_chain_matches": [m.to_dict() for m in self.cross_chain_matches],
            "universal_matches": [
                s.vuln_name for s in self.universal_signature_matches
            ],
            "analysis_timestamp": self.analysis_timestamp,
            "analysis_duration_ms": self.analysis_duration_ms,
        }

    def get_summary(self) -> str:
        """Get human-readable summary."""
        lines = [
            f"Cross-Chain Vulnerability Analysis",
            f"=" * 40,
            f"Target Chain: {self.target_chain.value}",
            f"Total Matches: {self.total_matches}",
            f"  - Critical: {self.critical_matches}",
            f"  - High: {self.high_matches}",
            "",
        ]

        if self.cross_chain_matches:
            lines.append("Cross-Chain Matches:")
            for m in self.cross_chain_matches[:5]:  # Top 5
                lines.append(
                    f"  [{m.confidence.value}] {m.original_exploit} "
                    f"({m.original_chain.value}) - {m.severity}"
                )

        if self.universal_signature_matches:
            lines.append("")
            lines.append("Universal Pattern Matches:")
            for s in self.universal_signature_matches:
                lines.append(f"  - {s.vuln_name}: {s.description}")

        return "\n".join(lines)


class CrossChainAnalyzer:
    """
    High-level analyzer for cross-chain vulnerability transfer.

    Main entry point for cross-chain analysis capabilities.
    """

    def __init__(
        self,
        database: Optional[CrossChainExploitDatabase] = None,
        translator_registry: Optional[TranslatorRegistry] = None,
    ):
        self.database = database or CROSS_CHAIN_DATABASE
        self.translator = translator_registry or TRANSLATOR_REGISTRY

    def analyze_operations(
        self,
        chain: Chain,
        operations: List[str],
        min_confidence: MatchConfidence = MatchConfidence.MEDIUM,
    ) -> CrossChainAnalysisResult:
        """
        Analyze operations for cross-chain vulnerability matches.

        Args:
            chain: Target chain being analyzed
            operations: List of chain-specific operations
            min_confidence: Minimum confidence for matches

        Returns:
            CrossChainAnalysisResult with findings
        """
        import time
        start_time = time.time()

        # Find cross-chain matches
        matches = self.database.find_cross_chain_matches(
            chain, operations, min_confidence
        )

        # Convert to ported vulnerabilities
        ported = []
        for match in matches:
            ported.append(PortedVulnerability(
                original_exploit=match.source_exploit.name,
                original_chain=match.source_exploit.chain,
                target_chain=chain,
                confidence=match.confidence,
                similarity=match.similarity_score,
                target_pattern=match.target_pattern,
                behavioral_signature=match.source_exploit.abstract_signature.get_behavioral_signature(),
                invariant_violated=match.source_exploit.abstract_signature.invariant_violated,
                severity=match.source_exploit.abstract_signature.severity,
                priority=match.priority,
                mitigation=match.mitigation,
                description=match.source_exploit.description,
            ))

        # Check against universal signatures
        abstract_ops = self.translator.translate_to_abstract(chain, operations)
        universal_matches = self._check_universal_signatures(abstract_ops)

        # Calculate summary
        critical = len([p for p in ported if p.priority == "critical"])
        high = len([p for p in ported if p.priority in ("critical", "high")])

        duration = (time.time() - start_time) * 1000

        return CrossChainAnalysisResult(
            target_chain=chain,
            target_operations=operations,
            cross_chain_matches=ported,
            universal_signature_matches=universal_matches,
            total_matches=len(ported) + len(universal_matches),
            critical_matches=critical,
            high_matches=high,
            analysis_timestamp=datetime.now().isoformat(),
            analysis_duration_ms=duration,
        )

    def analyze_source_code(
        self,
        chain: Chain,
        source_code: str,
        min_confidence: MatchConfidence = MatchConfidence.MEDIUM,
    ) -> CrossChainAnalysisResult:
        """
        Analyze source code for cross-chain vulnerability matches.

        Args:
            chain: Target chain
            source_code: Source code in chain's language
            min_confidence: Minimum confidence for matches

        Returns:
            CrossChainAnalysisResult with findings
        """
        # Get translator
        translator = self.translator.get(chain)
        if not translator:
            raise ValueError(f"No translator for chain: {chain}")

        # Parse source to operations
        operations = translator.parse_source(source_code)

        # Analyze operations
        return self.analyze_operations(chain, operations, min_confidence)

    def port_vulnerability(
        self,
        exploit_id: str,
        target_chain: Chain,
    ) -> Optional[PortedVulnerability]:
        """
        Port a specific vulnerability to a target chain.

        Args:
            exploit_id: ID of exploit to port
            target_chain: Chain to port to

        Returns:
            PortedVulnerability or None if not possible
        """
        exploit = self.database.exploits.get(exploit_id)
        if not exploit:
            return None

        if exploit.chain == target_chain:
            return None

        # Get target pattern
        target_pattern = self.database.transfer_vulnerability(exploit_id, target_chain)
        if not target_pattern:
            return None

        return PortedVulnerability(
            original_exploit=exploit.name,
            original_chain=exploit.chain,
            target_chain=target_chain,
            confidence=MatchConfidence.HIGH,  # Direct port
            similarity=1.0,
            target_pattern=target_pattern,
            behavioral_signature=exploit.abstract_signature.get_behavioral_signature(),
            invariant_violated=exploit.abstract_signature.invariant_violated,
            severity=exploit.abstract_signature.severity,
            priority="high",
            mitigation=self.database._generate_mitigation(exploit),
            description=f"Ported from {exploit.chain.value}: {exploit.description}",
        )

    def get_chain_statistics(self, chain: Chain) -> Dict[str, Any]:
        """Get vulnerability statistics for a chain."""
        exploits = self.database.find_by_category(chain=chain, category="")

        if not exploits:
            # Get all for chain
            exploit_ids = self.database._by_chain.get(chain, [])
            exploits = [
                self.database.exploits[id]
                for id in exploit_ids
                if id in self.database.exploits
            ]

        categories = {}
        severities = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        total_loss = 0.0

        for e in exploits:
            cat = e.vulnerability_type
            categories[cat] = categories.get(cat, 0) + 1
            severities[e.abstract_signature.severity] = \
                severities.get(e.abstract_signature.severity, 0) + 1
            total_loss += e.loss_usd

        return {
            "chain": chain.value,
            "total_exploits": len(exploits),
            "by_category": categories,
            "by_severity": severities,
            "total_loss_usd": total_loss,
        }

    def compare_chains(
        self,
        chain1: Chain,
        chain2: Chain,
    ) -> Dict[str, Any]:
        """
        Compare vulnerability profiles between two chains.

        Useful for understanding which vulnerabilities from one chain
        might appear on another.
        """
        stats1 = self.get_chain_statistics(chain1)
        stats2 = self.get_chain_statistics(chain2)

        # Find common vulnerability types
        cats1 = set(stats1["by_category"].keys())
        cats2 = set(stats2["by_category"].keys())

        common = cats1.intersection(cats2)
        unique_to_1 = cats1 - cats2
        unique_to_2 = cats2 - cats1

        return {
            "chain1": chain1.value,
            "chain2": chain2.value,
            "common_vulnerability_types": list(common),
            "unique_to_chain1": list(unique_to_1),
            "unique_to_chain2": list(unique_to_2),
            "chain1_stats": stats1,
            "chain2_stats": stats2,
            "transfer_opportunities": len(common),
        }

    def _check_universal_signatures(
        self,
        abstract_ops: List[AbstractOperation],
    ) -> List[AbstractVulnerabilitySignature]:
        """Check operations against universal vulnerability signatures."""
        matches = []

        for sig_name, signature in UNIVERSAL_SIGNATURES.items():
            if signature.matches_signature(abstract_ops):
                matches.append(signature)

        return matches

    def generate_detection_pattern(
        self,
        exploit_id: str,
        target_chain: Chain,
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a detection pattern for a vulnerability on target chain.

        This creates a complete pattern that can be used with the chain's
        analysis tools.
        """
        exploit = self.database.exploits.get(exploit_id)
        if not exploit:
            return None

        # Translate to target chain
        pattern = self.translator.translate_from_abstract(
            target_chain,
            exploit.abstract_signature.abstract_operations
        )

        # Add full metadata
        return {
            "id": f"{exploit_id}-{target_chain.value}",
            "name": f"{exploit.name} ({target_chain.value})",
            "description": exploit.description,
            "severity": exploit.abstract_signature.severity,
            "cwe_ids": exploit.abstract_signature.cwe_ids,
            "original_exploit": {
                "id": exploit_id,
                "chain": exploit.chain.value,
                "loss_usd": exploit.loss_usd,
            },
            "match": pattern,
        }


# Global analyzer instance
CROSS_CHAIN_ANALYZER = CrossChainAnalyzer()
