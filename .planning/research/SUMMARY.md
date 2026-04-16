# Research Summary: Phase 5.9 LLM Graph Interface Improvements

**Domain:** Static analysis graph interface for multi-agent security verification
**Researched:** 2026-01-27
**Overall confidence:** MEDIUM-HIGH

## Executive Summary

Phase 5.9 focuses on hardening the LLM-facing graph interface for reliable multi-agent reasoning. The research covers four key domains: static analysis algorithms (dominance, taint), API contract design (semver, schemas), evidence standards (SARIF), and LLM interface patterns (uncertainty, structured output).

The current AlphaSwarm.sol implementation uses CFG-ordered operations without true dominance analysis. This means `sequence_order` patterns cannot distinguish "always before" from "sometimes before" orderings. The existing taint analysis is minimal (input-to-state only) and lacks external-return tracking, sanitizers, and explicit sinks. These gaps align precisely with Phase 5.9's scope.

Industry research confirms that dominance computation is well-understood (Lengauer-Tarjan or Cooper-Harvey-Kennedy iterative algorithms), Slither provides CFG infrastructure we can leverage, and SARIF 2.1.0 provides a mature evidence reference format. For LLM interfaces, recent 2025 research on uncertainty quantification shows that explicit unknown states and calibrated confidence improve downstream reasoning significantly.

**Key insight:** The transformation from "boolean property detection" to "path-qualified ordering with unknowns" is the central technical challenge. This requires dominance tree computation plus explicit representation of analysis limitations.

## Key Findings

**Stack:** Use existing Slither CFG + SlithIR; implement dominance via iterative algorithm; adopt SARIF-compatible evidence refs; use JSON Schema 2020-12 for interface contract validation.

**Architecture:** Single unified slicing pipeline replacing fragmented router/llm/kg slicers; omission ledger attached to all subgraph outputs; taxonomy registry as single source of truth for operation/edge mapping.

**Critical pitfall:** Silent omissions cause false safety conclusions. Any pruning, truncation, or analysis limitation MUST surface as explicit metadata or the LLM will assume completeness.

## Implications for Roadmap

Based on research, the suggested phase structure from 05.9-CONTEXT.md is well-aligned:

1. **05.9-01: Graph Interface Contract v2** - Foundation for everything else
   - Addresses: Schema validation, semver, compatibility shim
   - Avoids: Schema drift, breaking changes without migration

2. **05.9-02: Ops Taxonomy Registry** - Prerequisite for consistent patterns
   - Addresses: SARIF aliasing, migration map, deprecations
   - Avoids: Taxonomy drift between patterns/VQL/tools

3. **05.9-03: Omission Ledger + Coverage** - Critical for trust
   - Addresses: Silent omissions, coverage scoring
   - Avoids: False safety from incomplete data

4. **05.9-04: Deterministic Evidence IDs** - Reproducibility foundation
   - Addresses: Build hash binding, evidence resolution
   - Avoids: Non-reproducible findings across builds

5. **05.9-05: Dominance/Ordering + Guard Dominance** - Core analysis upgrade
   - Addresses: Path-qualified ordering, interprocedural summaries
   - Avoids: CEI false positives/negatives from naive ordering

6. **05.9-06: Taint Expansion** - Complete dataflow picture
   - Addresses: External returns, call-target control, sanitizers
   - Avoids: Missing taint sources causing missed vulnerabilities

7. **05.9-07: Unified Slicing Pipeline** - Consistency guarantee
   - Addresses: Fragmented slicers, debug mode
   - Avoids: Agent confusion from inconsistent contexts

8. **05.9-08: Pattern Outputs v2** - Evidence-first findings
   - Addresses: Clause matrix, unknowns gating
   - Avoids: Confidence inflation from missing evidence

9. **05.9-09: Skills + Orchestration** - Agent integration
   - Addresses: New skills, evidence compliance
   - Avoids: Manual enforcement of contracts

**Phase ordering rationale:**
- Contract + registry MUST come first (foundation)
- Omission ledger + evidence IDs before analysis upgrades (infrastructure)
- Dominance before taint (dominance informs taint path sensitivity)
- Unified slicing before pattern outputs (single data path)
- Skills last (consumes all prior work)

**Research flags for phases:**
- Phase 05.9-05 (Dominance): May need deeper research on modifier inlining strategies
- Phase 05.9-06 (Taint): External-return aliasing rules need careful design
- Phase 05.9-07 (Slicing): Debug mode schema may need iteration

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Slither CFG, JSON Schema, SARIF well-documented |
| Features | HIGH | 05.9-CONTEXT.md already comprehensive |
| Architecture | MEDIUM-HIGH | Unified pipeline design needs implementation validation |
| Pitfalls | HIGH | Silent omissions, schema drift well-known problems |
| Dominance algorithms | HIGH | Textbook algorithms, multiple implementations exist |
| Taint expansion | MEDIUM | External-return aliasing rules are design decisions |
| LLM uncertainty | MEDIUM | Active research area, patterns still evolving |

## Gaps to Address

- **Modifier inlining for interprocedural analysis:** Slither handles modifiers but their effect on dominance ordering needs design work
- **External-return aliasing:** When does a return value from an external call "taint" storage? Rules need explicit definition
- **Coverage score formula:** The exact weighting for `relevant_nodes` needs empirical tuning
- **Unknown budget thresholds:** How many unknowns are too many? Needs calibration per pattern type
- **Debug slice schema:** The exact fields for omission diagnosis need iteration

## Sources

### Static Analysis Theory
- [Dominator (graph theory) - Wikipedia](https://en.wikipedia.org/wiki/Dominator_(graph_theory))
- [A Simple, Fast Dominance Algorithm - Cooper et al.](https://www.cs.tufts.edu/comp/150FP/archive/keith-cooper/dom14.pdf)
- [Static Program Analysis - Moller and Schwartzbach](https://cs.au.dk/~amoeller/spa/spa.pdf)

### Smart Contract Analysis
- [Slither GitHub](https://github.com/crytic/slither)
- [TaintSentinel: Path-Level Vulnerability Detection](https://arxiv.org/html/2510.18192)
- [TaintGuard: Cross-contract taint tracking](https://dl.acm.org/doi/10.1016/j.sysarc.2023.102925)

### Evidence Standards
- [SARIF 2.1.0 Specification](https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html)
- [Complete Guide to SARIF - Sonar](https://www.sonarsource.com/resources/library/sarif/)

### LLM Interface Patterns
- [Structured Outputs - OpenAI](https://platform.openai.com/docs/guides/structured-outputs)
- [Uncertainty Quantification Survey 2025](https://arxiv.org/abs/2503.15850)
- [LLM Structured Output Guide - Agenta](https://agenta.ai/blog/the-guide-to-structured-outputs-and-function-calling-with-llms)

### Schema Versioning
- [Semantic Versioning 2.0.0](https://semver.org/)
- [SchemaVer for semantic versioning of schemas](https://snowplow.io/blog/introducing-schemaver-for-semantic-versioning-of-schemas)
