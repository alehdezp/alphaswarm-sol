# Phase [N]: [Phase Name]

**Status:** [TODO | IN PROGRESS | COMPLETE | BLOCKED (by Phase X)]
**Priority:** [CRITICAL | HIGH | MEDIUM | LOW]
**Last Updated:** [YYYY-MM-DD]
**Author:** [WHO]
**Estimated Hours:** [TOTAL]
**Actual Hours:** [TRACKED]

---

## Quick Reference

| Field | Value |
|-------|-------|
| Entry Gate | [What must be true before starting - reference specific phases/tasks] |
| Exit Gate | [Concrete, testable criteria for completion] |
| Philosophy Pillars | [Which of the 5 pillars this serves] |
| Threat Model Categories | [Which attack surfaces this addresses] |
| Task Count | [N tasks] |
| Test Count Target | [N tests to add] |

---

## 0. CROSS-PHASE DEPENDENCIES

### 0.1 Upstream Dependencies (What This Phase Needs)

| Phase | Artifact Needed | Why Required | Task Reference |
|-------|----------------|--------------|----------------|
| Phase X | [Artifact/Output] | [How this phase uses it] | X.Y |
| Phase Y | [Artifact/Output] | [How this phase uses it] | Y.Z |

### 0.2 Downstream Dependencies (What Uses This Phase)

| Phase | What They Need | Artifact We Produce | Our Task |
|-------|----------------|---------------------|----------|
| Phase X | [Their requirement] | [What we deliver] | [N].X |
| Phase Y | [Their requirement] | [What we deliver] | [N].Y |

### 0.3 Cross-Phase Task References

| Our Task | Related Task in Other Phase | Relationship |
|----------|----------------------------|--------------|
| [N].X | Phase Y, Task Y.Z | [blocks | depends on | extends] |

**ARCHITECTURAL NOTE:** [Any concerns about dependency structure]

---

## 1. OBJECTIVES

### 1.1 Primary Objective

[One-sentence statement of what this phase achieves. Must be concrete and testable.]

### 1.2 Secondary Objectives

1. [Secondary goal 1]
2. [Secondary goal 2]
3. [Secondary goal 3]

### 1.3 Philosophy Alignment

| Pillar | How This Phase Contributes |
|--------|---------------------------|
| Knowledge Graph | [Contribution or N/A] |
| NL Query System | [Contribution or N/A] |
| Agentic Automation | [Contribution or N/A] |
| Self-Improvement | [Contribution or N/A] |
| Task System (Beads) | [Contribution or N/A] |

### 1.4 Success Metrics

| Metric | Target | Minimum | How to Measure | Command/Test |
|--------|--------|---------|----------------|--------------|
| [Metric 1] | [Target] | [Min] | [Description] | `uv run pytest...` or `vkg ...` |
| [Metric 2] | [Target] | [Min] | [Description] | [Command] |

### 1.5 Non-Goals (Explicit Scope Boundaries)

- [What this phase explicitly does NOT do]
- [Deferred to Phase X - with specific reason]

---

## 2. RESEARCH REQUIREMENTS

### 2.1 Required Research Before Implementation

| ID | Research Topic | Output | Est. Hours | Status | Documented At |
|----|---------------|--------|------------|--------|---------------|
| R[N].1 | [Topic] | [Document/Notes] | [Hours] | [TODO/DONE] | `phases/phase-N/research/` |
| R[N].2 | [Topic] | [Document/Notes] | [Hours] | [TODO/DONE] | `phases/phase-N/research/` |

### 2.2 Knowledge Gaps

- [ ] [Gap 1: What we don't know - be specific]
- [ ] [Gap 2: What needs investigation]

### 2.3 External References

| Reference | URL/Path | Purpose | Last Verified |
|-----------|----------|---------|---------------|
| [Paper/Doc] | [Link] | [Why needed] | [Date] |

### 2.4 Research Completion Criteria

- [ ] All research tasks completed
- [ ] Findings documented in `phases/phase-N/research/`
- [ ] Implementation approach selected and justified
- [ ] Uncertainties explicitly documented

---

## 3. TASK DECOMPOSITION

### 3.1 Task Dependency Graph

```
[ASCII diagram showing task dependencies]
R[N].1 ──┬── [N].1 ── [N].2 ── [N].3
         │
         └── [N].4 ── [N].5
```

### 3.2 Task Registry

| ID | Task | Est. | Priority | Depends On | Status | Exit Criteria |
|----|------|------|----------|------------|--------|---------------|
| R[N].1 | [Research task] | [Xh] | MUST | - | TODO | [Research doc exists] |
| [N].1 | [Task name] | [Xh] | MUST | R[N].1 | TODO | [Specific testable criteria] |
| [N].2 | [Task name] | [Xh] | MUST | [N].1 | TODO | [Specific testable criteria] |
| [N].3 | [Task name] | [Xh] | SHOULD | [N].2 | TODO | [Specific testable criteria] |
| [N].4 | [Task name] | [Xh] | COULD | - | TODO | [Specific testable criteria] |

**Priority Legend:**
- **MUST:** Phase cannot be completed without this
- **SHOULD:** Significantly improves phase quality
- **COULD:** Nice-to-have, can be deferred

### 3.3 Dynamic Task Spawning

**Tasks may be added during execution when:**
- Research reveals additional requirements
- Implementation uncovers edge cases
- Testing reveals gaps
- Reflection identifies missed requirements
- Cross-phase dependencies clarified

**Process for adding tasks:**
1. Document reason for new task
2. Assign ID: [N].X where X is next available
3. Update task registry with all fields
4. Update dependency graph
5. Re-estimate phase completion
6. Update INDEX.md in phases directory

### 3.4 Task Details

---

#### Task R[N].1: [Research Task Name]

**Objective:** [What this research discovers/validates]

**Research Questions:**
- [ ] [Question 1]
- [ ] [Question 2]

**Deliverables:**
- `phases/phase-N/research/[topic].md` - [Description]

**Estimated Hours:** [X]h
**Actual Hours:** [Tracked]

---

#### Task [N].1: [Task Name]

**Objective:** [What this task achieves - one sentence]

**Prerequisites:**
- [ ] [What must exist before starting]

**Implementation:**
```python
# Key code patterns or pseudocode
# Include REAL file paths where changes go
```

**Files to Create/Modify:**
| File | Action | Purpose |
|------|--------|---------|
| `path/to/file.py` | CREATE/MODIFY | [Purpose] |

**Validation Criteria:**
- [ ] [Criterion 1 - must be testable]
- [ ] [Criterion 2]

**Test Requirements:**
- [ ] Unit test: `tests/test_[feature].py::test_[specific]`
- [ ] Integration test: [Description and location]
- [ ] CI check: `uv run pytest ...` command

**Estimated Hours:** [X]h
**Actual Hours:** [Tracked]

**Notes:** [Implementation notes, gotchas, known issues]

---

## 4. TEST SUITE REQUIREMENTS

### 4.1 Test Categories

| Category | Count Target | Coverage Target | Location |
|----------|--------------|-----------------|----------|
| Unit Tests | [N] | [X]% | `tests/test_[module].py` |
| Integration Tests | [N] | - | `tests/integration/` |
| End-to-End Tests | [N] | - | `tests/e2e/` |
| Benchmark Tests | [N] | - | `tests/benchmark/` |
| Regression Tests | [N] | - | `tests/regression/` |

### 4.2 Test Matrix

| Feature | Happy Path | Edge Cases | Error Cases | Performance |
|---------|-----------|------------|-------------|-------------|
| [Feature 1] | [ ] | [ ] | [ ] | [ ] |
| [Feature 2] | [ ] | [ ] | [ ] | [ ] |

### 4.3 Test Fixtures Required

| Fixture | Location | Purpose | Exists? |
|---------|----------|---------|---------|
| [Fixture] | `tests/fixtures/[name]` | [Purpose] | [ ] |
| [Contract] | `tests/contracts/[name].sol` | [Purpose] | [ ] |

### 4.4 Benchmark Validation

| Benchmark | Target | Baseline | Current | Command |
|-----------|--------|----------|---------|---------|
| [Benchmark 1] | [Target] | [Baseline] | [Current] | `vkg benchmark...` |

### 4.5 Test Automation

```bash
# Commands to run all phase tests
uv run pytest tests/test_phase_[N]*.py -v

# Commands to run specific test categories
uv run pytest tests/test_[module].py -v -k "[pattern]"

# CI/CD command (this should match what CI runs)
uv run pytest tests/ -v --tb=short
```

---

## 5. IMPLEMENTATION GUIDELINES

### 5.1 Code Standards

- [ ] Type hints on all public functions
- [ ] Docstrings with examples for all public functions
- [ ] No hardcoded values (use config or constants)
- [ ] Error messages guide user to recovery
- [ ] Logging at appropriate levels (DEBUG, INFO, WARNING, ERROR)

### 5.2 File Locations

| Component | Location | Naming Convention |
|-----------|----------|-------------------|
| Core Logic | `src/true_vkg/[module]/` | `snake_case.py` |
| Tests | `tests/test_[module].py` | `test_[feature].py` |
| Fixtures | `tests/fixtures/` | `[Description].sol` or `.json` |
| Docs | `docs/[category]/` | `[feature].md` |

### 5.3 Dependencies

| Dependency | Version | Purpose | Optional? | Added By This Phase? |
|------------|---------|---------|-----------|---------------------|
| [Package] | [Version] | [Why needed] | [Yes/No] | [Yes/No] |

### 5.4 Configuration

```yaml
# New configuration options added by this phase
# Document in docs/configuration.md
[section]:
  [option]: [default]  # [description]
  [option]: [default]  # [description]
```

---

## 6. REFLECTION PROTOCOL

### 6.1 Brutal Self-Critique Checklist

**After EACH task completion, answer honestly:**

- [ ] Does this actually work on real-world code, not just test fixtures?
- [ ] Would a skeptical reviewer find obvious flaws?
- [ ] Are we testing the right thing, or just what's easy to test?
- [ ] Does this add unnecessary complexity?
- [ ] Could this be done simpler?
- [ ] Are we measuring what matters, or what's convenient?
- [ ] Would this survive adversarial input?
- [ ] Is the documentation accurate, or aspirational?
- [ ] Would a new developer understand this code?
- [ ] Does this break anything in other phases?

### 6.2 Real-World Validation Protocol

**Every task must be validated on:**
1. DVDeFi benchmark (if detection-related)
2. At least one real-world contract (not test fixtures)
3. Edge cases from previous bugs

**Validation Command:**
```bash
# Run this after every significant change
uv run pytest tests/ -v && vkg benchmark run --suite dvd
```

### 6.3 Known Limitations

| Limitation | Impact | Mitigation | Future Fix? | Related Phase |
|------------|--------|------------|-------------|---------------|
| [Limitation 1] | [Impact] | [Current workaround] | [Phase X or N/A] | [Phase Y if related] |

### 6.4 Alternative Approaches Considered

| Approach | Pros | Cons | Why Not Chosen |
|----------|------|------|----------------|
| [Approach 1] | [Pros] | [Cons] | [Reason] |
| [Approach 2] | [Pros] | [Cons] | [Reason] |

### 6.5 What If Current Approach Fails?

**Trigger:** [When to abandon current approach - be specific]

**Fallback Plan:**
1. [Step 1]
2. [Step 2]
3. [Step 3]

**Escalation:** [Who to consult, what to read, other phases to check]

---

## 7. ITERATION PROTOCOL

### 7.1 Success Measurement

| Checkpoint | Frequency | Pass Criteria | Action on Fail |
|------------|-----------|---------------|----------------|
| Unit tests pass | Every commit | 100% pass | Fix before proceeding |
| Benchmark check | Daily | No regression | Debug immediately |
| Integration test | Per task | 100% pass | Iterate on implementation |
| Real-world test | End of phase | >= target | Iterate or re-approach |

### 7.2 Iteration Triggers

**Iterate (same approach, fix issues):**
- Test failures in specific edge cases
- Performance below target by < 20%
- Minor gaps in functionality

**Re-approach (different approach):**
- Fundamental design flaw discovered
- Performance below target by > 50%
- Three failed iteration attempts
- New research invalidates assumptions

### 7.3 Maximum Iterations

| Task Type | Max Iterations | Escalation |
|-----------|---------------|------------|
| Simple fix | 3 | Re-approach |
| New feature | 5 | Architectural review |
| Integration | 4 | Dependency audit |

### 7.4 Iteration Log

| Date | Task | Issue | Action | Outcome | Hours Spent |
|------|------|-------|--------|---------|-------------|
| [Date] | [Task ID] | [Issue] | [Action] | [Outcome] | [Hours] |

---

## 8. COMPLETION CHECKLIST

### 8.1 Exit Criteria

**ALL of these must be true:**

- [ ] All MUST tasks completed
- [ ] All tests passing (`uv run pytest tests/ -v`)
- [ ] Benchmark targets met (no regression)
- [ ] Documentation updated
- [ ] No regressions introduced
- [ ] Reflection completed honestly
- [ ] Cross-phase dependencies satisfied
- [ ] INDEX.md updated with task status

**Phase [N] is COMPLETE when:**
- [ ] [Specific criterion 1]
- [ ] [Specific criterion 2]
- [ ] [Specific criterion 3]

**Gate Keeper:** [Specific test or command that MUST pass]
```bash
# Gate keeper command - phase cannot complete without this passing
[specific command]
```

### 8.2 Artifacts Produced

| Artifact | Location | Purpose | Verified? |
|----------|----------|---------|-----------|
| [Code] | [Path] | [Purpose] | [ ] |
| [Tests] | [Path] | [Purpose] | [ ] |
| [Docs] | [Path] | [Purpose] | [ ] |

### 8.3 Metrics Achieved

| Metric | Target | Achieved | Notes | Date |
|--------|--------|----------|-------|------|
| [Metric] | [Target] | [Actual] | [Notes] | [Date] |

### 8.4 Lessons Learned

1. [Lesson 1 - be specific and actionable]
2. [Lesson 2]
3. [Lesson 3]

### 8.5 Recommendations for Future Phases

| Recommendation | Relevant Phase | Priority |
|---------------|----------------|----------|
| [Recommendation 1] | Phase X | HIGH/MEDIUM/LOW |
| [Recommendation 2] | Phase Y | HIGH/MEDIUM/LOW |

---

## 9. APPENDICES

### 9.1 Detailed Technical Specifications

[Extended technical details that don't fit in main sections]

### 9.2 Code Examples

[Reference implementations, patterns to follow]

### 9.3 Troubleshooting Guide

| Problem | Cause | Solution | Related Task |
|---------|-------|----------|--------------|
| [Problem] | [Cause] | [Solution] | [Task ID] |

### 9.4 Glossary

| Term | Definition |
|------|------------|
| [Term] | [Definition] |

---

## 10. PHASE METADATA

**Version History:**
| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | [Date] | Initial creation | [Author] |
| 1.1 | [Date] | [Changes] | [Author] |

**Cross-References:**
- MASTER.md: [Section that references this phase]
- INDEX.md: [Row number in task index]
- Related Phases: [List of closely related phases]

---

*Phase [N] Tracker | Version X.0 | [Date]*
*Template: PHASE_TEMPLATE.md v2.0*
