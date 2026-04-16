"""Pattern packs for deterministic vulnerability checks.

Phase 3 introduces operation-based matchers:
- has_operation: Check if a single operation exists
- has_all_operations: Check if all operations exist
- has_any_operation: Check if any operation exists
- sequence_order: Check if operations occur in specific order
- signature_matches: Regex match on behavioral signature
"""

from __future__ import annotations

import functools
import json
import logging
import re
import warnings
from dataclasses import dataclass, field
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Any, TYPE_CHECKING

import yaml

from alphaswarm_sol.kg.schema import Edge, KnowledgeGraph, Node
from alphaswarm_sol.queries.errors import (
    EmptyPatternStoreError,
    PatternDirectoryNotFoundError,
)
from alphaswarm_sol.vulndocs.resolution import vulndocs_read_path

logger = logging.getLogger(__name__)


def _deprecated(reason: str):
    """Mark a callable as deprecated with migration instructions."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            warnings.warn(
                f"{func.__qualname__} is deprecated: {reason}",
                DeprecationWarning,
                stacklevel=2,
            )
            return func(*args, **kwargs)
        return wrapper
    return decorator

if TYPE_CHECKING:
    from alphaswarm_sol.taxonomy.storage import TagStore
    from alphaswarm_sol.queries.tier_b import TierBMatcher


SUPPORTED_SEVERITIES = {"critical", "high", "medium", "low", "info"}

# Valid semantic operations (from operations.py SemanticOperation enum)
VALID_OPERATIONS = frozenset({
    "TRANSFERS_VALUE_OUT", "RECEIVES_VALUE_IN", "READS_USER_BALANCE", "WRITES_USER_BALANCE",
    "CHECKS_PERMISSION", "MODIFIES_OWNER", "MODIFIES_ROLES",
    "CALLS_EXTERNAL", "CALLS_UNTRUSTED", "READS_EXTERNAL_VALUE",
    "MODIFIES_CRITICAL_STATE", "INITIALIZES_STATE", "READS_ORACLE",
    "LOOPS_OVER_ARRAY", "USES_TIMESTAMP", "USES_BLOCK_DATA",
    "PERFORMS_DIVISION", "PERFORMS_MULTIPLICATION",
    "VALIDATES_INPUT", "EMITS_EVENT",
})


@dataclass
class Condition:
    """Single property condition."""

    property: str
    op: str
    value: Any


@dataclass
class OperationCondition:
    """Operation-based condition (Phase 3).

    Types:
    - has_operation: Single operation must exist
    - has_all_operations: All operations must exist
    - has_any_operation: At least one operation must exist
    - sequence_order: Operation ordering constraint
    - signature_matches: Behavioral signature regex
    """

    type: str  # "has_operation", "has_all_operations", etc.
    value: Any  # Depends on type


@dataclass
class EdgeRequirement:
    """Edge requirement from a scoped node."""

    type: str
    direction: str = "out"  # out | in | any
    target_type: str | None = None


@dataclass
class PathStep:
    """Single step in a path traversal."""

    edge_type: str
    direction: str = "out"  # out | in | any
    target_type: str | None = None


@dataclass
class PathRequirement:
    """Path requirement with steps or bounded traversal."""

    steps: list[PathStep] = field(default_factory=list)
    edge_type: str | None = None
    direction: str = "out"
    max_depth: int = 3
    target_type: str | None = None


@dataclass
class TierBConditionSpec:
    """Tier B condition specification (Phase 14).

    Stores parsed tier_b conditions for risk tag matching.
    """
    type: str  # "has_risk_tag", "has_any_risk_tag", "has_all_risk_tags", "has_category"
    value: Any  # Tag name(s) or category
    min_confidence: str = "medium"  # "low", "medium", "high", "very_high"


@dataclass
class TierCConditionSpec:
    """Tier C condition specification (Phase 5).

    Stores parsed tier_c conditions for semantic label matching.

    Attributes:
        type: Condition type (has_label, has_any_label, has_all_labels, missing_label, has_category, label_confidence)
        value: Label ID(s) or category name
        min_confidence: Minimum confidence for match ("low", "medium", "high")
        context: Optional analysis context for filtering
    """
    type: str  # "has_label", "has_any_label", "has_all_labels", "missing_label", "has_category", "label_confidence"
    value: Any  # Label ID(s), category, or {label, confidence} dict
    min_confidence: str = "medium"  # "low", "medium", "high"
    context: str | None = None  # Optional analysis context for filtering


@dataclass
class PatternDefinition:
    """Pattern definition loaded from YAML/JSON."""

    id: str
    name: str
    description: str
    scope: str
    lens: list[str] = field(default_factory=list)
    severity: str = "medium"
    match_all: list[Condition] = field(default_factory=list)
    match_any: list[Condition] = field(default_factory=list)
    match_none: list[Condition] = field(default_factory=list)
    edges: list[EdgeRequirement] = field(default_factory=list)
    paths: list[PathRequirement] = field(default_factory=list)
    # Phase 3: Operation-based conditions
    ops_all: list[OperationCondition] = field(default_factory=list)
    ops_any: list[OperationCondition] = field(default_factory=list)
    ops_none: list[OperationCondition] = field(default_factory=list)
    # Phase 3: Aggregation mode for tier results
    # - tier_a_only: Only tier_a results matter
    # - tier_a_required: tier_a must match, tier_b provides context
    # - voting: Multiple tiers vote on match (future)
    aggregation_mode: str = "tier_a_only"
    # Phase 14: Tier B conditions for risk tag matching
    tier_b_all: list[TierBConditionSpec] = field(default_factory=list)
    tier_b_any: list[TierBConditionSpec] = field(default_factory=list)
    tier_b_none: list[TierBConditionSpec] = field(default_factory=list)
    # Phase 14: Voting threshold (for voting mode)
    voting_threshold: int = 2
    # Phase 5: Tier C conditions for semantic label matching
    tier_c_all: list[TierCConditionSpec] = field(default_factory=list)
    tier_c_any: list[TierCConditionSpec] = field(default_factory=list)
    tier_c_none: list[TierCConditionSpec] = field(default_factory=list)
    # Phase 5: Required labels for pattern to run (prerequisite check)
    required_labels: list[str] = field(default_factory=list)


class PatternStore:
    """Load patterns from a directory tree."""

    def __init__(self, root: Path) -> None:
        if not isinstance(root, Path):
            raise TypeError(
                f"PatternStore requires Path, got {type(root).__name__}"
            )
        self.root = root

    @classmethod
    def load_vulndocs_patterns(cls, vulndocs_root: Path) -> list[PatternDefinition]:
        """Load patterns from VulnDocs patterns/ directories only.

        Avoids index.yaml files by scanning **/patterns/*.yml|*.yaml.
        Raises PatternDirectoryNotFoundError if path doesn't exist.
        Returns [] only if path exists but has no matching files.
        """
        if not vulndocs_root.exists():
            raise PatternDirectoryNotFoundError(vulndocs_root)

        store = cls(vulndocs_root)
        patterns: list[PatternDefinition] = []
        for path in sorted(vulndocs_root.glob("**/patterns/*.yml")):
            patterns.extend(store._load_file(path))
        for path in sorted(vulndocs_root.glob("**/patterns/*.yaml")):
            patterns.extend(store._load_file(path))
        return patterns

    @_deprecated("Use get_patterns() instead. load() crashes on vulndocs index.yaml files.")
    def load(self) -> list[PatternDefinition]:
        if not self.root.exists():
            raise PatternDirectoryNotFoundError(self.root)
        patterns: list[PatternDefinition] = []
        for path in sorted(self.root.rglob("*")):
            if path.is_dir():
                continue
            if path.suffix.lower() not in {".yaml", ".yml", ".json"}:
                continue
            patterns.extend(self._load_file(path))
        return patterns

    def _load_file(self, path: Path) -> list[PatternDefinition]:
        data = self._read(path)
        if isinstance(data, list):
            return [self._parse(item, path) for item in data]
        return [self._parse(data, path)]

    def _read(self, path: Path) -> Any:
        text = path.read_text(encoding="utf-8")
        if path.suffix.lower() == ".json":
            return json.loads(text)
        return yaml.safe_load(text)

    def _parse(self, data: dict[str, Any], path: Path) -> PatternDefinition:
        # Operation condition keys (Phase 3)
        OP_CONDITION_KEYS = {
            "has_operation", "has_all_operations", "has_any_operation",
            "sequence_order", "signature_matches"
        }

        def parse_conditions(items: list[dict[str, Any]] | None) -> tuple[list[Condition], list[OperationCondition]]:
            """Parse both property conditions and operation conditions."""
            conditions: list[Condition] = []
            op_conditions: list[OperationCondition] = []

            for item in items or []:
                # Check if this is an operation condition
                op_keys = set(item.keys()) & OP_CONDITION_KEYS
                if op_keys:
                    # It's an operation condition
                    for key in op_keys:
                        op_conditions.append(OperationCondition(type=key, value=item[key]))
                elif "property" in item:
                    # It's a regular property condition
                    # Default to 'eq' operator if not specified (shorthand form)
                    op = item.get("op", "eq")
                    conditions.append(Condition(item["property"], op, item.get("value")))

            return conditions, op_conditions

        edges = []
        for edge in data.get("edges", []) or []:
            edges.append(
                EdgeRequirement(
                    type=edge["type"],
                    direction=edge.get("direction", "out"),
                    target_type=edge.get("target_type"),
                )
            )

        paths = []
        for path in data.get("paths", []) or []:
            steps = []
            for step in path.get("steps", []) or []:
                steps.append(
                    PathStep(
                        edge_type=step["edge_type"],
                        direction=step.get("direction", "out"),
                        target_type=step.get("target_type"),
                    )
                )
            paths.append(
                PathRequirement(
                    steps=steps,
                    edge_type=path.get("edge_type"),
                    direction=path.get("direction", "out"),
                    max_depth=int(path.get("max_depth", 3)),
                    target_type=path.get("target_type"),
                )
            )

        severity = (data.get("severity") or "medium").lower()
        if severity not in SUPPORTED_SEVERITIES:
            severity = "medium"

        description = data.get("description", "")
        if not isinstance(description, str):
            description = json.dumps(description)

        # Parse conditions from match section
        # Support both old structure (match.all) and new tier structure (match.tier_a.all)
        match_data = data.get("match") or {}

        # Check if tier_a structure is used (Phase 3 Schema v2)
        if "tier_a" in match_data:
            tier_a_data = match_data.get("tier_a") or {}
            match_all, ops_all = parse_conditions(tier_a_data.get("all"))
            match_any, ops_any = parse_conditions(tier_a_data.get("any"))
            match_none, ops_none = parse_conditions(tier_a_data.get("none"))
        else:
            # Backward compatible: old flat structure
            match_all, ops_all = parse_conditions(match_data.get("all"))
            match_any, ops_any = parse_conditions(match_data.get("any"))
            match_none, ops_none = parse_conditions(match_data.get("none"))

        # Parse aggregation mode (defaults to tier_a_only)
        aggregation_data = data.get("aggregation") or {}
        aggregation_mode = aggregation_data.get("mode", "tier_a_only")
        if aggregation_mode not in {"tier_a_only", "tier_a_required", "voting"}:
            aggregation_mode = "tier_a_only"
        voting_threshold = int(aggregation_data.get("threshold", 2))

        # Phase 14: Parse tier_b conditions
        tier_b_all, tier_b_any, tier_b_none = self._parse_tier_b_conditions(match_data)

        # Phase 5: Parse tier_c conditions
        tier_c_all, tier_c_any, tier_c_none = self._parse_tier_c_conditions(match_data)
        required_labels = data.get("required_labels", []) or []

        return PatternDefinition(
            id=data["id"],
            name=data.get("name", data["id"]),
            description=description,
            scope=data.get("scope", "Function"),
            lens=list(data.get("lens") or []),
            severity=severity,
            match_all=match_all,
            match_any=match_any,
            match_none=match_none,
            edges=edges,
            paths=paths,
            ops_all=ops_all,
            ops_any=ops_any,
            ops_none=ops_none,
            aggregation_mode=aggregation_mode,
            tier_b_all=tier_b_all,
            tier_b_any=tier_b_any,
            tier_b_none=tier_b_none,
            voting_threshold=voting_threshold,
            tier_c_all=tier_c_all,
            tier_c_any=tier_c_any,
            tier_c_none=tier_c_none,
            required_labels=required_labels,
        )

    def _parse_tier_b_conditions(
        self,
        match_data: dict[str, Any],
    ) -> tuple[list[TierBConditionSpec], list[TierBConditionSpec], list[TierBConditionSpec]]:
        """Parse tier_b conditions from match data (Phase 14).

        Args:
            match_data: The match section from pattern YAML

        Returns:
            Tuple of (all_conditions, any_conditions, none_conditions)
        """
        TIER_B_CONDITION_KEYS = {
            "has_risk_tag", "has_any_risk_tag", "has_all_risk_tags", "has_category"
        }

        def parse_tier_b_item(item: dict[str, Any]) -> TierBConditionSpec | None:
            """Parse a single tier_b condition item."""
            cond_keys = set(item.keys()) & TIER_B_CONDITION_KEYS
            if not cond_keys:
                return None

            cond_type = list(cond_keys)[0]
            value = item[cond_type]
            min_confidence = item.get("min_confidence", "medium")
            if min_confidence not in {"low", "medium", "high", "very_high"}:
                min_confidence = "medium"

            return TierBConditionSpec(
                type=cond_type,
                value=value,
                min_confidence=min_confidence,
            )

        tier_b_data = match_data.get("tier_b") or {}
        tier_b_all: list[TierBConditionSpec] = []
        tier_b_any: list[TierBConditionSpec] = []
        tier_b_none: list[TierBConditionSpec] = []

        for item in tier_b_data.get("all", []) or []:
            cond = parse_tier_b_item(item)
            if cond:
                tier_b_all.append(cond)

        for item in tier_b_data.get("any", []) or []:
            cond = parse_tier_b_item(item)
            if cond:
                tier_b_any.append(cond)

        for item in tier_b_data.get("none", []) or []:
            cond = parse_tier_b_item(item)
            if cond:
                tier_b_none.append(cond)

        return tier_b_all, tier_b_any, tier_b_none

    def _parse_tier_c_conditions(
        self,
        match_data: dict[str, Any],
    ) -> tuple[list[TierCConditionSpec], list[TierCConditionSpec], list[TierCConditionSpec]]:
        """Parse tier_c conditions from match data (Phase 5).

        Supports both full dict format and shorthand string format.

        Args:
            match_data: The match section from pattern YAML

        Returns:
            Tuple of (all_conditions, any_conditions, none_conditions)

        Examples:
            Full format:
            ```yaml
            tier_c:
              all:
                - type: has_label
                  value: access_control.owner_only
                  min_confidence: high
                  context: access_control
            ```

            Shorthand format:
            ```yaml
            tier_c:
              all:
                - has_label: access_control.owner_only
                - has_any_label: [access_control.owner_only, access_control.role_based]
            ```
        """
        # Valid tier_c condition types
        TIER_C_CONDITION_KEYS = {
            "has_label", "has_any_label", "has_all_labels",
            "missing_label", "has_category", "label_confidence"
        }

        def parse_tier_c_item(item: dict[str, Any] | str) -> TierCConditionSpec | None:
            """Parse a single tier_c condition item.

            Args:
                item: Either a string (shorthand for has_label) or dict

            Returns:
                TierCConditionSpec or None if invalid
            """
            # Handle shorthand: just a string means has_label
            if isinstance(item, str):
                return TierCConditionSpec(
                    type="has_label",
                    value=item,
                    min_confidence="medium",
                    context=None,
                )

            if not isinstance(item, dict):
                return None

            # Check for explicit type field (full format)
            if "type" in item:
                cond_type = item["type"]
                if cond_type not in TIER_C_CONDITION_KEYS:
                    return None
                return TierCConditionSpec(
                    type=cond_type,
                    value=item.get("value") or item.get("label") or item.get("labels"),
                    min_confidence=item.get("min_confidence", "medium"),
                    context=item.get("context"),
                )

            # Check for shorthand condition keys (e.g., has_label: value)
            cond_keys = set(item.keys()) & TIER_C_CONDITION_KEYS
            if not cond_keys:
                return None

            cond_type = list(cond_keys)[0]
            value = item[cond_type]
            min_confidence = item.get("min_confidence", "medium")
            if min_confidence not in {"low", "medium", "high"}:
                min_confidence = "medium"

            return TierCConditionSpec(
                type=cond_type,
                value=value,
                min_confidence=min_confidence,
                context=item.get("context"),
            )

        tier_c_data = match_data.get("tier_c") or {}
        tier_c_all: list[TierCConditionSpec] = []
        tier_c_any: list[TierCConditionSpec] = []
        tier_c_none: list[TierCConditionSpec] = []

        for item in tier_c_data.get("all", []) or []:
            cond = parse_tier_c_item(item)
            if cond:
                tier_c_all.append(cond)

        for item in tier_c_data.get("any", []) or []:
            cond = parse_tier_c_item(item)
            if cond:
                tier_c_any.append(cond)

        for item in tier_c_data.get("none", []) or []:
            cond = parse_tier_c_item(item)
            if cond:
                tier_c_none.append(cond)

        return tier_c_all, tier_c_any, tier_c_none


def _walk_pattern_files(root: Traversable) -> list[Traversable]:
    """Walk a Traversable tree to find pattern YAML files.

    Finds files matching **/patterns/*.yml and **/patterns/*.yaml
    using only the Traversable API (.iterdir(), .is_dir(), .is_file(), .name).
    """
    results: list[Traversable] = []

    def _recurse(node: Traversable) -> None:
        try:
            children = list(node.iterdir())
        except (OSError, TypeError):
            return
        for child in sorted(children, key=lambda c: c.name):
            if child.is_dir():
                _recurse(child)
            elif child.is_file() and node.name == "patterns":
                if child.name.endswith(".yml") or child.name.endswith(".yaml"):
                    results.append(child)

    _recurse(root)
    return results


def get_patterns(pattern_dir: Path | Traversable | None = None) -> list[PatternDefinition]:
    """Load patterns from vulndocs directory -- THE canonical entry point.

    All production code and tests should call this function.
    Uses vulndocs_read_path() for cwd-independent resolution.
    Raises PatternDirectoryNotFoundError if directory doesn't exist.
    Raises EmptyPatternStoreError if no patterns found.
    """
    pdir: Traversable = pattern_dir if pattern_dir is not None else vulndocs_read_path()

    # If it's a concrete Path, use the fast glob-based loader
    if isinstance(pdir, Path):
        try:
            patterns = PatternStore.load_vulndocs_patterns(pdir)
        except PatternDirectoryNotFoundError:
            raise
        except OSError as e:
            raise PatternDirectoryNotFoundError(pdir) from e
        if not patterns:
            raise EmptyPatternStoreError(pdir)
        return patterns

    # Traversable path — use the Traversable-compatible walker
    pattern_files = _walk_pattern_files(pdir)
    if not pattern_files:
        raise PatternDirectoryNotFoundError(pdir)

    # Create a temporary store for parsing
    store = PatternStore.__new__(PatternStore)
    store.root = Path(".")  # Placeholder, not used for traversable loading
    patterns: list[PatternDefinition] = []
    for tfile in pattern_files:
        try:
            text = tfile.read_text(encoding="utf-8")
            data = yaml.safe_load(text)
            if isinstance(data, list):
                for item in data:
                    patterns.append(store._parse(item, Path(tfile.name)))
            elif data:
                patterns.append(store._parse(data, Path(tfile.name)))
        except Exception as e:
            logger.warning("Failed to load pattern from %s: %s", tfile.name, e)

    if not patterns:
        raise EmptyPatternStoreError(pdir)
    return patterns


class PatternEngine:
    """Evaluate patterns against a knowledge graph."""

    def __init__(
        self,
        tag_store: "TagStore | None" = None,
        pattern_dir: "Path | None" = None,
    ):
        """Initialize pattern engine.

        Args:
            tag_store: Optional tag store for Tier B matching.
                       If None, tags will be assigned on-demand.
            pattern_dir: Optional path to pattern directory.
                         Used by run_all_patterns() and run_pattern().
                         Defaults to vulndocs_read_path() resolution.
        """
        self._tag_store = tag_store
        self._pattern_dir = pattern_dir
        self._tier_b_matcher: "TierBMatcher | None" = None

    def _get_tier_b_matcher(self) -> "TierBMatcher":
        """Lazy-initialize Tier B matcher."""
        if self._tier_b_matcher is None:
            from alphaswarm_sol.queries.tier_b import TierBMatcher
            self._tier_b_matcher = TierBMatcher(self._tag_store)
        return self._tier_b_matcher

    def _load_patterns(self) -> list[PatternDefinition]:
        """Load patterns -- lenient wrapper for engine use.

        Unlike get_patterns(), this returns [] on missing dirs with a warning.
        Only used internally by PatternEngine where patterns are optional.
        """
        pdir: Path | Traversable = self._pattern_dir if self._pattern_dir is not None else vulndocs_read_path()
        if isinstance(pdir, Path) and not pdir.exists():
            logger.warning("Pattern directory not found: %s -- returning empty", pdir)
            return []
        # Use the canonical get_patterns() which handles both Path and Traversable
        try:
            return get_patterns(pdir)
        except (PatternDirectoryNotFoundError, EmptyPatternStoreError) as e:
            logger.warning("Failed to load patterns from %s: %s", pdir, e)
            return []

    def run_all_patterns(
        self,
        graph: KnowledgeGraph,
        *,
        lens: list[str] | None = None,
        severity: list[str] | None = None,
        limit: int = 50,
        explain: bool = False,
    ) -> list[dict[str, Any]]:
        """Load all patterns from pattern_dir and run them against the graph.

        Convenience method that combines pattern loading with execution.

        Args:
            graph: Knowledge graph to match against.
            lens: Optional lens filter.
            severity: Optional severity filter.
            limit: Max findings to return.
            explain: Whether to include match explanations.

        Returns:
            List of findings (dicts).
        """
        patterns = self._load_patterns()
        return self.run(
            graph, patterns, lens=lens, severity=severity, limit=limit, explain=explain
        )

    def run_pattern(
        self,
        graph: KnowledgeGraph,
        pattern_id: str,
        *,
        limit: int = 50,
        explain: bool = False,
    ) -> list[dict[str, Any]]:
        """Run a specific pattern (by ID) against the graph.

        Args:
            graph: Knowledge graph to match against.
            pattern_id: The pattern ID to run.
            limit: Max findings to return.
            explain: Whether to include match explanations.

        Returns:
            List of findings (dicts).
        """
        patterns = self._load_patterns()
        return self.run(
            graph, patterns, pattern_ids=[pattern_id], limit=limit, explain=explain
        )

    def run(
        self,
        graph: KnowledgeGraph,
        patterns: list[PatternDefinition],
        *,
        lens: list[str] | None = None,
        pattern_ids: list[str] | None = None,
        severity: list[str] | None = None,
        limit: int = 50,
        explain: bool = False,
    ) -> list[dict[str, Any]]:
        filtered = self._filter_patterns(patterns, lens, pattern_ids, severity)

        # Collect all available properties from the graph for orphan detection
        graph_props: set[str] = {"label", "type", "id", "name"}
        for node in graph.nodes.values():
            graph_props.update(node.properties.keys())

        findings: list[dict[str, Any]] = []
        for pattern in filtered:
            # Check for patterns whose conditions all reference unavailable properties
            all_cond_props = [c.property for c in pattern.match_all + pattern.match_any + pattern.match_none]
            if all_cond_props:
                missing = [p for p in all_cond_props if p not in graph_props]
                if len(missing) == len(all_cond_props):
                    logger.warning(
                        "Pattern %s skipped: all %d conditions reference "
                        "unavailable properties: %s",
                        pattern.id, len(missing), ", ".join(sorted(set(missing))),
                    )
                    continue
            for node in graph.nodes.values():
                if node.type != pattern.scope:
                    continue

                # Tier A matching
                tier_a_matched, tier_a_details = self._match_node(graph, node, pattern, explain)

                # Phase 14: Tier B matching and aggregation
                tier_result = self._aggregate_tiers(
                    node, pattern, tier_a_matched, tier_a_details, explain
                )

                if not tier_result["final_matched"]:
                    continue

                finding = {
                    "pattern_id": pattern.id,
                    "pattern_name": pattern.name,
                    "severity": pattern.severity,
                    "lens": pattern.lens,
                    "node_id": node.id,
                    "node_label": node.label,
                    "node_type": node.type,
                    "aggregation_mode": pattern.aggregation_mode,
                }
                if explain:
                    finding["explain"] = tier_result.get("explain", tier_a_details)
                findings.append(finding)
                if len(findings) >= limit:
                    return findings
        return findings

    def _aggregate_tiers(
        self,
        node: Node,
        pattern: PatternDefinition,
        tier_a_matched: bool,
        tier_a_details: dict[str, Any] | None,
        explain: bool,
    ) -> dict[str, Any]:
        """Aggregate Tier A and Tier B results based on mode.

        Args:
            node: Node being matched
            pattern: Pattern definition
            tier_a_matched: Whether Tier A matched
            tier_a_details: Tier A match details
            explain: Whether to include explanations

        Returns:
            Dict with final_matched and optional explain
        """
        mode = pattern.aggregation_mode
        has_tier_b = bool(pattern.tier_b_all or pattern.tier_b_any or pattern.tier_b_none)

        # Fast path: tier_a_only mode or no tier_b conditions
        if mode == "tier_a_only" or not has_tier_b:
            return {
                "final_matched": tier_a_matched,
                "explain": tier_a_details,
            }

        # tier_a_required mode: tier_a must match first
        if mode == "tier_a_required" and not tier_a_matched:
            return {
                "final_matched": False,
                "explain": tier_a_details,
            }

        # Match Tier B
        tier_b_result = self._match_tier_b(node, pattern, explain)

        # Aggregate based on mode
        if mode == "tier_a_required":
            # Tier A is gate, Tier B adds context
            combined_explain = tier_a_details or {} if explain else None
            if explain and tier_b_result.get("details"):
                combined_explain = dict(tier_a_details or {})
                combined_explain["tier_b"] = tier_b_result["details"]
            return {
                "final_matched": tier_a_matched,  # Tier A is the gate
                "tier_b_matched": tier_b_result.get("matched", False),
                "tier_b_context": tier_b_result,
                "explain": combined_explain,
            }

        if mode == "voting":
            # Both tiers vote
            matched_count = 0
            if tier_a_matched:
                matched_count += 1
            if tier_b_result.get("matched", False):
                matched_count += 1

            final_matched = matched_count >= pattern.voting_threshold

            combined_explain = None
            if explain:
                combined_explain = dict(tier_a_details or {})
                combined_explain["tier_b"] = tier_b_result.get("details", {})
                combined_explain["voting"] = {
                    "tier_a_matched": tier_a_matched,
                    "tier_b_matched": tier_b_result.get("matched", False),
                    "matched_count": matched_count,
                    "threshold": pattern.voting_threshold,
                    "final": final_matched,
                }

            return {
                "final_matched": final_matched,
                "explain": combined_explain,
            }

        # Default: tier_a result
        return {
            "final_matched": tier_a_matched,
            "explain": tier_a_details,
        }

    def _match_tier_b(
        self,
        node: Node,
        pattern: PatternDefinition,
        explain: bool,
    ) -> dict[str, Any]:
        """Match Tier B conditions using risk tags.

        Args:
            node: Node to match
            pattern: Pattern with tier_b conditions
            explain: Whether to include details

        Returns:
            Dict with matched status and optional details
        """
        from alphaswarm_sol.queries.tier_b import TierBCondition, ConfidenceLevel

        matcher = self._get_tier_b_matcher()

        # Convert TierBConditionSpec to TierBCondition
        def to_condition(spec: TierBConditionSpec) -> TierBCondition:
            try:
                min_conf = ConfidenceLevel(spec.min_confidence)
            except ValueError:
                min_conf = ConfidenceLevel.MEDIUM
            return TierBCondition(
                type=spec.type,
                value=spec.value,
                min_confidence=min_conf,
            )

        all_conds = [to_condition(s) for s in pattern.tier_b_all]
        any_conds = [to_condition(s) for s in pattern.tier_b_any]
        none_conds = [to_condition(s) for s in pattern.tier_b_none]

        result = matcher.match_tier_b(node, all_conds, any_conds, none_conds)

        details = None
        if explain:
            details = {
                "matched": result.matched,
                "matched_tags": [t.value for t in result.matched_tags],
                "confidence": result.confidence,
                "evidence": result.evidence,
            }

        return {
            "matched": result.matched,
            "details": details,
        }

    def _filter_patterns(
        self,
        patterns: list[PatternDefinition],
        lens: list[str] | None,
        pattern_ids: list[str] | None,
        severity: list[str] | None,
    ) -> list[PatternDefinition]:
        result = []
        lens_set = {l.lower() for l in (lens or [])}
        id_set = {p for p in (pattern_ids or [])}
        severity_set = {s.lower() for s in (severity or [])}
        for pattern in patterns:
            if lens_set and not lens_set.intersection({l.lower() for l in pattern.lens}):
                continue
            if id_set and pattern.id not in id_set:
                continue
            if severity_set and pattern.severity.lower() not in severity_set:
                continue
            result.append(pattern)
        return result

    def _match_node(
        self,
        graph: KnowledgeGraph,
        node: Node,
        pattern: PatternDefinition,
        explain: bool,
    ) -> tuple[bool, dict[str, Any] | None]:
        details = {"all": [], "any": [], "none": [], "edges": []} if explain else None

        if pattern.match_all:
            for cond in pattern.match_all:
                matched, note = self._match_condition(node, cond, explain)
                if explain and note:
                    details["all"].append(note)
                if not matched:
                    return False, details if explain else None

        if pattern.match_any:
            any_matched = False
            for cond in pattern.match_any:
                matched, note = self._match_condition(node, cond, explain)
                if explain and note:
                    details["any"].append(note)
                if matched:
                    any_matched = True
            if not any_matched:
                return False, details if explain else None

        if pattern.match_none:
            for cond in pattern.match_none:
                matched, note = self._match_condition(node, cond, explain)
                if explain and note:
                    details["none"].append(note)
                if matched:
                    return False, details if explain else None

        # Phase 3: Operation condition matching
        if pattern.ops_all:
            if explain:
                details["ops_all"] = []
            for op_cond in pattern.ops_all:
                matched, note = self._match_operation_condition(node, op_cond, explain)
                if explain and note:
                    details["ops_all"].append(note)
                if not matched:
                    return False, details if explain else None

        if pattern.ops_any:
            if explain:
                details["ops_any"] = []
            any_matched = False
            for op_cond in pattern.ops_any:
                matched, note = self._match_operation_condition(node, op_cond, explain)
                if explain and note:
                    details["ops_any"].append(note)
                if matched:
                    any_matched = True
            if not any_matched:
                return False, details if explain else None

        if pattern.ops_none:
            if explain:
                details["ops_none"] = []
            for op_cond in pattern.ops_none:
                matched, note = self._match_operation_condition(node, op_cond, explain)
                if explain and note:
                    details["ops_none"].append(note)
                if matched:
                    return False, details if explain else None

        if pattern.edges:
            edges_ok, edge_notes = self._match_edges(graph, node, pattern.edges, explain)
            if explain and edge_notes:
                details["edges"].extend(edge_notes)
            if not edges_ok:
                return False, details if explain else None

        if pattern.paths:
            paths_ok, path_notes = self._match_paths(graph, node, pattern.paths, explain)
            if explain and path_notes:
                details["paths"] = path_notes
            if not paths_ok:
                return False, details if explain else None

        return True, details if explain else None

    def _match_edges(
        self,
        graph: KnowledgeGraph,
        node: Node,
        edges: list[EdgeRequirement],
        explain: bool,
    ) -> tuple[bool, list[dict[str, Any]]]:
        notes: list[dict[str, Any]] = []
        for requirement in edges:
            matched = self._has_edge(graph, node, requirement)
            if explain:
                notes.append(
                    {
                        "edge_type": requirement.type,
                        "direction": requirement.direction,
                        "target_type": requirement.target_type,
                        "matched": matched,
                    }
                )
            if not matched:
                return False, notes
        return True, notes

    def _has_edge(self, graph: KnowledgeGraph, node: Node, requirement: EdgeRequirement) -> bool:
        for edge in graph.edges.values():
            if edge.type != requirement.type:
                continue
            if requirement.direction == "out" and edge.source != node.id:
                continue
            if requirement.direction == "in" and edge.target != node.id:
                continue
            if requirement.direction == "any" and node.id not in {edge.source, edge.target}:
                continue
            if requirement.target_type:
                target_id = edge.target if edge.source == node.id else edge.source
                target = graph.nodes.get(target_id)
                if not target or target.type != requirement.target_type:
                    continue
            return True
        return False

    def _match_paths(
        self,
        graph: KnowledgeGraph,
        node: Node,
        paths: list[PathRequirement],
        explain: bool,
    ) -> tuple[bool, list[dict[str, Any]]]:
        notes: list[dict[str, Any]] = []
        for path in paths:
            matched = self._path_exists(graph, node, path)
            if explain:
                notes.append(
                    {
                        "edge_type": path.edge_type,
                        "direction": path.direction,
                        "max_depth": path.max_depth,
                        "target_type": path.target_type,
                        "steps": [s.edge_type for s in path.steps] if path.steps else [],
                        "matched": matched,
                    }
                )
            if not matched:
                return False, notes
        return True, notes

    def _path_exists(self, graph: KnowledgeGraph, node: Node, path: PathRequirement) -> bool:
        if path.steps:
            current_nodes = {node.id}
            for step in path.steps:
                next_nodes = set()
                for nid in current_nodes:
                    next_nodes.update(self._walk_step(graph, nid, step))
                if step.target_type:
                    next_nodes = {nid for nid in next_nodes if graph.nodes.get(nid, None) and graph.nodes[nid].type == step.target_type}
                if not next_nodes:
                    return False
                current_nodes = next_nodes
            return True

        edge_type = path.edge_type
        if not edge_type:
            return False
        frontier = {node.id}
        visited = set(frontier)
        for _depth in range(path.max_depth):
            next_frontier = set()
            for nid in frontier:
                next_frontier.update(self._walk_edges(graph, nid, edge_type, path.direction))
            if path.target_type:
                for nid in next_frontier:
                    target = graph.nodes.get(nid)
                    if target and target.type == path.target_type:
                        return True
            if not next_frontier:
                return False
            frontier = next_frontier - visited
            visited.update(frontier)
        return not path.target_type and bool(frontier)

    def _walk_step(self, graph: KnowledgeGraph, node_id: str, step: PathStep) -> set[str]:
        return self._walk_edges(graph, node_id, step.edge_type, step.direction)

    def _walk_edges(self, graph: KnowledgeGraph, node_id: str, edge_type: str, direction: str) -> set[str]:
        next_nodes = set()
        for edge in graph.edges.values():
            if edge.type != edge_type:
                continue
            if direction == "out" and edge.source == node_id:
                next_nodes.add(edge.target)
            elif direction == "in" and edge.target == node_id:
                next_nodes.add(edge.source)
            elif direction == "any" and node_id in {edge.source, edge.target}:
                next_nodes.add(edge.target if edge.source == node_id else edge.source)
        return next_nodes

    def _match_condition(self, node: Node, condition: Condition, explain: bool) -> tuple[bool, dict[str, Any] | None]:
        value = _resolve_node_property(node, condition.property)
        op = condition.op
        expected = condition.value
        matched = False
        if op == "eq":
            matched = value == expected
        if op == "neq":
            matched = value != expected
        if op == "in":
            matched = value in (expected or [])
        if op == "not_in":
            matched = value not in (expected or [])
        if op == "contains_any":
            if not isinstance(value, list):
                matched = False
            else:
                matched = any(item in value for item in (expected or []))
        if op == "contains_all":
            if not isinstance(value, list):
                matched = False
            else:
                matched = all(item in value for item in (expected or []))
        if op == "gt":
            matched = _safe_compare(value, expected, lambda a, b: a > b)
        if op == "gte":
            matched = _safe_compare(value, expected, lambda a, b: a >= b)
        if op == "lt":
            matched = _safe_compare(value, expected, lambda a, b: a < b)
        if op == "lte":
            matched = _safe_compare(value, expected, lambda a, b: a <= b)
        if op == "regex":
            try:
                matched = bool(value) and bool(_regex_match(str(value), str(expected)))
            except Exception:
                matched = False
        note = None
        if explain:
            note = {
                "property": condition.property,
                "op": condition.op,
                "expected": expected,
                "actual": value,
                "matched": matched,
            }
        return matched, note

    def _match_operation_condition(
        self,
        node: Node,
        op_cond: OperationCondition,
        explain: bool
    ) -> tuple[bool, dict[str, Any] | None]:
        """Match operation-based conditions (Phase 3).

        Supports:
        - has_operation: Single operation must exist in semantic_ops
        - has_all_operations: All operations must exist in semantic_ops
        - has_any_operation: At least one operation must exist
        - sequence_order: Check if {before: X, after: Y} ordering exists
        - signature_matches: Regex match on behavioral_signature
        """
        semantic_ops = node.properties.get("semantic_ops", []) or []
        op_ordering = node.properties.get("op_ordering", []) or []
        behavioral_sig = node.properties.get("behavioral_signature", "") or ""

        matched = False
        cond_type = op_cond.type
        value = op_cond.value

        if cond_type == "has_operation":
            # Single operation check
            matched = value in semantic_ops

        elif cond_type == "has_all_operations":
            # All operations must exist
            ops_to_check = value if isinstance(value, list) else [value]
            matched = all(op in semantic_ops for op in ops_to_check)

        elif cond_type == "has_any_operation":
            # At least one operation must exist
            ops_to_check = value if isinstance(value, list) else [value]
            matched = any(op in semantic_ops for op in ops_to_check)

        elif cond_type == "sequence_order":
            # Check if {before: X, after: Y} ordering exists
            if isinstance(value, dict):
                before_op = value.get("before")
                after_op = value.get("after")
                if before_op and after_op:
                    # op_ordering is a list of (before, after) tuples
                    matched = any(
                        pair[0] == before_op and pair[1] == after_op
                        for pair in op_ordering
                    )

        elif cond_type == "signature_matches":
            # Regex match on behavioral_signature
            if behavioral_sig and value:
                try:
                    matched = bool(re.search(str(value), behavioral_sig))
                except re.error:
                    matched = False

        note = None
        if explain:
            actual = {
                "has_operation": semantic_ops,
                "has_all_operations": semantic_ops,
                "has_any_operation": semantic_ops,
                "sequence_order": op_ordering,
                "signature_matches": behavioral_sig,
            }.get(cond_type, None)

            note = {
                "condition_type": cond_type,
                "expected": value,
                "actual": actual,
                "matched": matched,
            }

        return matched, note


def _resolve_node_property(node: Node, name: str) -> Any:
    if name == "label":
        return node.label
    if name == "type":
        return node.type
    if name == "id":
        return node.id
    return node.properties.get(name)


def _safe_compare(value: Any, expected: Any, cmp) -> bool:
    try:
        return cmp(float(value), float(expected))
    except Exception:
        return False


def _regex_match(value: str, pattern: str) -> bool:
    import re

    return re.search(pattern, value) is not None
