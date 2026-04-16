"""Enhanced economic probes for vulnerability plausibility analysis.

Per 05.11-CONTEXT.md: Lightweight probes to pressure-test real-world exploitability.
Probe failures produce unknowns or expansion requests, not false positives.

Probes:
- profitability_probe: Is there clear payoff given fees, caps, delays?
- control_path_probe: Can attacker reach necessary control?
- assumption_break_probe: If off-chain assumption fails, what changes?
- governance_capture_probe: Can upgrades/params enable abuse?
- value_at_risk_probe: Maximum extractable value in one path?
- counterfactual_probe: What if X guard existed? (NEW)
- cascade_probe: If this fails, what protocols are affected? (NEW)

Usage:
    from alphaswarm_sol.beads.economic_probes import (
        EconomicProbeRunner,
        ProbeResult,
        run_profitability_probe,
        run_counterfactual_probe,
        run_cascade_probe,
    )

    runner = EconomicProbeRunner(context_pack=pack, passports=passports)

    # Run all probes for a vulnerability
    results = runner.run_all_probes(vulnerability, causal_chain)

    # Check for unknowns
    unknowns = [r for r in results if r.status == ProbeStatus.UNKNOWN]
    if unknowns:
        request_context_expansion(unknowns)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from alphaswarm_sol.context.schema import ProtocolContextPack
    from alphaswarm_sol.context.linker import CausalChainLink
    from alphaswarm_sol.context.passports import ContractPassport
    from alphaswarm_sol.economics.payoff import PayoffMatrix


class ProbeStatus(Enum):
    """Status of an economic probe.

    Per 05.11-CONTEXT.md: Probe failures produce unknowns or expansion requests.
    """

    PASSED = "passed"  # Probe confirms exploitability
    FAILED = "failed"  # Probe suggests not exploitable
    UNKNOWN = "unknown"  # Insufficient data to determine
    EXPANSION_REQUIRED = "expansion_required"  # Need more context


class ProbeType(Enum):
    """Types of economic probes.

    Per 05.11-CONTEXT.md: Economic probes to pressure-test exploitability.
    """

    PROFITABILITY = "profitability"  # Is there clear payoff?
    CONTROL_PATH = "control_path"  # Can attacker reach necessary control?
    ASSUMPTION_BREAK = "assumption_break"  # What if assumption fails?
    GOVERNANCE_CAPTURE = "governance_capture"  # Can upgrades/params enable abuse?
    VALUE_AT_RISK = "value_at_risk"  # Max extractable value in one path
    COUNTERFACTUAL = "counterfactual"  # What if X guard existed?
    CASCADE = "cascade"  # What protocols are affected if this fails?


@dataclass
class ProbeResult:
    """Result of an economic probe.

    Per 05.11-CONTEXT.md: Probe results are recorded as evidence_refs
    and mark unknown if probes fail.

    Attributes:
        probe_type: Type of probe executed
        status: Probe outcome status
        findings: Specific findings from the probe
        evidence_refs: Evidence supporting the probe result
        confidence: Confidence in the probe result (0-1)
        expansion_request: Context expansion request if needed
        notes: Additional notes
    """

    probe_type: ProbeType
    status: ProbeStatus
    findings: List[str] = field(default_factory=list)
    evidence_refs: List[str] = field(default_factory=list)
    confidence: float = 0.5
    expansion_request: Optional[str] = None
    notes: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate confidence range."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be 0.0-1.0, got {self.confidence}")

    @property
    def is_conclusive(self) -> bool:
        """Whether the probe reached a conclusive result."""
        return self.status in (ProbeStatus.PASSED, ProbeStatus.FAILED)

    @property
    def needs_expansion(self) -> bool:
        """Whether context expansion is needed."""
        return self.status == ProbeStatus.EXPANSION_REQUIRED

    @property
    def is_unknown(self) -> bool:
        """Whether the probe result is unknown."""
        return self.status == ProbeStatus.UNKNOWN

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "probe_type": self.probe_type.value,
            "status": self.status.value,
            "findings": self.findings,
            "evidence_refs": self.evidence_refs,
            "confidence": round(self.confidence, 2),
            "expansion_request": self.expansion_request,
            "notes": self.notes,
            "is_conclusive": self.is_conclusive,
            "needs_expansion": self.needs_expansion,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProbeResult":
        """Create ProbeResult from dictionary."""
        return cls(
            probe_type=ProbeType(data.get("probe_type", "profitability")),
            status=ProbeStatus(data.get("status", "unknown")),
            findings=list(data.get("findings", [])),
            evidence_refs=list(data.get("evidence_refs", [])),
            confidence=float(data.get("confidence", 0.5)),
            expansion_request=data.get("expansion_request"),
            notes=list(data.get("notes", [])),
        )


@dataclass
class CounterfactualScenario:
    """A counterfactual scenario for analysis.

    Per 05.11-CONTEXT.md: Counterfactual probes ask "what if X guard existed?"

    Attributes:
        guard_id: Identifier for the hypothetical guard
        guard_description: What the guard would do
        would_block: Whether this guard would block the exploit
        affected_steps: Steps in the chain that would be blocked
        confidence: Confidence in this counterfactual assessment
    """

    guard_id: str
    guard_description: str
    would_block: bool = False
    affected_steps: List[str] = field(default_factory=list)
    confidence: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "guard_id": self.guard_id,
            "guard_description": self.guard_description,
            "would_block": self.would_block,
            "affected_steps": self.affected_steps,
            "confidence": round(self.confidence, 2),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CounterfactualScenario":
        """Create CounterfactualScenario from dictionary."""
        return cls(
            guard_id=str(data.get("guard_id", "")),
            guard_description=str(data.get("guard_description", "")),
            would_block=bool(data.get("would_block", False)),
            affected_steps=list(data.get("affected_steps", [])),
            confidence=float(data.get("confidence", 0.5)),
        )


@dataclass
class CascadeImpact:
    """Impact assessment for cascade failures.

    Per 05.11-CONTEXT.md: Cascade probes assess cross-protocol impact.

    Attributes:
        source_protocol: Protocol where failure originates
        affected_protocols: Protocols affected by cascade
        affected_tvl_usd: Total TVL at risk from cascade
        cascade_depth: How deep the cascade propagates
        critical_paths: Critical dependency paths
    """

    source_protocol: str
    affected_protocols: List[str] = field(default_factory=list)
    affected_tvl_usd: float = 0.0
    cascade_depth: int = 1
    critical_paths: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "source_protocol": self.source_protocol,
            "affected_protocols": self.affected_protocols,
            "affected_tvl_usd": round(self.affected_tvl_usd, 2),
            "cascade_depth": self.cascade_depth,
            "critical_paths": self.critical_paths,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CascadeImpact":
        """Create CascadeImpact from dictionary."""
        return cls(
            source_protocol=str(data.get("source_protocol", "")),
            affected_protocols=list(data.get("affected_protocols", [])),
            affected_tvl_usd=float(data.get("affected_tvl_usd", 0.0)),
            cascade_depth=int(data.get("cascade_depth", 1)),
            critical_paths=list(data.get("critical_paths", [])),
        )


class EconomicProbeRunner:
    """Runner for economic plausibility probes.

    Per 05.11-CONTEXT.md: Probes to pressure-test real-world exploitability.
    Results are stored as evidence_refs and mark unknown if probes fail.

    Usage:
        runner = EconomicProbeRunner(context_pack=pack, passports=passports)
        results = runner.run_all_probes(vulnerability, causal_chain)
    """

    def __init__(
        self,
        context_pack: Optional["ProtocolContextPack"] = None,
        passports: Optional[Dict[str, "ContractPassport"]] = None,
        payoff_matrix: Optional["PayoffMatrix"] = None,
    ) -> None:
        """Initialize the probe runner.

        Args:
            context_pack: Optional ProtocolContextPack for context
            passports: Optional mapping of contract_id to ContractPassport
            payoff_matrix: Optional PayoffMatrix for profitability analysis
        """
        self._context_pack = context_pack
        self._passports = passports or {}
        self._payoff_matrix = payoff_matrix

    def run_all_probes(
        self,
        vulnerability_id: str,
        causal_chain: Optional["CausalChainLink"] = None,
    ) -> List[ProbeResult]:
        """Run all economic probes for a vulnerability.

        Args:
            vulnerability_id: Vulnerability identifier
            causal_chain: Optional causal chain for analysis

        Returns:
            List of ProbeResult objects
        """
        results = []

        # 1. Profitability probe
        results.append(self.run_profitability_probe(vulnerability_id))

        # 2. Control path probe
        results.append(self.run_control_path_probe(vulnerability_id))

        # 3. Assumption break probe
        results.append(self.run_assumption_break_probe(vulnerability_id))

        # 4. Governance capture probe
        results.append(self.run_governance_capture_probe(vulnerability_id))

        # 5. Value at risk probe
        results.append(self.run_value_at_risk_probe(vulnerability_id))

        # 6. Counterfactual probe (if causal chain provided)
        if causal_chain:
            results.append(self.run_counterfactual_probe(causal_chain))

        # 7. Cascade probe
        results.append(self.run_cascade_probe(vulnerability_id))

        return results

    def run_profitability_probe(self, vulnerability_id: str) -> ProbeResult:
        """Probe: Is there clear payoff given fees, caps, delays?

        Per 05.11-CONTEXT.md: Check if attack is profitable after costs.

        Args:
            vulnerability_id: Vulnerability identifier

        Returns:
            ProbeResult for profitability
        """
        findings: List[str] = []
        evidence_refs: List[str] = []
        notes: List[str] = []

        if self._payoff_matrix:
            ev = self._payoff_matrix.attacker_expected_value
            evidence_refs.append(f"payoff_matrix:{self._payoff_matrix.scenario}")

            if ev > 0:
                findings.append(f"Positive expected value: ${ev:,.2f}")
                status = ProbeStatus.PASSED
                confidence = 0.8
            else:
                findings.append(f"Negative expected value: ${ev:,.2f}")
                status = ProbeStatus.FAILED
                confidence = 0.7
        else:
            findings.append("No payoff matrix available")
            notes.append("Profitability cannot be determined without payoff data")
            status = ProbeStatus.UNKNOWN
            confidence = 0.3

        return ProbeResult(
            probe_type=ProbeType.PROFITABILITY,
            status=status,
            findings=findings,
            evidence_refs=evidence_refs,
            confidence=confidence,
            notes=notes,
        )

    def run_control_path_probe(self, vulnerability_id: str) -> ProbeResult:
        """Probe: Can attacker reach necessary control?

        Args:
            vulnerability_id: Vulnerability identifier

        Returns:
            ProbeResult for control path
        """
        findings: List[str] = []
        evidence_refs: List[str] = []
        notes: List[str] = []

        # Check if vulnerability is in a publicly accessible function
        has_public_access = False
        has_role_requirement = False

        if self._context_pack:
            # Check roles and their required capabilities
            for role in self._context_pack.roles:
                if any("admin" in cap.lower() or "owner" in cap.lower() for cap in role.capabilities):
                    has_role_requirement = True
                    findings.append(f"Role required: {role.name}")
                    evidence_refs.append(f"role:{role.name}")

            if not has_role_requirement:
                has_public_access = True
                findings.append("No special role required for access")

        if has_public_access:
            status = ProbeStatus.PASSED
            confidence = 0.7
        elif has_role_requirement:
            status = ProbeStatus.FAILED
            confidence = 0.6
            notes.append("Attack requires privileged access")
        else:
            status = ProbeStatus.UNKNOWN
            confidence = 0.3
            notes.append("Cannot determine access requirements")

        return ProbeResult(
            probe_type=ProbeType.CONTROL_PATH,
            status=status,
            findings=findings,
            evidence_refs=evidence_refs,
            confidence=confidence,
            notes=notes,
        )

    def run_assumption_break_probe(self, vulnerability_id: str) -> ProbeResult:
        """Probe: If off-chain assumption fails, what changes?

        Args:
            vulnerability_id: Vulnerability identifier

        Returns:
            ProbeResult for assumption break
        """
        findings: List[str] = []
        evidence_refs: List[str] = []
        notes: List[str] = []

        if self._context_pack:
            # Check for off-chain assumptions
            for assumption in self._context_pack.assumptions:
                if assumption.category.lower() in ["oracle", "price", "offchain"]:
                    findings.append(f"Off-chain assumption: {assumption.description}")
                    evidence_refs.append(f"assumption:{assumption.category}")

                    if assumption.confidence.value == "unknown":
                        notes.append(f"Low confidence assumption: {assumption.description}")

            for offchain in self._context_pack.offchain_inputs:
                findings.append(f"Off-chain input: {offchain.name} ({offchain.input_type})")
                evidence_refs.append(f"offchain:{offchain.name}")

        if findings:
            status = ProbeStatus.PASSED
            confidence = 0.6
            notes.append("Off-chain assumptions present that could be broken")
        else:
            status = ProbeStatus.UNKNOWN
            confidence = 0.4
            notes.append("No off-chain assumptions documented")

        return ProbeResult(
            probe_type=ProbeType.ASSUMPTION_BREAK,
            status=status,
            findings=findings,
            evidence_refs=evidence_refs,
            confidence=confidence,
            notes=notes,
        )

    def run_governance_capture_probe(self, vulnerability_id: str) -> ProbeResult:
        """Probe: Can upgrades/params enable abuse?

        Args:
            vulnerability_id: Vulnerability identifier

        Returns:
            ProbeResult for governance capture
        """
        findings: List[str] = []
        evidence_refs: List[str] = []
        notes: List[str] = []

        upgrade_risk = False
        param_risk = False

        if self._context_pack:
            # Check for upgrade capabilities in roles
            for role in self._context_pack.roles:
                if any("upgrade" in cap.lower() for cap in role.capabilities):
                    upgrade_risk = True
                    findings.append(f"Upgrade capability: {role.name}")
                    evidence_refs.append(f"role:{role.name}:upgrade")

                if any("param" in cap.lower() or "set" in cap.lower() for cap in role.capabilities):
                    param_risk = True
                    findings.append(f"Parameter control: {role.name}")
                    evidence_refs.append(f"role:{role.name}:param")

        for contract_id, passport in self._passports.items():
            if "upgrade" in passport.critical_actions or any(
                "upgrade" in stage.value for stage in passport.allowed_lifecycle_stages
            ):
                upgrade_risk = True
                findings.append(f"Contract upgradeable: {contract_id}")
                evidence_refs.append(f"passport:{contract_id}:upgrade")

        if upgrade_risk or param_risk:
            status = ProbeStatus.PASSED
            confidence = 0.7
            notes.append("Governance vectors exist for potential abuse")
        else:
            status = ProbeStatus.FAILED
            confidence = 0.6
            notes.append("No significant governance attack surface")

        return ProbeResult(
            probe_type=ProbeType.GOVERNANCE_CAPTURE,
            status=status,
            findings=findings,
            evidence_refs=evidence_refs,
            confidence=confidence,
            notes=notes,
        )

    def run_value_at_risk_probe(self, vulnerability_id: str) -> ProbeResult:
        """Probe: Maximum extractable value in one path?

        Args:
            vulnerability_id: Vulnerability identifier

        Returns:
            ProbeResult for value at risk
        """
        findings: List[str] = []
        evidence_refs: List[str] = []
        notes: List[str] = []

        total_var = 0.0

        if self._payoff_matrix:
            total_var = self._payoff_matrix.tvl_at_risk_usd
            evidence_refs.append(f"payoff_matrix:{self._payoff_matrix.scenario}")
            findings.append(f"TVL at risk from payoff matrix: ${total_var:,.2f}")

        if self._context_pack:
            # Check value flows for maximum extraction
            for flow in self._context_pack.value_flows:
                if flow.to_role.lower() in ["user", "protocol", "attacker"]:
                    findings.append(f"Value flow: {flow.name} ({flow.asset})")
                    evidence_refs.append(f"flow:{flow.name}")

        if total_var > 0:
            if total_var >= 1_000_000:
                status = ProbeStatus.PASSED
                confidence = 0.8
                notes.append(f"High value at risk: ${total_var:,.2f}")
            else:
                status = ProbeStatus.PASSED
                confidence = 0.6
                notes.append(f"Moderate value at risk: ${total_var:,.2f}")
        else:
            status = ProbeStatus.UNKNOWN
            confidence = 0.3
            notes.append("Value at risk not quantified")

        return ProbeResult(
            probe_type=ProbeType.VALUE_AT_RISK,
            status=status,
            findings=findings,
            evidence_refs=evidence_refs,
            confidence=confidence,
            notes=notes,
        )

    def run_counterfactual_probe(
        self,
        causal_chain: "CausalChainLink",
        guards: Optional[List[str]] = None,
    ) -> ProbeResult:
        """Probe: What if X guard existed?

        Per 05.11-CONTEXT.md: NEW probe for counterfactual reasoning.

        Args:
            causal_chain: Causal chain to analyze
            guards: Optional list of hypothetical guards to test

        Returns:
            ProbeResult for counterfactual
        """
        findings: List[str] = []
        evidence_refs: List[str] = []
        notes: List[str] = []
        scenarios: List[CounterfactualScenario] = []

        # Default guards to test
        default_guards = guards or [
            "reentrancy_guard",
            "access_control",
            "pause_mechanism",
            "rate_limit",
            "oracle_validation",
        ]

        for guard_id in default_guards:
            scenario = self._evaluate_counterfactual(causal_chain, guard_id)
            scenarios.append(scenario)

            if scenario.would_block:
                findings.append(f"Guard '{guard_id}' would block exploit")
                evidence_refs.append(f"counterfactual:{guard_id}:block")
            else:
                notes.append(f"Guard '{guard_id}' would not block exploit")

        blocking_guards = [s for s in scenarios if s.would_block]

        if not blocking_guards:
            status = ProbeStatus.PASSED
            confidence = 0.6
            notes.append("No simple guards would block this exploit")
        elif len(blocking_guards) >= 2:
            status = ProbeStatus.FAILED
            confidence = 0.7
            notes.append(f"{len(blocking_guards)} guards would block exploit")
        else:
            status = ProbeStatus.PASSED
            confidence = 0.5
            notes.append("Single guard could block exploit")

        return ProbeResult(
            probe_type=ProbeType.COUNTERFACTUAL,
            status=status,
            findings=findings,
            evidence_refs=evidence_refs,
            confidence=confidence,
            notes=notes,
        )

    def _evaluate_counterfactual(
        self,
        causal_chain: "CausalChainLink",
        guard_id: str,
    ) -> CounterfactualScenario:
        """Evaluate if a guard would block a causal chain.

        Args:
            causal_chain: Causal chain to analyze
            guard_id: Guard to evaluate

        Returns:
            CounterfactualScenario with assessment
        """
        guard_lower = guard_id.lower()
        affected_steps: List[str] = []
        would_block = False

        # Heuristic evaluation based on guard type and chain steps
        for step in causal_chain.exploit_steps:
            step_lower = step.lower()

            # Reentrancy guard blocks reentrancy steps
            if guard_lower == "reentrancy_guard" and "reentran" in step_lower:
                would_block = True
                affected_steps.append(step)

            # Access control blocks unauthorized access
            if guard_lower == "access_control" and any(
                kw in step_lower for kw in ["unauthorized", "public", "external"]
            ):
                would_block = True
                affected_steps.append(step)

            # Pause mechanism blocks all operations
            if guard_lower == "pause_mechanism":
                would_block = True
                affected_steps.append(step)

            # Rate limit blocks rapid exploitation
            if guard_lower == "rate_limit" and any(
                kw in step_lower for kw in ["flash", "loop", "batch"]
            ):
                would_block = True
                affected_steps.append(step)

            # Oracle validation blocks price manipulation
            if guard_lower == "oracle_validation" and any(
                kw in step_lower for kw in ["oracle", "price", "twap"]
            ):
                would_block = True
                affected_steps.append(step)

        # Check counterfactual_blocks in the chain itself
        if guard_id in causal_chain.counterfactual_blocks:
            would_block = True

        guard_descriptions = {
            "reentrancy_guard": "ReentrancyGuard modifier to prevent reentrant calls",
            "access_control": "Access control restricting function to authorized roles",
            "pause_mechanism": "Emergency pause capability to halt operations",
            "rate_limit": "Rate limiting to prevent rapid exploitation",
            "oracle_validation": "Oracle validation with TWAP and freshness checks",
        }

        return CounterfactualScenario(
            guard_id=guard_id,
            guard_description=guard_descriptions.get(guard_id, f"Hypothetical guard: {guard_id}"),
            would_block=would_block,
            affected_steps=affected_steps,
            confidence=0.6 if would_block else 0.5,
        )

    def run_cascade_probe(self, vulnerability_id: str) -> ProbeResult:
        """Probe: If this fails, what protocols are affected?

        Per 05.11-CONTEXT.md: NEW probe for cross-protocol cascade analysis.

        Args:
            vulnerability_id: Vulnerability identifier

        Returns:
            ProbeResult for cascade
        """
        findings: List[str] = []
        evidence_refs: List[str] = []
        notes: List[str] = []

        # Analyze cross-protocol dependencies from passports
        affected_protocols: set[str] = set()
        cascade_depth = 1

        for contract_id, passport in self._passports.items():
            for dep in passport.cross_protocol_dependencies:
                if dep.criticality >= 7:
                    affected_protocols.add(dep.protocol_id)
                    findings.append(f"Critical dependency: {dep.protocol_id} (criticality={dep.criticality})")
                    evidence_refs.append(f"dep:{contract_id}:{dep.protocol_id}")

                    if dep.failure_cascade_impact:
                        notes.append(f"Cascade impact: {dep.failure_cascade_impact}")

        cascade_impact = CascadeImpact(
            source_protocol=vulnerability_id,
            affected_protocols=list(affected_protocols),
            cascade_depth=cascade_depth,
        )

        if len(affected_protocols) >= 3:
            status = ProbeStatus.PASSED
            confidence = 0.7
            notes.append(f"High cascade risk: {len(affected_protocols)} protocols affected")
        elif affected_protocols:
            status = ProbeStatus.PASSED
            confidence = 0.5
            notes.append(f"Moderate cascade risk: {len(affected_protocols)} protocols affected")
        else:
            status = ProbeStatus.FAILED
            confidence = 0.6
            notes.append("No significant cross-protocol cascade risk")

        return ProbeResult(
            probe_type=ProbeType.CASCADE,
            status=status,
            findings=findings,
            evidence_refs=evidence_refs,
            confidence=confidence,
            notes=notes,
        )


# Convenience functions for individual probes
def run_profitability_probe(
    vulnerability_id: str,
    payoff_matrix: Optional["PayoffMatrix"] = None,
) -> ProbeResult:
    """Run profitability probe."""
    runner = EconomicProbeRunner(payoff_matrix=payoff_matrix)
    return runner.run_profitability_probe(vulnerability_id)


def run_counterfactual_probe(
    causal_chain: "CausalChainLink",
    guards: Optional[List[str]] = None,
) -> ProbeResult:
    """Run counterfactual probe."""
    runner = EconomicProbeRunner()
    return runner.run_counterfactual_probe(causal_chain, guards)


def run_cascade_probe(
    vulnerability_id: str,
    passports: Optional[Dict[str, "ContractPassport"]] = None,
) -> ProbeResult:
    """Run cascade probe."""
    runner = EconomicProbeRunner(passports=passports)
    return runner.run_cascade_probe(vulnerability_id)


# Export all types
__all__ = [
    "ProbeStatus",
    "ProbeType",
    "ProbeResult",
    "CounterfactualScenario",
    "CascadeImpact",
    "EconomicProbeRunner",
    "run_profitability_probe",
    "run_counterfactual_probe",
    "run_cascade_probe",
]
