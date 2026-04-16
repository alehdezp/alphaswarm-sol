"""Economic prompt contract builder with causal and counterfactual requirements.

Per 05.11-CONTEXT.md: Agents must cite economic assumptions with provenance dates,
explore counterfactual scenarios, and build causal exploitation chains.

This module provides:
- LensTag: Economic reasoning lenses (VALUE, CONTROL, INCENTIVE, TRUST, TIMING, CONFIG)
- CausalChainElement: Elements of exploitation causal chains
- CounterfactualScenario: "What if" scenarios for mitigation exploration
- PromptValidator: Validates agent outputs meet economic contract requirements
- EconomicPromptContract: Builds prompts with economic context and requirements

Requirements enforced:
1. At least 1 lens tag per finding
2. Complete causal chain (root_cause -> exploit -> loss) for HIGH/CRITICAL
3. At least 2 counterfactual scenarios per finding
4. Provenance dates on all cited assumptions

Usage:
    from alphaswarm_sol.agents.prompts.economic_contract import (
        EconomicPromptContract,
        PromptValidator,
        LensTag,
    )

    # Build attacker prompt with economic context
    contract = EconomicPromptContract.for_attacker(
        dossier_summary="AMM protocol with TWAP oracle...",
        passport_snippet="Vault.sol: handles ETH custody, has 3 admin roles",
        policy_diff="Expected: onlyOwner on upgrade, Actual: no modifier",
        attack_ev=PayoffMatrix(scenario="oracle_manipulation", ...),
    )

    prompt = contract.build()

    # After agent execution, validate output
    validator = PromptValidator()
    result = validator.validate(agent_output)

    if not result.valid:
        for failure in result.failures:
            print(f"VALIDATION FAILURE: {failure}")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from alphaswarm_sol.economics.payoff import PayoffMatrix


class LensTag(str, Enum):
    """Economic reasoning lenses for agent findings.

    Per 05.11-CONTEXT.md: Each finding must reference at least one lens
    or explicitly state "lens missing".

    Lenses:
    - VALUE: Value flow analysis (deposits, withdrawals, custody)
    - CONTROL: Who can alter parameters, pause, upgrade
    - INCENTIVE: Who profits from breaking invariants
    - TRUST: Off-chain inputs (oracles, keepers, relayers)
    - TIMING: Delays, auctions, timelocks create windows
    - CONFIG: Mis-set parameters or role assignments

    Usage:
        finding = {
            "description": "Oracle price manipulation",
            "lens_tags": [LensTag.VALUE, LensTag.TRUST],
            ...
        }
    """

    VALUE = "value"
    CONTROL = "control"
    INCENTIVE = "incentive"
    TRUST = "trust"
    TIMING = "timing"
    CONFIG = "config"

    @classmethod
    def from_string(cls, value: str) -> "LensTag":
        """Create LensTag from string, case-insensitive."""
        normalized = value.lower().strip()
        aliases = {
            "value_flow": "value",
            "economic": "value",
            "access": "control",
            "governance": "control",
            "profit": "incentive",
            "reward": "incentive",
            "oracle": "trust",
            "offchain": "trust",
            "time": "timing",
            "delay": "timing",
            "configuration": "config",
            "misconfiguration": "config",
        }
        normalized = aliases.get(normalized, normalized)
        return cls(normalized)

    @classmethod
    def all_tags(cls) -> List["LensTag"]:
        """Return all lens tags."""
        return list(cls)


@dataclass
class CausalChainElement:
    """Element of a causal exploitation chain.

    Per 05.11-CONTEXT.md: Agents must cite complete causal chains:
    root_cause -> exploit_step_1 -> ... -> exploit_step_N -> financial_loss

    Attributes:
        step_type: Type of step (root_cause, exploit, amplifier, loss)
        description: What happens at this step
        evidence_refs: Evidence IDs supporting this step
        probability: Probability of this step succeeding (0.0-1.0)
        node_id: Optional graph node ID related to this step

    Usage:
        chain = [
            CausalChainElement(
                step_type="root_cause",
                description="Oracle price not validated for staleness",
                evidence_refs=["EVD-12345678"],
                probability=1.0,
            ),
            CausalChainElement(
                step_type="exploit",
                description="Attacker front-runs oracle update",
                probability=0.8,
            ),
            CausalChainElement(
                step_type="loss",
                description="$500k extracted from vault",
                probability=1.0,
            ),
        ]
    """

    step_type: str  # root_cause, exploit, amplifier, loss
    description: str
    evidence_refs: List[str] = field(default_factory=list)
    probability: float = 1.0
    node_id: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate step type and probability."""
        valid_types = {"root_cause", "exploit", "amplifier", "loss"}
        if self.step_type not in valid_types:
            raise ValueError(f"step_type must be one of {valid_types}, got {self.step_type}")
        if not 0.0 <= self.probability <= 1.0:
            raise ValueError(f"probability must be 0.0-1.0, got {self.probability}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "step_type": self.step_type,
            "description": self.description,
            "probability": self.probability,
        }
        if self.evidence_refs:
            result["evidence_refs"] = self.evidence_refs
        if self.node_id:
            result["node_id"] = self.node_id
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CausalChainElement":
        """Create from dictionary."""
        return cls(
            step_type=str(data.get("step_type", "exploit")),
            description=str(data.get("description", "")),
            evidence_refs=list(data.get("evidence_refs", [])),
            probability=float(data.get("probability", 1.0)),
            node_id=data.get("node_id"),
        )


@dataclass
class CounterfactualScenario:
    """A counterfactual "what if" scenario for mitigation exploration.

    Per 05.11-CONTEXT.md: Agents must explore at least 2 counterfactual
    scenarios per finding: "What if guard X existed?" / "What if param Y was different?"

    Attributes:
        scenario_type: Type (guard_exists, param_different, role_change, timing_change)
        description: What changes in this scenario
        would_prevent: Whether this would prevent the vulnerability
        impact: How the attack outcome changes
        evidence_refs: Evidence supporting this counterfactual analysis

    Usage:
        counterfactuals = [
            CounterfactualScenario(
                scenario_type="guard_exists",
                description="If reentrancy guard was present on withdraw()",
                would_prevent=True,
                impact="Attack blocked at external call step",
            ),
            CounterfactualScenario(
                scenario_type="param_different",
                description="If timelock delay was > 24 hours",
                would_prevent=False,
                impact="Attack delayed but not prevented",
            ),
        ]
    """

    scenario_type: str  # guard_exists, param_different, role_change, timing_change
    description: str
    would_prevent: bool
    impact: str
    evidence_refs: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate scenario type."""
        valid_types = {"guard_exists", "param_different", "role_change", "timing_change", "invariant_enforced"}
        if self.scenario_type not in valid_types:
            raise ValueError(f"scenario_type must be one of {valid_types}, got {self.scenario_type}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "scenario_type": self.scenario_type,
            "description": self.description,
            "would_prevent": self.would_prevent,
            "impact": self.impact,
        }
        if self.evidence_refs:
            result["evidence_refs"] = self.evidence_refs
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CounterfactualScenario":
        """Create from dictionary."""
        return cls(
            scenario_type=str(data.get("scenario_type", "guard_exists")),
            description=str(data.get("description", "")),
            would_prevent=bool(data.get("would_prevent", False)),
            impact=str(data.get("impact", "")),
            evidence_refs=list(data.get("evidence_refs", [])),
        )


@dataclass
class ValidationResult:
    """Result of prompt contract validation.

    Attributes:
        valid: Whether all validation checks passed
        failures: List of validation failure messages
        warnings: List of validation warning messages
        lens_tags_found: Lens tags found in the output
        causal_chain_valid: Whether causal chain is complete
        counterfactual_count: Number of counterfactual scenarios found
        cross_protocol_noted: Whether cross-protocol deps were mentioned
    """

    valid: bool
    failures: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    lens_tags_found: List[LensTag] = field(default_factory=list)
    causal_chain_valid: bool = False
    counterfactual_count: int = 0
    cross_protocol_noted: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "valid": self.valid,
            "failures": self.failures,
            "warnings": self.warnings,
            "lens_tags_found": [t.value for t in self.lens_tags_found],
            "causal_chain_valid": self.causal_chain_valid,
            "counterfactual_count": self.counterfactual_count,
            "cross_protocol_noted": self.cross_protocol_noted,
        }


class PromptValidator:
    """Validator for economic prompt contract requirements.

    Validates agent outputs meet requirements:
    1. At least 1 lens tag per finding
    2. Complete causal chain for HIGH/CRITICAL findings
    3. At least 2 counterfactual scenarios per finding
    4. Provenance dates on cited assumptions
    5. Cross-protocol dependencies noted when present

    Usage:
        validator = PromptValidator()
        result = validator.validate(agent_output)

        if not result.valid:
            for failure in result.failures:
                handle_validation_failure(failure)
    """

    # Minimum chain probability to be considered valid
    MIN_CHAIN_PROBABILITY = 0.1

    # Minimum counterfactuals required per finding
    MIN_COUNTERFACTUALS = 2

    def validate(self, output: Dict[str, Any]) -> ValidationResult:
        """Validate agent output against prompt contract requirements.

        Args:
            output: Agent output dictionary with findings

        Returns:
            ValidationResult with pass/fail status and details
        """
        failures: List[str] = []
        warnings: List[str] = []
        lens_tags_found: List[LensTag] = []
        causal_chain_valid = False
        counterfactual_count = 0
        cross_protocol_noted = False

        # Validate lens tags
        lens_result = self.validate_lens_tags(output)
        if not lens_result[0]:
            failures.append(lens_result[1])
        else:
            lens_tags_found = lens_result[2]

        # Validate causal chain (required for HIGH/CRITICAL)
        chain_result = self.validate_causal_chain(output)
        if not chain_result[0]:
            severity = output.get("severity", "medium").lower()
            if severity in ("high", "critical"):
                failures.append(chain_result[1])
            else:
                warnings.append(f"Causal chain incomplete: {chain_result[1]}")
        else:
            causal_chain_valid = True

        # Validate counterfactuals
        cf_result = self.validate_counterfactuals(output)
        if not cf_result[0]:
            warnings.append(cf_result[1])
        counterfactual_count = cf_result[2]

        # Validate cross-protocol awareness
        cp_result = self.validate_cross_protocol(output)
        if not cp_result[0]:
            warnings.append(cp_result[1])
        cross_protocol_noted = cp_result[0]

        # Validate provenance dates
        prov_result = self.validate_provenance(output)
        if not prov_result[0]:
            failures.append(prov_result[1])

        valid = len(failures) == 0

        return ValidationResult(
            valid=valid,
            failures=failures,
            warnings=warnings,
            lens_tags_found=lens_tags_found,
            causal_chain_valid=causal_chain_valid,
            counterfactual_count=counterfactual_count,
            cross_protocol_noted=cross_protocol_noted,
        )

    def validate_lens_tags(
        self, output: Dict[str, Any]
    ) -> Tuple[bool, str, List[LensTag]]:
        """Validate lens tags are present.

        Args:
            output: Agent output dictionary

        Returns:
            (valid, message, tags_found)
        """
        lens_tags = output.get("lens_tags", [])

        if not lens_tags:
            # Check for lens tag mentions in text fields
            text_fields = [
                output.get("description", ""),
                output.get("reasoning", ""),
                output.get("analysis", ""),
            ]
            combined_text = " ".join(str(f) for f in text_fields).lower()

            found_tags = []
            for tag in LensTag:
                if tag.value in combined_text:
                    found_tags.append(tag)

            if not found_tags:
                return (
                    False,
                    "No lens tags found. Each finding must reference at least one economic lens (VALUE, CONTROL, INCENTIVE, TRUST, TIMING, CONFIG).",
                    [],
                )
            return (True, "Lens tags found in text", found_tags)

        # Parse explicit lens tags
        parsed_tags = []
        for tag in lens_tags:
            if isinstance(tag, LensTag):
                parsed_tags.append(tag)
            elif isinstance(tag, str):
                try:
                    parsed_tags.append(LensTag.from_string(tag))
                except ValueError:
                    pass

        if not parsed_tags:
            return (
                False,
                "Invalid lens tags provided. Must be one of: VALUE, CONTROL, INCENTIVE, TRUST, TIMING, CONFIG.",
                [],
            )

        return (True, "Valid lens tags", parsed_tags)

    def validate_causal_chain(self, output: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate causal chain completeness.

        A complete chain must have:
        - At least one root_cause element
        - At least one exploit element
        - At least one loss element
        - Chain probability > MIN_CHAIN_PROBABILITY

        Args:
            output: Agent output dictionary

        Returns:
            (valid, message)
        """
        causal_chain = output.get("causal_chain", [])

        if not causal_chain:
            return (False, "Missing causal chain (root_cause -> exploit -> loss required)")

        has_root = False
        has_exploit = False
        has_loss = False
        chain_probability = 1.0

        for element in causal_chain:
            if isinstance(element, dict):
                step_type = element.get("step_type", "")
                prob = float(element.get("probability", 1.0))
            elif isinstance(element, CausalChainElement):
                step_type = element.step_type
                prob = element.probability
            else:
                continue

            chain_probability *= prob

            if step_type == "root_cause":
                has_root = True
            elif step_type == "exploit":
                has_exploit = True
            elif step_type == "loss":
                has_loss = True

        missing = []
        if not has_root:
            missing.append("root_cause")
        if not has_exploit:
            missing.append("exploit")
        if not has_loss:
            missing.append("loss")

        if missing:
            return (
                False,
                f"Incomplete causal chain. Missing elements: {', '.join(missing)}",
            )

        if chain_probability < self.MIN_CHAIN_PROBABILITY:
            return (
                False,
                f"Causal chain probability too low ({chain_probability:.2f} < {self.MIN_CHAIN_PROBABILITY})",
            )

        return (True, "Causal chain complete")

    def validate_counterfactuals(
        self, output: Dict[str, Any]
    ) -> Tuple[bool, str, int]:
        """Validate counterfactual scenarios.

        Per 05.11-CONTEXT.md: At least 2 counterfactual scenarios per finding.

        Args:
            output: Agent output dictionary

        Returns:
            (valid, message, count)
        """
        counterfactuals = output.get("counterfactuals", [])
        count = len(counterfactuals)

        if count < self.MIN_COUNTERFACTUALS:
            return (
                False,
                f"Insufficient counterfactual scenarios ({count} < {self.MIN_COUNTERFACTUALS}). Explore 'what if' mitigations.",
                count,
            )

        return (True, f"{count} counterfactual scenarios provided", count)

    def validate_cross_protocol(self, output: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate cross-protocol awareness.

        Args:
            output: Agent output dictionary

        Returns:
            (valid, message)
        """
        # Check if cross-protocol dependencies are mentioned
        cross_protocol = output.get("cross_protocol_dependencies", [])
        systemic_risk = output.get("systemic_risk_mentioned", False)

        if cross_protocol or systemic_risk:
            return (True, "Cross-protocol awareness demonstrated")

        # Check text fields for cross-protocol mentions
        text_fields = [
            output.get("description", ""),
            output.get("reasoning", ""),
            output.get("analysis", ""),
        ]
        combined_text = " ".join(str(f) for f in text_fields).lower()

        cross_protocol_keywords = [
            "cross-protocol",
            "cross protocol",
            "external protocol",
            "dependency",
            "cascade",
            "systemic",
            "composability",
        ]

        for keyword in cross_protocol_keywords:
            if keyword in combined_text:
                return (True, f"Cross-protocol awareness mentioned ({keyword})")

        # Not a failure, but a warning
        return (False, "Consider noting cross-protocol dependencies if present")

    def validate_provenance(self, output: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate provenance dates on assumptions.

        Args:
            output: Agent output dictionary

        Returns:
            (valid, message)
        """
        assumptions = output.get("assumptions", [])

        for assumption in assumptions:
            if isinstance(assumption, dict):
                if not assumption.get("source_date"):
                    return (
                        False,
                        f"Missing source_date on assumption: {assumption.get('description', 'unknown')[:50]}",
                    )

        # Check for evidence_refs without dates
        evidence = output.get("evidence", [])
        for ev in evidence:
            if isinstance(ev, dict):
                if ev.get("requires_provenance") and not ev.get("source_date"):
                    return (
                        False,
                        "Evidence marked as requires_provenance but missing source_date",
                    )

        return (True, "Provenance requirements met")


@dataclass
class EconomicPromptContract:
    """Economic prompt contract builder.

    Builds prompts with economic context and validation requirements:
    - Dossier summary (protocol overview)
    - Passport snippet (per-contract economic summary)
    - Policy diff (expected vs actual access control)
    - Attack EV (game-theoretic expected value)

    Also injects requirements for:
    - Lens tags (at least 1 per finding)
    - Causal chains (root_cause -> exploit -> loss)
    - Counterfactual scenarios (at least 2 per finding)
    - Cross-protocol awareness

    Usage:
        contract = EconomicPromptContract.for_attacker(
            dossier_summary="AMM protocol with $50M TVL...",
            passport_snippet="Vault.sol handles ETH custody...",
            policy_diff="Expected: onlyOwner, Actual: missing",
            attack_ev=PayoffMatrix(...),
        )

        prompt = contract.build()
    """

    role: str  # attacker, defender, verifier
    dossier_summary: str
    passport_snippet: str
    policy_diff: Optional[str] = None
    attack_ev: Optional[PayoffMatrix] = None
    cross_protocol_deps: List[str] = field(default_factory=list)
    required_lens_tags: List[LensTag] = field(default_factory=list)
    require_causal_chain: bool = True
    require_counterfactuals: bool = True
    min_counterfactuals: int = 2

    @classmethod
    def for_attacker(
        cls,
        dossier_summary: str,
        passport_snippet: str,
        policy_diff: Optional[str] = None,
        attack_ev: Optional[PayoffMatrix] = None,
        cross_protocol_deps: Optional[List[str]] = None,
    ) -> "EconomicPromptContract":
        """Create contract for attacker agent.

        Attacker focuses on VALUE, INCENTIVE, and TIMING lenses.
        """
        return cls(
            role="attacker",
            dossier_summary=dossier_summary,
            passport_snippet=passport_snippet,
            policy_diff=policy_diff,
            attack_ev=attack_ev,
            cross_protocol_deps=cross_protocol_deps or [],
            required_lens_tags=[LensTag.VALUE, LensTag.INCENTIVE],
            require_causal_chain=True,
            require_counterfactuals=True,
        )

    @classmethod
    def for_defender(
        cls,
        dossier_summary: str,
        passport_snippet: str,
        policy_diff: Optional[str] = None,
        cross_protocol_deps: Optional[List[str]] = None,
    ) -> "EconomicPromptContract":
        """Create contract for defender agent.

        Defender focuses on CONTROL and CONFIG lenses.
        """
        return cls(
            role="defender",
            dossier_summary=dossier_summary,
            passport_snippet=passport_snippet,
            policy_diff=policy_diff,
            attack_ev=None,  # Defender doesn't need attack EV
            cross_protocol_deps=cross_protocol_deps or [],
            required_lens_tags=[LensTag.CONTROL, LensTag.CONFIG],
            require_causal_chain=False,  # Defender identifies guards, not chains
            require_counterfactuals=True,
        )

    @classmethod
    def for_verifier(
        cls,
        dossier_summary: str,
        passport_snippet: str,
        attack_ev: Optional[PayoffMatrix] = None,
        cross_protocol_deps: Optional[List[str]] = None,
    ) -> "EconomicPromptContract":
        """Create contract for verifier agent.

        Verifier cross-checks evidence and validates chains.
        """
        return cls(
            role="verifier",
            dossier_summary=dossier_summary,
            passport_snippet=passport_snippet,
            policy_diff=None,
            attack_ev=attack_ev,
            cross_protocol_deps=cross_protocol_deps or [],
            required_lens_tags=[],  # Verifier validates, doesn't generate
            require_causal_chain=True,  # Must validate chains
            require_counterfactuals=True,
        )

    def build(self) -> str:
        """Build the complete prompt with economic context and requirements.

        Returns:
            Complete prompt string for agent
        """
        sections = []

        # Economic context section
        sections.append(self._build_context_section())

        # Requirements section
        sections.append(self._build_requirements_section())

        # Attack EV section (if applicable)
        if self.attack_ev:
            sections.append(self._build_attack_ev_section())

        # Cross-protocol section (if applicable)
        if self.cross_protocol_deps:
            sections.append(self._build_cross_protocol_section())

        return "\n\n".join(sections)

    def _build_context_section(self) -> str:
        """Build the economic context section."""
        lines = [
            "## Economic Context",
            "",
            "### Protocol Dossier",
            self.dossier_summary,
            "",
            "### Contract Passport",
            self.passport_snippet,
        ]

        if self.policy_diff:
            lines.extend([
                "",
                "### Policy Diff (Expected vs Actual)",
                self.policy_diff,
            ])

        return "\n".join(lines)

    def _build_requirements_section(self) -> str:
        """Build the output requirements section."""
        lines = [
            "## Output Requirements",
            "",
            "Your output MUST include the following elements:",
            "",
        ]

        # Lens tags
        lens_str = ", ".join(t.value.upper() for t in LensTag.all_tags())
        lines.append(f"### 1. Lens Tags (Required: at least 1)")
        lines.append(f"Tag your finding with economic lenses: {lens_str}")
        lines.append("")

        # Causal chain
        if self.require_causal_chain:
            lines.extend([
                "### 2. Causal Chain (Required for HIGH/CRITICAL)",
                "Provide complete exploitation chain:",
                "```",
                "causal_chain:",
                "  - step_type: root_cause",
                "    description: The underlying vulnerability",
                "    evidence_refs: [EVD-...]",
                "    probability: 1.0",
                "  - step_type: exploit",
                "    description: How attacker exploits it",
                "    probability: 0.8",
                "  - step_type: loss",
                "    description: Financial impact",
                "    probability: 1.0",
                "```",
                "",
            ])

        # Counterfactuals
        if self.require_counterfactuals:
            lines.extend([
                f"### 3. Counterfactual Scenarios (Required: at least {self.min_counterfactuals})",
                "Explore 'what if' mitigations:",
                "```",
                "counterfactuals:",
                "  - scenario_type: guard_exists",
                "    description: What if reentrancy guard existed?",
                "    would_prevent: true",
                "    impact: Attack blocked at external call",
                "  - scenario_type: param_different",
                "    description: What if timelock > 24h?",
                "    would_prevent: false",
                "    impact: Attack delayed but not prevented",
                "```",
                "",
            ])

        # Provenance
        lines.extend([
            "### 4. Provenance (Required on assumptions)",
            "All cited assumptions must include source_date:",
            "```",
            "assumptions:",
            "  - description: Admin is trusted multisig",
            "    source_date: 2025-01-15",
            "    source_id: whitepaper-v1.2",
            "```",
            "",
        ])

        return "\n".join(lines)

    def _build_attack_ev_section(self) -> str:
        """Build the attack expected value section."""
        if not self.attack_ev:
            return ""

        ev = self.attack_ev.attacker_expected_value
        is_profitable = self.attack_ev.is_attack_profitable
        tvl = self.attack_ev.tvl_at_risk_usd

        lines = [
            "## Attack Economics",
            "",
            f"**Expected Value (EV):** ${ev:,.2f}",
            f"**Is Profitable:** {'Yes' if is_profitable else 'No'}",
            f"**TVL at Risk:** ${tvl:,.2f}",
            "",
            "Consider these economics when assessing exploit viability.",
        ]

        if self.attack_ev.attacker_payoff:
            payoff = self.attack_ev.attacker_payoff
            lines.extend([
                "",
                "**Attack Details:**",
                f"- Expected Profit: ${payoff.expected_profit_usd:,.2f}",
                f"- Success Probability: {payoff.success_probability:.0%}",
                f"- MEV Risk: {payoff.mev_risk:.0%}",
                f"- Execution Complexity: {payoff.execution_complexity}",
            ])

        return "\n".join(lines)

    def _build_cross_protocol_section(self) -> str:
        """Build the cross-protocol dependencies section."""
        if not self.cross_protocol_deps:
            return ""

        lines = [
            "## Cross-Protocol Dependencies",
            "",
            "The following external protocols are dependencies:",
            "",
        ]

        for dep in self.cross_protocol_deps:
            lines.append(f"- {dep}")

        lines.extend([
            "",
            "**NOTE:** Consider systemic risk implications if these dependencies fail.",
        ])

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "role": self.role,
            "dossier_summary": self.dossier_summary,
            "passport_snippet": self.passport_snippet,
            "required_lens_tags": [t.value for t in self.required_lens_tags],
            "require_causal_chain": self.require_causal_chain,
            "require_counterfactuals": self.require_counterfactuals,
            "min_counterfactuals": self.min_counterfactuals,
        }

        if self.policy_diff:
            result["policy_diff"] = self.policy_diff
        if self.attack_ev:
            result["attack_ev"] = self.attack_ev.to_dict()
        if self.cross_protocol_deps:
            result["cross_protocol_deps"] = self.cross_protocol_deps

        return result


# Export all types
__all__ = [
    "LensTag",
    "CausalChainElement",
    "CounterfactualScenario",
    "ValidationResult",
    "PromptValidator",
    "EconomicPromptContract",
]
