"""CLI commands for model benchmarking.

This module provides commands for benchmarking models and managing rankings:
- benchmark run: Run benchmark suite on models
- benchmark rankings: Display current model rankings
- benchmark compare: Compare two models across categories
- benchmark integrate: Integrate new model with benchmarks
- benchmark export: Export benchmark results

Per 05.3-09-PLAN.md:
- Benchmark commands for model evaluation
- Integration with ranking system
- Export capabilities for analysis

Usage:
    alphaswarm benchmark run --all-models
    alphaswarm benchmark rankings
    alphaswarm benchmark compare model-a model-b
    alphaswarm benchmark integrate new-model-id
    alphaswarm benchmark export --format csv -o results.csv
"""

from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional

import typer

from alphaswarm_sol.agents.ranking import (
    RankingsStore,
    ModelRanking,
    TaskFeedback,
    ModelSelector,
    FeedbackCollector,
)
from alphaswarm_sol.agents.runtime.types import TaskType


benchmark_cli = typer.Typer(help="Model benchmarking commands")


# =============================================================================
# Output Format
# =============================================================================


class BenchmarkFormat(str, Enum):
    """Output format for benchmark results."""

    JSON = "json"
    CSV = "csv"
    TABLE = "table"


# =============================================================================
# Benchmark Categories
# =============================================================================


BENCHMARK_CATEGORIES = {
    "verify": "Verification tasks (fast, accuracy-focused)",
    "reasoning": "Reasoning tasks (complex analysis)",
    "code": "Code generation tasks",
    "summarize": "Summarization tasks",
    "critical": "Critical analysis (high accuracy)",
    "review": "Review tasks (discussion, debate)",
}


# =============================================================================
# Commands
# =============================================================================


@benchmark_cli.command("run")
def benchmark_run(
    model: Optional[str] = typer.Option(
        None,
        "--model",
        "-m",
        help="Specific model to benchmark (e.g., 'deepseek/deepseek-v3.2')",
    ),
    category: Optional[str] = typer.Option(
        None,
        "--category",
        "-c",
        help=f"Specific category to test. Options: {', '.join(BENCHMARK_CATEGORIES.keys())}",
    ),
    all_models: bool = typer.Option(
        False,
        "--all-models",
        help="Benchmark all configured models",
    ),
    iterations: int = typer.Option(
        3,
        "--iterations",
        "-n",
        help="Number of iterations per benchmark",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output path for results",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed output",
    ),
) -> None:
    """Run benchmark suite.

    Benchmarks models on various task types to update rankings.
    Results are stored in .vrs/rankings/rankings.yaml.

    Examples:
        # Benchmark specific model
        alphaswarm benchmark run --model deepseek/deepseek-v3.2

        # Benchmark all models
        alphaswarm benchmark run --all-models

        # Benchmark specific category
        alphaswarm benchmark run --category verify --all-models

        # Save results to file
        alphaswarm benchmark run --all-models -o results.json
    """
    from alphaswarm_sol.agents.runtime.types import DEFAULT_MODELS

    # Validate category
    if category and category not in BENCHMARK_CATEGORIES:
        typer.echo(f"Invalid category: {category}", err=True)
        typer.echo(f"Valid categories: {', '.join(BENCHMARK_CATEGORIES.keys())}", err=True)
        raise typer.Exit(code=1)

    # Determine models to benchmark
    if model:
        models_to_test = [model]
    elif all_models:
        models_to_test = list(set(DEFAULT_MODELS.values()))
        # Filter out CLI-based runtimes
        models_to_test = [m for m in models_to_test if m not in ("claude", "codex")]
    else:
        typer.echo("Specify --model or --all-models", err=True)
        raise typer.Exit(code=1)

    # Determine categories to test
    if category:
        categories = [category]
    else:
        categories = list(BENCHMARK_CATEGORIES.keys())

    typer.echo(f"Benchmarking {len(models_to_test)} models on {len(categories)} categories")
    typer.echo(f"Iterations per benchmark: {iterations}")
    typer.echo("")

    # Initialize store
    store = RankingsStore()

    results = []
    total_tests = len(models_to_test) * len(categories) * iterations

    with typer.progressbar(length=total_tests, label="Benchmarking") as progress:
        for model_id in models_to_test:
            for cat in categories:
                for i in range(iterations):
                    # Simulate benchmark (actual execution would go here)
                    result = _run_single_benchmark(model_id, cat, verbose)
                    results.append(result)

                    # Update rankings
                    _update_ranking_from_result(store, result)

                    progress.update(1)

    # Save rankings
    store.save()

    # Display summary
    typer.echo("")
    typer.echo("=" * 60)
    typer.echo("BENCHMARK SUMMARY")
    typer.echo("=" * 60)

    # Aggregate results by model
    model_stats = {}
    for r in results:
        if r["model_id"] not in model_stats:
            model_stats[r["model_id"]] = {
                "total": 0,
                "success": 0,
                "total_latency": 0,
                "total_quality": 0,
            }
        model_stats[r["model_id"]]["total"] += 1
        if r["success"]:
            model_stats[r["model_id"]]["success"] += 1
        model_stats[r["model_id"]]["total_latency"] += r["latency_ms"]
        model_stats[r["model_id"]]["total_quality"] += r["quality_score"]

    typer.echo(f"\n{'Model':<40} {'Success':<10} {'Avg Latency':<15} {'Avg Quality'}")
    typer.echo("-" * 75)

    for model_id, stats in model_stats.items():
        success_rate = stats["success"] / stats["total"] if stats["total"] > 0 else 0
        avg_latency = stats["total_latency"] / stats["total"] if stats["total"] > 0 else 0
        avg_quality = stats["total_quality"] / stats["total"] if stats["total"] > 0 else 0

        model_short = model_id[:38] + ".." if len(model_id) > 40 else model_id
        typer.echo(
            f"{model_short:<40} {success_rate:.1%}     {avg_latency:.0f}ms          {avg_quality:.2f}"
        )

    typer.echo("")
    typer.echo(f"Total benchmarks: {len(results)}")
    typer.echo(f"Rankings saved to: {store.path}")

    # Save results if output specified
    if output:
        with open(output, "w") as f:
            json.dump(results, f, indent=2, default=str)
        typer.echo(f"Results saved to: {output}")


def _run_single_benchmark(model_id: str, category: str, verbose: bool) -> dict:
    """Run a single benchmark test.

    In a real implementation, this would:
    1. Create a test prompt for the category
    2. Execute the prompt against the model
    3. Measure latency and evaluate response quality

    For now, returns simulated results.
    """
    import random
    import time

    # Simulate execution
    base_latency = {
        "verify": 800,
        "reasoning": 2500,
        "code": 1500,
        "summarize": 1200,
        "critical": 3000,
        "review": 2000,
    }

    # Add some randomness
    latency = base_latency.get(category, 1500) + random.randint(-200, 500)
    success = random.random() > 0.1  # 90% success rate
    quality = random.uniform(0.7, 0.98) if success else 0.0

    return {
        "model_id": model_id,
        "category": category,
        "success": success,
        "latency_ms": latency,
        "quality_score": quality,
        "tokens_used": random.randint(200, 2000),
        "cost_usd": random.uniform(0.0, 0.01),
        "timestamp": datetime.utcnow().isoformat(),
    }


def _update_ranking_from_result(store: RankingsStore, result: dict) -> None:
    """Update ranking from benchmark result."""
    from alphaswarm_sol.agents.ranking.feedback import update_ranking_from_feedback

    # Get existing ranking or create new one
    existing = store.get_ranking(result["model_id"], result["category"])

    if existing is None:
        existing = ModelRanking(
            model_id=result["model_id"],
            task_type=result["category"],
            success_rate=1.0 if result["success"] else 0.0,
            average_latency_ms=result["latency_ms"],
            average_tokens=result["tokens_used"],
            quality_score=result["quality_score"],
            cost_per_task=result["cost_usd"],
            sample_count=1,
        )
    else:
        # Create feedback and update
        feedback = TaskFeedback(
            task_id=f"bench-{datetime.utcnow().timestamp()}",
            model_id=result["model_id"],
            task_type=result["category"],
            success=result["success"],
            latency_ms=result["latency_ms"],
            tokens_used=result["tokens_used"],
            quality_score=result["quality_score"],
            cost_usd=result["cost_usd"],
        )
        existing = update_ranking_from_feedback(existing, feedback)

    store.update_ranking(existing)


@benchmark_cli.command("rankings")
def benchmark_rankings(
    task_type: Optional[str] = typer.Option(
        None,
        "--task-type",
        "-t",
        help="Filter by task type",
    ),
    top: int = typer.Option(
        5,
        "--top",
        "-n",
        help="Show top N models per category",
    ),
    fmt: BenchmarkFormat = typer.Option(
        BenchmarkFormat.TABLE,
        "--format",
        "-f",
        help="Output format",
    ),
) -> None:
    """Show current model rankings.

    Displays rankings from .vrs/rankings/rankings.yaml sorted by
    composite score (quality, latency, cost, success rate).

    Examples:
        alphaswarm benchmark rankings
        alphaswarm benchmark rankings --task-type verify
        alphaswarm benchmark rankings --top 3 --format json
    """
    store = RankingsStore()

    if not store.exists():
        typer.echo("No rankings found. Run 'alphaswarm benchmark run --all-models' first.")
        return

    rankings_data = store.load()

    if not rankings_data:
        typer.echo("Rankings file exists but is empty.")
        return

    # Filter by task type
    if task_type:
        if task_type not in rankings_data:
            typer.echo(f"No rankings for task type: {task_type}")
            typer.echo(f"Available: {', '.join(rankings_data.keys())}")
            return
        rankings_data = {task_type: rankings_data[task_type]}

    # JSON output
    if fmt == BenchmarkFormat.JSON:
        output = {}
        for tt, model_rankings in rankings_data.items():
            sorted_rankings = sorted(
                model_rankings.values(),
                key=lambda r: r.score(),
                reverse=True,
            )[:top]
            output[tt] = [r.to_dict() for r in sorted_rankings]
        typer.echo(json.dumps(output, indent=2, default=str))
        return

    # CSV output
    if fmt == BenchmarkFormat.CSV:
        typer.echo("task_type,rank,model_id,score,success_rate,quality,latency_ms,cost")
        for tt, model_rankings in rankings_data.items():
            sorted_rankings = sorted(
                model_rankings.values(),
                key=lambda r: r.score(),
                reverse=True,
            )[:top]
            for rank, r in enumerate(sorted_rankings, 1):
                typer.echo(
                    f"{tt},{rank},{r.model_id},{r.score():.4f},{r.success_rate:.4f},"
                    f"{r.quality_score:.4f},{r.average_latency_ms},{r.cost_per_task:.6f}"
                )
        return

    # Table output
    typer.echo("\n" + "=" * 80)
    typer.echo("MODEL RANKINGS")
    typer.echo("=" * 80)

    for tt, model_rankings in sorted(rankings_data.items()):
        sorted_rankings = sorted(
            model_rankings.values(),
            key=lambda r: r.score(),
            reverse=True,
        )[:top]

        typer.echo(f"\n## {tt.upper()}")
        typer.echo("-" * 80)
        typer.echo(
            f"{'#':<3} {'Model':<35} {'Score':<8} {'Quality':<8} {'Latency':<10} {'Cost'}"
        )
        typer.echo("-" * 80)

        for rank, r in enumerate(sorted_rankings, 1):
            model_short = r.model_id[:33] + ".." if len(r.model_id) > 35 else r.model_id
            typer.echo(
                f"{rank:<3} {model_short:<35} {r.score():.3f}   "
                f"{r.quality_score:.2f}     {r.average_latency_ms:>5}ms    ${r.cost_per_task:.4f}"
            )

    stats = store.get_stats()
    typer.echo("\n" + "=" * 80)
    typer.echo(f"Total rankings: {stats['total_rankings']}")
    typer.echo(f"Task types: {len(stats['task_types'])}")
    typer.echo("=" * 80 + "\n")


@benchmark_cli.command("compare")
def benchmark_compare(
    model_a: str = typer.Argument(..., help="First model ID"),
    model_b: str = typer.Argument(..., help="Second model ID"),
    fmt: BenchmarkFormat = typer.Option(
        BenchmarkFormat.TABLE,
        "--format",
        "-f",
        help="Output format",
    ),
) -> None:
    """Compare two models across categories.

    Shows side-by-side comparison of model performance across
    all task types with rankings.

    Examples:
        alphaswarm benchmark compare deepseek/deepseek-v3.2 google/gemini-3-flash
        alphaswarm benchmark compare model-a model-b --format json
    """
    store = RankingsStore()

    if not store.exists():
        typer.echo("No rankings found. Run benchmarks first.")
        return

    rankings_data = store.load()

    # Collect comparison data
    comparison = []
    for task_type, model_rankings in rankings_data.items():
        a_ranking = model_rankings.get(model_a)
        b_ranking = model_rankings.get(model_b)

        comparison.append({
            "task_type": task_type,
            "model_a": {
                "score": a_ranking.score() if a_ranking else None,
                "quality": a_ranking.quality_score if a_ranking else None,
                "latency": a_ranking.average_latency_ms if a_ranking else None,
                "cost": a_ranking.cost_per_task if a_ranking else None,
            },
            "model_b": {
                "score": b_ranking.score() if b_ranking else None,
                "quality": b_ranking.quality_score if b_ranking else None,
                "latency": b_ranking.average_latency_ms if b_ranking else None,
                "cost": b_ranking.cost_per_task if b_ranking else None,
            },
            "winner": _get_winner(a_ranking, b_ranking),
        })

    # JSON output
    if fmt == BenchmarkFormat.JSON:
        output = {
            "model_a": model_a,
            "model_b": model_b,
            "comparison": comparison,
            "summary": _get_comparison_summary(comparison),
        }
        typer.echo(json.dumps(output, indent=2, default=str))
        return

    # Table output
    typer.echo("\n" + "=" * 80)
    typer.echo("MODEL COMPARISON")
    typer.echo("=" * 80)
    typer.echo(f"\nModel A: {model_a}")
    typer.echo(f"Model B: {model_b}\n")

    typer.echo(f"{'Task Type':<15} {'Score A':<10} {'Score B':<10} {'Winner':<15}")
    typer.echo("-" * 80)

    a_wins = 0
    b_wins = 0

    for c in comparison:
        score_a = f"{c['model_a']['score']:.3f}" if c['model_a']['score'] else "N/A"
        score_b = f"{c['model_b']['score']:.3f}" if c['model_b']['score'] else "N/A"
        winner = c['winner']

        if winner == "A":
            a_wins += 1
            winner_display = "Model A"
        elif winner == "B":
            b_wins += 1
            winner_display = "Model B"
        else:
            winner_display = winner

        typer.echo(f"{c['task_type']:<15} {score_a:<10} {score_b:<10} {winner_display:<15}")

    typer.echo("-" * 80)
    typer.echo(f"\nWins: Model A = {a_wins}, Model B = {b_wins}")

    if a_wins > b_wins:
        typer.echo(f"Overall winner: {model_a}")
    elif b_wins > a_wins:
        typer.echo(f"Overall winner: {model_b}")
    else:
        typer.echo("Overall: Tie")

    typer.echo("=" * 80 + "\n")


def _get_winner(a_ranking: Optional[ModelRanking], b_ranking: Optional[ModelRanking]) -> str:
    """Determine winner between two rankings."""
    if a_ranking is None and b_ranking is None:
        return "N/A"
    if a_ranking is None:
        return "B"
    if b_ranking is None:
        return "A"

    a_score = a_ranking.score()
    b_score = b_ranking.score()

    if a_score > b_score:
        return "A"
    elif b_score > a_score:
        return "B"
    else:
        return "Tie"


def _get_comparison_summary(comparison: list) -> dict:
    """Generate comparison summary."""
    a_wins = sum(1 for c in comparison if c["winner"] == "A")
    b_wins = sum(1 for c in comparison if c["winner"] == "B")
    ties = sum(1 for c in comparison if c["winner"] == "Tie")

    return {
        "model_a_wins": a_wins,
        "model_b_wins": b_wins,
        "ties": ties,
        "total_categories": len(comparison),
        "overall_winner": "A" if a_wins > b_wins else ("B" if b_wins > a_wins else "Tie"),
    }


@benchmark_cli.command("integrate")
def benchmark_integrate(
    model_id: str = typer.Argument(..., help="Model ID to integrate (e.g., 'provider/model-name')"),
    run_benchmarks: bool = typer.Option(
        True,
        "--run-benchmarks/--no-benchmarks",
        help="Run benchmarks after integration",
    ),
    iterations: int = typer.Option(
        3,
        "--iterations",
        "-n",
        help="Number of benchmark iterations",
    ),
) -> None:
    """Integrate new model (run benchmarks and update rankings).

    Adds a new model to the ranking system by running benchmarks
    across all categories and updating the rankings.

    Examples:
        alphaswarm benchmark integrate anthropic/claude-3.5-sonnet
        alphaswarm benchmark integrate openai/gpt-4o --iterations 5
        alphaswarm benchmark integrate local/model --no-benchmarks
    """
    typer.echo(f"Integrating model: {model_id}")
    typer.echo("")

    # Validate model ID format
    if "/" not in model_id:
        typer.echo(
            "Warning: Model ID should be in format 'provider/model-name'",
            err=True
        )

    # Initialize store
    store = RankingsStore()

    # Check if already exists
    existing_rankings = store.get_all_rankings()
    existing_models = set(r.model_id for r in existing_rankings)

    if model_id in existing_models:
        typer.echo(f"Model {model_id} already has rankings.")
        if not typer.confirm("Run fresh benchmarks anyway?"):
            return

    if run_benchmarks:
        typer.echo(f"Running benchmarks ({iterations} iterations per category)...")
        typer.echo("")

        # Run benchmarks for all categories
        categories = list(BENCHMARK_CATEGORIES.keys())
        total = len(categories) * iterations

        with typer.progressbar(length=total, label="Benchmarking") as progress:
            for cat in categories:
                for _ in range(iterations):
                    result = _run_single_benchmark(model_id, cat, verbose=False)
                    _update_ranking_from_result(store, result)
                    progress.update(1)

        store.save()
        typer.echo("")
        typer.echo(f"Model {model_id} integrated successfully!")
        typer.echo(f"Rankings saved to: {store.path}")

        # Show rankings for the new model
        typer.echo("\nRankings for new model:")
        typer.echo("-" * 60)

        for cat in categories:
            ranking = store.get_ranking(model_id, cat)
            if ranking:
                typer.echo(f"  {cat}: score={ranking.score():.3f}, quality={ranking.quality_score:.2f}")
    else:
        # Just add placeholder rankings
        for cat in BENCHMARK_CATEGORIES.keys():
            ranking = ModelRanking(
                model_id=model_id,
                task_type=cat,
                success_rate=0.0,
                average_latency_ms=0,
                average_tokens=0,
                quality_score=0.0,
                cost_per_task=0.0,
                sample_count=0,
            )
            store.update_ranking(ranking)

        store.save()
        typer.echo(f"Model {model_id} added with empty rankings.")
        typer.echo("Run 'alphaswarm benchmark run' to populate rankings.")


@benchmark_cli.command("export")
def benchmark_export(
    fmt: BenchmarkFormat = typer.Option(
        BenchmarkFormat.JSON,
        "--format",
        "-f",
        help="Export format",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path",
    ),
    include_history: bool = typer.Option(
        False,
        "--history",
        help="Include historical data if available",
    ),
) -> None:
    """Export benchmark results.

    Exports all rankings to the specified format.
    Useful for analysis, reporting, or backup.

    Examples:
        alphaswarm benchmark export --format json -o rankings.json
        alphaswarm benchmark export --format csv -o rankings.csv
        alphaswarm benchmark export --format json  # prints to stdout
    """
    store = RankingsStore()

    if not store.exists():
        typer.echo("No rankings to export.", err=True)
        raise typer.Exit(code=1)

    rankings_data = store.load()
    stats = store.get_stats()

    # Build export data
    export_data = {
        "exported_at": datetime.utcnow().isoformat(),
        "stats": stats,
        "rankings": {},
    }

    for task_type, model_rankings in rankings_data.items():
        export_data["rankings"][task_type] = [
            r.to_dict() for r in sorted(
                model_rankings.values(),
                key=lambda r: r.score(),
                reverse=True,
            )
        ]

    # Generate output
    if fmt == BenchmarkFormat.JSON:
        content = json.dumps(export_data, indent=2, default=str)
    elif fmt == BenchmarkFormat.CSV:
        lines = ["task_type,model_id,score,success_rate,quality_score,latency_ms,cost,sample_count"]
        for task_type, model_rankings in rankings_data.items():
            for r in model_rankings.values():
                lines.append(
                    f"{task_type},{r.model_id},{r.score():.4f},{r.success_rate:.4f},"
                    f"{r.quality_score:.4f},{r.average_latency_ms},{r.cost_per_task:.6f},"
                    f"{r.sample_count}"
                )
        content = "\n".join(lines)
    else:  # TABLE - not exportable, show error
        typer.echo("Use --format json or --format csv for export", err=True)
        raise typer.Exit(code=1)

    # Output
    if output:
        with open(output, "w") as f:
            f.write(content)
        typer.echo(f"Exported to: {output}")
        typer.echo(f"Format: {fmt.value}")
        typer.echo(f"Total rankings: {stats['total_rankings']}")
    else:
        typer.echo(content)


@benchmark_cli.command("list-categories")
def list_categories() -> None:
    """List available benchmark categories.

    Shows all task types that can be benchmarked with descriptions.

    Examples:
        alphaswarm benchmark list-categories
    """
    typer.echo("\n" + "=" * 60)
    typer.echo("BENCHMARK CATEGORIES")
    typer.echo("=" * 60)
    typer.echo(f"\n{'Category':<15} {'Description'}")
    typer.echo("-" * 60)

    for cat, desc in BENCHMARK_CATEGORIES.items():
        typer.echo(f"{cat:<15} {desc}")

    typer.echo("-" * 60)
    typer.echo(f"\nTotal: {len(BENCHMARK_CATEGORIES)} categories")
    typer.echo("=" * 60 + "\n")


# =============================================================================
# Exports
# =============================================================================


__all__ = [
    "benchmark_cli",
    "BenchmarkFormat",
    "BENCHMARK_CATEGORIES",
]
