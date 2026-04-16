"""
Cross-Chain Exploit Database

Stores and indexes exploits with cross-chain awareness.
Enables finding similar vulnerabilities across different blockchain platforms.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Set, Tuple
from enum import Enum
from datetime import datetime
import hashlib
import logging

from alphaswarm_sol.crosschain.ontology import (
    Chain,
    AbstractOperation,
    OperationType,
    AbstractVulnerabilitySignature,
    InvariantType,
    UNIVERSAL_SIGNATURES,
)
from alphaswarm_sol.crosschain.translators import TranslatorRegistry, TRANSLATOR_REGISTRY

logger = logging.getLogger(__name__)


class MatchConfidence(Enum):
    """Confidence level for cross-chain matches."""
    EXACT = "exact"           # Identical signature
    HIGH = "high"             # Same operations, minor target differences
    MEDIUM = "medium"         # Similar operations, different context
    LOW = "low"               # Partial match, same category
    SPECULATIVE = "speculative"  # Same invariant violated only


@dataclass
class CrossChainExploit:
    """
    An exploit record with cross-chain metadata.
    """
    exploit_id: str
    name: str
    chain: Chain
    date: str                           # ISO date
    loss_usd: float                     # Financial impact
    vulnerability_type: str
    abstract_signature: AbstractVulnerabilitySignature

    # Original chain-specific details
    chain_operations: List[str] = field(default_factory=list)
    contract_address: Optional[str] = None
    tx_hash: Optional[str] = None

    # Cross-chain analysis
    similar_exploits: List[str] = field(default_factory=list)
    transferred_to_chains: List[Chain] = field(default_factory=list)

    # Metadata
    description: str = ""
    references: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    def get_signature_hash(self) -> str:
        """Get hash of the abstract signature."""
        return self.abstract_signature.get_signature_hash()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "exploit_id": self.exploit_id,
            "name": self.name,
            "chain": self.chain.value,
            "date": self.date,
            "loss_usd": self.loss_usd,
            "vulnerability_type": self.vulnerability_type,
            "signature_hash": self.get_signature_hash(),
            "behavioral_signature": self.abstract_signature.get_behavioral_signature(),
            "description": self.description,
            "similar_exploits": self.similar_exploits,
        }


@dataclass
class CrossChainMatch:
    """
    A cross-chain vulnerability match.
    """
    source_exploit: CrossChainExploit
    target_chain: Chain
    confidence: MatchConfidence
    matched_operations: List[AbstractOperation]
    missing_operations: List[AbstractOperation]
    similarity_score: float             # 0.0 to 1.0
    target_pattern: Dict[str, Any]      # Chain-specific pattern for target

    # Recommendations
    mitigation: str = ""
    priority: str = ""                  # critical, high, medium, low

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source_exploit": self.source_exploit.name,
            "source_chain": self.source_exploit.chain.value,
            "target_chain": self.target_chain.value,
            "confidence": self.confidence.value,
            "similarity_score": self.similarity_score,
            "matched_operations": len(self.matched_operations),
            "missing_operations": len(self.missing_operations),
            "priority": self.priority,
        }


class CrossChainExploitDatabase:
    """
    Database of cross-chain exploits with similarity matching.
    """

    def __init__(self, translator_registry: Optional[TranslatorRegistry] = None):
        self.translator = translator_registry or TRANSLATOR_REGISTRY
        self.exploits: Dict[str, CrossChainExploit] = {}

        # Indexes for fast lookup
        self._by_chain: Dict[Chain, List[str]] = {chain: [] for chain in Chain}
        self._by_signature: Dict[str, List[str]] = {}
        self._by_category: Dict[str, List[str]] = {}
        self._by_invariant: Dict[InvariantType, List[str]] = {inv: [] for inv in InvariantType}

        # Load well-known exploits
        self._load_known_exploits()

    def add_exploit(
        self,
        exploit_id: str,
        name: str,
        chain: Chain,
        date: str,
        loss_usd: float,
        vulnerability_type: str,
        chain_operations: List[str],
        **kwargs
    ) -> CrossChainExploit:
        """
        Add an exploit to the database.

        Automatically converts to abstract signature.
        """
        # Convert to abstract operations
        abstract_ops = self.translator.translate_to_abstract(chain, chain_operations)

        # Create abstract signature
        sig = AbstractVulnerabilitySignature(
            vuln_id=exploit_id,
            vuln_name=name,
            vuln_category=vulnerability_type,
            abstract_operations=abstract_ops,
            invariant_violated=self._infer_invariant(abstract_ops, vulnerability_type),
            severity=self._infer_severity(loss_usd),
        )

        exploit = CrossChainExploit(
            exploit_id=exploit_id,
            name=name,
            chain=chain,
            date=date,
            loss_usd=loss_usd,
            vulnerability_type=vulnerability_type,
            abstract_signature=sig,
            chain_operations=chain_operations,
            **kwargs
        )

        self.exploits[exploit_id] = exploit

        # Index
        self._index_exploit(exploit)

        # Find similar exploits
        exploit.similar_exploits = self._find_similar_ids(exploit)

        return exploit

    def find_cross_chain_matches(
        self,
        target_chain: Chain,
        target_operations: List[str],
        min_confidence: MatchConfidence = MatchConfidence.MEDIUM
    ) -> List[CrossChainMatch]:
        """
        Find exploits from OTHER chains that match the target operations.

        This is the core cross-chain transfer capability.
        """
        # Convert target to abstract
        target_abstract = self.translator.translate_to_abstract(target_chain, target_operations)

        matches = []
        confidence_order = [
            MatchConfidence.EXACT,
            MatchConfidence.HIGH,
            MatchConfidence.MEDIUM,
            MatchConfidence.LOW,
            MatchConfidence.SPECULATIVE,
        ]

        min_idx = confidence_order.index(min_confidence)

        for exploit in self.exploits.values():
            # Skip same chain (looking for cross-chain transfer)
            if exploit.chain == target_chain:
                continue

            # Calculate match
            match = self._calculate_match(exploit, target_chain, target_abstract)

            # Check confidence threshold
            if match and confidence_order.index(match.confidence) <= min_idx:
                matches.append(match)

        # Sort by similarity score
        matches.sort(key=lambda m: m.similarity_score, reverse=True)

        return matches

    def find_by_signature(
        self,
        signature_hash: str
    ) -> List[CrossChainExploit]:
        """Find exploits by signature hash."""
        ids = self._by_signature.get(signature_hash, [])
        return [self.exploits[id] for id in ids if id in self.exploits]

    def find_by_category(
        self,
        category: str,
        chain: Optional[Chain] = None
    ) -> List[CrossChainExploit]:
        """Find exploits by vulnerability category."""
        ids = self._by_category.get(category, [])
        exploits = [self.exploits[id] for id in ids if id in self.exploits]

        if chain:
            exploits = [e for e in exploits if e.chain == chain]

        return exploits

    def find_by_invariant(
        self,
        invariant: InvariantType
    ) -> List[CrossChainExploit]:
        """Find exploits by violated invariant."""
        ids = self._by_invariant.get(invariant, [])
        return [self.exploits[id] for id in ids if id in self.exploits]

    def transfer_vulnerability(
        self,
        exploit_id: str,
        target_chain: Chain
    ) -> Optional[Dict[str, Any]]:
        """
        Transfer a vulnerability pattern to a new chain.

        Returns the chain-specific pattern for the target.
        """
        exploit = self.exploits.get(exploit_id)
        if not exploit:
            return None

        if exploit.chain == target_chain:
            return None  # Already on target chain

        # Translate to target chain
        target_pattern = self.translator.translate_from_abstract(
            target_chain,
            exploit.abstract_signature.abstract_operations
        )

        # Add metadata
        target_pattern["source_exploit"] = exploit.name
        target_pattern["source_chain"] = exploit.chain.value
        target_pattern["loss_usd"] = exploit.loss_usd
        target_pattern["description"] = f"Ported from {exploit.chain.value}: {exploit.description}"

        # Track transfer
        if target_chain not in exploit.transferred_to_chains:
            exploit.transferred_to_chains.append(target_chain)

        return target_pattern

    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics."""
        return {
            "total_exploits": len(self.exploits),
            "by_chain": {
                chain.value: len(ids)
                for chain, ids in self._by_chain.items()
                if ids
            },
            "by_category": {
                cat: len(ids)
                for cat, ids in self._by_category.items()
            },
            "total_loss_usd": sum(e.loss_usd for e in self.exploits.values()),
            "unique_signatures": len(self._by_signature),
        }

    def _calculate_match(
        self,
        exploit: CrossChainExploit,
        target_chain: Chain,
        target_abstract: List[AbstractOperation]
    ) -> Optional[CrossChainMatch]:
        """Calculate match between exploit and target operations."""
        source_ops = set(
            (op.operation, op.target)
            for op in exploit.abstract_signature.abstract_operations
        )
        target_ops = set(
            (op.operation, op.target)
            for op in target_abstract
        )

        # Calculate overlap
        matched = source_ops.intersection(target_ops)
        missing = source_ops - target_ops

        if not matched:
            return None

        # Calculate similarity score
        similarity = len(matched) / len(source_ops) if source_ops else 0.0

        # Determine confidence
        if similarity >= 0.95:
            confidence = MatchConfidence.EXACT
        elif similarity >= 0.8:
            confidence = MatchConfidence.HIGH
        elif similarity >= 0.5:
            confidence = MatchConfidence.MEDIUM
        elif similarity >= 0.3:
            confidence = MatchConfidence.LOW
        else:
            confidence = MatchConfidence.SPECULATIVE

        # Get matched operation objects
        matched_ops = [
            op for op in exploit.abstract_signature.abstract_operations
            if (op.operation, op.target) in matched
        ]
        missing_ops = [
            op for op in exploit.abstract_signature.abstract_operations
            if (op.operation, op.target) in missing
        ]

        # Generate target pattern
        target_pattern = self.translator.translate_from_abstract(
            target_chain,
            exploit.abstract_signature.abstract_operations
        )

        return CrossChainMatch(
            source_exploit=exploit,
            target_chain=target_chain,
            confidence=confidence,
            matched_operations=matched_ops,
            missing_operations=missing_ops,
            similarity_score=similarity,
            target_pattern=target_pattern,
            mitigation=self._generate_mitigation(exploit),
            priority=self._determine_priority(exploit, similarity),
        )

    def _index_exploit(self, exploit: CrossChainExploit):
        """Index an exploit for fast lookup."""
        self._by_chain[exploit.chain].append(exploit.exploit_id)

        sig_hash = exploit.get_signature_hash()
        if sig_hash not in self._by_signature:
            self._by_signature[sig_hash] = []
        self._by_signature[sig_hash].append(exploit.exploit_id)

        cat = exploit.vulnerability_type
        if cat not in self._by_category:
            self._by_category[cat] = []
        self._by_category[cat].append(exploit.exploit_id)

        inv = exploit.abstract_signature.invariant_violated
        self._by_invariant[inv].append(exploit.exploit_id)

    def _find_similar_ids(self, exploit: CrossChainExploit) -> List[str]:
        """Find IDs of similar exploits."""
        similar = []
        sig_hash = exploit.get_signature_hash()

        # Same signature
        for id in self._by_signature.get(sig_hash, []):
            if id != exploit.exploit_id:
                similar.append(id)

        # Same category
        for id in self._by_category.get(exploit.vulnerability_type, []):
            if id != exploit.exploit_id and id not in similar:
                similar.append(id)

        return similar[:10]  # Limit

    def _infer_invariant(
        self,
        ops: List[AbstractOperation],
        vuln_type: str
    ) -> InvariantType:
        """Infer violated invariant from operations."""
        vuln_lower = vuln_type.lower()

        if "reentrancy" in vuln_lower:
            return InvariantType.CEI_PATTERN
        if "access" in vuln_lower or "auth" in vuln_lower:
            return InvariantType.ACCESS_CONTROL
        if "oracle" in vuln_lower:
            return InvariantType.ORACLE_FRESHNESS
        if "dos" in vuln_lower or "denial" in vuln_lower:
            return InvariantType.DENIAL_OF_SERVICE
        if "signature" in vuln_lower or "replay" in vuln_lower:
            return InvariantType.SIGNATURE_REPLAY
        if "init" in vuln_lower:
            return InvariantType.INITIALIZATION
        if "upgrade" in vuln_lower:
            return InvariantType.UPGRADE_SAFETY

        # Check operations
        has_transfer = any(op.operation == OperationType.TRANSFER_VALUE for op in ops)
        has_write = any(op.operation == OperationType.WRITE_VALUE for op in ops)

        if has_transfer and has_write:
            # Check ordering (if available)
            transfers = [op for op in ops if op.operation == OperationType.TRANSFER_VALUE]
            writes = [op for op in ops if op.operation == OperationType.WRITE_VALUE]
            if transfers and writes and transfers[0].timing < writes[0].timing:
                return InvariantType.CEI_PATTERN

        return InvariantType.ACCESS_CONTROL  # Default

    def _infer_severity(self, loss_usd: float) -> str:
        """Infer severity from financial loss."""
        if loss_usd >= 10_000_000:
            return "critical"
        if loss_usd >= 1_000_000:
            return "high"
        if loss_usd >= 100_000:
            return "medium"
        return "low"

    def _generate_mitigation(self, exploit: CrossChainExploit) -> str:
        """Generate mitigation recommendation."""
        inv = exploit.abstract_signature.invariant_violated

        mitigations = {
            InvariantType.CEI_PATTERN: "Follow Checks-Effects-Interactions pattern. Update state before external calls.",
            InvariantType.ACCESS_CONTROL: "Add proper access control modifiers. Verify caller authorization.",
            InvariantType.ORACLE_FRESHNESS: "Add staleness check. Verify oracle data is recent.",
            InvariantType.REENTRANCY_GUARD: "Use reentrancy guard modifier. Consider mutex locks.",
            InvariantType.DENIAL_OF_SERVICE: "Bound loop iterations. Avoid external calls in loops.",
            InvariantType.SIGNATURE_REPLAY: "Include nonce and chain ID in signed message.",
            InvariantType.INITIALIZATION: "Use initializer guard. Ensure one-time initialization.",
            InvariantType.UPGRADE_SAFETY: "Add storage gaps. Use proper upgrade patterns.",
        }

        return mitigations.get(inv, "Review and fix the identified vulnerability pattern.")

    def _determine_priority(self, exploit: CrossChainExploit, similarity: float) -> str:
        """Determine priority for addressing the match."""
        severity = exploit.abstract_signature.severity
        loss = exploit.loss_usd

        if severity == "critical" and similarity >= 0.8:
            return "critical"
        if severity in ("critical", "high") and similarity >= 0.5:
            return "high"
        if similarity >= 0.8 or loss >= 1_000_000:
            return "high"
        if similarity >= 0.5:
            return "medium"
        return "low"

    def _load_known_exploits(self):
        """Load well-known historical exploits."""
        known_exploits = [
            {
                "exploit_id": "EXP-DAO-2016",
                "name": "The DAO",
                "chain": Chain.EVM,
                "date": "2016-06-17",
                "loss_usd": 60_000_000,
                "vulnerability_type": "reentrancy",
                "chain_operations": [
                    "READS_USER_BALANCE",
                    "CALLS_EXTERNAL",
                    "TRANSFERS_VALUE_OUT",
                    "WRITES_USER_BALANCE",
                ],
                "description": "Classic reentrancy exploit via fallback function.",
                "references": ["https://hackingdistributed.com/2016/06/18/analysis-of-the-dao-exploit/"],
            },
            {
                "exploit_id": "EXP-PARITY-2017",
                "name": "Parity Wallet",
                "chain": Chain.EVM,
                "date": "2017-11-06",
                "loss_usd": 150_000_000,
                "vulnerability_type": "access_control",
                "chain_operations": [
                    "MODIFIES_OWNER",
                ],
                "description": "Missing access control on library initializer.",
                "references": ["https://www.parity.io/a-]postmortem-on-the-parity-multi-sig-library-self-destruct/"],
            },
            {
                "exploit_id": "EXP-CREAM-2021",
                "name": "Cream Finance",
                "chain": Chain.EVM,
                "date": "2021-08-30",
                "loss_usd": 130_000_000,
                "vulnerability_type": "reentrancy",
                "chain_operations": [
                    "READS_ORACLE",
                    "READS_USER_BALANCE",
                    "CALLS_EXTERNAL",
                    "WRITES_USER_BALANCE",
                ],
                "description": "Flash loan + reentrancy attack on lending protocol.",
            },
            {
                "exploit_id": "EXP-WORMHOLE-2022",
                "name": "Wormhole",
                "chain": Chain.SOLANA,
                "date": "2022-02-02",
                "loss_usd": 320_000_000,
                "vulnerability_type": "access_control",
                "chain_operations": [
                    "signer",
                    "transfer",
                ],
                "description": "Signature verification bypass on Solana.",
            },
            {
                "exploit_id": "EXP-MANGO-2022",
                "name": "Mango Markets",
                "chain": Chain.SOLANA,
                "date": "2022-10-11",
                "loss_usd": 114_000_000,
                "vulnerability_type": "oracle",
                "chain_operations": [
                    "account.data",
                    "transfer",
                ],
                "description": "Oracle price manipulation attack.",
            },
            {
                "exploit_id": "EXP-NOMAD-2022",
                "name": "Nomad Bridge",
                "chain": Chain.EVM,
                "date": "2022-08-01",
                "loss_usd": 190_000_000,
                "vulnerability_type": "initialization",
                "chain_operations": [
                    "MODIFIES_OWNER",
                    "MODIFIES_CRITICAL_STATE",
                ],
                "description": "Faulty upgrade allowed anyone to claim funds.",
            },
            {
                "exploit_id": "EXP-HARVEST-2020",
                "name": "Harvest Finance",
                "chain": Chain.EVM,
                "date": "2020-10-26",
                "loss_usd": 34_000_000,
                "vulnerability_type": "oracle",
                "chain_operations": [
                    "READS_ORACLE",
                    "READS_EXTERNAL_VALUE",
                    "CALLS_EXTERNAL",
                ],
                "description": "Flash loan oracle manipulation.",
            },
        ]

        for exploit_data in known_exploits:
            try:
                self.add_exploit(**exploit_data)
            except Exception as e:
                logger.warning(f"Failed to load exploit {exploit_data['exploit_id']}: {e}")


# Global database instance
CROSS_CHAIN_DATABASE = CrossChainExploitDatabase()
