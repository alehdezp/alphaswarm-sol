# Cost/Token Efficiency Playbook

## Principles
- **Progressive disclosure**: load minimal context first, pull more only on demand.
- **Retrieval-first**: use tools (rg/glob/bskg query) instead of dumping files.
- **Model tiering**: cheap validator/guardrail -> expensive specialist.
- **Cache results**: graph queries, tool outputs, and evidence packs are reusable.
- **Compress tool descriptions**: keep tool text short to reduce baseline tokens.

## Techniques
1) **Context budget**
   - Set per-skill max token budgets (e.g., 6k)
   - Refuse expansion without justification

2) **Guardrails**
   - Validate input/output with cheap model
   - Block tool usage if scope exceeds budget

3) **Evidence packing**
   - Use TOON for uniform arrays
   - Prefer compact evidence bundles over verbose prose

4) **Parallelism controls**
   - Avoid spawning more subagents than necessary
   - Use sampling (2-3) instead of broad swarms

5) **Prompt linting**
   - Enforce structured output
   - Remove verbose narrative sections

## Metrics to Track
- Tokens per bead and per agent
- Precision/recall deltas vs baseline
- Cache hit rate for graph/tool outputs
- Cost per successful finding
