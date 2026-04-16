#!/usr/bin/env python3
"""
Validate testing evidence packs in .vrs/testing/runs/<run_id>/.

This validator targets the testing framework evidence pack format (07.3.1.6).
It is separate from scripts/e2e/validate_evidence_pack.py (07.3.2 protocol).

Usage:
  python scripts/validate_evidence_pack.py .vrs/testing/runs/<run_id>
  python scripts/validate_evidence_pack.py .planning/testing/templates/evidence-pack-example --strict
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SESSION_LABEL_RE = re.compile(r"^vrs-demo-[a-z0-9][a-z0-9-]*-\d{8}-\d{6}$")
PANE_ID_RE = re.compile(r"^\d+:\d+\.\d+$")

SCHEMA_PATHS = {
    "manifest": Path("schemas/testing/evidence_manifest.schema.json"),
    "report": Path("schemas/testing/evidence_report.schema.json"),
    "environment": Path("schemas/testing/evidence_environment.schema.json"),
}


class ValidationResult:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)

    @property
    def valid(self) -> bool:
        return not self.errors


def load_json(path: Path, result: ValidationResult) -> dict[str, Any]:
    if not path.exists():
        result.add_error(f"Missing required file: {path}")
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        result.add_error(f"Invalid JSON in {path}: {exc}")
        return {}


def try_schema_validate(schema_path: Path, data: dict[str, Any], result: ValidationResult, label: str) -> None:
    try:
        import jsonschema  # type: ignore
    except Exception:
        result.add_warning("jsonschema not available; schema validation skipped")
        return

    if not schema_path.exists():
        result.add_error(f"Schema missing: {schema_path}")
        return

    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as exc:  # type: ignore[attr-defined]
        result.add_error(f"{label} schema validation failed: {exc.message}")
    except json.JSONDecodeError as exc:
        result.add_error(f"Invalid schema JSON {schema_path}: {exc}")


def require_fields(data: dict[str, Any], fields: list[str], result: ValidationResult, label: str) -> None:
    for field in fields:
        if field not in data:
            result.add_error(f"{label} missing required field: {field}")


def validate_session_label(session_label: str, result: ValidationResult, label: str) -> None:
    if not SESSION_LABEL_RE.match(session_label):
        result.add_error(f"{label} invalid session_label format: {session_label}")


def validate_pane_id(pane_id: str, result: ValidationResult, label: str) -> None:
    if not PANE_ID_RE.match(pane_id):
        result.add_error(f"{label} invalid pane_id format: {pane_id}")


def load_marker_registry() -> dict[str, Any]:
    try:
        import yaml  # type: ignore
    except Exception:
        return {}

    registry_path = Path(".planning/testing/MARKER-REGISTRY.yaml")
    if not registry_path.exists():
        return {}

    try:
        return yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def find_boundary_markers(registry: dict[str, Any]) -> tuple[str, str]:
    categories = registry.get("categories", {}) if isinstance(registry, dict) else {}
    boundary = categories.get("boundary", {}) if isinstance(categories, dict) else {}

    if isinstance(boundary, dict):
        canonical = boundary.get("canonical", {})
        if isinstance(canonical, dict):
            start = canonical.get("start")
            end = canonical.get("end")
            if isinstance(start, str) and isinstance(end, str):
                return start, end

        markers = boundary.get("markers", [])
        if isinstance(markers, list) and len(markers) >= 2:
            return str(markers[0]), str(markers[1])

    return "[ALPHASWARM-START]", "[ALPHASWARM-END]"


def check_marker_presence(transcript: str, markers: list[str], result: ValidationResult) -> None:
    for marker in markers:
        if marker.endswith("("):
            if marker not in transcript:
                result.add_error(f"Missing required marker prefix in transcript: {marker}")
        else:
            if marker not in transcript:
                result.add_error(f"Missing required marker in transcript: {marker}")


def validate_evidence_pack(pack_dir: Path, strict: bool = False) -> ValidationResult:
    result = ValidationResult()
    pack_dir = pack_dir.resolve()

    manifest_path = pack_dir / "manifest.json"
    report_path = pack_dir / "report.json"
    env_path = pack_dir / "environment.json"
    transcript_path = pack_dir / "transcript.txt"
    commands_path = pack_dir / "commands.log"

    manifest = load_json(manifest_path, result)
    report = load_json(report_path, result)
    environment = load_json(env_path, result)

    # Basic required fields
    require_fields(manifest, ["run_id", "workflow", "session_label", "pane_id"], result, "manifest")
    require_fields(report, ["session_label", "pane_id", "mode", "duration_ms"], result, "report")

    # Schema validation (if available)
    try_schema_validate(SCHEMA_PATHS["manifest"], manifest, result, "manifest")
    try_schema_validate(SCHEMA_PATHS["report"], report, result, "report")
    try_schema_validate(SCHEMA_PATHS["environment"], environment, result, "environment")

    # Session label/pane ID alignment
    manifest_label = manifest.get("session_label")
    report_label = report.get("session_label")
    if isinstance(manifest_label, str):
        validate_session_label(manifest_label, result, "manifest")
    if isinstance(report_label, str):
        validate_session_label(report_label, result, "report")
    if isinstance(manifest_label, str) and isinstance(report_label, str) and manifest_label != report_label:
        result.add_error("session_label mismatch between manifest.json and report.json")

    manifest_pane = manifest.get("pane_id")
    report_pane = report.get("pane_id")
    if isinstance(manifest_pane, str):
        validate_pane_id(manifest_pane, result, "manifest")
    if isinstance(report_pane, str):
        validate_pane_id(report_pane, result, "report")
    if isinstance(manifest_pane, str) and isinstance(report_pane, str) and manifest_pane != report_pane:
        result.add_error("pane_id mismatch between manifest.json and report.json")

    # Required markers present
    if isinstance(manifest.get("required_markers_present"), bool):
        if not manifest.get("required_markers_present"):
            result.add_error("manifest.required_markers_present is false")

    # Transcript checks
    if not transcript_path.exists():
        result.add_error(f"Missing transcript: {transcript_path}")
        transcript_text = ""
    else:
        transcript_text = transcript_path.read_text(encoding="utf-8", errors="replace")

    registry = load_marker_registry()
    start_marker, end_marker = find_boundary_markers(registry)

    if start_marker not in transcript_text or end_marker not in transcript_text:
        legacy_start = "[VRS-START]"
        legacy_end = "[VRS-END]"
        if legacy_start in transcript_text and legacy_end in transcript_text:
            result.add_warning("Transcript uses legacy VRS-START/VRS-END markers")
        else:
            result.add_error("Missing boundary markers in transcript")

    marker_list = manifest.get("marker_list")
    if isinstance(marker_list, list) and transcript_text:
        markers = [m for m in marker_list if isinstance(m, str)]
        check_marker_presence(transcript_text, markers, result)

    # Graph usage metrics (recommended for graph-first workflows)
    graph_first = report.get("graph_first")
    graph_usage = report.get("graph_usage")
    if isinstance(graph_first, dict) and graph_first.get("required") is True:
        if not isinstance(graph_usage, dict):
            result.add_warning("graph_usage metrics missing for graph-first workflow")

    # Proof token existence
    proof_tokens = report.get("proof_tokens")
    if isinstance(proof_tokens, list):
        for entry in proof_tokens:
            if not isinstance(entry, dict):
                continue
            token_path = entry.get("token_path")
            status = entry.get("status")
            if status == "required" and token_path:
                proof_path = pack_dir / token_path
                if not proof_path.exists():
                    result.add_error(f"Missing proof token: {token_path}")

    # Commands log
    if not commands_path.exists():
        result.add_warning("commands.log missing (recommended)")

    # Run directory alignment (skip for template packs)
    is_template_pack = ".planning/testing/templates" in str(pack_dir)
    if not is_template_pack:
        if pack_dir.name and manifest.get("run_id") and pack_dir.name != manifest.get("run_id"):
            result.add_warning("run_id does not match evidence pack directory name")
        if ".vrs/testing/runs" not in str(pack_dir):
            result.add_warning("Evidence pack not located under .vrs/testing/runs/")

    if strict and result.warnings:
        result.errors.extend([f"STRICT: {w}" for w in result.warnings])
        result.warnings = []

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate testing evidence packs")
    parser.add_argument("evidence_dir", type=Path, help="Path to evidence pack directory")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    args = parser.parse_args()

    if not args.evidence_dir.exists():
        print(f"ERROR: evidence directory not found: {args.evidence_dir}", file=sys.stderr)
        return 2

    result = validate_evidence_pack(args.evidence_dir, strict=args.strict)

    if result.valid:
        print("EVIDENCE PACK VALIDATION: PASS")
    else:
        print("EVIDENCE PACK VALIDATION: FAIL")

    if result.errors:
        print("Errors:")
        for err in result.errors:
            print(f"  - {err}")

    if result.warnings:
        print("Warnings:")
        for warn in result.warnings:
            print(f"  - {warn}")

    return 0 if result.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
