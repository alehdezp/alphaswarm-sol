"""VulnDocs automation for continuous knowledge discovery.

This module provides automated scanning and discovery tools for
keeping VulnDocs current with emerging vulnerabilities.
"""

from alphaswarm_sol.vulndocs.automation.exa_scanner import (
    ExaScanner,
    ExaDiscovery,
)

__all__ = [
    "ExaScanner",
    "ExaDiscovery",
]
