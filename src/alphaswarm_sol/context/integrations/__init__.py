"""Integration layer for protocol context packs.

Connects context packs to:
- Evidence packets (finding context)
- Vulnerability beads (investigation context)

Per PHILOSOPHY.md Evidence Packet Contract:
- protocol_context: [string] - Relevant protocol context sections
- assumptions: [string] - Assumptions that apply to this finding
- offchain_inputs: [string] - Off-chain dependencies

Per 03-CONTEXT.md:
- 'Violated assumption' is a first-class finding type
- Accepted risks auto-filtered from findings
- Beads inherit relevant context pack sections automatically
- Smart filtering: agents request only relevant properties

Usage:
    from alphaswarm_sol.context.integrations import (
        # Evidence packet integration
        EvidenceContextExtension,
        EvidenceContextProvider,
        # Bead integration
        BeadContext,
        BeadContextProvider,
    )

    # Evidence packet context
    pack = ProtocolContextPack.from_dict(yaml_data)
    evidence_provider = EvidenceContextProvider(pack)
    ext = evidence_provider.get_context_for_finding(
        function_name="withdraw",
        vulnerability_class="reentrancy",
        semantic_ops=["TRANSFERS_VALUE_OUT"],
    )

    # Bead context inheritance
    bead_provider = BeadContextProvider(pack)
    bead_ctx = bead_provider.get_context_for_bead(
        vulnerability_class="reentrancy",
        function_name="withdraw",
        semantic_ops=["TRANSFERS_VALUE_OUT"],
        max_tokens=2000,
    )
"""

from .evidence import (
    EvidenceContextExtension,
    EvidenceContextProvider,
    EvidenceAssembler,
    OPERATION_TO_ASSUMPTION_CATEGORIES,
    VULN_CLASS_TO_ASSUMPTION_CATEGORIES,
    VULN_CLASS_TO_CAPABILITIES,
)
from .bead import (
    BeadContext,
    BeadContextProvider,
)

__all__ = [
    # Evidence packet integration
    "EvidenceContextExtension",
    "EvidenceContextProvider",
    "EvidenceAssembler",
    # Bead integration
    "BeadContext",
    "BeadContextProvider",
    # Mapping exports for customization
    "OPERATION_TO_ASSUMPTION_CATEGORIES",
    "VULN_CLASS_TO_ASSUMPTION_CATEGORIES",
    "VULN_CLASS_TO_CAPABILITIES",
]
