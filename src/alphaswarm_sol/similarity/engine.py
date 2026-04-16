"""
Similarity Engine

High-level interface for semantic code similarity analysis.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Set
from datetime import datetime
import logging

from .fingerprint import (
    SemanticFingerprint,
    FingerprintGenerator,
    FingerprintConfig,
)
from .similarity import (
    SimilarityCalculator,
    SimilarityResult,
    SimilarityConfig,
)
from .index import (
    ContractIndex,
    IndexEntry,
    IndexConfig,
    SearchConfig,
    SearchResult,
)
from .matcher import (
    PatternMatcher,
    MatchResult,
    CloneDetector,
    Clone,
    CloneType,
)

logger = logging.getLogger(__name__)


@dataclass
class SimilarContract:
    """A similar contract found during analysis."""
    contract_name: str
    similarity_score: float
    matching_functions: List[str] = field(default_factory=list)
    shared_operations: List[str] = field(default_factory=list)
    clone_type: Optional[CloneType] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contract": self.contract_name,
            "similarity": round(self.similarity_score, 3),
            "matching_functions": len(self.matching_functions),
            "shared_operations": len(self.shared_operations),
            "clone_type": self.clone_type.value if self.clone_type else None,
        }


@dataclass
class VulnerabilityCorrelation:
    """Correlation between contracts sharing vulnerability patterns."""
    vulnerability_type: str
    severity: str
    affected_contracts: List[str] = field(default_factory=list)
    affected_functions: List[str] = field(default_factory=list)
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "vulnerability": self.vulnerability_type,
            "severity": self.severity,
            "affected_contracts": self.affected_contracts,
            "affected_functions": self.affected_functions,
            "confidence": round(self.confidence, 3),
        }


@dataclass
class AnalysisResult:
    """Result of similarity analysis."""
    contract_name: str
    analysis_time_ms: int = 0

    # Fingerprints
    fingerprints: List[SemanticFingerprint] = field(default_factory=list)

    # Similar contracts
    similar_contracts: List[SimilarContract] = field(default_factory=list)

    # Clones detected
    clones: List[Clone] = field(default_factory=list)

    # Pattern matches
    pattern_matches: List[MatchResult] = field(default_factory=list)

    # Vulnerability correlations
    vulnerability_correlations: List[VulnerabilityCorrelation] = field(default_factory=list)

    def get_high_risk_correlations(self) -> List[VulnerabilityCorrelation]:
        """Get high severity vulnerability correlations."""
        return [c for c in self.vulnerability_correlations if c.severity in ["critical", "high"]]

    def get_exact_clones(self) -> List[Clone]:
        """Get exact code clones."""
        return [c for c in self.clones if c.clone_type in [CloneType.TYPE_1, CloneType.TYPE_2]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contract": self.contract_name,
            "analysis_time_ms": self.analysis_time_ms,
            "num_fingerprints": len(self.fingerprints),
            "similar_contracts": [s.to_dict() for s in self.similar_contracts],
            "clones": [c.to_dict() for c in self.clones],
            "pattern_matches": [m.to_dict() for m in self.pattern_matches],
            "vulnerability_correlations": [v.to_dict() for v in self.vulnerability_correlations],
        }

    def summary(self) -> str:
        """Get human-readable summary."""
        lines = [
            f"=== Similarity Analysis: {self.contract_name} ===",
            f"Fingerprints: {len(self.fingerprints)}",
            f"Similar contracts: {len(self.similar_contracts)}",
            f"Code clones: {len(self.clones)}",
            f"Pattern matches: {len(self.pattern_matches)}",
            f"Vulnerability correlations: {len(self.vulnerability_correlations)}",
        ]

        if self.similar_contracts:
            lines.append("\nTop similar contracts:")
            for sc in self.similar_contracts[:3]:
                lines.append(f"  - {sc.contract_name}: {sc.similarity_score:.1%}")

        if self.pattern_matches:
            lines.append("\nPattern matches:")
            for pm in self.pattern_matches[:3]:
                lines.append(f"  - {pm.pattern_id}: {pm.target_function} ({pm.severity})")

        high_risk = self.get_high_risk_correlations()
        if high_risk:
            lines.append("\n⚠️  High-risk vulnerability correlations:")
            for vr in high_risk:
                lines.append(f"  - {vr.vulnerability_type}: {len(vr.affected_contracts)} contracts")

        return "\n".join(lines)


@dataclass
class EngineConfig:
    """Configuration for similarity engine."""
    # Fingerprint config
    fingerprint_config: Optional[FingerprintConfig] = None

    # Similarity config
    similarity_config: Optional[SimilarityConfig] = None

    # Index config
    index_config: Optional[IndexConfig] = None

    # Thresholds
    clone_threshold: float = 0.7
    similar_contract_threshold: float = 0.5
    pattern_match_threshold: float = 0.6

    # Options
    detect_clones: bool = True
    match_patterns: bool = True
    correlate_vulnerabilities: bool = True
    max_similar_contracts: int = 10


class SimilarityEngine:
    """
    High-level engine for semantic code similarity analysis.

    Capabilities:
    - Find similar contracts across a corpus
    - Detect code clones (copied code)
    - Match vulnerability patterns
    - Correlate vulnerabilities across contracts
    """

    def __init__(self, config: Optional[EngineConfig] = None):
        self.config = config or EngineConfig()

        # Initialize components
        self.fingerprint_generator = FingerprintGenerator(self.config.fingerprint_config)
        self.similarity_calculator = SimilarityCalculator(self.config.similarity_config)
        self.index = ContractIndex(self.config.index_config)
        self.clone_detector = CloneDetector()
        self.pattern_matcher = PatternMatcher()

    def analyze_contract(
        self,
        contract_name: str,
        kg_data: Dict[str, Any],
        compare_to_index: bool = True,
        add_to_index: bool = True,
    ) -> AnalysisResult:
        """Analyze a contract for similarity and patterns."""
        start_time = datetime.now()

        result = AnalysisResult(contract_name=contract_name)

        # Generate fingerprints
        fingerprints = self.fingerprint_generator.generate_from_kg(kg_data, contract_name)
        result.fingerprints = fingerprints

        # Match vulnerability patterns
        if self.config.match_patterns:
            for fp in fingerprints:
                matches = self.pattern_matcher.match(fp)
                result.pattern_matches.extend(matches)

        # Compare to index
        if compare_to_index and len(self.index.fingerprints) > 0:
            # Find similar contracts
            all_similarities = []
            for fp in fingerprints:
                search_result = self.index.search(
                    fp,
                    SearchConfig(
                        min_similarity=self.config.similar_contract_threshold,
                        max_results=50,
                        filter_same_contract=True,
                    ),
                )
                all_similarities.extend(search_result.matches)

            # Group by contract
            contract_sims = self._group_by_contract(all_similarities)
            result.similar_contracts = sorted(
                contract_sims,
                key=lambda sc: sc.similarity_score,
                reverse=True,
            )[:self.config.max_similar_contracts]

            # Detect clones
            if self.config.detect_clones:
                all_fps = list(self.index.fingerprints.values()) + fingerprints
                result.clones = self.clone_detector.detect_clones(
                    all_fps,
                    min_similarity=self.config.clone_threshold,
                )
                # Filter to only clones involving this contract
                result.clones = [
                    c for c in result.clones
                    if c.source_contract == contract_name or c.target_contract == contract_name
                ]

            # Correlate vulnerabilities
            if self.config.correlate_vulnerabilities and result.pattern_matches:
                result.vulnerability_correlations = self._correlate_vulnerabilities(
                    contract_name,
                    result.pattern_matches,
                )

        # Add to index
        if add_to_index:
            self.index.add_contract(contract_name, kg_data)

        elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        result.analysis_time_ms = elapsed_ms

        return result

    def _group_by_contract(
        self,
        similarities: List[SimilarityResult],
    ) -> List[SimilarContract]:
        """Group similarity results by contract."""
        contract_groups: Dict[str, SimilarContract] = {}

        for sim in similarities:
            contract = sim.target_contract or sim.target_name
            if contract not in contract_groups:
                contract_groups[contract] = SimilarContract(
                    contract_name=contract,
                    similarity_score=0.0,
                    matching_functions=[],
                    shared_operations=[],
                )

            sc = contract_groups[contract]

            # Update max similarity
            if sim.score.score > sc.similarity_score:
                sc.similarity_score = sim.score.score

            # Track matching functions
            if sim.target_name not in sc.matching_functions:
                sc.matching_functions.append(sim.target_name)

            # Track shared operations
            for op in sim.score.matching_operations:
                if op not in sc.shared_operations:
                    sc.shared_operations.append(op)

        return list(contract_groups.values())

    def _correlate_vulnerabilities(
        self,
        contract_name: str,
        pattern_matches: List[MatchResult],
    ) -> List[VulnerabilityCorrelation]:
        """Find contracts with similar vulnerability patterns."""
        correlations: Dict[str, VulnerabilityCorrelation] = {}

        for match in pattern_matches:
            vuln_type = match.vulnerability_type
            if not vuln_type:
                continue

            if vuln_type not in correlations:
                correlations[vuln_type] = VulnerabilityCorrelation(
                    vulnerability_type=vuln_type,
                    severity=match.severity or "medium",
                    affected_contracts=[contract_name],
                    affected_functions=[f"{contract_name}.{match.target_function}"],
                    confidence=match.confidence,
                )
            else:
                corr = correlations[vuln_type]
                if contract_name not in corr.affected_contracts:
                    corr.affected_contracts.append(contract_name)
                func_key = f"{contract_name}.{match.target_function}"
                if func_key not in corr.affected_functions:
                    corr.affected_functions.append(func_key)
                corr.confidence = max(corr.confidence, match.confidence)

        # Check index for similar vulnerabilities
        for vuln_type, corr in correlations.items():
            # Look for contracts with similar patterns
            similar_vulns = self._find_similar_vulnerable_contracts(vuln_type)
            for contract in similar_vulns:
                if contract not in corr.affected_contracts:
                    corr.affected_contracts.append(contract)

        return list(correlations.values())

    def _find_similar_vulnerable_contracts(self, vuln_type: str) -> List[str]:
        """Find indexed contracts with similar vulnerability patterns."""
        vulnerable_contracts = []

        for entry in self.index.entries.values():
            for fp in entry.fingerprints:
                matches = self.pattern_matcher.match(fp)
                for match in matches:
                    if match.vulnerability_type == vuln_type:
                        vulnerable_contracts.append(entry.contract_name)
                        break

        return vulnerable_contracts

    def find_clones_of_function(
        self,
        function_name: str,
        contract_name: str,
        min_similarity: float = 0.7,
    ) -> List[Clone]:
        """Find clones of a specific function across indexed contracts."""
        return self.index.find_function_clones(
            function_name,
            contract_name,
            min_similarity,
        )

    def find_similar_contracts(
        self,
        contract_name: str,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Find contracts similar to a given one."""
        return self.index.find_similar_contracts(
            contract_name,
            self.config.similar_contract_threshold,
            top_k,
        )

    def add_vulnerability_pattern(
        self,
        pattern_id: str,
        name: str,
        vuln_type: str,
        severity: str,
        required_ops: List[str],
        forbidden_ops: List[str] = None,
    ):
        """Add a custom vulnerability pattern."""
        from .matcher import VulnerabilityPattern

        pattern = VulnerabilityPattern(
            pattern_id=pattern_id,
            name=name,
            vulnerability_type=vuln_type,
            severity=severity,
            required_operations=required_ops,
            forbidden_operations=forbidden_ops or [],
        )

        self.pattern_matcher.add_pattern(pattern)

    def get_statistics(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            "index": self.index.get_statistics(),
            "patterns": len(self.pattern_matcher.patterns),
        }

    def clear(self):
        """Clear all indexed data."""
        self.index.clear()
