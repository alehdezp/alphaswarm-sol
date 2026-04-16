"""Type definitions for VulnDocs Phase 5.4 Unification.

This module provides foundational types for the unified vulndocs-patterns system,
supporting index.yaml validation and Phase 7 test generation fields.
"""

from enum import Enum
from typing import Literal

# =============================================================================
# Enums
# =============================================================================


class Severity(str, Enum):
    """Vulnerability severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


class ValidationLevel(str, Enum):
    """Progressive validation levels for vulnerability folders.

    Per 05.4-RESEARCH.md progressive validation pattern.
    """

    MINIMAL = "minimal"  # Just index.yaml with required fields
    STANDARD = "standard"  # index.yaml + at least one md file
    COMPLETE = "complete"  # All recommended files present
    EXCELLENT = "excellent"  # All files + patterns with test coverage


# =============================================================================
# Type Aliases
# =============================================================================

PatternId = str  # e.g., "oracle-001-twap"
CategoryPath = str  # e.g., "oracle/price-manipulation"
VqlQuery = str  # VQL query string
GraphPattern = str  # Graph pattern string like "R:bal->X:out->W:bal"
SemanticTrigger = str  # Semantic operation name


# =============================================================================
# Semantic Operations
# =============================================================================

# All 20 semantic operations from docs/reference/operations.md
# These are used for Phase 7 test generation and pattern matching
VALID_SEMANTIC_OPERATIONS = [
    # State Modification
    "WRITES_STATE",
    "WRITES_CRITICAL_STATE",
    "WRITES_BALANCE",
    # State Reading
    "READS_STATE",
    "READS_BALANCE",
    "READS_ORACLE",
    # External Calls
    "CALLS_EXTERNAL",
    "CALLS_UNTRUSTED",
    "DELEGATECALL",
    "STATICCALL",
    # Value Transfer
    "TRANSFERS_ETH",
    "TRANSFERS_TOKEN",
    # Taint Propagation
    "INPUT_TAINTS_STATE",
    "EXTERNAL_TAINTS",
    # Containment (structural - not typically used in patterns)
    "CONTAINS_FUNCTION",
    "CONTAINS_STATE",
    "CONTAINS_EVENT",
    "CONTAINS_MODIFIER",
    "FUNCTION_HAS_INPUT",
    "FUNCTION_HAS_LOOP",
]

# Commonly used semantic operations for pattern matching
PATTERN_SEMANTIC_OPERATIONS = [
    "WRITES_STATE",
    "WRITES_CRITICAL_STATE",
    "WRITES_BALANCE",
    "READS_STATE",
    "READS_BALANCE",
    "READS_ORACLE",
    "CALLS_EXTERNAL",
    "CALLS_UNTRUSTED",
    "DELEGATECALL",
    "TRANSFERS_ETH",
    "TRANSFERS_TOKEN",
    "INPUT_TAINTS_STATE",
    "EXTERNAL_TAINTS",
]

# =============================================================================
# Pattern Scope
# =============================================================================

PatternScope = Literal["Function", "Contract", "Transaction"]
VALID_PATTERN_SCOPES = ["Function", "Contract", "Transaction"]

# =============================================================================
# Test Status
# =============================================================================

TestStatus = Literal["draft", "ready", "excellent"]
VALID_TEST_STATUSES = ["draft", "ready", "excellent"]
