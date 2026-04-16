"""Enterprise features module for True VKG.

Provides configuration profiles, multi-project support, and report generation.
"""

from alphaswarm_sol.enterprise.profiles import (
    ProfileLevel,
    ConfigProfile,
    ProfileManager,
    get_profile,
)
from alphaswarm_sol.enterprise.multi_project import (
    ProjectInfo,
    MultiProjectManager,
    CrossProjectQuery,
)
from alphaswarm_sol.enterprise.reports import (
    ReportFormat,
    ReportSection,
    SecurityReport,
    ReportGenerator,
    generate_report,
)

__all__ = [
    "ProfileLevel",
    "ConfigProfile",
    "ProfileManager",
    "get_profile",
    "ProjectInfo",
    "MultiProjectManager",
    "CrossProjectQuery",
    "ReportFormat",
    "ReportSection",
    "SecurityReport",
    "ReportGenerator",
    "generate_report",
]
