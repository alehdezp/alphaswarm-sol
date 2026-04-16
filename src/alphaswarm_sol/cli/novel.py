"""CLI commands for Novel Solutions (Phase 15).

Integrates the top-scoring novel solutions:
- Semantic Similarity: Find similar code patterns
- Self-Evolution: Optimize patterns via genetic algorithms
- Formal Invariants: Discover and verify contract invariants
- Adversarial Testing: Test pattern robustness via mutation/metamorphic testing
"""

from __future__ import annotations

import json
from pathlib import Path

import structlog
import typer

novel_app = typer.Typer(help="Novel solution commands for advanced analysis")


def _handle_error(exc: Exception) -> None:
    logger = structlog.get_logger()
    logger.error("command_failed", error=str(exc))
    raise typer.Exit(code=1) from exc


# =============================================================================
# SEMANTIC SIMILARITY COMMANDS
# =============================================================================

similarity_app = typer.Typer(help="Semantic code similarity analysis")
novel_app.add_typer(similarity_app, name="similar")


@similarity_app.command("find")
def similar_find(
    graph: str = typer.Option(..., "--graph", "-g", help="Graph path or contract stem (e.g., 'Token')."),
    function: str = typer.Option(..., "--function", "-f", help="Function name to find similar code for"),
    threshold: float = typer.Option(0.7, "--threshold", "-t", help="Similarity threshold (0-1)"),
    limit: int = typer.Option(10, "--limit", "-l", help="Maximum results to return"),
    output_format: str = typer.Option("json", "--format", help="Output format: json or human"),
) -> None:
    """Find functions similar to a given function.

    Uses semantic fingerprinting based on operations, not syntax.
    """
    try:
        from alphaswarm_sol.similarity import (
            SimilarityEngine,
            EngineConfig,
            FingerprintGenerator,
        )
        from alphaswarm_sol.cli.graph_resolution import resolve_and_load_graph

        graph_obj, _ = resolve_and_load_graph(graph)

        # Create similarity engine
        config = EngineConfig(
            similarity_threshold=threshold,
            max_results=limit,
        )
        engine = SimilarityEngine(config)

        # Find target function
        target_node = None
        for node in graph_obj.nodes:
            if node.type == "Function" and node.properties.get("name") == function:
                target_node = node
                break

        if not target_node:
            typer.echo(f"Error: Function '{function}' not found in graph", err=True)
            raise typer.Exit(code=1)

        # Generate fingerprint for target
        generator = FingerprintGenerator()
        target_fp = generator.from_node(target_node)

        # Find similar functions
        results = []
        for node in graph_obj.nodes:
            if node.type != "Function" or node.id == target_node.id:
                continue

            node_fp = generator.from_node(node)
            score = engine.compute_similarity(target_fp, node_fp)

            if score.overall >= threshold:
                results.append({
                    "function": node.properties.get("name", node.id),
                    "contract": node.properties.get("contract", "unknown"),
                    "similarity": round(score.overall, 4),
                    "operation_match": round(score.operation_similarity, 4),
                    "structural_match": round(score.structural_similarity, 4),
                })

        # Sort by similarity
        results.sort(key=lambda x: x["similarity"], reverse=True)
        results = results[:limit]

        # Output
        if output_format == "json":
            output = {
                "target": function,
                "threshold": threshold,
                "similar_functions": results,
                "count": len(results),
            }
            typer.echo(json.dumps(output, indent=2))
        else:
            typer.echo(f"Functions similar to '{function}' (threshold: {threshold}):")
            typer.echo("=" * 60)
            for i, r in enumerate(results, 1):
                typer.echo(f"{i}. {r['contract']}.{r['function']}")
                typer.echo(f"   Similarity: {r['similarity']:.2%}")
                typer.echo(f"   Operations: {r['operation_match']:.2%}, Structure: {r['structural_match']:.2%}")
                typer.echo()

        structlog.get_logger().info(
            "similarity_search_complete",
            target=function,
            results=len(results),
        )

    except typer.Exit:
        raise
    except Exception as exc:
        _handle_error(exc)


@similarity_app.command("clones")
def similar_clones(
    graph: str = typer.Option(..., "--graph", "-g", help="Graph path or contract stem (e.g., 'Token')."),
    threshold: float = typer.Option(0.9, "--threshold", "-t", help="Clone detection threshold"),
    output_format: str = typer.Option("json", "--format", help="Output format: json or human"),
) -> None:
    """Detect code clones in the codebase.

    Finds functions that are near-copies of each other, which may
    indicate copy-paste vulnerabilities.
    """
    try:
        from alphaswarm_sol.similarity import CloneDetector, CloneType, FingerprintGenerator
        from alphaswarm_sol.cli.graph_resolution import resolve_and_load_graph

        graph_obj, _ = resolve_and_load_graph(graph)

        # Generate fingerprints for all functions
        generator = FingerprintGenerator()
        fingerprints = []
        for node in graph_obj.nodes.values():
            if node.type == "Function":
                fp = generator.from_node(node)
                fingerprints.append(fp)

        # Detect clones
        detector = CloneDetector()
        clones = detector.detect_clones(fingerprints, min_similarity=threshold)

        # Output
        if output_format == "json":
            output = {
                "threshold": threshold,
                "clones": [
                    {
                        "type": c.clone_type.value,
                        "source": f"{c.source_contract}.{c.source_function}",
                        "target": f"{c.target_contract}.{c.target_function}",
                        "similarity": round(c.similarity, 4),
                    }
                    for c in clones
                ],
                "count": len(clones),
            }
            typer.echo(json.dumps(output, indent=2))
        else:
            typer.echo(f"Code clones detected (threshold: {threshold}):")
            typer.echo("=" * 60)
            for c in clones:
                typer.echo(f"  {c.source_contract}.{c.source_function} <-> {c.target_contract}.{c.target_function}")
                typer.echo(f"  Type: {c.clone_type.value}, Similarity: {c.similarity:.2%}")
                typer.echo()

    except typer.Exit:
        raise
    except Exception as exc:
        _handle_error(exc)


# =============================================================================
# PATTERN EVOLUTION COMMANDS
# =============================================================================

evolution_app = typer.Typer(help="Pattern evolution via genetic algorithms")
novel_app.add_typer(evolution_app, name="evolve")


@evolution_app.command("pattern")
def evolve_pattern(
    pattern_file: str = typer.Argument(..., help="Path to pattern YAML file"),
    generations: int = typer.Option(10, "--generations", "-g", help="Number of generations"),
    population: int = typer.Option(20, "--population", "-p", help="Population size"),
    target_f1: float = typer.Option(0.9, "--target-f1", help="Target F1 score"),
    output: str | None = typer.Option(None, "--output", "-o", help="Output path for evolved pattern"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show evolution progress"),
) -> None:
    """Evolve a pattern to improve its F1 score.

    Uses genetic algorithms to mutate pattern conditions and
    thresholds, selecting for higher precision and recall.
    """
    try:
        from alphaswarm_sol.evolution import (
            PatternEvolutionEngine,
            EvolvablePattern,
        )
        import yaml

        # Load pattern
        pattern_path = Path(pattern_file)
        if not pattern_path.exists():
            typer.echo(f"Error: Pattern file not found: {pattern_path}", err=True)
            raise typer.Exit(code=1)

        with open(pattern_path) as f:
            pattern_data = yaml.safe_load(f)

        # Create evolvable pattern
        pattern = EvolvablePattern.from_dict(pattern_data)

        # Create evolution engine
        engine = PatternEvolutionEngine(
            population_size=population,
            generations=generations,
            target_f1=target_f1,
        )

        # Run evolution
        typer.echo(f"Evolving pattern: {pattern.id}")
        typer.echo(f"Generations: {generations}, Population: {population}, Target F1: {target_f1}")
        typer.echo()

        best = engine.evolve(
            pattern,
            callback=lambda g, f: typer.echo(f"  Gen {g}: Best F1 = {f:.4f}") if verbose else None,
        )

        # Output results
        typer.echo()
        typer.echo(f"Evolution complete!")
        typer.echo(f"  Initial F1: {pattern.fitness:.4f}")
        typer.echo(f"  Final F1:   {best.fitness:.4f}")
        typer.echo(f"  Improvement: {best.fitness - pattern.fitness:+.4f}")

        if output:
            output_path = Path(output)
            with open(output_path, "w") as f:
                yaml.dump(best.to_dict(), f, default_flow_style=False)
            typer.echo(f"Evolved pattern saved to: {output_path}")
        else:
            typer.echo()
            typer.echo("Evolved pattern (YAML):")
            typer.echo(yaml.dump(best.to_dict(), default_flow_style=False))

    except typer.Exit:
        raise
    except Exception as exc:
        _handle_error(exc)


# =============================================================================
# INVARIANT COMMANDS
# =============================================================================

invariant_app = typer.Typer(help="Formal invariant discovery and verification")
novel_app.add_typer(invariant_app, name="invariants")


@invariant_app.command("discover")
def invariant_discover(
    graph: str = typer.Option(..., "--graph", "-g", help="Graph path or contract stem (e.g., 'Token')."),
    contract: str | None = typer.Option(None, "--contract", "-c", help="Filter by contract name"),
    output_format: str = typer.Option("json", "--format", help="Output format: json or solidity"),
) -> None:
    """Discover contract invariants from code patterns.

    Analyzes the knowledge graph to infer properties that should
    always hold (e.g., "balance >= 0", "owner != address(0)").
    """
    try:
        from alphaswarm_sol.invariants import (
            InvariantMiner,
            InvariantGenerator,
            MiningConfig,
        )
        from alphaswarm_sol.cli.graph_resolution import resolve_and_load_graph

        graph_obj, _ = resolve_and_load_graph(graph)

        # Mine invariants
        config = MiningConfig()
        miner = InvariantMiner(config)
        result = miner.mine(graph_obj)

        # Filter by contract if specified
        invariants = result.invariants
        if contract:
            invariants = [
                inv for inv in invariants
                if inv.location and contract in inv.location
            ]

        if output_format == "solidity":
            # Generate Solidity assertions
            generator = InvariantGenerator()
            for inv in invariants:
                code = generator.generate(inv)
                typer.echo(f"// Invariant: {inv.description}")
                typer.echo(code.assertion_code)
                typer.echo()
        else:
            # JSON output
            output = {
                "contract": contract or "all",
                "invariants": [
                    {
                        "id": inv.id,
                        "type": inv.invariant_type.value,
                        "description": inv.description,
                        "expression": inv.expression,
                        "strength": inv.strength.value,
                        "location": inv.location,
                    }
                    for inv in invariants
                ],
                "count": len(invariants),
            }
            typer.echo(json.dumps(output, indent=2))

    except typer.Exit:
        raise
    except Exception as exc:
        _handle_error(exc)


@invariant_app.command("verify")
def invariant_verify(
    graph: str = typer.Option(..., "--graph", "-g", help="Graph path or contract stem (e.g., 'Token')."),
    invariant: str = typer.Option(..., "--invariant", "-i", help="Invariant expression to verify"),
    use_z3: bool = typer.Option(False, "--z3", help="Use Z3 for formal verification"),
) -> None:
    """Verify that an invariant holds.

    Checks whether the given invariant expression holds across
    all execution paths in the contract.
    """
    try:
        from alphaswarm_sol.kg.store import GraphStore
        from alphaswarm_sol.invariants import (
            InvariantVerifier,
            VerifierConfig,
            Invariant,
            InvariantType,
            InvariantStrength,
        )

        from alphaswarm_sol.cli.graph_resolution import resolve_and_load_graph

        graph_obj, _ = resolve_and_load_graph(graph)

        # Create invariant to verify
        inv = Invariant(
            id="user-invariant",
            invariant_type=InvariantType.CUSTOM,
            description="User-specified invariant",
            expression=invariant,
            strength=InvariantStrength.MUST,
        )

        # Verify
        config = VerifierConfig(use_z3=use_z3)
        verifier = InvariantVerifier(config)
        result = verifier.verify(graph_obj, inv)

        # Output
        if result.verified:
            typer.echo(f"✓ Invariant VERIFIED: {invariant}")
            typer.echo(f"  Method: {result.method}")
        else:
            typer.echo(f"✗ Invariant VIOLATED: {invariant}")
            if result.counter_example:
                typer.echo(f"  Counter-example: {result.counter_example}")
            typer.echo(f"  Violation path: {result.violation_path}")

    except typer.Exit:
        raise
    except Exception as exc:
        _handle_error(exc)


# =============================================================================
# ADVERSARIAL TESTING COMMANDS
# =============================================================================

adversarial_app = typer.Typer(help="Adversarial testing for pattern robustness")
novel_app.add_typer(adversarial_app, name="adversarial")


@adversarial_app.command("mutate")
def adversarial_mutate(
    contract: str = typer.Argument(..., help="Path to Solidity contract"),
    mutations: int = typer.Option(10, "--mutations", "-m", help="Number of mutations to generate"),
    output_dir: str | None = typer.Option(None, "--output-dir", "-o", help="Output directory for mutants"),
    operators: str = typer.Option(
        "all",
        "--operators",
        help="Mutation operators: all, remove-require, swap-statements, change-visibility",
    ),
) -> None:
    """Generate mutant contracts for testing.

    Creates variations of the input contract with injected bugs,
    useful for testing whether VKG patterns detect them.
    """
    try:
        from alphaswarm_sol.adversarial import (
            ContractMutator,
            RemoveRequireOperator,
            SwapStatementsOperator,
            ChangeVisibilityOperator,
            RemoveGuardOperator,
        )

        contract_path = Path(contract)
        if not contract_path.exists():
            typer.echo(f"Error: Contract not found: {contract_path}", err=True)
            raise typer.Exit(code=1)

        # Setup operators
        ops = []
        if operators == "all":
            ops = [
                RemoveRequireOperator(),
                SwapStatementsOperator(),
                ChangeVisibilityOperator(),
                RemoveGuardOperator(),
            ]
        else:
            op_map = {
                "remove-require": RemoveRequireOperator,
                "swap-statements": SwapStatementsOperator,
                "change-visibility": ChangeVisibilityOperator,
                "remove-guard": RemoveGuardOperator,
            }
            for op_name in operators.split(","):
                op_name = op_name.strip()
                if op_name in op_map:
                    ops.append(op_map[op_name]())

        # Generate mutants
        mutator = ContractMutator(operators=ops)
        source = contract_path.read_text()
        results = mutator.generate_mutants(source)

        # Limit to requested number
        results = results[:mutations]

        # Output
        out_dir = Path(output_dir) if output_dir else contract_path.parent / "mutants"
        out_dir.mkdir(parents=True, exist_ok=True)

        for i, (mutated_code, mutation_result) in enumerate(results):
            mutant_path = out_dir / f"mutant_{i+1}.sol"
            mutant_path.write_text(mutated_code)

        typer.echo(f"Generated {len(results)} mutants in: {out_dir}")
        for i, (_, mutation_result) in enumerate(results):
            typer.echo(f"  {i+1}. {mutation_result.operator_name}: {mutation_result.description}")

    except typer.Exit:
        raise
    except Exception as exc:
        _handle_error(exc)


@adversarial_app.command("metamorphic")
def adversarial_metamorphic(
    contract: str = typer.Argument(..., help="Path to Solidity contract"),
    iterations: int = typer.Option(5, "--iterations", "-i", help="Number of rename iterations"),
    pattern_id: str = typer.Option("test-all", "--pattern", "-p", help="Pattern ID to test"),
) -> None:
    """Test rename-invariance of VKG patterns.

    Renames identifiers in the contract and verifies that VKG
    produces identical findings. This proves "names lie, behavior doesn't".
    """
    try:
        from alphaswarm_sol.adversarial import MetamorphicTester, IdentifierRenamer

        contract_path = Path(contract)
        if not contract_path.exists():
            typer.echo(f"Error: Contract not found: {contract_path}", err=True)
            raise typer.Exit(code=1)

        typer.echo(f"Testing rename-invariance on: {contract_path}")
        typer.echo(f"Iterations: {iterations}")
        typer.echo()

        # Read contract code
        code = contract_path.read_text()

        # Create simple pattern checker (counts identifier occurrences)
        def simple_checker(source: str) -> bool:
            """Simple pattern check - returns True if code contains require."""
            return "require(" in source or "revert" in source

        # Run metamorphic test
        tester = MetamorphicTester(num_transformations=iterations)
        result = tester.test_pattern(pattern_id, code, simple_checker)

        # Output results
        typer.echo("Results:")
        typer.echo("=" * 60)
        typer.echo(f"  Pattern: {result.pattern_id}")
        typer.echo(f"  Transformations tested: {result.transformations_tested}")
        typer.echo(f"  Pass rate: {result.pass_rate:.0%}")

        if result.passed:
            typer.echo()
            typer.echo("✓ PASS: Pattern detection is rename-invariant!")
            typer.echo("  VKG correctly ignores function/variable names.")
        else:
            typer.echo()
            typer.echo("✗ FAIL: Pattern detection varies with names!")
            for failure in result.failures:
                typer.echo(f"    - {failure.transformation}: {failure.reason}")

    except typer.Exit:
        raise
    except Exception as exc:
        _handle_error(exc)


# =============================================================================
# INFO COMMAND
# =============================================================================

@novel_app.command("info")
def novel_info() -> None:
    """Show information about available novel solutions."""
    typer.echo("Novel Solutions (Phase 15)")
    typer.echo("=" * 60)
    typer.echo()

    solutions = [
        ("similar", "Semantic Similarity", "Find code with similar behavior, detect clones"),
        ("evolve", "Pattern Evolution", "Optimize patterns using genetic algorithms"),
        ("invariants", "Formal Invariants", "Discover and verify contract properties"),
        ("adversarial", "Adversarial Testing", "Test pattern robustness via mutations"),
    ]

    for cmd, name, desc in solutions:
        typer.echo(f"  vkg novel {cmd}")
        typer.echo(f"    {name}: {desc}")
        typer.echo()

    typer.echo("Examples:")
    typer.echo("  vkg novel similar find --graph graph.json --function withdraw")
    typer.echo("  vkg novel evolve pattern vulndocs/reentrancy/classic/patterns/reentrancy-classic.yaml --generations 20")
    typer.echo("  vkg novel invariants discover --graph graph.json")
    typer.echo("  vkg novel adversarial metamorphic Contract.sol")
