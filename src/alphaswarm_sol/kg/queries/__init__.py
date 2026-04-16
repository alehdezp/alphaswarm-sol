"""VQL Query Library for BSKG.

This module provides the VQL (Vulnerability Query Language) library for
querying the BSKG (Behavioral Security Knowledge Graph).

VQL queries are defined in YAML format and can be:
1. Executed against a KnowledgeGraph instance
2. Validated against the BSKG schema
3. Composed for complex analysis workflows
"""

from pathlib import Path

# Path to query library YAML
VQL_MINIMUM_SET_PATH = Path(__file__).parent / "vql_minimum_set.yaml"

__all__ = ["VQL_MINIMUM_SET_PATH"]
