"""Ground truth corpus for label evaluation.

This package provides manually verified labels for test contracts,
used to measure labeler precision and detection improvement.

Usage:
    from tests.labels.ground_truth import (
        load_ground_truth,
        ground_truth_to_overlay,
        get_expected_findings,
        list_ground_truth_files,
        load_all_ground_truth,
    )

    # List available ground truth files
    files = list_ground_truth_files()  # ['access_control', 'value_handling']

    # Load all ground truth as overlay
    overlay = load_all_ground_truth()

    # Get labels for a specific function
    labels = overlay.get_labels("ReentrancyClassic.withdraw")
"""

from .corpus import (
    CORPUS_DIR,
    load_ground_truth,
    ground_truth_to_overlay,
    get_expected_findings,
    list_ground_truth_files,
    load_all_ground_truth,
    get_all_expected_findings,
    get_ground_truth_function_ids,
    get_ground_truth_label_ids,
)

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
