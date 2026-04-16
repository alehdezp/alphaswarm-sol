# BSKG 4.0 - TODO

**Goal:** DVDeFi detection >= 80%

**Updated:** 2026-01-07

---

## Quick Navigation

| Document | Purpose |
|----------|---------|
| `MASTER.md` | High-level roadmap with phase overview |
| `REBUILD_TASKS.md` | **Consolidated task list (147 tasks, 737h est.)** |
| `TODO.md` | This file - Daily tracking and progress |
| `phases/phase-N/TRACKER.md` | Detailed phase trackers |

---

## Current Phase: 2 - Benchmark Infrastructure

**Phase 1 ✅ COMPLETE:** 84.6% detection rate (11/13 DVDeFi challenges)

See `phases/phase-2/TRACKER.md` for detailed tasks.
See `REBUILD_TASKS.md` for consolidated view across all phases.

### This Week

- [x] **R2.1 Research benchmark approaches** → benchmarks/RESEARCH_NOTES.md
- [x] **2.1 Define expected results** → 13 YAMLs in benchmarks/dvdefi/
- [x] **2.2 Implement benchmark runner** → src/true_vkg/benchmark/
- [x] **2.3 Baseline comparison** → compare_results() in runner.py
- [x] **2.4 CI integration** → .github/workflows/benchmark.yml
- [x] **2.6 Self-validation test** → tests/test_benchmark_validation.py
- [x] **2.9 Labeling protocol** → benchmarks/LABELING.md
- [x] **2.11 Multi-tier strategy** → benchmarks/TIER_STRATEGY.md
- [x] **2.12 Framework detection** → src/true_vkg/kg/framework.py

**Remaining Phase 2:**
- [ ] **2.5 Metrics dashboard** (SHOULD)
- [ ] **2.7 SmartBugs curated dataset** (MUST)
- [ ] **2.8 Safe set for false positives** (MUST)
- [ ] **2.10 Analysis completeness report** (MUST)

### Self-Critique After Each Fix

```bash
# 1. Run tests
uv run pytest tests/ -v

# 2. Check specific challenge
vkg build examples/damm-vuln-defi/src/unstoppable/
vkg analyze | grep dos

# 3. Run full benchmark
vkg benchmark run --suite dvd

# 4. Compare to baseline
vkg benchmark compare --baseline main
```

---

## Phase Summary

| Phase | Status | Next Action |
|-------|--------|-------------|
| 1. Fix Detection | ✅ COMPLETE | 84.6% detection rate achieved |
| 2. Benchmark Infra | **IN PROGRESS** (9/12 done) | 2.7, 2.8, 2.10 remaining |
| 3. CLI & Tasks | BLOCKED | Wait for Phase 2 |
| 4. Test Scaffolding | BLOCKED | Wait for Phase 3 |
| 5. Real-World | BLOCKED | Wait for Phase 4 |
| 6-10 | BLOCKED | Wait for Phase 5 (Core Complete) |
| 11-16 | BLOCKED | Wait for Phase 10 (Enhancement Complete) |

---

## Progress Tracker

| Challenge | Expected | Detected | Status |
|-----------|----------|----------|--------|
| Unstoppable | dos-strict-equality | dos-strict-equality | ✅ |
| Truster | auth-011, auth-017 | auth-011, auth-017 | ✅ |
| Naive Receiver | callback-auth | external-call-public-no-gate | ✅ |
| Side Entrance | reentrancy | reentrancy-basic | ✅ |
| The Rewarder | flash-loan-reward-attack | flash-loan-reward-attack | ✅ |
| Selfie | governance-flash-loan | governance-flash-loan | ✅ |
| Compromised | oracle-manipulation | - | ❌ (needs off-chain trust modeling) |
| Puppet | dex-oracle-manipulation | dex-oracle-manipulation | ✅ |
| Puppet V2 | dex-oracle-manipulation | dex-oracle-manipulation | ✅ |
| Puppet V3 | dex-oracle-manipulation | dex-oracle-manipulation | ✅ |
| Free Rider | msg-value-loop-reuse | msg-value-loop-reuse | ✅ |
| Backdoor | callback-controlled-recipient | callback-controlled-recipient | ✅ |
| Climber | timelock-bypass | - | ❌ |

**Detection Rate:** 11/13 (84.6%) → Target: 80% ✅ EXCEEDED

**New Patterns Created:**
- `governance-flash-loan` → selfie
- `flash-loan-reward-attack` → the-rewarder
- `dex-oracle-manipulation` → puppet, puppet-v2, puppet-v3
- `msg-value-loop-reuse` → free-rider
- `callback-controlled-recipient` → backdoor

---

## Quick Reference

**All phase trackers:** (relative to `task/4.0/`)

| Phase | File | Description | Status |
|-------|------|-------------|--------|
| 1 | `phases/phase-1/TRACKER.md` | Fix Detection | ✅ COMPLETE |
| 2 | `phases/phase-2/TRACKER.md` | Benchmark Infrastructure | **CURRENT** |
| 3 | `phases/phase-3/TRACKER.md` | CLI & Task System | BLOCKED |
| 4 | `phases/phase-4/TRACKER.md` | Test Scaffolding | BLOCKED |
| 5 | `phases/phase-5/TRACKER.md` | Real-World Validation | BLOCKED |
| 6 | `phases/phase-6/TRACKER.md` | Beads System | BLOCKED |
| 7 | `phases/phase-7/TRACKER.md` | Conservative Learning | BLOCKED |
| 8 | `phases/phase-8/TRACKER.md` | Metrics & Observability | BLOCKED |
| 9 | `phases/phase-9/TRACKER.md` | Context Optimization | BLOCKED |
| 10 | `phases/phase-10/TRACKER.md` | Graceful Degradation | BLOCKED |
| 11 | `phases/phase-11/TRACKER.md` | LLM Integration | BLOCKED |
| 12 | `phases/phase-12/TRACKER.md` | Agent SDK Micro-Agents | BLOCKED |
| 13 | `phases/phase-13/TRACKER.md` | Grimoires & Skills | BLOCKED |
| 14 | `phases/phase-14/TRACKER.md` | Confidence Calibration | BLOCKED |
| 15 | `phases/phase-15/TRACKER.md` | Novel Solutions | BLOCKED |
| 16 | `phases/phase-16/TRACKER.md` | Release & Distribution | BLOCKED |

**Master documents:**
- `MASTER.md` - High-level roadmap
- `REBUILD_TASKS.md` - Consolidated task list

---

## Daily Log

### 2026-01-07 (Night)
- Phase 1 ✅ COMPLETE (84.6% detection rate)
- Phase 2 IN PROGRESS (9/12 tasks done):
  - R2.1: benchmarks/RESEARCH_NOTES.md
  - 2.1: 13 DVDeFi challenge YAMLs
  - 2.2-2.4: Benchmark runner + CLI + CI
  - 2.6: Self-validation tests (9 tests)
  - 2.9: Labeling protocol
  - 2.11: Multi-tier strategy
  - 2.12: Framework detection (12 tests)
- 45 new tests passing across benchmark, framework modules
- Aligned task documentation with implementation

### 2026-01-07 (Evening)
- Restructured roadmap into 16 phases
- Each phase has TRACKER.md with:
  - Self-critique protocol
  - Research tasks where needed
  - Validation gates
  - Iteration requirements
- Every task requires real-world validation
- Independent agent verification built in
- Archive preserved for reference

### 2026-01-07 (Morning)
- Course correction applied
- Archived premature phases
- Created focused TODO
- Next: Run DVDeFi baseline

---

*One task at a time. Validate before proceeding.*
