"""VulnDocs scrapers for continuous knowledge discovery.

This module provides scrapers for fetching new vulnerability findings
from external sources like Solodit.
"""

from alphaswarm_sol.vulndocs.scrapers.solodit_fetcher import (
    SoloditFetcher,
    SoloditFinding,
)

__all__ = [
    "SoloditFetcher",
    "SoloditFinding",
]
