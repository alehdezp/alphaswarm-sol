"""Graph Value Scorer — measures how well agents used the BSKG.

Implements the EvaluationPlugin protocol. Scores 0-100 based on:
- Query coverage: % of expected query types issued
- Citation rate: % of query results cited in conclusions (TranscriptParser primary)
- Graph-first compliance: BSKG queries before conclusions (timestamp-based)

Heuristic scoring demoted to STRUCTURAL_PROXY only (locked decision).
PRIMARY citation source: TranscriptParser.graph_citation_rate()
FALLBACK citation source: BSKG node ID structural matching ([FCE]-xxx-yyy)

No imports from alphaswarm_sol.kg (DC-2). Works entirely from
observation data and collected output.

CONTRACT_VERSION: 04.2
CONSUMERS: [3.1c-07 (Evaluator), 3.1c-08 (Runner)]
"""

from __future__ import annotations

import re
from typing import Any

from alphaswarm_sol.testing.evaluation.models import (
    DimensionScore,
    GraphValueScore,
    PluginScore,
)


# Default weights (calibrated via RS-01 spike)
DEFAULT_WEIGHTS = {
    "query_coverage": 0.35,
    "citation_rate": 0.35,
    "graph_first": 0.30,
}

# BSKG node ID pattern: F-contractName-functionName, C-xxx-yyy, E-xxx-yyy
_BSKG_NODE_ID_RE = re.compile(r"[FCE]-\w+-\w+")

# Dimensions that have no real handler — return applicable=False (DEFAULT-30 fix)
_UNIMPLEMENTED_DIMENSIONS = frozenset({
    "exploit_path_construction",
    "arbitration_quality",
    "evidence_weighing",
    "investigation_depth",
})


class GraphValueScorer:
    """Score how well an agent used the BSKG.

    Implements the EvaluationPlugin protocol:
    - name: "graph_value"
    - score(collected_output, context) -> PluginScore
    - explain(score) -> str

    Scoring dimensions:
    1. Query coverage: fraction of expected query types issued
    2. Citation rate: fraction of query results cited in conclusions
       (TranscriptParser primary, BSKG node ID fallback)
    3. Graph-first compliance: BSKG queries precede code reading
       (timestamp-based via obs_summary, conservative False when absent)

    Weights default to {query_coverage: 0.35, citation_rate: 0.35, graph_first: 0.30}.
    """

    def __init__(
        self,
        expected_query_types: list[str] | None = None,
        weights: dict[str, float] | None = None,
    ):
        self._expected_query_types = expected_query_types or [
            "build-kg", "query", "pattern-query", "analyze",
        ]
        self._weights = weights or dict(DEFAULT_WEIGHTS)

    @property
    def name(self) -> str:
        return "graph_value"

    def score(
        self,
        collected_output: Any,
        context: dict[str, Any] | None = None,
    ) -> GraphValueScore:
        """Score graph usage from a CollectedOutput.

        Args:
            collected_output: A CollectedOutput instance with
                bskg_queries, tool_sequence, and optionally transcript.
            context: Optional runtime context with obs_summary, contract, etc.
                - obs_summary: ObservationSummary for timestamp-based graph-first
                - contract: dict with run_gvs field
                - ground_truth_entry: dict for citation relevance

        Returns:
            GraphValueScore with scoring breakdown.
        """
        context = context or {}

        # run_gvs: false guard — early return without parsing
        contract = context.get("contract") or {}
        if isinstance(contract, dict) and contract.get("run_gvs") is False:
            return GraphValueScore(
                plugin_name=self.name,
                score=0,
                query_coverage=0.0,
                citation_rate=0.0,
                graph_first_compliant=False,
                graph_first_score=0.0,
                dimensions=self._all_inapplicable_dimensions(),
                details={"skipped": True, "reason": "run_gvs: false"},
            )

        bskg_queries = getattr(collected_output, "bskg_queries", [])
        transcript = getattr(collected_output, "transcript", None)
        obs_summary = context.get("obs_summary")

        # 1. Query coverage
        query_coverage = self._calc_query_coverage(bskg_queries)

        # 2. Citation rate — TranscriptParser PRIMARY, node ID fallback
        citation_rate = self._calc_citation_rate(
            transcript, bskg_queries, collected_output, obs_summary
        )

        # 2b. Apply result utilization penalty to citation_rate
        # Failed BSKG queries mean no result was returned to utilize
        utilization_penalty = self._get_result_utilization_penalty(obs_summary)
        citation_rate = max(0.0, citation_rate - utilization_penalty)

        # 3. Graph-first compliance — timestamp-based via obs_summary
        graph_first, graph_first_score = self._check_graph_first(obs_summary)

        # Weighted score (only from applicable dimensions)
        raw_score = (
            self._weights["query_coverage"] * query_coverage
            + self._weights["citation_rate"] * citation_rate
            + self._weights["graph_first"] * graph_first_score
        )
        final_score = int(min(100, max(0, raw_score * 100)))

        # Build dimensions list
        dimensions = self._build_dimensions(
            query_coverage, citation_rate, graph_first, graph_first_score, context
        )

        return GraphValueScore(
            plugin_name=self.name,
            score=final_score,
            query_coverage=query_coverage,
            citation_rate=citation_rate,
            graph_first_compliant=graph_first,
            graph_first_score=graph_first_score,
            dimensions=dimensions,
            details={
                "queries_issued": len(bskg_queries),
                "expected_types": self._expected_query_types,
                "types_found": self._get_query_types(bskg_queries),
                "weights": self._weights,
            },
        )

    def explain(self, plugin_score: PluginScore) -> str:
        """Human-readable explanation of the score."""
        if isinstance(plugin_score, GraphValueScore):
            parts = [
                f"Graph Value Score: {plugin_score.score}/100",
                f"  Query coverage: {plugin_score.query_coverage:.0%}",
                f"  Citation rate: {plugin_score.citation_rate:.0%}",
                f"  Graph-first: {'Yes' if plugin_score.graph_first_compliant else 'No'}",
            ]
            if hasattr(plugin_score, "graph_first_score"):
                parts.append(
                    f"  Graph-first score: {plugin_score.graph_first_score:.0%}"
                )
            return "\n".join(parts)
        return f"Graph Value Score: {plugin_score.score}/100"

    # --- Citation rate computation ---

    def _calc_citation_rate(
        self,
        transcript: Any,
        bskg_queries: list,
        collected_output: Any,
        obs_summary: Any,
    ) -> float:
        """Calculate citation rate with TranscriptParser as PRIMARY source.

        Priority:
        1. PRIMARY: transcript.graph_citation_rate() (TranscriptParser)
        2. FALLBACK: BSKG node ID structural matching from observations
           (STRUCTURAL_PROXY — cross-references [FCE]-xxx-yyy node IDs)
        """
        # PRIMARY: TranscriptParser
        if transcript is not None and hasattr(transcript, "graph_citation_rate"):
            rate = transcript.graph_citation_rate()
            if rate is not None:
                return rate

        # FALLBACK: BSKG node ID structural matching (STRUCTURAL_PROXY)
        if bskg_queries and obs_summary is not None:
            return self._citation_rate_from_node_ids(
                bskg_queries, collected_output, obs_summary
            )

        return 0.0

    def _citation_rate_from_node_ids(
        self,
        _bskg_queries: list,
        collected_output: Any,
        obs_summary: Any,
    ) -> float:
        """Fallback citation rate using BSKG node ID structural matching.

        Cross-references BSKG node IDs ([FCE]-xxx-yyy) from observation data
        against conclusion text. This is a STRUCTURAL_PROXY — uses the canonical
        node ID format, not keyword soup.
        """
        # Collect all node IDs from BSKG query events in obs_summary
        node_inventory = self._get_node_inventory(obs_summary)
        if not node_inventory:
            return 0.0

        # Get conclusion/response text
        response_text = getattr(collected_output, "response_text", "")
        if not response_text:
            return 0.0

        # Count how many unique node IDs appear in the conclusion text
        cited_ids = {nid for nid in node_inventory if nid in response_text}
        return min(1.0, len(cited_ids) / max(1, len(node_inventory)))

    def _get_node_inventory(self, obs_summary: Any) -> set[str]:
        """Extract all BSKG node IDs from observation data.

        Includes PreCompact snapshot merge: when precompact_snapshot exists,
        merge pre-compaction node inventory with post-compaction data.
        """
        node_ids: set[str] = set()

        if obs_summary is None:
            return node_ids

        # Extract node IDs from bskg_query_events
        bskg_events = getattr(obs_summary, "bskg_query_events", [])
        for event in bskg_events:
            event_node_ids = getattr(event, "node_ids", [])
            if isinstance(event_node_ids, list):
                node_ids.update(event_node_ids)

        # PreCompact snapshot merge (P11-IMP-08): merge pre-compaction
        # node inventory with post-compaction data
        precompact = getattr(obs_summary, "precompact_snapshot", None)
        if precompact is not None:
            # precompact_snapshot is an ObservationSummary or dict
            if hasattr(precompact, "bskg_query_events"):
                for event in precompact.bskg_query_events:
                    event_node_ids = getattr(event, "node_ids", [])
                    if isinstance(event_node_ids, list):
                        node_ids.update(event_node_ids)
            elif isinstance(precompact, dict):
                for event in precompact.get("bskg_query_events", []):
                    if isinstance(event, dict):
                        node_ids.update(event.get("node_ids", []))

        return node_ids

    # --- Graph-first compliance ---

    def _check_graph_first(
        self,
        obs_summary: Any = None,
    ) -> tuple[bool, float]:
        """Check if BSKG queries came before file reading.

        Uses observation event timestamps for precise ordering.
        When obs_summary is absent or has no bskg_query events,
        returns conservative (False, 0.0) — no guessing from tool names.

        Args:
            obs_summary: ObservationSummary with bskg_query_events and
                tool_sequences containing timestamps.

        Returns:
            Tuple of (graph_first_compliant: bool, graph_first_score: float).
            graph_first_score is the proportion of Read/Bash calls preceded
            by at least one BSKG query (graduated scoring).
        """
        if obs_summary is None:
            return False, 0.0

        bskg_events = getattr(obs_summary, "bskg_query_events", [])
        tool_sequences = getattr(obs_summary, "tool_sequences", [])
        if not tool_sequences:
            return False, 0.0

        # Find the earliest BSKG query timestamp
        bskg_timestamps = []
        bskg_indices = set()
        for event in bskg_events:
            ts = getattr(event, "timestamp", None)
            idx = getattr(event, "tool_call_index", None)
            if ts is not None:
                bskg_timestamps.append(ts)
            if idx is not None:
                bskg_indices.add(idx)

        # Handle PostToolUseFailure: count failed BSKG queries toward compliance.
        # When a failed alphaswarm query is detected, add a sentinel index to
        # bskg_indices so the ordering logic treats it as an attempted BSKG query.
        # This must run BEFORE the early-exit check so that failed queries
        # are counted even when bskg_query_events is empty.
        tool_failures = getattr(obs_summary, "tool_failures", [])
        for failure in tool_failures:
            if isinstance(failure, dict):
                content = failure.get("content", "")
                # If failure is for an alphaswarm query, count the attempt
                if "alphaswarm" in content and "query" in content:
                    # Agent tried — counts for graph-first compliance.
                    # Use index 0 as sentinel: the failed query attempt is treated
                    # as if it occurred at position 0 (earliest possible).
                    bskg_indices.add(0)
                    if not bskg_timestamps:
                        bskg_timestamps.append("attempted")

        if not bskg_timestamps and not bskg_indices:
            return False, 0.0

        # Determine ordering using indices (more reliable than timestamps)
        # Find the earliest BSKG query index
        earliest_bskg_idx = min(bskg_indices) if bskg_indices else float("inf")

        # Count Read calls that are preceded by at least one BSKG query
        read_calls = [
            entry for entry in tool_sequences
            if getattr(entry, "tool_name", "") == "Read"
        ]

        if not read_calls:
            # No Read calls — trivially compliant if BSKG queries exist
            return True, 1.0

        # Binary: first BSKG query before first Read
        first_read_idx = min(
            getattr(entry, "index", float("inf")) for entry in read_calls
        )
        graph_first_compliant = earliest_bskg_idx < first_read_idx

        # Graduated: proportion of Read calls preceded by a BSKG query
        preceded_count = sum(
            1 for entry in read_calls
            if getattr(entry, "index", 0) > earliest_bskg_idx
        )
        graph_first_score = preceded_count / len(read_calls) if read_calls else 0.0

        return graph_first_compliant, graph_first_score

    # --- Citation relevance (crash guard) ---

    def _check_citation_relevance(
        self, context: dict[str, Any] | None = None,
    ) -> DimensionScore:
        """Check that cited graph data is relevant to the finding.

        Crash guard: returns applicable=False when context or ground_truth_entry
        is missing (full coherence logic deferred to later wave).
        """
        if context is None or context.get("ground_truth_entry") is None:
            return DimensionScore(
                dimension="graph_reasoning_coherence",
                score=0,
                applicable=False,
                explanation="No ground truth entry — coherence check not applicable",
            )
        # Full coherence implementation deferred to later wave
        return DimensionScore(
            dimension="graph_reasoning_coherence",
            score=0,
            applicable=False,
            explanation="Full coherence check not yet implemented",
        )

    # --- Dimension building ---

    def _build_dimensions(
        self,
        query_coverage: float,
        citation_rate: float,
        graph_first: bool,
        graph_first_score: float,
        context: dict[str, Any] | None = None,
    ) -> list[DimensionScore]:
        """Build dimension scores including DEFAULT-30 fix."""
        dimensions = [
            DimensionScore(
                dimension="query_coverage",
                score=int(query_coverage * 100),
                explanation=f"Query coverage: {query_coverage:.0%}",
            ),
            DimensionScore(
                dimension="citation_rate",
                score=int(citation_rate * 100),
                explanation=f"Citation rate: {citation_rate:.0%}",
            ),
            DimensionScore(
                dimension="graph_first_compliance",
                score=int(graph_first_score * 100),
                explanation=(
                    f"Graph-first: {'Yes' if graph_first else 'No'} "
                    f"(graduated: {graph_first_score:.0%})"
                ),
            ),
        ]

        # DEFAULT-30 fix: unimplemented dimensions return applicable=False
        for dim_name in sorted(_UNIMPLEMENTED_DIMENSIONS):
            dimensions.append(DimensionScore(
                dimension=dim_name,
                score=0,
                applicable=False,
                explanation=f"No handler implemented for {dim_name}",
            ))

        # Graph-reasoning coherence (crash guard)
        dimensions.append(self._check_citation_relevance(context))

        return dimensions

    def _all_inapplicable_dimensions(self) -> list[DimensionScore]:
        """Return all dimensions as inapplicable (for run_gvs: false)."""
        all_dims = [
            "query_coverage", "citation_rate", "graph_first_compliance",
            "graph_reasoning_coherence",
        ] + sorted(_UNIMPLEMENTED_DIMENSIONS)
        return [
            DimensionScore(
                dimension=name,
                score=0,
                applicable=False,
                explanation="Skipped: run_gvs is false",
            )
            for name in all_dims
        ]

    # --- Query helpers ---

    def _calc_query_coverage(self, bskg_queries: list) -> float:
        """Calculate fraction of expected query types that were issued."""
        if not self._expected_query_types:
            return 1.0

        found_types = set(self._get_query_types(bskg_queries))
        expected = set(self._expected_query_types)
        if not expected:
            return 1.0

        covered = len(found_types & expected)
        return covered / len(expected)

    def _get_query_types(self, bskg_queries: list) -> list[str]:
        """Extract query type categories from BSKG queries."""
        types = []
        for q in bskg_queries:
            if hasattr(q, "category"):
                types.append(q.category)
            elif isinstance(q, dict):
                cat = q.get("category", "")
                if cat:
                    types.append(cat)
                else:
                    # Infer from command
                    cmd = q.get("command", "")
                    if "build-kg" in cmd:
                        types.append("build-kg")
                    elif "query" in cmd:
                        types.append("query")
                    elif "analyze" in cmd:
                        types.append("analyze")
        return types

    # --- PostToolUseFailure handling ---

    def _get_result_utilization_penalty(
        self, obs_summary: Any,
    ) -> float:
        """Calculate result utilization penalty from PostToolUseFailure events.

        When PostToolUseFailure occurs for alphaswarm query: agent tried
        (counted for graph-first) but got no result (reduce utilization).

        Returns penalty as a float between 0.0 and 1.0 to subtract from
        utilization score.
        """
        if obs_summary is None:
            return 0.0

        tool_failures = getattr(obs_summary, "tool_failures", [])
        bskg_failures = 0
        for failure in tool_failures:
            if isinstance(failure, dict):
                content = failure.get("content", "")
                if "alphaswarm" in content and "query" in content:
                    bskg_failures += 1

        bskg_events = getattr(obs_summary, "bskg_query_events", [])
        total_queries = len(bskg_events) + bskg_failures
        if total_queries == 0:
            return 0.0

        return bskg_failures / total_queries
