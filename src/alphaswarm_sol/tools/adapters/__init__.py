"""Tool Adapters Module.

Provides adapters for converting between various static analysis tool
outputs and VKG internal format via SARIF 2.1.0 normalization.

Supported tools:
- Slither: Solidity static analyzer (Tier 0)
- Aderyn: Rust-based Solidity analyzer (Tier 1)
- Mythril: EVM bytecode analyzer - symbolic execution (Tier 1)
- Echidna: Property-based fuzzing (Tier 1)
- Foundry: Testing framework with fuzzing (Tier 1)
- Semgrep: Pattern-based analysis (Tier 2)
- Halmos: Symbolic execution and formal verification (Tier 2)

All tools normalize to SARIF 2.1.0, then convert to VKGFinding internal format.
"""

from alphaswarm_sol.tools.adapters.sarif import (
    SARIF_SCHEMA,
    SARIF_VERSION,
    SARIFAdapter,
    VKGFinding,
    sarif_to_vkg_findings,
    validate_sarif,
    vkg_findings_to_sarif,
)
from alphaswarm_sol.tools.adapters.slither_adapter import (
    SlitherAdapter,
    slither_to_sarif,
    slither_to_vkg_findings,
)
from alphaswarm_sol.tools.adapters.aderyn_adapter import (
    AderynAdapter,
    aderyn_to_sarif,
    aderyn_to_vkg_findings,
)
from alphaswarm_sol.tools.adapters.mythril_adapter import (
    MythrilAdapter,
    mythril_to_sarif,
    mythril_to_vkg_findings,
)
from alphaswarm_sol.tools.adapters.echidna_adapter import (
    EchidnaAdapter,
    echidna_to_sarif,
    echidna_json_to_sarif,
    echidna_to_vkg_findings,
    echidna_json_to_vkg_findings,
)
from alphaswarm_sol.tools.adapters.foundry_adapter import (
    FoundryAdapter,
    foundry_to_sarif,
    foundry_to_vkg_findings,
)
from alphaswarm_sol.tools.adapters.semgrep_adapter import (
    SemgrepAdapter,
    semgrep_to_sarif,
    semgrep_to_vkg_findings,
)
from alphaswarm_sol.tools.adapters.halmos_adapter import (
    HalmosAdapter,
    halmos_to_sarif,
    halmos_text_to_sarif,
    halmos_to_vkg_findings,
    halmos_text_to_vkg_findings,
)


__all__ = [
    # SARIF adapter
    "SARIF_VERSION",
    "SARIF_SCHEMA",
    "SARIFAdapter",
    "VKGFinding",
    "sarif_to_vkg_findings",
    "vkg_findings_to_sarif",
    "validate_sarif",
    # Slither adapter (Tier 0)
    "SlitherAdapter",
    "slither_to_sarif",
    "slither_to_vkg_findings",
    # Aderyn adapter (Tier 1)
    "AderynAdapter",
    "aderyn_to_sarif",
    "aderyn_to_vkg_findings",
    # Mythril adapter (Tier 1)
    "MythrilAdapter",
    "mythril_to_sarif",
    "mythril_to_vkg_findings",
    # Echidna adapter (Tier 1)
    "EchidnaAdapter",
    "echidna_to_sarif",
    "echidna_json_to_sarif",
    "echidna_to_vkg_findings",
    "echidna_json_to_vkg_findings",
    # Foundry adapter (Tier 1)
    "FoundryAdapter",
    "foundry_to_sarif",
    "foundry_to_vkg_findings",
    # Semgrep adapter (Tier 2)
    "SemgrepAdapter",
    "semgrep_to_sarif",
    "semgrep_to_vkg_findings",
    # Halmos adapter (Tier 2)
    "HalmosAdapter",
    "halmos_to_sarif",
    "halmos_text_to_sarif",
    "halmos_to_vkg_findings",
    "halmos_text_to_vkg_findings",
]
