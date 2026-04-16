# User Journey Metrics Report

**Run ID:** test-run-20260131-001
**Persona:** novice
**Generated:** 2026-01-31T01:04:33Z
**Overall Status:** FAIL

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Metrics Collected | 10 |
| Metrics Passed | 4 |
| Metrics Failed | 6 |
| Unknown/Missing | 5 |
| Gates Evaluated | 3 |
| Gates Passed | 1 |

---

## Quality Gates

### P0 UX Gate: FAIL

Critical UX requirements for GA

| Metric | Operator | Threshold | Actual | Status |
|--------|----------|-----------|--------|--------|
| UX-SUCCESS-001 | >= | 80 | 100.00 | PASS |
| UX-SUCCESS-002 | == | True | .vrs/reports/audit-report.md | FAIL |
| UX-TIME-001 | <= | 600 | 185.00 | PASS |
| UX-INT-001 | <= | 5 | 1 | PASS |

### P1 UX Gate: FAIL

Important UX requirements

| Metric | Operator | Threshold | Actual | Status |
|--------|----------|-----------|--------|--------|
| UX-SUCCESS-001 | >= | 90 | 100.00 | PASS |
| UX-TIME-003 | <= | 120 | None | FAIL |
| UX-ERR-001 | >= | 70 | None | FAIL |
| UX-SUCCESS-003 | >= | 70 | None | FAIL |

### P2 UX Gate: PASS

Nice-to-have UX improvements

| Metric | Operator | Threshold | Actual | Status |
|--------|----------|-----------|--------|--------|
| UX-SUCCESS-001 | >= | 95 | 100.00 | PASS |

---

## Metric Details

| ID | Name | Value | Unit | Level | Status |
|-----|------|-------|------|-------|--------|
| UX-TIME-001 | Time to First Report | 185.00 | seconds | acceptable | PASS |
| UX-TIME-002 | Installation Duration | 45.00 | seconds | acceptable | PASS |
| UX-TIME-003 | Failure Recovery Time | N/A | seconds | unknown | FAIL |
| UX-INT-001 | Manual Interventions | 1 | count | acceptable | PASS |
| UX-INT-002 | Documentation Lookups | N/A | count | unknown | FAIL |
| UX-SUCCESS-001 | Successful Run Rate | 100.00 | percentage | acceptable | PASS |
| UX-SUCCESS-002 | Report Generated | .vrs/reports/audit-report.md | boolean | failed | FAIL |
| UX-SUCCESS-003 | Findings Actionable | N/A | percentage | unknown | FAIL |
| UX-ERR-001 | Error Message Clarity | N/A | score | unknown | FAIL |
| UX-ERR-002 | Graceful Degradation | N/A | percentage | unknown | FAIL |

---

## Recommendations

The following metrics require attention:

- **Report Generated**: Current value (.vrs/reports/audit-report.md) is failed. Target: True

The following metrics could not be measured:

- **Failure Recovery Time**: Data not available in evidence pack
- **Documentation Lookups**: Data not available in evidence pack
- **Findings Actionable**: Data not available in evidence pack
- **Error Message Clarity**: Data not available in evidence pack
- **Graceful Degradation**: Data not available in evidence pack

---

## References

- Configuration: `configs/user_journey_metrics.yaml`
- Gate Definitions: `phases/07.3.2-execution-evidence-protocol/07.3.2-GATES.md`
- Phase Design: `07.3.4-PHASE-DESIGN.md`
