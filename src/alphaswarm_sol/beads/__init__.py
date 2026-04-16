"""Beads system - rich context packages for vulnerability investigation.

The Beads system provides comprehensive context packages that enable
LLM-driven vulnerability investigation with high accuracy. Each "bead"
contains:

1. The raw finding from pattern matching
2. Relevant code snippets with full context
3. Investigation steps tailored to the vulnerability type
4. Historical exploit references for similar patterns
5. Structured verdict tracking

Foundation Types (Task 6.0):
- Severity: Vulnerability severity levels
- BeadStatus: Status of a bead during investigation
- VerdictType: Type of verdict on a finding
- CodeSnippet: Code with metadata
- InvestigationStep: Single investigation step
- ExploitReference: Real-world exploit reference
- Verdict: Final determination on a finding
- Finding: Raw pattern match output

Schema Types (Task 6.1):
- VulnerabilityBead: Complete investigation package
- PatternContext: Why the pattern matched
- InvestigationGuide: How to investigate
- TestContext: Test scaffold and scenario

Usage:
    from alphaswarm_sol.beads import (
        Finding,
        VulnerabilityBead,
        CodeSnippet,
        InvestigationStep,
        ExploitReference,
        Verdict,
        Severity,
        BeadStatus,
        VerdictType,
        PatternContext,
        InvestigationGuide,
        TestContext,
    )

    # Create a finding from pattern match
    finding = Finding(
        id="VKG-001",
        pattern_id="vm-001",
        function_id="func_vault_withdraw",
        contract_name="Vault",
        function_name="withdraw",
        file_path="/path/to/Vault.sol",
        line_number=45,
        severity=Severity.CRITICAL,
        confidence=0.95,
        vulnerability_class="reentrancy",
        description="State update after external call"
    )

    # Create a complete bead for investigation
    bead = VulnerabilityBead(
        id="VKG-001",
        vulnerability_class="reentrancy",
        pattern_id="vm-001",
        severity=Severity.CRITICAL,
        confidence=0.95,
        vulnerable_code=CodeSnippet(...),
        ...
    )

    # Generate LLM investigation prompt
    prompt = bead.get_llm_prompt()

    # Create a verdict
    verdict = Verdict(
        type=VerdictType.TRUE_POSITIVE,
        reason="Confirmed via code analysis",
        confidence=0.99,
        evidence=["External call before state update"]
    )
"""

from alphaswarm_sol.beads.types import (
    Severity,
    BeadStatus,
    VerdictType,
    CodeSnippet,
    InvestigationStep,
    ExploitReference,
    Verdict,
    Finding,
)
from alphaswarm_sol.beads.schema import (
    VulnerabilityBead,
    TestContext,
    PatternContext,
    InvestigationGuide,
)
from alphaswarm_sol.beads.creator import (
    BeadCreator,
    BeadCreationConfig,
    create_bead,
    create_beads,
)
from alphaswarm_sol.beads.storage import BeadStorage
# Event sourcing (Phase 7.1.1)
from alphaswarm_sol.beads.event_store import (
    BeadEvent,
    BeadEventStore,
    get_pool_event_store,
)
from alphaswarm_sol.beads.accuracy_test import (
    ExpectedVerdict,
    TestCase,
    LLMVerdict,
    TestResult,
    AccuracyReport,
    BeadAccuracyTester,
    load_test_cases,
    create_test_case,
    analyze_failures,
)
# Tool finding integration (Phase 5.1)
from alphaswarm_sol.beads.from_tools import (
    ToolFindingToBead,
    ToolBeadContext,
    create_beads_from_tools,
    TOOL_FINDING_CONFIDENCE,
)
from alphaswarm_sol.beads.triage import (
    BeadTriager,
    TriagePriority,
    TriageResult,
    TriageBatch,
    triage_beads,
)
# Context merge beads (Phase 5.5)
from alphaswarm_sol.beads.context_merge import (
    ContextMergeBead,
    ContextBeadStatus,
)

__all__ = [
    # Enums
    "Severity",
    "BeadStatus",
    "VerdictType",
    "ContextBeadStatus",
    # Foundation types
    "CodeSnippet",
    "InvestigationStep",
    "ExploitReference",
    "Verdict",
    "Finding",
    # Schema types
    "VulnerabilityBead",
    "TestContext",
    "PatternContext",
    "InvestigationGuide",
    # Creator
    "BeadCreator",
    "BeadCreationConfig",
    "create_bead",
    "create_beads",
    # Storage
    "BeadStorage",
    # Event Sourcing (Phase 7.1.1)
    "BeadEvent",
    "BeadEventStore",
    "get_pool_event_store",
    # Accuracy Testing
    "ExpectedVerdict",
    "TestCase",
    "LLMVerdict",
    "TestResult",
    "AccuracyReport",
    "BeadAccuracyTester",
    "load_test_cases",
    "create_test_case",
    "analyze_failures",
    # Tool Finding Integration (Phase 5.1)
    "ToolFindingToBead",
    "ToolBeadContext",
    "create_beads_from_tools",
    "TOOL_FINDING_CONFIDENCE",
    # Triage (Phase 5.1)
    "BeadTriager",
    "TriagePriority",
    "TriageResult",
    "TriageBatch",
    "triage_beads",
    # Context Merge (Phase 5.5)
    "ContextMergeBead",
]
