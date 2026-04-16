"""
Context Optimizer

Main entry point for VKG 3.5 context optimization.
Integrates triage, compression, slicing, and prompt templating.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, List

from .triage import TriageClassifier, TriageResult
from .compressor import SemanticCompressor, CompressedContext
from .slicer import ContextSlicer, ContextSlice
from .templates import (
    get_template,
    get_system_prompt,
    format_pattern_list,
    format_spec_list,
)


@dataclass
class OptimizedContext:
    """Complete optimized context for LLM analysis."""
    triage: TriageResult
    compressed: Optional[CompressedContext]
    slice: Optional[ContextSlice]
    prompt: Optional[str]
    system_prompt: Optional[str]
    total_tokens: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/debugging."""
        return {
            "triage": self.triage.to_dict(),
            "compressed": self.compressed.to_dict() if self.compressed else None,
            "slice": self.slice.to_dict() if self.slice else None,
            "prompt_length": len(self.prompt) if self.prompt else 0,
            "system_prompt_length": len(self.system_prompt) if self.system_prompt else 0,
            "total_tokens": self.total_tokens,
        }


class ContextOptimizer:
    """Main entry point for context optimization."""

    def __init__(self, kg: Optional[object] = None):
        """
        Initialize optimizer.

        Args:
            kg: Optional knowledge graph for context slicing
        """
        self.kg = kg
        self.triage = TriageClassifier()
        self.compressor = SemanticCompressor()
        self.slicer = ContextSlicer()

    def optimize(self, fn_node: Dict[str, Any]) -> OptimizedContext:
        """
        Optimize context for a function.

        Args:
            fn_node: Function node with properties

        Returns:
            OptimizedContext with prompt and token estimate
        """
        # Step 1: Triage
        triage_result = self.triage.classify(fn_node)

        if not triage_result.requires_llm:
            return OptimizedContext(
                triage=triage_result,
                compressed=None,
                slice=None,
                prompt=None,
                system_prompt=None,
                total_tokens=0
            )

        # Step 2: Compress
        compressed = self.compressor.compress(
            fn_node,
            budget=triage_result.token_budget,
            kg=self.kg
        )

        # Step 3: Slice
        fn_id = fn_node.get("id", fn_node.get("name", "unknown"))
        slice_result = self.slicer.slice(
            self.kg,
            fn_id,
            triage_result.level
        )

        # Step 4: Build prompt
        template = get_template(triage_result.level.value)
        system_prompt = get_system_prompt(triage_result.level.value)

        # Format template variables
        patterns = fn_node.get("matched_patterns", [])
        specs = fn_node.get("cross_graph_links", [])

        prompt = template.format(
            compressed_context=compressed.compressed,
            patterns=format_pattern_list(patterns),
            specs=format_spec_list(specs),
            source_code=fn_node.get("source_code", ""),
            related_functions=self._format_related_functions(slice_result),
            known_vulns=self._format_known_vulns(fn_node),
            attack_patterns=self._format_attack_patterns(fn_node)
        )

        # Calculate total tokens
        total_tokens = (
            compressed.token_estimate +
            slice_result.token_estimate +
            len(system_prompt) // 4  # Rough token estimate for system prompt
        )

        return OptimizedContext(
            triage=triage_result,
            compressed=compressed,
            slice=slice_result,
            prompt=prompt,
            system_prompt=system_prompt,
            total_tokens=total_tokens
        )

    def batch_optimize(self, fn_nodes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Optimize a batch of functions and return statistics.

        Args:
            fn_nodes: List of function nodes

        Returns:
            Dict with results and statistics
        """
        results = []
        stats = {
            "level_0": 0,
            "level_1": 0,
            "level_2": 0,
            "level_3": 0,
            "total_tokens": 0,
            "saved_tokens": 0,
        }

        naive_tokens_per_fn = 6000  # Estimated naive approach

        for fn in fn_nodes:
            opt = self.optimize(fn)
            results.append(opt)

            level_key = f"level_{opt.triage.level.value}"
            stats[level_key] += 1
            stats["total_tokens"] += opt.total_tokens
            stats["saved_tokens"] += naive_tokens_per_fn - opt.total_tokens

        stats["functions_analyzed"] = len(fn_nodes)
        if len(fn_nodes) > 0:
            total_naive = naive_tokens_per_fn * len(fn_nodes)
            stats["token_reduction_pct"] = (
                stats["saved_tokens"] / total_naive * 100
            )
            stats["avg_tokens_per_function"] = (
                stats["total_tokens"] / len(fn_nodes)
            )
        else:
            stats["token_reduction_pct"] = 0.0
            stats["avg_tokens_per_function"] = 0.0

        return {"results": results, "stats": stats}

    def _format_related_functions(self, slice_obj: Optional[ContextSlice]) -> str:
        """Format related functions from context slice."""
        if not slice_obj or not slice_obj.included_edges:
            return "none"

        # Extract function calls from edges
        related = set()
        for src, tgt, data in slice_obj.included_edges[:5]:  # Limit to 5
            if isinstance(data, dict):
                edge_type = data.get("type", "")
                if "call" in edge_type.lower():
                    related.add(tgt)

        if not related:
            return "none"

        return ", ".join(list(related)[:5])

    def _format_known_vulns(self, fn_node: Dict[str, Any]) -> List[str]:
        """Format known vulnerabilities from cross-graph links."""
        vulns = []
        cross_links = fn_node.get("cross_graph_links", [])

        for link in cross_links[:3]:  # Limit to 3
            if isinstance(link, dict):
                vuln_type = link.get("type", "")
                if "vuln" in vuln_type.lower() or "exploit" in vuln_type.lower():
                    vuln_id = link.get("id", "unknown")
                    severity = link.get("severity", "?")
                    vulns.append(f"{vuln_id} ({severity})")

        return vulns

    def _format_attack_patterns(self, fn_node: Dict[str, Any]) -> List[str]:
        """Format attack patterns from cross-graph links."""
        patterns = []
        cross_links = fn_node.get("cross_graph_links", [])

        for link in cross_links[:3]:  # Limit to 3
            if isinstance(link, dict):
                link_type = link.get("type", "")
                if "attack" in link_type.lower() or "pattern" in link_type.lower():
                    pattern_id = link.get("id", "unknown")
                    description = link.get("description", "")
                    patterns.append(f"{pattern_id}: {description[:50]}")

        return patterns

    def get_optimization_stats(self, fn_nodes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get optimization statistics without running full optimization.

        Args:
            fn_nodes: List of function nodes

        Returns:
            Dict with triage distribution and token projections
        """
        triage_results = [self.triage.classify(fn) for fn in fn_nodes]

        stats = {
            "total_functions": len(fn_nodes),
            "level_0_count": sum(1 for r in triage_results if r.level.value == 0),
            "level_1_count": sum(1 for r in triage_results if r.level.value == 1),
            "level_2_count": sum(1 for r in triage_results if r.level.value == 2),
            "level_3_count": sum(1 for r in triage_results if r.level.value == 3),
            "total_tokens_budget": sum(r.token_budget for r in triage_results),
        }

        if len(fn_nodes) > 0:
            stats["avg_tokens_per_function"] = stats["total_tokens_budget"] / len(fn_nodes)
            stats["level_0_pct"] = stats["level_0_count"] / len(fn_nodes) * 100
            stats["level_1_pct"] = stats["level_1_count"] / len(fn_nodes) * 100
            stats["level_2_pct"] = stats["level_2_count"] / len(fn_nodes) * 100
            stats["level_3_pct"] = stats["level_3_count"] / len(fn_nodes) * 100

            naive_total = 6000 * len(fn_nodes)
            stats["token_reduction_pct"] = (
                (naive_total - stats["total_tokens_budget"]) / naive_total * 100
            )
        else:
            stats["avg_tokens_per_function"] = 0.0
            stats["token_reduction_pct"] = 0.0

        return stats
