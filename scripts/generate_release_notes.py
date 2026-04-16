#!/usr/bin/env python3
"""
Generate GA release notes from metrics and baseline.

Usage:
    uv run python scripts/generate_release_notes.py
    uv run python scripts/generate_release_notes.py --output RELEASE_NOTES.md
"""

import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path


def get_version() -> str:
    """Get version from pyproject.toml."""
    pyproject = Path("pyproject.toml")
    if pyproject.exists():
        for line in pyproject.read_text().split("\n"):
            if line.strip().startswith("version"):
                return line.split("=")[1].strip().strip('"')
    return "0.5.0"


def get_commit() -> str:
    """Get current git commit."""
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return "unknown"


def load_metrics() -> dict:
    """Load aggregated metrics."""
    metrics_file = Path(".vrs/ga-metrics/aggregated-metrics.json")
    if metrics_file.exists():
        return json.loads(metrics_file.read_text())
    return {}


def load_baseline() -> dict:
    """Load baseline."""
    baseline_file = Path(".vrs/baselines/ga-baseline.json")
    if baseline_file.exists():
        return json.loads(baseline_file.read_text())
    return {}


def generate_release_notes() -> str:
    """Generate release notes markdown."""
    version = get_version()
    commit = get_commit()
    date = datetime.now().strftime("%Y-%m-%d")
    metrics = load_metrics()
    baseline = load_baseline()

    lines = [
        f"# AlphaSwarm v{version} Release Notes",
        "",
        f"**Release Date:** {date}",
        f"**Commit:** {commit}",
        "",
        "## Overview",
        "",
        f"AlphaSwarm v{version} is the first General Availability (GA) release of the",
        "multi-agent smart contract security framework. This release includes:",
        "",
        "- Complete BSKG (Behavior-first Security Knowledge Graph) with 200+ emitted properties per function",
        "- 556+ vulnerability patterns across 18 categories",
        "- Multi-agent debate protocol (Attacker/Defender/Verifier)",
        "- External tool integration (Slither, Aderyn, Mythril, Echidna, Foundry, Semgrep, Halmos)",
        "- Protocol context pack generation with Exa MCP",
        "- Evidence-linked findings with BSKG node references",
        "",
        "## Installation",
        "",
        "```bash",
        "# Install AlphaSwarm",
        "uv tool install alphaswarm-sol",
        "",
        "# Or from source",
        "git clone https://github.com/alphaswarm/alphaswarm-sol",
        "cd alphaswarm-sol",
        "uv tool install -e .",
        "```",
        "",
        "## Quick Start",
        "",
        "```bash",
        "# Open Claude Code in your project",
        "cd your-solidity-project",
        "claude",
        "",
        "# Run full audit",
        "/vrs-audit contracts/",
        "```",
        "",
        "## Validation Metrics",
        "",
    ]

    if metrics:
        precision = metrics.get("overall_precision", 0)
        recall = metrics.get("overall_recall", 0)
        f1 = metrics.get("overall_f1", 0)
        tests = metrics.get("total_tests", 0)

        lines.extend([
            "Validated against external ground truth (Damn Vulnerable DeFi, SmartBugs, manual annotation):",
            "",
            "| Metric | Value | Target | Status |",
            "|--------|-------|--------|--------|",
            f"| Precision | {precision:.1%} | >= 70% | {'PASS' if precision >= 0.70 else 'FAIL'} |",
            f"| Recall | {recall:.1%} | >= 60% | {'PASS' if recall >= 0.60 else 'FAIL'} |",
            f"| F1 Score | {f1:.1%} | >= 65% | {'PASS' if f1 >= 0.65 else 'FAIL'} |",
            f"| Tests Passed | {tests} | >= 5 | {'PASS' if tests >= 5 else 'FAIL'} |",
            "",
        ])

        # By vulnerability type
        by_type = metrics.get("by_vulnerability_type", {})
        if by_type:
            lines.extend([
                "### Detection by Vulnerability Type",
                "",
                "| Type | Precision | Recall | F1 |",
                "|------|-----------|--------|-----|",
            ])
            for vtype, data in sorted(by_type.items()):
                lines.append(
                    f"| {vtype} | {data.get('precision', 0):.1%} | "
                    f"{data.get('recall', 0):.1%} | {data.get('f1_score', 0):.1%} |"
                )
            lines.append("")
    else:
        lines.extend([
            "*Note: No metrics data available. Run validation tests to populate.*",
            "",
        ])

    lines.extend([
        "## Key Features",
        "",
        "### BSKG (Behavior-first Security Knowledge Graph)",
        "",
        "- 200+ emitted security properties per function",
        "- 20 semantic operations (behavior-based, not name-based)",
        "- 17 behavioral signatures for vulnerability detection",
        "- Proxy resolution (EIP-1967, UUPS, Diamond, Beacon)",
        "- Deterministic node IDs for evidence linking",
        "",
        "### VulnDocs Knowledge System",
        "",
        "- 556+ vulnerability patterns",
        "- 18 categories (reentrancy, access control, oracle, etc.)",
        "- Tier A/B/C pattern classification",
        "- Graph-first detection strategies",
        "",
        "### Multi-Agent Verification",
        "",
        "- **Attacker Agent:** Constructs exploit paths",
        "- **Defender Agent:** Finds guards and mitigations",
        "- **Verifier Agent:** Arbitrates disputes with evidence",
        "- Debate protocol with claim/counterclaim/resolution",
        "",
        "### External Tool Integration",
        "",
        "- Slither (static analysis)",
        "- Aderyn (Rust-based analysis)",
        "- Mythril (symbolic execution)",
        "- Echidna (fuzzing)",
        "- Foundry (testing)",
        "- Semgrep (pattern matching)",
        "- Halmos (symbolic execution)",
        "",
        "## Breaking Changes",
        "",
        "None - this is the first GA release.",
        "",
        "## Known Limitations",
        "",
        "- Cross-contract analysis limited to imported contracts",
        "- Assembly blocks may have reduced coverage",
        "- Very large codebases (>50k LOC) may require chunked analysis",
        "",
        "## Documentation",
        "",
        "- [Getting Started Guide](docs/getting-started/first-audit.md)",
        "- [Pattern Authoring Guide](docs/guides/patterns-basics.md)",
        "- [VulnDocs Framework](docs/guides/vulndocs-basics.md)",
        "- [API Reference](docs/reference/)",
        "",
        "## Contributing",
        "",
        "See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.",
        "",
        "## License",
        "",
        "MIT License - see [LICENSE](LICENSE) for details.",
        "",
        "---",
        "",
        f"*Generated: {datetime.now().isoformat()}*",
    ])

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate release notes")
    parser.add_argument("--output", help="Output file (default: stdout)")
    args = parser.parse_args()

    notes = generate_release_notes()

    if args.output:
        Path(args.output).write_text(notes)
        print(f"Release notes saved to: {args.output}")
    else:
        print(notes)


if __name__ == "__main__":
    main()
