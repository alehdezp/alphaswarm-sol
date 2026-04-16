"""VulnDocs Knowledge Schema Package.

DEPRECATED: This module is deprecated. Use alphaswarm_sol.vulndocs instead.
The VulnDocs content has been unified under vulndocs/ directory.

Phase 17.0: Knowledge Schema Design for VulnDocs.
Phase 17.2: Document Templates for VulnDocs.
Phase 17.4: Knowledge Navigator API for VulnDocs.
Phase 17.5: Prompt Cache Integration for VulnDocs.
Phase 17.6: Context Builder for VulnDocs.
Phase 17.7: LLM Navigation Interface for VulnDocs.

This package provides the Python schema classes for the VulnDocs knowledge
system, which now lives under vulndocs/ directory. The schema classes enable:

1. Parsing and validation of YAML knowledge files
2. Type-safe navigation of the knowledge hierarchy
3. Integration with the existing alphaswarm_sol.vulndocs module
4. Template generation for document types (detection, patterns, exploits, fixes)
5. Programmatic navigation with caching and search capabilities
6. Prompt caching for efficient LLM interactions
7. Context building for LLM context optimization
8. LLM navigation interface with tool definitions

Design Philosophy:
- Behavior-first: Focus on semantic operations, not names
- Evidence-linked: Every finding links to code locations
- Minimal context: Each doc contains only what's needed
- Cacheable: Stable content blocks for token efficiency

Usage:
    from alphaswarm_sol.knowledge.vulndocs import (
        Category,
        Subcategory,
        Document,
        KnowledgeIndex,
        load_index,
        validate_schema,
    )

    # Load the knowledge index
    index = load_index()

    # Get a specific category
    reentrancy = index.get_category("reentrancy")

    # Validate schema
    errors = validate_schema(data)

    # Generate document templates
    from alphaswarm_sol.knowledge.vulndocs import generate_document_templates
    templates = generate_document_templates("reentrancy", "classic")

    # Use the navigator API (Phase 17.4)
    from alphaswarm_sol.knowledge.vulndocs import KnowledgeNavigator
    navigator = KnowledgeNavigator()
    categories = navigator.search_by_operation("TRANSFERS_VALUE_OUT")
    context = navigator.get_context("reentrancy", "classic", KnowledgeDepth.DETECTION)

    # Use the prompt cache (Phase 17.5)
    from alphaswarm_sol.knowledge.vulndocs import PromptCache, CachedBlock
    cache = PromptCache(navigator)
    blocks = cache.preload_category("reentrancy")
    anthropic_messages = cache.format_for_anthropic(blocks)

    # Use the context builder (Phase 17.6)
    from alphaswarm_sol.knowledge.vulndocs import ContextBuilder, BuiltContext
    builder = ContextBuilder(navigator, cache)
    ctx = builder.build_for_pattern("vm-001-classic", max_tokens=4000)
    system_msg = format_as_system_message(ctx)

    # Use the LLM navigation interface (Phase 17.7)
    from alphaswarm_sol.knowledge.vulndocs import LLMNavigator, create_llm_navigator
    llm_nav = create_llm_navigator()
    tools = llm_nav.get_tool_definitions()  # OpenAI/Anthropic compatible
    result = llm_nav.execute_tool("list_categories", {})
"""

from alphaswarm_sol.knowledge.vulndocs.schema import (
    # Core dataclasses
    Category,
    Subcategory,
    Document,
    KnowledgeIndex,
    GraphSignal,
    CodePattern,
    ExploitReference,
    FixRecommendation,
    NavigationMetadata,
    CacheConfig,
    OperationSequences,
    SubcategoryRef,
    # Enums
    Severity,
    KnowledgeDepth,
    DocumentType,
    CacheControlType,
    # Loading functions
    load_index,
    load_category,
    load_subcategory,
    # Validation functions
    validate_category,
    validate_subcategory,
    validate_document,
    validate_index,
    # Constants
    SCHEMA_VERSION,
    KNOWLEDGE_DIR,
)

from alphaswarm_sol.knowledge.vulndocs.templates import (
    # Template dataclasses
    DetectionTemplate,
    PatternsTemplate,
    ExploitsTemplate,
    FixesTemplate,
    ExploitIncident,
    FixRecommendationExtended,
    # Rendering functions
    render_detection_md,
    render_patterns_md,
    render_exploits_md,
    render_fixes_md,
    # Generation helpers
    generate_document_templates,
    create_template_bundle,
    # Validation functions
    validate_detection_template,
    validate_patterns_template,
    validate_exploits_template,
    validate_fixes_template,
    # Constants
    TEMPLATE_VERSION,
    TOKEN_BUDGET,
)

from alphaswarm_sol.knowledge.vulndocs.navigator import (
    # Navigator class
    KnowledgeNavigator,
    CacheEntry,
    # Helper functions
    load_category_from_disk,
    load_subcategory_from_disk,
    load_document_from_disk,
    format_context_for_llm,
)

from alphaswarm_sol.knowledge.vulndocs.cache import (
    # Cache class
    PromptCache,
    CachedBlock,
    # Helper functions
    estimate_tokens,
    generate_cache_key,
    generate_content_hash,
    merge_cached_blocks,
    # Constants
    CHARS_PER_TOKEN,
    MIN_TOKENS_FOR_CACHE,
    MAX_CACHE_ENTRIES,
)

from alphaswarm_sol.knowledge.vulndocs.builder import (
    # Builder class
    ContextBuilder,
    # Dataclasses
    ContextSource,
    BuiltContext,
    # Format functions
    format_as_system_message,
    format_as_user_context,
    format_for_bead,
    # Constants
    DEFAULT_MAX_TOKENS,
    MIN_TOKENS_PER_SOURCE,
    PRIORITY_CRITICAL,
    PRIORITY_HIGH,
    PRIORITY_MEDIUM,
    PRIORITY_LOW,
    PRIORITY_NAVIGATION,
    PATTERN_CATEGORY_MAP,
    OPERATION_CATEGORY_MAP,
)

from alphaswarm_sol.knowledge.vulndocs.llm_interface import (
    # LLM Navigator class
    LLMNavigator,
    # Dataclasses
    LLMNavigationTool,
    NavigationState,
    ToolExecutionResult,
    # Factory function
    create_llm_navigator,
    # Helper function
    get_tool_names,
    # Tool name constants
    TOOL_LIST_CATEGORIES,
    TOOL_GET_CATEGORY_INFO,
    TOOL_GET_SUBCATEGORY_INFO,
    TOOL_GET_DETECTION_GUIDE,
    TOOL_GET_PATTERNS,
    TOOL_GET_EXPLOITS,
    TOOL_GET_FIXES,
    TOOL_SEARCH_BY_OPERATION,
    TOOL_SEARCH_BY_SIGNATURE,
    ALL_TOOLS,
)

__all__ = [
    # Core dataclasses
    "Category",
    "Subcategory",
    "Document",
    "KnowledgeIndex",
    "GraphSignal",
    "CodePattern",
    "ExploitReference",
    "FixRecommendation",
    "NavigationMetadata",
    "CacheConfig",
    "OperationSequences",
    "SubcategoryRef",
    # Enums
    "Severity",
    "KnowledgeDepth",
    "DocumentType",
    "CacheControlType",
    # Loading functions
    "load_index",
    "load_category",
    "load_subcategory",
    # Validation functions
    "validate_category",
    "validate_subcategory",
    "validate_document",
    "validate_index",
    # Constants
    "SCHEMA_VERSION",
    "KNOWLEDGE_DIR",
    # Template dataclasses (Phase 17.2)
    "DetectionTemplate",
    "PatternsTemplate",
    "ExploitsTemplate",
    "FixesTemplate",
    "ExploitIncident",
    "FixRecommendationExtended",
    # Template rendering functions
    "render_detection_md",
    "render_patterns_md",
    "render_exploits_md",
    "render_fixes_md",
    # Template generation helpers
    "generate_document_templates",
    "create_template_bundle",
    # Template validation functions
    "validate_detection_template",
    "validate_patterns_template",
    "validate_exploits_template",
    "validate_fixes_template",
    # Template constants
    "TEMPLATE_VERSION",
    "TOKEN_BUDGET",
    # Navigator (Phase 17.4)
    "KnowledgeNavigator",
    "CacheEntry",
    # Navigator helper functions
    "load_category_from_disk",
    "load_subcategory_from_disk",
    "load_document_from_disk",
    "format_context_for_llm",
    # Cache (Phase 17.5)
    "PromptCache",
    "CachedBlock",
    # Cache helper functions
    "estimate_tokens",
    "generate_cache_key",
    "generate_content_hash",
    "merge_cached_blocks",
    # Cache constants
    "CHARS_PER_TOKEN",
    "MIN_TOKENS_FOR_CACHE",
    "MAX_CACHE_ENTRIES",
    # Builder (Phase 17.6)
    "ContextBuilder",
    "ContextSource",
    "BuiltContext",
    # Builder format functions
    "format_as_system_message",
    "format_as_user_context",
    "format_for_bead",
    # Builder constants
    "DEFAULT_MAX_TOKENS",
    "MIN_TOKENS_PER_SOURCE",
    "PRIORITY_CRITICAL",
    "PRIORITY_HIGH",
    "PRIORITY_MEDIUM",
    "PRIORITY_LOW",
    "PRIORITY_NAVIGATION",
    "PATTERN_CATEGORY_MAP",
    "OPERATION_CATEGORY_MAP",
    # LLM Interface (Phase 17.7)
    "LLMNavigator",
    "LLMNavigationTool",
    "NavigationState",
    "ToolExecutionResult",
    # LLM Interface factory
    "create_llm_navigator",
    # LLM Interface helper
    "get_tool_names",
    # Tool name constants
    "TOOL_LIST_CATEGORIES",
    "TOOL_GET_CATEGORY_INFO",
    "TOOL_GET_SUBCATEGORY_INFO",
    "TOOL_GET_DETECTION_GUIDE",
    "TOOL_GET_PATTERNS",
    "TOOL_GET_EXPLOITS",
    "TOOL_GET_FIXES",
    "TOOL_SEARCH_BY_OPERATION",
    "TOOL_SEARCH_BY_SIGNATURE",
    "ALL_TOOLS",
]
