"""Phase 12: LLM Subagent Orchestration Manager.

This module provides centralized management for routing tasks to
appropriate LLM subagents, selecting the right provider and model
tier based on task complexity.

Key features:
- Task-based routing to appropriate provider/tier
- TOON format for context (token efficiency)
- Cost tracking per subagent
- Fallback when preferred provider unavailable
- Batch dispatch with concurrency control

Usage:
    from alphaswarm_sol.llm.subagents import (
        LLMSubagentManager,
        SubagentTask,
        SubagentResult,
        TaskType,
    )

    manager = LLMSubagentManager(config)

    # Simple task - uses cheap tier
    evidence_task = SubagentTask(
        type=TaskType.EVIDENCE_EXTRACTION,
        prompt="Extract evidence from this code",
        context={"code": function_code},
    )
    result = await manager.dispatch(evidence_task)

    # Complex task - uses expensive tier
    exploit_task = SubagentTask(
        type=TaskType.EXPLOIT_SYNTHESIS,
        prompt="Synthesize an exploit for this vulnerability",
        context={"finding": finding, "code": code},
    )
    result = await manager.dispatch(exploit_task)
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
import json
import logging

from alphaswarm_sol.llm.tiers import (
    TierRouter,
    ModelTier,
    ModelTierConfig,
    AnalysisType,
    Complexity,
    TierStats,
    PolicyAwareTierRouter,
)
from alphaswarm_sol.llm.config import LLMConfig, Provider
from alphaswarm_sol.llm.routing_policy import (
    TierRoutingPolicy,
    RoutingDecision,
    EscalationReason,
)
from alphaswarm_sol.llm.context_budget import (
    ContextBudgetPolicy,
    ContextBudgetStage,
    ContextBudgetReport,
    apply_budget,
    estimate_context_tokens,
)
from alphaswarm_sol.llm.prompt_lint import (
    PromptLintReport,
    lint_prompt,
)

# Lazy import to avoid circular dependency (07.1.3-03)
# RetrievalPacker, EvidenceItem, PackedEvidenceBundle imported in methods


logger = logging.getLogger(__name__)


class TaskType(str, Enum):
    """Types of subagent tasks.

    Each task type has a default tier mapping:
    - CHEAP: Simple, mechanical tasks
    - STANDARD: Typical analysis tasks
    - PREMIUM: Complex reasoning tasks
    """
    # Cheap tier (simple checks)
    EVIDENCE_EXTRACTION = "evidence_extraction"
    PATTERN_VALIDATION = "pattern_validation"
    CODE_PARSING = "code_parsing"

    # Standard tier (typical analysis)
    TIER_B_VERIFICATION = "tier_b_verification"
    CONTEXT_ANALYSIS = "context_analysis"
    FP_FILTERING = "fp_filtering"

    # Premium tier (complex reasoning)
    EXPLOIT_SYNTHESIS = "exploit_synthesis"
    BUSINESS_LOGIC_ANALYSIS = "business_logic_analysis"
    MULTI_STEP_REASONING = "multi_step_reasoning"
    ATTACK_PATH_GENERATION = "attack_path_generation"


# Default tier mappings for task types
TASK_TIER_DEFAULTS: Dict[TaskType, ModelTier] = {
    # Cheap tier
    TaskType.EVIDENCE_EXTRACTION: ModelTier.CHEAP,
    TaskType.PATTERN_VALIDATION: ModelTier.CHEAP,
    TaskType.CODE_PARSING: ModelTier.CHEAP,

    # Standard tier
    TaskType.TIER_B_VERIFICATION: ModelTier.STANDARD,
    TaskType.CONTEXT_ANALYSIS: ModelTier.STANDARD,
    TaskType.FP_FILTERING: ModelTier.STANDARD,

    # Premium tier
    TaskType.EXPLOIT_SYNTHESIS: ModelTier.PREMIUM,
    TaskType.BUSINESS_LOGIC_ANALYSIS: ModelTier.PREMIUM,
    TaskType.MULTI_STEP_REASONING: ModelTier.PREMIUM,
    TaskType.ATTACK_PATH_GENERATION: ModelTier.PREMIUM,
}


@dataclass
class SubagentTask:
    """Task to be executed by an LLM subagent.

    Attributes:
        type: Task type (determines default tier)
        prompt: The prompt to send
        context: Context data (will be serialized as TOON)
        output_schema: Expected JSON schema for output
        preferred_provider: Override provider selection
        preferred_tier: Override tier selection
        max_cost_usd: Maximum cost for this task
        timeout_seconds: Timeout for execution
        bead_id: Associated bead ID (for tracking)
        risk_score: Risk score for routing policy (0.0 - 1.0)
        evidence_completeness: Evidence completeness for routing (0.0 - 1.0)
        severity: Severity level for routing hints
        pattern_type: Pattern type for routing hints
        pool_id: Pool ID for per-pool routing configuration
        workflow_id: Workflow ID for per-workflow routing configuration
    """
    type: TaskType
    prompt: str
    context: Dict[str, Any] = field(default_factory=dict)
    output_schema: Optional[Dict[str, Any]] = None
    preferred_provider: Optional[str] = None
    preferred_tier: Optional[ModelTier] = None
    max_cost_usd: float = 0.50
    timeout_seconds: int = 60
    bead_id: Optional[str] = None
    # Routing policy fields
    risk_score: float = 0.0
    evidence_completeness: float = 1.0
    severity: Optional[str] = None
    pattern_type: Optional[str] = None
    pool_id: Optional[str] = None
    workflow_id: Optional[str] = None
    # Context budget fields (Phase 7.1.3)
    context_budget_stage: ContextBudgetStage = ContextBudgetStage.EVIDENCE
    max_context_tokens: Optional[int] = None  # Override default budget

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": self.type.value,
            "prompt": self.prompt,
            "context": self.context,
            "output_schema": self.output_schema,
            "preferred_provider": self.preferred_provider,
            "preferred_tier": self.preferred_tier.value if self.preferred_tier else None,
            "max_cost_usd": self.max_cost_usd,
            "timeout_seconds": self.timeout_seconds,
            "bead_id": self.bead_id,
            "risk_score": self.risk_score,
            "evidence_completeness": self.evidence_completeness,
            "severity": self.severity,
            "pattern_type": self.pattern_type,
            "pool_id": self.pool_id,
            "workflow_id": self.workflow_id,
            "context_budget_stage": self.context_budget_stage.value,
            "max_context_tokens": self.max_context_tokens,
        }


@dataclass
class SubagentResult:
    """Result from an LLM subagent.

    Attributes:
        verdict: The verdict (if applicable)
        confidence: Confidence score
        reasoning: Reasoning for the verdict
        evidence: Supporting evidence
        output: Raw output from the model
        provider: Provider used
        model: Model used
        tier: Model tier
        tokens_used: Total tokens used
        cost_usd: Cost in USD
        latency_ms: Execution latency
        task_type: Original task type
        timestamp: When completed
        routing_decision: The routing policy decision (if used)
        tier_rationale: Rationale for tier selection
        escalation_reasons: Reasons for escalation/downgrade
    """
    verdict: Optional[str] = None
    confidence: float = 0.0
    reasoning: str = ""
    evidence: List[str] = field(default_factory=list)
    output: Optional[str] = None
    provider: str = ""
    model: str = ""
    tier: Optional[ModelTier] = None
    tokens_used: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
    task_type: Optional[TaskType] = None
    timestamp: datetime = field(default_factory=datetime.now)
    # Routing metadata
    routing_decision: Optional[Dict[str, Any]] = None
    tier_rationale: str = ""
    escalation_reasons: List[str] = field(default_factory=list)
    # Context budget metadata (Phase 7.1.3)
    context_budget_report: Optional[Dict[str, Any]] = None
    # Prompt lint report (Phase 7.1.3-05)
    prompt_lint_report: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "verdict": self.verdict,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "evidence": self.evidence,
            "output": self.output,
            "provider": self.provider,
            "model": self.model,
            "tier": self.tier.value if self.tier else None,
            "tokens_used": self.tokens_used,
            "cost_usd": round(self.cost_usd, 6),
            "latency_ms": self.latency_ms,
            "task_type": self.task_type.value if self.task_type else None,
            "timestamp": self.timestamp.isoformat(),
            "routing_decision": self.routing_decision,
            "tier_rationale": self.tier_rationale,
            "escalation_reasons": self.escalation_reasons,
            "context_budget_report": self.context_budget_report,
            "prompt_lint_report": self.prompt_lint_report,
        }

    @property
    def is_success(self) -> bool:
        """Whether the task completed successfully."""
        return self.output is not None


class TOONEncoder:
    """Encoder for TOON (Token-Optimized Output Notation).

    TOON is a compact format for encoding context that reduces
    token usage by 30-50% compared to verbose JSON.

    Example TOON output:
        F:withdraw|C:Vault|L:45|S:critical
        P:vm-001|M:state_write_after_external_call
        E:ext_call@48,bal_write@52

    vs verbose JSON:
        {"function": "withdraw", "contract": "Vault", ...}
    """

    # Field abbreviations
    ABBREVIATIONS = {
        "function": "F",
        "contract": "C",
        "line": "L",
        "severity": "S",
        "pattern": "P",
        "matched": "M",
        "evidence": "E",
        "operations": "O",
        "guard": "G",
        "modifier": "Mod",
        "external_call": "X",
        "state_write": "W",
        "state_read": "R",
        "balance": "bal",
        "owner": "own",
        "admin": "adm",
    }

    def encode(self, data: Dict[str, Any]) -> str:
        """Encode data to TOON format.

        Args:
            data: Data to encode

        Returns:
            TOON-encoded string
        """
        if not data:
            return ""

        lines = []

        # Encode each key-value pair
        for key, value in data.items():
            abbrev = self.ABBREVIATIONS.get(key, key[:3].upper())

            if isinstance(value, dict):
                # Nested dict - encode recursively
                nested = self.encode(value)
                lines.append(f"{abbrev}:{{{nested}}}")
            elif isinstance(value, list):
                # List - join with commas
                items = [self._encode_value(v) for v in value]
                lines.append(f"{abbrev}:[{','.join(items)}]")
            else:
                lines.append(f"{abbrev}:{self._encode_value(value)}")

        return "|".join(lines)

    def _encode_value(self, value: Any) -> str:
        """Encode a single value."""
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "T" if value else "F"
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, str):
            # Shorten common terms
            for full, abbrev in self.ABBREVIATIONS.items():
                value = value.replace(full, abbrev)
            return value
        return str(value)

    def decode(self, toon: str) -> Dict[str, Any]:
        """Decode TOON format to dictionary.

        Args:
            toon: TOON-encoded string

        Returns:
            Decoded dictionary
        """
        if not toon:
            return {}

        result = {}
        parts = toon.split("|")

        for part in parts:
            if ":" not in part:
                continue

            key, value = part.split(":", 1)

            # Find full key name
            full_key = key
            for full, abbrev in self.ABBREVIATIONS.items():
                if abbrev == key:
                    full_key = full
                    break

            # Decode value
            result[full_key] = self._decode_value(value)

        return result

    def _decode_value(self, value: str) -> Any:
        """Decode a single value."""
        if value == "null":
            return None
        if value == "T":
            return True
        if value == "F":
            return False
        if value.startswith("[") and value.endswith("]"):
            return value[1:-1].split(",")
        if value.startswith("{") and value.endswith("}"):
            return self.decode(value[1:-1])
        try:
            return int(value)
        except ValueError:
            try:
                return float(value)
            except ValueError:
                return value


class LLMSubagentManager:
    """Orchestrate LLM subagents across providers and tiers.

    This manager routes tasks to appropriate models based on:
    1. Task type (determines default tier)
    2. Task complexity (may override tier)
    3. Provider availability
    4. Cost constraints
    5. Routing policy (risk, evidence, budget)

    Example:
        manager = LLMSubagentManager(config)

        # Dispatch single task
        result = await manager.dispatch(task)

        # Dispatch batch with concurrency
        results = await manager.dispatch_batch(tasks, parallel=5)

        # Get routing summary
        print(manager.get_routing_summary())
    """

    def __init__(
        self,
        config: Optional[LLMConfig] = None,
        tier_config: Optional[ModelTierConfig] = None,
        routing_policy: Optional[TierRoutingPolicy] = None,
        budget_usd: Optional[float] = None,
    ):
        """Initialize subagent manager.

        Args:
            config: LLM configuration
            tier_config: Tier configuration
            routing_policy: Tier routing policy for cost-effective selection
            budget_usd: Total budget for this manager session
        """
        self.config = config or LLMConfig()
        self.tier_config = tier_config or ModelTierConfig()
        self.tier_router = TierRouter(self.tier_config)
        self.routing_policy = routing_policy or TierRoutingPolicy(tier_config=self.tier_config)
        self.toon_encoder = TOONEncoder()
        self._evidence_packer = None  # Lazy init to avoid circular import (07.1.3-03)
        self._results: List[SubagentResult] = []
        self._budget_usd = budget_usd
        self._spent_usd: float = 0.0

    @property
    def evidence_packer(self) -> "RetrievalPacker":
        """Lazy-initialized evidence packer (07.1.3-03)."""
        if self._evidence_packer is None:
            from alphaswarm_sol.context.retrieval_packer import RetrievalPacker
            self._evidence_packer = RetrievalPacker(max_tokens=3000)
        return self._evidence_packer

    @property
    def budget_remaining(self) -> Optional[float]:
        """Remaining budget if set."""
        if self._budget_usd is None:
            return None
        return max(0.0, self._budget_usd - self._spent_usd)

    async def dispatch(self, task: SubagentTask) -> SubagentResult:
        """Dispatch a task to appropriate subagent.

        Selection priority:
        1. Task's preferred tier (if specified)
        2. Routing policy decision (based on risk, evidence, budget)
        3. Task type default tier (TASK_TIER_DEFAULTS)

        Args:
            task: Task to dispatch

        Returns:
            SubagentResult with verdict, metrics, and routing metadata
        """
        start_time = time.time()

        # Select tier using routing policy
        tier, routing_decision = self._select_tier_with_policy(task)

        # Select provider and model
        provider_name, model = self._select_provider_model(task, tier)

        # Serialize context as TOON (token efficient)
        context_toon = self.toon_encoder.encode(task.context)

        # Build full prompt with budget enforcement and linting (07.1.3)
        full_prompt, budget_report, lint_report = self._build_prompt(task, context_toon)

        # Execute (mock for now - real implementation would call provider)
        try:
            result = await asyncio.wait_for(
                self._execute_with_provider(
                    prompt=full_prompt,
                    provider=provider_name,
                    model=model,
                    output_schema=task.output_schema,
                ),
                timeout=task.timeout_seconds,
            )

            result.tier = tier
            result.task_type = task.type
            result.latency_ms = int((time.time() - start_time) * 1000)

            # Add routing metadata
            if routing_decision:
                result.routing_decision = routing_decision.to_dict()
                result.tier_rationale = routing_decision.rationale
                result.escalation_reasons = [r.value for r in routing_decision.escalation_reasons]

            # Add budget report (07.1.3)
            if budget_report:
                result.context_budget_report = budget_report.to_dict()

            # Add lint report (07.1.3-05)
            if lint_report:
                result.prompt_lint_report = lint_report.to_dict()

            # Track spending
            self._spent_usd += result.cost_usd

            self._results.append(result)
            return result

        except asyncio.TimeoutError:
            return SubagentResult(
                verdict="TIMEOUT",
                reasoning=f"Task timed out after {task.timeout_seconds}s",
                provider=provider_name,
                model=model,
                tier=tier,
                task_type=task.type,
                latency_ms=int((time.time() - start_time) * 1000),
            )

        except Exception as e:
            logger.error(f"Subagent dispatch failed: {e}")
            return SubagentResult(
                verdict="ERROR",
                reasoning=str(e),
                provider=provider_name,
                model=model,
                tier=tier,
                task_type=task.type,
            )

    def _select_tier(self, task: SubagentTask) -> ModelTier:
        """Select tier based on task (legacy method without policy).

        Args:
            task: Task to select tier for

        Returns:
            Selected ModelTier
        """
        # Use preferred tier if specified
        if task.preferred_tier:
            return task.preferred_tier

        # Use task type default
        return TASK_TIER_DEFAULTS.get(task.type, ModelTier.STANDARD)

    def _select_tier_with_policy(
        self,
        task: SubagentTask,
    ) -> tuple[ModelTier, Optional[RoutingDecision]]:
        """Select tier using routing policy.

        Args:
            task: Task to select tier for

        Returns:
            Tuple of (ModelTier, RoutingDecision or None)
        """
        # Use preferred tier if specified (override policy)
        if task.preferred_tier:
            return task.preferred_tier, None

        # Route using policy
        decision = self.routing_policy.route(
            task_type=task.type.value,
            risk_score=task.risk_score,
            evidence_completeness=task.evidence_completeness,
            budget_remaining=self.budget_remaining,
            severity=task.severity,
            pattern_type=task.pattern_type,
            pool_id=task.pool_id,
            workflow_id=task.workflow_id,
        )

        logger.debug(
            "Routing decision for %s: tier=%s, rationale=%s",
            task.type.value,
            decision.tier.value,
            decision.rationale,
        )

        return decision.tier, decision

    def _select_provider_model(
        self,
        task: SubagentTask,
        tier: ModelTier,
    ) -> tuple[str, str]:
        """Select provider and model.

        Args:
            task: Task being dispatched
            tier: Selected tier

        Returns:
            Tuple of (provider_name, model_name)
        """
        # Use preferred provider if specified
        if task.preferred_provider:
            provider = task.preferred_provider
        else:
            # Default to first available
            provider = "claude"  # Would check availability

        # Get model for tier
        tier_models = self.tier_config.tier_models.get(tier, [])
        model = tier_models[0] if tier_models else "default"

        return provider, model

    def _build_prompt(
        self,
        task: SubagentTask,
        context_toon: str,
    ) -> tuple[str, Optional[ContextBudgetReport], Optional[PromptLintReport]]:
        """Build full prompt for task with budget enforcement and linting.

        Per 07.1.3: Applies context budget constraints and linting, returns reports.

        Args:
            task: Task
            context_toon: TOON-encoded context

        Returns:
            Tuple of (full_prompt_string, budget_report_or_none, lint_report_or_none)
        """
        # Determine budget for this task
        max_tokens = task.max_context_tokens or 6000  # Default per CLAUDE.md

        # Build initial prompt parts
        parts = [
            f"Task Type: {task.type.value}",
            "",
            "Context (TOON format):",
            context_toon,
            "",
            "Instructions:",
            task.prompt,
        ]

        if task.output_schema:
            parts.extend([
                "",
                "Output Schema:",
                json.dumps(task.output_schema, indent=2),
            ])

        full_prompt = "\n".join(parts)

        # Apply budget constraints to the prompt
        trimmed_prompt, budget_report = apply_budget(
            full_prompt,
            stage=task.context_budget_stage,
            max_tokens=max_tokens,
        )

        if budget_report.trimmed:
            logger.info(
                "Context trimmed for task %s: %d -> %d tokens (stage=%s)",
                task.type.value,
                budget_report.original_tokens,
                budget_report.final_tokens,
                budget_report.stage.value,
            )

        # Lint the prompt (non-blocking, logs warnings)
        lint_context = {
            "max_tokens": max_tokens,
            "output_schema": task.output_schema,
        }
        lint_report = lint_prompt(trimmed_prompt, context=lint_context)

        if lint_report.has_warnings:
            logger.warning(
                "Prompt lint warnings for task %s: %d warnings, ~%d wasteful tokens",
                task.type.value,
                lint_report.warning_count,
                lint_report.wasteful_tokens,
            )

        return trimmed_prompt, budget_report, lint_report

    def pack_evidence_context(
        self,
        evidence_items: List[Dict[str, Any]],
        max_tokens: int = 3000,
    ) -> "PackedEvidenceBundle":
        """Pack evidence items into compact TOON format (07.1.3-03).

        Use this method when constructing SubagentTask context that
        includes evidence data. The packed output preserves evidence IDs,
        file paths, line anchors, and risk scores while reducing tokens.

        Args:
            evidence_items: List of evidence dictionaries with fields:
                - evidence_id/id: Unique identifier (required)
                - file/location.file: File path
                - line/location.line: Line number(s)
                - code/snippet: Source code (may be trimmed)
                - risk_score/severity_score: Risk score 0.0-1.0
                - operations/semantic_ops: Semantic operations
            max_tokens: Maximum tokens for packed output

        Returns:
            PackedEvidenceBundle with compact TOON output

        Example:
            evidence = [
                {"id": "E-ABC", "file": "Vault.sol", "line": 45, "risk_score": 0.85},
            ]
            packed = manager.pack_evidence_context(evidence)
            task = SubagentTask(
                type=TaskType.EVIDENCE_EXTRACTION,
                prompt="Analyze evidence",
                context={"evidence_toon": packed.toon_output},
            )
        """
        from alphaswarm_sol.context.retrieval_packer import EvidenceItem

        items: List[EvidenceItem] = []

        for ev in evidence_items:
            # Handle various evidence dict formats
            evidence_id = (
                ev.get("evidence_id")
                or ev.get("id")
                or ev.get("node_id")
                or f"EV-{hash(str(ev)) & 0xFFFFFFFF:08x}"
            )

            location = ev.get("location", {})
            file_path = location.get("file", ev.get("file", ""))
            line_start = location.get("line", ev.get("line", 0))
            line_end = location.get("end_line", line_start)

            item = EvidenceItem(
                evidence_id=evidence_id,
                file_path=file_path,
                line_start=line_start,
                line_end=line_end,
                code_snippet=ev.get("code", ev.get("snippet", "")),
                risk_score=float(ev.get("risk_score", ev.get("severity_score", 0.0))),
                operations=list(ev.get("operations", ev.get("semantic_ops", []))),
                metadata={
                    k: v
                    for k, v in ev.items()
                    if k not in ("evidence_id", "id", "file", "line", "code", "snippet",
                                 "risk_score", "severity_score", "operations", "semantic_ops",
                                 "location", "node_id")
                },
                node_id=ev.get("node_id"),
            )
            items.append(item)

        return self.evidence_packer.pack(items, max_tokens=max_tokens)

    async def _execute_with_provider(
        self,
        prompt: str,
        provider: str,
        model: str,
        output_schema: Optional[Dict[str, Any]] = None,
    ) -> SubagentResult:
        """Execute task with provider.

        This is a placeholder - real implementation would call
        the actual LLM provider API.

        Args:
            prompt: Full prompt
            provider: Provider name
            model: Model name
            output_schema: Expected output schema

        Returns:
            SubagentResult
        """
        # Mock execution for now
        await asyncio.sleep(0.1)

        return SubagentResult(
            verdict="MOCK",
            confidence=0.5,
            reasoning="Mock execution - provider integration pending",
            evidence=["Provider integration not yet implemented"],
            output=f"Mock output from {provider}/{model}",
            provider=provider,
            model=model,
            tokens_used=100,
            cost_usd=0.001,
        )

    async def dispatch_batch(
        self,
        tasks: List[SubagentTask],
        parallel: int = 5,
    ) -> List[SubagentResult]:
        """Dispatch multiple tasks with concurrency control.

        Args:
            tasks: Tasks to dispatch
            parallel: Max concurrent tasks

        Returns:
            List of results
        """
        if not tasks:
            return []

        semaphore = asyncio.Semaphore(parallel)

        async def dispatch_with_limit(task: SubagentTask) -> SubagentResult:
            async with semaphore:
                return await self.dispatch(task)

        return await asyncio.gather(
            *[dispatch_with_limit(t) for t in tasks]
        )

    def get_routing_summary(self) -> Dict[str, Any]:
        """Get summary of routing decisions.

        Returns:
            Summary dictionary
        """
        if not self._results:
            return {"total_tasks": 0}

        # Count by tier
        tier_counts = {}
        for r in self._results:
            tier = r.tier.value if r.tier else "unknown"
            tier_counts[tier] = tier_counts.get(tier, 0) + 1

        # Count by provider
        provider_counts = {}
        for r in self._results:
            provider_counts[r.provider] = provider_counts.get(r.provider, 0) + 1

        # Total cost
        total_cost = sum(r.cost_usd for r in self._results)

        return {
            "total_tasks": len(self._results),
            "tier_distribution": tier_counts,
            "provider_distribution": provider_counts,
            "total_cost_usd": round(total_cost, 4),
            "avg_latency_ms": sum(r.latency_ms for r in self._results) / len(self._results),
            "success_rate": sum(1 for r in self._results if r.is_success) / len(self._results),
        }

    def reset_stats(self) -> None:
        """Reset accumulated statistics."""
        self._results = []


# Factory functions

def create_subagent_manager(
    default_tier: ModelTier = ModelTier.STANDARD,
) -> LLMSubagentManager:
    """Create a subagent manager with basic configuration.

    Args:
        default_tier: Default tier for tasks

    Returns:
        Configured LLMSubagentManager
    """
    tier_config = ModelTierConfig()
    return LLMSubagentManager(tier_config=tier_config)


def create_task(
    task_type: TaskType,
    prompt: str,
    context: Dict[str, Any],
    **kwargs,
) -> SubagentTask:
    """Create a subagent task.

    Args:
        task_type: Type of task
        prompt: Task prompt
        context: Context data
        **kwargs: Additional task options

    Returns:
        SubagentTask
    """
    return SubagentTask(
        type=task_type,
        prompt=prompt,
        context=context,
        **kwargs,
    )


def estimate_batch_cost(
    tasks: List[SubagentTask],
    tier_config: Optional[ModelTierConfig] = None,
) -> Dict[str, Any]:
    """Estimate cost for a batch of tasks.

    Args:
        tasks: Tasks to estimate
        tier_config: Tier configuration

    Returns:
        Cost estimate dictionary
    """
    config = tier_config or ModelTierConfig()

    tier_counts = {tier: 0 for tier in ModelTier}
    for task in tasks:
        tier = TASK_TIER_DEFAULTS.get(task.type, ModelTier.STANDARD)
        tier_counts[tier] += 1

    # Estimate based on tier weights
    estimated_cost = 0.0
    for tier, count in tier_counts.items():
        weight = config.tier_cost_weights.get(tier, 1.0)
        # Assume ~0.01 base cost per task
        estimated_cost += count * 0.01 * weight

    return {
        "total_tasks": len(tasks),
        "tier_distribution": {t.value: c for t, c in tier_counts.items() if c > 0},
        "estimated_cost_usd": round(estimated_cost, 4),
        "cost_breakdown": {
            tier.value: round(count * 0.01 * config.tier_cost_weights.get(tier, 1.0), 4)
            for tier, count in tier_counts.items()
            if count > 0
        },
    }
