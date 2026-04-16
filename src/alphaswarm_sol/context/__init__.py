"""Protocol Context Pack module.

The Protocol Context Pack captures protocol-level context (roles, assumptions,
invariants, off-chain inputs) with confidence tracking for LLM-driven
vulnerability detection.

This module provides:
- Foundation types with confidence tracking
- Schema for complete protocol context packs
- Storage for YAML-based persistence
- Builder for context pack generation from code + docs
- Parser submodule for code analysis and doc parsing

Usage:
    from alphaswarm_sol.context import (
        # Builder (main entry point)
        ContextPackBuilder,
        BuildConfig,
        BuildResult,
        # Schema
        ProtocolContextPack,
        ContextPackStorage,
        # Types
        Confidence,
        Role,
        Assumption,
        Invariant,
        OffchainInput,
        ValueFlow,
        AcceptedRisk,
    )

    # Build a context pack from code analysis
    from alphaswarm_sol.kg.schema import KnowledgeGraph
    from pathlib import Path

    graph = build_kg("contracts/")
    builder = ContextPackBuilder(
        graph=graph,
        project_path=Path("contracts/"),
        config=BuildConfig(
            protocol_name="MyProtocol",
            protocol_type="lending",
            include_code_analysis=True,
            include_doc_parsing=True,
        )
    )
    result = builder.build()

    # Access the pack
    pack = result.pack
    print(f"Roles: {[r.name for r in pack.roles]}")
    print(f"Assumptions: {len(pack.assumptions)}")
    print(f"Conflicts: {len(result.conflicts)}")

    # Save to storage
    storage = ContextPackStorage(Path(".vrs/context"))
    storage.save(pack)

    # Load from storage
    loaded = storage.load("MyProtocol")

    # Incremental update when code changes
    updated_result = builder.update(loaded, changed_files=["Token.sol"])
"""

from .types import (
    Confidence,
    ExpectationProvenance,
    CausalEdgeType,
    ConfidenceField,
    Role,
    Assumption,
    Invariant,
    OffchainInput,
    ValueFlow,
    AcceptedRisk,
    CausalEdge,
    SourceAttribution,
)
from .schema import ProtocolContextPack
from .storage import ContextPackStorage
from .builder import (
    ContextPackBuilder,
    BuildConfig,
    BuildResult,
    Conflict,
    SourceInfo,
    ChangelogEntry,
)
from .integrations import (
    EvidenceContextExtension,
    EvidenceContextProvider,
    EvidenceAssembler,
    BeadContext,
    BeadContextProvider,
)
from .retrieval_packer import (
    RetrievalPacker,
    PackedEvidenceBundle,
    EvidenceItem,
    pack_evidence_items,
    unpack_evidence_bundle,
)
from .dossier import (
    DossierSource,
    DossierRecord,
    DiffBeacon,
    DossierBuilder,
)
from .linker import (
    LinkSource,
    LinkType,
    LinkRecord,
    CausalChainLink,
    ContextLinker,
)
from .passports import (
    DependencyType,
    LifecycleStage,
    CrossProtocolDependency,
    ContractPassport,
    PassportBuilder,
)
from .invariant_registry import (
    InvariantSource,
    InvariantCategory,
    InvariantRecord,
    InvariantDiscrepancy,
    InvariantRegistry,
)

__all__ = [
    # Enums
    "Confidence",
    "ExpectationProvenance",
    "CausalEdgeType",
    # Foundation types
    "ConfidenceField",
    "Role",
    "Assumption",
    "Invariant",
    "OffchainInput",
    "ValueFlow",
    "AcceptedRisk",
    "CausalEdge",
    "SourceAttribution",
    # Schema
    "ProtocolContextPack",
    # Storage
    "ContextPackStorage",
    # Builder
    "ContextPackBuilder",
    "BuildConfig",
    "BuildResult",
    "Conflict",
    "SourceInfo",
    "ChangelogEntry",
    # Integrations
    "EvidenceContextExtension",
    "EvidenceContextProvider",
    "EvidenceAssembler",
    "BeadContext",
    "BeadContextProvider",
    # Retrieval Packer (07.1.3-03)
    "RetrievalPacker",
    "PackedEvidenceBundle",
    "EvidenceItem",
    "pack_evidence_items",
    "unpack_evidence_bundle",
    # Dossier (05.11)
    "DossierSource",
    "DossierRecord",
    "DiffBeacon",
    "DossierBuilder",
    # Linker (05.11-02)
    "LinkSource",
    "LinkType",
    "LinkRecord",
    "CausalChainLink",
    "ContextLinker",
    # Passports (05.11-02)
    "DependencyType",
    "LifecycleStage",
    "CrossProtocolDependency",
    "ContractPassport",
    "PassportBuilder",
    # Invariant Registry (05.11-02)
    "InvariantSource",
    "InvariantCategory",
    "InvariantRecord",
    "InvariantDiscrepancy",
    "InvariantRegistry",
]
