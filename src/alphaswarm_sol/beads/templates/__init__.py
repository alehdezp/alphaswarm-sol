"""Investigation templates for vulnerability classes.

This module provides YAML-based investigation templates for each of the
7 vulnerability lens categories. Templates guide LLM investigation by
providing:

1. Ordered investigation steps
2. Key questions to answer
3. Common false positive patterns
4. Key indicators of real vulnerabilities
5. Safe patterns that make code not vulnerable

Available Templates:
- reentrancy: Classic, cross-function, cross-contract reentrancy
- access_control: Missing access control, privilege escalation
- oracle: Staleness, manipulation, missing checks
- dos: Unbounded loops, griefing, revert bombs
- mev: Frontrunning, sandwich, slippage
- token: ERC20 issues, fee-on-transfer, return values
- upgrade: Proxy issues, storage collision, initialization

Usage:
    from alphaswarm_sol.beads.templates import load_template, list_available_templates

    # Load a specific template
    guide = load_template("reentrancy")

    # List all available templates
    templates = list_available_templates()
"""

from alphaswarm_sol.beads.templates.loader import (
    load_template,
    list_available_templates,
    get_template_version,
    get_template_metadata,
    clear_cache,
)

__all__ = [
    "load_template",
    "list_available_templates",
    "get_template_version",
    "get_template_metadata",
    "clear_cache",
]
