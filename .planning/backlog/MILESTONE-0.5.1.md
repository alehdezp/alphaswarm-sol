# AlphaSwarm.sol Milestone 0.5.1 - Consolidated Plan

**Created:** 2026-01-30
**Status:** PENDING (blocked by v0.5.0 GA release)
**Source Files:**
- `.planning/v0.5.1-ROADMAP.md`
- `.planning/backlog/v0.5.1.yaml`
- `.planning/ROADMAP.md` (Phase 7.3/7.4 context)
- `.planning/STATE.md`
- `.planning/CRITICAL-GA-BLOCK.md`

---

## Executive Summary

Milestone 0.5.1 captures all deferred work from the v0.5.0 GA release. It includes:
- **18 specific improvements** from Phase 7.3 GA Validation
- **9 major features** deferred from GA scope
- **4 research-driven proposals** for post-GA horizon

**Entry Criteria:** v0.5.0 GA released successfully after Phase 7.3 and 7.4 complete.

---

## 1. GA Validation Backlog (18 Items)

These improvements were identified during Phase 7.3 GA Validation and deferred to maintain release scope.

### 1.1 Critical Priority (2 Items)

| ID | Category | Description | Affected File | Complexity |
|----|----------|-------------|---------------|------------|
| IMPROV-001 | Bug | Fix WRITES_SHARED_STATE taxonomy error in reentrancy-002-gmx-cross-function.yaml. Pattern uses undefined semantic operation causing taxonomy validation failure. | `vulndocs/reentrancy/classic/patterns/reentrancy-002-gmx-cross-function.yaml` | Trivial |
| IMPROV-002 | Bug | Counterfactual factory generates pattern IDs (access-control-hidden, chain-specific-bypass) that don't exist in VulnDocs. Inflates FN count. | `scripts/counterfactual_factory.py` | Medium |

### 1.2 High Priority (6 Items)

| ID | Category | Description | Affected File | Complexity |
|----|----------|-------------|---------------|------------|
| IMPROV-003 | Performance | Weak-access-control pattern shows SSS of 0.00 under obfuscation. Pattern relies on identifier naming instead of semantic operations. | `vulndocs/access-control/weak/patterns/*.yaml` | Medium |
| IMPROV-004 | Performance | Approval-race pattern may rely on naming heuristics. Flagged for semantic operation enhancement. | `vulndocs/token/approval/patterns/*.yaml` | Medium |
| IMPROV-005 | Architecture | Add PCP (Pattern Context Pack) format support to ECC audit. Currently PCP files appear as "broken" due to different schema. | `scripts/run_pattern_tier_validation.py` | Medium |
| IMPROV-006 | Feature | Configure shadow mode with production-calibrated labelers. Current test data has intentional disagreement for testing. | `.vrs/testing/tier_c_stability.yaml` | Complex |
| IMPROV-007 | Performance | Improve reentrancy-classic pattern edge case detection. Shadow audit showed 33% recall (2 misses from mock simulation). | `vulndocs/reentrancy/classic/patterns/*.yaml` | Medium |
| IMPROV-008 | Performance | Strengthen weak-access-control Tier C patterns. Shadow audit showed 0% recall (label-dependent pattern limitations). | `vulndocs/access-control/weak/patterns/tier-c/*.yaml` | Complex |

### 1.3 Medium Priority (6 Items)

| ID | Category | Description | Affected File | Complexity |
|----|----------|-------------|---------------|------------|
| IMPROV-009 | Feature | Update 49 shipped skills with schema v2 frontmatter. Skills work but lack: role, model_tier, tools, evidence_requirements, output_contract, failure_modes, version fields. | `.claude/skills/*.md` | Simple |
| IMPROV-010 | Bug | Fix precision dashboard pattern ID mismatches. Dashboard uses legacy IDs that don't match VulnDocs patterns. | `scripts/generate_precision_dashboard.py` | Medium |
| IMPROV-011 | Feature | Define 15 new semantic operations for novel 2025-2026 attack patterns: precision-loss, eip7702-delegation, zk-proof-bypass, cached-storage, etc. | `src/alphaswarm_sol/kg/builder/operations.py` | Complex |
| IMPROV-012 | Feature | Install and validate Aderyn tool integration in live mode. Currently tested only in mock mode. | `scripts/run_tool_validation.py` | Simple |
| IMPROV-013 | Feature | Complete practice repo ground truth stubs with actual contract paths. 7 practice repositories have stub entries pending ingestion. | `.vrs/corpus/ground-truth/practice-repos.yaml` | Medium |
| IMPROV-014 | Feature | Populate mutations corpus segment via counterfactual factory. Currently empty, adversarial segment has contracts but mutations does not. | `.vrs/corpus/contracts/mutations/` | Medium |

### 1.4 Low Priority (4 Items)

| ID | Category | Description | Affected File | Complexity |
|----|----------|-------------|---------------|------------|
| IMPROV-015 | Performance | Add query benchmark success validation. Query benchmarks show failures due to missing pre-built graph files. | `scripts/run_performance_baseline.py` | Simple |
| IMPROV-016 | Feature | Pin commit SHAs for all corpus sources after ingestion. Currently using HEAD references which may drift. | `.vrs/corpus/metadata/sources.yaml` | Trivial |
| IMPROV-017 | Feature | Add more protocols to corpus database for context A/B testing. Simulated mode found only 2 protocols, switched to mock for 20-protocol sample. | `.vrs/corpus/metadata/` | Medium |
| IMPROV-018 | Feature | Add CI integration for claude-code-agent-teams-based workflow testing. Infrastructure works locally, CI integration deferred. | `.github/workflows/` | Complex |

### Backlog Summary

| Metric | Count |
|--------|-------|
| **Total Items** | 18 |
| **By Priority** | Critical: 2, High: 6, Medium: 6, Low: 4 |
| **By Category** | Bug: 3, Performance: 4, Feature: 9, Architecture: 1 |
| **By Complexity** | Trivial: 2, Simple: 3, Medium: 9, Complex: 4 |

---

## 2. Deferred Features (9 Items)

Major features deferred from v0.5.0 GA scope due to complexity, stability risk, or dependency issues.

### 2.1 Multi-Runtime Skill Shipping

| Attribute | Details |
|-----------|---------|
| **Reason** | Packaging/validation complexity across runtimes or failed smoke tests |
| **Required Artifacts** | Canonical skill spec, export pipeline, runtime installers, validation harness |
| **Entry Criteria** | Phase 5.9 LGRAPH-11 unable to pass all runtime checks |
| **Exit Criteria** | All three runtimes (OpenCode/Codex/Claude) ship the same skill bundle with passing invocation tests |

### 2.2 Model Comparison / Ranking Tests

| Attribute | Details |
|-----------|---------|
| **Reason** | Non-uniform model availability and inconsistent baselines across runtimes |
| **Scope** | Any tests that compare model quality or update rankings based on comparative runs |
| **Entry Criteria** | Phase 7.3 scope note triggered |
| **Exit Criteria** | Stable, comparable test harness + aligned model availability |

### 2.3 Multi-Agent Evolutionary Fuzzing (MARF)

| Attribute | Details |
|-----------|---------|
| **Reason** | Requires complex reinforcement learning loops and AST-transformation stability beyond the 0.5.0 GA scope |
| **Trigger** | Deferred from Phase 7.2 context update (v4) |
| **Exit Criteria** | Autonomous mutation agent successfully evolves "Safe" code to "Vulnerable" while maintaining functional parity |

### 2.4 Natural Language Specification Matching (Tier D)

| Attribute | Details |
|-----------|---------|
| **Reason** | LLM reliability for parsing technical PDF whitepapers into formal graph invariants is not yet high enough for production |
| **Trigger** | Deferred from Phase 7.2 context update (v4) |
| **Exit Criteria** | Tier D matcher achieves >= 80% precision on "Intent vs. Code" mismatch detection |

### 2.5 Exploit-as-a-Test (PoC Builder)

| Attribute | Details |
|-----------|---------|
| **Reason** | Requires Foundry harness, deterministic replay, and sandboxed chain state; too heavy for GA scope |
| **Trigger** | Deferred from Phase 7.3 (Plan 07.3-08-ADVERSARIAL) |
| **Exit Criteria** | PoC builder reliably reproduces a subset of findings with a stable success rate and no false attribution |

### 2.6 Cross-Contract Dependency Graph (CCDG)

| Attribute | Details |
|-----------|---------|
| **Reason** | Extending BSKG to track interactions across multiple .sol files and complex protocols (Phase 7.3 spillover) |
| **Trigger** | Deferred from Phase 7.3 Improvement Plan |
| **Exit Criteria** | CCDG correctly maps state-flow across multiple inherited and external contract calls |

### 2.7 Ghost Environment / Cross-Protocol Simulation

| Attribute | Details |
|-----------|---------|
| **Reason** | Needs scenario orchestration and composability harness across protocols; not safe to ship without dedicated infra |
| **Trigger** | Deferred from Phase 7.3 optional enhancements |
| **Exit Criteria** | Ghost scenarios run deterministically and yield stable metrics without corpus drift |

### 2.8 Red-Blue Tournament Orchestration

| Attribute | Details |
|-----------|---------|
| **Reason** | Requires adversarial loop control + scoring logic; risk of runaway cost in GA scope |
| **Trigger** | Deferred from Phase 7.3 optional enhancements |
| **Exit Criteria** | Tournament produces actionable gap reports with bounded runtime and cost |

### 2.9 ZK Witness Path Generation

| Attribute | Details |
|-----------|---------|
| **Reason** | Formal witness construction requires new proof tooling and is not ready for GA |
| **Trigger** | Deferred from Phase 7.2 improvement plan |
| **Exit Criteria** | Witness path generation is deterministic and passes reachability checks on a representative subset |

---

## 3. Research-Driven Proposals (4 Items)

Longer-horizon research and innovation proposals for post-v0.5.0 releases.

### 3.1 ERC-8004 On-Chain Identity Integration

| Attribute | Details |
|-----------|---------|
| **Reason** | As of January 2026, AI agents are moving to mainnet identity registries. AlphaSwarm agents should 'sign' their audits on-chain to prevent spoofing and build portable reputation. |
| **Trigger** | Official Mainnet Launch of ERC-8004 registries (scheduled Jan 29, 2026) |
| **Exit Criteria** | Audit reports include an EIP-712 signature linked to an ERC-8004 Identity NFT |

### 3.2 FCV-Attack (Functionally Correct yet Vulnerable) Shield

| Attribute | Details |
|-----------|---------|
| **Reason** | Latest research shows LLMs generate patches that pass 100% of unit tests but introduce security debt. We need a specific 'Negative Test' generator to detect "correct but unsafe" code. |
| **Trigger** | Findings from the 'Adversarial Evasion' paper analysis in Phase 7.4 |
| **Exit Criteria** | A 'Red Team' agent successfully flags a patch that passes all `foundry` tests but violates a behavioral signature |

### 3.3 Execution Trace 'Re-Enactment' (TraceLLM Mode)

| Attribute | Details |
|-----------|---------|
| **Reason** | Static analysis is reaching a semantic ceiling. Future versions must 're-enact' behavioral signatures in a 'Ghost Environment' (forked state) to verify state-deltas. |
| **Trigger** | Competitive analysis of TraceLLM/ETrace papers (Jan 2025/2026) |
| **Exit Criteria** | Auditor agents provide a 'Behavioral Diff' (Before/After state change) for every finding using live trace data |

### 3.4 Zero-Knowledge Proof (ZKP) of Vulnerability Reachability

| Attribute | Details |
|-----------|---------|
| **Reason** | Proving a vulnerability exists without revealing the exploit code is critical for private bug bounties and institutional disclosure. |
| **Trigger** | Integration of the 'Verified Verifiers' working group standards |
| **Exit Criteria** | Generation of a Circom/Halo2 witness that proves a state-lock is reachable via a behavioral signature path |

---

## 4. Current GA Status (v0.5.0)

Milestone 0.5.1 is blocked pending v0.5.0 GA release. Current v0.5.0 status:

### 4.1 Phase Progress

| Phase | Name | Status |
|-------|------|--------|
| 1-6.1 | Core Infrastructure | **COMPLETE** (127/127 plans) |
| 7.1-7.1.5 | Testing & Infrastructure | **COMPLETE** (50/50 plans) |
| 7.2 | Corpus Research & VulnDocs | **COMPLETE** (13/13 plans) |
| **7.3** | **GA Validation & Release Gate** | **PENDING** (0/8 v4 plans) |
| **7.4** | **Release Preparation Final** | **PENDING** (0/8 plans) |

**Overall Progress:** ~97% (~220/~228 plans complete)

### 4.2 Phase 7.3 v4 Redesign

Phase 7.3 was completely redesigned on 2026-01-30:
- **v3 plans INVALIDATED:** Used mock/simulated execution with hardcoded metrics
- **v4 plans CREATED:** 8 plans using real claude-code-agent-teams-based Claude Code CLI testing
- **Cost model:** $0 (subscription-based, no API charges)
- **Ground truth:** External (SmartBugs, CGT, Code4rena), not hardcoded Python

### 4.3 v4 Plan Structure

| Wave | Plans | Description |
|------|-------|-------------|
| 1 | 01-v4, 02-v4 | Ground truth import + smoke test |
| 2 | 03-v4, 04-v4 | Agent + integration tests |
| 3 | 05-v4, 06-v4 | E2E + A/B comparison |
| 4 | 07-v4, 08-v4 | Blind validation + GA report |

### 4.4 Phase 7.4 Scope

Release preparation focusing on:
- Research paper documentation (behavioral signatures, multi-agent verification)
- Demo pack (VulnerableVault, SafeVault, AdversarialNaming)
- Release bundle (wheel, checksums, QUICKSTART)
- Documentation validation
- Release ceremony

---

## 5. Proposed 0.5.1 Phase Structure

Recommended phases for milestone 0.5.1 execution:

### Phase 8.1: Critical Bug Fixes
- IMPROV-001: Fix taxonomy error
- IMPROV-002: Fix counterfactual factory pattern IDs
- **Estimated:** 8h

### Phase 8.2: Pattern Semantic Hardening
- IMPROV-003: Weak-access-control semantic operations
- IMPROV-004: Approval-race semantic operations
- IMPROV-007: Reentrancy-classic edge cases
- IMPROV-008: Tier C pattern strengthening
- **Estimated:** 32h

### Phase 8.3: Schema & Infrastructure Updates
- IMPROV-005: PCP format support
- IMPROV-009: Skill schema v2 frontmatter
- IMPROV-010: Dashboard pattern ID alignment
- IMPROV-012: Aderyn live mode validation
- **Estimated:** 24h

### Phase 8.4: Corpus & Ground Truth Expansion
- IMPROV-006: Shadow mode calibration
- IMPROV-013: Practice repo ground truth
- IMPROV-014: Mutations corpus population
- IMPROV-016: Commit SHA pinning
- IMPROV-017: Protocol corpus expansion
- **Estimated:** 40h

### Phase 8.5: New Semantic Operations
- IMPROV-011: 15 new operations for 2025-2026 attack patterns
- **Estimated:** 48h

### Phase 8.6: CI/Infrastructure
- IMPROV-015: Query benchmark validation
- IMPROV-018: claude-code-agent-teams-based CI integration
- **Estimated:** 24h

### Phase 8.7: Major Feature Selection
Select 2-3 deferred features for v0.5.1 scope:
- Candidates: CCDG, PoC Builder, Model Comparison
- **Estimated:** TBD based on selection

---

## 6. Success Criteria for 0.5.1

### Must Have
- [ ] All 2 critical bugs fixed (IMPROV-001, IMPROV-002)
- [ ] Pattern SSS improved to >= 0.85 (from 0.73)
- [ ] Schema v2 frontmatter on all skills
- [ ] Ground truth provenance for all corpus sources

### Should Have
- [ ] At least 1 major deferred feature complete
- [ ] 15 new semantic operations documented
- [ ] CI integration for claude-code-agent-teams-based testing
- [ ] Aderyn live mode validated

### Could Have
- [ ] Research proposals scoped for v0.6.0
- [ ] Tournament orchestration prototype
- [ ] ZK witness path generation POC

---

## 7. Timeline Dependencies

```
v0.5.0 GA Release
       │
       │ Phase 7.3 v4 complete (BLOCKING)
       │ Phase 7.4 complete (BLOCKING)
       ▼
v0.5.1 Development Start
       │
       │ Phases 8.1-8.6 (improvements)
       │ Phase 8.7 (major features)
       ▼
v0.5.1 Release
```

**Critical Path:** Phase 7.3 v4 execution → Phase 7.4 → v0.5.0 GA → v0.5.1 start

---

## 8. References

| Document | Purpose |
|----------|---------|
| `.planning/v0.5.1-ROADMAP.md` | Deferred features and research proposals |
| `.planning/backlog/v0.5.1.yaml` | Detailed improvement backlog |
| `.planning/ROADMAP.md` | Phase structure and progress |
| `.planning/STATE.md` | Current execution state |
| `.planning/VALIDATION-RULES.md` | Testing requirements |
| `.planning/CRITICAL-GA-BLOCK.md` | v4 redesign status |
| `.planning/phases/07.4-release-preparation-final/07.4-CONTEXT.md` | Release preparation context |

---

**Last Updated:** 2026-01-30
**Consolidated By:** Planning system merge
