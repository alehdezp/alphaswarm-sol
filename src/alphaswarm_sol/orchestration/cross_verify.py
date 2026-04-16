"""Cross-model verification for batch dismissals.

Implements multi-model verification to reduce correlated hallucination risk.
Per CONTEXT.md: Different models required for cross-agent verification.

Key principles:
- Model diversity reduces hallucination correlation
- 2-of-2 agreement required for dismissal
- Conflict = NOT dismissed (conservative)
- Fallback to skeptical prompting if only one provider available

Usage:
    from alphaswarm_sol.orchestration.cross_verify import (
        CrossModelVerifier, VerificationResult, get_diverse_verifier
    )

    # Get verifier with diverse providers
    verifier = get_diverse_verifier()

    # Verify a dismissal decision
    result = verifier.verify_dismissal(
        bead_ids=["VKG-001", "VKG-002"],
        dismissal_reason=reason,
        beads=beads
    )

    if result.consensus:
        print("Both models agree - safe to dismiss")
    else:
        print(f"Conflict: {result.conflict_details}")
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING
import asyncio
import logging

if TYPE_CHECKING:
    from alphaswarm_sol.beads.schema import VulnerabilityBead
    from alphaswarm_sol.llm.providers.base import LLMProvider

from .dismissal import DismissalReason

logger = logging.getLogger(__name__)


@dataclass
class VerificationResult:
    """Result of cross-model verification.

    Captures the verification outcome from both models, including
    their individual decisions and reasoning.

    Attributes:
        task_id: Unique ID for this verification task
        primary_model: Name of the primary model used
        secondary_model: Name of the secondary model used
        primary_agrees: Whether primary model agrees with dismissal
        secondary_agrees: Whether secondary model agrees with dismissal
        consensus: Whether both models agree (required for dismissal)
        primary_reasoning: Primary model's reasoning
        secondary_reasoning: Secondary model's reasoning
        conflict_details: Explanation of disagreement if no consensus

    Usage:
        result = VerificationResult(
            task_id="verify-001",
            primary_model="claude-sonnet-4",
            secondary_model="gpt-4o",
            primary_agrees=True,
            secondary_agrees=True,
            consensus=True,
            primary_reasoning="Evidence is sufficient...",
            secondary_reasoning="Agree with dismissal..."
        )

        if result.consensus:
            proceed_with_dismissal()
    """

    task_id: str
    primary_model: str
    secondary_model: str
    primary_agrees: bool
    secondary_agrees: bool
    consensus: bool  # Both must agree
    primary_reasoning: str
    secondary_reasoning: str
    conflict_details: Optional[str] = None
    verified_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "task_id": self.task_id,
            "primary_model": self.primary_model,
            "secondary_model": self.secondary_model,
            "primary_agrees": self.primary_agrees,
            "secondary_agrees": self.secondary_agrees,
            "consensus": self.consensus,
            "primary_reasoning": self.primary_reasoning,
            "secondary_reasoning": self.secondary_reasoning,
            "conflict_details": self.conflict_details,
            "verified_at": self.verified_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VerificationResult":
        """Create VerificationResult from dictionary.

        Args:
            data: Dictionary with result fields

        Returns:
            VerificationResult instance
        """
        verified_at_str = data.get("verified_at")
        if isinstance(verified_at_str, str):
            verified_at = datetime.fromisoformat(verified_at_str)
        else:
            verified_at = datetime.now()

        return cls(
            task_id=str(data.get("task_id", "")),
            primary_model=str(data.get("primary_model", "")),
            secondary_model=str(data.get("secondary_model", "")),
            primary_agrees=bool(data.get("primary_agrees", False)),
            secondary_agrees=bool(data.get("secondary_agrees", False)),
            consensus=bool(data.get("consensus", False)),
            primary_reasoning=str(data.get("primary_reasoning", "")),
            secondary_reasoning=str(data.get("secondary_reasoning", "")),
            conflict_details=data.get("conflict_details"),
            verified_at=verified_at,
        )


class CrossModelVerifier:
    """Verify decisions using multiple LLM models.

    Per CONTEXT.md: Different models required for cross-agent verification.
    This reduces correlated hallucination risk by using diverse model
    architectures or at minimum diverse prompting strategies.

    Model Diversity Strategy:
    1. Best: Different providers (Anthropic + OpenAI)
    2. Good: Different model tiers (Claude Opus + Claude Haiku)
    3. Fallback: Same model with skeptical prompting

    Attributes:
        primary: Primary LLM provider
        secondary: Secondary LLM provider (different model preferred)

    Usage:
        verifier = CrossModelVerifier(
            primary_provider=anthropic_provider,
            secondary_provider=openai_provider
        )

        result = await verifier.verify_dismissal(
            bead_ids=["VKG-001"],
            dismissal_reason=reason,
            beads=beads
        )
    """

    # Model pairs for cross-verification (provider diversity)
    MODEL_PAIRS: List[Tuple[str, str]] = [
        ("claude-sonnet-4", "gpt-4o"),  # Claude + OpenAI
        ("claude-sonnet-4", "claude-haiku"),  # Different Claude tiers
        ("gpt-4o", "claude-opus-4"),  # OpenAI + Claude Opus
        ("gemini-pro", "claude-sonnet-4"),  # Google + Claude
    ]

    def __init__(
        self,
        primary_provider: Optional["LLMProvider"] = None,
        secondary_provider: Optional["LLMProvider"] = None,
    ):
        """Initialize cross-model verifier.

        Args:
            primary_provider: Primary LLM provider
            secondary_provider: Secondary LLM provider (different model preferred)
        """
        self.primary = primary_provider
        self.secondary = secondary_provider
        self._model_diversity = self._assess_model_diversity()

    def _assess_model_diversity(self) -> str:
        """Assess the level of model diversity.

        Returns:
            Diversity level: "high", "medium", or "low"
        """
        if not self.primary:
            return "none"

        if not self.secondary:
            return "low"  # Single provider fallback

        # Check if providers are from different families
        primary_name = getattr(self.primary, "model_name", "")
        secondary_name = getattr(self.secondary, "model_name", "")

        # Different provider families = high diversity
        primary_family = self._get_model_family(primary_name)
        secondary_family = self._get_model_family(secondary_name)

        if primary_family != secondary_family:
            return "high"

        # Same family but different tiers = medium diversity
        if primary_name != secondary_name:
            return "medium"

        return "low"

    def _get_model_family(self, model_name: str) -> str:
        """Get model family from model name.

        Args:
            model_name: Full model name

        Returns:
            Model family (anthropic, openai, google, etc.)
        """
        model_lower = model_name.lower()
        if "claude" in model_lower:
            return "anthropic"
        if "gpt" in model_lower or "o1" in model_lower:
            return "openai"
        if "gemini" in model_lower:
            return "google"
        if "llama" in model_lower:
            return "meta"
        if "mistral" in model_lower:
            return "mistral"
        return "unknown"

    async def verify_dismissal(
        self,
        bead_ids: List[str],
        dismissal_reason: DismissalReason,
        beads: List["VulnerabilityBead"],
    ) -> VerificationResult:
        """Verify dismissal decision with two models.

        Both models must agree for dismissal to proceed.
        Conflict = conservative (NOT dismissed).

        Args:
            bead_ids: IDs of beads being dismissed
            dismissal_reason: Reason for dismissal
            beads: Full bead objects for context

        Returns:
            VerificationResult with consensus status

        Usage:
            result = await verifier.verify_dismissal(
                bead_ids=["VKG-001"],
                dismissal_reason=reason,
                beads=[bead]
            )
            if result.consensus:
                finalize_dismissal()
        """
        task_id = f"verify-dismiss-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Build verification prompt
        prompt = self._build_verification_prompt(beads, dismissal_reason)

        # Get primary opinion
        primary_response = ""
        primary_agrees = False
        primary_model = "unknown"

        if self.primary:
            try:
                primary_model = getattr(self.primary, "model_name", "primary")
                response = await self.primary.generate(
                    prompt=prompt,
                    system=(
                        "You are a security auditor verifying dismissal decisions. "
                        "Respond with 'AGREE' or 'DISAGREE' on the first line, "
                        "followed by your reasoning."
                    ),
                    max_tokens=1024,
                    temperature=0.1,
                )
                primary_response = response.content
                primary_agrees = "AGREE" in primary_response.upper().split("\n")[0]
            except Exception as e:
                logger.warning(f"Primary model verification failed: {e}")
                primary_response = f"Error: {e}"

        # Get secondary opinion (different model or skeptical prompting)
        secondary_response = ""
        secondary_agrees = False
        secondary_model = "unknown"

        if self.secondary:
            try:
                secondary_model = getattr(self.secondary, "model_name", "secondary")
                response = await self.secondary.generate(
                    prompt=prompt,
                    system=(
                        "You are a security auditor verifying dismissal decisions. "
                        "Respond with 'AGREE' or 'DISAGREE' on the first line, "
                        "followed by your reasoning."
                    ),
                    max_tokens=1024,
                    temperature=0.1,
                )
                secondary_response = response.content
                secondary_agrees = "AGREE" in secondary_response.upper().split("\n")[0]
            except Exception as e:
                logger.warning(f"Secondary model verification failed: {e}")
                secondary_response = f"Error: {e}"
        elif self.primary:
            # Fallback: use same provider with skeptical prompting
            try:
                secondary_model = f"{primary_model}-skeptical"
                response = await self.primary.generate(
                    prompt=prompt,
                    system=(
                        "You are a SKEPTICAL security auditor verifying dismissal decisions. "
                        "Your job is to CHALLENGE dismissal decisions and look for reasons "
                        "why the beads might still be valid vulnerabilities. "
                        "Respond with 'AGREE' or 'DISAGREE' on the first line, "
                        "followed by your reasoning. Err on the side of DISAGREE if uncertain."
                    ),
                    max_tokens=1024,
                    temperature=0.1,  # More deterministic skeptical review
                )
                secondary_response = response.content
                secondary_agrees = "AGREE" in secondary_response.upper().split("\n")[0]
            except Exception as e:
                logger.warning(f"Skeptical verification failed: {e}")
                secondary_response = f"Error: {e}"

        # Determine consensus (both must agree)
        consensus = primary_agrees and secondary_agrees

        # Build conflict explanation if no consensus
        conflict_details = None
        if not consensus:
            conflict_details = self._explain_conflict(primary_agrees, secondary_agrees)

        logger.info(
            f"Cross-model verification: {task_id} - "
            f"primary ({primary_model}): {'AGREE' if primary_agrees else 'DISAGREE'}, "
            f"secondary ({secondary_model}): {'AGREE' if secondary_agrees else 'DISAGREE'} "
            f"-> {'CONSENSUS' if consensus else 'CONFLICT'}"
        )

        return VerificationResult(
            task_id=task_id,
            primary_model=primary_model,
            secondary_model=secondary_model,
            primary_agrees=primary_agrees,
            secondary_agrees=secondary_agrees,
            consensus=consensus,
            primary_reasoning=primary_response,
            secondary_reasoning=secondary_response,
            conflict_details=conflict_details,
        )

    def verify_dismissal_sync(
        self,
        bead_ids: List[str],
        dismissal_reason: DismissalReason,
        beads: List["VulnerabilityBead"],
    ) -> VerificationResult:
        """Synchronous wrapper for verify_dismissal.

        Args:
            bead_ids: IDs of beads being dismissed
            dismissal_reason: Reason for dismissal
            beads: Full bead objects for context

        Returns:
            VerificationResult with consensus status
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self.verify_dismissal(bead_ids, dismissal_reason, beads)
        )

    def _build_verification_prompt(
        self,
        beads: List["VulnerabilityBead"],
        reason: DismissalReason,
    ) -> str:
        """Build prompt for verification.

        Args:
            beads: Beads being dismissed
            reason: Dismissal reason

        Returns:
            Verification prompt string
        """
        # Build bead summaries
        bead_summaries = []
        for bead in beads:
            summary = (
                f"- {bead.id}: {bead.vulnerability_class} in "
                f"{bead.vulnerable_code.contract_name or 'unknown'}."
                f"{bead.vulnerable_code.function_name or 'unknown'}()"
            )
            bead_summaries.append(summary)

        bead_list = "\n".join(bead_summaries) if bead_summaries else "No beads provided"

        # Build evidence list
        evidence_list = "\n".join(f"- {e}" for e in reason.evidence) if reason.evidence else "No evidence provided"

        return f"""Verify this batch dismissal decision:

## Beads to Dismiss
{bead_list}

## Dismissal Reason
Category: {reason.category.value}
Explanation: {reason.explanation}

Evidence:
{evidence_list}

## Your Task
1. Review the evidence supporting dismissal
2. Consider if any bead might still be a real vulnerability
3. Check if the dismissal category is appropriate
4. Decide: AGREE (safe to dismiss) or DISAGREE (keep for verification)

Respond with AGREE or DISAGREE on the first line, then explain your reasoning.
If you DISAGREE, explain what concerns you have about the dismissal.
"""

    def _explain_conflict(self, primary: bool, secondary: bool) -> str:
        """Explain why models disagreed.

        Args:
            primary: Primary model agrees
            secondary: Secondary model agrees

        Returns:
            Explanation of disagreement
        """
        if primary and not secondary:
            return "Primary model agreed but secondary model raised concerns"
        elif not primary and secondary:
            return "Secondary model agreed but primary model raised concerns"
        else:
            return "Both models raised concerns about the dismissal"

    @property
    def diversity_level(self) -> str:
        """Get the model diversity level."""
        return self._model_diversity


def get_diverse_verifier(
    prefer_provider: Optional[str] = None,
) -> CrossModelVerifier:
    """Get verifier with diverse model providers.

    Tries to use different providers (Anthropic + OpenAI) for maximum
    diversity. Falls back to single provider with skeptical prompting
    if only one provider is available.

    Args:
        prefer_provider: Preferred provider for primary ("anthropic", "openai")

    Returns:
        CrossModelVerifier with best available diversity

    Usage:
        verifier = get_diverse_verifier()
        print(f"Diversity level: {verifier.diversity_level}")
    """
    primary = None
    secondary = None

    # Try to load providers
    try:
        from alphaswarm_sol.llm.providers import AnthropicProvider
        from alphaswarm_sol.llm.config import get_provider_config

        config = get_provider_config("anthropic")
        primary = AnthropicProvider(config)
        logger.debug("Loaded Anthropic provider for primary verification")
    except Exception as e:
        logger.debug(f"Could not load Anthropic provider: {e}")

    try:
        from alphaswarm_sol.llm.providers import OpenAIProvider
        from alphaswarm_sol.llm.config import get_provider_config

        config = get_provider_config("openai")
        secondary = OpenAIProvider(config)
        logger.debug("Loaded OpenAI provider for secondary verification")
    except Exception as e:
        logger.debug(f"Could not load OpenAI provider: {e}")

    # Swap if user prefers OpenAI as primary
    if prefer_provider == "openai" and secondary:
        primary, secondary = secondary, primary

    # If no secondary, primary will use skeptical prompting fallback
    verifier = CrossModelVerifier(primary, secondary)

    logger.info(
        f"Created CrossModelVerifier with diversity level: {verifier.diversity_level}"
    )

    return verifier


def create_mock_verifier() -> CrossModelVerifier:
    """Create a mock verifier for testing.

    Returns:
        CrossModelVerifier with mock providers
    """
    try:
        from alphaswarm_sol.llm.providers import MockProvider
        from alphaswarm_sol.llm.config import ProviderConfig, LLMProviderType

        primary_config = ProviderConfig(
            provider=LLMProviderType.MOCK,
            model="mock-primary",
            api_key="mock",
            cost_per_1m_input=0.0,
            cost_per_1m_output=0.0,
        )
        secondary_config = ProviderConfig(
            provider=LLMProviderType.MOCK,
            model="mock-secondary",
            api_key="mock",
            cost_per_1m_input=0.0,
            cost_per_1m_output=0.0,
        )

        return CrossModelVerifier(
            primary_provider=MockProvider(primary_config),
            secondary_provider=MockProvider(secondary_config),
        )
    except ImportError:
        # Return empty verifier if mock provider not available
        return CrossModelVerifier()


# Export for module
__all__ = [
    "VerificationResult",
    "CrossModelVerifier",
    "get_diverse_verifier",
    "create_mock_verifier",
]
