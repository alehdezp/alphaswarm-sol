# BSKG NL Language Guide

**Note**: This guide documents VQL 1.0 (legacy). For the new, more powerful query language, see [VQL 2.0 Specification](./vql2-specification.md).

---

This guide documents the deterministic NL/VQL interface for the BSKG query engine, including features, rationale, and operational details.

## Why This Language Exists
- Deterministic and reproducible: no probabilistic parsing.
- Flexible across unknown codebases: schema‑guided hints adapt to project facts.
- Safe for LLM/agent use: bounded grammar, explicit operators, and explainable intent.

## VQL 2.0 Upgrade Path

VQL 2.0 is now available with significant enhancements:

- **10x more powerful**: SQL-like composability with WITH clauses, subqueries, set operations
- **LLM-optimized**: MCP-style guidance protocol with autocomplete and validation
- **Fault-tolerant**: Fuzzy matching, auto-correction, comprehensive error recovery
- **Graph-aware**: Cypher-inspired pattern matching for complex graph traversals
- **Dataflow-capable**: Advanced taint analysis with sanitizer requirements

**Migration**: All VQL 1.0 queries remain supported. To use VQL 2.0 features, see:
- [VQL 2.0 Specification](./vql2-specification.md) - Complete language reference
- [VQL 2.0 LLM Guide](./vql2-llm-guide.md) - How LLMs should construct queries
- [VQL 2.0 Grammar](./vql2-grammar.ebnf) - Formal EBNF grammar
- [VQL 2.0 README](../vql2-README.md) - Implementation guide

---

## VQL 1.0 (Legacy)

## Supported Query Inputs
- JSON intent payloads (direct schema).
- Safe NL phrases (light parsing).
- VQL (VKG Query Language): structured, SQL‑like syntax.

## VQL (Structured Queries)
- Format: `find|select|show <node type> where <conditions>`.
- Conditions support `and`, `or`, `not`, list values, and numeric comparisons.
- Example:
  - `find functions where visibility in [public, external] and writes_state and not has_access_gate limit 20`

## Operators
Supported ops: `eq`, `neq`, `in`, `not_in`, `contains_any`, `contains_all`, `gt`, `gte`, `lt`, `lte`, `regex`.

## Alias Normalization
Property aliases are normalized to canonical fields (e.g., `auth gate` -> `has_access_gate`).
Examples:
- `auth gate = false`
- `state write` -> `writes_state`

## Rule Map (Pattern Discovery)
Natural language phrases map to pattern IDs using:
- Pattern id/name/description
- Lens tags
- Synonyms
- Rule confidence scoring and candidate list

Example:
- `check unbounded loop` -> `dos-unbounded-loop`

## Confidence and Disambiguation
- Rule matches include `rule_confidence` and `rule_candidates`.
- Use `min-confidence <0.0-1.0>` to trigger disambiguation prompts when matches are weak.

## Schema‑Guided Hints
- Unknown properties/operators produce warnings and suggestions.
- Suggestions are derived from pattern definitions plus the builder‑emitted property set.

## CLI Support
- `--show-intent` outputs the parsed intent JSON for inspection.
- `schema` command exports a snapshot for autocomplete and validation.

Examples:
- `uv run alphaswarm query "check unbounded loop" --show-intent`
- `uv run alphaswarm schema --graph .true_vkg/graphs/graph.json`

## Error Recovery
VQL provides explicit error hints when:
- Missing WHERE clause
- Missing target type
- Missing conditions

Use the hints to repair the query without guessing.
