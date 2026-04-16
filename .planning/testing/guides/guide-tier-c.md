# Guide Tier C Pattern Testing

**Purpose:** Define when and how Tier C (label-dependent) patterns are tested with LLM assistance.

## When To Use

- Any workflow that enables Tier C patterns.
- Any time economic or protocol context is introduced.
- Any time you need lattice-based scenario design for complex patterns.

## Gating Conditions (Must All Be True)

- Protocol context pack exists.
- Economic context is generated or explicitly skipped with justification.
- Label coverage is above threshold for the target patterns.
- Graph build is complete and evidence refs are available.

## Required Sequence

1. Build the knowledge graph.
2. Generate protocol context pack (`alphaswarm context generate`).
3. Run economic context tasks if enabled.
4. Execute Tier C pattern queries.
5. Assign subagents only for Tier C patterns that meet gating conditions.

## Failure Handling

If gating fails:
- Mark Tier C as **unknown**.
- Do not run Tier C subagents.
- Record the missing gating condition in the report.

## Evidence Requirements

Tier C findings must include:
- Context pack reference ID
- Evidence refs with graph node IDs
- Explicit label dependencies
- Lattice-based scenario design reference (see `.planning/testing/guides/guide-pattern-lattice.md`)
- Economic behavior model reference when economic loss is central (see `.planning/testing/scenarios/economic/ECONOMIC-MODEL-LIBRARY.md`)
