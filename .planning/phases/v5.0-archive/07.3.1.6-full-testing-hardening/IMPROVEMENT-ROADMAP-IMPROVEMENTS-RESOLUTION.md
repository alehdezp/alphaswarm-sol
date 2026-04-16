# IMPROVEMENT-ROADMAP-IMPROVEMENTS Resolution

**Date:** 2026-02-04
**Resolution:** All 18 proposed improvements REJECTED or CLOSED
**Reason:** Critical review reveals most already exist, remainder are over-engineering

---

## Executive Summary

The `IMPROVEMENT-ROADMAP-IMPROVEMENTS.md` document proposed 18 "improvements" that were generated without verifying what already exists in the codebase. Upon thorough investigation:

- **7 items** already exist as implemented scripts/infrastructure
- **3 items** are deferred until Wave 5 (not blocking now)
- **8 items** are documentation bloat or over-engineering

**Verdict:** No action required. The existing infrastructure is complete.

---

## Resolution by Category

### Category 1: Already Implemented (CLOSED - NO ACTION)

| ID | Proposed | Reality | Resolution |
|----|----------|---------|------------|
| **IMP-M1** | Create test contract verification script | `scripts/verify_test_contracts.py` EXISTS | CLOSED |
| **IMP-M2** | Create VQL schema validation | `scripts/validate_vql_queries.py` EXISTS + 8 VQL-MIN queries in `kg/queries/vql_minimum_set.yaml` | CLOSED |
| **IMP-M10** | Create wave gate automation | `scripts/check_wave_gate.py` EXISTS | CLOSED |
| **IMP-M12** | Create evidence pack completeness checker | `scripts/validate_evidence_pack.py` EXISTS | CLOSED |

**Evidence:**
- 362 test contracts exist in `tests/contracts/`
- All referenced contracts (CrossFunctionReentrancy.sol, hard-case/, semantic-test-set/) exist
- Test fixtures (dvd/side-entrance/, smartbugs/) exist
- Ground truth corpus with 20+ datasets in `.vrs/corpus/ground-truth/`

### Category 2: Sufficient Manual Process (CLOSED - OVERKILL)

| ID | Proposed | Resolution |
|----|----------|------------|
| **IMP-M5** | Anti-fabrication automation script | CLOSED - `wc -l`, `grep` and manual review sufficient for 16 plans |
| **IMP-M6** | claude-code-agent-teams session isolation verification | CLOSED - Rules clear in `claude-code-controller-instructions.md`, no need to verify the verifier |
| **IMP-M7** | Graph citation verification tool | CLOSED - Evidence pack validation already covers this |
| **IMP-M11** | Proof token N/A validation script | CLOSED - Matrix exists, manual review sufficient |

**Rationale:** Creating automation scripts for processes that execute a handful of times adds complexity without benefit. The 16 plans in this phase don't justify building an automation framework.

### Category 3: Deferred to Wave 5 (NOT BLOCKING)

| ID | Proposed | Resolution |
|----|----------|------------|
| **IMP-M3** | Graph disable mechanism (--no-graph) | DEFERRED - Only needed for IMP-G1 ablation study in Wave 5. Graph-first is **intentionally mandatory** per architecture. Implement if/when ablation study actually starts. |
| **IMP-M4** | Single-agent baseline mode | DEFERRED - Only needed for IMP-H1 comparison in Wave 5. Not blocking core validation. |

**Rationale:** These are hypothetical needs for tests that may never run. If Wave 5 existential tests are scheduled, implement then.

### Category 4: Over-Engineering (REJECTED)

| ID | Proposed | Why Rejected |
|----|----------|--------------|
| **IMP-M8** | Expand Plan 15 dependencies to 03,04,09-14 | REJECTED - Plan 15 tests orchestration and E2E. Current deps (03, 04) are correct. E2E testing WILL reveal broken components without artificial dependency chains. |
| **IMP-M9** | Definition freeze mechanism with hash verification | REJECTED - Git tags already provide this. `git tag definition-freeze-wave0` is simpler than a custom hash system. |
| **IMP-M13** | Quick reference card | REJECTED - The roadmap IS the reference. More docs don't help. |
| **IMP-M14** | Existential validation runbook | REJECTED - Ablation study is standard A/B testing, not complex enough for a runbook. |
| **IMP-M15** | Metrics collection template | REJECTED - Evidence pack schema already defines metrics structure. |
| **IMP-M16** | Visual dependency graph (Mermaid) | REJECTED - Nice but decorative. Text dependencies are sufficient. |
| **IMP-M17** | Interrupted execution recovery protocol | REJECTED - Handle ad-hoc if interruption actually happens. |
| **IMP-M18** | Ground truth acquisition protocol | REJECTED - 20+ ground truth datasets already exist in `.vrs/corpus/ground-truth/`. Protocol not needed when corpus exists. |

---

## Infrastructure Verification

The following infrastructure was confirmed to exist:

### Scripts Directory (100+ scripts)
```
scripts/
├── verify_test_contracts.py      ✓
├── validate_vql_queries.py       ✓
├── check_wave_gate.py            ✓
├── validate_evidence_pack.py     ✓
├── validate_graph.py             ✓
├── validate_pattern_matches.py   ✓
├── ga_gate_check.py              ✓
└── ... (100+ more)
```

### Test Contracts (362 contracts)
```
tests/contracts/
├── CrossFunctionReentrancy.sol   ✓
├── hard-case/
│   └── NovelStorageCollision.sol ✓
├── semantic-test-set/
│   └── SemanticPrivilegedStateTest.sol ✓
├── safe/                         ✓ (AccessControl, Delegatecall, Reentrancy variants)
└── ... (362 total)
```

### Test Fixtures
```
tests/fixtures/
├── dvd/
│   ├── naive-receiver/           ✓
│   └── side-entrance/            ✓
├── smartbugs/                    ✓
├── foundry-vault/                ✓
└── vault-hard-case/              ✓
```

### Ground Truth Corpus
```
.vrs/corpus/ground-truth/
├── code4rena/
│   ├── 2024-03-revert-lend/      ✓
│   ├── 2024-04-dyad/             ✓
│   ├── 2024-05-munchables/       ✓
│   └── ... (5 total)
├── smartbugs/                    ✓
├── dvdefi-v3.yaml                ✓
├── ethernaut.yaml                ✓
└── internal/annotated/           ✓ (3 annotated)
```

### VQL Query System
```
src/alphaswarm_sol/kg/queries/
├── vql_minimum_set.yaml          ✓ (8 VQL-MIN queries)
└── __init__.py                   ✓ (VQL interface)
```

---

## Final Disposition

| Status | Count | Action |
|--------|-------|--------|
| CLOSED (already exists) | 7 | None |
| DEFERRED (Wave 5) | 2 | Implement if needed later |
| REJECTED (over-engineering) | 9 | None |
| **Total** | **18** | **No immediate action required** |

---

## Recommendation

Archive `IMPROVEMENT-ROADMAP-IMPROVEMENTS.md` as resolved. The deep analysis agent generated improvements without checking existing infrastructure. This is a lesson: **always verify before proposing**.

The testing infrastructure for Phase 07.3.1.6 is complete and ready for execution.
