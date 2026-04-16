# Pattern Robustness Against Renaming and Dynamic Code Shapes

This document collects concrete ideas and implementation alternatives to make
pattern matching tolerant to renamed variables/functions and code that does not
advertise intent in identifiers. It is intentionally blunt about tradeoffs.

## Problem Summary

Some patterns rely on name-based heuristics (regex on labels or "admin-like"
names). This breaks when teams use custom naming conventions or intentionally
avoid canonical names (e.g., UUPS/proxy flows without "proxy" or "upgrade" in
names). We need matches driven by behavior, not by labels.

## Design Constraints (Reality Check)

- Determinism matters. The repo's core value is reproducible, explainable
  results. Anything non-deterministic undermines trust and testability.
- We can accept heuristics, but they must be inspectable and testable.
- Name-based clues are weak signals. They should be optional evidence, not
  primary predicates.

## Most Promising Direction: Enrich the Graph With Semantic Roles

Instead of LLM tagging, compute semantic roles from static analysis and store
them as properties or lists on nodes. Then patterns match on roles rather than
names.

Examples of deterministic roles:

- Function roles:
  - `is_upgrade_like`: writes implementation slot, calls upgrade logic, emits
    upgrade events, or delegates to implementation selector.
  - `is_admin_like`: accesses privileged state, changes roles, pauses, rescues,
    or changes fees.
  - `is_oracle_update_like`: writes price or feed values, calls external feeds,
    uses timestamp freshness checks.
  - `is_balance_update_like`: writes a mapping keyed by msg.sender or an
    address parameter, usually paired with transfer logic.
- Variable roles:
  - `is_balance_like`: mapping(address => uint) with transfers or balance checks.
  - `is_owner_like`: single address used in access gates or admin modifiers.
  - `is_impl_slot_like`: storage slot with EIP-1967 constant or fixed hash slot.

Implementation mechanics:

- In the builder, infer roles from syntax and dataflow, not names.
- Store roles in list properties like `roles` or `labels`.
- Use `contains_any` in patterns (already supported) to match roles.

Pros:
- Deterministic, testable, transparent.
- Works even when identifiers are random.

Cons:
- Requires up-front engineering to derive roles reliably.

## Pattern Engine Extensions (Big Gain, Medium Cost)

The current YAML patterns only check properties of the scoped node and do not
let you assert properties on linked nodes. This pushes authors toward name
regex instead of structural checks.

Add "edge constraints" and "node constraints" on edge targets:

- Allow `edges` to specify target property conditions (e.g., target node has
  `roles` contains `implementation`).
- Allow `paths` to match a target node with property constraints.
- Or compile YAML patterns into VQL2 queries, where matching subnodes is
  already expressive.

Pros:
- Lets patterns express real structure, not names.
- Reduces need for brittle regex.

Cons:
- Requires pattern engine changes and possibly new YAML schema.

## Canonicalization and Alpha-Renaming (Cheap Win)

Normalize identifiers into a canonical, tokenized form, but do not rely on it
as a primary signal. This is a safety net, not a core detection method.

Ideas:

- Tokenize identifiers (camelCase, snake_case) and normalize common verbs.
- Maintain a deterministic synonym table (e.g., "upgrade", "migrate",
  "rollover") used only to set a weak "name_hint" role.
- Provide a per-project override dictionary for domain terms.

Pros:
- Low effort, improves recall for name-based heuristics.

Cons:
- Still brittle, still easy to evade, can increase false positives.

## Dataflow-Driven Roles (High Value, More Work)

Push more of the semantics into derived properties:

- "Writes privileged state": state variables gated by access checks.
- "User-controlled value": taint from input to critical state or call.
- "CEI violations": state updated after external call in same function.
- "Initializer-like": function called in constructor or guard patterns.

These are already partially present; expand them with more precise dataflow
edges and role inference.

Pros:
- The most robust path to name-agnostic detection.

Cons:
- More analysis complexity, more tests needed.

## Strong Example: UUPS/Proxy Detection Without Names

Behavior-based signals for UUPS/proxy patterns:

- `delegatecall` in fallback or proxy function with data passthrough.
- EIP-1967 storage slot constants or keccak-derived slot usage.
- `proxiableUUID` selector presence.
- Writes to implementation address slot.
- `upgradeTo`-like function detected via writes to slot + access gate + optional
  `onlyProxy`/`notDelegated` guard behavior.

Store these as roles or properties and match patterns on them.

## Pattern Parameterization (Flexible, Deterministic)

Let patterns accept variables and role aliases rather than literals:

- YAML schema supports `params` with alias lists.
- CLI or config can override params (e.g., `upgrade_roles: [uups, proxy]`).
- Pattern uses `contains_any` on `roles` or `labels`.

This allows per-project renaming without changing core patterns.

## Two-Tier Matching (Strict + Heuristic)

Run two modes:

1) Strict deterministic: property and dataflow driven.
2) Heuristic fallback: name hints, weak signals, or partial evidence.

Only the strict tier should be considered "deterministic findings". The second
tier could be labeled "suspicion" and requires manual review.

## Semi-Automated Pattern Mining (Creative and Practical)

Given a set of vulnerable and safe fixtures:

- Build graphs and compute property deltas.
- Rank property combos that separate vulnerable from safe.
- Generate candidate patterns and ask for human review.

This keeps the pipeline deterministic while using automation to expand coverage.

## LLM Tagging: Use as an Assistant, Not as Ground Truth

Blunt truth: using an LLM to tag every node would undermine determinism,
reproducibility, and testability. It also introduces attack surface (prompt
injection via source code) and creates a moving target for regression tests.

If you want LLM help, use it in "offline suggestion" mode:

- Generate candidate roles or synonyms from a codebase.
- Convert them into deterministic rules or config entries.
- Require human review before adding them to the builder or pattern packs.

LLMs can accelerate idea generation, but they should not be the source of
truth for a security scanner.

## Concrete Implementation Alternatives (Ordered by ROI)

1) Add semantic roles in the builder (deterministic tags on nodes).
2) Extend pattern engine to allow property constraints on edge targets.
3) Add deterministic synonym table and tokenized name hints.
4) Add param support in YAML patterns for per-project alias mapping.
5) Add a "strict vs heuristic" result tier in reports.
6) Implement pattern mining from fixture diffs.
7) LLM-assisted suggestions for roles/synonyms (offline only).

## Suggested Roadmap (Pragmatic)

Phase 1 (2-4 weeks):
- Add role properties for upgrade/admin/balance/oracle primitives.
- Refactor a few patterns to use roles instead of label regex.

Phase 2 (4-8 weeks):
- Extend pattern YAML to support target-node constraints or compile to VQL2.
- Add deterministic name normalization as a weak signal.

Phase 3 (8-12 weeks):
- Add fixture-driven pattern mining.
- Optional LLM assistant for suggestion-only workflows.

## Final Take

The best solution is not a smarter name matcher. It is richer, deterministic
semantic signals in the graph and a more expressive pattern language. LLMs can
help suggest ideas, but they should not drive the detector directly unless you
are willing to trade away reproducibility and trust.
