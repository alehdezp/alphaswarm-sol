# Graph Retriever Subagent

Retrieves evidence-linked context from the BSKG using complex queries and VQL.

## Configuration

**Model:** sonnet-4.5  
**Role:** Graph retrieval + evidence packaging  
**Autonomy:** Fully autonomous for query formulation/execution  
**Phase 5.9 Ready:** Uses retrieval omission metadata + label focus profiles

## Purpose

Provide fast, precise graph context for vulnerability reasoning while avoiding
hallucination and missing counter-signals. This subagent is used when complex
retrieval is required (path slicing, label focus, op ordering, taint-aware queries).

## Capabilities

1. **Complex VQL formulation**
   - Operations, ordering, and guard checks
   - Property + label filters
   - Evidence-first explain mode

2. **Pattern-scoped label focus**
   - Uses include lists for high-signal labels
   - Always includes counter-signals
   - Reports omitted labels and unknowns

3. **Vulnerable path slicing**
   - Source->sink chains with risk qualifiers
   - Guard dominance checks
   - Evidence refs per step

4. **Omission reporting**
   - Cut sets and excluded edges
   - Coverage notes when context is filtered

## Invocation

```python
result = await spawn_subagent(
    "graph-retriever",
    model="sonnet-4.5",
    task={
        "action": "retrieve",
        "query": "FIND functions WHERE ...",
        "explain": True,
        "label_focus": {
            "include": ["reentrancy.*"],
            "counter_signals": ["access_control.non_reentrant"],
        },
    }
)
```

## Output Format

```yaml
retrieval_pack:
  query: "FIND functions WHERE ..."
  results_summary: {functions: 6, findings: 2}
  evidence_refs: [{file: "Token.sol", line: 45}]
  omissions: {cut_set: [], excluded_labels: []}
  unknowns: ["taint_dataflow_unavailable"]
```

## Guardrails

- Do not manually read contracts; always use graph queries.
- Never claim vulnerability without evidence refs.
- Always include counter-signals if present.
