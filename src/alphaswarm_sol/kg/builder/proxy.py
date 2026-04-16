"""Proxy pattern detection and resolution for VKG Builder.

This module provides comprehensive proxy pattern detection including:
- EIP-1967 Transparent Proxy
- UUPS (Universal Upgradeable Proxy Standard)
- EIP-2535 Diamond/Multi-facet Proxy
- Beacon Proxy
- EIP-1167 Minimal Proxy (Clone)

Resolution is best-effort: returns ProxyInfo with confidence and notes,
never raises on resolution failure. Unresolved proxies are flagged with
warnings but don't fail the build.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from alphaswarm_sol.kg.builder.types import (
    CallConfidence,
    EIP1967_ADMIN_SLOT,
    EIP1967_BEACON_SLOT,
    EIP1967_IMPLEMENTATION_SLOT,
    ProxyInfo,
    ProxyPattern,
)

if TYPE_CHECKING:
    from alphaswarm_sol.kg.builder.context import BuildContext


# -----------------------------------------------------------------------------
# Known Proxy Base Contracts
# -----------------------------------------------------------------------------

TRANSPARENT_PROXY_BASES: set[str] = {
    # OpenZeppelin
    "TransparentUpgradeableProxy",
    "ERC1967Proxy",
    "Proxy",
    # Hardhat
    "AdminUpgradeabilityProxy",
    "UpgradeabilityProxy",
    # Common patterns
    "TransparentProxy",
    "ERC1967",
}

UUPS_BASES: set[str] = {
    # OpenZeppelin
    "UUPSUpgradeable",
    "ERC1967Upgrade",
    # Common patterns
    "UUPSProxy",
    "UUPSUpgradeableProxy",
    "UUPSImplementation",
}

DIAMOND_BASES: set[str] = {
    # EIP-2535
    "Diamond",
    "DiamondCutFacet",
    "DiamondLoupeFacet",
    "DiamondProxy",
    # Common variations
    "DiamondBase",
    "DiamondStorage",
    "LibDiamond",
}

BEACON_BASES: set[str] = {
    # OpenZeppelin
    "BeaconProxy",
    "UpgradeableBeacon",
    "IBeacon",
    # Common patterns
    "Beacon",
    "ProxyBeacon",
}

MINIMAL_PROXY_BASES: set[str] = {
    # EIP-1167
    "Clones",
    "CloneFactory",
    "MinimalProxy",
    # Common patterns
    "Clone",
    "ProxyClone",
}

# All proxy base contracts combined for quick lookup
ALL_PROXY_BASES: set[str] = (
    TRANSPARENT_PROXY_BASES
    | UUPS_BASES
    | DIAMOND_BASES
    | BEACON_BASES
    | MINIMAL_PROXY_BASES
)

# Diamond-specific function signatures
DIAMOND_SIGNATURES: set[str] = {
    "diamondCut",
    "facetAddresses",
    "facetFunctionSelectors",
    "facetAddress",
    "facets",
}

# UUPS-specific function signatures
UUPS_SIGNATURES: set[str] = {
    "_authorizeUpgrade",
    "upgradeTo",
    "upgradeToAndCall",
    "proxiableUUID",
}

# Name patterns that suggest proxy
PROXY_NAME_PATTERNS: list[str] = [
    "Proxy",
    "proxy",
    "Upgradeable",
    "upgradeable",
    "Beacon",
    "Diamond",
    "Facet",
]


# -----------------------------------------------------------------------------
# ProxyResolver Class
# -----------------------------------------------------------------------------


class ProxyResolver:
    """Comprehensive proxy pattern detection and resolution.

    Detects proxy patterns through multiple strategies:
    1. Slither's built-in proxy detection
    2. Inheritance from known proxy base contracts
    3. Diamond-specific function signatures
    4. EIP-1967 storage slot references in source
    5. Name heuristics (lowest confidence)

    Resolution is best-effort: returns ProxyInfo with confidence
    and notes, never raises on resolution failure.

    Example:
        >>> resolver = ProxyResolver(ctx)
        >>> info = resolver.resolve(contract)
        >>> if info.is_proxy:
        ...     print(f"Detected {info.pattern.value} proxy")
    """

    def __init__(self, ctx: BuildContext | None = None) -> None:
        """Initialize the ProxyResolver.

        Args:
            ctx: Optional BuildContext for warnings and logging.
        """
        self.ctx = ctx
        self._source_cache: dict[str, str] = {}

    def resolve(self, contract: Any) -> ProxyInfo:
        """Resolve proxy pattern for a contract.

        Attempts detection through multiple strategies in order
        of confidence, returning the highest-confidence result.

        Args:
            contract: Slither contract object.

        Returns:
            ProxyInfo with detection results and confidence.
        """
        contract_name = getattr(contract, "name", str(contract))
        evidence: list[str] = []
        resolution_notes: list[str] = []

        # Strategy 1: Check Slither's built-in proxy detection
        slither_proxy = self._is_slither_proxy(contract)
        if slither_proxy:
            evidence.append("Slither is_proxy=True")

        # Strategy 2: Check inheritance from known proxy bases
        detected_pattern, inheritance_evidence = self._detect_from_inheritance(contract)
        evidence.extend(inheritance_evidence)

        # Strategy 3: Check for Diamond-specific functions
        if detected_pattern == ProxyPattern.NONE or detected_pattern == ProxyPattern.UNKNOWN:
            is_diamond, diamond_evidence = self._is_diamond(contract)
            if is_diamond:
                detected_pattern = ProxyPattern.DIAMOND
                evidence.extend(diamond_evidence)

        # Strategy 4: Check for EIP-1967 slot references in source
        if detected_pattern == ProxyPattern.NONE or detected_pattern == ProxyPattern.UNKNOWN:
            has_slots, slot_pattern, slot_evidence = self._has_eip1967_slots(contract)
            if has_slots:
                if detected_pattern == ProxyPattern.NONE:
                    detected_pattern = slot_pattern
                evidence.extend(slot_evidence)

        # Strategy 5: Check UUPS-specific functions
        if detected_pattern == ProxyPattern.NONE or detected_pattern == ProxyPattern.UNKNOWN:
            is_uups, uups_evidence = self._is_uups(contract)
            if is_uups:
                detected_pattern = ProxyPattern.UUPS
                evidence.extend(uups_evidence)

        # Strategy 6: Name heuristics (lowest confidence)
        if detected_pattern == ProxyPattern.NONE:
            name_suggests, name_evidence = self._name_suggests_proxy(contract_name)
            if name_suggests:
                detected_pattern = ProxyPattern.UNKNOWN
                evidence.extend(name_evidence)
                resolution_notes.append("Detected by name heuristics only")

        # Determine if this is actually a proxy
        is_proxy = detected_pattern != ProxyPattern.NONE
        if slither_proxy and detected_pattern == ProxyPattern.NONE:
            is_proxy = True
            detected_pattern = ProxyPattern.UNKNOWN
            resolution_notes.append("Slither flagged as proxy but pattern unclear")

        # Calculate confidence
        confidence = self._calculate_confidence(
            detected_pattern, evidence, slither_proxy
        )

        # Create base ProxyInfo
        info = ProxyInfo(
            is_proxy=is_proxy,
            pattern=detected_pattern,
            confidence=confidence,
            evidence=evidence,
            resolution_notes=resolution_notes,
        )

        # Attempt pattern-specific resolution
        if is_proxy:
            info = self._resolve_pattern(contract, info)

        # Add warning for unresolved proxy
        if is_proxy and confidence == "LOW" and self.ctx:
            self.ctx.add_warning(
                f"Proxy '{contract_name}' detected but resolution uncertain: "
                f"{', '.join(resolution_notes) if resolution_notes else 'limited evidence'}"
            )

        return info

    def _is_slither_proxy(self, contract: Any) -> bool:
        """Check if Slither detected this as a proxy.

        Args:
            contract: Slither contract object.

        Returns:
            True if Slither's is_proxy flag is set.
        """
        try:
            return bool(getattr(contract, "is_proxy", False))
        except Exception:
            return False

    def _detect_from_inheritance(
        self, contract: Any
    ) -> tuple[ProxyPattern, list[str]]:
        """Detect proxy pattern from inheritance chain.

        Args:
            contract: Slither contract object.

        Returns:
            Tuple of (detected pattern, evidence list).
        """
        pattern = ProxyPattern.NONE
        evidence: list[str] = []

        try:
            inheritance = getattr(contract, "inheritance", [])
            inherited_names = {getattr(c, "name", "") for c in inheritance}
            inherited_names.add(getattr(contract, "name", ""))

            # Check each pattern category
            if inherited_names & DIAMOND_BASES:
                pattern = ProxyPattern.DIAMOND
                matched = inherited_names & DIAMOND_BASES
                evidence.append(f"Inherits from Diamond base: {matched}")

            elif inherited_names & UUPS_BASES:
                pattern = ProxyPattern.UUPS
                matched = inherited_names & UUPS_BASES
                evidence.append(f"Inherits from UUPS base: {matched}")

            elif inherited_names & BEACON_BASES:
                pattern = ProxyPattern.BEACON
                matched = inherited_names & BEACON_BASES
                evidence.append(f"Inherits from Beacon base: {matched}")

            elif inherited_names & TRANSPARENT_PROXY_BASES:
                pattern = ProxyPattern.TRANSPARENT
                matched = inherited_names & TRANSPARENT_PROXY_BASES
                evidence.append(f"Inherits from Transparent proxy base: {matched}")

            elif inherited_names & MINIMAL_PROXY_BASES:
                pattern = ProxyPattern.MINIMAL
                matched = inherited_names & MINIMAL_PROXY_BASES
                evidence.append(f"Inherits from Minimal proxy base: {matched}")

        except Exception as e:
            if self.ctx:
                self.ctx.add_warning(f"Error checking inheritance: {e}")

        return pattern, evidence

    def _is_diamond(self, contract: Any) -> tuple[bool, list[str]]:
        """Check if contract is a Diamond proxy.

        Looks for Diamond-specific function signatures.

        Args:
            contract: Slither contract object.

        Returns:
            Tuple of (is_diamond, evidence list).
        """
        evidence: list[str] = []
        found_functions: set[str] = set()

        try:
            functions = getattr(contract, "functions", [])
            for func in functions:
                func_name = getattr(func, "name", "")
                if func_name in DIAMOND_SIGNATURES:
                    found_functions.add(func_name)

            # Diamond requires at least diamondCut or facetAddresses
            key_functions = {"diamondCut", "facetAddresses"}
            if found_functions & key_functions:
                evidence.append(f"Diamond functions found: {found_functions}")
                return True, evidence

        except Exception as e:
            if self.ctx:
                self.ctx.add_warning(f"Error checking Diamond functions: {e}")

        return False, evidence

    def _is_uups(self, contract: Any) -> tuple[bool, list[str]]:
        """Check if contract is a UUPS implementation.

        Looks for UUPS-specific function signatures.

        Args:
            contract: Slither contract object.

        Returns:
            Tuple of (is_uups, evidence list).
        """
        evidence: list[str] = []
        found_functions: set[str] = set()

        try:
            functions = getattr(contract, "functions", [])
            for func in functions:
                func_name = getattr(func, "name", "")
                if func_name in UUPS_SIGNATURES:
                    found_functions.add(func_name)

            # UUPS requires _authorizeUpgrade or proxiableUUID
            key_functions = {"_authorizeUpgrade", "proxiableUUID"}
            if found_functions & key_functions:
                evidence.append(f"UUPS functions found: {found_functions}")
                return True, evidence

        except Exception as e:
            if self.ctx:
                self.ctx.add_warning(f"Error checking UUPS functions: {e}")

        return False, evidence

    def _has_eip1967_slots(
        self, contract: Any
    ) -> tuple[bool, ProxyPattern, list[str]]:
        """Check if contract references EIP-1967 storage slots.

        Searches source code for EIP-1967 slot constants.

        Args:
            contract: Slither contract object.

        Returns:
            Tuple of (has_slots, detected_pattern, evidence list).
        """
        evidence: list[str] = []
        pattern = ProxyPattern.NONE

        try:
            # Get source code
            source = self._get_contract_source(contract)
            if not source:
                return False, pattern, evidence

            # Check for slot constants
            has_impl_slot = EIP1967_IMPLEMENTATION_SLOT[2:] in source  # Remove 0x
            has_admin_slot = EIP1967_ADMIN_SLOT[2:] in source
            has_beacon_slot = EIP1967_BEACON_SLOT[2:] in source

            if has_beacon_slot:
                pattern = ProxyPattern.BEACON
                evidence.append("EIP-1967 beacon slot constant found")

            if has_impl_slot:
                if pattern == ProxyPattern.NONE:
                    pattern = ProxyPattern.TRANSPARENT
                evidence.append("EIP-1967 implementation slot constant found")

            if has_admin_slot:
                evidence.append("EIP-1967 admin slot constant found")

            return bool(evidence), pattern, evidence

        except Exception as e:
            if self.ctx:
                self.ctx.add_warning(f"Error checking EIP-1967 slots: {e}")

        return False, pattern, evidence

    def _name_suggests_proxy(self, name: str) -> tuple[bool, list[str]]:
        """Check if contract name suggests a proxy pattern.

        This is the lowest-confidence detection method.

        Args:
            name: Contract name.

        Returns:
            Tuple of (suggests_proxy, evidence list).
        """
        evidence: list[str] = []

        for pattern in PROXY_NAME_PATTERNS:
            if pattern in name:
                evidence.append(f"Name contains '{pattern}'")
                return True, evidence

        return False, evidence

    def _calculate_confidence(
        self,
        pattern: ProxyPattern,
        evidence: list[str],
        slither_proxy: bool,
    ) -> CallConfidence:
        """Calculate confidence level for the detection.

        Args:
            pattern: Detected proxy pattern.
            evidence: List of evidence strings.
            slither_proxy: Whether Slither flagged as proxy.

        Returns:
            Confidence level (HIGH, MEDIUM, or LOW).
        """
        if pattern == ProxyPattern.NONE:
            return "LOW"

        # Multiple strong indicators = HIGH confidence
        strong_indicators = sum(
            1
            for e in evidence
            if any(
                keyword in e.lower()
                for keyword in ["inherits", "diamond functions", "uups functions"]
            )
        )

        if strong_indicators >= 1 and slither_proxy:
            return "HIGH"
        elif strong_indicators >= 1 or (len(evidence) >= 2 and slither_proxy):
            return "HIGH"
        elif slither_proxy or len(evidence) >= 2:
            return "MEDIUM"
        else:
            return "LOW"

    def _resolve_pattern(self, contract: Any, info: ProxyInfo) -> ProxyInfo:
        """Attempt pattern-specific resolution.

        Fills in additional ProxyInfo fields based on detected pattern.

        Args:
            contract: Slither contract object.
            info: ProxyInfo with basic detection results.

        Returns:
            Enhanced ProxyInfo with resolution details.
        """
        if info.pattern == ProxyPattern.TRANSPARENT:
            return self._resolve_transparent(contract, info)
        elif info.pattern == ProxyPattern.UUPS:
            return self._resolve_uups(contract, info)
        elif info.pattern == ProxyPattern.DIAMOND:
            return self._resolve_diamond(contract, info)
        elif info.pattern == ProxyPattern.BEACON:
            return self._resolve_beacon(contract, info)
        elif info.pattern == ProxyPattern.MINIMAL:
            return self._resolve_minimal(contract, info)
        else:
            return self._heuristic_resolution(contract, info)

    def _resolve_transparent(self, contract: Any, info: ProxyInfo) -> ProxyInfo:
        """Resolve Transparent proxy details.

        Args:
            contract: Slither contract object.
            info: ProxyInfo to enhance.

        Returns:
            Enhanced ProxyInfo.
        """
        info.implementation_slot = EIP1967_IMPLEMENTATION_SLOT
        info.admin_slot = EIP1967_ADMIN_SLOT

        # Look for upgrade function
        try:
            functions = getattr(contract, "functions", [])
            for func in functions:
                func_name = getattr(func, "name", "")
                if func_name in ("upgradeTo", "upgradeToAndCall", "upgrade"):
                    info.upgrade_function = func_name
                    info.resolution_notes.append(f"Upgrade function: {func_name}")
                    break

            # Look for initializer
            for func in functions:
                func_name = getattr(func, "name", "")
                if func_name in ("initialize", "initializer", "__init__"):
                    info.initializer_function = func_name
                    info.resolution_notes.append(f"Initializer: {func_name}")
                    break

        except Exception as e:
            info.resolution_notes.append(f"Resolution error: {e}")

        return info

    def _resolve_uups(self, contract: Any, info: ProxyInfo) -> ProxyInfo:
        """Resolve UUPS proxy details.

        Args:
            contract: Slither contract object.
            info: ProxyInfo to enhance.

        Returns:
            Enhanced ProxyInfo.
        """
        info.implementation_slot = EIP1967_IMPLEMENTATION_SLOT

        try:
            functions = getattr(contract, "functions", [])
            for func in functions:
                func_name = getattr(func, "name", "")
                if func_name == "_authorizeUpgrade":
                    info.upgrade_function = "upgradeTo (via _authorizeUpgrade)"
                    info.resolution_notes.append("UUPS authorization found")
                    break
                elif func_name == "upgradeTo":
                    info.upgrade_function = func_name

            # Look for initializer
            for func in functions:
                func_name = getattr(func, "name", "")
                if func_name in ("initialize", "initializer", "__init__"):
                    info.initializer_function = func_name
                    break

        except Exception as e:
            info.resolution_notes.append(f"Resolution error: {e}")

        return info

    def _resolve_diamond(self, contract: Any, info: ProxyInfo) -> ProxyInfo:
        """Resolve Diamond proxy details.

        Args:
            contract: Slither contract object.
            info: ProxyInfo to enhance.

        Returns:
            Enhanced ProxyInfo.
        """
        try:
            functions = getattr(contract, "functions", [])

            # Look for diamondCut
            for func in functions:
                func_name = getattr(func, "name", "")
                if func_name == "diamondCut":
                    info.upgrade_function = "diamondCut"
                    info.resolution_notes.append("Diamond cut function found")
                    break

            # Note: Actual facet resolution would require runtime state
            info.resolution_notes.append(
                "Facet addresses require runtime state (not available in static analysis)"
            )
            info.unresolved_reason = "Diamond facets require runtime state"

        except Exception as e:
            info.resolution_notes.append(f"Resolution error: {e}")

        return info

    def _resolve_beacon(self, contract: Any, info: ProxyInfo) -> ProxyInfo:
        """Resolve Beacon proxy details.

        Args:
            contract: Slither contract object.
            info: ProxyInfo to enhance.

        Returns:
            Enhanced ProxyInfo.
        """
        info.implementation_slot = EIP1967_BEACON_SLOT

        try:
            functions = getattr(contract, "functions", [])

            # Look for beacon accessor
            for func in functions:
                func_name = getattr(func, "name", "")
                if func_name == "beacon":
                    info.resolution_notes.append("Beacon accessor found")
                    break
                elif func_name == "implementation":
                    info.resolution_notes.append("Implementation accessor found")

            # Note: Actual beacon address requires runtime state
            info.unresolved_reason = "Beacon address requires runtime state"

        except Exception as e:
            info.resolution_notes.append(f"Resolution error: {e}")

        return info

    def _resolve_minimal(self, contract: Any, info: ProxyInfo) -> ProxyInfo:
        """Resolve Minimal (clone) proxy details.

        Args:
            contract: Slither contract object.
            info: ProxyInfo to enhance.

        Returns:
            Enhanced ProxyInfo.
        """
        info.resolution_notes.append(
            "Minimal proxy implementation embedded in bytecode"
        )
        info.unresolved_reason = (
            "Clone implementation requires bytecode analysis"
        )
        return info

    def _heuristic_resolution(self, contract: Any, info: ProxyInfo) -> ProxyInfo:
        """Fallback heuristic resolution for unknown proxy patterns.

        Args:
            contract: Slither contract object.
            info: ProxyInfo to enhance.

        Returns:
            Enhanced ProxyInfo with LOW confidence.
        """
        info.confidence = "LOW"

        try:
            # Look for any upgrade-related functions
            functions = getattr(contract, "functions", [])
            upgrade_keywords = {"upgrade", "update", "implement", "proxy"}

            for func in functions:
                func_name = getattr(func, "name", "").lower()
                for keyword in upgrade_keywords:
                    if keyword in func_name:
                        info.resolution_notes.append(
                            f"Potential upgrade function: {getattr(func, 'name', '')}"
                        )

            # Look for fallback/receive functions (proxy indicators)
            for func in functions:
                if getattr(func, "is_fallback", False):
                    info.resolution_notes.append("Has fallback function")
                if getattr(func, "is_receive", False):
                    info.resolution_notes.append("Has receive function")

        except Exception as e:
            info.resolution_notes.append(f"Heuristic resolution error: {e}")

        if not info.unresolved_reason:
            info.unresolved_reason = "Unknown proxy pattern, limited resolution"

        return info

    def _get_contract_source(self, contract: Any) -> str:
        """Get source code for a contract.

        Args:
            contract: Slither contract object.

        Returns:
            Source code string or empty string if unavailable.
        """
        contract_name = getattr(contract, "name", "")

        # Check cache
        if contract_name in self._source_cache:
            return self._source_cache[contract_name]

        try:
            # Try to get source from source_mapping
            source_mapping = getattr(contract, "source_mapping", None)
            if source_mapping:
                filename = getattr(source_mapping, "filename", None)
                if filename:
                    # Use BuildContext if available
                    if self.ctx:
                        lines = self.ctx.get_source_lines(str(filename.absolute))
                        source = "\n".join(lines)
                        self._source_cache[contract_name] = source
                        return source
                    else:
                        # Direct file read
                        try:
                            from pathlib import Path

                            path = Path(filename.absolute)
                            if path.exists():
                                source = path.read_text()
                                self._source_cache[contract_name] = source
                                return source
                        except Exception:
                            pass

        except Exception:
            pass

        self._source_cache[contract_name] = ""
        return ""


# -----------------------------------------------------------------------------
# Convenience Functions
# -----------------------------------------------------------------------------


def resolve_proxy(
    contract: Any,
    ctx: BuildContext | None = None,
) -> ProxyInfo:
    """Convenience function to resolve proxy pattern for a contract.

    Args:
        contract: Slither contract object.
        ctx: Optional BuildContext for warnings and logging.

    Returns:
        ProxyInfo with detection results and confidence.

    Example:
        >>> info = resolve_proxy(contract)
        >>> if info.is_proxy:
        ...     print(f"Pattern: {info.pattern.value}")
    """
    resolver = ProxyResolver(ctx)
    return resolver.resolve(contract)


def is_proxy_contract(contract: Any) -> bool:
    """Quick check if a contract is a proxy.

    Args:
        contract: Slither contract object.

    Returns:
        True if the contract appears to be a proxy.
    """
    info = resolve_proxy(contract)
    return info.is_proxy


def get_proxy_pattern(contract: Any) -> ProxyPattern:
    """Get the detected proxy pattern for a contract.

    Args:
        contract: Slither contract object.

    Returns:
        ProxyPattern enum value.
    """
    info = resolve_proxy(contract)
    return info.pattern


# -----------------------------------------------------------------------------
# Module Exports
# -----------------------------------------------------------------------------

__all__ = [
    # Main class
    "ProxyResolver",
    # Convenience functions
    "resolve_proxy",
    "is_proxy_contract",
    "get_proxy_pattern",
    # Constants
    "TRANSPARENT_PROXY_BASES",
    "UUPS_BASES",
    "DIAMOND_BASES",
    "BEACON_BASES",
    "MINIMAL_PROXY_BASES",
    "ALL_PROXY_BASES",
    "DIAMOND_SIGNATURES",
    "UUPS_SIGNATURES",
]
