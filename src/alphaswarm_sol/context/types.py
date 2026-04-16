"""Foundation types for the Protocol Context Pack system.

The Protocol Context Pack captures protocol-level context (roles, assumptions,
invariants, off-chain inputs) with confidence tracking for LLM-driven
vulnerability detection.

Types defined here:
- Confidence: Confidence levels for context fields (certain/inferred/unknown)
- ExpectationProvenance: Labels for expectation sources (declared/inferred/hypothesis)
- CausalEdgeType: Causal relationship types (causes/enables/amplifies/blocks)
- ConfidenceField: Generic wrapper for any value with confidence metadata
- Role: Protocol role with capabilities and trust assumptions
- Assumption: Protocol assumption with metadata
- Invariant: Both semi-formal and natural language invariants
- OffchainInput: Oracles, relayers, admins, UIs
- ValueFlow: Economic value movement tracking
- AcceptedRisk: Known/accepted behaviors to filter from findings
- CausalEdge: Causal relationship between nodes for exploitation reasoning

Usage:
    from alphaswarm_sol.context.types import (
        Confidence, ExpectationProvenance, CausalEdgeType,
        Role, Assumption, Invariant, OffchainInput, ValueFlow, AcceptedRisk,
        CausalEdge
    )

    role = Role(
        name="admin",
        capabilities=["pause", "upgrade"],
        trust_assumptions=["trusted to not rug"],
        confidence=Confidence.CERTAIN
    )

    assumption = Assumption(
        description="Oracle prices are accurate within 1%",
        category="price",
        affects_functions=["swap", "liquidate"],
        confidence=Confidence.INFERRED,
        source="whitepaper",
        provenance=ExpectationProvenance.DECLARED
    )

    # Causal edge for exploitation reasoning
    edge = CausalEdge(
        source_node="oracle.price_manipulation",
        target_node="vault.bad_liquidation",
        edge_type=CausalEdgeType.CAUSES,
        probability=0.8,
        evidence_refs=["price-oracle-vuln-001"]
    )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Confidence(Enum):
    """Confidence levels for context pack fields.

    Per 03-CONTEXT.md decision: explicit confidence levels on each field.

    Levels:
    - CERTAIN: Explicitly stated in official documentation
    - INFERRED: Derived from code analysis or community sources
    - UNKNOWN: Not determined, requires investigation

    Usage:
        from alphaswarm_sol.context.types import Confidence

        confidence = Confidence.CERTAIN
        confidence_str = confidence.value  # "certain"
        restored = Confidence.from_string("certain")
    """

    CERTAIN = "certain"
    INFERRED = "inferred"
    UNKNOWN = "unknown"

    @classmethod
    def from_string(cls, value: str) -> "Confidence":
        """Create Confidence from string, case-insensitive.

        Args:
            value: Confidence string ("certain", "INFERRED", etc.)

        Returns:
            Confidence enum value

        Raises:
            ValueError: If value is not a valid confidence level

        Usage:
            confidence = Confidence.from_string("inferred")  # Confidence.INFERRED
        """
        normalized = value.lower().strip()
        # Handle common aliases
        aliases = {
            "high": "certain",
            "medium": "inferred",
            "low": "unknown",
            "confirmed": "certain",
            "derived": "inferred",
        }
        normalized = aliases.get(normalized, normalized)
        return cls(normalized)

    def __lt__(self, other: "Confidence") -> bool:
        """Enable ordering: UNKNOWN < INFERRED < CERTAIN."""
        order = {Confidence.UNKNOWN: 0, Confidence.INFERRED: 1, Confidence.CERTAIN: 2}
        return order[self] < order[other]


class ExpectationProvenance(Enum):
    """Provenance labels for expectations (roles, assumptions, invariants).

    Per 05.11-CONTEXT.md: Expected behavior must record source + date and
    be labeled as declared, inferred, or hypothesis.

    Levels:
    - DECLARED: Explicit in official docs/governance or on-chain config
    - INFERRED: Deduced from code + common patterns + risk heuristics
    - HYPOTHESIS: Plausible but unsupported; requires probe to confirm

    Rules:
    - Misconfiguration findings require DECLARED or DECLARED + Code evidence
    - INFERRED expectations can emit warnings but not final findings
    - HYPOTHESIS triggers probes and context expansion, not findings

    Usage:
        from alphaswarm_sol.context.types import ExpectationProvenance

        provenance = ExpectationProvenance.DECLARED
        provenance_str = provenance.value  # "declared"
    """

    DECLARED = "declared"
    INFERRED = "inferred"
    HYPOTHESIS = "hypothesis"

    @classmethod
    def from_string(cls, value: str) -> "ExpectationProvenance":
        """Create ExpectationProvenance from string, case-insensitive.

        Args:
            value: Provenance string ("declared", "INFERRED", etc.)

        Returns:
            ExpectationProvenance enum value

        Raises:
            ValueError: If value is not a valid provenance level
        """
        normalized = value.lower().strip()
        # Handle common aliases
        aliases = {
            "official": "declared",
            "explicit": "declared",
            "derived": "inferred",
            "speculative": "hypothesis",
            "guess": "hypothesis",
        }
        normalized = aliases.get(normalized, normalized)
        return cls(normalized)

    def __lt__(self, other: "ExpectationProvenance") -> bool:
        """Enable ordering: HYPOTHESIS < INFERRED < DECLARED."""
        order = {
            ExpectationProvenance.HYPOTHESIS: 0,
            ExpectationProvenance.INFERRED: 1,
            ExpectationProvenance.DECLARED: 2,
        }
        return order[self] < order[other]


class CausalEdgeType(Enum):
    """Causal edge types for exploitation reasoning.

    Per 05.11-CONTEXT.md: Causal edges represent exploitation relationships
    between nodes in the economic context overlay.

    Types:
    - CAUSES: Direct causation (A causes B)
    - ENABLES: A enables B to happen (necessary but not sufficient)
    - AMPLIFIES: A increases severity/impact of B
    - BLOCKS: A prevents or mitigates B

    Usage:
        from alphaswarm_sol.context.types import CausalEdgeType

        edge_type = CausalEdgeType.CAUSES
        if edge_type == CausalEdgeType.BLOCKS:
            print("This is a mitigation")
    """

    CAUSES = "causes"
    ENABLES = "enables"
    AMPLIFIES = "amplifies"
    BLOCKS = "blocks"

    @classmethod
    def from_string(cls, value: str) -> "CausalEdgeType":
        """Create CausalEdgeType from string, case-insensitive.

        Args:
            value: Edge type string ("causes", "ENABLES", etc.)

        Returns:
            CausalEdgeType enum value

        Raises:
            ValueError: If value is not a valid edge type
        """
        normalized = value.lower().strip()
        # Handle common aliases
        aliases = {
            "leads_to": "causes",
            "triggers": "causes",
            "allows": "enables",
            "permits": "enables",
            "increases": "amplifies",
            "worsens": "amplifies",
            "prevents": "blocks",
            "mitigates": "blocks",
        }
        normalized = aliases.get(normalized, normalized)
        return cls(normalized)

    @property
    def is_negative(self) -> bool:
        """Whether this edge type represents a negative/blocking relationship."""
        return self == CausalEdgeType.BLOCKS

    @property
    def is_positive(self) -> bool:
        """Whether this edge type represents a positive/enabling relationship."""
        return self in (CausalEdgeType.CAUSES, CausalEdgeType.ENABLES, CausalEdgeType.AMPLIFIES)


@dataclass
class ConfidenceField:
    """Generic wrapper for any value with confidence metadata.

    Wraps any value with its confidence level and source attribution.
    Enables granular confidence tracking at the field level.

    Attributes:
        value: The actual value (any type)
        confidence: Confidence level
        source: Where this information came from
        source_tier: Reliability tier (1=official, 2=audit, 3=community)

    Usage:
        field = ConfidenceField(
            value="Only admin can pause",
            confidence=Confidence.CERTAIN,
            source="whitepaper",
            source_tier=1
        )

        # Access
        print(field.value)  # "Only admin can pause"
        print(field.is_certain)  # True
    """

    value: Any
    confidence: Confidence
    source: str
    source_tier: int = 1  # 1=official, 2=audit, 3=community

    def __post_init__(self) -> None:
        """Validate source tier."""
        if not 1 <= self.source_tier <= 3:
            raise ValueError(f"source_tier must be 1-3, got {self.source_tier}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dict representation suitable for YAML encoding
        """
        return {
            "value": self.value,
            "confidence": self.confidence.value,
            "source": self.source,
            "source_tier": self.source_tier,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConfidenceField":
        """Create ConfidenceField from dictionary.

        Args:
            data: Dictionary with field data

        Returns:
            ConfidenceField instance
        """
        confidence = data.get("confidence", "unknown")
        if isinstance(confidence, str):
            confidence = Confidence.from_string(confidence)
        elif isinstance(confidence, Confidence):
            pass
        else:
            confidence = Confidence.UNKNOWN

        return cls(
            value=data.get("value"),
            confidence=confidence,
            source=str(data.get("source", "")),
            source_tier=int(data.get("source_tier", 3)),
        )

    @property
    def is_certain(self) -> bool:
        """Whether this field has certain confidence."""
        return self.confidence == Confidence.CERTAIN

    @property
    def is_inferred(self) -> bool:
        """Whether this field was inferred."""
        return self.confidence == Confidence.INFERRED


@dataclass
class Role:
    """Protocol role with capabilities and trust assumptions.

    Per 03-CONTEXT.md: hybrid approach with capability-based roles
    plus trust assumptions. Supports nuanced reasoning about
    "maybe vulnerable" scenarios.

    Per 05.11-CONTEXT.md: Extended with provenance and source attribution
    for staleness tracking and evidence-gated reasoning.

    Attributes:
        name: Role identifier (e.g., "admin", "liquidator", "keeper")
        capabilities: What this role can do (mint, pause, upgrade, etc.)
        trust_assumptions: Trust assumptions about this role
        confidence: How confident we are about this role definition
        description: Optional human-readable description
        addresses: Optional known addresses for this role
        provenance: Expectation provenance (declared/inferred/hypothesis)
        source_id: Source identifier for this role definition
        source_date: Date of the source (ISO format)
        source_type: Type of source (docs, governance, on-chain, audit)
        expires_at: Optional TTL for staleness tracking

    Usage:
        role = Role(
            name="admin",
            capabilities=["pause", "upgrade", "set_fees"],
            trust_assumptions=[
                "Admin is trusted multisig",
                "Admin will not rug users"
            ],
            confidence=Confidence.CERTAIN,
            provenance=ExpectationProvenance.DECLARED,
            source_id="whitepaper-v1.2",
            source_date="2025-01-15"
        )

        # Serialize
        data = role.to_dict()

        # Deserialize
        restored = Role.from_dict(data)
    """

    name: str
    capabilities: List[str]
    trust_assumptions: List[str]
    confidence: Confidence
    description: str = ""
    addresses: List[str] = field(default_factory=list)
    # Provenance fields (05.11)
    provenance: Optional["ExpectationProvenance"] = None
    source_id: str = ""
    source_date: str = ""
    source_type: str = ""
    expires_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dict representation suitable for YAML encoding
        """
        result = {
            "name": self.name,
            "capabilities": self.capabilities,
            "trust_assumptions": self.trust_assumptions,
            "confidence": self.confidence.value,
            "description": self.description,
            "addresses": self.addresses,
        }
        # Include provenance fields if set
        if self.provenance:
            result["provenance"] = self.provenance.value
        if self.source_id:
            result["source_id"] = self.source_id
        if self.source_date:
            result["source_date"] = self.source_date
        if self.source_type:
            result["source_type"] = self.source_type
        if self.expires_at:
            result["expires_at"] = self.expires_at
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Role":
        """Create Role from dictionary.

        Args:
            data: Dictionary with role data

        Returns:
            Role instance
        """
        confidence = data.get("confidence", "unknown")
        if isinstance(confidence, str):
            confidence = Confidence.from_string(confidence)
        elif isinstance(confidence, Confidence):
            pass
        else:
            confidence = Confidence.UNKNOWN

        provenance = data.get("provenance")
        if isinstance(provenance, str):
            provenance = ExpectationProvenance.from_string(provenance)
        elif isinstance(provenance, ExpectationProvenance):
            pass
        else:
            provenance = None

        return cls(
            name=str(data.get("name", "")),
            capabilities=list(data.get("capabilities", [])),
            trust_assumptions=list(data.get("trust_assumptions", [])),
            confidence=confidence,
            description=str(data.get("description", "")),
            addresses=list(data.get("addresses", [])),
            provenance=provenance,
            source_id=str(data.get("source_id", "")),
            source_date=str(data.get("source_date", "")),
            source_type=str(data.get("source_type", "")),
            expires_at=data.get("expires_at"),
        )

    def has_capability(self, capability: str) -> bool:
        """Check if role has a specific capability.

        Args:
            capability: Capability to check (e.g., "pause")

        Returns:
            True if role has this capability
        """
        return capability.lower() in [c.lower() for c in self.capabilities]

    def is_stale(self, current_date: Optional[str] = None) -> bool:
        """Check if this role definition has expired based on TTL.

        Args:
            current_date: Current date in ISO format (defaults to today)

        Returns:
            True if the role has expired
        """
        if not self.expires_at:
            return False

        from datetime import datetime

        if current_date is None:
            current_date = datetime.utcnow().strftime("%Y-%m-%d")

        try:
            expires = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
            current = datetime.fromisoformat(current_date.replace("Z", "+00:00"))
            return current > expires
        except (ValueError, AttributeError):
            return False


@dataclass
class Assumption:
    """Protocol assumption with metadata.

    Per 03-CONTEXT.md: freeform tags for categorization,
    function-level granularity for affects_functions.

    Per 05.11-CONTEXT.md: Extended with provenance and source attribution
    for staleness tracking and evidence-gated reasoning.

    Attributes:
        description: The assumption description
        category: Assumption category (price, time, trust, economic, etc.)
        affects_functions: Functions this assumption affects
        confidence: How confident we are about this assumption
        source: Where this assumption came from
        tags: Additional freeform tags
        provenance: Expectation provenance (declared/inferred/hypothesis)
        source_id: Unique identifier for the source
        source_date: Date of the source (ISO format)
        source_type: Type of source (docs, governance, on-chain, audit)
        expires_at: Optional TTL for staleness tracking
        scope: Scope of this assumption (protocol-wide, contract-specific, function-specific)

    Usage:
        assumption = Assumption(
            description="Oracle prices are accurate within 1%",
            category="price",
            affects_functions=["swap", "liquidate", "borrow"],
            confidence=Confidence.INFERRED,
            source="whitepaper section 3.2",
            provenance=ExpectationProvenance.DECLARED,
            source_id="whitepaper-v1.2",
            source_date="2025-01-15",
            scope="protocol-wide"
        )

        # Check relevance
        if assumption.affects_function("liquidate"):
            print("Relevant to liquidation analysis")
    """

    description: str
    category: str
    affects_functions: List[str]
    confidence: Confidence
    source: str
    tags: List[str] = field(default_factory=list)
    # Provenance fields (05.11)
    provenance: Optional["ExpectationProvenance"] = None
    source_id: str = ""
    source_date: str = ""
    source_type: str = ""
    expires_at: Optional[str] = None
    scope: str = ""  # protocol-wide, contract-specific, function-specific

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dict representation suitable for YAML encoding
        """
        result = {
            "description": self.description,
            "category": self.category,
            "affects_functions": self.affects_functions,
            "confidence": self.confidence.value,
            "source": self.source,
            "tags": self.tags,
        }
        # Include provenance fields if set
        if self.provenance:
            result["provenance"] = self.provenance.value
        if self.source_id:
            result["source_id"] = self.source_id
        if self.source_date:
            result["source_date"] = self.source_date
        if self.source_type:
            result["source_type"] = self.source_type
        if self.expires_at:
            result["expires_at"] = self.expires_at
        if self.scope:
            result["scope"] = self.scope
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Assumption":
        """Create Assumption from dictionary.

        Args:
            data: Dictionary with assumption data

        Returns:
            Assumption instance
        """
        confidence = data.get("confidence", "unknown")
        if isinstance(confidence, str):
            confidence = Confidence.from_string(confidence)
        elif isinstance(confidence, Confidence):
            pass
        else:
            confidence = Confidence.UNKNOWN

        provenance = data.get("provenance")
        if isinstance(provenance, str):
            provenance = ExpectationProvenance.from_string(provenance)
        elif isinstance(provenance, ExpectationProvenance):
            pass
        else:
            provenance = None

        return cls(
            description=str(data.get("description", "")),
            category=str(data.get("category", "")),
            affects_functions=list(data.get("affects_functions", [])),
            confidence=confidence,
            source=str(data.get("source", "")),
            tags=list(data.get("tags", [])),
            provenance=provenance,
            source_id=str(data.get("source_id", "")),
            source_date=str(data.get("source_date", "")),
            source_type=str(data.get("source_type", "")),
            expires_at=data.get("expires_at"),
            scope=str(data.get("scope", "")),
        )

    def affects_function(self, function_name: str) -> bool:
        """Check if this assumption affects a specific function.

        Args:
            function_name: Function name to check

        Returns:
            True if this assumption affects the function
        """
        # Support both exact match and partial match (contract.function)
        fn_lower = function_name.lower()
        for affected in self.affects_functions:
            if affected.lower() == fn_lower or affected.lower().endswith(f".{fn_lower}"):
                return True
        return False

    def is_stale(self, current_date: Optional[str] = None) -> bool:
        """Check if this assumption has expired based on TTL.

        Args:
            current_date: Current date in ISO format (defaults to today)

        Returns:
            True if the assumption has expired
        """
        if not self.expires_at:
            return False

        from datetime import datetime

        if current_date is None:
            current_date = datetime.utcnow().strftime("%Y-%m-%d")

        try:
            expires = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
            current = datetime.fromisoformat(current_date.replace("Z", "+00:00"))
            return current > expires
        except (ValueError, AttributeError):
            return False

    def can_trigger_finding(self) -> bool:
        """Check if this assumption can trigger a misconfiguration finding.

        Per 05.11-CONTEXT.md: Only DECLARED provenance can emit findings.
        INFERRED emits warnings, HYPOTHESIS triggers probes.

        Returns:
            True if this assumption can trigger a finding
        """
        return self.provenance == ExpectationProvenance.DECLARED


@dataclass
class Invariant:
    """Protocol invariant with semi-formal and natural language representations.

    Per 03-CONTEXT.md: Both semi-formal AND natural language for each invariant.
    Semi-formal enables automated checking, natural language enables LLM reasoning.

    Per 05.11-CONTEXT.md: Extended with provenance and source attribution
    for staleness tracking and evidence-gated reasoning.

    Attributes:
        formal: Semi-formal representation (e.g., {what: 'totalSupply', must: 'lte', value: 'maxSupply'})
        natural_language: Human-readable description for LLM reasoning
        confidence: How confident we are about this invariant
        source: Where this invariant was documented/derived
        category: Optional category (supply, balance, access, economic)
        critical: Whether violating this invariant is critical
        provenance: Expectation provenance (declared/inferred/hypothesis)
        source_id: Unique identifier for the source
        source_date: Date of the source (ISO format)
        source_type: Type of source (docs, governance, on-chain, audit)
        expires_at: Optional TTL for staleness tracking

    Usage:
        invariant = Invariant(
            formal={"what": "totalSupply", "must": "lte", "value": "maxSupply"},
            natural_language="Total supply must never exceed max supply",
            confidence=Confidence.CERTAIN,
            source="ERC20 spec",
            category="supply",
            critical=True,
            provenance=ExpectationProvenance.DECLARED,
            source_id="erc20-spec-v1",
            source_date="2025-01-01"
        )

        # Check if this is about supply
        if invariant.is_supply_invariant():
            print("Supply-related invariant")
    """

    formal: Dict[str, Any]
    natural_language: str
    confidence: Confidence
    source: str
    category: str = ""
    critical: bool = False
    # Provenance fields (05.11)
    provenance: Optional["ExpectationProvenance"] = None
    source_id: str = ""
    source_date: str = ""
    source_type: str = ""
    expires_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dict representation suitable for YAML encoding
        """
        result = {
            "formal": self.formal,
            "natural_language": self.natural_language,
            "confidence": self.confidence.value,
            "source": self.source,
            "category": self.category,
            "critical": self.critical,
        }
        # Include provenance fields if set
        if self.provenance:
            result["provenance"] = self.provenance.value
        if self.source_id:
            result["source_id"] = self.source_id
        if self.source_date:
            result["source_date"] = self.source_date
        if self.source_type:
            result["source_type"] = self.source_type
        if self.expires_at:
            result["expires_at"] = self.expires_at
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Invariant":
        """Create Invariant from dictionary.

        Args:
            data: Dictionary with invariant data

        Returns:
            Invariant instance
        """
        confidence = data.get("confidence", "unknown")
        if isinstance(confidence, str):
            confidence = Confidence.from_string(confidence)
        elif isinstance(confidence, Confidence):
            pass
        else:
            confidence = Confidence.UNKNOWN

        provenance = data.get("provenance")
        if isinstance(provenance, str):
            provenance = ExpectationProvenance.from_string(provenance)
        elif isinstance(provenance, ExpectationProvenance):
            pass
        else:
            provenance = None

        return cls(
            formal=dict(data.get("formal", {})),
            natural_language=str(data.get("natural_language", "")),
            confidence=confidence,
            source=str(data.get("source", "")),
            category=str(data.get("category", "")),
            critical=bool(data.get("critical", False)),
            provenance=provenance,
            source_id=str(data.get("source_id", "")),
            source_date=str(data.get("source_date", "")),
            source_type=str(data.get("source_type", "")),
            expires_at=data.get("expires_at"),
        )

    def is_supply_invariant(self) -> bool:
        """Check if this is a supply-related invariant."""
        supply_keywords = ["supply", "mint", "burn", "total"]
        what = str(self.formal.get("what", "")).lower()
        return any(kw in what for kw in supply_keywords) or self.category == "supply"

    def is_balance_invariant(self) -> bool:
        """Check if this is a balance-related invariant."""
        balance_keywords = ["balance", "amount", "fund"]
        what = str(self.formal.get("what", "")).lower()
        return any(kw in what for kw in balance_keywords) or self.category == "balance"

    def is_stale(self, current_date: Optional[str] = None) -> bool:
        """Check if this invariant has expired based on TTL.

        Args:
            current_date: Current date in ISO format (defaults to today)

        Returns:
            True if the invariant has expired
        """
        if not self.expires_at:
            return False

        from datetime import datetime

        if current_date is None:
            current_date = datetime.utcnow().strftime("%Y-%m-%d")

        try:
            expires = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
            current = datetime.fromisoformat(current_date.replace("Z", "+00:00"))
            return current > expires
        except (ValueError, AttributeError):
            return False


@dataclass
class OffchainInput:
    """Off-chain input dependency (oracles, relayers, admins, UIs).

    Per 03-CONTEXT.md: Track external inputs that affect protocol security.
    Trust assumptions captured at the input level.

    Attributes:
        name: Input identifier (e.g., "Chainlink ETH/USD", "Gelato keeper")
        input_type: Type of input (oracle, relayer, admin, ui, keeper)
        description: What this input provides
        trust_assumptions: Trust assumptions about this input
        affects_functions: Functions that depend on this input
        confidence: How confident we are about this input
        endpoints: Optional API/contract endpoints

    Usage:
        oracle = OffchainInput(
            name="Chainlink ETH/USD",
            input_type="oracle",
            description="Price feed for ETH/USD",
            trust_assumptions=[
                "Oracle nodes are decentralized",
                "Prices are updated within heartbeat"
            ],
            affects_functions=["liquidate", "borrow", "repay"],
            confidence=Confidence.CERTAIN
        )
    """

    name: str
    input_type: str  # oracle, relayer, admin, ui, keeper
    description: str
    trust_assumptions: List[str]
    affects_functions: List[str]
    confidence: Confidence
    endpoints: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate input type."""
        valid_types = {"oracle", "relayer", "admin", "ui", "keeper", "bridge", "indexer"}
        if self.input_type.lower() not in valid_types:
            # Allow unknown types but warn
            pass

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dict representation suitable for YAML encoding
        """
        return {
            "name": self.name,
            "input_type": self.input_type,
            "description": self.description,
            "trust_assumptions": self.trust_assumptions,
            "affects_functions": self.affects_functions,
            "confidence": self.confidence.value,
            "endpoints": self.endpoints,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OffchainInput":
        """Create OffchainInput from dictionary.

        Args:
            data: Dictionary with input data

        Returns:
            OffchainInput instance
        """
        confidence = data.get("confidence", "unknown")
        if isinstance(confidence, str):
            confidence = Confidence.from_string(confidence)
        elif isinstance(confidence, Confidence):
            pass
        else:
            confidence = Confidence.UNKNOWN

        return cls(
            name=str(data.get("name", "")),
            input_type=str(data.get("input_type", "")),
            description=str(data.get("description", "")),
            trust_assumptions=list(data.get("trust_assumptions", [])),
            affects_functions=list(data.get("affects_functions", [])),
            confidence=confidence,
            endpoints=list(data.get("endpoints", [])),
        )

    def is_oracle(self) -> bool:
        """Check if this is an oracle input."""
        return self.input_type.lower() == "oracle"

    def affects_function(self, function_name: str) -> bool:
        """Check if this input affects a specific function."""
        fn_lower = function_name.lower()
        for affected in self.affects_functions:
            if affected.lower() == fn_lower or affected.lower().endswith(f".{fn_lower}"):
                return True
        return False


@dataclass
class ValueFlow:
    """Economic value movement tracking.

    Per 03-CONTEXT.md: Track how value flows through the protocol
    for economic analysis and attack surface mapping.

    Attributes:
        name: Flow identifier (e.g., "deposit", "liquidation_reward")
        from_role: Source role or "user" / "protocol"
        to_role: Destination role or "user" / "protocol"
        asset: Asset being transferred (ETH, USDC, native token)
        conditions: Conditions for this flow
        confidence: How confident we are about this flow

    Usage:
        flow = ValueFlow(
            name="liquidation_reward",
            from_role="protocol",
            to_role="liquidator",
            asset="ETH",
            conditions=["health_factor < 1", "debt > 0"],
            confidence=Confidence.CERTAIN
        )
    """

    name: str
    from_role: str
    to_role: str
    asset: str
    conditions: List[str]
    confidence: Confidence
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dict representation suitable for YAML encoding
        """
        return {
            "name": self.name,
            "from_role": self.from_role,
            "to_role": self.to_role,
            "asset": self.asset,
            "conditions": self.conditions,
            "confidence": self.confidence.value,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ValueFlow":
        """Create ValueFlow from dictionary.

        Args:
            data: Dictionary with flow data

        Returns:
            ValueFlow instance
        """
        confidence = data.get("confidence", "unknown")
        if isinstance(confidence, str):
            confidence = Confidence.from_string(confidence)
        elif isinstance(confidence, Confidence):
            pass
        else:
            confidence = Confidence.UNKNOWN

        return cls(
            name=str(data.get("name", "")),
            from_role=str(data.get("from_role", "")),
            to_role=str(data.get("to_role", "")),
            asset=str(data.get("asset", "")),
            conditions=list(data.get("conditions", [])),
            confidence=confidence,
            description=str(data.get("description", "")),
        )

    def involves_role(self, role_name: str) -> bool:
        """Check if this flow involves a specific role."""
        role_lower = role_name.lower()
        return self.from_role.lower() == role_lower or self.to_role.lower() == role_lower


@dataclass
class AcceptedRisk:
    """Known/accepted behavior to filter from findings.

    Per 03-CONTEXT.md: Auto-filter accepted risks from findings.
    Prevents known design decisions from being flagged as vulnerabilities.

    Attributes:
        description: What behavior is accepted
        reason: Why it's accepted
        affects_functions: Functions where this risk applies
        documented_in: Where this was documented
        severity: Maximum severity to filter (won't filter higher)
        patterns: Pattern IDs to exclude (optional)

    Usage:
        risk = AcceptedRisk(
            description="Admin can pause all transfers",
            reason="Emergency circuit breaker by design",
            affects_functions=["transfer", "transferFrom"],
            documented_in="audit_report_v1.pdf",
            severity="medium"
        )

        # Check if a finding should be filtered
        if risk.should_filter(finding):
            print("Finding matches accepted risk")
    """

    description: str
    reason: str
    affects_functions: List[str]
    documented_in: str
    severity: str = "medium"  # Max severity to filter
    patterns: List[str] = field(default_factory=list)  # Pattern IDs to exclude

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dict representation suitable for YAML encoding
        """
        return {
            "description": self.description,
            "reason": self.reason,
            "affects_functions": self.affects_functions,
            "documented_in": self.documented_in,
            "severity": self.severity,
            "patterns": self.patterns,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AcceptedRisk":
        """Create AcceptedRisk from dictionary.

        Args:
            data: Dictionary with risk data

        Returns:
            AcceptedRisk instance
        """
        return cls(
            description=str(data.get("description", "")),
            reason=str(data.get("reason", "")),
            affects_functions=list(data.get("affects_functions", [])),
            documented_in=str(data.get("documented_in", "")),
            severity=str(data.get("severity", "medium")),
            patterns=list(data.get("patterns", [])),
        )

    def affects_function(self, function_name: str) -> bool:
        """Check if this risk applies to a specific function."""
        if not self.affects_functions:
            return True  # Applies to all if no specific functions
        fn_lower = function_name.lower()
        for affected in self.affects_functions:
            if affected.lower() == fn_lower or affected.lower().endswith(f".{fn_lower}"):
                return True
        return False

    def matches_pattern(self, pattern_id: str) -> bool:
        """Check if this risk explicitly excludes a pattern."""
        if not self.patterns:
            return False
        return pattern_id.lower() in [p.lower() for p in self.patterns]


@dataclass
class CausalEdge:
    """Causal edge for exploitation reasoning in economic context.

    Per 05.11-CONTEXT.md: Represents causal relationships between nodes
    for attack path modeling and exploitation reasoning.

    Attributes:
        source_node: Source node ID (e.g., "oracle.price_manipulation")
        target_node: Target node ID (e.g., "vault.bad_liquidation")
        edge_type: Type of causal relationship (causes/enables/amplifies/blocks)
        probability: Probability estimate for this causal link (0.0-1.0)
        evidence_refs: References to evidence supporting this edge
        description: Human-readable description of the relationship
        confidence: Confidence level in this edge

    Usage:
        edge = CausalEdge(
            source_node="oracle.price_manipulation",
            target_node="vault.bad_liquidation",
            edge_type=CausalEdgeType.CAUSES,
            probability=0.8,
            evidence_refs=["price-oracle-vuln-001"],
            description="Manipulated oracle price causes incorrect liquidation"
        )

        if edge.edge_type.is_negative:
            print("This is a mitigation edge")
    """

    source_node: str
    target_node: str
    edge_type: CausalEdgeType
    probability: float = 0.5
    evidence_refs: List[str] = field(default_factory=list)
    description: str = ""
    confidence: Confidence = Confidence.INFERRED

    def __post_init__(self) -> None:
        """Validate probability range."""
        if not 0.0 <= self.probability <= 1.0:
            raise ValueError(f"probability must be 0.0-1.0, got {self.probability}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dict representation suitable for YAML encoding
        """
        return {
            "source_node": self.source_node,
            "target_node": self.target_node,
            "edge_type": self.edge_type.value,
            "probability": self.probability,
            "evidence_refs": self.evidence_refs,
            "description": self.description,
            "confidence": self.confidence.value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CausalEdge":
        """Create CausalEdge from dictionary.

        Args:
            data: Dictionary with edge data

        Returns:
            CausalEdge instance
        """
        edge_type = data.get("edge_type", "causes")
        if isinstance(edge_type, str):
            edge_type = CausalEdgeType.from_string(edge_type)
        elif isinstance(edge_type, CausalEdgeType):
            pass
        else:
            edge_type = CausalEdgeType.CAUSES

        confidence = data.get("confidence", "inferred")
        if isinstance(confidence, str):
            confidence = Confidence.from_string(confidence)
        elif isinstance(confidence, Confidence):
            pass
        else:
            confidence = Confidence.INFERRED

        return cls(
            source_node=str(data.get("source_node", "")),
            target_node=str(data.get("target_node", "")),
            edge_type=edge_type,
            probability=float(data.get("probability", 0.5)),
            evidence_refs=list(data.get("evidence_refs", [])),
            description=str(data.get("description", "")),
            confidence=confidence,
        )

    @property
    def is_blocking(self) -> bool:
        """Whether this edge represents a blocking/mitigation relationship."""
        return self.edge_type == CausalEdgeType.BLOCKS

    @property
    def is_high_probability(self) -> bool:
        """Whether this edge has high probability (>= 0.7)."""
        return self.probability >= 0.7


@dataclass
class SourceAttribution:
    """Source attribution for provenance tracking.

    Per 05.11-CONTEXT.md: Every fact needs source_id, source_date,
    and source_type for staleness and confidence tracking.

    Attributes:
        source_id: Unique identifier for the source (e.g., "whitepaper-v1.2")
        source_date: Date of the source (ISO format)
        source_type: Type of source (docs, governance, on-chain, audit, code)
        expires_at: Optional TTL - when this fact should be considered stale
    """

    source_id: str
    source_date: str  # ISO date format
    source_type: str  # docs, governance, on-chain, audit, code
    expires_at: Optional[str] = None  # ISO date format, optional TTL

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "source_id": self.source_id,
            "source_date": self.source_date,
            "source_type": self.source_type,
        }
        if self.expires_at:
            result["expires_at"] = self.expires_at
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SourceAttribution":
        """Create SourceAttribution from dictionary."""
        return cls(
            source_id=str(data.get("source_id", "")),
            source_date=str(data.get("source_date", "")),
            source_type=str(data.get("source_type", "")),
            expires_at=data.get("expires_at"),
        )

    def is_stale(self, current_date: Optional[str] = None) -> bool:
        """Check if this source has expired based on TTL.

        Args:
            current_date: Current date in ISO format (defaults to today)

        Returns:
            True if the source has expired
        """
        if not self.expires_at:
            return False

        from datetime import datetime

        if current_date is None:
            current_date = datetime.utcnow().strftime("%Y-%m-%d")

        try:
            expires = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
            current = datetime.fromisoformat(current_date.replace("Z", "+00:00"))
            return current > expires
        except (ValueError, AttributeError):
            return False


# Export all types
__all__ = [
    "Confidence",
    "ExpectationProvenance",
    "CausalEdgeType",
    "ConfidenceField",
    "Role",
    "Assumption",
    "Invariant",
    "OffchainInput",
    "ValueFlow",
    "AcceptedRisk",
    "CausalEdge",
    "SourceAttribution",
]
