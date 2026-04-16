#!/usr/bin/env python3
"""
Evidence Pack Validator for Execution Evidence Protocol.

Validates evidence packs according to 07.3.2-EVIDENCE-PACK-SCHEMA.md:
- Transcripts + hashes present and valid
- Proof tokens for all stages
- Debug artifacts per skill/agent
- Tool outputs or explicit skip reasons

Exit codes:
  0 - Evidence pack valid
  1 - Validation errors found
  2 - Invalid arguments or I/O error

Usage:
    python validate_evidence_pack.py <evidence_dir> [--strict] [--verbose]
    python validate_evidence_pack.py .vrs/validation/runs/run-001/
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

# Add the package to path if running standalone
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from alphaswarm_sol.testing.evidence_pack import (
    EvidencePackManifest,
    EVIDENCE_PACK_SCHEMA_VERSION,
    MIN_DURATION_MS,
    load_evidence_pack,
)
from alphaswarm_sol.testing.proof_tokens import Stage

logger = logging.getLogger(__name__)


# =============================================================================
# VALIDATION ERROR TYPES
# =============================================================================


@dataclass
class PackValidationError:
    """A single validation error."""

    category: str  # "manifest" | "transcript" | "proof" | "debug" | "tool" | "ground_truth"
    error_type: str
    message: str
    severity: str = "error"  # "error" | "warning"
    path: str = ""

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary."""
        return {
            "category": self.category,
            "error_type": self.error_type,
            "message": self.message,
            "severity": self.severity,
            "path": self.path,
        }


@dataclass
class PackValidationResult:
    """Result of validating an evidence pack."""

    valid: bool
    status: str  # "valid" | "degraded" | "invalid"
    errors: list[PackValidationError] = field(default_factory=list)
    warnings: list[PackValidationError] = field(default_factory=list)

    # Component status
    manifest_valid: bool = True
    transcripts_valid: bool = True
    proofs_valid: bool = True
    debug_artifacts_valid: bool = True
    tool_outputs_valid: bool = True
    ground_truth_valid: bool = True

    # Metrics
    transcript_count: int = 0
    proof_count: int = 0
    debug_artifact_count: int = 0
    tool_output_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "valid": self.valid,
            "status": self.status,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
            "manifest_valid": self.manifest_valid,
            "transcripts_valid": self.transcripts_valid,
            "proofs_valid": self.proofs_valid,
            "debug_artifacts_valid": self.debug_artifacts_valid,
            "tool_outputs_valid": self.tool_outputs_valid,
            "ground_truth_valid": self.ground_truth_valid,
            "transcript_count": self.transcript_count,
            "proof_count": self.proof_count,
            "debug_artifact_count": self.debug_artifact_count,
            "tool_output_count": self.tool_output_count,
        }


# =============================================================================
# REQUIRED COMPONENTS
# =============================================================================

# Required transcript stages
REQUIRED_TRANSCRIPT_STAGES = [
    "graph",
    "context",
    "pattern",
    "agents",
    "debate",
    "report",
]

# Required proof tokens
REQUIRED_PROOF_STAGES = [
    "stage.graph_build",
    "stage.context_pack",
    "stage.pattern_match",
    "stage.agent_spawn",
    "stage.debate",
    "stage.report",
]

# Required manifest fields
REQUIRED_MANIFEST_FIELDS = [
    "run_id",
    "suite_id",
    "command",
    "duration_ms",
    "session_id",
    "schema_version",
    "transcript_hashes",
    "proof_tokens",
]


# =============================================================================
# EVIDENCE PACK VALIDATOR
# =============================================================================


class EvidencePackValidator:
    """
    Validates evidence packs according to 07.3.2-EVIDENCE-PACK-SCHEMA.md.

    Validates:
    - Manifest: All required fields present, schema version valid
    - Transcripts: All required stages present, hashes match
    - Proof tokens: All stages have proof tokens
    - Debug artifacts: Present for required skills/agents
    - Tool outputs: Present or have explicit skip reason
    - Ground truth: References exist and valid
    """

    def __init__(
        self,
        evidence_dir: Path,
        strict: bool = False,
        check_hash_integrity: bool = True,
    ):
        """
        Initialize the validator.

        Args:
            evidence_dir: Directory containing the evidence pack
            strict: If True, treat warnings as errors
            check_hash_integrity: If True, verify file hashes
        """
        self.evidence_dir = Path(evidence_dir)
        self.strict = strict
        self.check_hash_integrity = check_hash_integrity

        self.errors: list[PackValidationError] = []
        self.warnings: list[PackValidationError] = []

        self._manifest: Optional[EvidencePackManifest] = None

    def _add_error(
        self,
        category: str,
        error_type: str,
        message: str,
        path: str = "",
    ) -> None:
        """Add a validation error."""
        self.errors.append(
            PackValidationError(
                category=category,
                error_type=error_type,
                message=message,
                severity="error",
                path=path,
            )
        )

    def _add_warning(
        self,
        category: str,
        error_type: str,
        message: str,
        path: str = "",
    ) -> None:
        """Add a validation warning."""
        self.warnings.append(
            PackValidationError(
                category=category,
                error_type=error_type,
                message=message,
                severity="warning",
                path=path,
            )
        )

    def _compute_hash(self, filepath: Path) -> str:
        """Compute SHA-256 hash of a file."""
        content = filepath.read_bytes()
        return f"sha256:{hashlib.sha256(content).hexdigest()}"

    def validate_manifest(self) -> bool:
        """
        Validate the manifest.json file.

        Returns True if manifest is valid.
        """
        manifest_path = self.evidence_dir / "manifest.json"

        if not manifest_path.exists():
            self._add_error(
                "manifest", "missing",
                "manifest.json not found",
                str(manifest_path),
            )
            return False

        try:
            self._manifest = load_evidence_pack(self.evidence_dir)
        except Exception as e:
            self._add_error(
                "manifest", "parse_error",
                f"Failed to parse manifest: {e}",
                str(manifest_path),
            )
            return False

        manifest = self._manifest

        # Check required fields
        manifest_dict = manifest.to_dict()
        for field_name in REQUIRED_MANIFEST_FIELDS:
            if field_name not in manifest_dict or not manifest_dict[field_name]:
                self._add_error(
                    "manifest", "missing_field",
                    f"Required field '{field_name}' is missing or empty",
                )

        # Check schema version
        if manifest.schema_version != EVIDENCE_PACK_SCHEMA_VERSION:
            self._add_warning(
                "manifest", "schema_version_mismatch",
                f"Schema version {manifest.schema_version} != expected {EVIDENCE_PACK_SCHEMA_VERSION}",
            )

        # Check duration
        if manifest.duration_ms <= MIN_DURATION_MS:
            self._add_error(
                "manifest", "invalid_duration",
                f"duration_ms ({manifest.duration_ms}) <= minimum ({MIN_DURATION_MS})",
            )

        return len([e for e in self.errors if e.category == "manifest"]) == 0

    def validate_transcripts(self) -> tuple[bool, int]:
        """
        Validate transcript files.

        Returns (is_valid, transcript_count).
        """
        if not self._manifest:
            return False, 0

        manifest = self._manifest
        count = 0
        valid = True

        # Check all required stages have transcripts
        for stage in REQUIRED_TRANSCRIPT_STAGES:
            if stage not in manifest.transcript_hashes:
                self._add_error(
                    "transcript", "missing_stage",
                    f"No transcript for required stage: {stage}",
                )
                valid = False

        # Validate each transcript
        for stage, expected_hash in manifest.transcript_hashes.items():
            transcript_path = self.evidence_dir / "transcripts" / f"{stage}.txt"

            if not transcript_path.exists():
                self._add_error(
                    "transcript", "file_missing",
                    f"Transcript file not found: {stage}",
                    str(transcript_path),
                )
                valid = False
                continue

            count += 1

            # Check file not empty
            if transcript_path.stat().st_size == 0:
                self._add_error(
                    "transcript", "empty",
                    f"Transcript file is empty: {stage}",
                    str(transcript_path),
                )
                valid = False
                continue

            # Verify hash if enabled
            if self.check_hash_integrity and expected_hash:
                actual_hash = self._compute_hash(transcript_path)
                if actual_hash != expected_hash:
                    self._add_error(
                        "transcript", "hash_mismatch",
                        f"Transcript hash mismatch for {stage}",
                        str(transcript_path),
                    )
                    valid = False

        return valid, count

    def validate_proof_tokens(self) -> tuple[bool, int]:
        """
        Validate proof token files.

        Returns (is_valid, proof_count).
        """
        if not self._manifest:
            return False, 0

        manifest = self._manifest
        count = 0
        valid = True

        # Check proof tokens exist
        if not manifest.proof_tokens:
            self._add_error(
                "proof", "no_tokens",
                "No proof tokens in manifest",
            )
            return False, 0

        # Build map of stage -> proof path
        stage_proofs = {}
        for proof_path in manifest.proof_tokens:
            # Extract stage from filename (e.g., "proofs/proof-graph_build.json" -> "stage.graph_build")
            filename = Path(proof_path).stem
            if filename.startswith("proof-"):
                stage_name = filename[6:]  # Remove "proof-" prefix
                stage_id = f"stage.{stage_name}"
                stage_proofs[stage_id] = proof_path

        # Check all required stages have proof tokens
        for stage_id in REQUIRED_PROOF_STAGES:
            if stage_id not in stage_proofs:
                self._add_warning(
                    "proof", "missing_stage",
                    f"No proof token for stage: {stage_id}",
                )

        # Validate each proof token file exists
        for proof_path in manifest.proof_tokens:
            full_path = self.evidence_dir / proof_path

            if not full_path.exists():
                self._add_error(
                    "proof", "file_missing",
                    f"Proof token file not found: {proof_path}",
                    str(full_path),
                )
                valid = False
                continue

            count += 1

            # Check file not empty
            if full_path.stat().st_size == 0:
                self._add_error(
                    "proof", "empty",
                    f"Proof token file is empty: {proof_path}",
                    str(full_path),
                )
                valid = False
                continue

            # Validate JSON structure
            try:
                with open(full_path) as f:
                    data = json.load(f)

                # Check required fields exist
                if "proof_id" not in data or "stage_id" not in data:
                    self._add_error(
                        "proof", "invalid_structure",
                        f"Proof token missing proof_id or stage_id: {proof_path}",
                        str(full_path),
                    )
                    valid = False

            except json.JSONDecodeError as e:
                self._add_error(
                    "proof", "invalid_json",
                    f"Invalid JSON in proof token: {e}",
                    str(full_path),
                )
                valid = False

        return valid, count

    def validate_debug_artifacts(self) -> tuple[bool, int]:
        """
        Validate debug artifacts.

        Returns (is_valid, artifact_count).
        """
        if not self._manifest:
            return False, 0

        manifest = self._manifest
        count = 0
        valid = True

        # Debug artifacts are optional but if referenced, must exist
        if not manifest.debug_artifacts:
            # No debug artifacts is a warning, not error
            self._add_warning(
                "debug", "no_artifacts",
                "No debug artifacts in manifest",
            )
            return True, 0

        for skill_or_agent, artifact_path in manifest.debug_artifacts.items():
            full_path = self.evidence_dir / artifact_path

            if not full_path.exists():
                self._add_error(
                    "debug", "file_missing",
                    f"Debug artifact not found for {skill_or_agent}",
                    str(full_path),
                )
                valid = False
                continue

            count += 1

        return valid, count

    def validate_tool_outputs(self) -> tuple[bool, int]:
        """
        Validate tool outputs.

        Returns (is_valid, output_count).
        """
        if not self._manifest:
            return False, 0

        manifest = self._manifest
        count = 0
        valid = True

        # Tool outputs are optional but if referenced, must exist or have skip reason
        if not manifest.tool_outputs:
            self._add_warning(
                "tool", "no_outputs",
                "No tool outputs in manifest",
            )
            return True, 0

        for tool, output in manifest.tool_outputs.items():
            if isinstance(output, dict):
                # Check for skip reason
                if "skip_reason" in output:
                    # Valid: tool was skipped with reason
                    count += 1
                    continue
                else:
                    self._add_error(
                        "tool", "invalid_entry",
                        f"Tool output for {tool} has no path or skip_reason",
                    )
                    valid = False
            elif isinstance(output, str):
                if not output:
                    self._add_error(
                        "tool", "empty_path",
                        f"Tool output path for {tool} is empty",
                    )
                    valid = False
                    continue

                full_path = self.evidence_dir / output

                if not full_path.exists():
                    self._add_error(
                        "tool", "file_missing",
                        f"Tool output file not found for {tool}",
                        str(full_path),
                    )
                    valid = False
                    continue

                count += 1

                # Check file not empty
                if full_path.stat().st_size == 0:
                    self._add_error(
                        "tool", "empty",
                        f"Tool output file is empty for {tool}",
                        str(full_path),
                    )
                    valid = False

        return valid, count

    def validate_ground_truth(self) -> bool:
        """
        Validate ground truth references.

        Returns True if valid.
        """
        if not self._manifest:
            return False

        manifest = self._manifest
        valid = True

        if not manifest.ground_truth_refs:
            self._add_warning(
                "ground_truth", "no_refs",
                "No ground truth references in manifest",
            )
            return True

        full_path = self.evidence_dir / manifest.ground_truth_refs

        if not full_path.exists():
            self._add_error(
                "ground_truth", "file_missing",
                "Ground truth manifest not found",
                str(full_path),
            )
            return False

        # Check file not empty
        if full_path.stat().st_size == 0:
            self._add_error(
                "ground_truth", "empty",
                "Ground truth manifest is empty",
                str(full_path),
            )
            valid = False

        return valid

    def validate_hash_manifest(self) -> bool:
        """
        Validate hash manifest.

        Returns True if valid.
        """
        if not self._manifest:
            return False

        manifest = self._manifest

        if not manifest.hash_manifest:
            self._add_warning(
                "manifest", "no_hash_manifest",
                "No hash_manifest path in manifest",
            )
            return True

        full_path = self.evidence_dir / manifest.hash_manifest

        if not full_path.exists():
            self._add_error(
                "manifest", "hash_manifest_missing",
                "Hash manifest file not found",
                str(full_path),
            )
            return False

        return True

    def validate(self) -> PackValidationResult:
        """
        Run all validations.

        Returns:
            PackValidationResult with all errors and warnings
        """
        self.errors = []
        self.warnings = []

        # Run validations
        manifest_valid = self.validate_manifest()
        transcripts_valid, transcript_count = self.validate_transcripts()
        proofs_valid, proof_count = self.validate_proof_tokens()
        debug_valid, debug_count = self.validate_debug_artifacts()
        tools_valid, tool_count = self.validate_tool_outputs()
        ground_truth_valid = self.validate_ground_truth()
        hash_manifest_valid = self.validate_hash_manifest()

        # In strict mode, warnings become errors
        if self.strict:
            self.errors.extend(self.warnings)
            self.warnings = []

        # Determine overall validity
        has_errors = len(self.errors) > 0
        has_warnings = len(self.warnings) > 0

        if has_errors:
            status = "invalid"
            valid = False
        elif has_warnings:
            status = "degraded"
            valid = True
        else:
            status = "valid"
            valid = True

        return PackValidationResult(
            valid=valid,
            status=status,
            errors=self.errors,
            warnings=self.warnings,
            manifest_valid=manifest_valid,
            transcripts_valid=transcripts_valid,
            proofs_valid=proofs_valid,
            debug_artifacts_valid=debug_valid,
            tool_outputs_valid=tools_valid,
            ground_truth_valid=ground_truth_valid,
            transcript_count=transcript_count,
            proof_count=proof_count,
            debug_artifact_count=debug_count,
            tool_output_count=tool_count,
        )


# =============================================================================
# PUBLIC API
# =============================================================================


def validate_pack(
    evidence_dir: Path,
    strict: bool = False,
    check_hash_integrity: bool = True,
) -> PackValidationResult:
    """
    Validate an evidence pack.

    Args:
        evidence_dir: Directory containing the evidence pack
        strict: If True, treat warnings as errors
        check_hash_integrity: If True, verify file hashes

    Returns:
        PackValidationResult with validation status and errors
    """
    validator = EvidencePackValidator(
        evidence_dir=evidence_dir,
        strict=strict,
        check_hash_integrity=check_hash_integrity,
    )
    return validator.validate()


def validate_pack_completeness(evidence_dir: Path) -> tuple[bool, list[str]]:
    """
    Quick check for evidence pack completeness.

    Args:
        evidence_dir: Directory containing the evidence pack

    Returns:
        (is_complete, list of missing items)
    """
    evidence_dir = Path(evidence_dir)
    missing = []

    # Check manifest
    if not (evidence_dir / "manifest.json").exists():
        missing.append("manifest.json")

    # Check directories
    required_dirs = ["proofs", "transcripts"]
    for dir_name in required_dirs:
        if not (evidence_dir / dir_name).is_dir():
            missing.append(f"{dir_name}/")

    # Check for at least one proof token
    proofs_dir = evidence_dir / "proofs"
    if proofs_dir.exists():
        proof_files = list(proofs_dir.glob("proof-*.json"))
        if not proof_files:
            missing.append("proof tokens")

    # Check for at least one transcript
    transcripts_dir = evidence_dir / "transcripts"
    if transcripts_dir.exists():
        transcript_files = list(transcripts_dir.glob("*.txt"))
        if not transcript_files:
            missing.append("transcripts")

    return len(missing) == 0, missing


# =============================================================================
# CLI
# =============================================================================


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Validate evidence packs according to 07.3.2-EVIDENCE-PACK-SCHEMA.md",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s .vrs/validation/runs/run-001/
    %(prog)s evidence/ --strict
    %(prog)s evidence/ --verbose --json
        """,
    )
    parser.add_argument(
        "evidence_dir",
        type=Path,
        help="Directory containing the evidence pack",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors",
    )
    parser.add_argument(
        "--no-hash-check",
        action="store_true",
        help="Skip hash integrity verification",
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
    if not args.evidence_dir.exists():
        print(f"Error: Evidence directory not found: {args.evidence_dir}", file=sys.stderr)
        return 2

    # Run validation
    result = validate_pack(
        evidence_dir=args.evidence_dir,
        strict=args.strict,
        check_hash_integrity=not args.no_hash_check,
    )

    # Output results
    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(f"\n{'=' * 60}")
        print(f"EVIDENCE PACK VALIDATION RESULT")
        print(f"{'=' * 60}")
        print(f"Status: {result.status.upper()}")
        print(f"Valid: {result.valid}")
        print()
        print("Component Status:")
        print(f"  Manifest:        {'PASS' if result.manifest_valid else 'FAIL'}")
        print(f"  Transcripts:     {'PASS' if result.transcripts_valid else 'FAIL'} ({result.transcript_count} files)")
        print(f"  Proof Tokens:    {'PASS' if result.proofs_valid else 'FAIL'} ({result.proof_count} files)")
        print(f"  Debug Artifacts: {'PASS' if result.debug_artifacts_valid else 'FAIL'} ({result.debug_artifact_count} files)")
        print(f"  Tool Outputs:    {'PASS' if result.tool_outputs_valid else 'FAIL'} ({result.tool_output_count} files)")
        print(f"  Ground Truth:    {'PASS' if result.ground_truth_valid else 'FAIL'}")

        if result.errors:
            print(f"\nErrors ({len(result.errors)}):")
            for error in result.errors:
                path_info = f" [{error.path}]" if error.path else ""
                print(f"  [{error.category}] {error.error_type}: {error.message}{path_info}")

        if result.warnings:
            print(f"\nWarnings ({len(result.warnings)}):")
            for warning in result.warnings:
                path_info = f" [{warning.path}]" if warning.path else ""
                print(f"  [{warning.category}] {warning.error_type}: {warning.message}{path_info}")

        print(f"{'=' * 60}")

    return 0 if result.valid else 1


if __name__ == "__main__":
    sys.exit(main())
