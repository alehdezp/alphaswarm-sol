# Adapter Capabilities Reference

**Phase:** 07.1.4 Interop & Orchestrator Adapters
**Last Updated:** 2026-01-29

## Overview

AlphaSwarm VRS workflows can execute across multiple orchestration frameworks while preserving evidence-first outputs and BSKG query requirements. The adapter system provides a unified interface with capability-based feature detection.

**Supported Frameworks:**
- **Anthropic Agents SDK**: Native Anthropic with prompt caching and tool conversion
- **LangGraph**: LangChain's stateful graph orchestration with persistent checkpointing
- **AutoGen**: Microsoft's multi-agent conversation framework
- **CrewAI**: Role-based agent collaboration with shared memory
- **Beads (Gastown)**: Evidence-first investigation pattern with replay support

**Design Principles:**
1. **Evidence Preservation**: VulnerabilityBead contracts survive framework boundaries
2. **Trace Continuity**: Distributed tracing propagates across agent handoffs
3. **Capability Detection**: Runtime adapter selection based on required features
4. **Framework Agnostic**: Unified AgentConfig and AgentResponse interfaces

## Capability Definitions

| Capability | Category | Description |
|------------|----------|-------------|
| `TOOL_EXECUTION` | Tool | Can execute tools/functions during agent execution |
| `TOOL_CONVERSION` | Tool | Can convert tools between formats (e.g., Anthropic ↔ OpenAI) |
| `MEMORY_SHARED` | Memory | Shared memory accessible across all agents |
| `MEMORY_THREAD` | Memory | Thread-local memory scoped to conversation thread |
| `MEMORY_PERSISTENT` | Memory | Persistent checkpointing for resumable execution |
| `TRACE_PROPAGATION` | Trace | Can propagate trace context across handoffs |
| `TRACE_EXPORT_OTEL` | Trace | Exports OpenTelemetry-compatible traces |
| `TRACE_EXPORT_CUSTOM` | Trace | Exports custom trace format |
| `HANDOFF_SYNC` | Handoff | Supports synchronous agent-to-agent handoffs |
| `HANDOFF_ASYNC` | Handoff | Supports asynchronous agent-to-agent handoffs |
| `GUARDRAILS` | VRS | Input/output guardrails for safety constraints |
| `COST_TRACKING` | VRS | Tracks token usage and costs per agent |
| `BEAD_REPLAY` | VRS | Can replay bead state for interrupted investigations |
| `GRAPH_FIRST` | VRS | Enforces BSKG query requirements before manual code reading |

## Adapter Comparison Matrix

| Framework | Tool Exec | Tool Conv | Memory | Trace | Handoff | Guardrails | Cost | Bead Replay | Graph First |
|-----------|-----------|-----------|--------|-------|---------|------------|------|-------------|-------------|
| **agents-sdk** | ✅ | ✅ | - | ✅ | Sync | ✅ | ✅ | ❌ | ❌ |
| **langgraph** | ✅ | - | Persistent | ✅ OTEL | Async | - | - | ✅ | ❌ |
| **autogen** | ✅ | - | Thread | - | Both | - | - | ❌ | ❌ |
| **crewai** | ✅ | - | Shared | - | Sync | - | - | ❌ | ❌ |
| **beads-gastown** | - | - | Persistent | - | - | - | - | ✅ | ✅ |

**Legend:**
- ✅ = Fully supported
- ❌ = Not supported
- `-` = Partial or not applicable

## Evidence Preservation

Evidence contracts (VulnerabilityBead) must remain unchanged during framework transitions. The adapter system validates evidence integrity through:

1. **Evidence Snapshots**: Captured in HandoffContext before transfer
2. **Validation Methods**: `preserve_evidence()` and `validate_evidence_preserved()`
3. **Critical Fields**: Bead ID, vulnerability class, severity, confidence, operations

**Evidence Modes:**
- `inline`: Evidence embedded in conversation messages
- `bead`: Evidence passed as structured VulnerabilityBead object
- `external`: Evidence stored externally with reference ID

**Warnings:**
If an adapter lacks `BEAD_REPLAY` or `GRAPH_FIRST`, evidence preservation warnings are issued:

```python
from alphaswarm_sol.adapters.capability import check_evidence_requirements

warnings = check_evidence_requirements("autogen")
# Returns: ["Adapter 'autogen' lacks BEAD_REPLAY capability..."]
```

## Trace Propagation

Distributed tracing enables observability across agent handoffs. The `TraceContext` object carries:

- **trace_id**: Unique trace identifier (W3C format compatible)
- **span_id**: Current span ID
- **parent_span_id**: Parent span for nesting
- **operation**: Operation name (e.g., "vrs.investigate")
- **attributes**: Key-value trace enrichment
- **events**: Timestamped trace events

**Propagation Modes:**
- `header`: Trace context in message headers (HTTP-like)
- `context`: Trace context in execution context (LangGraph checkpoints)
- `none`: No trace propagation

**Example:**
```python
from alphaswarm_sol.adapters import TraceContext

trace = TraceContext(
    trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
    span_id="00f067aa0ba902b7",
    operation="vrs.investigate",
    attributes={"bead_id": "VKG-001", "severity": "critical"},
)
trace.add_event("handoff_initiated")

# Propagate to target agent
response = await adapter.spawn_with_trace(config, task, trace)
```

## Usage Examples

### Check Adapter Capabilities

```python
from alphaswarm_sol.adapters.capability import (
    get_capability_matrix,
    AdapterCapability,
)

matrix = get_capability_matrix("agents-sdk")

if matrix.supports(AdapterCapability.GUARDRAILS):
    print("Guardrails available")

if matrix.supports_all({
    AdapterCapability.TOOL_EXECUTION,
    AdapterCapability.COST_TRACKING,
}):
    print("Can execute tools with cost tracking")

missing = matrix.missing_for({
    AdapterCapability.BEAD_REPLAY,
    AdapterCapability.GRAPH_FIRST,
})
if missing:
    print(f"Missing VRS features: {missing}")
```

### Execute Agent with Adapter

```python
from alphaswarm_sol.adapters import OrchestratorAdapter, AdapterConfig
from alphaswarm_sol.agents.runtime.base import AgentConfig, AgentRole

# Create adapter (implementation in Phase 07.1.4-02)
adapter_config = AdapterConfig(
    name="agents-sdk",
    capabilities=matrix.capabilities,
    evidence_mode="bead",
    trace_propagation="header",
)
adapter = AgentsSDKAdapter(adapter_config)

# Execute agent
agent_config = AgentConfig(
    role=AgentRole.ATTACKER,
    system_prompt="You are a security expert...",
    tools=[],
)
response = await adapter.execute_agent(agent_config, messages)
```

### Agent Handoff with Evidence Preservation

```python
from alphaswarm_sol.adapters import HandoffContext

ctx = HandoffContext(
    source_agent="vrs-attacker",
    target_agent="vrs-defender",
    bead_id="VKG-001",
    trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
)

# Preserve evidence before handoff
preserved_bead = adapter.preserve_evidence(bead, ctx)

# Perform handoff
result = await adapter.handoff(ctx)

if result.success and result.evidence_preserved:
    print("Handoff successful with evidence preserved")
else:
    print(f"Handoff failed: {result.errors}")
```

## Integration Notes

### Agentwise Multi-Agent Marketplace

**Agentwise** is a platform for discovering and composing AI agents into workflows. Key features:

- **Agent Discovery**: Browse agents by capability, pricing, and performance
- **Agent Composition**: Chain agents into multi-step workflows
- **Payment Handling**: Built-in payment routing for agent usage
- **Quality Metrics**: Agent ratings and success rates

**VRS Integration (Future Work):**
- Expose VRS investigation agents (attacker, defender, verifier) as Agentwise services
- Enable composition with external security agents (e.g., fuzz testing, formal verification)
- Payment model: Per-investigation pricing with confidence-based discounts

### Agentrooms Persistent Environments

**Agentrooms** provides persistent, containerized environments for long-running agent sessions. Key features:

- **Session Persistence**: Agents maintain state across disconnections
- **Resource Isolation**: Each agent runs in isolated container
- **File System**: Persistent storage for artifacts (graphs, reports)
- **Collaboration**: Multiple agents can share workspace

**VRS Integration (Future Work):**
- Deploy VRS pools in Agentrooms for multi-day audits
- Persistent BSKG graphs for incremental analysis
- Shared context packs across investigation sessions
- Replay interrupted investigations from checkpoints

**Key Considerations:**
1. **Agent Discovery**: How to expose VRS capabilities in Agentwise catalog
2. **Session Persistence**: Mapping VulnerabilityBead state to Agentrooms checkpoints
3. **Payment Handling**: Token-based billing vs. per-finding pricing
4. **Security**: Sandboxing untrusted contract analysis in isolated environments

## See Also

- [Agent Runtime Base](../../src/alphaswarm_sol/agents/runtime/base.py) - AgentConfig and AgentResponse
- [Bead Schema](../../src/alphaswarm_sol/beads/schema.py) - VulnerabilityBead structure
- [Orchestration Handlers](../../src/alphaswarm_sol/orchestration/handlers.py) - Pool execution
- [PHILOSOPHY.md](../PHILOSOPHY.md) - VRS design principles
