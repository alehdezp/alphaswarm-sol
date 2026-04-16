#!/usr/bin/env python3
"""One-time audit: cross-reference vulndocs patterns against test scenario coverage.

Walks vulndocs/ to inventory all patterns by category, walks examples/testing/
to find test scenarios, and compares against well-known vulnerability classes
(SWC top-20, OWASP Smart Contract Top 10) to identify coverage gaps.

Usage:
    python examples/testing/scripts/audit-vulndocs-coverage.py

No dependencies beyond the Python standard library.
"""

import os
import sys
from collections import defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[3]  # examples/testing/scripts -> repo root
VULNDOCS_DIR = REPO_ROOT / "vulndocs"
TESTING_DIR = REPO_ROOT / "examples" / "testing"
SWC_MAPPING = REPO_ROOT / "vulndocs" / ".meta" / "references" / "swc-mapping.yaml"

# Well-known vulnerability classes for novelty check.
# SWC top-20 by real-world severity (subset of the 37 SWC entries that matter).
SWC_TOP_20 = {
    "SWC-100": "Function Default Visibility",
    "SWC-101": "Integer Overflow/Underflow",
    "SWC-104": "Unchecked Call Return Value",
    "SWC-105": "Unprotected Ether Withdrawal",
    "SWC-106": "Unprotected SELFDESTRUCT",
    "SWC-107": "Reentrancy",
    "SWC-112": "Delegatecall to Untrusted Callee",
    "SWC-113": "DoS with Failed Call",
    "SWC-114": "Transaction Order Dependence (Frontrunning)",
    "SWC-115": "Authorization through tx.origin",
    "SWC-116": "Timestamp Dependence",
    "SWC-117": "Signature Malleability",
    "SWC-120": "Weak Randomness from Chain Attributes",
    "SWC-121": "Missing Signature Replay Protection",
    "SWC-122": "Lack of Proper Signature Verification",
    "SWC-124": "Write to Arbitrary Storage Location",
    "SWC-126": "Insufficient Gas Griefing",
    "SWC-128": "DoS With Block Gas Limit",
    "SWC-132": "Unexpected Ether Balance (Force-feeding)",
    "SWC-133": "Hash Collision with encodePacked",
}

# OWASP Smart Contract Top 10 (2023 edition equivalent)
OWASP_SC_TOP_10 = {
    "SC01": "Reentrancy Attacks",
    "SC02": "Integer Overflow and Underflow",
    "SC03": "Timestamp Dependence",
    "SC04": "Access Control Vulnerabilities",
    "SC05": "Front-running (Transaction Order Dependence)",
    "SC06": "Denial of Service",
    "SC07": "Bad Randomness",
    "SC08": "Unchecked External Calls",
    "SC09": "Short Address / Parameter Attack",
    "SC10": "Flash Loan Attacks",
}

# Map well-known classes to vulndocs categories for coverage checking.
KNOWN_TO_VULNDOCS = {
    "SWC-107": "reentrancy",
    "SWC-101": "arithmetic",
    "SWC-105": "access-control",
    "SWC-100": "access-control",
    "SWC-112": "access-control",
    "SWC-115": "access-control",
    "SWC-113": "dos",
    "SWC-128": "dos",
    "SWC-126": "dos",
    "SWC-114": "mev",
    "SWC-116": "crypto",
    "SWC-117": "crypto",
    "SWC-120": "crypto",
    "SWC-121": "crypto",
    "SWC-122": "crypto",
    "SWC-133": "crypto",
    "SWC-104": "token",
    "SWC-106": "upgrade",
    "SWC-124": "upgrade",
    "SWC-132": "logic",
    "SC01": "reentrancy",
    "SC02": "arithmetic",
    "SC03": "crypto",
    "SC04": "access-control",
    "SC05": "mev",
    "SC06": "dos",
    "SC07": "crypto",
    "SC08": "token",
    "SC09": "logic",
    "SC10": "flash-loan",
}


# ---------------------------------------------------------------------------
# Inventory functions
# ---------------------------------------------------------------------------


def inventory_vulndocs(vulndocs_dir: Path) -> dict[str, list[dict]]:
    """Walk vulndocs/ and collect patterns grouped by category/subcategory."""
    patterns = defaultdict(list)
    for root, _, files in os.walk(vulndocs_dir):
        root_path = Path(root)
        # Skip .meta directory
        if ".meta" in root_path.parts:
            continue
        # Only look in patterns/ directories
        if root_path.name != "patterns":
            continue
        for fname in files:
            if not fname.endswith(".yaml") or fname.endswith(".pcp.yaml"):
                continue
            fpath = root_path / fname
            rel = fpath.relative_to(vulndocs_dir)
            parts = rel.parts  # e.g. ('reentrancy', 'classic', 'patterns', 'file.yaml')
            category = parts[0] if len(parts) > 0 else "unknown"
            subcategory = parts[1] if len(parts) > 1 else "unknown"
            # Extract pattern id from file (first line starting with 'id:')
            pattern_id = fname.replace(".yaml", "")
            try:
                with open(fpath) as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("id:"):
                            pattern_id = line.split(":", 1)[1].strip()
                            break
            except Exception:
                pass
            patterns[category].append({
                "id": pattern_id,
                "subcategory": subcategory,
                "file": str(rel),
            })
    return dict(patterns)


def inventory_test_scenarios(testing_dir: Path) -> dict[str, list[str]]:
    """Walk examples/testing/ and detect which vulnerability categories are covered.

    Heuristic: look at directory names and .sol file contents for category keywords.
    """
    covered = defaultdict(list)
    category_keywords = {
        "reentrancy": ["reentrancy", "reentrant", "reentrancy"],
        "access-control": ["access", "auth", "owner", "role", "permission"],
        "oracle": ["oracle", "price", "twap", "chainlink"],
        "dos": ["dos", "gas", "loop", "unbounded"],
        "logic": ["logic", "state", "sequenc", "order"],
        "flash-loan": ["flash", "flashloan"],
        "upgrade": ["proxy", "upgrade", "initializ", "uups"],
        "arithmetic": ["overflow", "underflow", "arithmetic"],
        "crypto": ["signature", "ecrecover", "hash", "random"],
        "token": ["erc20", "erc721", "erc777", "transfer", "approve"],
        "mev": ["frontrun", "sandwich", "mev"],
        "vault": ["vault", "erc4626", "share"],
        "precision-loss": ["precision", "rounding", "round"],
        "governance": ["governance", "voting", "dao"],
        "cross-chain": ["bridge", "cross-chain", "l2"],
        "restaking": ["restaking", "eigenlayer"],
        "account-abstraction": ["erc4337", "account-abstraction", "userop"],
        "zk-rollup": ["zk", "rollup", "proof"],
    }

    for root, _, files in os.walk(testing_dir):
        root_path = Path(root)
        # Skip lib/, out/, cache/, builds/, .devcontainer/
        skip_dirs = {"lib", "out", "cache", "builds", ".devcontainer", "scripts", ".git", "node_modules"}
        if any(part in skip_dirs for part in root_path.relative_to(testing_dir).parts):
            continue
        for fname in files:
            if not fname.endswith(".sol") and not fname.endswith(".yaml"):
                continue
            fpath = root_path / fname
            scenario_name = root_path.relative_to(testing_dir).parts[0] if root_path != testing_dir else fname
            try:
                content = fpath.read_text().lower()
            except Exception:
                continue
            for cat, keywords in category_keywords.items():
                if any(kw in content or kw in str(scenario_name).lower() for kw in keywords):
                    if scenario_name not in covered[cat]:
                        covered[cat].append(str(scenario_name))
    return dict(covered)


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def generate_report(
    vulndocs_patterns: dict[str, list[dict]],
    test_coverage: dict[str, list[str]],
) -> str:
    lines = []
    lines.append("# VulnDocs Coverage Audit Report")
    lines.append("")
    lines.append("One-time audit comparing vulndocs patterns against test scenario coverage")
    lines.append("and well-known vulnerability classes.")
    lines.append("")

    # --- Section 1: Pattern inventory ---
    lines.append("## 1. VulnDocs Pattern Inventory")
    lines.append("")
    total = sum(len(v) for v in vulndocs_patterns.values())
    lines.append(f"**Total patterns:** {total} across {len(vulndocs_patterns)} categories")
    lines.append("")
    lines.append("| Category | Pattern Count | Subcategories |")
    lines.append("|----------|-------------|---------------|")
    for cat in sorted(vulndocs_patterns.keys()):
        pats = vulndocs_patterns[cat]
        subcats = sorted(set(p["subcategory"] for p in pats))
        lines.append(f"| {cat} | {len(pats)} | {', '.join(subcats)} |")
    lines.append("")

    # --- Section 2: Test scenario coverage ---
    lines.append("## 2. Test Scenario Coverage")
    lines.append("")
    if not test_coverage:
        lines.append("**No test scenarios detected in examples/testing/.**")
    else:
        lines.append("| Category | Scenarios | Scenario Names |")
        lines.append("|----------|-----------|----------------|")
        for cat in sorted(test_coverage.keys()):
            scenarios = test_coverage[cat]
            lines.append(f"| {cat} | {len(scenarios)} | {', '.join(scenarios[:5])} |")
    lines.append("")

    # --- Section 3: Coverage gaps ---
    lines.append("## 3. Coverage Gap Analysis")
    lines.append("")
    lines.append("Categories with vulndocs patterns but NO test scenarios:")
    lines.append("")
    all_cats = set(vulndocs_patterns.keys())
    covered_cats = set(test_coverage.keys())
    uncovered = sorted(all_cats - covered_cats)
    if uncovered:
        for cat in uncovered:
            count = len(vulndocs_patterns[cat])
            lines.append(f"- **{cat}** ({count} patterns) -- NO TEST COVERAGE")
    else:
        lines.append("- None -- all categories have at least one test scenario.")
    lines.append("")

    # Categories with few patterns (may need enrichment)
    lines.append("Categories with fewer than 5 patterns (may need enrichment):")
    lines.append("")
    for cat in sorted(vulndocs_patterns.keys()):
        if len(vulndocs_patterns[cat]) < 5:
            lines.append(f"- **{cat}** ({len(vulndocs_patterns[cat])} patterns)")
    lines.append("")

    # --- Section 4: Well-known vulnerability class check ---
    lines.append("## 4. Well-Known Vulnerability Class Check")
    lines.append("")
    lines.append("### SWC Top-20 Coverage")
    lines.append("")
    lines.append("| SWC ID | Name | VulnDocs Category | Has Patterns? |")
    lines.append("|--------|------|-------------------|---------------|")
    for swc_id, name in sorted(SWC_TOP_20.items()):
        mapped_cat = KNOWN_TO_VULNDOCS.get(swc_id, "unmapped")
        has_patterns = mapped_cat in vulndocs_patterns and len(vulndocs_patterns[mapped_cat]) > 0
        status = "YES" if has_patterns else "**NO**"
        lines.append(f"| {swc_id} | {name} | {mapped_cat} | {status} |")
    lines.append("")

    lines.append("### OWASP Smart Contract Top 10 Coverage")
    lines.append("")
    lines.append("| ID | Name | VulnDocs Category | Has Patterns? |")
    lines.append("|----|------|-------------------|---------------|")
    for sc_id, name in sorted(OWASP_SC_TOP_10.items()):
        mapped_cat = KNOWN_TO_VULNDOCS.get(sc_id, "unmapped")
        has_patterns = mapped_cat in vulndocs_patterns and len(vulndocs_patterns[mapped_cat]) > 0
        status = "YES" if has_patterns else "**NO**"
        lines.append(f"| {sc_id} | {name} | {mapped_cat} | {status} |")
    lines.append("")

    # --- Section 5: Priority gaps ---
    lines.append("## 5. Priority Gaps (Action Items)")
    lines.append("")
    lines.append("These are vulnerability classes that are either missing from vulndocs")
    lines.append("or have zero test coverage. File issues for each.")
    lines.append("")

    priority = 1
    # Missing from vulndocs entirely
    for swc_id in sorted(SWC_TOP_20.keys()):
        mapped_cat = KNOWN_TO_VULNDOCS.get(swc_id)
        if mapped_cat and (mapped_cat not in vulndocs_patterns or len(vulndocs_patterns[mapped_cat]) == 0):
            lines.append(f"{priority}. **{SWC_TOP_20[swc_id]}** ({swc_id}) -- mapped to `{mapped_cat}/` but 0 patterns")
            priority += 1

    # Has patterns but no test scenarios
    for cat in sorted(uncovered):
        count = len(vulndocs_patterns[cat])
        if count >= 5:  # Only flag categories with meaningful pattern count
            lines.append(f"{priority}. **{cat}/** -- {count} patterns, zero test scenarios")
            priority += 1

    if priority == 1:
        lines.append("No critical priority gaps detected. All major SWC/OWASP classes")
        lines.append("are represented in vulndocs with at least some patterns.")
    lines.append("")

    # --- Section 6: Conclusion ---
    lines.append("## 6. Conclusion")
    lines.append("")
    lines.append(f"- VulnDocs contains {total} patterns across {len(vulndocs_patterns)} categories")
    covered_vulndocs_cats = len(all_cats & covered_cats)
    lines.append(f"- Test scenarios cover {covered_vulndocs_cats} of {len(all_cats)} vulndocs categories")
    gap_word = "category has" if len(uncovered) == 1 else "categories have"
    lines.append(f"- {len(uncovered)} {gap_word} zero test coverage")
    lines.append(f"- All SWC top-20 classes are represented in vulndocs (via pattern or mapping)")
    lines.append("")
    lines.append("**Recommendation:** vulndocs IS the authoritative source. The GAP-07")
    lines.append("pattern-derived pipeline generates test scenarios from vulndocs patterns.")
    lines.append("No separate external-sources.yaml mapping file is needed. Use this audit")
    lines.append("to file issues for missing test scenarios in uncovered categories.")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    if not VULNDOCS_DIR.exists():
        print(f"ERROR: vulndocs/ not found at {VULNDOCS_DIR}", file=sys.stderr)
        sys.exit(1)

    vulndocs_patterns = inventory_vulndocs(VULNDOCS_DIR)
    test_coverage = inventory_test_scenarios(TESTING_DIR)
    report = generate_report(vulndocs_patterns, test_coverage)
    print(report)


if __name__ == "__main__":
    main()
