"""ContextMergeAgent - produces verified context bundles for single vuln class.

Per 05.5-CONTEXT.md:
- Quality loop: merge -> verify -> retry with feedback (max 3)
- On success: create bead via factory
- Abort on schema errors (missing vulndoc)
- Retry on quality errors (incomplete fields, low quality)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from alphaswarm_sol.agents.context.bead_factory import ContextBeadFactory
    from alphaswarm_sol.agents.context.merger import ContextMerger
    from alphaswarm_sol.agents.context.verifier import ContextVerifier
    from alphaswarm_sol.beads.context_merge import ContextMergeBead
    from alphaswarm_sol.context.schema import ProtocolContextPack


@dataclass
class ContextMergeConfig:
    """Configuration for ContextMergeAgent.

    Attributes:
        max_retries: Maximum retry attempts on verification failure (default 3)
        abort_on_schema_error: Whether to abort on schema errors (default True)
        retry_on_quality_error: Whether to retry on quality errors (default True)
    """

    max_retries: int = 3
    abort_on_schema_error: bool = True
    retry_on_quality_error: bool = True


@dataclass
class ContextMergeResult:
    """Result of ContextMergeAgent execution.

    Attributes:
        success: Whether bead creation succeeded
        bead: Created ContextMergeBead (None if failed)
        vuln_class: Vulnerability class processed
        attempts: Number of merge attempts made
        errors: List of error messages
        final_quality_score: Final quality score (0.0 if failed)
    """

    success: bool
    bead: Optional[ContextMergeBead]
    vuln_class: str
    attempts: int
    errors: List[str] = field(default_factory=list)
    final_quality_score: float = 0.0


class ContextMergeAgent:
    """Agent that produces verified context bundles for a single vulnerability class.

    This agent implements the quality loop:
    1. Merge context sources (vulndoc + protocol + additional)
    2. Verify bundle completeness and quality
    3. If verification fails: retry with feedback (max 3 attempts)
    4. If verification passes: create bead via factory
    5. Return result

    The agent is responsible for a single vulnerability class and runs
    as part of a parallel batch orchestrated by SubCoordinator.

    Attributes:
        MODEL: Claude model to use for this agent
        ROLE: Agent role for tracking
        merger: ContextMerger instance
        verifier: ContextVerifier instance
        bead_factory: ContextBeadFactory instance
        config: ContextMergeConfig instance
    """

    MODEL = "claude-sonnet-4-5"
    ROLE = "COORDINATOR"

    def __init__(
        self,
        merger: ContextMerger,
        verifier: ContextVerifier,
        bead_factory: ContextBeadFactory,
        config: Optional[ContextMergeConfig] = None,
    ):
        """Initialize ContextMergeAgent.

        Args:
            merger: ContextMerger for merging context sources
            verifier: ContextVerifier for quality validation
            bead_factory: ContextBeadFactory for bead creation
            config: Optional configuration (uses defaults if None)
        """
        self.merger = merger
        self.verifier = verifier
        self.bead_factory = bead_factory
        self.config = config or ContextMergeConfig()

    def execute(
        self,
        vuln_class: str,
        protocol_pack: ProtocolContextPack,
        target_scope: List[str],
        pool_id: Optional[str] = None,
    ) -> ContextMergeResult:
        """Execute context merge with quality loop.

        Args:
            vuln_class: Vulnerability class (e.g., "reentrancy/classic")
            protocol_pack: Protocol context pack
            target_scope: List of contract files to analyze
            pool_id: Optional pool ID for bead association

        Returns:
            ContextMergeResult with success status and bead
        """
        errors: List[str] = []
        attempts = 0
        feedback: Optional[str] = None

        while attempts < self.config.max_retries:
            attempts += 1

            # Phase 1: Merge context sources
            merge_result = self.merger.merge(
                vuln_class=vuln_class,
                protocol_pack=protocol_pack,
                target_scope=target_scope,
                additional_context={"feedback": feedback} if feedback else None,
            )

            if not merge_result.success:
                errors.extend(merge_result.errors)

                # Check if this is a schema error (missing vulndoc)
                schema_error = any(
                    "not found" in err.lower() or "missing" in err.lower()
                    for err in merge_result.errors
                )

                if schema_error and self.config.abort_on_schema_error:
                    # Abort immediately on schema errors
                    return ContextMergeResult(
                        success=False,
                        bead=None,
                        vuln_class=vuln_class,
                        attempts=attempts,
                        errors=errors,
                        final_quality_score=0.0,
                    )

                # Continue retry loop for other errors
                feedback = f"Merge failed: {'; '.join(merge_result.errors)}"
                continue

            # Phase 2: Verify bundle quality
            bundle = merge_result.bundle
            if bundle is None:
                errors.append("Merge succeeded but bundle is None")
                return ContextMergeResult(
                    success=False,
                    bead=None,
                    vuln_class=vuln_class,
                    attempts=attempts,
                    errors=errors,
                    final_quality_score=0.0,
                )

            verification_result = self.verifier.verify(bundle)

            if not verification_result.valid:
                # Verification failed - prepare feedback for retry
                errors.extend([e.message for e in verification_result.errors])

                if self.config.retry_on_quality_error and attempts < self.config.max_retries:
                    # Use verifier's feedback for next attempt
                    feedback = verification_result.feedback_for_retry
                    continue
                else:
                    # Max retries exhausted
                    return ContextMergeResult(
                        success=False,
                        bead=None,
                        vuln_class=vuln_class,
                        attempts=attempts,
                        errors=errors,
                        final_quality_score=verification_result.quality_score,
                    )

            # Phase 3: Create bead from verified merge
            try:
                bead = self.bead_factory.create_from_verified_merge(
                    merge_result=merge_result,
                    verification_result=verification_result,
                    pool_id=pool_id,
                    created_by=f"context-merge-agent-{self.MODEL}",
                )

                # Phase 4: Save bead to storage
                self.bead_factory.save_bead(bead)

                return ContextMergeResult(
                    success=True,
                    bead=bead,
                    vuln_class=vuln_class,
                    attempts=attempts,
                    errors=[],
                    final_quality_score=verification_result.quality_score,
                )

            except Exception as e:
                errors.append(f"Bead creation failed: {e}")
                return ContextMergeResult(
                    success=False,
                    bead=None,
                    vuln_class=vuln_class,
                    attempts=attempts,
                    errors=errors,
                    final_quality_score=verification_result.quality_score,
                )

        # Max retries exhausted without success
        return ContextMergeResult(
            success=False,
            bead=None,
            vuln_class=vuln_class,
            attempts=attempts,
            errors=errors or ["Max retries exhausted"],
            final_quality_score=0.0,
        )
