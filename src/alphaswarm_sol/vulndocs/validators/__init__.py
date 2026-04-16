"""Validators for VulnDocs knowledge pipeline.

Task 18.2: Validation components to ensure quality during knowledge building.
Phase 5.10: Pattern Context Pack (PCP) v2 lint rules.

Key Components:
- IdeaCaptureValidator: Ensures no unique ideas are lost during merging
- CompletenessValidator: Checks document completeness
- QualityScorer: Computes quality scores for documents
- PCPLinter: Lints Pattern Context Pack v2 files for determinism and evidence gating

Design Principle: "Every unique idea captured" guarantee.
Even slightly different scenarios should be preserved - we err on the
side of capturing too much rather than losing valuable information.
"""

from alphaswarm_sol.vulndocs.validators.idea_capture import (
    IdeaCaptureValidator,
    IdeaCapture,
    IdeaCaptureResult,
    IdeaLoss,
    IdeaLossType,
)
from alphaswarm_sol.vulndocs.validators.completeness import (
    CompletenessValidator,
    CompletenessResult,
    SectionCompleteness,
    MissingSectionType,
)
from alphaswarm_sol.vulndocs.validators.quality import (
    QualityScorer,
    QualityScore,
    QualityDimension,
    QualityResult,
)
from alphaswarm_sol.vulndocs.validators.svr_sync import (
    SVRFieldSync,
    SVRFieldSyncResult,
    sync_svr_doc,
    sync_svr_summary,
)
from alphaswarm_sol.vulndocs.validators.pcp_lint import (
    PCPLinter,
    PCPLintResult,
    PCPLintIssue,
    PCPLintSeverity,
    PCPLintRuleId,
    lint_pcp_file,
    lint_pcp_directory,
    validate_pcp_schema,
)

__all__ = [
    # Idea Capture
    "IdeaCaptureValidator",
    "IdeaCapture",
    "IdeaCaptureResult",
    "IdeaLoss",
    "IdeaLossType",
    # Completeness
    "CompletenessValidator",
    "CompletenessResult",
    "SectionCompleteness",
    "MissingSectionType",
    # Quality
    "QualityScorer",
    "QualityScore",
    "QualityDimension",
    "QualityResult",
    # SVR field sync
    "SVRFieldSync",
    "SVRFieldSyncResult",
    "sync_svr_doc",
    "sync_svr_summary",
    # PCP v2 Linting
    "PCPLinter",
    "PCPLintResult",
    "PCPLintIssue",
    "PCPLintSeverity",
    "PCPLintRuleId",
    "lint_pcp_file",
    "lint_pcp_directory",
    "validate_pcp_schema",
]
