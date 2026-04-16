# Phase 17 Completion Plan

**Date:** 2026-01-09
**Status:** Re-Crawl In Progress
**Target:** Complete all 87 sources, generate 50+ patterns

---

## Current State

### Active Work (NOW)

**3 Background Subagents Processing 13 Sources:**

| Agent | Batch | Sources | Status | Progress |
|-------|-------|---------|--------|----------|
| a420331 | Batch A: Audit Firms | 5 sources | 🔄 RUNNING | 11 tools, 10K tokens |
| a1730fe | Batch B: Vuln DBs | 3 sources | 🔄 RUNNING | 13 tools, 7.7K tokens |
| a80a2dc | Batch C: Documentation | 5 sources | 🔄 RUNNING | crawl4ai started |

**Completed Work:**
- ✅ Initial 38 sources processed (47+ vulnerabilities, 19+ VulnDocs)
- ✅ URL targeting issue discovered and fixed (34+ corrections)
- ✅ Corrected sources.yaml created (87 sources)
- ✅ Priority re-crawl batch launched (13 sources)

**Subagent 1 (ab20226) Status:**
- Still processing defi-vulns comprehensive guide (47 more vulnerabilities pending)
- Source: https://github.com/immunefi-team/Web3-Security-Library (defi-vulns repository)

### Metrics

| Metric | Current | Target | Progress |
|--------|---------|--------|----------|
| Sources crawled | 38/87 (+13 re-crawling) | 87/87 | 59% (51/87) |
| Content hit rate | 10.5% → 70-80% (expected) | 70%+ | ✅ Fixed |
| Vulnerabilities extracted | 47+ (120+ pending) | 300+ | 15-55% |
| VulnDocs files | 19+ (100+ pending) | 100+ | 19-119% |
| Patterns generated | 0 | 50+ | 0% (next step) |

---

## Completion Roadmap

### Phase 1: Complete Re-Crawl (IN PROGRESS)

**Timeline:** 2-4 hours
**Status:** 3 subagents active

**Tasks:**
1. ⏳ **Wait for Batch A** (Audit Firms) - 5 sources
   - Expected: 20-40 vulnerabilities
   - Audit firms publish detailed 2023-2024 findings
2. ⏳ **Wait for Batch B** (Vuln DBs) - 3 sources
   - Expected: 40-60 vulnerabilities
   - Primary vulnerability databases with exploits
3. ⏳ **Wait for Batch C** (Documentation) - 5 sources
   - Expected: 15-25 vulnerabilities
   - Detection patterns and safe code examples
4. ⏳ **Wait for Subagent 1** (defi-vulns) - 47 more vulnerabilities

**Expected Output:**
- 75-125 vulnerabilities from re-crawl
- 47 vulnerabilities from defi-vulns
- **Total: 120-170 new vulnerabilities**
- **50-75 new VulnDocs files**

### Phase 2: Process Remaining Priority Sources

**Timeline:** 1-2 hours
**Sources:** 7 remaining from recrawl_batch_priority.json

**Priority Sources:**
1. Peckshield Blog - https://blog.peckshield.com/
2. Spearbit Portfolio - https://github.com/spearbit/portfolio
3. Trail of Bits Reviews - https://github.com/trailofbits/publications/tree/master/reviews
4. Aave Flash Loans - https://docs.aave.com/developers/guides/flash-loans
5. Compound Security - https://docs.compound.finance/#security
6. Uniswap Contracts - https://docs.uniswap.org/contracts/v4/overview
7. Yearn Developers - https://docs.yearn.fi/developers/v3/overview

**Action:**
```bash
# Create batch file for remaining 7
python scripts/vkg_crawl.py --batch .true_vkg/vulndocs_reference/recrawl_batch_remaining.json
```

**Expected Output:**
- 20-30 vulnerabilities
- 10-15 VulnDocs files

### Phase 3: Crawl Uncrawled Sources

**Timeline:** 8-12 hours
**Sources:** 36 uncrawled sources from Tier 1-11

**Breakdown:**
- **Tier 1-2 (4 sources):** DefiLlama, CodeHawks, Secure3, Hats Finance
- **Tier 4-11 (32 sources):** Researchers, tools, protocols, L2 docs

**Strategy:**
1. Create 4 batches of ~9 sources each
2. Process in parallel with 4 subagents
3. Prioritize known-good sources first

**Expected Output:**
- 80-120 vulnerabilities (mix of high/medium value sources)
- 40-60 VulnDocs files

### Phase 4: Pattern Generation

**Timeline:** 2-4 hours
**Input:** 100+ VulnDocs updates

**Process:**

```bash
# For each new vulnerability subcategory/specific
uv run alphaswarm generate-pattern --from-vulndocs logic/transient-storage
uv run alphaswarm generate-pattern --from-vulndocs logic/balance-manipulation/forced-ether-selfdestruct
uv run alphaswarm generate-pattern --from-vulndocs upgrade/selfdestruct
uv run alphaswarm generate-pattern --from-vulndocs logic/arithmetic
uv run alphaswarm generate-pattern --from-vulndocs logic/configuration
# ... continue for all 100+ updates
```

**Or use pattern-forge skill:**
```bash
# Batch pattern generation
/pattern-forge --batch-from-vulndocs knowledge/vulndocs/categories/
```

**Expected Output:**
- 50-70 BSKG detection patterns
- YAML files in `patterns/` directory
- Test contracts for each pattern

### Phase 5: Pattern Validation

**Timeline:** 2-4 hours
**Input:** 50+ generated patterns

**Process:**

1. **Test Each Pattern:**
```bash
# For each pattern
uv run pytest tests/test_pattern_*.py -v
```

2. **Calculate Metrics:**
```bash
# Use pattern-tester agent for each pattern
```

3. **Assign Ratings:**
- draft: < 70% precision, < 50% recall
- ready: >= 70% precision, >= 50% recall
- excellent: >= 90% precision, >= 85% recall

**Expected Output:**
- Tested patterns with metrics
- Quality ratings assigned
- False positive/negative analysis

### Phase 6: Integration & Documentation

**Timeline:** 1-2 hours

**Tasks:**
1. **Run Integration Tests:**
```bash
uv run pytest tests/integration/ -v
```

2. **Update Documentation:**
- Update TRACKER.md with final status
- Update ROADMAP.md with Phase 17 completion
- Create final summary report

3. **Validate VulnDocs Structure:**
```bash
# Check all VulnDocs have required files
find knowledge/vulndocs -name "index.yaml" | wc -l
find knowledge/vulndocs -name "detection.md" | wc -l
```

4. **Generate Metrics Report:**
- Total sources processed: 87/87
- Vulnerabilities extracted: 300+
- VulnDocs files: 100+
- Patterns generated: 50+
- Pattern quality breakdown

---

## Estimated Timeline

| Phase | Duration | Cumulative |
|-------|----------|------------|
| 1. Complete Re-Crawl | 2-4h | 2-4h |
| 2. Remaining Priority | 1-2h | 3-6h |
| 3. Uncrawled Sources | 8-12h | 11-18h |
| 4. Pattern Generation | 2-4h | 13-22h |
| 5. Pattern Validation | 2-4h | 15-26h |
| 6. Integration & Docs | 1-2h | 16-28h |

**Total:** 16-28 hours (2-3.5 days of work)

**With parallelization:** Can reduce to 12-20 hours

---

## Success Criteria

### Must Have (Phase 17 Complete)

- ✅ All 87 sources crawled and processed
- ✅ 300+ vulnerabilities extracted
- ✅ 100+ VulnDocs files created/updated
- ✅ 50+ BSKG detection patterns generated
- ✅ All patterns tested with metrics
- ✅ Integration tests passing
- ✅ Documentation updated

### Nice to Have (Excellence)

- 70%+ of sources yield technical content
- 85%+ pattern precision/recall average
- Novel vulnerability categories discovered (5+)
- Real-world exploits documented (20+)
- Complete exploit database ($ amounts, dates)

---

## Risk Mitigation

### Risk: Subagents Fail or Timeout

**Mitigation:**
- Monitor subagent output files regularly
- Resume failed subagents with agent ID
- Use smaller batches for problematic sources

### Risk: Corrected URLs Still Have No Content

**Mitigation:**
- Use Exa search to find specific writeups
- Target GitHub repos directly for audit reports
- Use Medium/Substack for researcher blogs
- Fall back to manually curated URL list

### Risk: Pattern Generation Takes Too Long

**Mitigation:**
- Prioritize high-value vulnerabilities first
- Use pattern-forge skill for batch generation
- Generate patterns incrementally as VulnDocs are created

### Risk: False Positive Rate Too High

**Mitigation:**
- Add none conditions to patterns
- Include safe pattern examples
- Test on real codebases
- Iterate with pattern-tester feedback

---

## Monitoring & Progress Tracking

### Check Subagent Status

```bash
# Check output files
tail -f /var/folders/.../tasks/a420331.output
tail -f /var/folders/.../tasks/a1730fe.output
tail -f /var/folders/.../tasks/a80a2dc.output
tail -f /var/folders/.../tasks/ab20226.output  # Original subagent 1
```

### Check VulnDocs Updates

```bash
# Count new files
find knowledge/vulndocs -name "*.md" -newer .true_vkg/discovery/PHASE_17_PROGRESS_REPORT.md | wc -l

# Check recent changes
git status knowledge/vulndocs/
```

### Check Discovery Logs

```bash
# View subagent logs
ls -lh .true_vkg/discovery/subagent_*_log.yaml
ls -lh .true_vkg/discovery/recrawl_batch_*_log.yaml

# View summaries
ls -lh .true_vkg/discovery/*_summary.md
```

---

## Next Immediate Actions

**Right Now (Parallel):**
1. ⏳ Monitor 3 active subagents (a420331, a1730fe, a80a2dc)
2. ⏳ Wait for Subagent 1 (ab20226) to finish defi-vulns

**Next (After Re-Crawl Completes):**
1. Launch Batch D: 7 remaining priority sources
2. Review re-crawl results and aggregate findings
3. Begin uncrawled sources (36 sources, 4 batches)

**Then (After All Sources Processed):**
1. Generate patterns for 100+ VulnDocs updates
2. Test and validate all patterns
3. Run integration tests
4. Create final completion report

---

## Files to Update on Completion

### Phase 17 Documentation
- `task/4.0/phases/phase-17/TRACKER.md` - Mark as COMPLETE
- `task/4.0/phases/phase-17/COMPLETION_PLAN.md` - This file
- `task/4.0/phases/phase-17/FINAL_REPORT.md` - Create on completion

### Master Documentation
- `docs/ROADMAP.md` - Update Phase 17 status
- `docs/README.md` - Update feature registry
- `README.md` - Update completion status

### Discovery Logs
- `.true_vkg/discovery/PHASE_17_FINAL_SUMMARY.md` - Complete metrics
- `.true_vkg/discovery/PATTERN_GENERATION_LOG.yaml` - Pattern details

---

*Phase 17 Completion Plan | 2026-01-09*
*Current: Re-Crawl In Progress | Next: Process Remaining Sources*
