"""Load and manage evaluation contracts.

Evaluation contracts define what to check per workflow. They are YAML files
validated against the evaluation_contract.schema.json schema.

CONTRACT_VERSION: 06.2
CONSUMERS: [3.1c-07, 3.1c-08, 3.1c-09, 3.1c-10, 3.1c-11]
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

# Default locations
_CONTRACTS_DIR = Path(__file__).parent / "contracts"
_TEMPLATES_DIR = _CONTRACTS_DIR / "templates"
_SCHEMA_PATH = Path(".vrs/testing/schemas/evaluation_contract.schema.json")

# Mapping from scenario workflow IDs to contract filenames.
# Scenarios use short names (e.g., "vrs-audit") while contract files
# follow the convention "skill-vrs-audit.yaml", "agent-vrs-attacker.yaml", etc.
_WORKFLOW_TO_CONTRACT: dict[str, str] = {
    "vrs-audit": "skill-vrs-audit",
    "vrs-verify": "skill-vrs-verify",
    "vrs-investigate": "skill-vrs-investigate",
    "vrs-debate": "skill-vrs-debate",
    "vrs-attacker": "agent-vrs-attacker",
    "vrs-defender": "agent-vrs-defender",
    "vrs-verifier": "agent-vrs-verifier",
    "vrs-secure-reviewer": "agent-vrs-secure-reviewer",
    "full-audit": "orchestrator-full-audit",
    "tool-slither": "skill-vrs-tool-slither",
}


def resolve_contract_id(workflow_id: str) -> str:
    """Resolve a scenario workflow ID to a contract filename stem.

    Scenarios may use short workflow names (e.g., ``"vrs-audit"``).
    Contract files use a prefixed convention (e.g., ``"skill-vrs-audit"``).
    This function maps short names to contract names, passing through
    already-qualified IDs unchanged.

    Args:
        workflow_id: Short or fully-qualified workflow identifier.

    Returns:
        Contract filename stem suitable for file lookup.
    """
    return _WORKFLOW_TO_CONTRACT.get(workflow_id, workflow_id)


def _find_schema() -> Path | None:
    """Find the evaluation contract schema file."""
    # Try relative to CWD first, then absolute
    if _SCHEMA_PATH.exists():
        return _SCHEMA_PATH
    # Try relative to project root (walk up from this file)
    candidate = Path(__file__).parents[4] / _SCHEMA_PATH
    if candidate.exists():
        return candidate
    return None


def load_contract(
    workflow_id: str, contracts_dir: Path | None = None
) -> dict[str, Any]:
    """Load an evaluation contract by workflow ID.

    Args:
        workflow_id: Contract identifier (e.g., 'agent-vrs-attacker').
        contracts_dir: Override contracts directory.

    Returns:
        Parsed contract as a dict.

    Raises:
        FileNotFoundError: If no contract found for the workflow ID.
        ValueError: If the YAML is malformed.
    """
    directory = contracts_dir or _CONTRACTS_DIR
    resolved_id = resolve_contract_id(workflow_id)
    path = directory / f"{resolved_id}.yaml"

    if not path.exists():
        extra = ""
        if resolved_id != workflow_id:
            extra = f" (resolved from '{workflow_id}')"
        raise FileNotFoundError(
            f"No evaluation contract found for '{resolved_id}'{extra} at {path}"
        )

    with open(path) as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Contract {path} is not a YAML mapping")

    return data


def list_contracts(contracts_dir: Path | None = None) -> list[str]:
    """List all available contract workflow IDs.

    Args:
        contracts_dir: Override contracts directory.

    Returns:
        Sorted list of workflow IDs (filenames without .yaml extension).
    """
    directory = contracts_dir or _CONTRACTS_DIR
    if not directory.exists():
        return []

    return sorted(
        p.stem
        for p in directory.glob("*.yaml")
        if not p.name.startswith("_")
        and p.stem != "templates"
        and p.stem != "dimension_registry"
    )


def load_template(template_name: str) -> dict[str, Any]:
    """Load a contract template.

    Args:
        template_name: Template identifier (e.g., 'investigation', 'tool').

    Returns:
        Parsed template as a dict.

    Raises:
        FileNotFoundError: If template not found.
    """
    path = _TEMPLATES_DIR / f"template-{template_name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"No template found: {path}")

    with open(path) as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Template {path} is not a YAML mapping")

    return data


def list_templates() -> list[str]:
    """List available template names.

    Returns:
        Sorted list of template names (without 'template-' prefix and .yaml suffix).
    """
    if not _TEMPLATES_DIR.exists():
        return []
    return sorted(
        p.stem.removeprefix("template-")
        for p in _TEMPLATES_DIR.glob("template-*.yaml")
    )


def generate_from_template(
    template_name: str,
    workflow_id: str,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate a contract from a template with overrides.

    Args:
        template_name: Template to base on (e.g., 'investigation').
        workflow_id: Workflow ID for the generated contract.
        overrides: Fields to override from the template.

    Returns:
        Complete contract dict with template defaults + overrides.
    """
    template = load_template(template_name)

    # Remove template metadata
    template.pop("_template", None)

    # Apply overrides
    contract = {**template, "workflow_id": workflow_id}
    if overrides:
        for key, value in overrides.items():
            if isinstance(value, list) and isinstance(contract.get(key), list):
                # Extend lists rather than replace
                contract[key] = contract[key] + value
            else:
                contract[key] = value

    return contract


def _validate_debrief_mode_compatibility(contract: dict[str, Any]) -> list[str]:
    """Reject incompatible debrief configurations (P11-ADV-4-01).

    Two forbidden combinations:
    (a) tier=="standard" + debrief: true → REJECT
    (b) run_mode=="headless" + debrief: true → REJECT
    """
    errors: list[str] = []
    ec = contract.get("evaluation_config", {})
    debrief = ec.get("debrief", False)
    if not debrief:
        return errors

    tier = contract.get("metadata", {}).get("tier", "")
    if tier == "standard":
        errors.append(
            f"Standard-tier contract '{contract.get('workflow_id', '?')}' "
            "must not have debrief: true"
        )

    run_mode = ec.get("run_mode", "")
    if run_mode == "headless":
        errors.append(
            f"Contract '{contract.get('workflow_id', '?')}' has "
            "run_mode=headless with debrief: true — incompatible"
        )

    return errors


def _validate_stub_reasoning(contract: dict[str, Any]) -> list[str]:
    """Reject stub contracts with run_reasoning: true + empty dimensions (P15-IMP-03)."""
    ec = contract.get("evaluation_config", {})
    dims = contract.get("reasoning_dimensions", [])
    if ec.get("run_reasoning") is True and not dims:
        return [
            f"Contract '{contract.get('workflow_id', '?')}' has "
            "run_reasoning: true but reasoning_dimensions is empty"
        ]
    return []


def validate_contract(contract: dict[str, Any]) -> list[str]:
    """Validate a contract against the JSON schema and semantic rules.

    Args:
        contract: Contract dict to validate.

    Returns:
        List of validation errors (empty if valid).
    """
    schema_path = _find_schema()
    if schema_path is None:
        return ["Schema file not found — cannot validate"]

    errors: list[str] = []
    try:
        import jsonschema
    except ImportError:
        return ["jsonschema package not installed"]

    try:
        with open(schema_path) as f:
            schema = json.load(f)

        jsonschema.validate(instance=contract, schema=schema)
    except jsonschema.ValidationError as exc:
        errors.append(exc.message)
    except Exception as exc:
        errors.append(str(exc))

    # Semantic validation
    errors.extend(_validate_debrief_mode_compatibility(contract))
    errors.extend(_validate_stub_reasoning(contract))

    return errors


def validate_mapping_completeness(
    contracts_dir: Path | None = None,
) -> list[str]:
    """Cross-check workflow_id against _WORKFLOW_TO_CONTRACT dict.

    Returns list of warnings for unmapped contracts.
    """
    directory = contracts_dir or _CONTRACTS_DIR
    contract_ids = set()
    for p in directory.glob("*.yaml"):
        if not p.name.startswith("_") and p.name != "dimension_registry.yaml":
            contract_ids.add(p.stem)

    mapped_ids = set(_WORKFLOW_TO_CONTRACT.values())
    gaps: list[str] = []
    for cid in sorted(contract_ids - mapped_ids):
        gaps.append(f"Contract '{cid}' has no entry in _WORKFLOW_TO_CONTRACT")
    return gaps
