#!/usr/bin/env python3
"""
CLI runner for collecting proof tokens with nonce challenge enforcement.

This script manages proof token collection from test runs:
- Generates and injects nonces into test sessions
- Captures transcripts with nonce verification
- Computes transcript hashes for integrity
- Validates nonce presence in transcripts (invalidates if missing)

Nonce Challenge Protocol:
1. Controller generates nonce
2. Subject echoes nonce in test output
3. Proof token stores nonce + transcript hash
4. Missing nonce invalidates the stage proof

Usage:
    # Generate nonce for a stage
    python scripts/e2e/collect_proof_tokens.py \\
        --stage graph_build \\
        --generate-nonce

    # Collect proof token after stage completion
    python scripts/e2e/collect_proof_tokens.py \\
        --stage graph_build \\
        --transcript transcripts/graph.txt \\
        --nonce nonce-8f3d \\
        --output .vrs/proofs \\
        --run-id run-001

    # Validate all proof tokens
    python scripts/e2e/collect_proof_tokens.py \\
        --proofs-dir .vrs/proofs \\
        --validate

    # Collect all proofs from a run
    python scripts/e2e/collect_proof_tokens.py \\
        --transcripts-dir transcripts/ \\
        --output .vrs/proofs \\
        --run-id run-001 \\
        --collect-all
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from alphaswarm_sol.testing.proof_tokens import (
    ProofToken,
    ProofTokenCollector,
    Stage,
    ToolVersions,
    PROOF_SCHEMA_VERSION,
    compute_transcript_hash,
    verify_nonce_in_transcript,
    load_proof_token,
    load_all_proof_tokens,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


# ANSI colors for output
class Colors:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    NC = "\033[0m"  # No color


def log_success(msg: str) -> None:
    """Log success message."""
    print(f"{Colors.GREEN}[OK]{Colors.NC} {msg}")


def log_error(msg: str) -> None:
    """Log error message."""
    print(f"{Colors.RED}[ERROR]{Colors.NC} {msg}")


def log_warn(msg: str) -> None:
    """Log warning message."""
    print(f"{Colors.YELLOW}[WARN]{Colors.NC} {msg}")


def log_info(msg: str) -> None:
    """Log info message."""
    print(f"{Colors.BLUE}[INFO]{Colors.NC} {msg}")


def generate_nonce() -> str:
    """
    Generate a cryptographically secure nonce.

    Returns:
        Nonce string in format 'nonce-XXXX'
    """
    import secrets
    return f"nonce-{secrets.token_hex(2)}"


def inject_nonce_command(nonce: str, marker: str = "[ALPHASWARM-NONCE]") -> str:
    """
    Generate the command to inject nonce into test output.

    The subject should echo this to make nonce visible in transcript.

    Args:
        nonce: The nonce to inject
        marker: Marker prefix for easier extraction

    Returns:
        Command string to execute in test session
    """
    return f'echo "{marker} {nonce}"'


def collect_proof(
    stage: Stage,
    transcript_path: Path,
    nonce: str,
    output_dir: Path,
    run_id: str,
    suite_id: str = "full-testing",
    stage_data: Optional[dict] = None,
    command: str = "/vrs-audit contracts/",
    strict: bool = True,
) -> tuple[ProofToken, bool]:
    """
    Collect a proof token for a completed stage.

    Args:
        stage: The stage that was completed
        transcript_path: Path to transcript file
        nonce: The nonce that should be in transcript
        output_dir: Directory for proof token files
        run_id: Run identifier
        suite_id: Suite identifier
        stage_data: Stage-specific data
        command: Command that was executed
        strict: If True, fail on missing nonce

    Returns:
        (ProofToken, is_valid) tuple
    """
    transcript_path = Path(transcript_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Verify transcript exists
    if not transcript_path.exists():
        raise FileNotFoundError(f"Transcript not found: {transcript_path}")

    # Verify nonce in transcript
    nonce_found = verify_nonce_in_transcript(nonce, transcript_path)

    if not nonce_found:
        log_error(f"Nonce '{nonce}' not found in transcript {transcript_path}")
        if strict:
            log_error("Stage proof is INVALID - nonce challenge failed")

    # Compute transcript hash
    transcript_hash = compute_transcript_hash(transcript_path)

    # Generate proof ID
    stage_name = stage.value.split(".")[-1]
    run_suffix = run_id.split("-")[-1] if "-" in run_id else run_id[:6]
    proof_id = f"proof-{stage_name}-{run_suffix}"

    # Get current time
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Create proof token
    token = ProofToken(
        proof_id=proof_id,
        run_id=run_id,
        suite_id=suite_id,
        stage_id=stage.value,
        session_id="alphaswarm-test-session",
        command=command,
        duration_ms=0,  # Will be filled by caller or from stage_data
        transcript_path=str(transcript_path),
        transcript_hash=transcript_hash,
        nonce=nonce,
        timestamp=timestamp,
        tool_versions=ToolVersions(),
        config_hash="",
        graph_schema_version="1.3.0",
        stage_data=stage_data or {},
        nonce_verified=nonce_found,
    )

    # Write proof token
    proof_path = output_dir / f"proof-{stage_name}.json"
    with open(proof_path, "w") as f:
        json.dump(token.to_dict(), f, indent=2)

    logger.info(f"Wrote proof token: {proof_path}")

    # Validate
    errors = token.validate()
    is_valid = len(errors) == 0 and nonce_found

    return token, is_valid


def collect_all_proofs(
    transcripts_dir: Path,
    nonces_file: Optional[Path],
    output_dir: Path,
    run_id: str,
    suite_id: str = "full-testing",
    strict: bool = True,
) -> dict[str, tuple[ProofToken, bool]]:
    """
    Collect proof tokens for all stages from transcripts directory.

    Expects transcripts named like: graph.txt, context.txt, pattern.txt, etc.
    Maps to stages: stage.graph_build, stage.context_pack, stage.pattern_match, etc.

    Args:
        transcripts_dir: Directory containing transcript files
        nonces_file: Optional JSON file mapping stage to nonce
        output_dir: Directory for proof token files
        run_id: Run identifier
        suite_id: Suite identifier
        strict: If True, fail on missing nonces

    Returns:
        Dictionary mapping stage name to (ProofToken, is_valid) tuples
    """
    transcripts_dir = Path(transcripts_dir)
    output_dir = Path(output_dir)

    # Stage name mapping
    stage_map = {
        "graph": Stage.GRAPH_BUILD,
        "context": Stage.CONTEXT_PACK,
        "pattern": Stage.PATTERN_MATCH,
        "agents": Stage.AGENT_SPAWN,
        "debate": Stage.DEBATE,
        "report": Stage.REPORT,
    }

    # Load nonces if provided
    nonces = {}
    if nonces_file and nonces_file.exists():
        with open(nonces_file) as f:
            nonces = json.load(f)
        logger.info(f"Loaded {len(nonces)} nonces from {nonces_file}")

    results = {}

    for transcript_name, stage in stage_map.items():
        transcript_path = transcripts_dir / f"{transcript_name}.txt"

        if not transcript_path.exists():
            log_warn(f"Transcript not found: {transcript_path}")
            continue

        # Get nonce for this stage
        nonce = nonces.get(transcript_name, nonces.get(stage.value, ""))
        if not nonce:
            log_warn(f"No nonce provided for stage {transcript_name}")
            nonce = ""

        try:
            token, is_valid = collect_proof(
                stage=stage,
                transcript_path=transcript_path,
                nonce=nonce,
                output_dir=output_dir,
                run_id=run_id,
                suite_id=suite_id,
                strict=strict,
            )

            results[transcript_name] = (token, is_valid)

            if is_valid:
                log_success(f"Collected proof for {stage.value}")
            else:
                log_error(f"Invalid proof for {stage.value}")

        except Exception as e:
            log_error(f"Failed to collect proof for {stage.value}: {e}")

    return results


def validate_proofs(proofs_dir: Path) -> tuple[bool, dict[str, list[str]]]:
    """
    Validate all proof tokens in a directory.

    Enforces:
    - All required fields present
    - Nonce verified in transcript
    - Transcript hash valid
    - Temporal ordering correct

    Args:
        proofs_dir: Directory containing proof token files

    Returns:
        (all_valid, errors_by_stage)
    """
    proofs_dir = Path(proofs_dir)
    tokens = load_all_proof_tokens(proofs_dir)

    if not tokens:
        return False, {"_global": ["No proof tokens found"]}

    errors_by_stage = {}
    all_valid = True

    print("")
    print("=" * 60)
    print("  Proof Token Validation Report")
    print("=" * 60)
    print("")

    for token in tokens:
        stage_name = token.stage_id
        validation_errors = token.validate()

        # Additional checks
        additional_errors = []

        # Check nonce verification
        if not token.nonce_verified:
            additional_errors.append("Nonce not found in transcript (challenge failed)")

        # Check transcript file exists
        if token.transcript_path:
            transcript_path = Path(token.transcript_path)
            if not transcript_path.is_absolute():
                # Try relative to proofs dir
                transcript_path = proofs_dir.parent / token.transcript_path

            if transcript_path.exists():
                # Verify hash matches
                actual_hash = compute_transcript_hash(transcript_path)
                if actual_hash != token.transcript_hash:
                    additional_errors.append(
                        f"Transcript hash mismatch: expected {token.transcript_hash[:20]}..., "
                        f"got {actual_hash[:20]}..."
                    )
            else:
                additional_errors.append(f"Transcript file not found: {token.transcript_path}")

        all_errors = validation_errors + additional_errors

        if all_errors:
            all_valid = False
            errors_by_stage[stage_name] = all_errors
            log_error(f"{stage_name}: INVALID")
            for error in all_errors:
                print(f"    - {error}")
        else:
            log_success(f"{stage_name}: VALID (nonce={token.nonce})")

    print("")
    print("-" * 60)

    if all_valid:
        print(f"{Colors.GREEN}All {len(tokens)} proof tokens are VALID{Colors.NC}")
    else:
        invalid_count = len(errors_by_stage)
        valid_count = len(tokens) - invalid_count
        print(f"{Colors.RED}INVALID: {invalid_count}/{len(tokens)} proof tokens have errors{Colors.NC}")
        print(f"{Colors.GREEN}Valid: {valid_count}/{len(tokens)}{Colors.NC}")

    print("")

    # Check stage ordering
    print("Stage Order Validation:")
    expected_order = Stage.all_stages()
    actual_order = []

    for token in tokens:
        try:
            stage = Stage.from_string(token.stage_id)
            actual_order.append(stage)
        except ValueError:
            pass

    order_valid = True
    for i, stage in enumerate(actual_order):
        expected_idx = expected_order.index(stage)
        if i > 0:
            prev_stage = actual_order[i - 1]
            prev_idx = expected_order.index(prev_stage)
            if expected_idx <= prev_idx:
                order_valid = False
                log_error(f"Order violation: {stage.value} after {prev_stage.value}")

    if order_valid:
        log_success("Stage order is correct")
    else:
        all_valid = False
        errors_by_stage["_order"] = ["Stage execution order violated"]

    print("")
    return all_valid, errors_by_stage


def generate_nonces_file(output_path: Path, stages: Optional[list[str]] = None) -> dict[str, str]:
    """
    Generate a nonces file for all stages.

    Args:
        output_path: Path to write nonces JSON file
        stages: Optional list of stage names (default: all)

    Returns:
        Dictionary mapping stage name to nonce
    """
    stage_names = stages or ["graph", "context", "pattern", "agents", "debate", "report"]

    nonces = {}
    for stage in stage_names:
        nonces[stage] = generate_nonce()

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(nonces, f, indent=2)

    log_success(f"Generated nonces file: {output_path}")
    for stage, nonce in nonces.items():
        print(f"  {stage}: {nonce}")

    return nonces


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Collect proof tokens with nonce challenge enforcement",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate nonce for a stage
  %(prog)s --stage graph_build --generate-nonce

  # Generate nonces file for all stages
  %(prog)s --generate-nonces-file nonces.json

  # Collect proof for a single stage
  %(prog)s --stage graph_build --transcript transcripts/graph.txt \\
           --nonce nonce-8f3d --output .vrs/proofs --run-id run-001

  # Collect all proofs from transcripts directory
  %(prog)s --transcripts-dir transcripts/ --nonces-file nonces.json \\
           --output .vrs/proofs --run-id run-001 --collect-all

  # Validate proof tokens
  %(prog)s --proofs-dir .vrs/proofs --validate
""",
    )

    parser.add_argument(
        "--stage",
        choices=[s.name.lower() for s in Stage],
        help="Stage to collect proof for",
    )
    parser.add_argument(
        "--transcript",
        type=Path,
        help="Path to transcript file",
    )
    parser.add_argument(
        "--nonce",
        help="Nonce to verify in transcript",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output directory for proof tokens",
    )
    parser.add_argument(
        "--run-id",
        default="",
        help="Run identifier",
    )
    parser.add_argument(
        "--suite-id",
        default="full-testing",
        help="Suite identifier (default: full-testing)",
    )
    parser.add_argument(
        "--generate-nonce",
        action="store_true",
        help="Generate and print a nonce",
    )
    parser.add_argument(
        "--generate-nonces-file",
        type=Path,
        help="Generate nonces file for all stages",
    )
    parser.add_argument(
        "--transcripts-dir",
        type=Path,
        help="Directory containing transcript files",
    )
    parser.add_argument(
        "--nonces-file",
        type=Path,
        help="JSON file mapping stage to nonce",
    )
    parser.add_argument(
        "--collect-all",
        action="store_true",
        help="Collect proofs for all stages from transcripts directory",
    )
    parser.add_argument(
        "--proofs-dir",
        type=Path,
        help="Directory containing proof tokens",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate proof tokens",
    )
    parser.add_argument(
        "--no-strict",
        action="store_true",
        help="Don't fail on missing nonce (degraded mode)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Generate nonce mode
    if args.generate_nonce:
        nonce = generate_nonce()
        print(f"Generated nonce: {nonce}")
        if args.stage:
            print(f"Inject command: {inject_nonce_command(nonce)}")
        return 0

    # Generate nonces file mode
    if args.generate_nonces_file:
        generate_nonces_file(args.generate_nonces_file)
        return 0

    # Validate mode
    if args.validate:
        if not args.proofs_dir:
            log_error("--proofs-dir is required for validation mode")
            return 1
        if not args.proofs_dir.exists():
            log_error(f"Proofs directory not found: {args.proofs_dir}")
            return 1

        all_valid, _ = validate_proofs(args.proofs_dir)
        return 0 if all_valid else 1

    # Collect all mode
    if args.collect_all:
        if not args.transcripts_dir:
            log_error("--transcripts-dir is required for collect-all mode")
            return 1
        if not args.output:
            log_error("--output is required for collect-all mode")
            return 1

        run_id = args.run_id or f"run-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        results = collect_all_proofs(
            transcripts_dir=args.transcripts_dir,
            nonces_file=args.nonces_file,
            output_dir=args.output,
            run_id=run_id,
            suite_id=args.suite_id,
            strict=not args.no_strict,
        )

        # Summary
        print("")
        valid_count = sum(1 for _, is_valid in results.values() if is_valid)
        total_count = len(results)
        print(f"Collected {total_count} proof tokens ({valid_count} valid)")

        return 0 if valid_count == total_count else 1

    # Single stage collection mode
    if args.stage:
        if not args.transcript:
            log_error("--transcript is required for single stage collection")
            return 1
        if not args.output:
            log_error("--output is required for single stage collection")
            return 1

        stage = Stage[args.stage.upper()]
        run_id = args.run_id or f"run-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        nonce = args.nonce or generate_nonce()

        try:
            token, is_valid = collect_proof(
                stage=stage,
                transcript_path=args.transcript,
                nonce=nonce,
                output_dir=args.output,
                run_id=run_id,
                suite_id=args.suite_id,
                strict=not args.no_strict,
            )

            if is_valid:
                log_success(f"Proof token collected: {token.proof_id}")
            else:
                log_error(f"Proof token collected but INVALID: {token.proof_id}")
                for error in token.validation_errors:
                    print(f"  - {error}")

            return 0 if is_valid else 1

        except Exception as e:
            log_error(f"Failed to collect proof: {e}")
            return 1

    # No action specified
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
