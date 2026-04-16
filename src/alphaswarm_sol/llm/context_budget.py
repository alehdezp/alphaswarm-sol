"""Context Budget and Progressive Disclosure (Phase 7.1.3).

This module provides context budget policies that cap context size per pool/agent
while preserving evidence-first behavior. Works alongside ContextPolicy for
data minimization.

Key features:
- Per-pool and per-agent budget defaults
- Staged disclosure (summary -> evidence -> raw)
- Deterministic trimming that never exceeds hard caps
- Budget reports for auditability

Usage:
    from alphaswarm_sol.llm.context_budget import (
        ContextBudgetPolicy,
        ContextBudgetStage,
        ContextBudgetReport,
        apply_budget,
    )

    policy = ContextBudgetPolicy(max_tokens=6000)

    # Apply budget to context
    trimmed, report = policy.apply_budget(context_str, stage=ContextBudgetStage.EVIDENCE)

    # Request expansion (if budget allows)
    expanded, report = policy.expand_context(current, additional, from_stage, to_stage)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class ContextBudgetStage(Enum):
    """Progressive disclosure stages.

    SUMMARY: Minimal context with IDs, types, and one-line descriptions.
             Target: ~500 tokens. Enough to route and triage.

    EVIDENCE: Summary + evidence IDs, code locations, and operation sequences.
              Target: ~2000 tokens. Enough for Tier A/B verification.

    RAW: Full context including source snippets and detailed metadata.
         Target: <= max_tokens. Used only when deeper analysis needed.
    """

    SUMMARY = "summary"
    EVIDENCE = "evidence"
    RAW = "raw"


# Default token budgets per stage (as fraction of max_tokens)
STAGE_BUDGETS: Dict[ContextBudgetStage, float] = {
    ContextBudgetStage.SUMMARY: 0.15,   # ~900 tokens of 6000
    ContextBudgetStage.EVIDENCE: 0.50,  # ~3000 tokens of 6000
    ContextBudgetStage.RAW: 1.0,        # Full budget
}


# Role-based default budgets (max_tokens)
ROLE_BUDGETS: Dict[str, int] = {
    "classifier": 2000,     # Minimal context
    "attacker": 6000,       # Rich context for exploit synthesis
    "defender": 5000,       # Specs and guards
    "verifier": 4000,       # Paths and constraints
    "validator": 3000,      # Evidence checking
    "default": 6000,        # Safe default per CLAUDE.md
}


# Pool-based default budgets
POOL_BUDGETS: Dict[str, int] = {
    "triage": 2000,         # Quick classification
    "investigation": 6000,  # Full analysis
    "verification": 4000,   # Focused verification
    "default": 6000,
}


@dataclass
class ContextBudgetReport:
    """Report of budget enforcement actions.

    Attributes:
        stage: Current disclosure stage
        original_tokens: Estimated tokens before trimming
        final_tokens: Tokens after trimming
        max_tokens: Budget limit applied
        dropped_sections: List of section names that were trimmed
        preserved_evidence_ids: Evidence IDs that were kept
        trimmed: Whether any trimming occurred
        can_expand: Whether expansion to next stage is possible
        expansion_budget: Remaining tokens available for expansion
    """

    stage: ContextBudgetStage
    original_tokens: int
    final_tokens: int
    max_tokens: int
    dropped_sections: List[str] = field(default_factory=list)
    preserved_evidence_ids: List[str] = field(default_factory=list)
    trimmed: bool = False
    can_expand: bool = True
    expansion_budget: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "stage": self.stage.value,
            "original_tokens": self.original_tokens,
            "final_tokens": self.final_tokens,
            "max_tokens": self.max_tokens,
            "dropped_sections": self.dropped_sections,
            "preserved_evidence_ids": self.preserved_evidence_ids,
            "trimmed": self.trimmed,
            "can_expand": self.can_expand,
            "expansion_budget": self.expansion_budget,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextBudgetReport":
        """Create from dictionary."""
        return cls(
            stage=ContextBudgetStage(data["stage"]),
            original_tokens=data["original_tokens"],
            final_tokens=data["final_tokens"],
            max_tokens=data["max_tokens"],
            dropped_sections=data.get("dropped_sections", []),
            preserved_evidence_ids=data.get("preserved_evidence_ids", []),
            trimmed=data.get("trimmed", False),
            can_expand=data.get("can_expand", True),
            expansion_budget=data.get("expansion_budget", 0),
        )


class ContextBudgetPolicy:
    """Enforce context budgets with progressive disclosure.

    This policy caps context size per pool/agent while preserving
    evidence-first behavior. Trimming is deterministic and prioritizes:
    1. Evidence IDs (never trimmed)
    2. Code locations
    3. Operation sequences
    4. Source snippets (trimmed first)

    Usage:
        policy = ContextBudgetPolicy(max_tokens=6000, role="attacker")

        # Apply budget at EVIDENCE stage
        trimmed, report = policy.apply_budget(context, stage=ContextBudgetStage.EVIDENCE)

        # Check if expansion is possible
        if report.can_expand:
            expanded, report = policy.expand_context(trimmed, more_context)
    """

    # Token estimation: ~4 chars per token (simple heuristic, no external tokenizer)
    CHARS_PER_TOKEN = 4

    # Patterns for evidence IDs (must be preserved)
    EVIDENCE_ID_PATTERN = re.compile(
        r"(E-[A-Z0-9]{6,}|"           # E-ABCDEF style
        r"EV-[a-f0-9]{8,}|"           # EV-hexhash style
        r"evidence_id:\s*[^\s,]+|"    # evidence_id: xxx
        r"node_id:\s*[^\s,]+|"        # node_id: xxx
        r"ref:\s*[^\s,]+)"            # ref: xxx
    )

    # Section markers for structured context
    SECTION_MARKERS = [
        "## Source",
        "## Raw Code",
        "## Full Context",
        "## Metadata",
        "## Additional",
        "```solidity",
        "```",
    ]

    def __init__(
        self,
        max_tokens: int = 6000,
        role: Optional[str] = None,
        pool: Optional[str] = None,
        stage_budgets: Optional[Dict[ContextBudgetStage, float]] = None,
        hard_cap: int = 8000,
    ):
        """Initialize context budget policy.

        Args:
            max_tokens: Maximum tokens for this policy (default 6000 per CLAUDE.md)
            role: Agent role for default budget lookup
            pool: Pool name for default budget lookup
            stage_budgets: Custom stage budget fractions
            hard_cap: Absolute maximum (never exceeded, default 8000 per CLAUDE.md)
        """
        # Determine max_tokens from role/pool if not specified
        if role and role in ROLE_BUDGETS:
            self._max_tokens = min(ROLE_BUDGETS[role], max_tokens)
        elif pool and pool in POOL_BUDGETS:
            self._max_tokens = min(POOL_BUDGETS[pool], max_tokens)
        else:
            self._max_tokens = max_tokens

        self._hard_cap = hard_cap
        self._stage_budgets = stage_budgets or STAGE_BUDGETS.copy()
        self._current_stage = ContextBudgetStage.SUMMARY
        self._used_tokens = 0

    @property
    def max_tokens(self) -> int:
        """Maximum tokens allowed."""
        return min(self._max_tokens, self._hard_cap)

    @property
    def current_stage(self) -> ContextBudgetStage:
        """Current disclosure stage."""
        return self._current_stage

    @property
    def remaining_budget(self) -> int:
        """Remaining token budget."""
        return max(0, self.max_tokens - self._used_tokens)

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count using simple char-based heuristic.

        Args:
            text: Text to estimate

        Returns:
            Estimated token count
        """
        if not text:
            return 0
        return len(text) // self.CHARS_PER_TOKEN

    def get_stage_budget(self, stage: ContextBudgetStage) -> int:
        """Get token budget for a specific stage.

        Args:
            stage: Disclosure stage

        Returns:
            Token budget for that stage
        """
        fraction = self._stage_budgets.get(stage, 1.0)
        return int(self.max_tokens * fraction)

    def apply_budget(
        self,
        context: str,
        stage: Optional[ContextBudgetStage] = None,
    ) -> Tuple[str, ContextBudgetReport]:
        """Apply budget constraints to context.

        Trims context deterministically to fit within budget while
        preserving evidence IDs and critical information.

        Args:
            context: Raw context string
            stage: Target disclosure stage (default: current stage)

        Returns:
            Tuple of (trimmed_context, budget_report)
        """
        stage = stage or self._current_stage
        stage_budget = self.get_stage_budget(stage)

        original_tokens = self.estimate_tokens(context)
        dropped_sections: List[str] = []
        preserved_ids = self._extract_evidence_ids(context)

        # If within budget, return as-is
        if original_tokens <= stage_budget:
            self._current_stage = stage
            self._used_tokens = original_tokens
            return context, ContextBudgetReport(
                stage=stage,
                original_tokens=original_tokens,
                final_tokens=original_tokens,
                max_tokens=stage_budget,
                preserved_evidence_ids=preserved_ids,
                trimmed=False,
                can_expand=stage != ContextBudgetStage.RAW,
                expansion_budget=self.max_tokens - original_tokens,
            )

        # Need to trim - use deterministic strategy
        trimmed, dropped = self._trim_to_budget(context, stage_budget, preserved_ids)
        final_tokens = self.estimate_tokens(trimmed)

        self._current_stage = stage
        self._used_tokens = final_tokens

        return trimmed, ContextBudgetReport(
            stage=stage,
            original_tokens=original_tokens,
            final_tokens=final_tokens,
            max_tokens=stage_budget,
            dropped_sections=dropped,
            preserved_evidence_ids=preserved_ids,
            trimmed=True,
            can_expand=stage != ContextBudgetStage.RAW,
            expansion_budget=self.max_tokens - final_tokens,
        )

    def expand_context(
        self,
        current_context: str,
        additional_context: str,
        to_stage: Optional[ContextBudgetStage] = None,
    ) -> Tuple[str, ContextBudgetReport]:
        """Expand context to include additional information.

        Progressive disclosure: request more context only if budget allows.

        Args:
            current_context: Current trimmed context
            additional_context: Additional context to include
            to_stage: Target stage (default: next stage)

        Returns:
            Tuple of (expanded_context, budget_report)
        """
        # Determine target stage
        if to_stage is None:
            if self._current_stage == ContextBudgetStage.SUMMARY:
                to_stage = ContextBudgetStage.EVIDENCE
            elif self._current_stage == ContextBudgetStage.EVIDENCE:
                to_stage = ContextBudgetStage.RAW
            else:
                to_stage = ContextBudgetStage.RAW

        target_budget = self.get_stage_budget(to_stage)
        current_tokens = self.estimate_tokens(current_context)
        additional_tokens = self.estimate_tokens(additional_context)
        total_tokens = current_tokens + additional_tokens

        # Check if expansion fits within new stage budget
        if total_tokens <= target_budget:
            combined = f"{current_context}\n\n{additional_context}"
            final_tokens = self.estimate_tokens(combined)
            self._current_stage = to_stage
            self._used_tokens = final_tokens

            return combined, ContextBudgetReport(
                stage=to_stage,
                original_tokens=total_tokens,
                final_tokens=final_tokens,
                max_tokens=target_budget,
                preserved_evidence_ids=self._extract_evidence_ids(combined),
                trimmed=False,
                can_expand=to_stage != ContextBudgetStage.RAW,
                expansion_budget=self.max_tokens - final_tokens,
            )

        # Need to trim the combined content
        combined = f"{current_context}\n\n{additional_context}"
        preserved_ids = self._extract_evidence_ids(combined)
        trimmed, dropped = self._trim_to_budget(combined, target_budget, preserved_ids)
        final_tokens = self.estimate_tokens(trimmed)

        self._current_stage = to_stage
        self._used_tokens = final_tokens

        return trimmed, ContextBudgetReport(
            stage=to_stage,
            original_tokens=total_tokens,
            final_tokens=final_tokens,
            max_tokens=target_budget,
            dropped_sections=dropped,
            preserved_evidence_ids=preserved_ids,
            trimmed=True,
            can_expand=to_stage != ContextBudgetStage.RAW,
            expansion_budget=self.max_tokens - final_tokens,
        )

    def _extract_evidence_ids(self, text: str) -> List[str]:
        """Extract evidence IDs from text (must be preserved).

        Args:
            text: Context text

        Returns:
            List of evidence ID strings
        """
        matches = self.EVIDENCE_ID_PATTERN.findall(text)
        return list(set(matches))

    def _trim_to_budget(
        self,
        text: str,
        budget: int,
        preserve_ids: List[str],
    ) -> Tuple[str, List[str]]:
        """Trim text to fit budget while preserving evidence IDs.

        Trimming priority (first to be cut):
        1. Source code blocks (```solidity ... ```)
        2. Raw/Full sections (## Raw Code, ## Full Context)
        3. Metadata sections (## Metadata, ## Additional)
        4. Line truncation (keeping evidence lines)

        Args:
            text: Text to trim
            budget: Token budget
            preserve_ids: Evidence IDs that must be preserved

        Returns:
            Tuple of (trimmed_text, list_of_dropped_sections)
        """
        dropped: List[str] = []
        current = text

        # Step 1: Remove code blocks if over budget
        current_tokens = self.estimate_tokens(current)
        if current_tokens > budget:
            current, removed = self._remove_code_blocks(current)
            if removed:
                dropped.append("code_blocks")

        # Step 2: Remove low-priority sections
        current_tokens = self.estimate_tokens(current)
        if current_tokens > budget:
            for marker in ["## Source", "## Raw Code", "## Full Context"]:
                current, removed = self._remove_section(current, marker)
                if removed:
                    dropped.append(marker)
                if self.estimate_tokens(current) <= budget:
                    break

        # Step 3: Remove metadata sections
        current_tokens = self.estimate_tokens(current)
        if current_tokens > budget:
            for marker in ["## Metadata", "## Additional"]:
                current, removed = self._remove_section(current, marker)
                if removed:
                    dropped.append(marker)
                if self.estimate_tokens(current) <= budget:
                    break

        # Step 4: Line truncation (preserve evidence lines)
        current_tokens = self.estimate_tokens(current)
        if current_tokens > budget:
            current = self._truncate_lines(current, budget, preserve_ids)
            dropped.append("line_truncation")

        return current, dropped

    def _remove_code_blocks(self, text: str) -> Tuple[str, bool]:
        """Remove fenced code blocks from text.

        Args:
            text: Input text

        Returns:
            Tuple of (text_without_code_blocks, removed_any)
        """
        pattern = r"```[\w]*\n.*?```"
        result = re.sub(pattern, "[code block trimmed]", text, flags=re.DOTALL)
        removed = result != text
        return result, removed

    def _remove_section(self, text: str, marker: str) -> Tuple[str, bool]:
        """Remove a section starting with a marker.

        Args:
            text: Input text
            marker: Section marker (e.g., "## Source")

        Returns:
            Tuple of (text_without_section, removed)
        """
        if marker not in text:
            return text, False

        # Find section and remove until next section or end
        lines = text.split("\n")
        result_lines: List[str] = []
        in_section = False

        for line in lines:
            if line.startswith(marker):
                in_section = True
                result_lines.append(f"[{marker.strip('#').strip()} trimmed]")
                continue
            elif in_section and line.startswith("## "):
                in_section = False

            if not in_section:
                result_lines.append(line)

        return "\n".join(result_lines), True

    def _truncate_lines(
        self,
        text: str,
        budget: int,
        preserve_ids: List[str],
    ) -> str:
        """Truncate lines while preserving evidence.

        Args:
            text: Input text
            budget: Token budget
            preserve_ids: Evidence IDs to preserve

        Returns:
            Truncated text
        """
        lines = text.split("\n")
        result_lines: List[str] = []
        current_tokens = 0
        target_chars = budget * self.CHARS_PER_TOKEN

        for line in lines:
            line_chars = len(line)

            # Always include lines with evidence IDs
            has_evidence = any(eid in line for eid in preserve_ids)

            if has_evidence:
                result_lines.append(line)
                current_tokens += line_chars // self.CHARS_PER_TOKEN
            elif current_tokens * self.CHARS_PER_TOKEN + line_chars <= target_chars:
                result_lines.append(line)
                current_tokens += line_chars // self.CHARS_PER_TOKEN
            else:
                # Budget exhausted, add truncation marker and stop
                result_lines.append("... [truncated]")
                break

        return "\n".join(result_lines)

    def reset(self) -> None:
        """Reset policy state for new context."""
        self._current_stage = ContextBudgetStage.SUMMARY
        self._used_tokens = 0


def get_budget_policy(
    role: Optional[str] = None,
    pool: Optional[str] = None,
    max_tokens: int = 6000,
) -> ContextBudgetPolicy:
    """Get a context budget policy for a role or pool.

    Args:
        role: Agent role (e.g., "attacker", "defender")
        pool: Pool name (e.g., "triage", "investigation")
        max_tokens: Override max tokens

    Returns:
        Configured ContextBudgetPolicy
    """
    return ContextBudgetPolicy(
        max_tokens=max_tokens,
        role=role,
        pool=pool,
    )


def apply_budget(
    context: str,
    stage: ContextBudgetStage = ContextBudgetStage.EVIDENCE,
    max_tokens: int = 6000,
    role: Optional[str] = None,
) -> Tuple[str, ContextBudgetReport]:
    """Apply budget constraints to context (convenience function).

    Args:
        context: Raw context string
        stage: Target disclosure stage
        max_tokens: Maximum tokens
        role: Agent role for budget lookup

    Returns:
        Tuple of (trimmed_context, budget_report)
    """
    policy = ContextBudgetPolicy(max_tokens=max_tokens, role=role)
    return policy.apply_budget(context, stage=stage)


def estimate_context_tokens(context: str) -> int:
    """Estimate token count for context string.

    Args:
        context: Context string

    Returns:
        Estimated token count
    """
    return ContextBudgetPolicy().estimate_tokens(context)
