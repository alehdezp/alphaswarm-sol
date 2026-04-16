"""
Invariant Miner

Discovers invariants from code patterns using static analysis.
Infers likely invariants that can then be verified.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Set, Callable
from datetime import datetime
import hashlib
import logging
import re

from .types import Invariant, InvariantType, InvariantStrength

logger = logging.getLogger(__name__)


@dataclass
class PatternTemplate:
    """A template for mining invariants."""
    template_id: str
    invariant_type: InvariantType
    name: str
    description: str

    # Pattern matching
    code_patterns: List[str]        # Regex patterns to match
    required_elements: List[str]    # Required code elements

    # Invariant generation
    predicate_template: str         # Template for predicate

    # Optional fields with defaults
    excluded_elements: List[str] = field(default_factory=list)
    variable_extraction: Dict[str, str] = field(default_factory=dict)  # How to extract vars

    # Confidence
    base_confidence: float = 0.7

    def matches(self, code: str, elements: Set[str]) -> bool:
        """Check if code matches this template."""
        # Check required elements
        for req in self.required_elements:
            if req not in elements:
                return False

        # Check excluded elements
        for exc in self.excluded_elements:
            if exc in elements:
                return False

        # Check code patterns
        for pattern in self.code_patterns:
            if re.search(pattern, code):
                return True

        return len(self.code_patterns) == 0  # No patterns = match on elements


@dataclass
class MiningConfig:
    """Configuration for invariant mining."""
    # Which invariant types to mine
    enabled_types: Set[InvariantType] = field(default_factory=lambda: set(InvariantType))

    # Confidence thresholds
    min_confidence: float = 0.5
    high_confidence_threshold: float = 0.8

    # Mining depth
    analyze_state_vars: bool = True
    analyze_functions: bool = True
    analyze_modifiers: bool = True
    analyze_events: bool = True

    # Limits
    max_invariants_per_function: int = 10
    max_total_invariants: int = 100


@dataclass
class MiningResult:
    """Result of invariant mining."""
    contract: str
    invariants: List[Invariant]
    mining_time_ms: int = 0
    patterns_checked: int = 0
    candidates_found: int = 0

    def get_by_type(self, inv_type: InvariantType) -> List[Invariant]:
        """Get invariants by type."""
        return [i for i in self.invariants if i.invariant_type == inv_type]

    def get_high_confidence(self, threshold: float = 0.8) -> List[Invariant]:
        """Get high confidence invariants."""
        return [i for i in self.invariants if i.confidence >= threshold]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contract": self.contract,
            "total_invariants": len(self.invariants),
            "by_type": {
                t.value: len(self.get_by_type(t))
                for t in InvariantType
                if self.get_by_type(t)
            },
            "high_confidence": len(self.get_high_confidence()),
            "mining_time_ms": self.mining_time_ms,
        }


class InvariantMiner:
    """
    Discovers invariants from code patterns.

    Uses static analysis to infer likely invariants:
    1. Identifies common patterns (balance tracking, ownership, etc.)
    2. Generates candidate invariants from templates
    3. Scores candidates by confidence
    """

    # Built-in pattern templates
    DEFAULT_TEMPLATES = [
        PatternTemplate(
            template_id="balance_conservation",
            invariant_type=InvariantType.BALANCE_CONSERVATION,
            name="Balance Conservation",
            description="Sum of balances equals total supply",
            code_patterns=[r"totalSupply", r"balanceOf", r"_balances\["],
            required_elements={"mapping", "uint256"},
            predicate_template="sum(balances) == totalSupply",
        ),
        PatternTemplate(
            template_id="balance_non_negative",
            invariant_type=InvariantType.BALANCE_NON_NEGATIVE,
            name="Non-negative Balance",
            description="Balances cannot be negative",
            code_patterns=[r"_balances\[", r"balanceOf"],
            required_elements={"mapping", "uint256"},
            predicate_template="balances[addr] >= 0",
            base_confidence=0.95,  # Very likely for uint
        ),
        PatternTemplate(
            template_id="owner_non_zero",
            invariant_type=InvariantType.OWNER_NON_ZERO,
            name="Owner Non-Zero",
            description="Owner address is never zero",
            code_patterns=[r"owner\s*!=\s*address\(0\)", r"_owner"],
            required_elements={"owner", "address"},
            predicate_template="owner != address(0)",
        ),
        PatternTemplate(
            template_id="single_owner",
            invariant_type=InvariantType.SINGLE_OWNER,
            name="Single Owner",
            description="Only one owner at a time",
            code_patterns=[r"address\s+(private|public|internal)?\s*owner"],
            required_elements={"owner"},
            excluded_elements={"owners", "mapping"},
            predicate_template="count(owners) == 1",
        ),
        PatternTemplate(
            template_id="reentrancy_lock",
            invariant_type=InvariantType.LOCK_HELD,
            name="Reentrancy Lock",
            description="Lock held during external calls",
            code_patterns=[r"nonReentrant", r"_status\s*==\s*_NOT_ENTERED"],
            required_elements={"modifier", "bool"},
            predicate_template="_locked == true during external_call",
        ),
        PatternTemplate(
            template_id="monotonic_nonce",
            invariant_type=InvariantType.MONOTONIC_INCREASE,
            name="Monotonic Nonce",
            description="Nonce only increases",
            code_patterns=[r"nonce\s*\+\+", r"nonce\s*\+=\s*1"],
            required_elements={"nonce", "uint"},
            predicate_template="nonce' >= nonce",
        ),
        PatternTemplate(
            template_id="timestamp_order",
            invariant_type=InvariantType.TIMESTAMP_ORDERED,
            name="Timestamp Ordering",
            description="Timestamps always increase",
            code_patterns=[r"block\.timestamp", r"lastUpdate"],
            required_elements={"timestamp", "uint"},
            predicate_template="newTimestamp >= lastTimestamp",
        ),
        PatternTemplate(
            template_id="admin_only",
            invariant_type=InvariantType.ADMIN_PRIVILEGED,
            name="Admin Only Functions",
            description="Certain functions require admin",
            code_patterns=[r"onlyOwner", r"onlyAdmin", r"require\(.*owner"],
            required_elements={"modifier"},
            predicate_template="msg.sender == admin for privileged_functions",
        ),
    ]

    def __init__(self, config: Optional[MiningConfig] = None):
        self.config = config or MiningConfig()
        self.templates: List[PatternTemplate] = self.DEFAULT_TEMPLATES.copy()
        self._invariant_counter = 0

    def add_template(self, template: PatternTemplate):
        """Add a custom pattern template."""
        self.templates.append(template)

    def _generate_id(self, prefix: str) -> str:
        """Generate unique invariant ID."""
        self._invariant_counter += 1
        return f"{prefix}-{self._invariant_counter:04d}"

    def mine(
        self,
        contract_name: str,
        code: str,
        state_vars: Optional[List[Dict[str, Any]]] = None,
        functions: Optional[List[Dict[str, Any]]] = None,
    ) -> MiningResult:
        """
        Mine invariants from contract code.

        Args:
            contract_name: Name of the contract
            code: Solidity source code
            state_vars: List of state variable info
            functions: List of function info
        """
        start_time = datetime.now()
        invariants: List[Invariant] = []
        patterns_checked = 0

        # Extract code elements
        elements = self._extract_elements(code, state_vars, functions)

        # Try each template
        for template in self.templates:
            if template.invariant_type not in self.config.enabled_types:
                continue

            patterns_checked += 1

            if template.matches(code, elements):
                # Generate invariant from template
                inv = self._generate_invariant(template, contract_name, elements)
                if inv and inv.confidence >= self.config.min_confidence:
                    invariants.append(inv)

                    if len(invariants) >= self.config.max_total_invariants:
                        break

        # Mine additional invariants from state variables
        if self.config.analyze_state_vars and state_vars:
            var_invariants = self._mine_from_state_vars(contract_name, state_vars)
            invariants.extend(var_invariants)

        # Mine from function signatures
        if self.config.analyze_functions and functions:
            func_invariants = self._mine_from_functions(contract_name, functions)
            invariants.extend(func_invariants)

        # Deduplicate
        invariants = self._deduplicate(invariants)

        elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        return MiningResult(
            contract=contract_name,
            invariants=invariants,
            mining_time_ms=elapsed_ms,
            patterns_checked=patterns_checked,
            candidates_found=len(invariants),
        )

    def _extract_elements(
        self,
        code: str,
        state_vars: Optional[List[Dict]] = None,
        functions: Optional[List[Dict]] = None,
    ) -> Set[str]:
        """Extract code elements for pattern matching."""
        elements = set()

        # From code patterns
        if "mapping" in code:
            elements.add("mapping")
        if "uint256" in code or "uint" in code:
            elements.add("uint256")
            elements.add("uint")
        if "address" in code:
            elements.add("address")
        if "owner" in code.lower():
            elements.add("owner")
        if "modifier" in code:
            elements.add("modifier")
        if "bool" in code:
            elements.add("bool")
        if "nonce" in code.lower():
            elements.add("nonce")
        if "timestamp" in code.lower():
            elements.add("timestamp")

        # From state vars
        if state_vars:
            for var in state_vars:
                var_name = var.get("name", "").lower()
                var_type = var.get("type", "")
                elements.add(var_name)
                if "uint" in var_type:
                    elements.add("uint")
                    elements.add("uint256")
                if "address" in var_type:
                    elements.add("address")
                if "mapping" in var_type:
                    elements.add("mapping")

        return elements

    def _generate_invariant(
        self,
        template: PatternTemplate,
        contract: str,
        elements: Set[str],
    ) -> Optional[Invariant]:
        """Generate invariant from template."""
        return Invariant(
            invariant_id=self._generate_id("INV"),
            invariant_type=template.invariant_type,
            name=template.name,
            description=template.description,
            predicate=template.predicate_template,
            variables=list(template.variable_extraction.keys()) or list(elements)[:3],
            contract=contract,
            strength=InvariantStrength.CANDIDATE,
            confidence=template.base_confidence,
            discovered_by="pattern_mining",
        )

    def _mine_from_state_vars(
        self,
        contract: str,
        state_vars: List[Dict[str, Any]],
    ) -> List[Invariant]:
        """Mine invariants from state variable analysis."""
        invariants = []

        for var in state_vars:
            var_name = var.get("name", "")
            var_type = var.get("type", "")
            visibility = var.get("visibility", "internal")

            # Non-negative for uint
            if "uint" in var_type and not var_type.startswith("int"):
                inv = Invariant(
                    invariant_id=self._generate_id("INV"),
                    invariant_type=InvariantType.BALANCE_NON_NEGATIVE,
                    name=f"Non-negative {var_name}",
                    description=f"{var_name} is always non-negative (uint)",
                    predicate=f"{var_name} >= 0",
                    variables=[var_name],
                    contract=contract,
                    strength=InvariantStrength.LIKELY,
                    confidence=0.99,  # uint is always >= 0
                    discovered_by="type_analysis",
                )
                invariants.append(inv)

            # Owner-related
            if "owner" in var_name.lower() and "address" in var_type:
                inv = Invariant(
                    invariant_id=self._generate_id("INV"),
                    invariant_type=InvariantType.OWNER_NON_ZERO,
                    name=f"Non-zero {var_name}",
                    description=f"{var_name} should not be zero address",
                    predicate=f"{var_name} != address(0)",
                    variables=[var_name],
                    contract=contract,
                    strength=InvariantStrength.CANDIDATE,
                    confidence=0.7,
                    discovered_by="naming_analysis",
                )
                invariants.append(inv)

        return invariants

    def _mine_from_functions(
        self,
        contract: str,
        functions: List[Dict[str, Any]],
    ) -> List[Invariant]:
        """Mine invariants from function analysis."""
        invariants = []

        for func in functions:
            func_name = func.get("name", "")
            modifiers = func.get("modifiers", [])
            visibility = func.get("visibility", "internal")

            # Access control from modifiers
            access_modifiers = {"onlyOwner", "onlyAdmin", "onlyRole", "onlyAuthorized"}
            for mod in modifiers:
                if mod in access_modifiers or "only" in mod.lower():
                    inv = Invariant(
                        invariant_id=self._generate_id("INV"),
                        invariant_type=InvariantType.PERMISSION_REQUIRED,
                        name=f"Permission for {func_name}",
                        description=f"{func_name} requires {mod} permission",
                        predicate=f"hasPermission(msg.sender) for {func_name}",
                        variables=["msg.sender"],
                        contract=contract,
                        functions=[func_name],
                        strength=InvariantStrength.LIKELY,
                        confidence=0.9,
                        discovered_by="modifier_analysis",
                    )
                    invariants.append(inv)

            # Reentrancy guard
            if "nonReentrant" in modifiers:
                inv = Invariant(
                    invariant_id=self._generate_id("INV"),
                    invariant_type=InvariantType.LOCK_HELD,
                    name=f"Reentrancy guard on {func_name}",
                    description=f"{func_name} is protected by reentrancy guard",
                    predicate=f"_locked == true during {func_name}",
                    variables=["_locked"],
                    contract=contract,
                    functions=[func_name],
                    strength=InvariantStrength.PROVEN,
                    confidence=0.95,
                    discovered_by="modifier_analysis",
                )
                invariants.append(inv)

        return invariants

    def _deduplicate(self, invariants: List[Invariant]) -> List[Invariant]:
        """Remove duplicate invariants."""
        seen = set()
        unique = []

        for inv in invariants:
            key = (inv.invariant_type, inv.predicate, inv.contract)
            if key not in seen:
                seen.add(key)
                unique.append(inv)

        return unique

    def mine_from_kg(
        self,
        contract_name: str,
        kg_data: Dict[str, Any],
    ) -> MiningResult:
        """
        Mine invariants from knowledge graph data.

        Args:
            contract_name: Contract name
            kg_data: Knowledge graph data with nodes and properties
        """
        start_time = datetime.now()
        invariants = []

        # Extract relevant info from KG
        functions = kg_data.get("functions", [])
        state_vars = kg_data.get("state_variables", [])

        for func in functions:
            props = func.get("properties", {})

            # Check for reentrancy guard
            if props.get("has_reentrancy_guard"):
                inv = Invariant(
                    invariant_id=self._generate_id("INV"),
                    invariant_type=InvariantType.LOCK_HELD,
                    name=f"Reentrancy protected: {func.get('name')}",
                    description="Function has reentrancy guard",
                    predicate="_locked during execution",
                    variables=["_locked"],
                    contract=contract_name,
                    functions=[func.get("name", "")],
                    strength=InvariantStrength.PROVEN,
                    confidence=0.95,
                    discovered_by="kg_analysis",
                )
                invariants.append(inv)

            # Check for access control
            if props.get("has_access_gate"):
                inv = Invariant(
                    invariant_id=self._generate_id("INV"),
                    invariant_type=InvariantType.PERMISSION_REQUIRED,
                    name=f"Access controlled: {func.get('name')}",
                    description="Function has access control",
                    predicate="authorized(msg.sender)",
                    variables=["msg.sender"],
                    contract=contract_name,
                    functions=[func.get("name", "")],
                    strength=InvariantStrength.LIKELY,
                    confidence=0.85,
                    discovered_by="kg_analysis",
                )
                invariants.append(inv)

        elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        return MiningResult(
            contract=contract_name,
            invariants=invariants,
            mining_time_ms=elapsed_ms,
            patterns_checked=len(functions),
            candidates_found=len(invariants),
        )

    def get_statistics(self) -> Dict[str, Any]:
        """Get miner statistics."""
        return {
            "templates": len(self.templates),
            "enabled_types": len(self.config.enabled_types),
            "invariants_generated": self._invariant_counter,
        }
