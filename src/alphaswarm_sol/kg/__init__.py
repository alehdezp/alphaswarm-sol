"""Knowledge graph core for True VKG."""

from alphaswarm_sol.kg.builder import VKGBuilder
from alphaswarm_sol.kg.property_sets import (
    CORE_PROPERTIES,
    PROPERTY_SETS,
    PropertySet,
    VulnerabilityCategory,
    get_all_categories,
    get_category_from_pattern_id,
    get_property_set,
    get_relevant_properties,
    is_property_relevant,
)
from alphaswarm_sol.kg.schema import Edge, Evidence, KnowledgeGraph, Node
from alphaswarm_sol.kg.slicer import (
    GraphSlicer,
    SlicedGraph,
    SlicingStats,
    calculate_slicing_impact,
    slice_graph_for_category,
    slice_graph_for_finding,
)
from alphaswarm_sol.kg.slicing_benchmark import (
    SlicingBenchmark,
    compare_full_vs_sliced,
    generate_benchmark_report,
    run_slicing_benchmark,
    validate_slicing_for_detection,
)
from alphaswarm_sol.kg.ppr import (
    PPRConfig,
    PPRResult,
    VKGPPR,
    get_relevant_nodes_ppr,
    run_ppr,
)
from alphaswarm_sol.kg.ppr_weights import (
    BASE_WEIGHTS,
    calculate_edge_weight,
    create_analysis_weights,
    normalize_weights,
)
from alphaswarm_sol.kg.seed_mapper import (
    SeedMapper,
    SeedMapping,
    SeedNode,
    SeedType,
    extract_seeds_for_ppr,
    map_query_to_ppr_result,
)
from alphaswarm_sol.kg.ppr_subgraph import (
    PPRExtractionConfig,
    PPRSubgraphExtractor,
    PPRSubgraphResult,
    extract_ppr_subgraph,
    extract_ppr_subgraph_for_findings,
)
from alphaswarm_sol.kg.store import GraphStore
from alphaswarm_sol.kg.toon import toon_dump, toon_dumps, toon_load, toon_loads

# Phase 5.9: Graph Build Hash
from alphaswarm_sol.kg.graph_hash import (
    BuildHashError,
    BuildHashTracker,
    compute_graph_hash,
    compute_source_hash,
    compute_content_hash,
    compute_incremental_hash,
    validate_build_hash,
    validate_build_hash_strict,
    check_build_hash_consistency,
    embed_build_hash,
    extract_build_hash,
    BUILD_HASH_LENGTH,
    BUILD_HASH_PATTERN,
)

# Phase 5.10: Canonical Evidence IDs
from alphaswarm_sol.kg.evidence_id import (
    evidence_id_for,
    evidence_id_for_evidence,
    evidence_ids_for_node,
    compute_evidence_id_deterministic,
    CanonicalEvidenceID,
    EvidenceIDRegistry,
    EvidenceIDError,
    EvidenceResolutionError,
    validate_evidence_id,
    EVIDENCE_ID_PATTERN,
)

__all__ = [
    "VKGBuilder",
    "GraphStore",
    "KnowledgeGraph",
    "Node",
    "Edge",
    "Evidence",
    # Property sets for graph slicing
    "VulnerabilityCategory",
    "PropertySet",
    "PROPERTY_SETS",
    "CORE_PROPERTIES",
    "get_property_set",
    "get_relevant_properties",
    "is_property_relevant",
    "get_all_categories",
    "get_category_from_pattern_id",
    # Graph slicer
    "GraphSlicer",
    "SlicedGraph",
    "SlicingStats",
    "slice_graph_for_category",
    "slice_graph_for_finding",
    "calculate_slicing_impact",
    # Slicing benchmark
    "SlicingBenchmark",
    "run_slicing_benchmark",
    "compare_full_vs_sliced",
    "generate_benchmark_report",
    "validate_slicing_for_detection",
    # PPR algorithm
    "PPRConfig",
    "PPRResult",
    "VKGPPR",
    "run_ppr",
    "get_relevant_nodes_ppr",
    # PPR weights
    "BASE_WEIGHTS",
    "calculate_edge_weight",
    "create_analysis_weights",
    "normalize_weights",
    # Seed mapper
    "SeedMapper",
    "SeedMapping",
    "SeedNode",
    "SeedType",
    "extract_seeds_for_ppr",
    "map_query_to_ppr_result",
    # PPR subgraph extraction
    "PPRExtractionConfig",
    "PPRSubgraphExtractor",
    "PPRSubgraphResult",
    "extract_ppr_subgraph",
    "extract_ppr_subgraph_for_findings",
    # TOON serialization utilities
    "toon_dumps",
    "toon_loads",
    "toon_dump",
    "toon_load",
    # Phase 5.9: Graph build hash
    "BuildHashError",
    "BuildHashTracker",
    "compute_graph_hash",
    "compute_source_hash",
    "compute_content_hash",
    "compute_incremental_hash",
    "validate_build_hash",
    "validate_build_hash_strict",
    "check_build_hash_consistency",
    "embed_build_hash",
    "extract_build_hash",
    "BUILD_HASH_LENGTH",
    "BUILD_HASH_PATTERN",
    # Phase 5.10: Canonical evidence IDs
    "evidence_id_for",
    "evidence_id_for_evidence",
    "evidence_ids_for_node",
    "compute_evidence_id_deterministic",
    "CanonicalEvidenceID",
    "EvidenceIDRegistry",
    "EvidenceIDError",
    "EvidenceResolutionError",
    "validate_evidence_id",
    "EVIDENCE_ID_PATTERN",
]
