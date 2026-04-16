"""
Knowledge Graph Persistence Layer

Handles serialization, deserialization, and versioning for all knowledge graphs:
- Domain Knowledge Graph
- Adversarial Knowledge Graph
- Cross-Graph Linker edges

Supports gzip compression and version migration.
"""

import json
import gzip
from pathlib import Path
from typing import Any, Dict, Optional, Union
from datetime import datetime
from enum import Enum
from dataclasses import asdict, is_dataclass

from .domain_kg import (
    DomainKnowledgeGraph,
    Specification,
    Invariant,
    DeFiPrimitive,
    SpecType,
)
from .adversarial_kg import (
    AdversarialKnowledgeGraph,
    AttackPattern,
    ExploitRecord,
    AttackCategory,
    Severity,
)
from .linker import (
    CrossGraphLinker,
    CrossGraphEdge,
    CrossGraphRelation,
)


# Schema version for forward compatibility
SCHEMA_VERSION = "3.5.0"


class GraphType(Enum):
    """Types of knowledge graphs that can be persisted."""
    DOMAIN = "domain"
    ADVERSARIAL = "adversarial"
    CROSS_GRAPH = "cross_graph"


# Custom JSON encoder for dataclasses and enums
class KGJSONEncoder(json.JSONEncoder):
    """JSON encoder that handles dataclasses, enums, and sets."""

    def default(self, obj):
        if is_dataclass(obj):
            return asdict(obj)
        elif isinstance(obj, Enum):
            return obj.value
        elif isinstance(obj, set):
            return list(obj)
        return super().default(obj)


def _serialize_dataclass(obj: Any) -> Dict[str, Any]:
    """
    Recursively serialize a dataclass to dict.

    Args:
        obj: Dataclass instance

    Returns:
        Dict representation with enums converted to values
    """
    if is_dataclass(obj):
        result = {}
        for field_name, field_value in asdict(obj).items():
            if isinstance(field_value, Enum):
                result[field_name] = field_value.value
            elif isinstance(field_value, list):
                result[field_name] = [
                    _serialize_dataclass(item) if is_dataclass(item) else item
                    for item in field_value
                ]
            elif isinstance(field_value, dict):
                result[field_name] = {
                    k: _serialize_dataclass(v) if is_dataclass(v) else v
                    for k, v in field_value.items()
                }
            else:
                result[field_name] = field_value
        return result
    return obj


def save_domain_kg(
    kg: DomainKnowledgeGraph,
    file_path: Union[str, Path],
    compress: bool = True,
) -> None:
    """
    Save Domain Knowledge Graph to file.

    Args:
        kg: DomainKnowledgeGraph instance
        file_path: Path to save to
        compress: Whether to gzip compress (default: True)
    """
    file_path = Path(file_path)

    # Build serializable content
    content = {
        "specifications": {
            spec_id: _serialize_dataclass(spec)
            for spec_id, spec in kg.specifications.items()
        },
        "primitives": {
            prim_id: _serialize_dataclass(prim)
            for prim_id, prim in kg.primitives.items()
        },
    }

    # Wrap with metadata
    data = {
        "schema_version": SCHEMA_VERSION,
        "graph_type": GraphType.DOMAIN.value,
        "created_at": datetime.now().isoformat(),
        "metadata": {
            "total_specifications": len(kg.specifications),
            "total_primitives": len(kg.primitives),
        },
        "content": content,
    }

    # Write to file
    json_str = json.dumps(data, indent=2, cls=KGJSONEncoder)

    if compress:
        with gzip.open(file_path, 'wt', encoding='utf-8') as f:
            f.write(json_str)
    else:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(json_str)


def load_domain_kg(file_path: Union[str, Path]) -> DomainKnowledgeGraph:
    """
    Load Domain Knowledge Graph from file.

    Args:
        file_path: Path to load from

    Returns:
        DomainKnowledgeGraph instance

    Raises:
        ValueError: If schema version incompatible
    """
    file_path = Path(file_path)

    # Read file (auto-detect gzip)
    try:
        with gzip.open(file_path, 'rt', encoding='utf-8') as f:
            data = json.load(f)
    except gzip.BadGzipFile:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

    # Check version
    version = data.get("schema_version", "0.0.0")
    if not _is_compatible_version(version):
        data = _migrate_version(data, version, SCHEMA_VERSION)

    # Deserialize content
    kg = DomainKnowledgeGraph()

    # Load specifications
    for spec_id, spec_dict in data["content"]["specifications"].items():
        # Reconstruct Invariant objects
        invariants = [
            Invariant(**inv_dict) for inv_dict in spec_dict["invariants"]
        ]

        # Reconstruct Specification
        spec = Specification(
            id=spec_dict["id"],
            spec_type=SpecType(spec_dict["spec_type"]),
            name=spec_dict["name"],
            description=spec_dict["description"],
            version=spec_dict.get("version", "1.0"),
            function_signatures=spec_dict.get("function_signatures", []),
            expected_operations=spec_dict.get("expected_operations", []),
            invariants=invariants,
            preconditions=spec_dict.get("preconditions", []),
            postconditions=spec_dict.get("postconditions", []),
            common_violations=spec_dict.get("common_violations", []),
            related_cwes=spec_dict.get("related_cwes", []),
            semantic_tags=spec_dict.get("semantic_tags", []),
            external_refs=spec_dict.get("external_refs", {}),
        )
        kg.add_specification(spec)

    # Load DeFi primitives
    for prim_id, prim_dict in data["content"].get("primitives", {}).items():
        # Reconstruct Invariant objects
        invariants = [
            Invariant(**inv_dict) for inv_dict in prim_dict["primitive_invariants"]
        ]

        # Reconstruct DeFiPrimitive
        prim = DeFiPrimitive(
            id=prim_dict["id"],
            name=prim_dict["name"],
            description=prim_dict["description"],
            entry_functions=prim_dict.get("entry_functions", []),
            callback_pattern=prim_dict.get("callback_pattern"),
            implements_specs=prim_dict.get("implements_specs", []),
            trust_assumptions=prim_dict.get("trust_assumptions", []),
            attack_surface=prim_dict.get("attack_surface", []),
            known_attack_patterns=prim_dict.get("known_attack_patterns", []),
            primitive_invariants=invariants,
        )
        kg.add_primitive(prim)

    return kg


def save_adversarial_kg(
    kg: AdversarialKnowledgeGraph,
    file_path: Union[str, Path],
    compress: bool = True,
) -> None:
    """
    Save Adversarial Knowledge Graph to file.

    Args:
        kg: AdversarialKnowledgeGraph instance
        file_path: Path to save to
        compress: Whether to gzip compress (default: True)
    """
    file_path = Path(file_path)

    # Build serializable content
    content = {
        "patterns": {
            pattern_id: _serialize_dataclass(pattern)
            for pattern_id, pattern in kg.patterns.items()
        },
        "exploits": {
            exploit_id: _serialize_dataclass(exploit)
            for exploit_id, exploit in kg.exploits.items()
        },
    }

    # Wrap with metadata
    data = {
        "schema_version": SCHEMA_VERSION,
        "graph_type": GraphType.ADVERSARIAL.value,
        "created_at": datetime.now().isoformat(),
        "metadata": {
            "total_patterns": len(kg.patterns),
            "total_exploits": len(kg.exploits),
            "unique_cwes": len(set(cwe for p in kg.patterns.values() for cwe in p.cwes)),
        },
        "content": content,
    }

    # Write to file
    json_str = json.dumps(data, indent=2, cls=KGJSONEncoder)

    if compress:
        with gzip.open(file_path, 'wt', encoding='utf-8') as f:
            f.write(json_str)
    else:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(json_str)


def load_adversarial_kg(file_path: Union[str, Path]) -> AdversarialKnowledgeGraph:
    """
    Load Adversarial Knowledge Graph from file.

    Args:
        file_path: Path to load from

    Returns:
        AdversarialKnowledgeGraph instance

    Raises:
        ValueError: If schema version incompatible
    """
    file_path = Path(file_path)

    # Read file (auto-detect gzip)
    try:
        with gzip.open(file_path, 'rt', encoding='utf-8') as f:
            data = json.load(f)
    except gzip.BadGzipFile:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

    # Check version
    version = data.get("schema_version", "0.0.0")
    if not _is_compatible_version(version):
        data = _migrate_version(data, version, SCHEMA_VERSION)

    # Deserialize content
    kg = AdversarialKnowledgeGraph()

    # Load patterns
    for pattern_id, pattern_dict in data["content"]["patterns"].items():
        # Reconstruct required_properties as set
        required_props = pattern_dict.get("required_properties", [])
        if isinstance(required_props, list):
            required_props = set(required_props)

        pattern = AttackPattern(
            id=pattern_dict["id"],
            name=pattern_dict["name"],
            category=AttackCategory(pattern_dict["category"]),
            severity=Severity(pattern_dict["severity"]),
            description=pattern_dict["description"],
            required_operations=pattern_dict["required_operations"],
            operation_sequence=pattern_dict.get("operation_sequence"),
            supporting_operations=pattern_dict.get("supporting_operations", []),
            preconditions=pattern_dict.get("preconditions", []),
            false_positive_indicators=pattern_dict.get("false_positive_indicators", []),
            violated_properties=pattern_dict.get("violated_properties", []),
            cwes=pattern_dict.get("cwes", []),
            detection_hints=pattern_dict.get("detection_hints", []),
            remediation=pattern_dict.get("remediation", ""),
            known_exploits=pattern_dict.get("known_exploits", []),
            related_patterns=pattern_dict.get("related_patterns", []),
            required_properties=required_props,
        )
        kg.add_pattern(pattern)

    # Load exploits
    for exploit_id, exploit_dict in data["content"]["exploits"].items():
        exploit = ExploitRecord(
            id=exploit_dict["id"],
            name=exploit_dict["name"],
            date=exploit_dict["date"],
            loss_usd=exploit_dict["loss_usd"],
            chain=exploit_dict["chain"],
            category=AttackCategory(exploit_dict["category"]),
            cwes=exploit_dict["cwes"],
            pattern_ids=exploit_dict["pattern_ids"],
            attack_summary=exploit_dict["attack_summary"],
            attack_steps=exploit_dict["attack_steps"],
            postmortem_url=exploit_dict.get("postmortem_url"),
            vulnerable_code_url=exploit_dict.get("vulnerable_code_url"),
            fixed_code_url=exploit_dict.get("fixed_code_url"),
            tx_hash=exploit_dict.get("tx_hash"),
        )
        kg.add_exploit(exploit)

    return kg


def save_cross_graph_edges(
    linker: CrossGraphLinker,
    file_path: Union[str, Path],
    compress: bool = True,
) -> None:
    """
    Save Cross-Graph edges to file.

    Args:
        linker: CrossGraphLinker instance
        file_path: Path to save to
        compress: Whether to gzip compress (default: True)
    """
    file_path = Path(file_path)

    # Build serializable content
    content = {
        "edges": [_serialize_dataclass(edge) for edge in linker.edges],
    }

    # Wrap with metadata
    data = {
        "schema_version": SCHEMA_VERSION,
        "graph_type": GraphType.CROSS_GRAPH.value,
        "created_at": datetime.now().isoformat(),
        "metadata": {
            "total_edges": len(linker.edges),
            "by_relation": {
                rel.value: sum(1 for e in linker.edges if e.relation == rel)
                for rel in CrossGraphRelation
            },
        },
        "content": content,
    }

    # Write to file
    json_str = json.dumps(data, indent=2, cls=KGJSONEncoder)

    if compress:
        with gzip.open(file_path, 'wt', encoding='utf-8') as f:
            f.write(json_str)
    else:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(json_str)


def load_cross_graph_edges(
    file_path: Union[str, Path],
    code_kg: Any,
    domain_kg: DomainKnowledgeGraph,
    adversarial_kg: AdversarialKnowledgeGraph,
) -> CrossGraphLinker:
    """
    Load Cross-Graph edges from file.

    Args:
        file_path: Path to load from
        code_kg: Code KG instance (VKG)
        domain_kg: Domain KG instance
        adversarial_kg: Adversarial KG instance

    Returns:
        CrossGraphLinker instance with loaded edges

    Raises:
        ValueError: If schema version incompatible
    """
    file_path = Path(file_path)

    # Read file (auto-detect gzip)
    try:
        with gzip.open(file_path, 'rt', encoding='utf-8') as f:
            data = json.load(f)
    except gzip.BadGzipFile:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

    # Check version
    version = data.get("schema_version", "0.0.0")
    if not _is_compatible_version(version):
        data = _migrate_version(data, version, SCHEMA_VERSION)

    # Create linker
    linker = CrossGraphLinker(code_kg, domain_kg, adversarial_kg)

    # Load edges
    for edge_dict in data["content"]["edges"]:
        edge = CrossGraphEdge(
            id=edge_dict["id"],
            source_graph=edge_dict["source_graph"],
            source_id=edge_dict["source_id"],
            target_graph=edge_dict["target_graph"],
            target_id=edge_dict["target_id"],
            relation=CrossGraphRelation(edge_dict["relation"]),
            confidence=edge_dict["confidence"],
            evidence=edge_dict["evidence"],
            created_by=edge_dict["created_by"],
            created_at=edge_dict["created_at"],
        )
        linker._add_edge(edge)

    return linker


def _is_compatible_version(version: str) -> bool:
    """
    Check if schema version is compatible with current version.

    Args:
        version: Version string (e.g., "3.5.0")

    Returns:
        True if compatible
    """
    # For now, only accept exact match
    # In future, implement backward compatibility
    return version == SCHEMA_VERSION


def _migrate_version(data: Dict[str, Any], from_version: str, to_version: str) -> Dict[str, Any]:
    """
    Migrate data from old schema version to new.

    Args:
        data: Original data
        from_version: Source version
        to_version: Target version

    Returns:
        Migrated data

    Raises:
        ValueError: If migration not supported
    """
    # For now, no migrations needed (first version)
    # Future: implement version-specific migrations
    raise ValueError(f"Cannot migrate from version {from_version} to {to_version}")


def get_file_stats(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Get statistics about a persisted knowledge graph file.

    Args:
        file_path: Path to KG file

    Returns:
        Dict with stats (size, type, version, etc.)
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Read metadata (don't load full content)
    try:
        with gzip.open(file_path, 'rt', encoding='utf-8') as f:
            data = json.load(f)
        compressed = True
    except gzip.BadGzipFile:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        compressed = False

    return {
        "file_path": str(file_path),
        "file_size_bytes": file_path.stat().st_size,
        "compressed": compressed,
        "schema_version": data.get("schema_version"),
        "graph_type": data.get("graph_type"),
        "created_at": data.get("created_at"),
        "metadata": data.get("metadata", {}),
    }
