"""Ground truth corpus for label evaluation.

This module provides utilities for loading manually verified labels
from YAML files and converting them to LabelOverlay objects for
precision measurement.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from alphaswarm_sol.labels.schema import FunctionLabel, LabelConfidence, LabelSource
from alphaswarm_sol.labels.overlay import LabelOverlay

CORPUS_DIR = Path(__file__).parent


def load_ground_truth(name: str) -> Dict[str, Any]:
    """Load a ground truth file.

    Args:
        name: Name of the ground truth file (without 'labeled_' prefix and '.yaml' suffix)

    Returns:
        Parsed YAML data as dictionary

    Raises:
        FileNotFoundError: If ground truth file doesn't exist
    """
    path = CORPUS_DIR / f"labeled_{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Ground truth not found: {name} (looked for {path})")
    with open(path) as f:
        return yaml.safe_load(f)


def ground_truth_to_overlay(data: Dict[str, Any]) -> LabelOverlay:
    """Convert ground truth data to LabelOverlay.

    Args:
        data: Ground truth data loaded from YAML

    Returns:
        LabelOverlay with all labels from ground truth
    """
    overlay = LabelOverlay()

    # Process main functions
    for func_data in data.get("functions", []):
        _add_function_labels(overlay, func_data)

    # Process additional functions (from additional_functions, auth_functions, etc.)
    for key in data.keys():
        if key.endswith("_functions") and key != "functions":
            for func_data in data.get(key, []):
                _add_function_labels(overlay, func_data)

    return overlay


def _add_function_labels(overlay: LabelOverlay, func_data: Dict[str, Any]) -> None:
    """Add labels from function data to overlay.

    Args:
        overlay: Overlay to add labels to
        func_data: Function data from YAML
    """
    func_id = func_data["function_id"]
    for label_data in func_data.get("labels", []):
        confidence_str = label_data.get("confidence", "medium")
        confidence = LabelConfidence(confidence_str)

        label = FunctionLabel(
            label_id=label_data["label_id"],
            confidence=confidence,
            source=LabelSource.USER_OVERRIDE,  # Ground truth is manually verified
            reasoning=label_data.get("reasoning"),
        )
        overlay.add_label(func_id, label)


def get_expected_findings(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get expected findings from ground truth.

    Args:
        data: Ground truth data loaded from YAML

    Returns:
        List of expected findings with pattern_id, function_id, should_match
    """
    return data.get("expected_findings", [])


def list_ground_truth_files() -> List[str]:
    """List available ground truth files.

    Returns:
        List of ground truth names (without 'labeled_' prefix)
    """
    return [
        p.stem.replace("labeled_", "")
        for p in CORPUS_DIR.glob("labeled_*.yaml")
    ]


def load_all_ground_truth() -> LabelOverlay:
    """Load and merge all ground truth into one overlay.

    Returns:
        LabelOverlay containing all ground truth labels
    """
    overlay = LabelOverlay()
    for name in list_ground_truth_files():
        data = load_ground_truth(name)
        partial = ground_truth_to_overlay(data)
        overlay = overlay.merge(partial)
    return overlay


def get_all_expected_findings() -> List[Dict[str, Any]]:
    """Get all expected findings from all ground truth files.

    Returns:
        List of all expected findings
    """
    findings = []
    for name in list_ground_truth_files():
        data = load_ground_truth(name)
        findings.extend(get_expected_findings(data))
    return findings


def get_ground_truth_function_ids() -> List[str]:
    """Get all function IDs that have ground truth labels.

    Returns:
        List of function IDs with ground truth
    """
    overlay = load_all_ground_truth()
    return overlay.get_all_functions()


def get_ground_truth_label_ids(function_id: str) -> List[str]:
    """Get ground truth label IDs for a specific function.

    Args:
        function_id: Function to get labels for

    Returns:
        List of label IDs from ground truth
    """
    overlay = load_all_ground_truth()
    label_set = overlay.get_labels(function_id)
    return [label.label_id for label in label_set.labels]


__all__ = [
    "CORPUS_DIR",
    "load_ground_truth",
    "ground_truth_to_overlay",
    "get_expected_findings",
    "list_ground_truth_files",
    "load_all_ground_truth",
    "get_all_expected_findings",
    "get_ground_truth_function_ids",
    "get_ground_truth_label_ids",
]
