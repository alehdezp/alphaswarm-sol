# Trace Schema Reference

Complete specification for AlphaSwarm OpenTelemetry traces following GenAI semantic conventions.

## Overview

AlphaSwarm uses OpenTelemetry for distributed tracing of multi-agent orchestration. All traces follow the [GenAI Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/) with AlphaSwarm-specific extensions.

## Span Types

### Agent Span

Represents execution of a single agent (attacker, defender, verifier).

**Naming:**
```
name: agent.{agent_type}
kind: INTERNAL
```

**Required Attributes:**

| Attribute | Type | Description | Example |
|-----------|------|-------------|---------|
| `gen_ai.system` | string | LLM provider | `anthropic`, `openai` |
| `gen_ai.request.model` | string | Model name | `claude-3-5-sonnet` |
| `gen_ai.operation.name` | string | Operation type | `investigate`, `verify` |
| `alphaswarm.pool.id` | string | Pool identifier | `pool-abc123` |
| `alphaswarm.bead.id` | string | Bead identifier | `VKG-042` |
| `alphaswarm.agent.type` | string | Agent type | `vrs-attacker`, `vrs-defender` |
| `alphaswarm.agent.role` | string | Agent role | `attacker`, `defender`, `verifier` |

**Optional Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `gen_ai.usage.input_tokens` | int | Input token count |
| `gen_ai.usage.output_tokens` | int | Output token count |
| `gen_ai.usage.total_tokens` | int | Total tokens (computed) |
| `gen_ai.usage.cost_usd` | float | Cost in USD |
| `gen_ai.response.finish_reason` | string | `stop`, `length`, `error` |

**Events:**

- `gen_ai.input`: Input summary and token estimate
  - Attributes: `input_summary` (string), `token_estimate` (int)
- `gen_ai.output`: Output summary, tokens, cost
  - Attributes: `output_summary` (string), `input_tokens` (int), `output_tokens` (int), `cost_usd` (float), `finish_reason` (string)

**Example:**

```python
with create_agent_span(
    agent_type="vrs-attacker",
    pool_id="pool-abc123",
    bead_id="VKG-042",
    model="claude-3-5-sonnet",
    role="attacker",
) as span:
    # Span attributes set automatically
    # gen_ai.system = "anthropic"
    # gen_ai.request.model = "claude-3-5-sonnet"
    # alphaswarm.agent.type = "vrs-attacker"
    ...
```

### Tool Span

Represents execution of an external tool (Slither, Mythril, etc.).

**Naming:**
```
name: tool.{tool_name}
kind: CLIENT
```

**Required Attributes:**

| Attribute | Type | Description | Example |
|-----------|------|-------------|---------|
| `alphaswarm.tool.name` | string | Tool name | `slither`, `mythril` |
| `alphaswarm.pool.id` | string | Pool identifier | `pool-abc123` |

**Optional Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `alphaswarm.tool.version` | string | Tool version |
| `alphaswarm.tool.duration_ms` | int | Execution duration |
| `alphaswarm.tool.exit_code` | int | Exit code (0 = success) |

**Example:**

```python
with create_tool_span(
    tool_name="slither",
    pool_id="pool-abc123",
) as span:
    findings = run_slither(...)
    span.set_attribute("alphaswarm.tool.exit_code", 0)
```

### Handoff Span

Represents context transfer between agents.

**Naming:**
```
name: agent.handoff
kind: INTERNAL
```

**Required Attributes:**

| Attribute | Type | Description | Example |
|-----------|------|-------------|---------|
| `alphaswarm.handoff.from_agent` | string | Source agent | `vrs-attacker` |
| `alphaswarm.handoff.to_agent` | string | Target agent | `vrs-defender` |
| `alphaswarm.pool.id` | string | Pool identifier | `pool-abc123` |
| `alphaswarm.bead.id` | string | Bead identifier | `VKG-042` |

**Optional Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `alphaswarm.handoff.context_keys` | string[] | Context items passed |
| `alphaswarm.handoff.context_size_bytes` | int | Context payload size |

**Example:**

```python
with create_handoff_span(
    from_agent="vrs-attacker",
    to_agent="vrs-defender",
    pool_id="pool-abc123",
    bead_id="VKG-042",
) as span:
    span.set_attribute("alphaswarm.handoff.context_keys", ["findings", "evidence"])
```

### Guardrail Span

Represents policy/guardrail check.

**Naming:**
```
name: guardrail.{guardrail_type}
kind: INTERNAL
```

**Required Attributes:**

| Attribute | Type | Description | Example |
|-----------|------|-------------|---------|
| `alphaswarm.guardrail.id` | string | Guardrail identifier | `evidence-gate` |
| `alphaswarm.guardrail.type` | string | Guardrail type | `evidence_integrity` |
| `alphaswarm.guardrail.result` | string | Result | `passed`, `failed`, `warning` |
| `alphaswarm.pool.id` | string | Pool identifier | `pool-abc123` |

**Optional Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `alphaswarm.guardrail.violation_details` | string | Violation message if failed |

**Example:**

```python
with create_guardrail_span(
    guardrail_id="evidence-gate",
    guardrail_type="evidence_integrity",
    pool_id="pool-abc123",
) as span:
    result = check_evidence_requirements(...)
    span.set_attribute("alphaswarm.guardrail.result", "passed")
```

## Usage Attributes (GenAI Conventions)

All token and cost tracking follows GenAI semantic conventions:

| Attribute | Type | Description | When Used |
|-----------|------|-------------|-----------|
| `gen_ai.usage.input_tokens` | int | Input token count | After LLM call |
| `gen_ai.usage.output_tokens` | int | Output token count | After LLM call |
| `gen_ai.usage.total_tokens` | int | Total tokens | After LLM call |
| `gen_ai.usage.cost_usd` | float | Cost in USD | After LLM call |

**Recording Usage:**

```python
record_llm_usage(
    span,
    input_tokens=1500,
    output_tokens=800,
    cost_usd=0.05,
)
```

## Trace Context Propagation

Trace context propagates through Pool/Bead metadata:

### Pool Metadata

```python
pool = Pool(
    id="pool-abc123",
    metadata={
        "trace_id": "trace_xyz789",  # Root trace ID
    },
)
```

### Bead Metadata

```python
bead = Bead(
    id="VKG-042",
    pool_id="pool-abc123",
    metadata={
        "trace_id": "trace_xyz789",   # Inherited from pool
        "parent_span_id": "span_def",  # Parent span for nesting
    },
)
```

### Function Parameters

```python
def handle_agent_execution(
    pool_id: str,
    agent_type: str,
    trace_id: str = None,  # Optional trace_id parameter
):
    with create_agent_span(
        agent_type=agent_type,
        pool_id=pool_id,
    ) as span:
        # trace_id automatically propagated from context
        ...
```

## Trace Backends

### Jaeger

```python
setup_tracing(
    service_name="alphaswarm",
    endpoint="http://localhost:4318/v1/traces",
)
```

View traces at: http://localhost:16686

### Console (Debug)

```python
setup_tracing()  # No endpoint = console export
```

### OTLP (Production)

```python
setup_tracing(
    service_name="alphaswarm",
    endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"),
)
```

## Best Practices

1. **Always set trace_id** in pool metadata at creation
2. **Propagate trace_id** through all function calls
3. **Don't log full prompts** in span attributes (use events with summaries)
4. **Record token usage** on every LLM call
5. **Use child spans** for nested operations (tool calls within agents)
6. **Shutdown tracing** gracefully to flush pending spans

```python
from alphaswarm_sol.observability import shutdown_tracing

# At application shutdown
shutdown_tracing()
```

## Schema Validation

Attributes conform to OpenTelemetry semantic conventions:

- **GenAI Conventions**: `gen_ai.*` namespace
- **AlphaSwarm Extensions**: `alphaswarm.*` namespace
- **Custom Attributes**: Use `alphaswarm.custom.*` for project-specific data

## See Also

- [Observability Guide](../guides/observability.md)
- [OpenTelemetry GenAI Conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/)
