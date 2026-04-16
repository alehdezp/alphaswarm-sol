"""Improvement loop with Jujutsu workspace isolation.

Plan 12 Part 1 (3.1c scope): WorkspaceManager API for safe prompt mutation.
Parts 2-5 (improvement loop, metaprompting, failure reporter) are 3.1f scope —
this module provides the isolation infrastructure they depend on.

CRITICAL SAFETY INVARIANT:
    improvement.py MUST NEVER modify production `.claude/` directly.
    All prompt mutations happen in Jujutsu workspaces.
    Violation triggers HALT.

DC-2 enforcement: No imports from kg or vulndocs subpackages.

Key types:
- WorkspaceManager: Creates/manages Jujutsu workspaces for variant testing
- CalibrationGuard: Verifies CalibrationConfig matches EvaluatorConstants
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

# Safety: directories that MUST NOT be modified without workspace isolation
PROTECTED_PATHS = frozenset({
    ".claude/",
    ".claude/agents/",
    ".claude/skills/",
})

CALIBRATION_CONFIG_PATH = Path(".vrs/evaluations/calibration_config.yaml")


class WorkspaceIsolationError(Exception):
    """Raised when code attempts to modify production paths without isolation."""


class CalibrationMismatchError(Exception):
    """Raised when CalibrationConfig doesn't match EvaluatorConstants."""


class WorkspaceManager:
    """Manages Jujutsu workspaces for isolated variant testing.

    SAFETY: All prompt changes happen ONLY in workspaces, never in
    production `.claude/`. WorkspaceManager enforces this invariant.

    API documented for 3.1f Variant Tester wrapper (~50 LOC).

    Usage:
        manager = WorkspaceManager()
        workspace = manager.create_workspace("variant-001")
        try:
            manager.apply_variant(workspace, {"agents/vrs-attacker.md": new_content})
            # Run evaluation in workspace...
        finally:
            manager.discard_workspace(workspace)
    """

    def __init__(self, repo_root: Path | None = None) -> None:
        self._repo_root = repo_root or Path.cwd()
        self._active_workspaces: dict[str, Path] = {}

    def _check_jj_available(self) -> bool:
        """Verify Jujutsu is available."""
        try:
            result = subprocess.run(
                ["jj", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def create_workspace(self, variant_id: str) -> Path:
        """Create isolated Jujutsu workspace for variant testing.

        Args:
            variant_id: Unique identifier for this variant (e.g., "variant-001").

        Returns:
            Path to the workspace root.

        Raises:
            RuntimeError: If Jujutsu is not available or workspace creation fails.
        """
        if not self._check_jj_available():
            raise RuntimeError(
                "Jujutsu (jj) is not available. "
                "Install it: https://martinvonz.github.io/jj/"
            )

        workspace_name = f"variant-{variant_id}"
        workspace_path = self._repo_root / ".jj-workspaces" / workspace_name

        try:
            result = subprocess.run(
                ["jj", "workspace", "add", str(workspace_path)],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self._repo_root),
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"jj workspace add failed: {result.stderr}"
                )
        except subprocess.TimeoutExpired:
            raise RuntimeError("jj workspace add timed out")

        self._active_workspaces[variant_id] = workspace_path
        logger.info("Created workspace: %s at %s", variant_id, workspace_path)
        return workspace_path

    def apply_variant(self, workspace: Path, changes: dict[str, str]) -> None:
        """Apply prompt changes in workspace only.

        Args:
            workspace: Path to the workspace root (from create_workspace).
            changes: Dict mapping relative file paths to new content.
                     Paths must be within .claude/ directory.

        Raises:
            WorkspaceIsolationError: If changes target paths outside workspace.
        """
        # Safety check: verify workspace is a real workspace, not production
        if workspace == self._repo_root:
            raise WorkspaceIsolationError(
                "HALT: Attempted to apply variant to production root. "
                "This is a safety violation. Use create_workspace() first."
            )

        for rel_path, content in changes.items():
            target = workspace / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
            logger.info("Applied variant change: %s", rel_path)

    def discard_workspace(self, workspace: Path) -> None:
        """Clean up workspace after evaluation.

        Args:
            workspace: Path to the workspace root.
        """
        # Find variant_id from workspace path
        variant_id = None
        for vid, wpath in self._active_workspaces.items():
            if wpath == workspace:
                variant_id = vid
                break

        if variant_id:
            del self._active_workspaces[variant_id]

        workspace_name = workspace.name
        try:
            result = subprocess.run(
                ["jj", "workspace", "forget", workspace_name],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self._repo_root),
            )
            if result.returncode != 0:
                logger.warning("jj workspace forget failed: %s", result.stderr)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            logger.warning("Failed to forget workspace: %s", workspace_name)

        # Clean up directory
        if workspace.exists():
            import shutil
            shutil.rmtree(workspace, ignore_errors=True)

        logger.info("Discarded workspace: %s", workspace_name)

    @property
    def active_workspaces(self) -> dict[str, Path]:
        """Return currently active workspaces."""
        return dict(self._active_workspaces)


def check_production_safety(target_path: str | Path) -> None:
    """Startup guard: HALT if any code path writes to .claude/ without isolation.

    This should be called before any write operation in the improvement loop.

    Args:
        target_path: Path being written to.

    Raises:
        WorkspaceIsolationError: If target is a protected production path.
    """
    target = Path(target_path)
    target_str = str(target)

    for protected in PROTECTED_PATHS:
        if target_str.startswith(protected) or f"/{protected}" in target_str:
            # Check if this is inside a workspace (contains .jj-workspaces)
            if ".jj-workspaces/" not in target_str:
                raise WorkspaceIsolationError(
                    f"HALT: Attempted to modify production path '{target_path}' "
                    f"without workspace isolation. Use WorkspaceManager."
                )


class CalibrationGuard:
    """Verifies CalibrationConfig matches EvaluatorConstants at startup.

    Any CalibrationConfig field change requires full anchor re-run.
    """

    @staticmethod
    def verify(config_path: Path | None = None) -> bool:
        """Verify CalibrationConfig on disk matches EvaluatorConstants.

        Returns:
            True if config matches or no config exists yet.

        Raises:
            CalibrationMismatchError: If config exists but doesn't match.
        """
        path = config_path or CALIBRATION_CONFIG_PATH
        if not path.exists():
            logger.info("No CalibrationConfig on disk — first run")
            return True

        with open(path) as f:
            config = yaml.safe_load(f)

        evaluator = config.get("evaluator_config", {})

        # EvaluatorConstants fields — single source of truth
        expected = {
            "evaluator_model": "opus",
            "scoring_scale_min": 0,
            "scoring_scale_max": 100,
            "disagreement_threshold": 15,
            "min_moves_for_assessment": 3,
            "max_token_budget": 6000,
        }

        mismatches = []
        if evaluator.get("evaluator_model") != expected["evaluator_model"]:
            mismatches.append(
                f"evaluator_model: disk={evaluator.get('evaluator_model')}, "
                f"expected={expected['evaluator_model']}"
            )
        if evaluator.get("scoring_scale_min") != expected["scoring_scale_min"]:
            mismatches.append(
                f"scoring_scale_min: disk={evaluator.get('scoring_scale_min')}, "
                f"expected={expected['scoring_scale_min']}"
            )
        if evaluator.get("scoring_scale_max") != expected["scoring_scale_max"]:
            mismatches.append(
                f"scoring_scale_max: disk={evaluator.get('scoring_scale_max')}, "
                f"expected={expected['scoring_scale_max']}"
            )
        if evaluator.get("disagreement_threshold") != expected["disagreement_threshold"]:
            mismatches.append(
                f"disagreement_threshold: disk={evaluator.get('disagreement_threshold')}, "
                f"expected={expected['disagreement_threshold']}"
            )

        if mismatches:
            raise CalibrationMismatchError(
                "CalibrationConfig mismatch — full anchor re-run required:\n"
                + "\n".join(f"  - {m}" for m in mismatches)
            )

        return True
