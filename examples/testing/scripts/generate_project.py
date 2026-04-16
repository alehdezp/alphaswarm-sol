#!/usr/bin/env python3
"""Orchestration wrapper for corpus-generator subagent.

Invokes the Opus-powered corpus-generator Claude Code subagent to produce
adversarial Solidity test projects with embedded vulnerability patterns,
adversarial obfuscation, ground truth with reasoning chains, and safe variants.

Usage:
    # Generate a specific project with named patterns
    python generate_project.py --patterns reentrancy-basic,access-control-missing \\
        --category A --tier 1 --output examples/testing/corpus/project-name/

    # Generate multiple random projects
    python generate_project.py --count 5 --category A,B --output examples/testing/corpus/

    # Generate and verify
    python generate_project.py --patterns random --category A --tier 2 \\
        --output /tmp/test-gen/ --verify

Requirements:
    - claude CLI installed and authenticated
    - solc (Solidity compiler) installed for verification
"""

import argparse
import json
import logging
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

# Repo root relative to this script
REPO_ROOT = Path(__file__).resolve().parents[3]
GUIDELINES_DIR = REPO_ROOT / "examples" / "testing" / "guidelines"
AGENT_PATH = REPO_ROOT / ".claude" / "agents" / "corpus-generator.md"


def build_generation_prompt(
    patterns: list[str],
    category: str,
    tier: int,
    output_dir: Path,
) -> str:
    """Build the prompt for the corpus-generator subagent.

    The prompt instructs the agent on what patterns to embed, what obfuscation
    to apply, and where to write the output.
    """
    pattern_str = ", ".join(patterns) if patterns else "random"
    project_name = output_dir.name or f"adversarial-{int(time.time())}"

    prompt = f"""You are the corpus-generator agent. Generate an adversarial Solidity test project.

## Parameters
- **Patterns:** {pattern_str}
- **Adversarial Category:** {category}
- **Complexity Tier:** {tier}
- **Output Directory:** {output_dir}
- **Project Name:** {project_name}

## Instructions

1. Read the generation guidelines from:
   - {GUIDELINES_DIR / 'pattern-catalog.yaml'}
   - {GUIDELINES_DIR / 'adversarial-taxonomy.md'}
   - {GUIDELINES_DIR / 'combination-rules.yaml'}
   - {GUIDELINES_DIR / 'generation-pipeline.md'}

2. Follow the 8-step generation pipeline exactly as specified.

3. Write ALL output files to: {output_dir}

4. The project must:
   - Embed {"the specified patterns: " + pattern_str if patterns else "at least 5 randomly selected compatible patterns"}
   - Apply adversarial obfuscation from Category {category}
   - Use Tier {tier} complexity
   - Compile with solc
   - Have both vulnerable and safe variants
   - Include ground-truth.yaml with expected_reasoning_chain per finding
   - Include project-manifest.yaml
   - Include build-verification.sh

5. CRITICAL: All contracts must be NOVEL. No Ethernaut, DVDeFi, SWC, or CTF contracts.

After completion, verify that all .sol files compile with solc.
"""
    return prompt


def generate_single_project(
    patterns: list[str],
    category: str,
    tier: int,
    output_dir: Path,
    model: str = "opus",
    timeout: int = 300,
) -> bool:
    """Invoke the corpus-generator subagent to create one project.

    Args:
        patterns: List of pattern IDs to embed, or empty for random selection.
        category: Adversarial category (A, B, C, or comma-separated combination).
        tier: Complexity tier (1=basic, 2=complex, 3=adversarial).
        output_dir: Directory to write the generated project.
        model: Claude model to use (default: opus).
        timeout: Timeout in seconds for the generation subprocess.

    Returns:
        True if generation succeeded, False otherwise.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    prompt = build_generation_prompt(patterns, category, tier, output_dir)

    log.info("Generating project in %s (model=%s, tier=%d, category=%s)", output_dir, model, tier, category)
    log.info("Patterns: %s", patterns or ["random"])

    cmd = [
        "claude",
        "--print",
        "-p", prompt,
        "--model", model,
        "--allowedTools", "Read,Write,Edit,Bash,Glob,Grep",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(REPO_ROOT),
        )

        if result.returncode != 0:
            log.error("Generation failed (exit code %d)", result.returncode)
            if result.stderr:
                log.error("stderr: %s", result.stderr[:2000])
            return False

        log.info("Generation command completed successfully")
        return True

    except subprocess.TimeoutExpired:
        log.error("Generation timed out after %d seconds", timeout)
        return False
    except FileNotFoundError:
        log.error("claude CLI not found. Install with: npm install -g @anthropic-ai/claude-code")
        return False


def verify_project(project_dir: Path) -> dict:
    """Verify a generated project: compilation, ground truth, manifest.

    Args:
        project_dir: Path to the generated project directory.

    Returns:
        Dictionary with verification results.
    """
    results = {
        "project_dir": str(project_dir),
        "contracts_exist": False,
        "ground_truth_exists": False,
        "manifest_exists": False,
        "ground_truth_valid": False,
        "finding_count": 0,
        "safe_pattern_count": 0,
        "has_reasoning_chains": False,
        "compilation_status": "not_checked",
        "errors": [],
    }

    # Check directory exists
    if not project_dir.exists():
        results["errors"].append(f"Project directory not found: {project_dir}")
        return results

    # Check contracts exist
    sol_files = list(project_dir.rglob("*.sol"))
    results["contracts_exist"] = len(sol_files) > 0
    if not sol_files:
        results["errors"].append("No .sol files found")

    # Check ground truth
    gt_path = project_dir / "ground-truth.yaml"
    results["ground_truth_exists"] = gt_path.exists()
    if gt_path.exists():
        try:
            import yaml

            with open(gt_path) as f:
                gt = yaml.safe_load(f)

            if isinstance(gt, dict):
                findings = gt.get("findings", [])
                safe_patterns = gt.get("safe_patterns", [])
                results["ground_truth_valid"] = True
                results["finding_count"] = len(findings)
                results["safe_pattern_count"] = len(safe_patterns)

                # Check reasoning chains
                has_chains = all(
                    len(finding.get("expected_reasoning_chain", [])) >= 3
                    for finding in findings
                )
                results["has_reasoning_chains"] = has_chains
                if not has_chains:
                    results["errors"].append(
                        "Some findings missing expected_reasoning_chain (need 3+ steps)"
                    )
            else:
                results["errors"].append("ground-truth.yaml is not a valid YAML mapping")
        except Exception as e:
            results["errors"].append(f"Failed to parse ground-truth.yaml: {e}")

    # Check manifest
    manifest_path = project_dir / "project-manifest.yaml"
    results["manifest_exists"] = manifest_path.exists()

    # Check compilation (if solc is available)
    vulnerable_sols = [f for f in sol_files if "_safe" not in f.name]
    safe_sols = [f for f in sol_files if "_safe" in f.name]

    if vulnerable_sols:
        try:
            compile_result = subprocess.run(
                ["solc", "--bin"] + [str(f) for f in vulnerable_sols],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if compile_result.returncode == 0:
                results["compilation_status"] = "passed"
            else:
                results["compilation_status"] = "failed"
                results["errors"].append(
                    f"Compilation failed: {compile_result.stderr[:500]}"
                )
        except FileNotFoundError:
            results["compilation_status"] = "solc_not_found"
            results["errors"].append("solc not found in PATH")
        except subprocess.TimeoutExpired:
            results["compilation_status"] = "timeout"
            results["errors"].append("Compilation timed out")

    return results


def select_random_patterns(count: int = 7) -> list[str]:
    """Select random compatible patterns from the catalog.

    Uses combination rules to ensure selected patterns are compatible.

    Args:
        count: Number of patterns to select (default: 7).

    Returns:
        List of pattern IDs.
    """
    try:
        import yaml
    except ImportError:
        log.error("PyYAML required for random pattern selection")
        return []

    catalog_path = GUIDELINES_DIR / "pattern-catalog.yaml"
    rules_path = GUIDELINES_DIR / "combination-rules.yaml"

    if not catalog_path.exists():
        log.error("Pattern catalog not found at %s", catalog_path)
        return []

    with open(catalog_path) as f:
        catalog = yaml.safe_load(f)

    with open(rules_path) as f:
        rules = yaml.safe_load(f)

    # Get high-severity patterns as candidates
    high_severity = [
        p["pattern_id"]
        for p in catalog
        if p.get("severity") in ("critical", "high")
    ]

    # Get compatible combination suggestions
    compatible = rules.get("compatible_combinations", [])
    if compatible:
        # Pick a compatible set as the starting point
        import random

        combo = random.choice(compatible)
        selected = list(combo.get("patterns", []))

        # Fill with high-severity patterns
        remaining = [p for p in high_severity if p not in selected]
        random.shuffle(remaining)
        while len(selected) < count and remaining:
            selected.append(remaining.pop())

        return selected[:count]

    # Fallback: random high-severity
    import random

    random.shuffle(high_severity)
    return high_severity[:count]


def main():
    parser = argparse.ArgumentParser(
        description="Generate adversarial Solidity test projects using the corpus-generator agent.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate with specific patterns
  %(prog)s --patterns reentrancy-basic,access-control-missing --category A --tier 1 --output /tmp/test/

  # Generate 3 random projects
  %(prog)s --count 3 --category A,B --output examples/testing/corpus/

  # Generate and verify
  %(prog)s --patterns random --category A --tier 2 --output /tmp/test/ --verify
        """,
    )

    parser.add_argument(
        "--patterns",
        type=str,
        default="random",
        help="Comma-separated pattern IDs to embed, or 'random' for auto-selection (default: random)",
    )
    parser.add_argument(
        "--category",
        type=str,
        default="A",
        help="Adversarial obfuscation category: A, B, C, or combination like 'A,B' (default: A)",
    )
    parser.add_argument(
        "--tier",
        type=int,
        default=1,
        choices=[1, 2, 3],
        help="Complexity tier: 1=basic, 2=complex, 3=adversarial (default: 1)",
    )
    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="Output directory for generated project(s)",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=1,
        help="Number of projects to generate (default: 1)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="opus",
        help="Claude model to use (default: opus)",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Run verification after generation",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Timeout per project in seconds (default: 300)",
    )

    args = parser.parse_args()

    # Parse patterns
    if args.patterns == "random":
        pattern_list: list[str] = []
    else:
        pattern_list = [p.strip() for p in args.patterns.split(",") if p.strip()]

    output_base = Path(args.output).resolve()
    results = []

    for i in range(args.count):
        if args.count > 1:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
            project_dir = output_base / f"project-{i + 1:03d}-{timestamp}"
        else:
            project_dir = output_base

        # Select patterns for this project
        if not pattern_list:
            patterns = select_random_patterns()
            log.info("Randomly selected patterns: %s", patterns)
        else:
            patterns = pattern_list

        success = generate_single_project(
            patterns=patterns,
            category=args.category,
            tier=args.tier,
            output_dir=project_dir,
            model=args.model,
            timeout=args.timeout,
        )

        project_result = {
            "project": str(project_dir),
            "generation_success": success,
            "patterns": patterns,
            "verification": None,
        }

        if success and args.verify:
            log.info("Verifying project: %s", project_dir)
            verification = verify_project(project_dir)
            project_result["verification"] = verification

            if verification["errors"]:
                log.warning("Verification issues for %s:", project_dir)
                for error in verification["errors"]:
                    log.warning("  - %s", error)
            else:
                log.info("Verification passed for %s", project_dir)

        results.append(project_result)

    # Print summary
    print("\n" + "=" * 60)
    print("GENERATION SUMMARY")
    print("=" * 60)

    succeeded = sum(1 for r in results if r["generation_success"])
    print(f"Projects generated: {succeeded}/{len(results)}")

    for r in results:
        status = "OK" if r["generation_success"] else "FAILED"
        print(f"  [{status}] {r['project']}")
        if r["verification"]:
            v = r["verification"]
            print(f"         Contracts: {v['contracts_exist']}, Ground truth: {v['finding_count']} findings")
            print(f"         Compilation: {v['compilation_status']}")
            if v["errors"]:
                for e in v["errors"]:
                    print(f"         ERROR: {e}")

    return 0 if succeeded == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
