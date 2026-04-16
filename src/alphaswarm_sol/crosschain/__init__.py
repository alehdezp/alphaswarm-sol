"""
Cross-Chain Vulnerability Transfer Module

Provides chain-agnostic vulnerability detection through a Universal Vulnerability Ontology (UVO).
Enables transfer of vulnerability knowledge between different blockchain platforms (EVM, Solana, Move, etc.).
"""

from alphaswarm_sol.crosschain.ontology import (
    Chain,
    AbstractOperation,
    OperationType,
    AbstractVulnerabilitySignature,
    InvariantType,
)

from alphaswarm_sol.crosschain.translators import (
    ChainTranslator,
    EVMTranslator,
    SolanaTranslator,
    MoveTranslator,
    TranslatorRegistry,
)

from alphaswarm_sol.crosschain.database import (
    CrossChainExploitDatabase,
    CrossChainMatch,
    MatchConfidence,
)

from alphaswarm_sol.crosschain.analyzer import (
    CrossChainAnalyzer,
    CrossChainAnalysisResult,
    PortedVulnerability,
)

__all__ = [
    # Core types
    "Chain",
    "AbstractOperation",
    "OperationType",
    "AbstractVulnerabilitySignature",
    "InvariantType",
    # Translators
    "ChainTranslator",
    "EVMTranslator",
    "SolanaTranslator",
    "MoveTranslator",
    "TranslatorRegistry",
    # Database
    "CrossChainExploitDatabase",
    "CrossChainMatch",
    "MatchConfidence",
    # Analyzer
    "CrossChainAnalyzer",
    "CrossChainAnalysisResult",
    "PortedVulnerability",
]
