# Improvement Digest — Phase 3.1c.1

**Generated:** 2026-02-28
**Updated:** 2026-03-01
**Passes completed:** 2
**Total items:** 59 (35 P1 + 24 P2)

## Active Items

None. All items have reached terminal status.

## Rejection Log

| ID | Title | Reason |
|----|-------|--------|
| P1-IMP-03 | Missing negative test -- vulndocs absent entirely | Missing error message is test coverage, not an execution blocker; conflates correctness with defensive programming |
| P1-IMP-11 | No Graph Listing or Cleanup Command Creates Operational Blindness | Human-readable manifest is a usability feature, not an execution blocker. meta.json sidecar provides basic discoverability. |
| P1-IMP-22 | Dependency on Plans 01-03 Is Sequential But Not Stated as a Hard Gate | Redundant with IMP-15; accepting both creates maintenance overhead without enforcement gain |
| P1-IMP-16 | Interrogation Protocol Is Completely Undefined | REFRAMED: Full protocol spec premature; replaced by ADV-201 (minimum viable scaffold: 3 questions + storage) |
| P1-IMP-26 | No Enforcement Mechanism -- Mandate Lives in Docs Claude Will Skip | REFRAMED: Machine-readable CONTEXT.md is still advisory; replaced by ADV-301 (enforcement via plan task done criteria) |
| P2-IMP-05 | Spec Assumes importlib.resources.files() Is Available — Python 3.8 Compatibility | Resolvable by reading pyproject.toml (< 5 min). Codebase uses `match` statements (Python 3.10+), making importlib.resources.files() a non-issue. |
| P2-IMP-18 | Pre-Validation Partial Failure Has No Recovery Path | Pre-validation already names three scoped components. Recovery table restates component-to-domain mapping already implicit. Documentation alignment, not falsifiability gap. |

## Convergence State

Pass 1: 35 items proposed across 3 adversarial lenses (Path & Hash Determinism, Agent Protocol Coherence, Governance Architecture). 30 items merged into CONTEXT.md. High structural signal — first pass identified foundational specification gaps (contract identity, dual-mode vulndocs resolution, interrogation protocol, phase-type taxonomy).

Pass 2: 24 items proposed across 3 adversarial lenses (Resolution & Packaging Determinism, Cross-Plan Interface Integrity, Testing Criteria Falsifiability). 22 items merged into CONTEXT.md. 100% structural signal (0% cosmetic). Key themes: cross-plan interface contracts (meta.json schema), CLI I/O channel protocol (stdout=data, stderr=diagnostics, exit codes), concurrent race conditions, and testing falsifiability (ground-truth patterns, disk-observable assertions).

Convergence trend: Pass 1 (35 items, 86% merge rate) → Pass 2 (24 items, 92% merge rate). Structural items remain at 100% in Pass 2, indicating the specification still has genuine gaps. However, items in Pass 2 are increasingly refinements of Pass 1 additions rather than wholly new gaps — suggesting approaching convergence.

## Provenance Manifest

| Pass | Item ID | Verdict | Lens | Key Insight |
|------|---------|---------|------|-------------|
| P1 | IMP-01 | enhanced -> implemented | Path & Hash | Audit ALL vulndocs consumers, not just default constant |
| P1 | IMP-02 | confirmed -> implemented | Path & Hash | importlib.resources for reads, __file__ for writes |
| P1 | IMP-04 | confirmed -> implemented | Path & Hash | Test code must use same resolution helpers |
| P1 | IMP-05 | researched -> implemented | Path & Hash | Jujutsu copies files (not symlinks); __file__ safe |
| P1 | IMP-06 | confirmed -> implemented | Path & Hash | realpath (not abspath) for stable hashing |
| P1 | IMP-07 | confirmed -> implemented | Path & Hash | Hash = sha256(realpath.encode('utf-8'))[:12] |
| P1 | IMP-08 | confirmed -> implemented | Path & Hash | Flat-file fallback with deprecation warning |
| P1 | IMP-09 | confirmed -> implemented | Path & Hash | GraphStore caller audit required |
| P1 | IMP-10 | confirmed -> implemented | Path & Hash | Compilation unit = atomic identity |
| P1 | IMP-12 | confirmed -> implemented | Protocol | mtime auto-discovery -> error-when-ambiguous |
| P1 | IMP-13 | confirmed -> implemented | Protocol | --graph uses stem-based lookup via meta.json |
| P1 | IMP-14 | enhanced -> implemented | Protocol | Error messages must embed recovery commands |
| P1 | IMP-15 | confirmed -> implemented | Protocol | Plan 03 hard-depends on Plans 01+02 |
| P1 | IMP-17 | enhanced -> implemented | Protocol | 4 binary checks for CLI usage confirmation |
| P1 | IMP-18 | confirmed -> implemented | Protocol | Framework pre-validation before agent spawning |
| P1 | IMP-19 | confirmed -> implemented | Protocol | Diagnostic output contract (6 fields) |
| P1 | IMP-20 | confirmed -> implemented | Protocol | jujutsu prereq check + git-worktree fallback |
| P1 | IMP-21 | enhanced -> implemented | Protocol | Smoke test: 2 contracts, 3 queries, 1 concurrent |
| P1 | IMP-23 | enhanced -> implemented | Governance | Testing gate template per phase type |
| P1 | IMP-24 | confirmed -> implemented | Governance | Near-term vs far-future phase tiering |
| P1 | IMP-25 | enhanced -> implemented | Governance | 3.1c.2 bootstrap exception (snapshot validation) |
| P1 | IMP-27 | confirmed -> implemented | Governance | Phase type taxonomy: CODE/EVAL/FRAMEWORK/SYNTHESIS |
| P1 | IMP-28 | confirmed -> implemented | Governance | Plan 05 split into 05a (design) + 05b (rollout) |
| P1 | IMP-29 | enhanced -> implemented | Governance | Framework contribution = mandatory artifact output |
| P1 | ADV-201 | confirmed -> implemented | Protocol | 3-question interrogation protocol + storage |
| P1 | ADV-301 | confirmed -> implemented | Governance | Done criteria > advisory CONTEXT sections |
| P1 | SYN-01 | confirmed -> implemented | Cross-cutting | Canonical contract identity spec |
| P1 | SYN-02 | confirmed -> implemented | Cross-cutting | Read-path migration inventory |
| P1 | CSC-01 | researched -> implemented | Cross-cutting | Compilation unit identity from Slither |
| P1 | CSC-02 | confirmed -> implemented | Cross-cutting | Dual-mode vulndocs (read/write paths) |
| P2 | IMP-01 | enhanced -> implemented | Resolution & Packaging | VulndocsPathConflict guard for dual-root detection |
| P2 | IMP-02 | confirmed -> implemented | Resolution & Packaging | Traversable API contract — no Path() cast |
| P2 | IMP-03 | confirmed -> implemented | Resolution & Packaging | Recursive `**` glob in package_data |
| P2 | IMP-04 | enhanced -> implemented | Resolution & Packaging | ALPHASWARM_VULNDOCS_DIR full contract (read+write override) |
| P2 | IMP-06 | researched -> implemented | Cross-Plan Interface | Dependency filtering via is_dependency + project root prefix |
| P2 | IMP-07 | confirmed -> implemented | Cross-Plan Interface | Broader grep for 'graphs' + read-path inventory |
| P2 | IMP-08 | confirmed -> implemented | Cross-Plan Interface | Atomic writes (tmp+rename) + skip-if-exists + --force |
| P2 | IMP-09 | confirmed -> implemented | Cross-Plan Interface | meta.json canonical schema (producer-consumer contract) |
| P2 | IMP-10 | confirmed -> implemented | Cross-Plan Interface | Stem disambiguation — error on collision with paths |
| P2 | IMP-11 | enhanced -> implemented | Cross-Plan Interface | Structured result header + exit codes 0/1/2 |
| P2 | IMP-12 | confirmed -> implemented | Cross-Plan Interface | Non-existent stem error with available graphs list |
| P2 | IMP-13 | enhanced -> implemented | Cross-Plan Interface | CLI I/O channel contract (stdout=data, stderr=diagnostics) |
| P2 | IMP-14 | enhanced -> implemented | Testing Falsifiability | Concurrent same-contract test — disk-observable |
| P2 | IMP-15 | confirmed -> implemented | Testing Falsifiability | Self-contained diagnostic schema (decoupled from ObservationRecord) |
| P2 | IMP-16 | confirmed -> implemented | Testing Falsifiability | Mixed-type phases protocol (CODE+FRAMEWORK) |
| P2 | IMP-17 | enhanced -> implemented | Testing Falsifiability | Mechanical Snapshot Protocol (jj change ID + restore) |
| P2 | IMP-19 | enhanced -> implemented | Testing Falsifiability | Ground-truth pattern verification for cross-contamination |
| P2 | SYN-01 | enhanced -> implemented | Cross-cutting | Canonical meta.json schema as Decision D-meta |
| P2 | CSC-01 | enhanced -> implemented | Cascade | --check-fresh staleness detection (exit 42) |
| P2 | CSC-02 | enhanced -> implemented | Cascade | Non-git directory fallback (project_root_type) |
| P2 | CSC-03 | enhanced -> implemented | Cascade | Query stdout parsing contract (header regex + JSON lines) |
| P2 | CSC-04 | enhanced -> implemented | Cascade | Snapshot Protocol Inheritance for downstream phases |

## Merged Summary

| Pass | Items | Merged | Rejected | Reframed | Themes |
|------|-------|--------|----------|----------|--------|
| P1 | 35 | 30 | 3 | 2 | Contract identity specification, dual-mode vulndocs, error-when-ambiguous query, interrogation protocol, phase-type taxonomy, enforcement via done criteria |
| P2 | 24 | 22 | 2 | 0 | Cross-plan meta.json contract, CLI I/O channel protocol, concurrent race conditions, testing falsifiability (ground-truth patterns), mixed-type phases, snapshot protocol |
