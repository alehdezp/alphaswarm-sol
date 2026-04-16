#!/usr/bin/env python3
"""Analyze vm-001-classic pattern metrics for Iteration 2."""

import sys
from pathlib import Path

# Add tests directory to path
sys.path.insert(0, str(Path(__file__).parent))

from graph_cache import load_graph
from pattern_loader import load_all_patterns
from alphaswarm_sol.queries.patterns import PatternEngine

def main():
    patterns = list(load_all_patterns())
    engine = PatternEngine()

    # Load the graph
    graph = load_graph("projects/pattern-rewrite/ReentrancyTest.sol")

    # Run the pattern
    findings = engine.run(graph, patterns, pattern_ids=["vm-001-classic"], limit=200)

    # Extract labels
    labels = {finding["node_label"] for finding in findings if finding["pattern_id"] == "vm-001-classic"}

    print("=" * 80)
    print("vm-001-classic ITERATION 2 ANALYSIS")
    print("=" * 80)
    print()

    # ========================================================================
    # TRUE POSITIVES (should be flagged as vulnerable)
    # ========================================================================

    true_positives = [
        "withdraw(uint256)",           # TP1: Classic withdraw with balances
        "extract(uint256)",            # TP2: Uses 'funds' variable
        "fn_0x123abc(uint256)",        # TP3: Uses 'shares' variable
        "withdrawViaCall(uint256)",    # TP4: call() instead of transfer()
        "withdrawViaSend(uint256)",    # TP5: send() instead of transfer()
        "withdrawNoGuard(uint256)",    # TP6: Inheritance without guard
        "withdrawTokens(uint256)",     # TP7: ERC777 callback reentrancy
        "withdrawBalance(uint256)",    # TP8: Cross-function reentrancy
        "removeFunds(uint256)",        # VARIATION1: userDeposits variable
        "extractShares(uint256)",      # VARIATION2: accountShares variable
        "quickWithdraw(uint256)",      # VARIATION3: userDeposits (compact style)
        "init(uint256)",               # EDGE9: Fake initializer (no guard)
    ]

    tp_count = 0
    fn_count = 0

    print("TRUE POSITIVES (should be flagged):")
    for func in true_positives:
        if func in labels:
            print(f"  ✓ {func}")
            tp_count += 1
        else:
            print(f"  ✗ {func} (FALSE NEGATIVE)")
            fn_count += 1

    print(f"\nTP: {tp_count}/{len(true_positives)}")
    print()

    # ========================================================================
    # TRUE NEGATIVES (should NOT be flagged)
    # ========================================================================

    true_negatives = [
        "withdrawSafe(uint256)",                # TN1: Correct CEI pattern
        "withdrawWithGuard(uint256)",           # TN2: Has nonReentrant
        "withdrawWithRenamedGuard(uint256)",    # TN3: Has renamed guard
        "getBalance(address)",                  # TN4: View function
        "donate()",                             # TN5: No balance write
        "updateBalance(address,uint256)",       # TN6: No transfer
        "withdrawTokensSafe(uint256)",          # TN7: Safe token withdrawal
        "_internalWithdraw(address,uint256)",   # EDGE1: Internal function
        "_privateWithdraw(address,uint256)",    # EDGE2: Private function
        "calculate(uint256,uint256)",           # EDGE3: Pure function
        "withdrawWithInheritedGuard(uint256)",  # EDGE7: Inherited guard
        "initialize(address[],uint256[])",      # EDGE8: True initializer
    ]

    tn_count = 0
    fp_count = 0

    print("TRUE NEGATIVES (should NOT be flagged):")
    for func in true_negatives:
        if func in labels:
            print(f"  ✗ {func} (FALSE POSITIVE)")
            fp_count += 1
        else:
            print(f"  ✓ {func}")
            tn_count += 1

    print(f"\nTN: {tn_count}/{len(true_negatives)}")
    print()

    # ========================================================================
    # VARIATION TESTS (naming conventions)
    # ========================================================================

    variations_tested = [
        ("balances", "withdraw(uint256)"),              # Standard naming
        ("funds", "extract(uint256)"),                  # Alternative 1
        ("shares", "fn_0x123abc(uint256)"),            # Alternative 2
        ("userDeposits", "removeFunds(uint256)"),      # Alternative 3
        ("accountShares", "extractShares(uint256)"),   # Alternative 4
    ]

    variations_passed = 0
    variations_failed = 0

    print("VARIATION TESTS (naming conventions):")
    for var_name, func in variations_tested:
        if func in labels:
            print(f"  ✓ {var_name:15} -> {func}")
            variations_passed += 1
        else:
            print(f"  ✗ {var_name:15} -> {func} (NOT DETECTED)")
            variations_failed += 1

    print(f"\nVariations Passed: {variations_passed}/{len(variations_tested)}")
    print()

    # ========================================================================
    # METRICS CALCULATION
    # ========================================================================

    precision = tp_count / (tp_count + fp_count) if (tp_count + fp_count) > 0 else 0
    recall = tp_count / (tp_count + fn_count) if (tp_count + fn_count) > 0 else 0
    variation_score = variations_passed / len(variations_tested) if len(variations_tested) > 0 else 0

    print("=" * 80)
    print("METRICS")
    print("=" * 80)
    print(f"True Positives:   {tp_count}")
    print(f"False Positives:  {fp_count}")
    print(f"True Negatives:   {tn_count}")
    print(f"False Negatives:  {fn_count}")
    print()
    print(f"Precision:        {precision:.2%} ({tp_count}/{tp_count + fp_count})")
    print(f"Recall:           {recall:.2%} ({tp_count}/{tp_count + fn_count})")
    print(f"Variation Score:  {variation_score:.2%} ({variations_passed}/{len(variations_tested)})")
    print()

    # ========================================================================
    # RATING DETERMINATION
    # ========================================================================

    print("=" * 80)
    print("RATING DETERMINATION")
    print("=" * 80)
    print()

    # Rating thresholds
    if precision < 0.70 or recall < 0.50 or variation_score < 0.60:
        status = "draft"
        reason = []
        if precision < 0.70:
            reason.append(f"Precision {precision:.2%} < 70%")
        if recall < 0.50:
            reason.append(f"Recall {recall:.2%} < 50%")
        if variation_score < 0.60:
            reason.append(f"Variation {variation_score:.2%} < 60%")
        print(f"Status: DRAFT")
        print(f"Reason: {', '.join(reason)}")
    elif precision >= 0.90 and recall >= 0.85 and variation_score >= 0.85:
        status = "excellent"
        print(f"Status: EXCELLENT")
        print(f"Reason: All metrics exceed excellence thresholds")
        print(f"  - Precision {precision:.2%} >= 90%")
        print(f"  - Recall {recall:.2%} >= 85%")
        print(f"  - Variation {variation_score:.2%} >= 85%")
    else:
        status = "ready"
        print(f"Status: READY")
        print(f"Reason: All metrics meet ready thresholds but not excellent")
        print(f"  - Precision {precision:.2%} >= 70%")
        print(f"  - Recall {recall:.2%} >= 50%")
        print(f"  - Variation {variation_score:.2%} >= 60%")

    print()

    # ========================================================================
    # ITERATION COMPARISON
    # ========================================================================

    print("=" * 80)
    print("ITERATION COMPARISON")
    print("=" * 80)
    print()
    print("Metric           | Iteration 1 | Iteration 2 | Change")
    print("-" * 65)
    print(f"Precision        | 100%        | {precision:.2%}       | {precision - 1.0:+.2%}")
    print(f"Recall           | 58%         | {recall:.2%}       | {recall - 0.58:+.2%}")
    print(f"Variation Score  | 0%          | {variation_score:.2%}       | {variation_score - 0.0:+.2%}")
    print(f"Status           | draft       | {status:9}   |")
    print()

    # ========================================================================
    # DETAILED FINDINGS
    # ========================================================================

    if fn_count > 0 or fp_count > 0:
        print("=" * 80)
        print("ISSUES TO INVESTIGATE")
        print("=" * 80)
        print()

        if fn_count > 0:
            print(f"FALSE NEGATIVES ({fn_count}):")
            for func in true_positives:
                if func not in labels:
                    print(f"  - {func}")
            print()

        if fp_count > 0:
            print(f"FALSE POSITIVES ({fp_count}):")
            for func in true_negatives:
                if func in labels:
                    print(f"  - {func}")
            print()

    # ========================================================================
    # ALL FINDINGS
    # ========================================================================

    print("=" * 80)
    print(f"ALL FINDINGS ({len(labels)} functions flagged)")
    print("=" * 80)
    for label in sorted(labels):
        print(f"  - {label}")
    print()

    return {
        "precision": precision,
        "recall": recall,
        "variation_score": variation_score,
        "status": status,
        "tp_count": tp_count,
        "fp_count": fp_count,
        "tn_count": tn_count,
        "fn_count": fn_count,
    }

if __name__ == "__main__":
    main()
