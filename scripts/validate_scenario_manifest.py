#!/usr/bin/env python3
"""
Validate .planning/testing/scenarios/SCENARIO-MANIFEST.yaml against schema + policy.

Usage:
  python scripts/validate_scenario_manifest.py
  python scripts/validate_scenario_manifest.py --manifest path/to/SCENARIO-MANIFEST.yaml
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

DEFAULT_MANIFEST = Path(".planning/testing/scenarios/SCENARIO-MANIFEST.yaml")
SCHEMA_PATH = Path("schemas/testing/scenario_manifest.schema.json")


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


def load_yaml(path: Path, result: ValidationResult) -> list[dict[str, Any]]:
    try:
        import yaml  # type: ignore
    except Exception:
        result.add_error("PyYAML not installed; cannot load manifest")
        return []

    if not path.exists():
        result.add_error(f"Manifest not found: {path}")
        return []

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            result.add_error("Manifest must be a list of scenarios")
            return []
        return data
    except Exception as exc:
        result.add_error(f"Failed to parse YAML: {exc}")
        return []


def try_schema_validate(data: list[dict[str, Any]], result: ValidationResult) -> None:
    try:
        import jsonschema  # type: ignore
    except Exception:
        result.add_warning("jsonschema not available; schema validation skipped")
        return

    if not SCHEMA_PATH.exists():
        result.add_error(f"Schema missing: {SCHEMA_PATH}")
        return

    try:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as exc:  # type: ignore[attr-defined]
        result.add_error(f"Schema validation failed: {exc.message}")
    except json.JSONDecodeError as exc:
        result.add_error(f"Invalid schema JSON {SCHEMA_PATH}: {exc}")


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


def marker_in_registry(marker: str, registry: dict[str, Any]) -> bool:
    categories = registry.get("categories", {}) if isinstance(registry, dict) else {}
    marker_list: list[str] = []
    for entry in categories.values():
        if isinstance(entry, dict):
            markers = entry.get("markers")
            if isinstance(markers, list):
                marker_list.extend([m for m in markers if isinstance(m, str)])

    for reg in marker_list:
        if marker == reg:
            return True
        if reg.endswith("(") and marker.startswith(reg):
            return True
    return False


def validate_entries(data: list[dict[str, Any]], result: ValidationResult) -> None:
    ids = set()
    registry = load_marker_registry()

    for idx, entry in enumerate(data):
        prefix = f"scenario[{idx}]"

        scenario_id = entry.get("id")
        if not scenario_id or not isinstance(scenario_id, str):
            result.add_error(f"{prefix} missing id")
        else:
            if scenario_id in ids:
                result.add_error(f"Duplicate scenario id: {scenario_id}")
            ids.add(scenario_id)

        status = entry.get("status")
        if status == "blocked":
            reason = entry.get("blocked_reason")
            if not reason or (isinstance(reason, str) and reason.strip().upper() == "TBD"):
                result.add_error(f"{scenario_id}: blocked status requires concrete blocked_reason")

        if entry.get("requires_ground_truth") is True:
            gt = entry.get("ground_truth_ref")
            if not gt or (isinstance(gt, str) and gt.strip().upper() == "TBD"):
                if status == "blocked":
                    result.add_warning(f"{scenario_id}: requires_ground_truth true but ground_truth_ref missing (blocked)")
                else:
                    result.add_error(f"{scenario_id}: requires_ground_truth true but ground_truth_ref missing")

        workflow_ref = entry.get("workflow_ref")
        if isinstance(workflow_ref, str) and workflow_ref:
            if not Path(workflow_ref).exists():
                result.add_warning(f"{scenario_id}: workflow_ref not found: {workflow_ref}")

        doc = entry.get("doc")
        if isinstance(doc, str) and doc:
            if not Path(doc).exists():
                result.add_warning(f"{scenario_id}: doc not found: {doc}")

        artifacts = entry.get("artifacts")
        if entry.get("evidence_pack_required") is True and isinstance(artifacts, list):
            required = {"manifest.json", "transcript.txt", "report.json", "environment.json"}
            if not required.issubset(set(artifacts)):
                result.add_warning(
                    f"{scenario_id}: artifacts missing required evidence files: {sorted(required - set(artifacts))}"
                )

        min_markers = entry.get("min_markers")
        if isinstance(min_markers, list) and min_markers:
            for marker in min_markers:
                if isinstance(marker, str) and registry and not marker_in_registry(marker, registry):
                    result.add_warning(f"{scenario_id}: min_marker not in registry: {marker}")

        # Economic model enforcement (warn if missing)
        behavior_model_ref = entry.get("behavior_model_ref")
        context_ref = entry.get("context_ref")
        if any(
            isinstance(val, str) and "economic" in val.lower()
            for val in [doc, context_ref]
        ):
            if not behavior_model_ref:
                result.add_warning(f"{scenario_id}: economic scenario missing behavior_model_ref")

        # Graph scenarios should declare VQL bundle when applicable
        if entry.get("tier") == "graph":
            vql_bundle = entry.get("vql_bundle")
            if not vql_bundle:
                result.add_warning(f"{scenario_id}: graph scenario missing vql_bundle")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate scenario manifest")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST, help="Manifest path")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    args = parser.parse_args()

    result = ValidationResult()
    data = load_yaml(args.manifest, result)
    if data:
        try_schema_validate(data, result)
        validate_entries(data, result)

    if args.strict and result.warnings:
        result.errors.extend([f"STRICT: {w}" for w in result.warnings])
        result.warnings = []

    if result.valid:
        print("SCENARIO MANIFEST VALIDATION: PASS")
    else:
        print("SCENARIO MANIFEST VALIDATION: FAIL")

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
