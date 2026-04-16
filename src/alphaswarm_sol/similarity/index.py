"""
Contract Index

Index contracts by semantic fingerprints for fast similarity search.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Set
from datetime import datetime
import logging

from .fingerprint import SemanticFingerprint, FingerprintType, FingerprintGenerator
from .similarity import SimilarityCalculator, SimilarityResult

logger = logging.getLogger(__name__)


@dataclass
class IndexEntry:
    """Entry in the contract index."""
    entry_id: str
    contract_name: str
    contract_address: Optional[str] = None

    # Fingerprints
    fingerprints: List[SemanticFingerprint] = field(default_factory=list)

    # Metadata
    num_functions: int = 0
    total_operations: int = 0
    unique_operations: Set[str] = field(default_factory=set)

    # Timestamps
    indexed_at: datetime = field(default_factory=datetime.now)
    source: str = ""  # Where this came from (file, etherscan, etc.)

    # Tags for fast filtering
    tags: Set[str] = field(default_factory=set)  # e.g., "defi", "token", "nft"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "contract": self.contract_name,
            "address": self.contract_address,
            "num_functions": self.num_functions,
            "num_fingerprints": len(self.fingerprints),
            "total_operations": self.total_operations,
            "unique_operations": len(self.unique_operations),
            "indexed_at": self.indexed_at.isoformat(),
            "tags": list(self.tags),
        }


@dataclass
class SearchConfig:
    """Configuration for index search."""
    min_similarity: float = 0.5
    max_results: int = 10
    include_partial: bool = True
    filter_same_contract: bool = True
    filter_tags: Optional[Set[str]] = None


@dataclass
class SearchResult:
    """Result of an index search."""
    query_fingerprint: SemanticFingerprint
    matches: List[SimilarityResult]
    search_time_ms: int = 0
    total_compared: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query_fingerprint.source_name,
            "num_matches": len(self.matches),
            "search_time_ms": self.search_time_ms,
            "total_compared": self.total_compared,
            "top_matches": [m.to_dict() for m in self.matches[:5]],
        }


@dataclass
class IndexConfig:
    """Configuration for the index."""
    # What to index
    index_functions: bool = True
    index_contracts: bool = True

    # Storage
    persist_path: Optional[str] = None  # Path to persist index

    # Performance
    use_hashing: bool = True  # Use hash for fast exact matching
    hash_bucket_size: int = 100  # Number of buckets for hash index


class ContractIndex:
    """
    Index for fast semantic similarity search across contracts.

    Supports:
    - Adding contracts to index
    - Finding similar functions/contracts
    - Filtering by tags
    - Persistence (optional)
    """

    def __init__(self, config: Optional[IndexConfig] = None):
        self.config = config or IndexConfig()

        # Main storage
        self.entries: Dict[str, IndexEntry] = {}  # entry_id -> entry
        self.fingerprints: Dict[str, SemanticFingerprint] = {}  # fp_id -> fingerprint

        # Indexes
        self._hash_index: Dict[str, List[str]] = {}  # hash -> [fp_ids]
        self._contract_index: Dict[str, str] = {}  # contract_name -> entry_id
        self._tag_index: Dict[str, Set[str]] = {}  # tag -> {entry_ids}
        self._operation_index: Dict[str, Set[str]] = {}  # operation -> {fp_ids}

        # Components
        self.generator = FingerprintGenerator()
        self.calculator = SimilarityCalculator()

        self._entry_counter = 0

    def _generate_entry_id(self) -> str:
        """Generate unique entry ID."""
        self._entry_counter += 1
        return f"IDX-{self._entry_counter:06d}"

    def add_contract(
        self,
        contract_name: str,
        kg_data: Dict[str, Any],
        address: Optional[str] = None,
        source: str = "",
        tags: Optional[Set[str]] = None,
    ) -> IndexEntry:
        """Add a contract to the index."""
        entry_id = self._generate_entry_id()

        # Generate fingerprints
        fingerprints = self.generator.generate_from_kg(kg_data, contract_name)

        # Count operations
        all_ops = []
        for fp in fingerprints:
            all_ops.extend(fp.operations)

        entry = IndexEntry(
            entry_id=entry_id,
            contract_name=contract_name,
            contract_address=address,
            fingerprints=fingerprints,
            num_functions=len([fp for fp in fingerprints if fp.fingerprint_type == FingerprintType.OPERATION_SEQUENCE]),
            total_operations=len(all_ops),
            unique_operations=set(all_ops),
            source=source,
            tags=tags or set(),
        )

        # Store entry
        self.entries[entry_id] = entry
        self._contract_index[contract_name] = entry_id

        # Index fingerprints
        for fp in fingerprints:
            self.fingerprints[fp.fingerprint_id] = fp

            # Hash index
            if self.config.use_hashing:
                if fp.hash_value not in self._hash_index:
                    self._hash_index[fp.hash_value] = []
                self._hash_index[fp.hash_value].append(fp.fingerprint_id)

            # Operation index
            for op in fp.operations:
                if op not in self._operation_index:
                    self._operation_index[op] = set()
                self._operation_index[op].add(fp.fingerprint_id)

        # Tag index
        if tags:
            for tag in tags:
                if tag not in self._tag_index:
                    self._tag_index[tag] = set()
                self._tag_index[tag].add(entry_id)

        logger.info(f"Added {contract_name} to index with {len(fingerprints)} fingerprints")

        return entry

    def search(
        self,
        query_fingerprint: SemanticFingerprint,
        config: Optional[SearchConfig] = None,
    ) -> SearchResult:
        """Search for similar fingerprints."""
        config = config or SearchConfig()
        start_time = datetime.now()

        matches: List[SimilarityResult] = []
        total_compared = 0

        # Fast path: check hash index first
        if self.config.use_hashing and query_fingerprint.hash_value in self._hash_index:
            exact_matches = self._hash_index[query_fingerprint.hash_value]
            for fp_id in exact_matches:
                if fp_id == query_fingerprint.fingerprint_id:
                    continue

                fp = self.fingerprints.get(fp_id)
                if fp:
                    result = self.calculator.calculate(query_fingerprint, fp)
                    if result.score.score >= config.min_similarity:
                        if not config.filter_same_contract or fp.contract_name != query_fingerprint.contract_name:
                            matches.append(result)
                    total_compared += 1

        # Slow path: compare all fingerprints
        candidates = self._get_candidates(query_fingerprint, config)

        for fp in candidates:
            if fp.fingerprint_id == query_fingerprint.fingerprint_id:
                continue

            # Skip if same contract and filtering
            if config.filter_same_contract and fp.contract_name == query_fingerprint.contract_name:
                continue

            result = self.calculator.calculate(query_fingerprint, fp)
            total_compared += 1

            if result.score.score >= config.min_similarity:
                matches.append(result)

        # Sort and limit
        matches.sort(key=lambda r: r.score.score, reverse=True)
        matches = matches[:config.max_results]

        elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        return SearchResult(
            query_fingerprint=query_fingerprint,
            matches=matches,
            search_time_ms=elapsed_ms,
            total_compared=total_compared,
        )

    def _get_candidates(
        self,
        query: SemanticFingerprint,
        config: SearchConfig,
    ) -> List[SemanticFingerprint]:
        """Get candidate fingerprints for comparison."""
        # Start with all fingerprints
        candidate_ids = set(self.fingerprints.keys())

        # Filter by operation overlap (optimization)
        if query.operations:
            overlapping = set()
            for op in query.operations:
                if op in self._operation_index:
                    overlapping.update(self._operation_index[op])
            if overlapping:
                candidate_ids &= overlapping

        # Filter by tags
        if config.filter_tags:
            tagged_entries = set()
            for tag in config.filter_tags:
                if tag in self._tag_index:
                    tagged_entries.update(self._tag_index[tag])

            # Get fingerprints from tagged entries
            tagged_fps = set()
            for entry_id in tagged_entries:
                entry = self.entries.get(entry_id)
                if entry:
                    for fp in entry.fingerprints:
                        tagged_fps.add(fp.fingerprint_id)

            candidate_ids &= tagged_fps

        return [self.fingerprints[fp_id] for fp_id in candidate_ids if fp_id in self.fingerprints]

    def find_similar_contracts(
        self,
        contract_name: str,
        min_similarity: float = 0.6,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Find contracts similar to the given one."""
        entry_id = self._contract_index.get(contract_name)
        if not entry_id:
            return []

        entry = self.entries.get(entry_id)
        if not entry:
            return []

        # Get contract-level fingerprint
        contract_fp = None
        for fp in entry.fingerprints:
            if fp.fingerprint_type == FingerprintType.BEHAVIORAL_SIGNATURE:
                contract_fp = fp
                break

        if not contract_fp:
            # Use first fingerprint
            contract_fp = entry.fingerprints[0] if entry.fingerprints else None

        if not contract_fp:
            return []

        # Search
        result = self.search(
            contract_fp,
            SearchConfig(
                min_similarity=min_similarity,
                max_results=top_k,
                filter_same_contract=True,
            ),
        )

        # Group by contract
        contract_matches: Dict[str, float] = {}
        for match in result.matches:
            contract = match.target_contract or match.target_name
            if contract not in contract_matches:
                contract_matches[contract] = match.score.score
            else:
                contract_matches[contract] = max(contract_matches[contract], match.score.score)

        # Format results
        results = [
            {"contract": name, "similarity": score}
            for name, score in sorted(contract_matches.items(), key=lambda x: x[1], reverse=True)
        ]

        return results[:top_k]

    def find_function_clones(
        self,
        function_name: str,
        contract_name: Optional[str] = None,
        min_similarity: float = 0.8,
    ) -> List[SimilarityResult]:
        """Find function clones across all indexed contracts."""
        # Find the function fingerprint
        target_fp = None

        for fp in self.fingerprints.values():
            if fp.source_name == function_name:
                if contract_name is None or fp.contract_name == contract_name:
                    target_fp = fp
                    break

        if not target_fp:
            return []

        result = self.search(
            target_fp,
            SearchConfig(
                min_similarity=min_similarity,
                max_results=50,
                filter_same_contract=False,
            ),
        )

        return result.matches

    def get_statistics(self) -> Dict[str, Any]:
        """Get index statistics."""
        return {
            "total_contracts": len(self.entries),
            "total_fingerprints": len(self.fingerprints),
            "unique_hashes": len(self._hash_index),
            "indexed_operations": len(self._operation_index),
            "tags": list(self._tag_index.keys()),
        }

    def remove_contract(self, contract_name: str) -> bool:
        """Remove a contract from the index."""
        entry_id = self._contract_index.get(contract_name)
        if not entry_id:
            return False

        entry = self.entries.get(entry_id)
        if not entry:
            return False

        # Remove fingerprints
        for fp in entry.fingerprints:
            if fp.fingerprint_id in self.fingerprints:
                del self.fingerprints[fp.fingerprint_id]

            # Remove from hash index
            if fp.hash_value in self._hash_index:
                self._hash_index[fp.hash_value] = [
                    fid for fid in self._hash_index[fp.hash_value]
                    if fid != fp.fingerprint_id
                ]

            # Remove from operation index
            for op in fp.operations:
                if op in self._operation_index:
                    self._operation_index[op].discard(fp.fingerprint_id)

        # Remove from tag index
        for tag in entry.tags:
            if tag in self._tag_index:
                self._tag_index[tag].discard(entry_id)

        # Remove entry
        del self.entries[entry_id]
        del self._contract_index[contract_name]

        return True

    def clear(self):
        """Clear all index data."""
        self.entries.clear()
        self.fingerprints.clear()
        self._hash_index.clear()
        self._contract_index.clear()
        self._tag_index.clear()
        self._operation_index.clear()
        self._entry_counter = 0
