"""Query assistance layer for VQL.

This package provides components that help LLMs use VQL effectively:
- Query suggester: Recommends queries based on contract analysis
- Property explorer: Explains what properties mean
- Example library: Shows queries that found real vulnerabilities
- Effectiveness tracker: Learns which queries work best
"""

from .contract_analyzer import ContractAnalysis, analyze_contract
from .query_suggester import suggest_queries, QuerySuggestion

__all__ = [
    "ContractAnalysis",
    "analyze_contract",
    "suggest_queries",
    "QuerySuggestion",
]
