"""
Workflow Testing Infrastructure for VRS.

This module provides infrastructure for real-world workflow testing using
Claude Code CLI automation.

Components:
- WorkflowEvaluator: Evaluate workflow transcripts against criteria

Usage:
    from alphaswarm_sol.testing.workflow import (
        WorkflowEvaluator,
        EvalStatus,
        EvalCriteria,
        EvalResult,
    )

    # Evaluate result
    criteria = EvalCriteria(expected_patterns=["PASS", "Complete"])
    evaluator = WorkflowEvaluator()
    eval_result = evaluator.evaluate(transcript, criteria)
"""

from alphaswarm_sol.testing.workflow.workflow_evaluator import (
    EvalStatus,
    EvalCriteria,
    EvalError,
    EvalResult,
    WorkflowEvaluator,
)

__all__ = [
    # WorkflowEvaluator
    "EvalStatus",
    "EvalCriteria",
    "EvalError",
    "EvalResult",
    "WorkflowEvaluator",
]
