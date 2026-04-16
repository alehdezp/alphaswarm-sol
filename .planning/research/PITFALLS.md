# Domain Pitfalls

**Domain:** LLM-facing graph interface for security analysis
**Researched:** 2026-01-27

## Critical Pitfalls

Mistakes that cause rewrites or major issues.

### Pitfall 1: Silent Omissions Cause False Safety

**What goes wrong:** When a subgraph extraction prunes nodes or edges, the LLM receives a smaller graph and assumes it's complete. Missing nodes are interpreted as "no evidence of vulnerability" rather than "evidence not included." This leads to false safety conclusions.

**Why it happens:** Natural instinct is to minimize context for token efficiency. Pruning logic focuses on what to keep, not what was cut.

**Consequences:**
- Agent concludes "no reentrancy guard needed" when guard exists but was pruned
- Agent concludes "no external call before state write" when call was in pruned path
- Vulnerability missed because evidence was silently omitted

**Prevention:**
- Mandatory omission ledger on ALL subgraph outputs
- Coverage score as a first-class field (not optional)
- Cut set recording: which edges blocked traversal
- Training agents to check coverage before concluding safety

**Detection:**
- Coverage score < 0.8 should trigger warning
- Agent asks "is this all the relevant code?" with no answer = problem
- Regression tests with known omissions

### Pitfall 2: Boolean Guards Hide Bypass Paths

**What goes wrong:** `has_reentrancy_guard: true` sounds safe, but the guard may not dominate the external call. An attacker can reach the vulnerable code path without passing through the guard.

**Why it happens:** Guard detection is easy (name matching, modifier presence). Dominance analysis is hard. The easy solution ships first.

**Consequences:**
- "Guarded" functions are actually vulnerable
- Agents trust boolean guard property without verification
- False negatives on guard bypass vulnerabilities

**Prevention:**
- Replace boolean guards with dominance-qualified states:
  - `dominating`: guard dominates all paths to sink
  - `bypassable`: guard exists but at least one path bypasses it
  - `unknown`: dominance cannot be computed (e.g., truncated CFG)
- Require evidence refs for guard locations
- Pattern matching on `guard_dominates_sink`, not `has_guard`

**Detection:**
- Test cases with guards that don't dominate
- Fuzz testing with path-selective execution
- Cross-check with manual audit findings

### Pitfall 3: CFG Order != Dominance Order

**What goes wrong:** Current `compute_ordering_pairs()` uses CFG traversal order. This produces "(A, B) in pairs" meaning "A appears before B in CFG." But CFG order doesn't mean "A always executes before B" - it means "A is at a lower CFG node number."

**Why it happens:** CFG traversal order is easy to compute. True dominance requires dominator tree construction.

**Consequences:**
- CEI patterns wrongly classified: "state write before external call" in CFG order may not be "state write dominates external call"
- Conditional branches create paths where the "earlier" operation is actually never executed
- Reentrancy detection produces false positives/negatives

**Prevention:**
- Compute dominator tree from CFG
- Path-qualified ordering: always_before, sometimes_before, never_before, unknown
- Test suite with conditional paths that break CFG order assumptions

**Detection:**
- Contracts with `if (condition) { write_state(); } external_call();`
- The write_state is CFG-ordered before external_call but doesn't dominate it
- Regression tests for this exact pattern

### Pitfall 4: Taxonomy Drift Across Tools

**What goes wrong:** Patterns use `TRANSFERS_VALUE_OUT`, VQL uses `transfers_value`, SARIF adapter uses `VALUE_TRANSFER`. Same concept, different names. Queries miss matches.

**Why it happens:** Different developers, different times, different contexts. No central registry enforces naming.

**Consequences:**
- Patterns don't match because operation name differs
- VQL queries return empty results for valid concepts
- Tool integration breaks due to name mismatches

**Prevention:**
- Central taxonomy registry (single source of truth)
- All lookups go through registry
- Migration map: old_name -> new_name with deprecation warnings
- CI validation: all patterns/VQL use registered names

**Detection:**
- Unit tests for all known aliases
- Pattern validation at load time
- VQL validation at parse time

## Moderate Pitfalls

Mistakes that cause delays or technical debt.

### Pitfall 1: Interprocedural Analysis is Harder Than Expected

**What goes wrong:** Modifier effects on dominance seem simple but aren't. Inherited modifiers, multi-modifier chains, and internal call summaries create combinatorial complexity.

**Prevention:**
- Start with single-modifier, single-function analysis
- Add interprocedural summaries incrementally
- Use explicit "unknown" when analysis can't resolve cross-boundary effects
- Design for extension: summary interface that can be improved later

### Pitfall 2: External-Return Taint Aliasing Ambiguity

**What goes wrong:** When `uint price = oracle.getPrice()`, does `price` taint storage writes? What if `price` is stored, then read later, then used in a calculation? Aliasing rules become complex.

**Prevention:**
- Start with direct taint: return value taints immediate uses
- Add storage aliasing rules explicitly (not implicitly)
- Document taint propagation rules in TAINT_RULES.md
- Use availability flag when aliasing is ambiguous

### Pitfall 3: Coverage Score Without Formal Definition

**What goes wrong:** "Coverage score" sounds good but what does 0.7 mean? Different interpretations lead to inconsistent behavior.

**Prevention:**
- Formal definition: `coverage = captured_weight / relevant_weight`
- Explicit `relevant_weight` calculation:
  - PPR-selected nodes
  - Query-matched nodes
  - Dependency-closed nodes
- Testable and reproducible formula

### Pitfall 4: Schema Version Conflicts

**What goes wrong:** Interface v2 deployed, but old clients send v1 requests. Breaking changes cause errors.

**Prevention:**
- Semver on interface version
- Compatibility shim for v1 -> v2 migration
- Deprecation warnings before removal
- Version negotiation in schema header

### Pitfall 5: Debug Mode Leaks to Production

**What goes wrong:** Debug slice mode bypasses pruning for diagnosis. Accidentally enabled in production = huge context, slow responses, potential data exposure.

**Prevention:**
- Debug mode requires explicit opt-in flag
- Debug outputs include `slice_mode: debug` marker
- CI checks that debug mode is not default
- Rate limiting on debug mode in production

## Minor Pitfalls

Mistakes that cause annoyance but are fixable.

### Pitfall 1: Evidence IDs Change Between Builds

**What goes wrong:** Evidence ref `EVD-001` in build A points to different code than `EVD-001` in build B. Agents reference stale evidence.

**Prevention:**
- Build hash included in evidence ID
- Full ID format: `{build_hash}:{node_id}:{snippet_id}`
- Evidence resolution validates build hash

### Pitfall 2: Omission Ledger is Too Verbose

**What goes wrong:** `omitted_nodes` list can be thousands of entries. Token waste.

**Prevention:**
- `omitted_nodes` is optional
- Default: only `coverage_score`, `cut_set`, `excluded_edges`
- Verbose mode for debugging only

### Pitfall 3: Clause Matrix vs Matched/Failed/Unknown Lists Mismatch

**What goes wrong:** `clause_matrix` includes status per clause, but `matched_clauses` list doesn't match matrix entries due to serialization bug.

**Prevention:**
- Single source: clause_matrix is authoritative
- `matched_clauses`, `failed_clauses`, `unknown_clauses` derived from matrix
- Validation: lists must equal matrix extraction

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| 05.9-01 Contract v2 | Schema too strict initially | Start permissive, tighten with data |
| 05.9-02 Taxonomy | Missing legacy aliases | Comprehensive alias audit before migration |
| 05.9-03 Omission | Coverage formula ambiguity | Formal definition with test cases |
| 05.9-04 Evidence | Hash collision (unlikely but possible) | Use 12-char xxhash, monitor for collisions |
| 05.9-05 Dominance | Modifier inlining complexity | Start single-modifier, extend incrementally |
| 05.9-06 Taint | Aliasing rule explosion | Start direct taint, add aliasing explicitly |
| 05.9-07 Slicing | Backward compatibility | Maintain old API with deprecation warnings |
| 05.9-08 Patterns | Unknowns budget too aggressive | Calibrate per pattern category |
| 05.9-09 Skills | Skill prompt context overflow | Budget enforcement in skill wrapper |

## Sources

- [05.9-CONTEXT.md](./.planning/phases/05.9-llm-graph-interface-improvements/05.9-CONTEXT.md)
- [Knowledge Graph Incompleteness in RAG](https://arxiv.org/html/2508.08344v1)
- [How to Mitigate Information Loss in Knowledge Graphs](https://www.ijcai.org/proceedings/2025/0901.pdf)
- [Static Program Analysis - Moller and Schwartzbach](https://cs.au.dk/~amoeller/spa/spa.pdf)
- [Uncertainty Quantification Survey 2025](https://arxiv.org/abs/2503.15850)
