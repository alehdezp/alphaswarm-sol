# Task Template

```markdown
# [PX-TY] Task Name

**Phase**: X - Phase Name
**Task ID**: PX-TY
**Status**: NOT_STARTED | IN_PROGRESS | BLOCKED | COMPLETED | DEPRECATED
**Priority**: CRITICAL | HIGH | MEDIUM | LOW
**Estimated Effort**: X days/weeks
**Actual Effort**: - (fill after completion)

---

## Executive Summary

[2-3 sentences describing what this task accomplishes and why it matters]

---

## Dependencies

### Required Before Starting
- [ ] [PX-TY] Task Name - Why needed
- [ ] [PX-TY] Task Name - Why needed

### Blocks These Tasks
- [PX-TY] Task Name - What they need from this

---

## Objectives

### Primary Objectives
1. [Specific, measurable objective]
2. [Specific, measurable objective]

### Stretch Goals
1. [Nice-to-have if time permits]

---

## Success Criteria

### Must Have (Definition of Done)
- [ ] Criterion 1 with measurable target
- [ ] Criterion 2 with measurable target
- [ ] All tests pass
- [ ] Documentation updated

### Should Have
- [ ] Performance within X% of baseline
- [ ] Backward compatible with existing code

### Nice to Have
- [ ] Additional capability X

---

## Technical Design

### Architecture

[Diagram or description of how this fits in the system]

### New Files
- `src/true_vkg/new/file.py` - Purpose
- `tests/test_new/test_file.py` - Tests

### Modified Files
- `src/true_vkg/existing/file.py` - What changes

### Key Data Structures

```python
@dataclass
class NewStructure:
    """Purpose"""
    field1: Type  # Description
    field2: Type  # Description
```

### Key Algorithms

1. **Algorithm Name**: Description of approach
   - Step 1
   - Step 2
   - Complexity: O(?)

---

## Implementation Plan

### Phase 1: Foundation (X days)
- [ ] Step 1: Description
- [ ] Step 2: Description
- [ ] Checkpoint: What should be working

### Phase 2: Core Logic (X days)
- [ ] Step 1: Description
- [ ] Step 2: Description
- [ ] Checkpoint: What should be working

### Phase 3: Integration (X days)
- [ ] Step 1: Description
- [ ] Step 2: Description
- [ ] Checkpoint: What should be working

---

## Validation Tests

### Unit Tests

```python
# Test file: tests/test_3.5/test_PX_TY.py

def test_basic_functionality():
    """Test that basic functionality works."""
    # Setup
    # Action
    # Assert

def test_edge_case_1():
    """Test specific edge case."""
    pass

def test_integration_with_existing():
    """Test integration with existing VKG."""
    pass
```

### Integration Tests

```python
def test_end_to_end():
    """Full pipeline test."""
    pass
```

### Performance Tests

```python
def test_performance_baseline():
    """Ensure no regression."""
    # Must complete in < X seconds
    pass
```

### The Ultimate Test

[Describe a complex, real-world scenario that proves this works]

---

## Metrics & Measurement

### Before Implementation (Baseline)
| Metric | Value | How Measured |
|--------|-------|--------------|
| Metric 1 | - | Method |
| Metric 2 | - | Method |

### After Implementation (Results)
| Metric | Target | Actual | Pass/Fail |
|--------|--------|--------|-----------|
| Metric 1 | X | - | - |
| Metric 2 | Y | - | - |

### Measurement Commands

```bash
# How to measure metric 1
uv run python -m true_vkg.benchmark metric1

# How to measure metric 2
uv run python -m true_vkg.benchmark metric2
```

---

## Risk Assessment

### Technical Risks
| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Risk 1 | HIGH | MEDIUM | Mitigation strategy |

### Dependency Risks
| Risk | Impact | Mitigation |
|------|--------|------------|
| External library X unavailable | HIGH | Fallback to Y |

---

## Alternative Approaches

### Approach A: [Current Choice]
- **Pros**:
- **Cons**:
- **Why chosen**:

### Approach B: [Alternative]
- **Pros**:
- **Cons**:
- **Why not chosen**:

---

## Critical Self-Analysis

### What Could Go Wrong
1. [Potential failure mode and how to detect]
2. [Potential failure mode and how to detect]

### Assumptions Being Made
1. [Assumption and what happens if wrong]
2. [Assumption and what happens if wrong]

### Questions to Answer During Implementation
1. [Open question that needs investigation]
2. [Open question that needs investigation]

---

## Improvement Opportunities

### Discovered During Planning
- [ ] [Improvement idea]

### To Explore During Implementation
- [ ] [Area to investigate]

### For Future Phases
- [ ] [Enhancement for later]

---

## Blockers

[Document any blockers encountered]

| Date | Blocker | Resolution | Resolved Date |
|------|---------|------------|---------------|
| - | - | - | - |

---

## Results

### Outcomes
[Fill after completion]

### Metrics Achieved
[Fill after completion]

### Artifacts Produced
- [ ] Code: `path/to/code`
- [ ] Tests: `path/to/tests`
- [ ] Docs: `path/to/docs`

---

## Retrospective

### What Went Well
[Fill after completion]

### What Could Be Improved
[Fill after completion]

### Lessons Learned
[Fill after completion]

### Recommendations for Similar Tasks
[Fill after completion]

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| YYYY-MM-DD | Created | Name |
```
