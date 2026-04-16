#!/usr/bin/env python3
"""Verify behavioral signatures for vm-001-classic functions."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from graph_cache import load_graph

def main():
    graph = load_graph("projects/pattern-rewrite/ReentrancyTest.sol")

    print("=" * 80)
    print("BEHAVIORAL SIGNATURE VERIFICATION")
    print("=" * 80)
    print()

    # Expected vulnerable functions
    vulnerable_functions = [
        "withdraw(uint256)",
        "extract(uint256)",
        "fn_0x123abc(uint256)",
        "removeFunds(uint256)",
        "extractShares(uint256)",
        "quickWithdraw(uint256)",
    ]

    print("VULNERABLE FUNCTIONS (should have R:bal→X:out→W:bal signature):")
    print()
    for func_name in vulnerable_functions:
        for node in graph.nodes.values():
            if node.type == "Function" and node.label == func_name:
                sig = node.properties.get("behavioral_signature", "")
                sem_ops = node.properties.get("semantic_operations", [])

                print(f"Function: {func_name}")
                print(f"  Behavioral Signature: {sig}")
                print(f"  Semantic Operations:  {sem_ops}")

                # Check for reentrancy signature
                has_read_bal = "R:bal" in sig
                has_external = "X:out" in sig
                has_write_bal = "W:bal" in sig

                print(f"  Contains R:bal? {has_read_bal}")
                print(f"  Contains X:out? {has_external}")
                print(f"  Contains W:bal? {has_write_bal}")

                if has_read_bal and has_external and has_write_bal:
                    # Check ordering
                    r_pos = sig.index("R:bal")
                    x_pos = sig.index("X:out")
                    w_pos = sig.index("W:bal")

                    # Vulnerable: external call before balance write
                    if x_pos < w_pos:
                        print(f"  ✓ VULNERABLE: X:out before W:bal (CEI violation)")
                    else:
                        print(f"  ✗ SAFE: W:bal before X:out (CEI correct)")
                else:
                    print(f"  ✗ Missing signature components")

                print()
                break

    # Expected safe functions
    safe_functions = [
        "withdrawSafe(uint256)",
        "withdrawWithGuard(uint256)",
    ]

    print()
    print("SAFE FUNCTIONS (should have W:bal→X:out or nonReentrant):")
    print()
    for func_name in safe_functions:
        for node in graph.nodes.values():
            if node.type == "Function" and node.label == func_name:
                sig = node.properties.get("behavioral_signature", "")
                has_guard = node.properties.get("has_reentrancy_guard", False)

                print(f"Function: {func_name}")
                print(f"  Behavioral Signature: {sig}")
                print(f"  Has Reentrancy Guard: {has_guard}")

                if has_guard:
                    print(f"  ✓ SAFE: Reentrancy guard present")
                elif "W:bal" in sig and "X:out" in sig:
                    w_pos = sig.index("W:bal")
                    x_pos = sig.index("X:out")
                    if w_pos < x_pos:
                        print(f"  ✓ SAFE: W:bal before X:out (CEI correct)")
                    else:
                        print(f"  ✗ VULNERABLE: X:out before W:bal")
                else:
                    print(f"  ? No clear signature")

                print()
                break

if __name__ == "__main__":
    main()
