"""Vulnerability Knowledge Documentation System (VulnDocs).

Phase 17-18: Granular, navigable vulnerability knowledge for LLM-powered analysis.

Key Components:
- schema.py: Knowledge schema definitions (Phase 17)
- knowledge_doc.py: Multi-model document schema (Phase 18.2)
- agents/: Multi-model agent system (Phase 18.2)
- pipeline/: Processing pipeline (Phase 18.2)
- navigator.py: API for navigating knowledge hierarchy
- cache.py: Prompt caching integration
- builder.py: Context building from docs
- llm_interface.py: LLM navigation interface

Design Principles:
1. Granular Structure: Fine-grained categories → subcategories → patterns
2. Minimal Context: Each doc contains only what's needed
3. Navigable Hierarchy: LLMs can discover and traverse the knowledge tree
4. Cacheable Blocks: Stable content cached for token efficiency
5. Self-Improving: Solodit skill extracts new patterns automatically
6. Dual Navigation: Python API or LLM agent can navigate
7. Multi-Model: Haiku for bulk processing, Opus for intelligent decisions

Usage:
    from alphaswarm_sol.vulndocs import VulnDocsNavigator

    nav = VulnDocsNavigator()

    # Get context for specific vulnerability
    context = nav.get_context(
        category="reentrancy",
        subcategory="classic",
        depth="detection",
    )

    # Get context for multiple findings
    context = nav.get_context_for_findings(findings)

    # Multi-model pipeline (Phase 18.2)
    from alphaswarm_sol.vulndocs.knowledge_doc import VulnKnowledgeDoc
    from alphaswarm_sol.vulndocs.agents import CategoryAgent, MergeOrchestrator
"""

from alphaswarm_sol.vulndocs.schema import (
    CategoryIndex,
    DetectionDocument,
    DocumentType,
    KnowledgeDepth,
    PatternDocument,
    SubcategoryIndex,
    VulnCategory,
    VulnSubcategory,
    # Phase 5.4 Unified Schema Models
    VulnDocIndex,
    PatternRef,
    VulnDocCategory,
    TestCoverage,
    generate_json_schema,
    load_vulndoc_index,
    load_pattern_ref,
)
from alphaswarm_sol.vulndocs.types import (
    Severity as SeverityEnum,
    ValidationLevel,
)
from alphaswarm_sol.vulndocs.knowledge_doc import (
    DetectionSection,
    DocMetadata,
    ExamplesSection,
    ExploitationSection,
    MergeConflict,
    MergeResult,
    MitigationSection,
    PatternLinkage,
    PatternLinkageType,
    Prevalence,
    RealExploitRef,
    Severity,
    SourceSummary,
    UniqueIdea,
    VulnKnowledgeDoc,
)
from alphaswarm_sol.vulndocs.validation import (
    ValidationResult,
    FrameworkValidationResult,
    validate_vulnerability,
    validate_framework,
    suggest_research,
)
from alphaswarm_sol.vulndocs.discovery import (
    CategoryInfo,
    VulnerabilityInfo,
    PatternInfo,
    discover_categories,
    discover_vulnerabilities,
    discover_patterns,
    get_expected_files,
)

__all__ = [
    # Phase 17 Schema
    "CategoryIndex",
    "DetectionDocument",
    "DocumentType",
    "KnowledgeDepth",
    "PatternDocument",
    "SubcategoryIndex",
    "VulnCategory",
    "VulnSubcategory",
    # Phase 18 Knowledge Doc
    "DetectionSection",
    "DocMetadata",
    "ExamplesSection",
    "ExploitationSection",
    "MergeConflict",
    "MergeResult",
    "MitigationSection",
    "PatternLinkage",
    "PatternLinkageType",
    "Prevalence",
    "RealExploitRef",
    "Severity",
    "SourceSummary",
    "UniqueIdea",
    "VulnKnowledgeDoc",
    # Phase 5.4 Unified Schema
    "VulnDocIndex",
    "PatternRef",
    "VulnDocCategory",
    "TestCoverage",
    "SeverityEnum",
    "ValidationLevel",
    "generate_json_schema",
    "load_vulndoc_index",
    "load_pattern_ref",
    # Phase 5.4 Validation (Plan 03)
    "ValidationResult",
    "FrameworkValidationResult",
    "validate_vulnerability",
    "validate_framework",
    "suggest_research",
    # Phase 5.4 Discovery (Plan 03)
    "CategoryInfo",
    "VulnerabilityInfo",
    "PatternInfo",
    "discover_categories",
    "discover_vulnerabilities",
    "discover_patterns",
    "get_expected_files",
]
