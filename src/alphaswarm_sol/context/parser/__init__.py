"""Protocol context parser module for VKG.

This module provides tools to extract protocol context from both
code analysis and documentation parsing:

Code Analysis (code_analyzer.py):
- CodeAnalyzer: Extract context from VKG KnowledgeGraph
- AnalysisResult: Result dataclass with roles, assumptions, etc.
- OPERATION_ASSUMPTIONS: Mapping of operations to inferred assumptions
- ROLE_CAPABILITIES: Mapping of modifiers to role capabilities

Document Parsing (doc_parser.py):
- DocParser: LLM-driven extraction from documentation
- DocParseResult: Result dataclass with extracted context

Document Discovery (web_fetcher.py):
- WebFetcher: Auto-discover and fetch protocol docs
- FetchedDocument: Fetched document with metadata

Usage:
    from alphaswarm_sol.context.parser import (
        # Code analysis
        CodeAnalyzer, AnalysisResult,
        # Doc parsing
        DocParser, DocParseResult,
        # Document discovery
        WebFetcher, FetchedDocument,
    )

    # Analyze code
    graph = build_kg("contracts/")
    code_analyzer = CodeAnalyzer(graph)
    code_result = code_analyzer.analyze()

    # Discover and fetch docs
    fetcher = WebFetcher(Path("project/"))
    docs = await fetcher.fetch_all()

    # Parse docs with LLM
    doc_parser = DocParser()
    for doc in docs:
        doc_result = await doc_parser.parse(doc)
"""

from .code_analyzer import (
    CodeAnalyzer,
    AnalysisResult,
    OPERATION_ASSUMPTIONS,
    ROLE_CAPABILITIES,
    ROLE_TRUST_ASSUMPTIONS,
)

from .doc_parser import (
    DocParser,
    DocParseResult,
    CrossValidationResult,
)

from .web_fetcher import (
    WebFetcher,
    FetchedDocument,
    DiscoveredSource,
    SourceType,
    SourceTier,
    SOURCE_TIER_MAP,
)


__all__ = [
    # Code analyzer
    "CodeAnalyzer",
    "AnalysisResult",
    "OPERATION_ASSUMPTIONS",
    "ROLE_CAPABILITIES",
    "ROLE_TRUST_ASSUMPTIONS",
    # Doc parser
    "DocParser",
    "DocParseResult",
    "CrossValidationResult",
    # Web fetcher
    "WebFetcher",
    "FetchedDocument",
    "DiscoveredSource",
    "SourceType",
    "SourceTier",
    "SOURCE_TIER_MAP",
]
