"""Phase 12: RAG Integration with Pattern Library.

This module provides Retrieval-Augmented Generation (RAG) capabilities
using the VKG pattern library for context-enhanced LLM queries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import os
import yaml

from alphaswarm_sol.kg.schema import Node
from alphaswarm_sol.kg.similarity import compute_signature_similarity


@dataclass
class RAGResult:
    """Result from RAG retrieval.

    Attributes:
        pattern_id: ID of the matched pattern
        pattern_name: Name of the pattern
        similarity_score: Similarity score (0.0 - 1.0)
        pattern_description: Description of the pattern
        match_reason: Why this pattern matched
        remediation: Suggested remediation
        examples: Example code snippets
        metadata: Additional metadata
    """
    pattern_id: str
    pattern_name: str
    similarity_score: float
    pattern_description: str = ""
    match_reason: str = ""
    remediation: str = ""
    examples: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "pattern_name": self.pattern_name,
            "similarity_score": self.similarity_score,
            "pattern_description": self.pattern_description,
            "match_reason": self.match_reason,
            "remediation": self.remediation,
            "examples": self.examples,
            "metadata": self.metadata,
        }

    def to_context_string(self) -> str:
        """Convert to context string for LLM."""
        parts = [
            f"Pattern: {self.pattern_name} ({self.pattern_id})",
            f"Description: {self.pattern_description}",
            f"Match reason: {self.match_reason}",
        ]
        if self.remediation:
            parts.append(f"Remediation: {self.remediation}")
        return "\n".join(parts)


@dataclass
class PatternEntry:
    """Entry in the pattern library.

    Attributes:
        id: Pattern identifier
        name: Pattern name
        description: Description
        severity: Severity level
        behavioral_signature: Expected behavioral signature
        required_operations: Required operations
        properties: Property matches
        remediation: Fix suggestion
        examples: Example code
        references: External references
    """
    id: str
    name: str
    description: str = ""
    severity: str = "medium"
    behavioral_signature: str = ""
    required_operations: List[str] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    remediation: str = ""
    examples: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)

    @staticmethod
    def from_yaml(data: Dict[str, Any]) -> "PatternEntry":
        """Create from YAML data."""
        return PatternEntry(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            severity=data.get("severity", "medium"),
            behavioral_signature=data.get("behavioral_signature", ""),
            required_operations=data.get("required_operations", []),
            properties=data.get("properties", {}),
            remediation=data.get("remediation", ""),
            examples=data.get("examples", []),
            references=data.get("references", []),
        )


class PatternRAG:
    """RAG system using VKG pattern library.

    Retrieves relevant patterns for LLM context augmentation.
    """

    def __init__(self, patterns_dir: Optional[str] = None):
        """Initialize PatternRAG.

        Args:
            patterns_dir: Directory containing pattern YAML files
        """
        self.patterns_dir = patterns_dir
        self.patterns: List[PatternEntry] = []
        self._signature_index: Dict[str, List[PatternEntry]] = {}
        self._operation_index: Dict[str, List[PatternEntry]] = {}

        if patterns_dir:
            self.load_patterns(patterns_dir)

    def load_patterns(self, patterns_dir: str) -> int:
        """Load patterns from directory.

        Args:
            patterns_dir: Directory containing YAML files

        Returns:
            Number of patterns loaded
        """
        self.patterns = []
        self._signature_index = {}
        self._operation_index = {}

        path = Path(patterns_dir)
        if not path.exists():
            return 0

        for yaml_file in path.glob("**/*.yaml"):
            try:
                with open(yaml_file) as f:
                    data = yaml.safe_load(f)

                if data and isinstance(data, dict):
                    # Handle both single pattern and pattern lists
                    if "patterns" in data:
                        for pattern_data in data["patterns"]:
                            self._add_pattern(pattern_data)
                    else:
                        self._add_pattern(data)

            except (yaml.YAMLError, IOError):
                continue

        return len(self.patterns)

    def _add_pattern(self, data: Dict[str, Any]) -> None:
        """Add a pattern to the library."""
        if not data.get("id"):
            return

        pattern = PatternEntry.from_yaml(data)
        self.patterns.append(pattern)

        # Index by signature
        if pattern.behavioral_signature:
            self._signature_index.setdefault(
                pattern.behavioral_signature, []
            ).append(pattern)

        # Index by operations
        for op in pattern.required_operations:
            self._operation_index.setdefault(op, []).append(pattern)

    def add_pattern(self, pattern: PatternEntry) -> None:
        """Add a pattern programmatically."""
        self._add_pattern({
            "id": pattern.id,
            "name": pattern.name,
            "description": pattern.description,
            "severity": pattern.severity,
            "behavioral_signature": pattern.behavioral_signature,
            "required_operations": pattern.required_operations,
            "properties": pattern.properties,
            "remediation": pattern.remediation,
            "examples": pattern.examples,
            "references": pattern.references,
        })

    def retrieve(
        self,
        function: Node,
        top_k: int = 3,
        min_similarity: float = 0.5,
    ) -> List[RAGResult]:
        """Retrieve relevant patterns for a function.

        Args:
            function: Function node to match against
            top_k: Maximum number of results
            min_similarity: Minimum similarity threshold

        Returns:
            List of RAGResult sorted by similarity
        """
        if function.type != "Function":
            return []

        results: List[RAGResult] = []
        seen_ids: set = set()

        fn_sig = function.properties.get("behavioral_signature", "")
        fn_ops = set(function.properties.get("semantic_ops", []))

        # Match by behavioral signature
        if fn_sig:
            # Exact matches
            for pattern in self._signature_index.get(fn_sig, []):
                if pattern.id not in seen_ids:
                    seen_ids.add(pattern.id)
                    results.append(RAGResult(
                        pattern_id=pattern.id,
                        pattern_name=pattern.name,
                        similarity_score=1.0,
                        pattern_description=pattern.description,
                        match_reason=f"Exact signature match: {fn_sig}",
                        remediation=pattern.remediation,
                        examples=pattern.examples,
                        metadata={"severity": pattern.severity},
                    ))

            # Partial signature matches
            for sig, patterns in self._signature_index.items():
                if sig != fn_sig:
                    similarity = compute_signature_similarity(fn_sig, sig)
                    if similarity >= min_similarity:
                        for pattern in patterns:
                            if pattern.id not in seen_ids:
                                seen_ids.add(pattern.id)
                                results.append(RAGResult(
                                    pattern_id=pattern.id,
                                    pattern_name=pattern.name,
                                    similarity_score=similarity,
                                    pattern_description=pattern.description,
                                    match_reason=f"Similar signature ({similarity:.0%}): {sig}",
                                    remediation=pattern.remediation,
                                    examples=pattern.examples,
                                    metadata={"severity": pattern.severity},
                                ))

        # Match by operations
        for op in fn_ops:
            for pattern in self._operation_index.get(op, []):
                if pattern.id not in seen_ids:
                    # Calculate operation overlap
                    required = set(pattern.required_operations)
                    overlap = fn_ops & required
                    if overlap:
                        similarity = len(overlap) / len(required)
                        if similarity >= min_similarity:
                            seen_ids.add(pattern.id)
                            results.append(RAGResult(
                                pattern_id=pattern.id,
                                pattern_name=pattern.name,
                                similarity_score=similarity,
                                pattern_description=pattern.description,
                                match_reason=f"Operation match ({len(overlap)}/{len(required)}): {', '.join(overlap)}",
                                remediation=pattern.remediation,
                                examples=pattern.examples,
                                metadata={"severity": pattern.severity},
                            ))

        # Match by properties
        for pattern in self.patterns:
            if pattern.id not in seen_ids and pattern.properties:
                match_count = 0
                total_props = len(pattern.properties)

                for prop, expected in pattern.properties.items():
                    actual = function.properties.get(prop)
                    if actual == expected:
                        match_count += 1

                if match_count > 0:
                    similarity = match_count / total_props
                    if similarity >= min_similarity:
                        seen_ids.add(pattern.id)
                        results.append(RAGResult(
                            pattern_id=pattern.id,
                            pattern_name=pattern.name,
                            similarity_score=similarity,
                            pattern_description=pattern.description,
                            match_reason=f"Property match ({match_count}/{total_props})",
                            remediation=pattern.remediation,
                            examples=pattern.examples,
                            metadata={"severity": pattern.severity},
                        ))

        # Sort by similarity and limit
        results.sort(key=lambda r: r.similarity_score, reverse=True)
        return results[:top_k]

    def retrieve_by_query(
        self,
        query: str,
        top_k: int = 3,
    ) -> List[RAGResult]:
        """Retrieve patterns by text query.

        Simple keyword matching for now.

        Args:
            query: Text query
            top_k: Maximum results

        Returns:
            List of matching patterns
        """
        query_lower = query.lower()
        keywords = query_lower.split()

        scored_patterns: List[Tuple[float, PatternEntry]] = []

        for pattern in self.patterns:
            score = 0.0
            searchable = (
                f"{pattern.name} {pattern.description} "
                f"{' '.join(pattern.required_operations)}"
            ).lower()

            for keyword in keywords:
                if keyword in searchable:
                    score += 1.0

            if score > 0:
                normalized_score = min(score / len(keywords), 1.0)
                scored_patterns.append((normalized_score, pattern))

        # Sort by score
        scored_patterns.sort(key=lambda x: x[0], reverse=True)

        results = []
        for score, pattern in scored_patterns[:top_k]:
            results.append(RAGResult(
                pattern_id=pattern.id,
                pattern_name=pattern.name,
                similarity_score=score,
                pattern_description=pattern.description,
                match_reason=f"Query match: {query}",
                remediation=pattern.remediation,
                examples=pattern.examples,
            ))

        return results

    def get_pattern(self, pattern_id: str) -> Optional[PatternEntry]:
        """Get pattern by ID."""
        for pattern in self.patterns:
            if pattern.id == pattern_id:
                return pattern
        return None


def retrieve_similar_patterns(
    function: Node,
    patterns_dir: Optional[str] = None,
    top_k: int = 3,
) -> List[RAGResult]:
    """Convenience function to retrieve similar patterns.

    Args:
        function: Function node to match
        patterns_dir: Optional patterns directory
        top_k: Maximum results

    Returns:
        List of RAGResult
    """
    rag = PatternRAG(patterns_dir)
    return rag.retrieve(function, top_k=top_k)


def build_rag_context(
    function: Node,
    rag_results: List[RAGResult],
) -> str:
    """Build context string from RAG results.

    Args:
        function: Function being analyzed
        rag_results: Retrieved patterns

    Returns:
        Context string for LLM prompt
    """
    if not rag_results:
        return ""

    parts = [
        "Relevant patterns from the vulnerability pattern library:",
        "",
    ]

    for i, result in enumerate(rag_results, 1):
        parts.append(f"{i}. {result.pattern_name}")
        parts.append(f"   - Similarity: {result.similarity_score:.0%}")
        parts.append(f"   - Reason: {result.match_reason}")
        if result.pattern_description:
            parts.append(f"   - Description: {result.pattern_description}")
        if result.remediation:
            parts.append(f"   - Remediation: {result.remediation}")
        parts.append("")

    return "\n".join(parts)


__all__ = [
    "RAGResult",
    "PatternEntry",
    "PatternRAG",
    "retrieve_similar_patterns",
    "build_rag_context",
]
