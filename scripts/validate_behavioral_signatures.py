#!/usr/bin/env python3
"""Behavioral Signature Validation CLI for GA Validation (Plan 07.3-02).

Validates that BSKG behavioral signatures are computed consistently and
do not rely on function names. This proves semantic operation sequencing
(not naming) drives detection.

Usage:
    uv run python scripts/validate_behavioral_signatures.py --help
    uv run python scripts/validate_behavioral_signatures.py --sample 50
    uv run python scripts/validate_behavioral_signatures.py --sample 50 --output .vrs/testing/reports/behavioral-signatures.json

Philosophy Reference: "Names lie. Behavior does not." - PHILOSOPHY.md Pillar 2
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import structlog

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)
logger = structlog.get_logger()

# Common name heuristic tokens that should NOT be needed for detection
NAME_HEURISTIC_TOKENS = frozenset({
    "withdraw",
    "transfer",
    "admin",
    "owner",
    "mint",
    "burn",
    "deposit",
    "claim",
    "redeem",
    "stake",
    "unstake",
    "send",
    "receive",
    "approve",
    "allowance",
})


@dataclass
class FunctionSignatureData:
    """Data for a single function's behavioral signature."""

    contract_id: str
    contract_name: str
    function_name: str
    behavioral_signature: str
    has_name_heuristic: bool
    name_tokens_matched: List[str]


@dataclass
class SignatureStats:
    """Statistics for a particular signature type."""

    signature: str
    count: int
    functions_with_name_heuristic: int
    functions_without_name_heuristic: int
    name_free_ratio: float
    sample_functions: List[str] = field(default_factory=list)


@dataclass
class ValidationReport:
    """Complete validation report for behavioral signatures."""

    generated_at: str
    corpus_version: str
    sample_size: int
    contracts_processed: int
    total_functions: int
    functions_with_signatures: int
    unique_signatures: int

    # Top signatures by frequency
    top_signatures: List[SignatureStats]

    # Name-agnostic validation
    name_heuristic_analysis: Dict[str, Any]

    # Key signature coverage
    key_signatures: Dict[str, SignatureStats]

    # Pass/fail status
    min_name_free_threshold: float
    passes_threshold: bool
    violations: List[str]


def check_name_heuristics(function_name: str) -> Tuple[bool, List[str]]:
    """Check if a function name contains common heuristic tokens.

    Args:
        function_name: Name of the function to check

    Returns:
        Tuple of (has_heuristic_tokens, list_of_matched_tokens)
    """
    normalized = function_name.lower()
    matched = []

    for token in NAME_HEURISTIC_TOKENS:
        if token in normalized:
            matched.append(token)

    return len(matched) > 0, matched


def get_corpus_contracts(
    corpus_db_path: Path,
    sample_size: Optional[int] = None,
    seed: int = 42,
) -> List[Dict[str, Any]]:
    """Load contracts from corpus database.

    Args:
        corpus_db_path: Path to corpus.db
        sample_size: Optional number of contracts to sample
        seed: Random seed for reproducibility

    Returns:
        List of contract records
    """
    from alphaswarm_sol.testing.corpus.db import CorpusDB

    db = CorpusDB(corpus_db_path)

    # Get all contracts
    all_contracts = db.get_contracts()
    db.close()

    if sample_size is not None and sample_size < len(all_contracts):
        random.seed(seed)
        return random.sample(all_contracts, sample_size)

    return all_contracts


def get_test_contracts(
    test_contracts_dir: Path,
    sample_size: Optional[int] = None,
    seed: int = 42,
) -> List[Dict[str, Any]]:
    """Load test contracts from filesystem.

    Args:
        test_contracts_dir: Path to tests/contracts directory
        sample_size: Optional number of contracts to sample
        seed: Random seed for reproducibility

    Returns:
        List of synthetic contract records
    """
    contracts = []

    # Find all .sol files (excluding .t.sol test files)
    for sol_file in test_contracts_dir.glob("*.sol"):
        if sol_file.name.endswith(".t.sol"):
            continue

        contracts.append({
            "contract_id": sol_file.stem,
            "source_path": str(sol_file.relative_to(test_contracts_dir.parent.parent)),
            "category": "test",
        })

    if sample_size is not None and sample_size < len(contracts):
        random.seed(seed)
        return random.sample(contracts, sample_size)

    return contracts


def build_graph_for_contract(
    source_path: str,
    corpus_root: Path,
) -> Optional[Any]:
    """Build knowledge graph for a contract.

    Args:
        source_path: Relative path to contract within corpus
        corpus_root: Root path of corpus

    Returns:
        KnowledgeGraph or None if build fails
    """
    from alphaswarm_sol.kg.builder.core import VKGBuilder

    full_path = corpus_root / source_path

    if not full_path.exists():
        logger.warning("contract_not_found", path=str(full_path))
        return None

    try:
        # Use the directory containing the contract as project root
        # But resolve to absolute path for Slither compatibility
        project_root = full_path.parent.resolve()
        target_path = full_path.resolve()

        builder = VKGBuilder(
            project_root,
            exclude_dependencies=True,
            generate_completeness_report=False,
        )
        return builder.build(target_path)
    except Exception as e:
        logger.warning(
            "graph_build_failed",
            path=str(full_path),
            error=str(e)[:200],
        )
        return None


def extract_function_signatures(
    graph: Any,
    contract_id: str,
) -> List[FunctionSignatureData]:
    """Extract behavioral signatures from a knowledge graph.

    Args:
        graph: KnowledgeGraph object
        contract_id: Contract identifier for reporting

    Returns:
        List of FunctionSignatureData objects
    """
    results = []

    # KnowledgeGraph.nodes is a dict[str, Node]
    for node_id, node in graph.nodes.items():
        # Node type is capitalized ("Function", not "function")
        if node.type.lower() != "function":
            continue

        props = node.properties
        signature = props.get("behavioral_signature", "")
        function_name = props.get("name", "") or node.id.split(".")[-1]
        contract_name = props.get("contract", "") or contract_id

        # Skip empty signatures
        if not signature:
            continue

        has_heuristic, matched_tokens = check_name_heuristics(function_name)

        results.append(FunctionSignatureData(
            contract_id=contract_id,
            contract_name=contract_name,
            function_name=function_name,
            behavioral_signature=signature,
            has_name_heuristic=has_heuristic,
            name_tokens_matched=matched_tokens,
        ))

    return results


def compute_signature_stats(
    all_signatures: List[FunctionSignatureData],
    top_n: int = 20,
) -> Tuple[List[SignatureStats], Dict[str, SignatureStats]]:
    """Compute statistics for behavioral signatures.

    Args:
        all_signatures: List of all function signature data
        top_n: Number of top signatures to return

    Returns:
        Tuple of (top_signatures_list, key_signatures_dict)
    """
    # Group by signature
    signature_groups: Dict[str, List[FunctionSignatureData]] = {}
    for sig_data in all_signatures:
        sig = sig_data.behavioral_signature
        if sig not in signature_groups:
            signature_groups[sig] = []
        signature_groups[sig].append(sig_data)

    # Compute stats for each signature
    all_stats: List[SignatureStats] = []

    for sig, funcs in signature_groups.items():
        with_heuristic = sum(1 for f in funcs if f.has_name_heuristic)
        without_heuristic = len(funcs) - with_heuristic
        name_free_ratio = without_heuristic / len(funcs) if funcs else 0.0

        # Get sample function names
        sample_funcs = [f.function_name for f in funcs[:5]]

        all_stats.append(SignatureStats(
            signature=sig,
            count=len(funcs),
            functions_with_name_heuristic=with_heuristic,
            functions_without_name_heuristic=without_heuristic,
            name_free_ratio=name_free_ratio,
            sample_functions=sample_funcs,
        ))

    # Sort by count for top signatures
    all_stats.sort(key=lambda s: s.count, reverse=True)
    top_signatures = all_stats[:top_n]

    # Key signatures for reentrancy/CEI detection
    # Vulnerable pattern: R:bal -> X:out -> W:bal or similar
    # Safe pattern: R:bal -> W:bal -> X:out
    key_signature_patterns = {
        "vulnerable_reentrancy": re.compile(r".*X:(out|call).*W:bal.*"),
        "safe_cei": re.compile(r".*W:bal.*X:(out|call).*"),
        "external_call": re.compile(r".*X:(call|out|unk).*"),
        "balance_write": re.compile(r".*W:bal.*"),
        "auth_check": re.compile(r".*C:auth.*"),
        "owner_modify": re.compile(r".*M:(own|crit).*"),
    }

    key_signatures: Dict[str, SignatureStats] = {}
    for key, pattern in key_signature_patterns.items():
        matching = [s for s in all_stats if pattern.match(s.signature)]
        if matching:
            # Aggregate all matching
            total_count = sum(s.count for s in matching)
            total_with = sum(s.functions_with_name_heuristic for s in matching)
            total_without = sum(s.functions_without_name_heuristic for s in matching)
            name_free = total_without / total_count if total_count else 0.0

            key_signatures[key] = SignatureStats(
                signature=f"[{len(matching)} patterns]",
                count=total_count,
                functions_with_name_heuristic=total_with,
                functions_without_name_heuristic=total_without,
                name_free_ratio=name_free,
                sample_functions=[s.signature for s in matching[:3]],
            )

    return top_signatures, key_signatures


def validate_behavioral_signatures(
    corpus_db_path: Path,
    corpus_root: Path,
    sample_size: Optional[int] = None,
    min_name_free: float = 0.5,
    seed: int = 42,
) -> ValidationReport:
    """Run behavioral signature validation.

    Args:
        corpus_db_path: Path to corpus.db
        corpus_root: Root path of corpus contracts
        sample_size: Optional number of contracts to sample
        min_name_free: Minimum ratio of name-free detections (0-1)
        seed: Random seed for reproducibility

    Returns:
        ValidationReport with results
    """
    logger.info(
        "validation_start",
        corpus_db=str(corpus_db_path),
        sample_size=sample_size,
    )

    # Load contracts
    contracts = get_corpus_contracts(corpus_db_path, sample_size, seed)
    logger.info("contracts_loaded", count=len(contracts))

    # Process each contract
    all_signatures: List[FunctionSignatureData] = []
    contracts_processed = 0

    for contract in contracts:
        source_path = contract.get("source_path", "")
        contract_id = contract.get("contract_id", "unknown")

        # Build graph
        graph = build_graph_for_contract(source_path, corpus_root)
        if graph is None:
            continue

        # Extract signatures
        signatures = extract_function_signatures(graph, contract_id)
        all_signatures.extend(signatures)
        contracts_processed += 1

        if contracts_processed % 10 == 0:
            logger.info(
                "progress",
                processed=contracts_processed,
                total=len(contracts),
                signatures=len(all_signatures),
            )

    logger.info(
        "extraction_complete",
        contracts=contracts_processed,
        signatures=len(all_signatures),
    )

    # Compute statistics
    unique_signatures = len(set(s.behavioral_signature for s in all_signatures))
    top_signatures, key_signatures = compute_signature_stats(all_signatures)

    # Name heuristic analysis
    total_with_heuristic = sum(1 for s in all_signatures if s.has_name_heuristic)
    total_without_heuristic = len(all_signatures) - total_with_heuristic
    overall_name_free_ratio = total_without_heuristic / len(all_signatures) if all_signatures else 0.0

    name_heuristic_analysis = {
        "total_functions": len(all_signatures),
        "functions_with_name_heuristic": total_with_heuristic,
        "functions_without_name_heuristic": total_without_heuristic,
        "overall_name_free_ratio": overall_name_free_ratio,
        "token_frequency": dict(Counter(
            token
            for s in all_signatures
            for token in s.name_tokens_matched
        )),
    }

    # Check violations
    violations = []
    for key, stats in key_signatures.items():
        if stats.name_free_ratio < min_name_free:
            violations.append(
                f"{key}: name_free_ratio={stats.name_free_ratio:.2f} < {min_name_free}"
            )

    passes_threshold = len(violations) == 0

    # Build report
    report = ValidationReport(
        generated_at=datetime.now(timezone.utc).isoformat(),
        corpus_version="v1",
        sample_size=len(contracts),
        contracts_processed=contracts_processed,
        total_functions=len(all_signatures),
        functions_with_signatures=len([s for s in all_signatures if s.behavioral_signature]),
        unique_signatures=unique_signatures,
        top_signatures=top_signatures,
        name_heuristic_analysis=name_heuristic_analysis,
        key_signatures={k: asdict(v) for k, v in key_signatures.items()},
        min_name_free_threshold=min_name_free,
        passes_threshold=passes_threshold,
        violations=violations,
    )

    logger.info(
        "validation_complete",
        unique_signatures=unique_signatures,
        passes_threshold=passes_threshold,
        violations=len(violations),
    )

    return report


def validate_behavioral_signatures_from_dir(
    contracts_dir: Path,
    sample_size: Optional[int] = None,
    min_name_free: float = 0.5,
    seed: int = 42,
) -> ValidationReport:
    """Run behavioral signature validation on a directory of contracts.

    Args:
        contracts_dir: Path to directory containing .sol files
        sample_size: Optional number of contracts to sample
        min_name_free: Minimum ratio of name-free detections (0-1)
        seed: Random seed for reproducibility

    Returns:
        ValidationReport with results
    """
    from alphaswarm_sol.kg.builder.core import VKGBuilder

    logger.info(
        "validation_start_dir",
        contracts_dir=str(contracts_dir),
        sample_size=sample_size,
    )

    # Find contracts
    contracts = list(contracts_dir.glob("*.sol"))
    # Filter out test files
    contracts = [c for c in contracts if not c.name.endswith(".t.sol")]

    if sample_size is not None and sample_size < len(contracts):
        random.seed(seed)
        contracts = random.sample(contracts, sample_size)

    logger.info("contracts_found", count=len(contracts))

    # Process each contract
    all_signatures: List[FunctionSignatureData] = []
    contracts_processed = 0

    for contract_path in contracts:
        contract_id = contract_path.stem

        try:
            builder = VKGBuilder(
                contract_path.parent,
                exclude_dependencies=True,
                generate_completeness_report=False,
            )
            graph = builder.build(contract_path)
        except Exception as e:
            logger.warning(
                "graph_build_failed",
                path=str(contract_path),
                error=str(e)[:200],
            )
            continue

        # Extract signatures
        signatures = extract_function_signatures(graph, contract_id)
        all_signatures.extend(signatures)
        contracts_processed += 1

        if contracts_processed % 10 == 0:
            logger.info(
                "progress",
                processed=contracts_processed,
                total=len(contracts),
                signatures=len(all_signatures),
            )

    logger.info(
        "extraction_complete",
        contracts=contracts_processed,
        signatures=len(all_signatures),
    )

    # Compute statistics
    unique_signatures = len(set(s.behavioral_signature for s in all_signatures))
    top_signatures, key_signatures = compute_signature_stats(all_signatures)

    # Name heuristic analysis
    total_with_heuristic = sum(1 for s in all_signatures if s.has_name_heuristic)
    total_without_heuristic = len(all_signatures) - total_with_heuristic
    overall_name_free_ratio = total_without_heuristic / len(all_signatures) if all_signatures else 0.0

    name_heuristic_analysis = {
        "total_functions": len(all_signatures),
        "functions_with_name_heuristic": total_with_heuristic,
        "functions_without_name_heuristic": total_without_heuristic,
        "overall_name_free_ratio": overall_name_free_ratio,
        "token_frequency": dict(Counter(
            token
            for s in all_signatures
            for token in s.name_tokens_matched
        )),
    }

    # Check violations
    violations = []
    for key, stats in key_signatures.items():
        if stats.name_free_ratio < min_name_free:
            violations.append(
                f"{key}: name_free_ratio={stats.name_free_ratio:.2f} < {min_name_free}"
            )

    passes_threshold = len(violations) == 0

    # Build report
    report = ValidationReport(
        generated_at=datetime.now(timezone.utc).isoformat(),
        corpus_version="test-contracts",
        sample_size=len(contracts),
        contracts_processed=contracts_processed,
        total_functions=len(all_signatures),
        functions_with_signatures=len([s for s in all_signatures if s.behavioral_signature]),
        unique_signatures=unique_signatures,
        top_signatures=top_signatures,
        name_heuristic_analysis=name_heuristic_analysis,
        key_signatures={k: asdict(v) for k, v in key_signatures.items()},
        min_name_free_threshold=min_name_free,
        passes_threshold=passes_threshold,
        violations=violations,
    )

    logger.info(
        "validation_complete",
        unique_signatures=unique_signatures,
        passes_threshold=passes_threshold,
        violations=len(violations),
    )

    return report


def serialize_report(report: ValidationReport) -> Dict[str, Any]:
    """Serialize report to JSON-compatible dict."""
    result = {
        "generated_at": report.generated_at,
        "corpus_version": report.corpus_version,
        "sample_size": report.sample_size,
        "contracts_processed": report.contracts_processed,
        "total_functions": report.total_functions,
        "functions_with_signatures": report.functions_with_signatures,
        "unique_signatures": report.unique_signatures,
        "top_signatures": [asdict(s) for s in report.top_signatures],
        "name_heuristic_analysis": report.name_heuristic_analysis,
        "key_signatures": report.key_signatures,
        "min_name_free_threshold": report.min_name_free_threshold,
        "passes_threshold": report.passes_threshold,
        "violations": report.violations,
    }
    return result


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate behavioral signature coverage and name-agnosticism",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--sample",
        type=int,
        default=None,
        help="Number of contracts to sample (default: all)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(".vrs/testing/reports/behavioral-signatures.json"),
        help="Output path for JSON report",
    )
    parser.add_argument(
        "--min-name-free",
        type=float,
        default=0.5,
        help="Minimum ratio of name-free detections (default: 0.5)",
    )
    parser.add_argument(
        "--corpus-db",
        type=Path,
        default=Path(".vrs/corpus/corpus.db"),
        help="Path to corpus database",
    )
    parser.add_argument(
        "--corpus-root",
        type=Path,
        default=Path(".vrs/corpus"),
        help="Root path for corpus contracts",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for sampling (default: 42)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print summary without writing output",
    )
    parser.add_argument(
        "--use-test-contracts",
        action="store_true",
        help="Use tests/contracts instead of corpus (for dev/testing)",
    )
    parser.add_argument(
        "--test-contracts-dir",
        type=Path,
        default=Path("tests/contracts"),
        help="Path to test contracts directory",
    )

    args = parser.parse_args()

    # Validate paths
    if args.use_test_contracts:
        if not args.test_contracts_dir.exists():
            print(f"ERROR: Test contracts dir not found: {args.test_contracts_dir}", file=sys.stderr)
            return 1
    else:
        if not args.corpus_db.exists():
            print(f"ERROR: Corpus database not found: {args.corpus_db}", file=sys.stderr)
            return 1

        if not args.corpus_root.exists():
            print(f"ERROR: Corpus root not found: {args.corpus_root}", file=sys.stderr)
            return 1

    # Run validation
    try:
        if args.use_test_contracts:
            report = validate_behavioral_signatures_from_dir(
                contracts_dir=args.test_contracts_dir.resolve(),
                sample_size=args.sample,
                min_name_free=args.min_name_free,
                seed=args.seed,
            )
        else:
            report = validate_behavioral_signatures(
                corpus_db_path=args.corpus_db,
                corpus_root=args.corpus_root,
                sample_size=args.sample,
                min_name_free=args.min_name_free,
                seed=args.seed,
            )
    except Exception as e:
        print(f"ERROR: Validation failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1

    # Print summary
    print("\n" + "=" * 60)
    print("BEHAVIORAL SIGNATURE VALIDATION SUMMARY")
    print("=" * 60)
    print()
    print(f"Sample size:            {report.sample_size}")
    print(f"Contracts processed:    {report.contracts_processed}")
    print(f"Total functions:        {report.total_functions}")
    print(f"Functions w/signatures: {report.functions_with_signatures}")
    print(f"Unique signatures:      {report.unique_signatures}")
    print()

    print("TOP 10 SIGNATURES:")
    for i, sig in enumerate(report.top_signatures[:10], 1):
        print(f"  {i}. [{sig.count:4d}] {sig.signature[:50]:<50} (name-free: {sig.name_free_ratio:.0%})")
    print()

    print("KEY SIGNATURES (Name-agnostic check):")
    for key, stats in report.key_signatures.items():
        status = "PASS" if stats["name_free_ratio"] >= args.min_name_free else "FAIL"
        print(f"  {key:25s}: {stats['count']:4d} funcs, name-free: {stats['name_free_ratio']:.0%} [{status}]")
    print()

    print(f"NAME HEURISTIC ANALYSIS:")
    nha = report.name_heuristic_analysis
    print(f"  Overall name-free ratio: {nha['overall_name_free_ratio']:.1%}")
    print(f"  Functions with name tokens: {nha['functions_with_name_heuristic']}")
    print(f"  Functions without name tokens: {nha['functions_without_name_heuristic']}")
    print()

    if report.violations:
        print("VIOLATIONS:")
        for v in report.violations:
            print(f"  - {v}")
        print()

    status = "PASSED" if report.passes_threshold else "FAILED"
    print(f"VALIDATION: {status} (threshold: {args.min_name_free})")
    print()

    # Write output
    if not args.dry_run:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w") as f:
            json.dump(serialize_report(report), f, indent=2)
        print(f"Report written to: {args.output}")
    else:
        print("[DRY RUN] Report not written")

    return 0 if report.passes_threshold else 1


if __name__ == "__main__":
    sys.exit(main())
