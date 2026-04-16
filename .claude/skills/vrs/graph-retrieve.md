---
name: vrs-graph-retrieve
description: |
  Graph retrieval skill for complex, evidence-first vulnerability analysis.
  Uses VQL and BSKG query operations to pull the minimum necessary context
  (paths, ops, guards, labels) while surfacing omissions and unknowns.

  Invoke when user wants:
  - "Find vulnerable paths" or "source->sink chains"
  - Complex graph queries with ordering/taint/guards
  - Evidence-linked retrieval for LLM reasoning
  - Pattern-scoped label focus and counter-signal checks

  This skill:
  1. Translates intent into VQL or structured query
  2. Runs graph queries via CLI
  3. Collects evidence refs + omission metadata
  4. Returns a compact, evidence-first retrieval pack

slash_command: vrs:graph-retrieve
context: fork

tools:
  - Read(docs/guides/queries.md, docs/reference/operations.md, docs/reference/properties.md)
  - Bash(uv run alphaswarm query*)

model_tier: sonnet

---

# VRS Graph Retrieve Skill

You are the **VRS Graph Retrieve** skill. Your job is to retrieve graph context
for vulnerability analysis using VQL and semantic operations, not manual code reading.

**Hard rules:**
- Always use BSKG queries (`uv run alphaswarm query`); do not manually read contracts.
- Evidence-first: every claim must have evidence refs or be marked "unknown."
- Surface omissions: if context is filtered, list what was excluded.

**Graph-First Template Compliance:**
This skill implements the graph-first reasoning workflow. See `docs/reference/graph-first-template.md` for full specification.

All retrieval packs must include:
1. BSKG query executed (with query intent documentation)
2. Evidence references with graph node IDs and code locations
3. Explicit unknowns/omissions section
4. No manual code reading before queries

## Primary Outputs (Retrieval Pack)

Return a compact payload:

```yaml
retrieval_pack:
  query: "FIND functions WHERE ..."
  results_summary: {functions: 12, findings: 3}
  evidence_refs: [{file: "...", line: 42}]
  omissions: {cut_set: [], excluded_labels: []}
  notes: ["taint_dataflow_unavailable"]
```

## Workflow

### Step 1: Translate intent to query

Decide between:
- **VQL** for property/ops/order checks
- **Pattern/lens** if user asks for a known vulnerability class

**Examples:**

Reentrancy candidate (order + guard):
```sql
FIND functions WHERE
  visibility IN [public, external] AND
  has_all_operations([TRANSFERS_VALUE_OUT, WRITES_USER_BALANCE]) AND
  sequence_order(before: TRANSFERS_VALUE_OUT, after: WRITES_USER_BALANCE) AND
  NOT has_reentrancy_guard
```

Label focus (pattern-scoped):
```sql
FIND functions WHERE
  has_label(access_control.reentrancy_guard) OR
  missing_label(access_control.reentrancy_guard)
```

### Step 2: Execute query

Use the CLI:
```bash
uv run alphaswarm query "FIND functions WHERE visibility IN [public, external] ..."
```

If explainability is required, include `explain` in the query:
```bash
uv run alphaswarm query "FIND functions WHERE ... explain"
```

### Step 3: Extract evidence + omissions

Collect:
- Evidence refs from node/edge evidence (file + line)
- Any missing/unknown signals (taint unavailable, guard not modeled)
- Omitted context if using sliced/subgraph views

### Step 4: Provide retrieval pack

Summarize results without narrative. Attach evidence and omission metadata.

## Guardrails

1. **Unknown vs false**
   - If taint dataflow is unavailable, mark it as unknown.
2. **Counter-signals**
   - Always include guard/CEI counter-signals in the pack.
3. **No prose claims**
   - Only describe what the graph shows, with evidence refs.
