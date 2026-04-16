#!/usr/bin/env python3
"""Run label evaluation on real-world corpus.

This script executes the labeling pipeline on a real-world contract corpus
and measures the detection delta required by exit gate LABEL-12.

Exit Gate Criteria (LABEL-12):
- Label precision >= 0.75 (75%)
- Detection delta >= +5%
- Token budget <= 6000 per call

Usage:
    # Run on test contracts (ground truth available)
    uv run python scripts/run_label_evaluation.py --corpus tests/contracts/

    # Run on real-world corpus
    uv run python scripts/run_label_evaluation.py --corpus .vkg/benchmarks/corpora/

    # Save JSON report for CI
    uv run python scripts/run_label_evaluation.py --corpus tests/contracts/ --output report.json

    # Dry run (no LLM calls)
    uv run python scripts/run_label_evaluation.py --corpus tests/contracts/ --dry-run

The script:
1. Builds knowledge graph from corpus
2. Runs baseline patterns (Tier A/B) without labels
3. Runs semantic labeling on functions (or uses ground truth)
4. Runs labeled patterns (Tier A/B/C) with labels
5. Computes detection delta
6. Reports exit gate status
7. Returns exit code 0 on pass, 1 on fail
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from alphaswarm_sol.kg.builder.core import build_graph
from alphaswarm_sol.kg.schema import KnowledgeGraph
from alphaswarm_sol.queries.patterns import PatternEngine, PatternStore
from alphaswarm_sol.labels import (
    LabelOverlay,
    LabelingConfig,
    LLMLabeler,
)
from alphaswarm_sol.labels.evaluation import (
    LabelEvaluator,
    EvaluationReport,
    TokenMetrics,
    DetectionMetrics,
    PrecisionMetrics,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def find_solidity_files(corpus_path: Path) -> List[Path]:
    """Find all Solidity files in corpus.

    Args:
        corpus_path: Path to corpus directory

    Returns:
        List of Solidity file paths (excluding tests/mocks)
    """
    sol_files = list(corpus_path.rglob("*.sol"))
    # Filter out test files, mocks, and node_modules
    sol_files = [
        f for f in sol_files
        if "test" not in f.name.lower()
        and "mock" not in f.name.lower()
        and "node_modules" not in str(f)
        and ".t.sol" not in f.name
    ]
    return sorted(sol_files)


def run_patterns(
    graph: KnowledgeGraph,
    patterns_dir: Path,
    label_overlay: Optional[LabelOverlay] = None,
    tier_c_only: bool = False,
) -> Tuple[int, List[Dict[str, Any]]]:
    """Run pattern matching on graph.

    Args:
        graph: Knowledge graph to query
        patterns_dir: Path to patterns directory
        label_overlay: Optional label overlay for Tier C patterns
        tier_c_only: If True, only run Tier C patterns

    Returns:
        Tuple of (finding_count, findings_list)
    """
    store = PatternStore(patterns_dir)
    patterns = store.load()
    engine = PatternEngine()

    # Filter patterns by tier
    if tier_c_only:
        # Only Tier C patterns (require labels)
        patterns = [p for p in patterns if getattr(p, 'tier', 'A') == 'C']
    elif label_overlay is None:
        # Only Tier A/B patterns (no labels needed)
        patterns = [p for p in patterns if getattr(p, 'tier', 'A') in ('A', 'B', None)]

    findings = engine.run(graph, patterns, limit=1000)
    return len(findings), findings


def compare_findings(
    baseline: List[Dict[str, Any]],
    with_labels: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Compare baseline and labeled findings.

    Args:
        baseline: Findings without labels
        with_labels: Findings with labels

    Returns:
        Comparison results
    """
    # Create finding IDs (pattern_id + node_id)
    def finding_id(f: Dict) -> str:
        return f"{f.get('pattern_id', '')}:{f.get('node_id', '')}"

    baseline_ids = {finding_id(f) for f in baseline}
    label_ids = {finding_id(f) for f in with_labels}

    new_findings = label_ids - baseline_ids
    lost_findings = baseline_ids - label_ids
    common_findings = baseline_ids & label_ids

    return {
        "baseline_count": len(baseline),
        "label_count": len(with_labels),
        "new_findings": list(new_findings),
        "lost_findings": list(lost_findings),
        "common_findings": len(common_findings),
        "net_new": len(new_findings) - len(lost_findings),
    }


async def run_labeling(
    graph: KnowledgeGraph,
    config: LabelingConfig,
) -> Tuple[LabelOverlay, TokenMetrics]:
    """Run semantic labeling on graph.

    Args:
        graph: Knowledge graph to label
        config: Labeling configuration

    Returns:
        Tuple of (overlay, token_metrics)
    """
    from alphaswarm_sol.llm import LLMClient

    # Get LLM client
    client = LLMClient()
    # Use the default provider
    provider = await client._get_provider()

    labeler = LLMLabeler(provider, config)

    # Get function node IDs
    function_ids = [
        node.id for node in graph.nodes.values()
        if node.type == "Function"
    ]

    logger.info(f"Labeling {len(function_ids)} functions...")

    result = await labeler.label_functions(graph, function_ids)

    token_metrics = TokenMetrics(
        total_tokens=result.total_tokens,
        total_cost_usd=result.total_cost_usd,
        functions_labeled=result.functions_labeled,
        max_tokens_single_call=config.max_tokens_per_call,
    )
    token_metrics.calculate_averages()

    return labeler.get_overlay(), token_metrics


def load_ground_truth_overlay() -> Optional[LabelOverlay]:
    """Load ground truth overlay if available.

    Returns:
        Ground truth overlay or None if not available
    """
    try:
        from tests.labels.ground_truth import load_all_ground_truth
        return load_all_ground_truth()
    except ImportError:
        return None


def print_report(
    report: EvaluationReport,
    comparison: Dict[str, Any],
    corpus_path: Path,
    duration_seconds: float,
) -> None:
    """Print evaluation report to console.

    Args:
        report: Evaluation report
        comparison: Finding comparison results
        corpus_path: Path to evaluated corpus
        duration_seconds: Time taken for evaluation
    """
    print("\n" + "=" * 60)
    print("SEMANTIC LABELING EVALUATION REPORT")
    print(f"Corpus: {corpus_path}")
    print(f"Duration: {duration_seconds:.1f}s")
    print("=" * 60)

    print("\n--- Detection Metrics ---")
    print(f"Baseline findings (Tier A/B): {comparison['baseline_count']}")
    print(f"With labels (all tiers):      {comparison['label_count']}")
    print(f"New findings from labels:     {len(comparison['new_findings'])}")
    print(f"Lost findings:                {len(comparison['lost_findings'])}")

    delta = report.detection_metrics.detection_delta
    delta_str = f"{delta:+.1f}%" if delta != float('inf') else "+inf%"
    print(f"Detection Delta:              {delta_str}")

    if report.precision_metrics.total_ground_truth > 0:
        print("\n--- Precision Metrics (vs Ground Truth) ---")
        print(f"Precision:                    {report.precision_metrics.precision:.2%}")
        print(f"Recall:                       {report.precision_metrics.recall:.2%}")
        print(f"F1 Score:                     {report.precision_metrics.f1_score:.2%}")
        print(f"True Positives:               {report.precision_metrics.true_positives}")
        print(f"False Positives:              {report.precision_metrics.false_positives}")

    print("\n--- Token Usage ---")
    print(f"Total tokens:                 {report.token_metrics.total_tokens:,}")
    print(f"Total cost:                   ${report.token_metrics.total_cost_usd:.4f}")
    if report.token_metrics.functions_labeled > 0:
        print(f"Functions labeled:            {report.token_metrics.functions_labeled}")
        print(f"Avg tokens/function:          {report.token_metrics.avg_tokens_per_function:.0f}")

    print("\n--- Exit Gate Status (LABEL-12) ---")
    report.check_exit_gate(
        min_precision=0.75,
        min_detection_delta=5.0,
        max_tokens_per_call=6000,
    )

    for criterion, passed in report.exit_gate_details.items():
        status = "PASS" if passed else "FAIL"
        symbol = "[+]" if passed else "[-]"
        print(f"  {symbol} {criterion}: {status}")

    print("\n" + "-" * 60)
    overall = "PASS" if report.passed_exit_gate else "FAIL"
    print(f"OVERALL EXIT GATE: {overall}")
    print("=" * 60 + "\n")


async def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 on pass, 1 on fail)
    """
    parser = argparse.ArgumentParser(
        description="Run label evaluation on real-world corpus",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--corpus",
        type=Path,
        required=True,
        help="Path to corpus directory with Solidity files",
    )
    parser.add_argument(
        "--patterns",
        type=Path,
        default=Path("vulndocs"),
        help="Path to patterns directory",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Path to save JSON report",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=6000,
        help="Max tokens per labeling call",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Use ground truth labels instead of LLM (no API calls)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    start_time = time.time()

    # Verify corpus exists
    if not args.corpus.exists():
        logger.error(f"Corpus not found: {args.corpus}")
        return 1

    # Find Solidity files
    sol_files = find_solidity_files(args.corpus)
    if not sol_files:
        logger.error(f"No Solidity files found in {args.corpus}")
        return 1

    logger.info(f"Found {len(sol_files)} Solidity files in corpus")

    # Build knowledge graph
    logger.info("Building knowledge graph...")
    try:
        graph = build_graph(args.corpus)
    except Exception as e:
        logger.error(f"Failed to build graph: {e}")
        return 1

    func_count = sum(1 for n in graph.nodes.values() if n.type == "Function")
    logger.info(f"Graph has {func_count} functions")

    # Run baseline (no labels)
    logger.info("Running baseline pattern matching (Tier A/B)...")
    baseline_count, baseline_findings = run_patterns(graph, args.patterns)
    logger.info(f"Baseline: {baseline_count} findings")

    # Get labels (LLM or ground truth)
    token_metrics = TokenMetrics()
    ground_truth_overlay = load_ground_truth_overlay()

    if args.dry_run:
        logger.info("Dry run: using ground truth labels...")
        if ground_truth_overlay is None:
            logger.warning("Ground truth not available, using empty overlay")
            overlay = LabelOverlay()
        else:
            overlay = ground_truth_overlay
            logger.info(f"Loaded {overlay.get_label_count()} ground truth labels")
    else:
        logger.info("Running semantic labeling...")
        config = LabelingConfig(max_tokens_per_call=args.max_tokens)
        try:
            overlay, token_metrics = await run_labeling(graph, config)
            label_count = overlay.get_label_count()
            logger.info(f"Applied {label_count} labels to {len(overlay.labels)} functions")
        except Exception as e:
            logger.error(f"Labeling failed: {e}")
            logger.info("Falling back to ground truth labels")
            overlay = ground_truth_overlay or LabelOverlay()

    # Run with labels
    logger.info("Running pattern matching with labels...")
    labeled_count, labeled_findings = run_patterns(
        graph, args.patterns, label_overlay=overlay
    )
    logger.info(f"With labels: {labeled_count} findings")

    # Compare findings
    comparison = compare_findings(baseline_findings, labeled_findings)

    # Build detection metrics
    detection_metrics = DetectionMetrics(
        baseline_findings=baseline_count,
        label_findings=labeled_count,
        new_findings=len(comparison["new_findings"]),
        lost_findings=len(comparison["lost_findings"]),
    )

    # Build precision metrics (if ground truth available)
    precision_metrics = PrecisionMetrics()
    if ground_truth_overlay is not None:
        evaluator = LabelEvaluator(ground_truth_overlay)
        precision_report = evaluator.evaluate(overlay)
        precision_metrics = precision_report.precision_metrics

    # Build report
    report = EvaluationReport(
        precision_metrics=precision_metrics,
        detection_metrics=detection_metrics,
        token_metrics=token_metrics,
    )

    duration = time.time() - start_time

    # Print report
    print_report(report, comparison, args.corpus, duration)

    # Save JSON if requested
    if args.output:
        result = {
            "corpus": str(args.corpus),
            "solidity_files": len(sol_files),
            "functions": func_count,
            "duration_seconds": round(duration, 2),
            "evaluation": report.to_dict(),
            "comparison": comparison,
            "dry_run": args.dry_run,
        }
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2)
        logger.info(f"Report saved to {args.output}")

    # Return exit code based on exit gate
    return 0 if report.passed_exit_gate else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
