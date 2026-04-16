"""
Guardrail Policy Loader and Validator

This module loads and validates role-based tool policies for skills and subagents.
It enforces data access boundaries and tool gating based on role definitions.

Phase: 07.1.2-skill-subagent-design-system
Plan: 05
"""

import yaml
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of policy validation."""
    valid: bool
    errors: List[str]
    warnings: List[str]
    role: Optional[str] = None
    policy: Optional[Dict[str, Any]] = None


def load_tool_policy(policy_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Load tool policy from YAML file.

    Args:
        policy_path: Path to policy YAML (default: configs/skill_tool_policies.yaml)

    Returns:
        Parsed policy dictionary

    Raises:
        FileNotFoundError: If policy file not found
        yaml.YAMLError: If policy file is invalid YAML
    """
    if policy_path is None:
        # Default to project root / configs / skill_tool_policies.yaml
        project_root = Path(__file__).parent.parent.parent.parent
        policy_path = project_root / "configs" / "skill_tool_policies.yaml"

    if not policy_path.exists():
        raise FileNotFoundError(f"Tool policy file not found: {policy_path}")

    with open(policy_path, 'r') as f:
        policy = yaml.safe_load(f)

    if not policy or 'roles' not in policy:
        raise ValueError(f"Invalid policy file: missing 'roles' section")

    return policy


def extract_skill_frontmatter(skill_path: Path) -> Optional[Dict[str, Any]]:
    """
    Extract frontmatter from skill markdown file.

    Args:
        skill_path: Path to skill .md file

    Returns:
        Parsed frontmatter dict, or None if no frontmatter
    """
    if not skill_path.exists():
        raise FileNotFoundError(f"Skill file not found: {skill_path}")

    content = skill_path.read_text()

    # Extract YAML frontmatter between --- markers
    frontmatter_pattern = r'^---\s*\n(.*?)\n---\s*\n'
    match = re.match(frontmatter_pattern, content, re.DOTALL)

    if not match:
        return None

    frontmatter_text = match.group(1)

    try:
        frontmatter = yaml.safe_load(frontmatter_text)
        return frontmatter
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid frontmatter YAML in {skill_path}: {e}")


def check_tool_allowed(tool: str, allowed_tools: List[str]) -> bool:
    """
    Check if a tool matches any allowed tool pattern.

    Args:
        tool: Tool name (e.g., "Read", "Bash(uv run alphaswarm query*)")
        allowed_tools: List of allowed tool patterns

    Returns:
        True if tool is allowed, False otherwise
    """
    for allowed in allowed_tools:
        # Exact match
        if tool == allowed:
            return True

        # Pattern match for Bash commands
        if allowed.startswith("Bash(") and allowed.endswith(")"):
            # Extract pattern from Bash(pattern)
            pattern = allowed[5:-1]  # Remove "Bash(" and ")"

            if tool.startswith("Bash(") and tool.endswith(")"):
                command = tool[5:-1]

                # Convert glob pattern to regex
                # * -> .*
                # ? -> .
                regex_pattern = pattern.replace("*", ".*").replace("?", ".")
                regex_pattern = f"^{regex_pattern}$"

                if re.match(regex_pattern, command):
                    return True

        # Pattern match for MCP tools
        if allowed.startswith("mcp__"):
            # Prefix match for MCP tools
            if tool.startswith(allowed.rstrip("*")):
                return True

    return False


def check_path_allowed(path: str, allowed_paths: List[str], forbidden_paths: List[str]) -> tuple[bool, Optional[str]]:
    """
    Check if a file path is allowed based on allow/forbid patterns.

    Args:
        path: File path to check
        allowed_paths: List of allowed path patterns (globs)
        forbidden_paths: List of forbidden path patterns (globs)

    Returns:
        (is_allowed, reason) - reason is None if allowed, error message if not
    """
    from fnmatch import fnmatch

    # Check forbidden first (takes precedence)
    for forbidden in forbidden_paths:
        if fnmatch(path, forbidden):
            return False, f"Path matches forbidden pattern: {forbidden}"

    # Check allowed
    for allowed in allowed_paths:
        if fnmatch(path, allowed):
            return True, None

    return False, "Path does not match any allowed pattern"


def validate_tool_policy(
    skill_path: Path,
    role: str,
    policy_path: Optional[Path] = None,
    strict: bool = False
) -> ValidationResult:
    """
    Validate a skill's tool usage against role-based policy.

    Args:
        skill_path: Path to skill .md file
        role: Role to validate against (e.g., "attacker", "defender")
        policy_path: Optional path to policy YAML (uses default if None)
        strict: If True, fail if skill has no frontmatter

    Returns:
        ValidationResult with validity status, errors, and warnings
    """
    errors = []
    warnings = []

    # Load policy
    try:
        policy = load_tool_policy(policy_path)
    except Exception as e:
        return ValidationResult(
            valid=False,
            errors=[f"Failed to load policy: {e}"],
            warnings=[],
            role=role
        )

    # Check role exists
    if role not in policy['roles']:
        return ValidationResult(
            valid=False,
            errors=[f"Role '{role}' not defined in policy"],
            warnings=[],
            role=role
        )

    role_policy = policy['roles'][role]

    # Extract skill frontmatter
    try:
        frontmatter = extract_skill_frontmatter(Path(skill_path))
    except Exception as e:
        return ValidationResult(
            valid=False,
            errors=[f"Failed to extract frontmatter: {e}"],
            warnings=[],
            role=role,
            policy=role_policy
        )

    if frontmatter is None:
        if strict:
            return ValidationResult(
                valid=False,
                errors=["Skill has no frontmatter (strict mode)"],
                warnings=[],
                role=role,
                policy=role_policy
            )
        else:
            warnings.append("Skill has no frontmatter - cannot validate")
            return ValidationResult(
                valid=True,
                errors=[],
                warnings=warnings,
                role=role,
                policy=role_policy
            )

    # Validate tools
    skill_tools = frontmatter.get('tools', [])
    allowed_tools = role_policy['allowed_tools']

    for tool in skill_tools:
        if not check_tool_allowed(tool, allowed_tools):
            errors.append(f"Tool '{tool}' not allowed for role '{role}'")

    # Validate constraints
    constraints = role_policy.get('constraints', {})

    # Check evidence requirement
    if constraints.get('evidence_required', False):
        evidence_reqs = frontmatter.get('evidence_requirements', {})
        if not evidence_reqs:
            warnings.append("Evidence required for this role but skill has no evidence_requirements")
        elif not evidence_reqs.get('must_link_code') and not evidence_reqs.get('cite_graph_nodes'):
            warnings.append("Evidence required but skill doesn't require code links or graph nodes")

    # Check graph-first requirement
    if constraints.get('require_graph_first', False):
        evidence_reqs = frontmatter.get('evidence_requirements', {})
        if evidence_reqs and not evidence_reqs.get('graph_first'):
            warnings.append("Role requires graph-first but skill evidence_requirements.graph_first is false/missing")

    # Check token budget
    skill_budget = frontmatter.get('token_budget')
    role_budget = constraints.get('token_budget')
    if skill_budget and role_budget:
        if skill_budget > role_budget:
            warnings.append(
                f"Skill token budget ({skill_budget}) exceeds role budget ({role_budget})"
            )

    # Check model tier
    skill_model = frontmatter.get('model', '')
    role_tier = role_policy.get('model_tier')

    # Map model names to tiers
    model_tier_map = {
        'haiku': ['haiku', 'claude-haiku'],
        'sonnet': ['sonnet', 'claude-sonnet'],
        'opus': ['opus', 'claude-opus']
    }

    skill_tier = None
    for tier, models in model_tier_map.items():
        if any(m in skill_model.lower() for m in models):
            skill_tier = tier
            break

    if skill_tier and role_tier:
        tier_order = ['haiku', 'sonnet', 'opus']
        if tier_order.index(skill_tier) > tier_order.index(role_tier):
            warnings.append(
                f"Skill uses {skill_tier} but role default is {role_tier} "
                f"(may require escalation)"
            )

    # Check for overbroad patterns
    for tool in skill_tools:
        if tool == "Bash(*)":
            errors.append("Overbroad tool pattern 'Bash(*)' - use specific command patterns")
        if tool == "Write" and role not in ['architect', 'curator']:
            errors.append(f"Tool 'Write' not typically allowed for role '{role}'")

    # Determine validity
    valid = len(errors) == 0

    return ValidationResult(
        valid=valid,
        errors=errors,
        warnings=warnings,
        role=role,
        policy=role_policy
    )


def check_escalation_required(
    skill_path: Path,
    role: str,
    policy_path: Optional[Path] = None
) -> tuple[bool, List[str]]:
    """
    Check if skill execution requires escalation/validation.

    Args:
        skill_path: Path to skill .md file
        role: Role being used
        policy_path: Optional path to policy YAML

    Returns:
        (requires_escalation, reasons) - List of reasons if escalation needed
    """
    try:
        policy = load_tool_policy(policy_path)
        frontmatter = extract_skill_frontmatter(Path(skill_path))
    except Exception as e:
        return True, [f"Error loading policy or skill: {e}"]

    if not frontmatter:
        return False, []

    escalation_rules = policy.get('escalation', {}).get('require_guardrail_validation', [])

    reasons = []

    for rule in escalation_rules:
        condition = rule['condition']
        message = rule['message']

        # Evaluate condition
        # token_budget > 6000
        if 'token_budget' in condition:
            skill_budget = frontmatter.get('token_budget', 0)
            if '>' in condition:
                threshold = int(condition.split('>')[1].strip())
                if skill_budget > threshold:
                    reasons.append(message)

        # model_tier == opus
        if 'model_tier' in condition:
            skill_model = frontmatter.get('model', '').lower()
            if 'opus' in condition and 'opus' in skill_model:
                reasons.append(message)

    return len(reasons) > 0, reasons


def validate_policy_schema(policy_path: Optional[Path] = None) -> ValidationResult:
    """
    Validate policy file against JSON schema.

    Args:
        policy_path: Path to policy YAML (default: configs/skill_tool_policies.yaml)

    Returns:
        ValidationResult indicating schema validity
    """
    try:
        from jsonschema import validate, ValidationError

        # Load policy
        policy = load_tool_policy(policy_path)

        # Load schema
        project_root = Path(__file__).parent.parent.parent.parent
        schema_path = project_root / "schemas" / "skill_tool_policy_v1.json"

        if not schema_path.exists():
            return ValidationResult(
                valid=False,
                errors=[f"Schema file not found: {schema_path}"],
                warnings=[]
            )

        with open(schema_path, 'r') as f:
            schema = json.load(f)

        # Validate
        validate(instance=policy, schema=schema)

        return ValidationResult(
            valid=True,
            errors=[],
            warnings=[]
        )

    except ValidationError as e:
        return ValidationResult(
            valid=False,
            errors=[f"Schema validation failed: {e.message}"],
            warnings=[]
        )
    except Exception as e:
        return ValidationResult(
            valid=False,
            errors=[f"Validation error: {e}"],
            warnings=[]
        )


# Convenience function for CLI usage
def main():
    """CLI entry point for policy validation."""
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="Validate skill tool policies")
    parser.add_argument("skill_path", help="Path to skill .md file")
    parser.add_argument("--role", required=True, help="Role to validate against")
    parser.add_argument("--policy", help="Path to policy YAML (optional)")
    parser.add_argument("--strict", action="store_true", help="Fail if no frontmatter")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    result = validate_tool_policy(
        Path(args.skill_path),
        args.role,
        Path(args.policy) if args.policy else None,
        strict=args.strict
    )

    if args.json:
        import json
        output = {
            "valid": result.valid,
            "errors": result.errors,
            "warnings": result.warnings,
            "role": result.role
        }
        print(json.dumps(output, indent=2))
    else:
        print(f"Validation Result: {'✅ PASS' if result.valid else '❌ FAIL'}")
        print(f"Role: {result.role}")

        if result.errors:
            print("\nErrors:")
            for error in result.errors:
                print(f"  ❌ {error}")

        if result.warnings:
            print("\nWarnings:")
            for warning in result.warnings:
                print(f"  ⚠️  {warning}")

    sys.exit(0 if result.valid else 1)


if __name__ == "__main__":
    main()
