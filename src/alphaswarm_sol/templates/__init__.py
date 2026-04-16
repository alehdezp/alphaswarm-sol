"""Template generators for VKG integration with external tools."""

from alphaswarm_sol.templates.opencode import (
    generate_opencode_config,
    write_opencode_config,
    OpenCodeConfig,
)
from alphaswarm_sol.templates.codex import (
    get_output_schema,
    get_schema_json,
    write_output_schema,
    format_finding_for_codex,
    format_findings_for_codex,
    format_findings_to_json,
    calculate_summary,
    calculate_verdict,
    generate_recommendations,
    validate_codex_output,
    validate_codex_output_file,
    ContractInfo,
    Recommendation,
    AuditMetadata,
    CODEX_OUTPUT_SCHEMA_VERSION,
)

__all__ = [
    # OpenCode integration
    "generate_opencode_config",
    "write_opencode_config",
    "OpenCodeConfig",
    # Codex integration
    "get_output_schema",
    "get_schema_json",
    "write_output_schema",
    "format_finding_for_codex",
    "format_findings_for_codex",
    "format_findings_to_json",
    "calculate_summary",
    "calculate_verdict",
    "generate_recommendations",
    "validate_codex_output",
    "validate_codex_output_file",
    "ContractInfo",
    "Recommendation",
    "AuditMetadata",
    "CODEX_OUTPUT_SCHEMA_VERSION",
]
