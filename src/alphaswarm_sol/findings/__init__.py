"""
Findings Management Module

Provides persistent storage and management of security findings
for AI agent workflows and session handoff.

Philosophy Alignment:
- Evidence-first: Every finding includes behavioral evidence
- Persistent state: Findings survive session restarts
- LLM-friendly: Structured output for AI consumption
"""

from alphaswarm_sol.findings.model import (
    Finding,
    FindingStatus,
    FindingSeverity,
    FindingConfidence,
    FindingTier,
    FINDING_SCHEMA_VERSION,
    Evidence,
    EvidenceRef,
    Location,
)
from alphaswarm_sol.findings.store import FindingsStore
from alphaswarm_sol.findings.taxonomy import (
    TaxonomyMapping,
    get_taxonomy,
    get_swc,
    get_cwe,
    enrich_finding_with_taxonomy,
)
from alphaswarm_sol.findings.verification import (
    VerificationMethod,
    VerificationStep,
    VerificationChecklist,
    generate_checklist,
)

__all__ = [
    # Core finding types
    "Finding",
    "FindingStatus",
    "FindingSeverity",
    "FindingConfidence",
    "FindingTier",
    "FINDING_SCHEMA_VERSION",
    "Evidence",
    "EvidenceRef",
    "Location",
    "FindingsStore",
    # Taxonomy mapping (Task 3.16)
    "TaxonomyMapping",
    "get_taxonomy",
    "get_swc",
    "get_cwe",
    "enrich_finding_with_taxonomy",
    # Verification checklist (Task 3.15)
    "VerificationMethod",
    "VerificationStep",
    "VerificationChecklist",
    "generate_checklist",
]
