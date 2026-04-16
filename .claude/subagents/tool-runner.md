# Tool Runner Subagent

Executes external static analysis tools and parses their output.

## Configuration

**Model:** haiku-4.5
**Role:** Tool execution, output parsing, error handling
**Autonomy:** Fully autonomous for tool running
**Phase 5.2 Ready:** Hook-compatible, can be spawned by SDK

## Purpose

Run external tools (Slither, Aderyn, Mythril, etc.) with:
- Proper configuration per tool
- Timeout enforcement
- Error recovery
- Output parsing to BSKG format

This subagent handles the mechanical work of tool execution, freeing
higher-tier agents (sonnet/opus) for reasoning tasks.

## Capabilities

1. **Execute any tool from ToolRegistry**
   - Slither, Aderyn, Mythril, Semgrep, etc.
   - Checks tool availability before execution

2. **Apply VKG-optimized configurations**
   - Exclude low-value detectors
   - Filter library paths
   - Set appropriate timeouts

3. **Parse tool-specific output formats**
   - JSON output to VKGFinding
   - SWC mapping for Mythril
   - Detector mapping for Slither/Aderyn

4. **Handle failures gracefully**
   - Timeout recovery with partial results
   - Compilation error diagnosis
   - Retry on transient failures

5. **Report partial results on timeout**
   - Capture output before timeout
   - Mark as partial=True
   - Still useful for analysis

## Invocation

### Via Task (Phase 5.2 - future)

```python
from true_vkg.sdk import spawn_subagent

result = await spawn_subagent(
    "tool-runner",
    model="haiku-4.5",
    task={
        "action": "run_tool",
        "tool": "slither",
        "project_path": "/path/to/project",
        "config": {
            "timeout": 120,
            "exclude_detectors": ["naming-convention"],
        }
    }
)
```

### Direct (current Phase 5.1)

```python
from true_vkg.tools.executor import ToolExecutor
from true_vkg.tools.config import get_optimal_config

executor = ToolExecutor()
config = get_optimal_config("slither")
result = executor.execute_tool("slither", config, project_path)
```

### Via Hook Interface (Phase 5.2)

```python
from true_vkg.tools.hooks import run_tool, ToolRunRequest, HookPriority

# Simple invocation
result = await run_tool("slither", Path("./contracts"))

# Full control
request = ToolRunRequest(
    tool="mythril",
    project_path=Path("./contracts"),
    config={"timeout": 300},
    priority=HookPriority.HIGH,
    use_cache=True,
)

hook = get_tool_hook()
request_id = await hook.submit(request)
result = await hook.get_result(request_id)
```

## Output Format

Returns ExecutionResult:

```python
@dataclass
class ExecutionResult:
    tool: str              # Tool name (slither, mythril, etc.)
    success: bool          # True if completed without fatal error
    findings: List[VKGFinding]  # Normalized findings
    execution_time: float  # Seconds
    error: Optional[str]   # Error message if failed
    from_cache: bool       # True if from cache
    partial: bool          # True if timed out with partial results
    raw_output: Optional[str]  # Truncated raw output
    metadata: Dict[str, Any]   # Additional info (exit_code, etc.)
```

### VKGFinding structure

```python
@dataclass
class VKGFinding:
    rule_id: str           # slither-reentrancy-eth, mythril-swc-107
    title: str             # Human-readable title
    message: str           # Description
    severity: str          # critical, high, medium, low, info
    file_path: str         # Source file
    line: int              # Line number
    column: int            # Column (if available)
    tool: str              # Source tool
    confidence: str        # high, medium, low
    vkg_pattern: Optional[str]  # Mapped BSKG pattern ID
    swc_id: Optional[str]  # SWC ID for Mythril
```

## Error Handling

| Error Type | Action |
|------------|--------|
| Tool not found | Return NOT_INSTALLED status, suggest install command |
| Timeout | Capture partial output, mark partial=True |
| Compilation error | Log detailed error, suggest fixes |
| Parse error | Log error, return empty findings, include raw output |
| Config error | Retry with defaults |
| Permission denied | Log error, suggest fix |

### Error recovery hints

```python
result = executor.execute_tool("slither", config, path)

if not result.success:
    if "not found" in result.error:
        print("Install slither: pip install slither-analyzer")
    elif "compilation" in result.error.lower():
        print("Check Solidity version. Try: solc-select use 0.8.20")
    elif "timeout" in result.error.lower():
        print("Try increasing timeout or analyzing fewer files")
```

## Parallel Execution

The subagent supports parallel tool execution within groups:

```python
# Executor handles parallelization
executor = ToolExecutor(max_workers=4)

# Execute parallel group
results = executor.execute_parallel_group(
    tools=["slither", "aderyn", "semgrep"],
    configs={...},
    project_path=path,
)
```

## Caching

When cache is available:

1. Check cache before execution
2. Return cached result if valid
3. Execute if cache miss
4. Store successful results

```python
# Cache check flow
result = executor._execute_with_cache(
    tool="slither",
    config=config,
    project_path=path,
    use_cache=True,
)

if result.from_cache:
    print("Result from cache, no execution needed")
```

## Model Tier Rationale

Uses **haiku-4.5** because:

1. **Tool execution is mechanical**
   - Run command with arguments
   - Capture stdout/stderr
   - Parse structured JSON output

2. **No complex reasoning required**
   - Detector mappings are deterministic
   - SWC to BSKG pattern mapping is predefined
   - No interpretation of findings

3. **Cost efficiency for many tool runs**
   - Multiple tools per audit
   - Multiple contracts per project
   - Frequent re-runs during development

4. **Fast inference for responsive execution**
   - Quick tool invocation
   - Minimal latency overhead

### When higher tier is needed

Tool **coordination** (which tools to run, why) uses **sonnet-4.5**:
- Project analysis requires understanding
- Strategy decisions have consequences
- Explaining rationale needs reasoning

Tool **execution** uses **haiku-4.5**:
- Mechanical: run command, parse output
- No judgment calls
- High volume

## Integration Points

### ToolExecutor

```python
from true_vkg.tools.executor import ToolExecutor

executor = ToolExecutor()
# Uses this subagent's logic internally
```

### ToolRegistry

```python
from true_vkg.tools.registry import ToolRegistry

registry = ToolRegistry()
available = registry.get_available_tools()
# Subagent only runs available tools
```

### Hook System (Phase 5.2)

```python
from true_vkg.tools.hooks import LocalToolHook, ToolRunRequest

# Hook wraps subagent capabilities
hook = LocalToolHook()
request_id = await hook.submit(request)
```

## Related Components

| Component | Relationship |
|-----------|--------------|
| ToolCoordinator | Decides which tools to run |
| ToolExecutor | Orchestrates parallel execution |
| ToolRunner | Low-level subprocess execution |
| Tool Adapters | Parse tool-specific output |
| Hook System | Async interface for Phase 5.2 |

## Security Considerations

1. **Sandboxing** - Tools run in isolated environment
2. **Timeout enforcement** - Prevent runaway processes
3. **Output truncation** - Limit memory usage
4. **No arbitrary commands** - Only registered tools
5. **Path validation** - Only analyze specified paths
