# Phase 19 Philosophy: Semantic Labeling for Logic Risk

**Goal:** Convert implicit business logic into minimal, queryable labels that
unlock complex vulnerability detection without bloating LLM context.

---

## Core Principles

1. **Behavior Over Syntax**
   Labels describe intent and behavior (what the code DOES), not just
   syntactic patterns. This allows detection of logic flaws static analysis misses.

2. **Evidence-First Labeling**
   No label exists without anchored evidence (code lines or specific
   bead evidence). Labels must be auditable and reversible.

3. **Minimal Context, Maximum Signal**
   All labels are short, structured, and category-gated. Avoid prose in
   the knowledge graph. Limit label count per node.

4. **Scoped Learning**
   Labels are project-scoped by default. Global knowledge requires
   repeated confirmation across projects and a curated promotion path.

5. **Strict Validation**
   Labels must pass deterministic validation (guard patterns, property
   signals, evidence line checks). LLM output alone is not sufficient.

6. **Token Budget Discipline**
   The labeling pipeline must respect hard token budgets for both
   labeling and detection contexts.

7. **Retrospective Improvement**
   Every stage includes retrospective tests that can trigger new tasks
   or revisions of earlier steps.

---

## Outcome Expectations

- Labels improve detection of authorization drift, invariant violations,
  state machine mistakes, and misconfigured permissions.
- LLM context usage remains under strict caps with observable precision gains.
- The labeling system is explainable, reversible, and measurable.
