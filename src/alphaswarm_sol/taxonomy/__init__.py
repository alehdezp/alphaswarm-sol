"""Phase 13: Risk Tag Taxonomy.

This module provides a hierarchical risk tag system based on OpenSCV taxonomy
for classifying smart contract vulnerabilities.

Key features:
- Hierarchical tag system with categories and sub-tags
- Tag assignment with confidence scoring
- Tag storage on graph nodes
- Tag-based pattern matching
"""

from alphaswarm_sol.taxonomy.tags import (
    RiskCategory,
    RiskTag,
    RISK_TAG_HIERARCHY,
    RISK_TAG_DESCRIPTIONS,
    get_tag_category,
    get_tags_in_category,
    get_all_tags,
    is_valid_tag,
    get_parent_category,
)
from alphaswarm_sol.taxonomy.assignment import (
    TagAssignment,
    TagAssigner,
    assign_tags_from_properties,
    assign_tags_from_operations,
)
from alphaswarm_sol.taxonomy.storage import (
    NodeTags,
    TagStore,
    add_tag_to_node,
    get_node_tags,
    query_nodes_by_tag,
)
from alphaswarm_sol.taxonomy.matching import (
    TagMatcher,
    TagMatchResult,
    match_tag_pattern,
    has_risk_tag,
)

__all__ = [
    # Tags
    "RiskCategory",
    "RiskTag",
    "RISK_TAG_HIERARCHY",
    "RISK_TAG_DESCRIPTIONS",
    "get_tag_category",
    "get_tags_in_category",
    "get_all_tags",
    "is_valid_tag",
    "get_parent_category",
    # Assignment
    "TagAssignment",
    "TagAssigner",
    "assign_tags_from_properties",
    "assign_tags_from_operations",
    # Storage
    "NodeTags",
    "TagStore",
    "add_tag_to_node",
    "get_node_tags",
    "query_nodes_by_tag",
    # Matching
    "TagMatcher",
    "TagMatchResult",
    "match_tag_pattern",
    "has_risk_tag",
]
