# Evaluation Template: [Solution Name]

**Evaluator:** BSKG Team
**Date:** YYYY-MM-DD
**Solution Location:** `src/true_vkg/[module]/`
**Test Location:** `tests/test_[module].py`

---

## 1. BASIC FUNCTIONALITY

### 1.1 Tests Pass

```bash
# Command:
uv run pytest tests/test_[module].py -v --tb=short

# Results:
# Pass: [X]
# Fail: [X]
```

**Score (0-5):** [X] / 5

### 1.2 Core Feature Works

**Test Scenario:** [Describe real usage test]

**Result:** [Works / Partial / Fails]

**Score (0-5):** [X] / 5

---

## 2. REAL-WORLD VALUE

**Would auditors use this daily?** [Yes/No - explain]

**Is output actionable?** [Yes/No - explain]

**Score (0-5):** [X] / 5

---

## 3. COMPLEXITY COST (inverse scoring)

**External Dependencies:** [List]

**Installation Difficulty:** [Easy/Medium/Hard]

**Score (5 = simple, 0 = complex):** [X] / 5

---

## 4. MAINTENANCE BURDEN (inverse scoring)

**Test Coverage:** [X]%

**Code Quality:** [Good/Fair/Poor]

**Likely to Break:** [Yes/No - why]

**Score (5 = low burden, 0 = high burden):** [X] / 5

---

## 5. USER DEMAND

**Related Requests:** [Links or N/A]

**Unique Value:** [What does this offer that others don't?]

**Score (0-5):** [X] / 5

---

## TOTAL SCORE

| Category | Score | Weight | Weighted |
|----------|-------|--------|----------|
| Tests Pass | /5 | 0.15 | |
| Core Works | /5 | 0.15 | |
| Real-World Value | /5 | 0.30 | |
| Complexity (inverse) | /5 | 0.15 | |
| Maintenance (inverse) | /5 | 0.10 | |
| User Demand | /5 | 0.15 | |
| **TOTAL** | | 1.00 | **/5** |

---

## DECISION

| Decision | Criteria |
|----------|----------|
| **INTEGRATE** | Total >= 3.5 AND Real-World Value >= 4 |
| **DEFER** | Total 2.5-3.5 OR promising but needs work |
| **CUT** | Total < 2.5 OR doesn't work OR high maintenance |

**Decision:** [INTEGRATE / DEFER / CUT]

**Rationale:** [Brief explanation]

---

*Evaluation completed: YYYY-MM-DD*
