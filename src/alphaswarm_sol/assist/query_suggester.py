"""Query suggester for vulnerability discovery.

Suggests high-value queries based on contract analysis and historical effectiveness.
"""

import yaml
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional
from ..kg.schema import KnowledgeGraph
from .contract_analyzer import ContractAnalysis, analyze_contract


@dataclass
class QueryTemplate:
    """Template for a vulnerability query with metadata."""

    id: str
    query: str
    priority: str  # CRITICAL, HIGH, MEDIUM, LOW
    category: str
    title: str
    why: str
    expected_findings: str
    effectiveness: float
    base_score: int
    applicability_conditions: Dict[str, Any]
    found_in: List[str]


@dataclass
class QuerySuggestion:
    """A ranked query suggestion."""

    rank: int
    query_id: str
    query: str
    priority: str
    category: str
    title: str
    why: str
    expected_findings: str
    effectiveness: float
    final_score: float
    found_in: List[str]
    execute_with: str


class QueryLibrary:
    """Loads and manages the query library."""

    def __init__(self, yaml_path: Optional[Path] = None):
        """Load query library from YAML file.

        Args:
            yaml_path: Path to query_library.yaml. If None, uses default.
        """
        if yaml_path is None:
            # Default to query_library.yaml in same directory
            yaml_path = Path(__file__).parent / "query_library.yaml"

        with open(yaml_path) as f:
            self.data = yaml.safe_load(f)

        self.queries = self._parse_queries()

    def _parse_queries(self) -> List[QueryTemplate]:
        """Parse YAML data into QueryTemplate objects."""
        queries = []
        for category, category_queries in self.data.items():
            for q in category_queries:
                queries.append(QueryTemplate(
                    id=q["id"],
                    query=q["query"],
                    priority=q["priority"],
                    category=q.get("category", category),
                    title=q["title"],
                    why=q["why"],
                    expected_findings=q["expected_findings"],
                    effectiveness=q["effectiveness"],
                    base_score=q["base_score"],
                    applicability_conditions=q["applicability_conditions"],
                    found_in=q["found_in"]
                ))
        return queries

    def get_all_queries(self) -> List[QueryTemplate]:
        """Get all queries in library."""
        return self.queries

    def get_by_category(self, category: str) -> List[QueryTemplate]:
        """Get queries for specific category."""
        return [q for q in self.queries if q.category == category]


class QueryRanker:
    """Ranks queries based on contract characteristics."""

    def __init__(self, library: QueryLibrary):
        """Initialize ranker with query library.

        Args:
            library: QueryLibrary instance
        """
        self.library = library

    def rank_queries(
        self,
        analysis: ContractAnalysis,
        focus: str = "all",
        limit: int = 5
    ) -> List[QuerySuggestion]:
        """Rank queries by relevance to contract.

        Args:
            analysis: Contract analysis results
            focus: Category to focus on ("all" or category name)
            limit: Maximum number of suggestions to return

        Returns:
            List of ranked query suggestions
        """
        candidates = self.library.get_all_queries()

        # Filter by focus if specified
        if focus != "all":
            candidates = [q for q in candidates if q.category == focus]

        # Score each query
        scored = []
        for query in candidates:
            score = self._calculate_score(query, analysis)
            if score > 0:  # Only include applicable queries
                scored.append((query, score))

        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)

        # Build suggestions
        suggestions = []
        for rank, (query, score) in enumerate(scored[:limit], 1):
            suggestions.append(QuerySuggestion(
                rank=rank,
                query_id=query.id,
                query=query.query,
                priority=query.priority,
                category=query.category,
                title=query.title,
                why=query.why,
                expected_findings=query.expected_findings,
                effectiveness=query.effectiveness,
                final_score=score,
                found_in=query.found_in,
                execute_with=f'uv run alphaswarm query "{query.query}" --vql2'
            ))

        return suggestions

    def _calculate_score(
        self,
        query: QueryTemplate,
        analysis: ContractAnalysis
    ) -> float:
        """Calculate relevance score for query.

        Args:
            query: Query template
            analysis: Contract analysis

        Returns:
            Relevance score (0 if not applicable)
        """
        # 1. Check required conditions (must all be met)
        if not self._check_applicability(query, analysis):
            return 0  # Query not applicable

        # 2. Start with base score (priority-based)
        score = query.base_score

        # 3. Apply boosts for matching conditions
        for boost_condition in query.applicability_conditions.get("boosts_if", []):
            if self._check_condition(boost_condition["condition"], analysis):
                score += boost_condition["boost"]

        # 4. Multiply by historical effectiveness
        score *= query.effectiveness

        return score

    def _check_applicability(
        self,
        query: QueryTemplate,
        analysis: ContractAnalysis
    ) -> bool:
        """Check if query is applicable to this contract.

        Args:
            query: Query template
            analysis: Contract analysis

        Returns:
            True if all required conditions are met
        """
        required = query.applicability_conditions.get("requires", [])

        for condition in required:
            if not self._check_condition(condition, analysis):
                return False

        return True

    def _check_condition(self, condition: str, analysis: ContractAnalysis) -> bool:
        """Evaluate a single condition.

        Args:
            condition: Condition string (e.g., "total_functions > 0")
            analysis: Contract analysis

        Returns:
            True if condition is met
        """
        # Parse condition: "property operator value"
        # Supports: ==, !=, >, <, >=, <=
        condition = condition.strip()

        # Try different operators
        for op in ["==", "!=", ">=", "<=", ">", "<"]:
            if op in condition:
                parts = condition.split(op)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value_str = parts[1].strip()

                    # Get analysis value
                    analysis_value = getattr(analysis, key, None)
                    if analysis_value is None:
                        return False

                    # Parse expected value
                    if value_str.lower() == "true":
                        expected_value = True
                    elif value_str.lower() == "false":
                        expected_value = False
                    else:
                        try:
                            expected_value = int(value_str)
                        except ValueError:
                            try:
                                expected_value = float(value_str)
                            except ValueError:
                                expected_value = value_str.strip('"\'')

                    # Evaluate comparison
                    if op == "==":
                        return analysis_value == expected_value
                    elif op == "!=":
                        return analysis_value != expected_value
                    elif op == ">":
                        return analysis_value > expected_value
                    elif op == "<":
                        return analysis_value < expected_value
                    elif op == ">=":
                        return analysis_value >= expected_value
                    elif op == "<=":
                        return analysis_value <= expected_value

        return False


def suggest_queries(
    graph: KnowledgeGraph,
    focus: str = "all",
    limit: int = 5,
    library_path: Optional[Path] = None
) -> Dict[str, Any]:
    """Suggest high-value queries for a contract.

    Args:
        graph: Knowledge graph of contract
        focus: Category to focus on ("all" or category name)
        limit: Maximum number of suggestions
        library_path: Optional custom query library path

    Returns:
        Dictionary with contract_analysis and suggestions
    """
    # 1. Analyze contract
    analysis = analyze_contract(graph)

    # 2. Load query library
    library = QueryLibrary(library_path)

    # 3. Rank queries
    ranker = QueryRanker(library)
    suggestions = ranker.rank_queries(analysis, focus, limit)

    # 4. Build response
    return {
        "contract_analysis": {
            "functions": analysis.total_functions,
            "external_functions": analysis.external_functions,
            "public_functions": analysis.public_functions,
            "state_variables": analysis.total_state_vars,
            "privileged_state_vars": analysis.privileged_state_vars,
            "has_access_control": analysis.has_access_control,
            "has_external_calls": analysis.has_external_calls,
            "has_delegatecalls": analysis.has_delegatecalls,
            "has_oracle_reads": analysis.has_oracle_reads,
            "has_swap_operations": analysis.has_swap_operations,
            "has_token_transfers": analysis.has_token_transfers,
            "has_unbounded_loops": analysis.has_unbounded_loops,
            "complexity": analysis.complexity,
        },
        "suggestions": [
            {
                "rank": s.rank,
                "query_id": s.query_id,
                "priority": s.priority,
                "category": s.category,
                "title": s.title,
                "query": s.query,
                "why": s.why,
                "expected_findings": s.expected_findings,
                "effectiveness": s.effectiveness,
                "final_score": round(s.final_score, 2),
                "found_in": s.found_in,
                "execute_with": s.execute_with,
            }
            for s in suggestions
        ],
        "metadata": {
            "total_candidates": len(library.get_all_queries()),
            "applicable_queries": len([
                q for q in library.get_all_queries()
                if ranker._check_applicability(q, analysis)
            ]),
            "returned_suggestions": len(suggestions),
            "focus": focus,
        }
    }
