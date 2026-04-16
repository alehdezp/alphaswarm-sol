#!/usr/bin/env python3
"""
Proof Token Validator for Execution Evidence Protocol.

Validates proof tokens according to 07.3.2-PROOF-TOKEN-SPEC.md:
- Nonce presence and echo in transcript
- Hash validity (graph/context/pattern/agents/debate/report)
- Temporal ordering (stage ordering)
- Cross-references to graph nodes

Exit codes:
  0 - All proof tokens valid
  1 - Validation errors found
  2 - Invalid arguments or I/O error

Usage:
    python validate_proof_tokens.py <proofs_dir> [--strict] [--verbose]
    python validate_proof_tokens.py .vrs/validation/runs/run-001/proofs/
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# Add the package to path if running standalone
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from alphaswarm_sol.testing.proof_tokens import (
    ProofToken,
    Stage,
    PROOF_SCHEMA_VERSION,
    load_proof_token,
    load_all_proof_tokens,
)

logger = logging.getLogger(__name__)


# =============================================================================
# VALIDATION ERROR TYPES
# =============================================================================


@dataclass
class ValidationError:
    """A single validation error."""

    proof_id: str
    stage_id: str
    error_type: str
    message: str
    severity: str = "error"  # "error" | "warning"

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary."""
        return {
            "proof_id": self.proof_id,
            "stage_id": self.stage_id,
            "error_type": self.error_type,
            "message": self.message,
            "severity": self.severity,
        }


@dataclass
class ValidationResult:
    """Result of validating proof tokens."""

    valid: bool
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationError] = field(default_factory=list)
    tokens_checked: int = 0
    stages_covered: list[str] = field(default_factory=list)
    hash_chain_valid: bool = True
    temporal_order_valid: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "valid": self.valid,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
            "tokens_checked": self.tokens_checked,
            "stages_covered": self.stages_covered,
            "hash_chain_valid": self.hash_chain_valid,
            "temporal_order_valid": self.temporal_order_valid,
        }


# =============================================================================
# REQUIRED FIELDS BY STAGE
# =============================================================================

# Common required fields for all proof tokens
COMMON_REQUIRED_FIELDS = [
    "proof_id",
    "run_id",
    "suite_id",
    "stage_id",
    "session_id",
    "command",
    "duration_ms",
    "transcript_path",
    "transcript_hash",
    "nonce",
    "timestamp",
    "tool_versions",
    "config_hash",
    "graph_schema_version",
    "proof_schema_version",
]

# Stage-specific required fields
STAGE_REQUIRED_FIELDS = {
    "stage.graph_build": ["graph_hash", "node_count", "edge_count", "graph_builder_version"],
    "stage.context_pack": ["context_hash", "context_sources"],
    "stage.pattern_match": ["pattern_pack_version", "pattern_match_count"],
    "stage.agent_spawn": ["agent_id", "agent_role", "vql_queries", "graph_nodes_queried"],
    "stage.debate": ["finding_id", "attacker_claim_id", "defender_claim_id", "verifier_verdict_id"],
    "stage.report": ["report_path", "report_hash"],
}

# Expected stage order
EXPECTED_STAGE_ORDER = [
    "stage.graph_build",
    "stage.context_pack",
    "stage.pattern_match",
    "stage.agent_spawn",
    "stage.debate",
    "stage.report",
]


# =============================================================================
# PROOF TOKEN VALIDATOR
# =============================================================================


class ProofTokenValidator:
    """
    Validates proof tokens according to 07.3.2-PROOF-TOKEN-SPEC.md.

    Validates:
    - Structure: All required fields present and non-empty
    - Hashes: Transcript hash matches actual transcript content
    - Nonce: Nonce echoed in transcript
    - Temporal: Stages in correct order by timestamp
    - Cross-references: Graph node references exist (if graph provided)
    """

    def __init__(
        self,
        proofs_dir: Path,
        transcripts_dir: Optional[Path] = None,
        graph_path: Optional[Path] = None,
        strict: bool = False,
    ):
        """
        Initialize the validator.

        Args:
            proofs_dir: Directory containing proof token JSON files
            transcripts_dir: Directory containing transcript files (for hash verification)
            graph_path: Path to graph file (for cross-reference verification)
            strict: If True, treat warnings as errors
        """
        self.proofs_dir = Path(proofs_dir)
        self.transcripts_dir = transcripts_dir
        self.graph_path = graph_path
        self.strict = strict

        self.errors: list[ValidationError] = []
        self.warnings: list[ValidationError] = []

        # Cache for loaded data
        self._graph_nodes: Optional[set[str]] = None

    def _add_error(
        self,
        proof_id: str,
        stage_id: str,
        error_type: str,
        message: str,
    ) -> None:
        """Add a validation error."""
        self.errors.append(
            ValidationError(
                proof_id=proof_id,
                stage_id=stage_id,
                error_type=error_type,
                message=message,
                severity="error",
            )
        )

    def _add_warning(
        self,
        proof_id: str,
        stage_id: str,
        error_type: str,
        message: str,
    ) -> None:
        """Add a validation warning."""
        self.warnings.append(
            ValidationError(
                proof_id=proof_id,
                stage_id=stage_id,
                error_type=error_type,
                message=message,
                severity="warning",
            )
        )

    def _load_graph_nodes(self) -> set[str]:
        """Load graph node IDs for cross-reference validation."""
        if self._graph_nodes is not None:
            return self._graph_nodes

        self._graph_nodes = set()

        if not self.graph_path or not self.graph_path.exists():
            return self._graph_nodes

        try:
            with open(self.graph_path) as f:
                graph_data = json.load(f)

            # Extract node IDs from graph
            if "nodes" in graph_data:
                for node in graph_data["nodes"]:
                    if "id" in node:
                        self._graph_nodes.add(node["id"])

            logger.debug(f"Loaded {len(self._graph_nodes)} graph nodes")
        except Exception as e:
            logger.warning(f"Failed to load graph: {e}")

        return self._graph_nodes

    def validate_structure(self, token: ProofToken) -> list[ValidationError]:
        """
        Validate proof token structure.

        Checks:
        - All common required fields present and non-empty
        - All stage-specific required fields present
        - Hash format correct (sha256:...)
        - Duration positive
        """
        errors = []
        proof_id = token.proof_id or "unknown"
        stage_id = token.stage_id or "unknown"

        # Check common required fields
        token_dict = token.to_dict()
        for field_name in COMMON_REQUIRED_FIELDS:
            if field_name == "tool_versions":
                # Check tool_versions is dict with at least one entry
                tool_versions = token_dict.get("tool_versions", {})
                if not isinstance(tool_versions, dict) or not tool_versions:
                    self._add_warning(
                        proof_id, stage_id, "missing_field",
                        f"tool_versions is empty or invalid"
                    )
            elif field_name == "duration_ms":
                duration = token_dict.get("duration_ms", 0)
                if duration <= 0:
                    self._add_error(
                        proof_id, stage_id, "invalid_duration",
                        f"duration_ms must be positive, got {duration}"
                    )
            else:
                value = token_dict.get(field_name)
                if not value:
                    self._add_error(
                        proof_id, stage_id, "missing_field",
                        f"Required field '{field_name}' is missing or empty"
                    )

        # Check stage-specific required fields
        if stage_id in STAGE_REQUIRED_FIELDS:
            stage_data = token.stage_data or {}
            for field_name in STAGE_REQUIRED_FIELDS[stage_id]:
                if field_name not in stage_data and field_name not in token_dict:
                    self._add_warning(
                        proof_id, stage_id, "missing_stage_field",
                        f"Stage-specific field '{field_name}' is missing"
                    )

        # Check hash format
        transcript_hash = token.transcript_hash
        if transcript_hash and not transcript_hash.startswith("sha256:"):
            self._add_error(
                proof_id, stage_id, "invalid_hash_format",
                f"transcript_hash must start with 'sha256:', got '{transcript_hash[:20]}...'"
            )

        # Check stage-specific hashes
        if stage_id == "stage.graph_build":
            graph_hash = token.stage_data.get("graph_hash", "")
            if graph_hash and not graph_hash.startswith("sha256:"):
                self._add_error(
                    proof_id, stage_id, "invalid_hash_format",
                    f"graph_hash must start with 'sha256:'"
                )

        return errors

    def validate_hash(self, token: ProofToken) -> bool:
        """
        Validate transcript hash matches actual transcript content.

        Returns True if hash is valid.
        """
        proof_id = token.proof_id
        stage_id = token.stage_id

        if not self.transcripts_dir:
            logger.debug("No transcripts_dir provided, skipping hash validation")
            return True

        transcript_path_str = token.transcript_path
        if not transcript_path_str:
            self._add_error(
                proof_id, stage_id, "missing_transcript_path",
                "transcript_path is empty"
            )
            return False

        # Try to find transcript
        transcript_path = Path(transcript_path_str)
        if not transcript_path.is_absolute():
            # Try relative to transcripts_dir
            transcript_path = self.transcripts_dir / transcript_path.name

        if not transcript_path.exists():
            # Try extracting stage name
            stage_name = stage_id.split(".")[-1] if stage_id else "unknown"
            transcript_path = self.transcripts_dir / f"{stage_name}.txt"

        if not transcript_path.exists():
            self._add_error(
                proof_id, stage_id, "transcript_not_found",
                f"Transcript file not found: {transcript_path_str}"
            )
            return False

        # Compute hash and compare
        try:
            content = transcript_path.read_text(encoding="utf-8", errors="replace")
            actual_hash = f"sha256:{hashlib.sha256(content.encode()).hexdigest()}"

            if actual_hash != token.transcript_hash:
                self._add_error(
                    proof_id, stage_id, "transcript_hash_mismatch",
                    f"Transcript hash mismatch: expected {token.transcript_hash[:30]}..., "
                    f"got {actual_hash[:30]}..."
                )
                return False
        except Exception as e:
            self._add_error(
                proof_id, stage_id, "hash_computation_error",
                f"Failed to compute transcript hash: {e}"
            )
            return False

        return True

    def validate_nonce(self, token: ProofToken) -> bool:
        """
        Validate nonce is echoed in transcript.

        Returns True if nonce is found.
        """
        proof_id = token.proof_id
        stage_id = token.stage_id

        if not token.nonce:
            self._add_error(
                proof_id, stage_id, "missing_nonce",
                "Nonce is missing from proof token"
            )
            return False

        if not token.nonce_verified:
            self._add_error(
                proof_id, stage_id, "nonce_not_verified",
                f"Nonce '{token.nonce}' was not found in transcript"
            )
            return False

        return True

    def validate_temporal_order(self, tokens: list[ProofToken]) -> bool:
        """
        Validate stages are in correct temporal order.

        Returns True if order is valid.
        """
        if len(tokens) < 2:
            return True

        # Parse timestamps and sort
        timestamped_tokens = []
        for token in tokens:
            try:
                ts = datetime.fromisoformat(token.timestamp.replace("Z", "+00:00"))
                timestamped_tokens.append((ts, token))
            except Exception as e:
                self._add_error(
                    token.proof_id, token.stage_id, "invalid_timestamp",
                    f"Cannot parse timestamp '{token.timestamp}': {e}"
                )
                return False

        # Sort by timestamp
        timestamped_tokens.sort(key=lambda x: x[0])

        # Check stage order
        stage_order = [t[1].stage_id for t in timestamped_tokens]

        # Build expected order based on what stages are present
        expected_order = [s for s in EXPECTED_STAGE_ORDER if s in stage_order]

        # Check if actual order matches expected
        actual_order = [s for s in stage_order if s in EXPECTED_STAGE_ORDER]

        if actual_order != expected_order:
            self._add_error(
                "all", "temporal_order", "stage_order_violation",
                f"Stages out of order: expected {expected_order}, got {actual_order}"
            )
            return False

        return True

    def validate_cross_references(self, token: ProofToken) -> bool:
        """
        Validate cross-references to graph nodes exist.

        Returns True if all references are valid.
        """
        if not self.graph_path:
            return True

        proof_id = token.proof_id
        stage_id = token.stage_id
        graph_nodes = self._load_graph_nodes()

        if not graph_nodes:
            # No graph loaded, skip validation
            return True

        # Check agent_spawn proof for graph_nodes_queried
        if stage_id == "stage.agent_spawn":
            queried_nodes = token.stage_data.get("graph_nodes_queried", [])
            if isinstance(queried_nodes, list):
                for node_id in queried_nodes:
                    if node_id not in graph_nodes:
                        self._add_warning(
                            proof_id, stage_id, "invalid_node_reference",
                            f"Graph node '{node_id}' not found in graph"
                        )

        return True

    def validate(self) -> ValidationResult:
        """
        Run all validations on proof tokens.

        Returns:
            ValidationResult with all errors and warnings
        """
        self.errors = []
        self.warnings = []

        # Load all proof tokens
        try:
            tokens = load_all_proof_tokens(self.proofs_dir)
        except Exception as e:
            self._add_error("all", "load", "load_error", f"Failed to load proof tokens: {e}")
            return ValidationResult(
                valid=False,
                errors=self.errors,
                warnings=self.warnings,
                tokens_checked=0,
            )

        if not tokens:
            self._add_error("all", "load", "no_tokens", "No proof tokens found")
            return ValidationResult(
                valid=False,
                errors=self.errors,
                warnings=self.warnings,
                tokens_checked=0,
            )

        # Validate each token
        for token in tokens:
            self.validate_structure(token)
            self.validate_hash(token)
            self.validate_nonce(token)
            self.validate_cross_references(token)

        # Validate temporal order across all tokens
        temporal_valid = self.validate_temporal_order(tokens)

        # Determine hash chain validity
        hash_chain_valid = all(
            e.error_type != "transcript_hash_mismatch"
            for e in self.errors
        )

        # In strict mode, warnings become errors
        if self.strict:
            self.errors.extend(self.warnings)
            self.warnings = []

        # Determine overall validity
        valid = len(self.errors) == 0

        return ValidationResult(
            valid=valid,
            errors=self.errors,
            warnings=self.warnings,
            tokens_checked=len(tokens),
            stages_covered=[t.stage_id for t in tokens],
            hash_chain_valid=hash_chain_valid,
            temporal_order_valid=temporal_valid,
        )


# =============================================================================
# PUBLIC API
# =============================================================================


def validate_proof_tokens(
    proofs_dir: Path,
    transcripts_dir: Optional[Path] = None,
    graph_path: Optional[Path] = None,
    strict: bool = False,
) -> ValidationResult:
    """
    Validate proof tokens in a directory.

    Args:
        proofs_dir: Directory containing proof token JSON files
        transcripts_dir: Directory containing transcript files
        graph_path: Path to graph file for cross-reference validation
        strict: If True, treat warnings as errors

    Returns:
        ValidationResult with validation status and errors
    """
    validator = ProofTokenValidator(
        proofs_dir=proofs_dir,
        transcripts_dir=transcripts_dir,
        graph_path=graph_path,
        strict=strict,
    )
    return validator.validate()


def validate_single_proof_token(
    token_path: Path,
    transcript_path: Optional[Path] = None,
) -> tuple[bool, list[str]]:
    """
    Validate a single proof token.

    Args:
        token_path: Path to proof token JSON file
        transcript_path: Optional path to transcript file

    Returns:
        (is_valid, list of error messages)
    """
    errors = []

    try:
        token = load_proof_token(token_path)
    except Exception as e:
        return False, [f"Failed to load proof token: {e}"]

    # Validate structure
    token_errors = token.validate()
    errors.extend(token_errors)

    # Validate transcript hash if provided
    if transcript_path and transcript_path.exists():
        content = transcript_path.read_text(encoding="utf-8", errors="replace")
        actual_hash = f"sha256:{hashlib.sha256(content.encode()).hexdigest()}"
        if actual_hash != token.transcript_hash:
            errors.append(f"Transcript hash mismatch")

        # Verify nonce in transcript
        if token.nonce and token.nonce not in content:
            errors.append(f"Nonce not found in transcript")

    return len(errors) == 0, errors


# =============================================================================
# CLI
# =============================================================================


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Validate proof tokens according to 07.3.2-PROOF-TOKEN-SPEC.md",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s .vrs/validation/runs/run-001/proofs/
    %(prog)s proofs/ --transcripts transcripts/ --strict
    %(prog)s proofs/ --graph graph.json --verbose
        """,
    )
    parser.add_argument(
        "proofs_dir",
        type=Path,
        help="Directory containing proof token JSON files",
    )
    parser.add_argument(
        "--transcripts",
        type=Path,
        dest="transcripts_dir",
        help="Directory containing transcript files",
    )
    parser.add_argument(
        "--graph",
        type=Path,
        dest="graph_path",
        help="Path to graph file for cross-reference validation",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    # Validate inputs
    if not args.proofs_dir.exists():
        print(f"Error: Proofs directory not found: {args.proofs_dir}", file=sys.stderr)
        return 2

    # Run validation
    result = validate_proof_tokens(
        proofs_dir=args.proofs_dir,
        transcripts_dir=args.transcripts_dir,
        graph_path=args.graph_path,
        strict=args.strict,
    )

    # Output results
    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(f"\n{'=' * 60}")
        print(f"PROOF TOKEN VALIDATION RESULT")
        print(f"{'=' * 60}")
        print(f"Valid: {result.valid}")
        print(f"Tokens checked: {result.tokens_checked}")
        print(f"Stages covered: {', '.join(result.stages_covered)}")
        print(f"Hash chain valid: {result.hash_chain_valid}")
        print(f"Temporal order valid: {result.temporal_order_valid}")

        if result.errors:
            print(f"\nErrors ({len(result.errors)}):")
            for error in result.errors:
                print(f"  [{error.stage_id}] {error.error_type}: {error.message}")

        if result.warnings:
            print(f"\nWarnings ({len(result.warnings)}):")
            for warning in result.warnings:
                print(f"  [{warning.stage_id}] {warning.error_type}: {warning.message}")

        print(f"{'=' * 60}")

    return 0 if result.valid else 1


if __name__ == "__main__":
    sys.exit(main())
