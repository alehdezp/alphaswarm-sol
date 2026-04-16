"""
Intent Schema

Defines data structures for capturing LLM-inferred business intent.
Intent enables detection of business logic bugs by comparing what code DOES
vs what it SHOULD do based on its business purpose.

KEY INSIGHT: Most vulnerabilities aren't syntax errors - they're behavior
that makes sense syntactically but violates business-level expectations.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
from enum import Enum


class BusinessPurpose(Enum):
    """
    Taxonomy of function business purposes.

    This taxonomy covers 90%+ of DeFi functions and enables
    intent-aware vulnerability detection.
    """

    # === VALUE MOVEMENT ===
    WITHDRAWAL = "withdrawal"  # User withdraws their assets
    DEPOSIT = "deposit"  # User deposits assets
    TRANSFER = "transfer"  # Transfer between users
    CLAIM_REWARDS = "claim_rewards"  # Claim accrued rewards
    MINT = "mint"  # Mint new tokens
    BURN = "burn"  # Burn tokens

    # === TRADING ===
    SWAP = "swap"  # Exchange assets (AMM)
    ADD_LIQUIDITY = "add_liquidity"  # Provide liquidity
    REMOVE_LIQUIDITY = "remove_liquidity"  # Remove liquidity

    # === GOVERNANCE ===
    VOTE = "vote"  # Cast vote on proposal
    PROPOSE = "propose"  # Create governance proposal
    EXECUTE_PROPOSAL = "execute_proposal"  # Execute passed proposal
    DELEGATE = "delegate"  # Delegate voting power

    # === ADMINISTRATION ===
    SET_PARAMETER = "set_parameter"  # Update protocol parameter
    PAUSE = "pause"  # Emergency pause
    UNPAUSE = "unpause"  # Resume from pause
    UPGRADE = "upgrade"  # Upgrade contract logic
    TRANSFER_OWNERSHIP = "transfer_ownership"  # Change owner
    GRANT_ROLE = "grant_role"  # Grant access control role
    REVOKE_ROLE = "revoke_role"  # Revoke access control role

    # === FINANCIAL (LENDING/BORROWING) ===
    BORROW = "borrow"  # Borrow assets
    REPAY = "repay"  # Repay loan
    LIQUIDATE = "liquidate"  # Liquidate undercollateralized position
    ACCRUE_INTEREST = "accrue_interest"  # Update interest accrual

    # === ORACLE/PRICE ===
    UPDATE_PRICE = "update_price"  # Update oracle price
    SYNC_RESERVES = "sync_reserves"  # Sync AMM reserves

    # === UTILITY ===
    VIEW_ONLY = "view_only"  # Read-only function
    CALLBACK = "callback"  # Callback from external contract
    INTERNAL_HELPER = "internal_helper"  # Internal utility function
    CONSTRUCTOR = "constructor"  # Contract constructor
    FALLBACK = "fallback"  # Fallback/receive function

    # === STAKING ===
    STAKE = "stake"  # Stake tokens
    UNSTAKE = "unstake"  # Unstake tokens

    # === FLASH LOAN ===
    FLASH_LOAN = "flash_loan"  # Initiate flash loan
    FLASH_LOAN_CALLBACK = "flash_loan_callback"  # Flash loan callback

    # === UNKNOWN ===
    UNKNOWN = "unknown"  # Cannot infer purpose
    COMPLEX_MULTIFUNCTION = "complex_multifunction"  # Multiple purposes


class TrustLevel(Enum):
    """
    Expected trust level for function callers.

    Defines who SHOULD be able to call this function safely.
    Violations indicate authorization vulnerabilities.
    """

    PERMISSIONLESS = "permissionless"  # Anyone can call safely
    DEPOSITOR_ONLY = "depositor_only"  # Only users with deposits/balance
    ROLE_RESTRICTED = "role_restricted"  # Specific roles (admin, minter, etc.)
    OWNER_ONLY = "owner_only"  # Contract owner only
    GOVERNANCE_ONLY = "governance_only"  # Governance contract only
    INTERNAL_ONLY = "internal_only"  # Only callable by contract itself
    TRUSTED_CONTRACTS = "trusted_contracts"  # Whitelisted contracts only


@dataclass
class TrustAssumption:
    """
    A security assumption the function makes.

    Trust assumptions are conditions that MUST hold for safe execution.
    Violations of critical assumptions often lead to exploits.

    Examples:
    - "Oracle price is fresh (< 1 hour old)"
    - "External contract is non-reentrant"
    - "Caller has sufficient balance"
    """

    id: str  # Unique identifier
    description: str  # Human-readable description
    category: str  # "oracle", "external_contract", "caller", "timing", "state"
    critical: bool  # If violated, is this exploitable?
    validation_check: Optional[str] = None  # Code that validates assumption

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TrustAssumption":
        """Deserialize from dict."""
        return cls(**data)


@dataclass
class InferredInvariant:
    """
    A property that should hold after function execution.

    Invariants are conditions that MUST remain true. Violations indicate
    business logic bugs.

    Examples:
    - "Total supply equals sum of all balances"
    - "Caller's balance decreases by withdrawn amount"
    - "No funds locked in contract"
    """

    id: str  # Unique identifier
    description: str  # Human-readable invariant
    scope: str  # "function", "transaction", "global", "temporal"
    formal: Optional[str] = None  # Formal specification (e.g., SMT-LIB)
    related_spec: Optional[str] = None  # Link to Domain KG spec ID

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InferredInvariant":
        """Deserialize from dict."""
        return cls(**data)


@dataclass
class FunctionIntent:
    """
    LLM-inferred business intent and security context for a function.

    This is THE KEY DATA STRUCTURE for semantic vulnerability detection.
    It captures what the function is SUPPOSED to do, enabling detection
    when actual behavior deviates from expected behavior.

    Example:
        A function named `emergencyWithdraw()` might have:
        - business_purpose: WITHDRAWAL
        - expected_trust_level: DEPOSITOR_ONLY
        - trust_assumptions: ["Caller has positive balance"]
        - inferred_invariants: ["Caller balance decreases", "Total supply unchanged"]

        If the actual code allows ANYONE to withdraw ANYONE's funds,
        this deviation from intent indicates a critical vulnerability.
    """

    # === BUSINESS PURPOSE ===

    business_purpose: BusinessPurpose  # What operation is this?
    purpose_confidence: float  # LLM confidence in purpose inference (0.0-1.0)
    purpose_reasoning: str  # Why LLM inferred this purpose

    # === AUTHORIZATION ===

    expected_trust_level: TrustLevel  # Who should be able to call this?
    authorized_callers: List[str] = field(default_factory=list)  # ["depositor", "owner", "anyone"]

    # === SECURITY ASSUMPTIONS ===

    trust_assumptions: List[TrustAssumption] = field(default_factory=list)  # Assumptions that must hold

    # === EXPECTED BEHAVIOR ===

    inferred_invariants: List[InferredInvariant] = field(default_factory=list)  # Properties that should hold

    # === DOMAIN KNOWLEDGE LINKS ===

    likely_specs: List[str] = field(default_factory=list)  # Spec IDs from Domain KG
    spec_confidence: Dict[str, float] = field(default_factory=dict)  # spec_id -> confidence

    # === RISK ASSESSMENT ===

    risk_notes: List[str] = field(default_factory=list)  # LLM-identified risks
    complexity_score: float = 0.0  # How complex/risky is this function (0.0-1.0)

    # === METADATA ===

    raw_llm_response: Optional[str] = None  # Original LLM output for debugging
    inferred_at: Optional[str] = None  # ISO timestamp of inference

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize to dict for JSON storage.

        Returns:
            Dict representation with enums converted to values
        """
        result = {
            "business_purpose": self.business_purpose.value,
            "purpose_confidence": self.purpose_confidence,
            "purpose_reasoning": self.purpose_reasoning,
            "expected_trust_level": self.expected_trust_level.value,
            "authorized_callers": self.authorized_callers[:],
            "trust_assumptions": [ta.to_dict() for ta in self.trust_assumptions],
            "inferred_invariants": [inv.to_dict() for inv in self.inferred_invariants],
            "likely_specs": self.likely_specs[:],
            "spec_confidence": dict(self.spec_confidence),
            "risk_notes": self.risk_notes[:],
            "complexity_score": self.complexity_score,
            "raw_llm_response": self.raw_llm_response,
            "inferred_at": self.inferred_at,
        }

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FunctionIntent":
        """
        Deserialize from dict.

        Args:
            data: Dict representation

        Returns:
            FunctionIntent instance
        """
        # Make a copy to avoid modifying the input dict
        data = dict(data)

        # Convert enum values back to enums
        if isinstance(data.get("business_purpose"), str):
            data["business_purpose"] = BusinessPurpose(data["business_purpose"])

        if isinstance(data.get("expected_trust_level"), str):
            data["expected_trust_level"] = TrustLevel(data["expected_trust_level"])

        # Reconstruct nested objects
        if "trust_assumptions" in data:
            data["trust_assumptions"] = [
                TrustAssumption.from_dict(ta) if isinstance(ta, dict) else ta
                for ta in data["trust_assumptions"]
            ]

        if "inferred_invariants" in data:
            data["inferred_invariants"] = [
                InferredInvariant.from_dict(inv) if isinstance(inv, dict) else inv
                for inv in data["inferred_invariants"]
            ]

        return cls(**data)

    def is_high_risk(self, threshold: float = 0.7) -> bool:
        """
        Check if this function is high-risk based on analysis.

        Args:
            threshold: Complexity score threshold

        Returns:
            True if high-risk
        """
        return (
            self.complexity_score >= threshold
            or len(self.risk_notes) >= 3
            or any(ta.critical for ta in self.trust_assumptions)
        )

    def has_authorization_requirements(self) -> bool:
        """
        Check if function has authorization requirements.

        Returns:
            True if not permissionless
        """
        return self.expected_trust_level != TrustLevel.PERMISSIONLESS

    def get_critical_assumptions(self) -> List[TrustAssumption]:
        """
        Get all critical trust assumptions.

        Returns:
            List of critical assumptions
        """
        return [ta for ta in self.trust_assumptions if ta.critical]

    def __str__(self) -> str:
        """Human-readable representation."""
        return (
            f"FunctionIntent("
            f"purpose={self.business_purpose.value}, "
            f"trust={self.expected_trust_level.value}, "
            f"confidence={self.purpose_confidence:.2f}, "
            f"assumptions={len(self.trust_assumptions)}, "
            f"invariants={len(self.inferred_invariants)})"
        )


# Helper functions for intent analysis

def get_all_business_purposes() -> List[BusinessPurpose]:
    """
    Get all business purpose enum values.

    Returns:
        List of all business purposes
    """
    return list(BusinessPurpose)


def get_all_trust_levels() -> List[TrustLevel]:
    """
    Get all trust level enum values.

    Returns:
        List of all trust levels
    """
    return list(TrustLevel)


def categorize_business_purpose(purpose: BusinessPurpose) -> str:
    """
    Get high-level category for business purpose.

    Args:
        purpose: Business purpose

    Returns:
        Category string
    """
    value_movement = {
        BusinessPurpose.WITHDRAWAL,
        BusinessPurpose.DEPOSIT,
        BusinessPurpose.TRANSFER,
        BusinessPurpose.CLAIM_REWARDS,
        BusinessPurpose.MINT,
        BusinessPurpose.BURN,
    }

    trading = {
        BusinessPurpose.SWAP,
        BusinessPurpose.ADD_LIQUIDITY,
        BusinessPurpose.REMOVE_LIQUIDITY,
    }

    governance = {
        BusinessPurpose.VOTE,
        BusinessPurpose.PROPOSE,
        BusinessPurpose.EXECUTE_PROPOSAL,
        BusinessPurpose.DELEGATE,
    }

    admin = {
        BusinessPurpose.SET_PARAMETER,
        BusinessPurpose.PAUSE,
        BusinessPurpose.UNPAUSE,
        BusinessPurpose.UPGRADE,
        BusinessPurpose.TRANSFER_OWNERSHIP,
        BusinessPurpose.GRANT_ROLE,
        BusinessPurpose.REVOKE_ROLE,
    }

    financial = {
        BusinessPurpose.BORROW,
        BusinessPurpose.REPAY,
        BusinessPurpose.LIQUIDATE,
        BusinessPurpose.ACCRUE_INTEREST,
    }

    if purpose in value_movement:
        return "value_movement"
    elif purpose in trading:
        return "trading"
    elif purpose in governance:
        return "governance"
    elif purpose in admin:
        return "administration"
    elif purpose in financial:
        return "lending_borrowing"
    else:
        return "other"
