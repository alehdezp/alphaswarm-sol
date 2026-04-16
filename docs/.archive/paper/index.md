# Research Paper

This section contains the formal research documentation for AlphaSwarm.sol, a behavioral vulnerability detection system for Solidity smart contracts.

## Contents

### [Architecture Paper](alphaswarm-architecture.md)

The main research paper documenting AlphaSwarm.sol's technical architecture, including:

- **Abstract** - Summary of the problem, solution, and contributions
- **Introduction** - Problem statement and core insight ("Names lie. Behavior does not.")
- **Related Work** - Comparison with CKG-LLM, SmartGuard, LLM-SmartAudit, and other approaches
- **Architecture** - BSKG, semantic operations, behavioral signatures, pattern system, multi-agent verification
- **Protocol Context Pack** - Economic context for logic bug detection
- **Conclusion** - Summary and future work

### [Appendix A - Semantic Operations](appendix-operations.md)

Complete reference for all 20 semantic operations with:

- Operation codes and descriptions
- Signature code vocabulary
- Composition examples
- Vocabulary policy

### [Appendix B - Pattern Examples](appendix-patterns.md)

Pattern examples for each tier:

- **Tier A** - Deterministic, graph-only patterns (Classic Reentrancy, Permissive Access Control)
- **Tier B** - Exploratory, LLM-verified patterns (Oracle Manipulation)
- **Tier C** - Label-dependent patterns (State Machine Violation)

## Status

**Version:** 0.5.0
**Status:** Technical Report (Pre-evaluation)
**Date:** January 2026

This paper documents the technical architecture as implemented. Performance evaluation and benchmarks are planned for Phase 7.
