"""
Subagent Catalog Loader

Loads and validates the canonical subagent catalog for VRS agents.

Usage:
    from alphaswarm_sol.agents.catalog import list_subagents, get_subagent

    # List all agents
    agents = list_subagents()

    # Get specific agent
    attacker = get_subagent("vrs-attacker")
    print(attacker.role)  # "attacker"
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import yaml


@dataclass
class OutputContract:
    """Output contract specification for agent responses."""
    format: str  # "json", "structured", etc.
    schema_ref: Optional[str] = None  # Path to JSON schema file
    required_fields: List[str] = field(default_factory=list)


@dataclass
class EvidenceRequirements:
    """Evidence-first and graph-first requirements."""
    must_link_code: bool = False
    min_evidence_items: int = 0
    cite_graph_nodes: bool = False
    graph_first: bool = False
    require_behavioral_signature: bool = False


@dataclass
class AgentLocation:
    """File locations for shipped and dev versions."""
    shipped: Optional[str] = None
    dev: Optional[str] = None


@dataclass
class SubagentEntry:
    """Catalog entry for a VRS agent."""
    id: str
    name: str
    role: str
    model_tier: str
    purpose: str
    output_contract: OutputContract
    allowed_tools: List[str]
    default_context: str
    evidence_requirements: EvidenceRequirements
    location: AgentLocation
    category: str = "investigation"  # investigation, tool_integration, orchestration, support, discovery


# Cache for loaded catalog
_catalog_cache: Optional[Dict[str, SubagentEntry]] = None


def _get_catalog_path() -> Path:
    """Get path to catalog.yaml file."""
    # Catalog is in same directory as this module
    return Path(__file__).parent / "catalog.yaml"


def _load_catalog_raw() -> dict:
    """Load raw catalog YAML."""
    catalog_path = _get_catalog_path()

    if not catalog_path.exists():
        raise FileNotFoundError(
            f"Subagent catalog not found at {catalog_path}. "
            "Run from project root or verify installation."
        )

    with open(catalog_path, "r") as f:
        return yaml.safe_load(f)


def _parse_output_contract(data: dict) -> OutputContract:
    """Parse output contract from catalog entry."""
    return OutputContract(
        format=data.get("format", "structured"),
        schema_ref=data.get("schema_ref"),
        required_fields=data.get("required_fields", [])
    )


def _parse_evidence_requirements(data: dict) -> EvidenceRequirements:
    """Parse evidence requirements from catalog entry."""
    return EvidenceRequirements(
        must_link_code=data.get("must_link_code", False),
        min_evidence_items=data.get("min_evidence_items", 0),
        cite_graph_nodes=data.get("cite_graph_nodes", False),
        graph_first=data.get("graph_first", False),
        require_behavioral_signature=data.get("require_behavioral_signature", False)
    )


def _parse_location(data: dict) -> AgentLocation:
    """Parse location from catalog entry."""
    return AgentLocation(
        shipped=data.get("shipped"),
        dev=data.get("dev")
    )


def _load_catalog() -> Dict[str, SubagentEntry]:
    """Load and parse catalog into SubagentEntry objects."""
    global _catalog_cache

    if _catalog_cache is not None:
        return _catalog_cache

    raw = _load_catalog_raw()
    agents_data = raw.get("agents", [])

    catalog = {}
    for agent_data in agents_data:
        agent_id = agent_data["id"]

        entry = SubagentEntry(
            id=agent_id,
            name=agent_data["name"],
            role=agent_data["role"],
            model_tier=agent_data["model_tier"],
            purpose=agent_data["purpose"],
            output_contract=_parse_output_contract(agent_data.get("output_contract", {})),
            allowed_tools=agent_data.get("allowed_tools", []),
            default_context=agent_data.get("default_context", "fork"),
            evidence_requirements=_parse_evidence_requirements(
                agent_data.get("evidence_requirements", {})
            ),
            location=_parse_location(agent_data.get("location", {})),
            category=agent_data.get("category", "investigation"),
        )

        catalog[agent_id] = entry

    _catalog_cache = catalog
    return catalog


def list_subagents() -> List[SubagentEntry]:
    """
    List all agents in the catalog.

    Returns:
        List of SubagentEntry objects, sorted by ID.

    Example:
        >>> agents = list_subagents()
        >>> print(f"Found {len(agents)} agents")
        >>> for agent in agents:
        ...     print(f"{agent.id}: {agent.role} ({agent.model_tier})")
    """
    catalog = _load_catalog()
    return sorted(catalog.values(), key=lambda a: a.id)


def get_subagent(agent_id: str) -> Optional[SubagentEntry]:
    """
    Get a specific agent by ID.

    Args:
        agent_id: Agent identifier (e.g., "vrs-attacker")

    Returns:
        SubagentEntry if found, None otherwise.

    Example:
        >>> attacker = get_subagent("vrs-attacker")
        >>> if attacker:
        ...     print(f"Role: {attacker.role}")
        ...     print(f"Model: {attacker.model_tier}")
        ...     print(f"Graph-first: {attacker.evidence_requirements.graph_first}")
    """
    catalog = _load_catalog()
    return catalog.get(agent_id)


def filter_by_role(role: str) -> List[SubagentEntry]:
    """
    Filter agents by role.

    Args:
        role: Role name (e.g., "attacker", "verifier", "triage")

    Returns:
        List of agents with matching role.

    Example:
        >>> verifiers = filter_by_role("verifier")
        >>> print([v.id for v in verifiers])
        ['vrs-verifier', 'vrs-pattern-verifier']
    """
    return [agent for agent in list_subagents() if agent.role == role]


def filter_by_model_tier(tier: str) -> List[SubagentEntry]:
    """
    Filter agents by model tier.

    Args:
        tier: Model tier (e.g., "opus", "sonnet", "haiku")

    Returns:
        List of agents with matching model tier.

    Example:
        >>> opus_agents = filter_by_model_tier("opus")
        >>> print([a.id for a in opus_agents])
        ['vrs-attacker', 'vrs-verifier', 'vrs-test-conductor', 'vrs-gap-finder']
    """
    return [agent for agent in list_subagents() if agent.model_tier == tier]


def filter_shipped_only() -> List[SubagentEntry]:
    """
    Get only agents that are shipped to end users.

    Returns:
        List of agents with non-null shipped location.

    Example:
        >>> shipped = filter_shipped_only()
        >>> print(f"{len(shipped)} shipped agents")
    """
    return [agent for agent in list_subagents() if agent.location.shipped is not None]


def filter_dev_only() -> List[SubagentEntry]:
    """
    Get only development-only agents.

    Returns:
        List of agents with null shipped location.

    Example:
        >>> dev_only = filter_dev_only()
        >>> print([a.id for a in dev_only])
        ['skill-auditor', 'cost-governor', 'gsd-context-researcher']
    """
    return [agent for agent in list_subagents() if agent.location.shipped is None]


def validate_catalog() -> List[str]:
    """
    Validate catalog entries for completeness and correctness.

    Returns:
        List of validation issues (empty if valid).

    Example:
        >>> issues = validate_catalog()
        >>> if issues:
        ...     print("Validation failed:")
        ...     for issue in issues:
        ...         print(f"  - {issue}")
        ... else:
        ...     print("Catalog is valid")
    """
    issues = []

    try:
        catalog = _load_catalog()
    except Exception as e:
        return [f"Failed to load catalog: {e}"]

    # Valid roles (from skill schema v2)
    valid_roles = {
        "attacker", "defender", "verifier", "secure-reviewer",
        "auditor", "researcher", "triage", "orchestrator",
        "architect", "curator", "tester", "adversarial"
    }

    # Valid model tiers
    valid_tiers = {"haiku", "sonnet", "opus", "adaptive"}

    # Valid context modes
    valid_contexts = {"fork", "inline"}

    for agent_id, agent in catalog.items():
        # Check required fields are non-empty
        if not agent.name:
            issues.append(f"{agent_id}: name is empty")

        if not agent.role:
            issues.append(f"{agent_id}: role is empty")
        elif agent.role not in valid_roles:
            issues.append(f"{agent_id}: invalid role '{agent.role}'")

        if not agent.model_tier:
            issues.append(f"{agent_id}: model_tier is empty")
        elif agent.model_tier not in valid_tiers:
            issues.append(f"{agent_id}: invalid model_tier '{agent.model_tier}'")

        if not agent.purpose:
            issues.append(f"{agent_id}: purpose is empty")

        if agent.default_context not in valid_contexts:
            issues.append(f"{agent_id}: invalid default_context '{agent.default_context}'")

        # Check output contract
        if not agent.output_contract.format:
            issues.append(f"{agent_id}: output_contract.format is empty")

        # Check that schema_ref exists if specified
        if agent.output_contract.schema_ref:
            schema_path = Path(agent.output_contract.schema_ref)
            # Try relative to project root
            if not schema_path.exists():
                # Try relative to catalog file
                catalog_dir = _get_catalog_path().parent.parent.parent
                alt_path = catalog_dir / schema_path
                if not alt_path.exists():
                    issues.append(
                        f"{agent_id}: schema_ref '{agent.output_contract.schema_ref}' "
                        f"not found"
                    )

        # Check that at least one location exists
        if not agent.location.shipped and not agent.location.dev:
            issues.append(f"{agent_id}: no location specified (shipped or dev)")

        # Verify location files exist (if absolute or relative to project)
        for loc_type, loc_path in [
            ("shipped", agent.location.shipped),
            ("dev", agent.location.dev)
        ]:
            if loc_path:
                path = Path(loc_path)
                if not path.exists():
                    # Try relative to project root
                    catalog_dir = _get_catalog_path().parent.parent.parent
                    alt_path = catalog_dir / path
                    if not alt_path.exists():
                        issues.append(
                            f"{agent_id}: {loc_type} location '{loc_path}' not found"
                        )

    return issues


def get_catalog_stats() -> dict:
    """
    Get catalog statistics.

    Returns:
        Dictionary with counts by role, model tier, shipped/dev status.

    Example:
        >>> stats = get_catalog_stats()
        >>> print(f"Total: {stats['total']}")
        >>> print(f"Opus agents: {stats['by_model_tier']['opus']}")
    """
    agents = list_subagents()

    # Count by role
    by_role = {}
    for agent in agents:
        by_role[agent.role] = by_role.get(agent.role, 0) + 1

    # Count by model tier
    by_tier = {}
    for agent in agents:
        by_tier[agent.model_tier] = by_tier.get(agent.model_tier, 0) + 1

    # Count shipped vs dev
    shipped = len(filter_shipped_only())
    dev_only = len(filter_dev_only())

    return {
        "total": len(agents),
        "shipped": shipped,
        "dev_only": dev_only,
        "by_role": by_role,
        "by_model_tier": by_tier
    }


def clear_cache():
    """Clear the catalog cache (useful for testing)."""
    global _catalog_cache
    _catalog_cache = None


# CLI entry point for testing
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "validate":
        # Validate catalog
        issues = validate_catalog()
        if issues:
            print("Catalog validation FAILED:")
            for issue in issues:
                print(f"  - {issue}")
            sys.exit(1)
        else:
            print("Catalog validation PASSED")
            stats = get_catalog_stats()
            print(f"\nCatalog statistics:")
            print(f"  Total agents: {stats['total']}")
            print(f"  Shipped: {stats['shipped']}")
            print(f"  Dev-only: {stats['dev_only']}")
            print(f"\n  By model tier:")
            for tier, count in sorted(stats['by_model_tier'].items()):
                print(f"    {tier}: {count}")
            sys.exit(0)

    # Default: list all agents
    print("VRS Subagent Catalog\n")
    for agent in list_subagents():
        shipped_marker = "✓" if agent.location.shipped else "✗"
        print(f"[{shipped_marker}] {agent.id:30s} {agent.role:15s} {agent.model_tier:10s} - {agent.purpose[:60]}")

    print(f"\nTotal: {len(list_subagents())} agents")
    print(f"Shipped: {len(filter_shipped_only())} | Dev-only: {len(filter_dev_only())}")
