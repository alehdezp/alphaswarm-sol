# Observability Guide

This guide explains how to use AlphaSwarm's observability infrastructure for tracing, audit logging, and evidence lineage tracking.

## Overview

Phase 7.1.5 introduces production-grade observability across multi-agent orchestration:

- **Tracing**: OpenTelemetry-based span tracking for agents, tools, and handoffs
- **Audit Logging**: Structured JSON logs for verdicts, evidence usage, and policy checks
- **Evidence Lineage**: Complete provenance chains from BSKG/tool sources to verdicts

## Quick Start

### Enable Tracing

```python
from alphaswarm_sol.observability import setup_tracing, get_tracer

# Initialize tracing (call once at startup)
tracer = setup_tracing(
    service_name="alphaswarm",
    endpoint="http://localhost:4318/v1/traces",  # Optional: OTLP endpoint
)

# Get tracer for instrumentation
tracer = get_tracer("alphaswarm.orchestration")
```

### Create Spans

```python
from alphaswarm_sol.observability import (
    create_agent_span,
    create_tool_span,
    create_handoff_span,
    create_guardrail_span,
)

# Agent execution span
with create_agent_span(
    agent_type="vrs-attacker",
    pool_id="pool-abc123",
    bead_id="VKG-042",
    model="claude-3-5-sonnet",
    role="attacker",
) as span:
    # Agent work here
    result = execute_agent(...)

    # Record token usage
    span.set_attribute("gen_ai.usage.input_tokens", result.input_tokens)
    span.set_attribute("gen_ai.usage.output_tokens", result.output_tokens)

# Tool execution span (child of agent)
with create_tool_span(
    tool_name="slither",
    pool_id="pool-abc123",
) as span:
    # Tool execution
    findings = run_slither(...)

# Handoff span
with create_handoff_span(
    from_agent="vrs-attacker",
    to_agent="vrs-defender",
    pool_id="pool-abc123",
    bead_id="VKG-042",
) as span:
    # Pass context to next agent
    pass

# Guardrail span
with create_guardrail_span(
    guardrail_id="evidence-gate",
    guardrail_type="evidence_integrity",
    pool_id="pool-abc123",
) as span:
    # Check policy
    result = check_evidence_requirements(...)
    span.set_attribute("alphaswarm.guardrail.result", "passed")
```

### Record Events

```python
from alphaswarm_sol.observability import (
    record_input_event,
    record_output_event,
    record_error_event,
    record_llm_usage,
)

# Record input (summary only, not full prompt)
record_input_event(
    span,
    input_summary="Investigating reentrancy in withdraw()",
    token_estimate=500,
)

# Record output with token usage
record_output_event(
    span,
    output_summary="Found potential reentrancy pattern",
    input_tokens=1500,
    output_tokens=800,
    cost_usd=0.05,
    finish_reason="stop",
)

# Record LLM usage separately
record_llm_usage(
    span,
    input_tokens=1500,
    output_tokens=800,
    cost_usd=0.05,
)

# Record errors
try:
    result = call_llm(...)
except Exception as e:
    record_error_event(span, e, recoverable=True)
    raise
```

## Audit Logging

### Setup AuditLogger

```python
from alphaswarm_sol.observability.audit import AuditLogger, AuditCategory
from pathlib import Path

logger = AuditLogger(log_path=Path("logs/audit.jsonl"))
```

### Log Verdicts

```python
logger.log_verdict(
    pool_id="pool-abc123",
    bead_id="VKG-042",
    verdict="vulnerable",
    confidence="LIKELY",
    evidence_refs=["ev-001", "ev-002"],
    agent_type="vrs-attacker",
    trace_id="trace_xyz789",
)
```

### Log Policy Violations

```python
logger.log_policy_violation(
    pool_id="pool-abc123",
    policy_id="cost_budget.hard_limit",
    violation_type="budget_exceeded",
    actor="vrs-attacker",
    severity="critical",
    suggested_action="block",
    details={"current_cost": 15.0, "limit": 10.0},
    trace_id="trace_xyz789",
)
```

### Log Evidence Usage

```python
logger.log_evidence_usage(
    pool_id="pool-abc123",
    bead_id="VKG-042",
    evidence_id="ev-001",
    source_type="BSKG",
    source_id="node_func_vault_withdraw_123",
    agent_type="vrs-attacker",
    trace_id="trace_xyz789",
)
```

## Evidence Lineage

### Track Evidence Origin

```python
from alphaswarm_sol.observability.lineage import LineageTracker, SourceType

tracker = LineageTracker()

# Create lineage when extracting evidence
lineage = tracker.create_lineage(
    evidence_id="ev-001",
    source_type=SourceType.BSKG,
    source_id="node_func_vault_withdraw_123",
    extracting_agent="vrs-attacker",
)

# Add transformation steps
tracker.add_transformation(
    evidence_id="ev-001",
    transform_type="pattern_match",
    transforming_agent="vrs-attacker",
)

# Add verification
tracker.add_verification(
    evidence_id="ev-001",
    verifying_agent="vrs-verifier",
    verification_result="confirmed",
)
```

### Query Lineage

```python
# Get lineage for evidence
lineage = tracker.get_lineage("ev-001")
print(lineage.chain)  # Full provenance chain

# Find all evidence from a source
evidence = tracker.query_by_source(
    SourceType.BSKG,
    "node_func_vault_withdraw_123",
)
```

## Trace Backends

### Jaeger (Development)

```bash
# Start Jaeger
docker run -d \
  -p 16686:16686 \
  -p 4317:4317 \
  -p 4318:4318 \
  jaegertracing/all-in-one:latest

# View traces at http://localhost:16686
```

Configure AlphaSwarm to export to Jaeger:

```python
setup_tracing(
    service_name="alphaswarm",
    endpoint="http://localhost:4318/v1/traces",
)
```

### Console (Debug)

```python
# No endpoint = console output
setup_tracing()  # Prints spans to stdout
```

## Best Practices

1. **Always propagate trace_id** through Pool/Bead metadata
2. **Don't log full prompts** in span attributes (use events with summaries)
3. **Record evidence lineage** at extraction time, not later
4. **Include trace_id** in all audit log entries for correlation
5. **Shutdown tracing** gracefully to flush pending spans

```python
from alphaswarm_sol.observability import shutdown_tracing

# At application shutdown
shutdown_tracing()
```

## Integration with Existing Code

### Pool/Bead Context

```python
# Pool carries trace_id
pool = Pool(
    id="pool-abc123",
    metadata={"trace_id": "trace_xyz789"},
)

# Beads inherit trace_id
bead = Bead(
    id="VKG-042",
    pool_id=pool.id,
    metadata={"trace_id": pool.metadata["trace_id"]},
)
```

### Handler Instrumentation

```python
# In orchestration/handlers.py
from alphaswarm_sol.observability import create_agent_span

def handle_agent_execution(pool_id: str, agent_type: str, ...):
    with create_agent_span(
        agent_type=agent_type,
        pool_id=pool_id,
        model=model,
    ) as span:
        # Execute agent
        result = agent.execute(...)

        # Record usage
        record_llm_usage(span, result.input_tokens, result.output_tokens, result.cost)

        return result
```

## See Also

- [Trace Schema Reference](../reference/trace-schema.md)
- [Governance Guide](governance.md)
- [Reliability Guide](reliability.md)
