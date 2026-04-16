# Utility Functions Reference

**Purpose:** Catalog of reusable helper functions across all modules.
**Last Updated:** 2026-01-22

---

## Table of Contents

1. [Builder Helpers](#builder-helpers)
2. [Context Helpers](#context-helpers)
3. [Labeling Helpers](#labeling-helpers)
4. [Orchestration Helpers](#orchestration-helpers)
5. [Agent Helpers](#agent-helpers)
6. [Tool Helpers](#tool-helpers)

---

## Builder Helpers

**Location:** `src/alphaswarm_sol/kg/builder/helpers.py` (551 LOC)

### Source Location Functions

```python
def source_location(obj: Any) -> Optional[SourceLocation]:
    """
    Extract source location from Slither object.

    Args:
        obj: Slither Function, StateVariable, Contract, or Node

    Returns:
        SourceLocation with file_path, line_start, line_end, or None

    Example:
        loc = source_location(function)
        # SourceLocation(file_path="src/Token.sol", line_start=45, line_end=67)
    """

def relpath(filename: str, project_root: Path) -> str:
    """
    Convert absolute path to relative path from project root.

    Args:
        filename: Absolute file path
        project_root: Project root directory

    Returns:
        Relative path string

    Example:
        relpath("/home/project/src/Token.sol", Path("/home/project"))
        # "src/Token.sol"
    """

def evidence_from_location(
    file_path: str,
    line_start: int,
    line_end: int
) -> List[Evidence]:
    """
    Create Evidence list from location information.

    Args:
        file_path: Relative file path
        line_start: Starting line number
        line_end: Ending line number

    Returns:
        List with single Evidence object

    Example:
        evidence = evidence_from_location("src/Token.sol", 45, 67)
        # [Evidence(file="src/Token.sol", lines=(45, 67))]
    """

def get_source_lines(
    file_path: Path,
    project_root: Path,
    cache: Dict[Path, List[str]]
) -> List[str]:
    """
    Get source lines with caching for repeated reads.

    Args:
        file_path: Path to source file
        project_root: Project root for relative paths
        cache: Shared cache dictionary

    Returns:
        List of source lines (1-indexed internally)

    Note:
        Caches result in provided dict for reuse
    """

def get_source_slice(
    file_path: Path,
    project_root: Path,
    line_start: int,
    line_end: int,
    cache: Dict[Path, List[str]]
) -> str:
    """
    Get source code slice from file.

    Args:
        file_path: Path to source file
        project_root: Project root
        line_start: Start line (1-indexed)
        line_end: End line (1-indexed, inclusive)
        cache: Source line cache

    Returns:
        Source code string

    Example:
        code = get_source_slice(path, root, 45, 50, cache)
        # "function transfer(address to, uint256 amount) external {\n..."
    """
```

### Function/Node Analysis

```python
def function_label(fn: Function) -> str:
    """
    Get human-readable function label.

    Returns:
        "ContractName.functionName" format

    Example:
        function_label(transfer_fn)
        # "Token.transfer"
    """

def is_access_gate(modifier_name: str) -> bool:
    """
    Check if modifier name indicates access control.

    Args:
        modifier_name: Modifier name (case-insensitive)

    Returns:
        True if access control modifier

    Recognized patterns:
        - onlyOwner, onlyAdmin, onlyRole
        - auth, authorized, restricted
        - whenNotPaused, initializer

    Example:
        is_access_gate("onlyOwner")  # True
        is_access_gate("nonReentrant")  # False
    """

def uses_var_name(variables: List[Variable], name: str) -> bool:
    """
    Check if any variable has the specified name.

    Args:
        variables: List of Slither Variable objects
        name: Variable name to search (case-sensitive)

    Returns:
        True if found

    Example:
        uses_var_name(fn.state_variables_read, "totalSupply")
    """

def strip_comments(text: str) -> str:
    """
    Remove single-line and multi-line comments from source.

    Args:
        text: Source code string

    Returns:
        Code with comments removed

    Handles:
        - // single line comments
        - /* multi-line comments */
        - Nested comments
    """

def node_expression(node: Node) -> Optional[str]:
    """
    Get string representation of CFG node expression.

    Args:
        node: Slither CFG Node

    Returns:
        Expression string or None

    Example:
        node_expression(if_node)
        # "balance[msg.sender] >= amount"
    """

def normalize_state_mutability(fn: Function) -> str:
    """
    Normalize function state mutability.

    Returns one of:
        - "pure"
        - "view"
        - "nonpayable"
        - "payable"

    Example:
        normalize_state_mutability(fn)
        # "nonpayable"
    """
```

### Call Analysis

```python
def callsite_data_expression(call: HighLevelCall) -> Optional[str]:
    """
    Get the data/arguments expression of a call.

    Args:
        call: Slither HighLevelCall object

    Returns:
        String representation of call arguments

    Example:
        callsite_data_expression(transfer_call)
        # "to, amount"
    """

def callsite_destination(call: HighLevelCall) -> Optional[str]:
    """
    Get the destination address/contract of a call.

    Args:
        call: Slither HighLevelCall object

    Returns:
        Destination as string

    Example:
        callsite_destination(call)
        # "token" or "msg.sender" or "0x1234..."
    """

def is_user_controlled_destination(
    destination: str,
    parameter_names: Set[str]
) -> bool:
    """
    Check if call destination is user-controlled.

    Args:
        destination: Destination expression string
        parameter_names: Set of function parameter names

    Returns:
        True if destination derived from user input

    User-controlled indicators:
        - Parameter names (address from, address to)
        - msg.sender, tx.origin
        - Mapping/array lookups with user keys
    """

def is_user_controlled_expression(
    expression: str,
    parameter_names: Set[str],
    allow_msg_value: bool = False
) -> bool:
    """
    Check if expression is user-controlled.

    Args:
        expression: Expression string
        parameter_names: Function parameter names
        allow_msg_value: Whether msg.value is considered user-controlled

    Returns:
        True if user-controlled

    Example:
        is_user_controlled_expression("balances[to]", {"to", "amount"}, False)
        # True (uses parameter 'to')
    """

def is_hardcoded_gas(gas_value: Optional[int]) -> bool:
    """
    Check if gas value is hardcoded (2300 or similar).

    Args:
        gas_value: Gas limit if specified

    Returns:
        True if hardcoded gas limit

    Known hardcoded values:
        - 2300 (transfer/send)
        - 0 (no gas limit)
    """
```

### ID Generation

```python
def node_id_hash(
    kind: str,
    name: str,
    file_path: str,
    line_start: int
) -> str:
    """
    Generate deterministic node ID.

    Format: "{kind}:{name}:{12-char-sha256}"

    Args:
        kind: Node type (function, contract, state_var)
        name: Node name
        file_path: Source file path
        line_start: Starting line number

    Returns:
        Stable, unique ID

    Example:
        node_id_hash("function", "transfer", "src/Token.sol", 45)
        # "function:transfer:a1b2c3d4e5f6"
    """

def edge_id_hash(
    edge_type: str,
    source: str,
    target: str
) -> str:
    """
    Generate deterministic edge ID.

    Format: "{type}:{source}->{target}:{8-char-sha256}"

    Args:
        edge_type: Edge type (CALLS, READS, WRITES, etc.)
        source: Source node ID
        target: Target node ID

    Returns:
        Stable, unique ID

    Example:
        edge_id_hash("CALLS", "function:transfer:abc", "function:_update:def")
        # "CALLS:function:transfer:abc->function:_update:def:12345678"
    """
```

### CFG Node Analysis

```python
def node_type_name(node: Node) -> str:
    """
    Get lowercase node type name.

    Returns one of:
        - "entry_point", "return", "if", "ifloop"
        - "startloop", "endloop", "assembly"
        - "expression", "variable", "throw", etc.
    """

def is_loop_start(node: Node) -> bool:
    """
    Check if node is loop start (STARTLOOP or first IFLOOP).
    """

def is_loop_end(node: Node) -> bool:
    """
    Check if node is ENDLOOP type.
    """

def node_has_external_call(node: Node) -> bool:
    """
    Check if CFG node contains external call.

    Checks for:
        - HighLevelCall (contract.method())
        - LowLevelCall (address.call())
        - LibraryCall to external library
    """

def node_has_delete(node: Node) -> bool:
    """
    Check if node contains delete operation.

    Example: delete balances[user];
    """
```

### Parameter Classification

```python
def classify_parameter_types(
    parameters: List[Variable]
) -> Dict[str, List[str]]:
    """
    Classify function parameters by type category.

    Returns dict with keys:
        - "addresses": address parameters
        - "amounts": uint/int parameters (likely amounts)
        - "data": bytes/string parameters
        - "arrays": array parameters
        - "structs": struct parameters
        - "other": unclassified

    Example:
        classify_parameter_types(fn.parameters)
        # {
        #     "addresses": ["to", "from"],
        #     "amounts": ["amount", "deadline"],
        #     "data": ["data"],
        #     ...
        # }
    """
```

---

## Context Helpers

**Location:** `src/alphaswarm_sol/context/` (various files)

### Token Estimation

```python
def estimate_tokens(text: str) -> int:
    """
    Rough token estimation (4 characters per token).

    Args:
        text: Input text

    Returns:
        Estimated token count

    Note:
        This is an approximation. Actual tokenization varies by model.

    Example:
        estimate_tokens("Hello, world!")
        # 4 (13 chars / 4 = 3.25, rounded up)
    """
```

### Confidence Helpers

```python
def merge_confidence(
    conf1: Confidence,
    conf2: Confidence
) -> Confidence:
    """
    Merge two confidence levels (takes lower).

    Hierarchy: CERTAIN > INFERRED > UNKNOWN

    Example:
        merge_confidence(Confidence.CERTAIN, Confidence.INFERRED)
        # Confidence.INFERRED
    """

def boost_confidence(
    conf: Confidence,
    boost_amount: int = 1
) -> Confidence:
    """
    Boost confidence level.

    Args:
        conf: Current confidence
        boost_amount: Levels to boost (1 or 2)

    Returns:
        Boosted confidence (capped at CERTAIN)
    """
```

### Source Tier Helpers

```python
def classify_source_tier(url: str) -> SourceTier:
    """
    Classify documentation source by trust level.

    Tiers:
        - OFFICIAL: Protocol docs, verified repos
        - AUDIT: Audit firm reports
        - COMMUNITY: Forums, blogs, tutorials
        - UNKNOWN: Unclassified

    Example:
        classify_source_tier("https://docs.uniswap.org/...")
        # SourceTier.OFFICIAL
    """

def source_trust_score(tier: SourceTier) -> float:
    """
    Get trust score for source tier.

    Returns:
        OFFICIAL: 1.0
        AUDIT: 0.9
        COMMUNITY: 0.6
        UNKNOWN: 0.3
    """
```

---

## Labeling Helpers

**Location:** `src/alphaswarm_sol/labels/` (various files)

### Prompt Building

```python
def build_labeling_prompt(
    taxonomy: LabelTaxonomy,
    context: Optional[str] = None
) -> str:
    """
    Build labeling prompt with available labels.

    Args:
        taxonomy: Label taxonomy to use
        context: Optional analysis context filter

    Returns:
        Formatted prompt string

    Example:
        prompt = build_labeling_prompt(CORE_TAXONOMY, "reentrancy")
        # Includes only reentrancy-relevant labels
    """

def format_function_context(
    graph: KnowledgeGraph,
    function_id: str,
    max_tokens: int = 2000
) -> str:
    """
    Format function context for labeling.

    Includes:
        - Function signature and modifiers
        - Key properties (visibility, state mutability)
        - Call relationships
        - State variable access

    Args:
        graph: Knowledge graph
        function_id: Function node ID
        max_tokens: Token budget

    Returns:
        Formatted context string
    """

def get_labels_for_context(
    taxonomy: LabelTaxonomy,
    context: str
) -> List[str]:
    """
    Get relevant label IDs for analysis context.

    Context mappings:
        - "reentrancy" -> external_interaction, security_pattern
        - "access_control" -> access_control
        - "value_handling" -> value_handling, state_mutation
        - "general" -> all labels

    Returns:
        List of label IDs
    """
```

### Confidence Mapping

```python
def llm_confidence_to_level(
    llm_confidence: float
) -> ConfidenceLevel:
    """
    Map LLM confidence score to discrete level.

    Thresholds:
        >= 0.8 -> HIGH
        >= 0.5 -> MEDIUM
        < 0.5 -> LOW

    Example:
        llm_confidence_to_level(0.92)
        # ConfidenceLevel.HIGH
    """
```

---

## Orchestration Helpers

**Location:** `src/alphaswarm_sol/orchestration/` (various files)

### Pool Helpers

```python
def can_advance_phase(pool: Pool) -> bool:
    """
    Check if pool can transition to next phase.

    Rules:
        - INTAKE -> CONTEXT: Always OK
        - CONTEXT -> BEADS: Must have graph
        - BEADS -> EXECUTE: Must have beads
        - EXECUTE -> VERIFY: All agents complete
        - VERIFY -> INTEGRATE: Debate complete or skipped
        - INTEGRATE -> COMPLETE: All verdicts collected

    Returns:
        True if advancement allowed
    """

def get_next_phase(current: PoolStatus) -> Optional[PoolStatus]:
    """
    Get next phase in execution sequence.

    Sequence:
        INTAKE -> CONTEXT -> BEADS -> EXECUTE -> VERIFY -> INTEGRATE -> COMPLETE

    Returns:
        Next status or None if terminal
    """

def should_pause_for_human(pool: Pool) -> bool:
    """
    Check if pool requires human input.

    Triggers:
        - Any verdict with human_flag=True
        - Debate with unresolved disagreement
        - CONFIRMED verdict without strong evidence

    Returns:
        True if human review needed
    """
```

### Verdict Helpers

```python
def create_uncertain_verdict(
    finding_id: str,
    reason: str
) -> Verdict:
    """
    Create UNCERTAIN verdict for missing context.

    Args:
        finding_id: Related finding ID
        reason: Why context is missing

    Returns:
        Verdict with confidence=UNCERTAIN, human_flag=True
    """

def merge_verdicts(
    verdicts: List[Verdict]
) -> Verdict:
    """
    Merge multiple verdicts into single verdict.

    Rules:
        - Majority confidence wins
        - Union of evidence
        - All rationales combined
        - human_flag if any True

    Example:
        merged = merge_verdicts([v1, v2, v3])
    """
```

### Evidence Helpers

```python
def create_evidence(
    file_path: str,
    line_start: int,
    line_end: int,
    snippet: Optional[str] = None,
    explanation: Optional[str] = None
) -> Evidence:
    """
    Create Evidence object with optional code snippet.

    Args:
        file_path: Relative file path
        line_start: Start line (1-indexed)
        line_end: End line (1-indexed)
        snippet: Code snippet (optional)
        explanation: Evidence explanation (optional)

    Returns:
        Evidence object
    """

def evidence_overlaps(e1: Evidence, e2: Evidence) -> bool:
    """
    Check if two evidence objects overlap in location.

    Overlap if same file and line ranges intersect.
    """
```

---

## Agent Helpers

**Location:** `src/alphaswarm_sol/agents/` (various files)

### Message Building

```python
def build_system_prompt(
    role: AgentRole,
    context: str,
    tools: List[Dict]
) -> str:
    """
    Build system prompt for agent role.

    Includes:
        - Role description and capabilities
        - Protocol context
        - Available tools
        - Output format instructions

    Args:
        role: Agent role
        context: Protocol/bead context
        tools: Available tools

    Returns:
        Formatted system prompt
    """

def format_messages(
    system_prompt: str,
    user_message: str,
    history: Optional[List[Dict]] = None
) -> List[Dict]:
    """
    Format messages for API call.

    Returns:
        List of message dicts with role/content
    """
```

### Usage Tracking

```python
def calculate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int
) -> float:
    """
    Calculate cost for model usage.

    Uses MODEL_PRICING from config.py.

    Returns:
        Cost in USD
    """

def aggregate_usage(
    usages: List[Dict[str, int]]
) -> Dict[str, int]:
    """
    Aggregate multiple usage dicts.

    Returns:
        {"input_tokens": total, "output_tokens": total}
    """
```

### Error Classification

```python
def is_retryable_error(error: Exception) -> bool:
    """
    Check if error should trigger retry.

    Retryable:
        - Rate limit errors (429)
        - Connection errors
        - Timeout errors
        - Server errors (5xx)

    Not retryable:
        - Auth errors (401/403)
        - Bad request (4xx except 429)
        - Invalid API key
    """

def classify_error(error: Exception) -> str:
    """
    Classify error for logging/metrics.

    Returns one of:
        - "rate_limit"
        - "connection"
        - "timeout"
        - "server_error"
        - "auth"
        - "bad_request"
        - "unknown"
    """
```

---

## Tool Helpers

**Location:** `src/alphaswarm_sol/tools/` (various files)

### Finding Helpers

```python
def normalize_severity(
    tool: str,
    raw_severity: str
) -> Severity:
    """
    Normalize tool-specific severity to standard levels.

    Args:
        tool: Tool name
        raw_severity: Tool's severity string

    Returns:
        Normalized Severity enum

    Example:
        normalize_severity("slither", "High")
        # Severity.HIGH
    """

def generate_finding_id(
    tool: str,
    detector: str,
    file_path: str,
    line: int
) -> str:
    """
    Generate stable finding ID.

    Format: "{tool}:{detector}:{file}:{line}:{hash}"

    Example:
        generate_finding_id("slither", "reentrancy-eth", "Token.sol", 45)
        # "slither:reentrancy-eth:Token.sol:45:abc12345"
    """
```

### Path Helpers

```python
def normalize_path(
    path: str,
    project_root: Path
) -> str:
    """
    Normalize file path to relative format.

    Handles:
        - Absolute paths
        - Windows/Unix path separators
        - Duplicate slashes
        - ./  and ../ components

    Returns:
        Clean relative path
    """

def is_solidity_file(path: str) -> bool:
    """
    Check if path is a Solidity file.

    Returns True for .sol files.
    """

def is_test_file(path: str) -> bool:
    """
    Check if path is a test file.

    Indicators:
        - Contains "test" in path
        - In test/ or tests/ directory
        - Filename starts with Test or ends with Test.sol
    """
```

### Detector Helpers

```python
def is_excluded_detector(
    tool: str,
    detector: str,
    config: ToolConfig
) -> bool:
    """
    Check if detector should be excluded.

    Args:
        tool: Tool name
        detector: Detector ID
        config: Tool configuration

    Returns:
        True if detector is excluded in config
    """

def get_detector_category(
    tool: str,
    detector: str
) -> Optional[str]:
    """
    Get vulnerability category for detector.

    Categories:
        - reentrancy
        - access-control
        - arithmetic
        - oracle
        - etc.
    """
```

---

## Quick Reference

### Most Used Helpers

| Helper | Location | Purpose |
|--------|----------|---------|
| `source_location()` | builder/helpers.py | Extract location from Slither objects |
| `node_id_hash()` | builder/helpers.py | Generate stable node IDs |
| `is_access_gate()` | builder/helpers.py | Check if modifier is access control |
| `estimate_tokens()` | context | Rough token estimation |
| `can_advance_phase()` | orchestration | Check phase transition rules |
| `normalize_severity()` | tools | Standardize severity levels |
| `is_retryable_error()` | agents | Classify errors for retry |

### Import Patterns

```python
# Builder helpers
from alphaswarm_sol.kg.builder.helpers import (
    source_location,
    evidence_from_location,
    is_access_gate,
    node_id_hash,
    edge_id_hash,
)

# Labeling helpers
from alphaswarm_sol.labels.prompts import (
    build_labeling_prompt,
    format_function_context,
)

# Orchestration helpers
from alphaswarm_sol.orchestration.rules import (
    can_advance_phase,
    should_pause_for_human,
)

# Tool helpers
from alphaswarm_sol.tools.sarif import (
    normalize_severity,
    normalize_path,
)
```

---

*Reference: helpers.md*
*Last Updated: 2026-01-22*
