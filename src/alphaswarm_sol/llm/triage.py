"""
Hierarchical Triage System

Deterministically classifies functions into analysis levels (0-3)
based on Tier A properties WITHOUT using LLM.

This is the FIRST filter in VKG 3.5's efficiency strategy.
"""

from dataclasses import dataclass
from enum import IntEnum
from typing import Optional, Dict, Any


class TriageLevel(IntEnum):
    """Analysis depth levels with token budgets."""
    LEVEL_0_SKIP = 0       # No LLM needed (trivially safe)
    LEVEL_1_QUICK = 1      # Quick scan (100 tokens)
    LEVEL_2_FOCUSED = 2    # Focused analysis (500 tokens)
    LEVEL_3_DEEP = 3       # Deep adversarial (2000 tokens)


@dataclass
class TriageResult:
    """Result of triage classification."""
    level: TriageLevel
    reason: str
    token_budget: int
    confidence: float  # How confident we are in this classification

    @property
    def requires_llm(self) -> bool:
        """Check if LLM analysis is needed."""
        return self.level > TriageLevel.LEVEL_0_SKIP

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/debugging."""
        return {
            "level": self.level.value,
            "level_name": self.level.name,
            "reason": self.reason,
            "token_budget": self.token_budget,
            "confidence": self.confidence,
            "requires_llm": self.requires_llm,
        }


class TriageClassifier:
    """Deterministic function triage based on Tier A properties."""

    # Token budgets per level
    BUDGETS = {
        TriageLevel.LEVEL_0_SKIP: 0,
        TriageLevel.LEVEL_1_QUICK: 100,
        TriageLevel.LEVEL_2_FOCUSED: 500,
        TriageLevel.LEVEL_3_DEEP: 2000,
    }

    def classify(self, fn_node: Dict[str, Any]) -> TriageResult:
        """
        Classify function into analysis level.

        Args:
            fn_node: Function node with properties

        Returns:
            TriageResult with level, reason, budget, confidence
        """
        props = fn_node.get("properties", {})

        # Level 0: Trivially safe - no LLM needed
        if self._is_trivially_safe(props):
            return TriageResult(
                level=TriageLevel.LEVEL_0_SKIP,
                reason="Trivially safe: no external calls, no state writes, or fully guarded",
                token_budget=self.BUDGETS[TriageLevel.LEVEL_0_SKIP],
                confidence=0.95
            )

        # Level 3: High-risk patterns - needs deep analysis
        reason_deep = self._needs_deep_analysis_reason(props)
        if reason_deep:
            return TriageResult(
                level=TriageLevel.LEVEL_3_DEEP,
                reason=f"High-risk: {reason_deep}",
                token_budget=self.BUDGETS[TriageLevel.LEVEL_3_DEEP],
                confidence=0.90
            )

        # Level 2: Pattern-matched - needs focused analysis
        reason_focused = self._needs_focused_analysis_reason(props)
        if reason_focused:
            return TriageResult(
                level=TriageLevel.LEVEL_2_FOCUSED,
                reason=f"Pattern match: {reason_focused}",
                token_budget=self.BUDGETS[TriageLevel.LEVEL_2_FOCUSED],
                confidence=0.85
            )

        # Level 1: Has potential issues - quick scan
        return TriageResult(
            level=TriageLevel.LEVEL_1_QUICK,
            reason="Potential issues: needs quick LLM verification",
            token_budget=self.BUDGETS[TriageLevel.LEVEL_1_QUICK],
            confidence=0.80
        )

    def _is_trivially_safe(self, props: Dict[str, Any]) -> bool:
        """Check if function is trivially safe (Level 0)."""
        # View/pure functions
        if props.get("state_mutability") in ("view", "pure"):
            return True

        # Internal/private with no external calls AND no state writes
        if props.get("visibility") in ("internal", "private"):
            if not props.get("has_external_calls") and not props.get("writes_state"):
                return True

        return False

    def _needs_deep_analysis_reason(self, props: Dict[str, Any]) -> Optional[str]:
        """
        Check if function needs deep adversarial analysis (Level 3).

        Returns reason string if deep analysis needed, None otherwise.
        """
        # Reentrancy risk
        if props.get("state_write_after_external_call"):
            if not props.get("has_reentrancy_guard"):
                return "state write after external call without reentrancy guard"

        # Access control risk
        if props.get("writes_privileged_state"):
            if not props.get("has_access_gate"):
                return "writes privileged state without access control"

        # Oracle manipulation risk
        if props.get("reads_oracle_price"):
            if not props.get("has_staleness_check"):
                return "reads oracle price without staleness check"

        # MEV risk
        if props.get("swap_like"):
            if props.get("risk_missing_slippage_parameter"):
                return "swap without slippage protection"
            if props.get("risk_missing_deadline_check"):
                return "swap without deadline check"

        # Public/external functions writing owner/admin state
        if props.get("visibility") in ("public", "external"):
            if props.get("writes_owner") or props.get("writes_admin"):
                if not props.get("has_access_gate"):
                    return "public function modifies privileged state"

        return None

    def _needs_focused_analysis_reason(self, props: Dict[str, Any]) -> Optional[str]:
        """
        Check if function needs focused analysis (Level 2).

        Returns reason string if focused analysis needed, None otherwise.
        """
        # External calls with value
        if props.get("has_external_calls") and props.get("transfers_value"):
            return "external call with value transfer"

        # State modifications in public functions without gate
        if props.get("visibility") in ("public", "external"):
            if props.get("writes_state") and not props.get("has_access_gate"):
                return "public state write without access control"

        # Loop with external calls (DoS risk)
        if props.get("external_calls_in_loop"):
            return "external calls in unbounded loop"

        # Unbounded operations
        if props.get("has_unbounded_loop"):
            return "unbounded loop detected"

        # Token operations without safe patterns
        if props.get("uses_erc20_transfer"):
            if not props.get("uses_safe_erc20"):
                return "unsafe ERC20 transfer pattern"

        return None

    def batch_classify(self, fn_nodes: list) -> Dict[str, Any]:
        """
        Classify a batch of functions and return statistics.

        Args:
            fn_nodes: List of function nodes

        Returns:
            Dict with results and statistics
        """
        results = []
        stats = {
            "level_0_count": 0,
            "level_1_count": 0,
            "level_2_count": 0,
            "level_3_count": 0,
            "total_functions": len(fn_nodes),
            "total_tokens_budget": 0,
            "llm_required_count": 0,
        }

        for fn in fn_nodes:
            result = self.classify(fn)
            results.append(result)

            level_key = f"level_{result.level.value}_count"
            stats[level_key] += 1
            stats["total_tokens_budget"] += result.token_budget

            if result.requires_llm:
                stats["llm_required_count"] += 1

        # Calculate percentages
        total = stats["total_functions"]
        if total > 0:
            stats["level_0_pct"] = stats["level_0_count"] / total * 100
            stats["level_1_pct"] = stats["level_1_count"] / total * 100
            stats["level_2_pct"] = stats["level_2_count"] / total * 100
            stats["level_3_pct"] = stats["level_3_count"] / total * 100
            stats["llm_required_pct"] = stats["llm_required_count"] / total * 100

        return {
            "results": results,
            "stats": stats,
        }
