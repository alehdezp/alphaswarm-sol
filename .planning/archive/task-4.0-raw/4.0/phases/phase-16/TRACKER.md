# Phase 16: Release & Distribution

**Status:** TODO (unblocked; Phase 15 complete)
**Priority:** MEDIUM - Public availability
**Last Updated:** 2026-01-07
**Author:** BSKG Team
**Version:** 4.0 (Improved with brutal review)

---

## Quick Reference

| Field | Value |
|-------|-------|
| Entry Gate | Phase 15 complete (all novel solutions evaluated) |
| Exit Gate | PyPI published, Docker published, fresh install test passes on 3+ platforms |
| Philosophy Pillars | All 5 Pillars (release validates entire system) |
| Threat Model Categories | Install Security, Package Integrity |
| Estimated Hours | 48h (revised from 41h) |
| Actual Hours | [Tracked] |
| Task Count | 13 tasks (added 16.0, split 16.1) |
| Test Count Target | 25+ release validation tests |

---

## CRITICAL CHANGES FROM REVIEW

### Issues Identified and Fixed

1. **Missing account setup task** - Added 16.0 as blocker
2. **Task 16.1 too large** - Split into sub-tasks with individual files
3. **Unrealistic time estimates** - Revised upward (16.9: 2h -> 4h)
4. **Missing Test PyPI step** - Added to 16.4
5. **Docker image too naive** - Complete rewrite with multi-stage build
6. **No fresh install scripts** - Added concrete test scripts
7. **Missing security scanning** - Added trivy for Docker

### New Task Files Created

See `tasks/` directory for self-contained task instructions:
- `16.0-account-setup.md` - NEW: Credentials and accounts
- `16.1-docs-readme.md` - README update details
- `16.1-docs-getting-started.md` - Getting started guide
- `16.4-pypi-publish.md` - Complete PyPI workflow
- `16.5-docker-image.md` - Production Docker setup
- `16.9-fresh-install-test.md` - Platform test scripts

---

## 1. OBJECTIVES

### 1.1 Primary Objective

Package BSKG 4.0 for public release with verified first-run experience across multiple platforms.

### 1.2 Secondary Objectives

1. Complete, tested documentation for all user types
2. Multiple distribution channels (PyPI, Docker, GitHub)
3. First-run experience that works without maintainer help
4. Pattern versioning for audit traceability

### 1.3 Philosophy Alignment

| Pillar | How This Phase Contributes |
|--------|---------------------------|
| Knowledge Graph | Release validates KG functionality on real projects |
| NL Query System | Release validates query capabilities |
| Agentic Automation | Release includes automation features |
| Self-Improvement | Release includes feedback mechanisms |
| Task System (Beads) | Release validates task workflow |

### 1.4 Success Metrics

| Metric | Target | Minimum | How to Measure |
|--------|--------|---------|----------------|
| Fresh Install Success | 100% on 4 platforms | 100% on 2 platforms | Platform test matrix |
| Getting Started Time | < 10 min | < 15 min | User testing |
| Documentation Coverage | 100% core features | 90% | Feature audit |
| PyPI Install Works | First try | Within 2 tries | Fresh env test |
| Docker Works | First try | Within 2 tries | Docker run test |

### 1.5 Non-Goals (Explicit Scope Boundaries)

- Marketing website (docs sufficient for v4.0)
- Community forums (GitHub issues sufficient)
- Enterprise features (SaaS, team management)
- Automatic updates (manual upgrade process)
- Windows native support (WSL documented as workaround)

---

## 2. RESEARCH REQUIREMENTS

### 2.1 Required Research Before Implementation

| ID | Research Topic | Output | Est. Hours | Status |
|----|---------------|--------|------------|--------|
| R16.1 | PyPI Trusted Publisher | OIDC setup guide | 1h | TODO |
| R16.2 | Docker Multi-Platform | buildx configuration | 1h | TODO |
| R16.3 | GitHub Actions Release | CI/CD workflow | 1h | TODO |

### 2.2 Knowledge Gaps (Must Answer Before Starting)

- [ ] Who owns PyPI and Docker Hub accounts?
- [ ] What GitHub org will be used?
- [ ] What is the package name on PyPI? (Check availability)
- [ ] What is the Docker Hub repository name?
- [ ] Do we need code signing?

### 2.3 External References

| Reference | URL/Path | Purpose |
|-----------|----------|---------|
| PyPI Trusted Publishing | https://docs.pypi.org/trusted-publishers/ | OIDC setup |
| Docker Buildx | https://docs.docker.com/buildx/ | Multi-platform builds |
| Trivy | https://trivy.dev/ | Container security scanning |
| SARIF GitHub | https://docs.github.com/code-security/code-scanning | SARIF validation |

### 2.4 Research Completion Criteria

- [ ] All account ownership documented
- [ ] Package/repo names confirmed available
- [ ] CI/CD pipeline designed
- [ ] Security scanning tool selected

---

## 3. TASK DECOMPOSITION

### 3.1 Task Dependency Graph

```
16.0 (Accounts) ──────────────────┬───────────────────────────────┐
                                  │                               │
        ┌─────────────────────────┼───────────────────────────────┤
        │                         │                               │
        ▼                         ▼                               ▼
16.1a (README) ──► 16.1b (Getting Started) ──► 16.2 (CLI Ref)    │
                                  │                               │
        ┌─────────────────────────┘                               │
        ▼                                                         │
16.3 (API Final) ────────────────────────────────────────────────┤
        │                                                         │
        ▼                                                         │
16.4 (PyPI) ──► 16.5 (Docker) ──► 16.6 (GH Release) ──► 16.7 (Marketplace)
        │              │                    │
        └──────────────┴────────────────────┘
                       │
                       ▼
              16.8 (Pre-Release Check)
                       │
                       ▼
              16.9 (Fresh Install Test)
                       │
                       ▼
           ┌───────────┴───────────┐
           │                       │
           ▼                       ▼
    16.10 (Pattern Ver)     16.11 (CODEOWNERS)
```

### 3.2 Task Registry

#### Foundation (16.0)

| ID | Task | Est. | Priority | Depends On | Status | Task File |
|----|------|------|----------|------------|--------|-----------|
| 16.0 | Account Setup & Credentials | 2h | MUST | - | TODO | `tasks/16.0-account-setup.md` |

#### Documentation (16.1-16.2)

| ID | Task | Est. | Priority | Depends On | Status | Task File |
|----|------|------|----------|------------|--------|-----------|
| 16.1a | README.md Update | 2h | MUST | - | TODO | `tasks/16.1-docs-readme.md` |
| 16.1b | Getting Started Guide | 3h | MUST | 16.1a | TODO | `tasks/16.1-docs-getting-started.md` |
| 16.1c | CLI Reference | 2h | MUST | 16.1a | TODO | - |
| 16.1d | API Reference | 3h | SHOULD | 16.3 | TODO | - |
| 16.1e | Limitations Doc | 1h | MUST | - | TODO | - |
| 16.2 | Link Checker & Spellcheck | 1h | MUST | 16.1a-e | TODO | - |

#### API & Packaging (16.3-16.5)

| ID | Task | Est. | Priority | Depends On | Status | Task File |
|----|------|------|----------|------------|--------|-----------|
| 16.3 | API Finalization | 6h | MUST | - | TODO | - |
| 16.4 | PyPI Package | 4h | MUST | 16.0, 16.3 | TODO | `tasks/16.4-pypi-publish.md` |
| 16.5 | Docker Image | 4h | SHOULD | 16.4 | TODO | `tasks/16.5-docker-image.md` |

#### Release (16.6-16.8)

| ID | Task | Est. | Priority | Depends On | Status | Task File |
|----|------|------|----------|------------|--------|-----------|
| 16.6 | GitHub Release | 2h | MUST | 16.4, 16.5 | TODO | - |
| 16.7 | GitHub Marketplace | 4h | COULD | 16.6 | TODO | - |
| 16.8 | Pre-Release Checklist | 2h | MUST | 16.4-16.6 | TODO | - |

#### Validation (16.9)

| ID | Task | Est. | Priority | Depends On | Status | Task File |
|----|------|------|----------|------------|--------|-----------|
| 16.9 | Fresh Install Test | 4h | MUST | 16.8 | TODO | `tasks/16.9-fresh-install-test.md` |

#### Metadata (16.10-16.11)

| ID | Task | Est. | Priority | Depends On | Status | Task File |
|----|------|------|----------|------------|--------|-----------|
| 16.10 | Pattern Pack Versioning | 4h | SHOULD | - | TODO | - |
| 16.11 | CODEOWNERS Definition | 1h | COULD | - | TODO | - |

### 3.3 Dynamic Task Spawning

**Tasks may be added during execution when:**
- Fresh install testing reveals platform-specific issues
- Documentation gaps discovered during user testing
- Security scanning reveals vulnerabilities
- PyPI or Docker Hub reject submissions

**Process for adding tasks:**
1. Document the issue found
2. Assess if blocker or workaround exists
3. Assign ID: 16.X where X is next available
4. Update dependency graph
5. Re-estimate phase completion

---

## 4. TEST SUITE REQUIREMENTS

### 4.1 Test Categories

| Category | Count Target | Location |
|----------|--------------|----------|
| Install Tests | 10 | `tests/release/test_install.py` |
| CLI Tests | 5 | `tests/test_cli.py` (extend) |
| Documentation Tests | 5 | `tests/release/test_docs.py` |
| Fresh Install Scripts | 4 | `scripts/test_fresh_install_*.sh` |

### 4.2 Platform Test Matrix

| Platform | Python | Test Method | Priority |
|----------|--------|-------------|----------|
| Ubuntu 22.04 | 3.11 | Docker | MUST |
| Ubuntu 22.04 | 3.10 | Docker | SHOULD |
| Ubuntu 22.04 | 3.9 | Docker | SHOULD |
| macOS 13+ | 3.11 | Local | SHOULD |
| Windows 11 | 3.11 | WSL | COULD |

### 4.3 Benchmark Validation

| Benchmark | Target | Baseline | Current |
|-----------|--------|----------|---------|
| Install Time | < 60s | N/A | [Measured] |
| First Audit Time | < 5 min | N/A | [Measured] |
| DVDeFi Detection | >= 80% | Phase 5 | [Measured] |

### 4.4 Test Automation

```bash
# Run release tests
uv run pytest tests/release/ -v

# Run fresh install test (Ubuntu)
./scripts/test_fresh_install_ubuntu.sh

# Run documentation tests
./scripts/check_docs.sh

# Full pre-release validation
./scripts/pre_release_check.sh
```

---

## 5. IMPLEMENTATION GUIDELINES

### 5.1 Code Standards

- [ ] Type hints on all public functions
- [ ] Docstrings with examples
- [ ] No hardcoded values (use config)
- [ ] Error messages guide recovery
- [ ] All user-facing messages reviewed

### 5.2 File Locations

| Component | Location |
|-----------|----------|
| Task Details | `phases/phase-16/tasks/` |
| Release Scripts | `scripts/` |
| Docker | `Dockerfile`, `docker-compose.yml` |
| GitHub Actions | `.github/workflows/release.yml` |
| Documentation | `docs/` |

### 5.3 Required Dependencies

| Dependency | Purpose | Install |
|------------|---------|---------|
| twine | PyPI upload | `pip install twine` |
| docker | Image build | System install |
| trivy | Security scan | `brew install trivy` |
| markdown-link-check | Link validation | `npm i -g markdown-link-check` |

---

## 6. REFLECTION PROTOCOL

### 6.1 Brutal Self-Critique Checklist

**After EACH task completion, answer honestly:**

- [ ] Would a user with no BSKG experience succeed with this?
- [ ] Did I test on a CLEAN environment, not my dev machine?
- [ ] Are error messages helpful or cryptic?
- [ ] Did I document the workarounds I take for granted?
- [ ] Would this work on a machine without our tools installed?

**Before Release:**
1. Have someone UNFAMILIAR with BSKG follow the getting started guide
2. Watch them (screen share) - don't help unless stuck > 5 minutes
3. Note every point of confusion
4. Fix documentation or code based on observations
5. Repeat until smooth

**CRITICAL:** First impressions matter. Broken install = users never return.

### 6.2 Known Limitations

| Limitation | Impact | Mitigation | Future Fix? |
|------------|--------|------------|-------------|
| Requires Slither | External dependency | Document clearly | N/A |
| Python 3.9+ only | Limited compatibility | Document requirements | N/A |
| No Windows native | Windows users need WSL | Document workaround | v4.1+ |
| Large install (~200MB) | Slow on slow connections | Optimize deps | v4.1+ |

### 6.3 What If Current Approach Fails?

**Trigger:** Fresh install fails on 2+ platforms

**Fallback Plan:**
1. Document issues clearly
2. Fix identified issues
3. Re-test on all platforms
4. If still failing: Release as 4.0.0-beta
5. Gather community feedback and iterate
6. Release 4.0.0 when stable

**Escalation:** Delay release until MUST platforms pass

---

## 7. ITERATION PROTOCOL

### 7.1 Success Measurement

| Checkpoint | Frequency | Pass Criteria | Action on Fail |
|------------|-----------|---------------|----------------|
| Unit tests | Every commit | 100% pass | Fix before proceeding |
| PyPI test | After 16.4 | Works on Test PyPI | Debug and fix |
| Docker test | After 16.5 | Works on 2+ platforms | Fix or skip platform |
| Fresh install | After 16.8 | Works on MUST platforms | Fix before release |
| User test | Before release | Succeeds without help | Improve docs |

### 7.2 Maximum Iterations

| Task Type | Max Iterations | Escalation |
|-----------|---------------|------------|
| Install fix | 5 | Delay release |
| Doc update | 3 | Accept limitation |
| Platform fix | 3 | Document limitation |

### 7.3 Iteration Log

| Date | Task | Issue | Action | Outcome |
|------|------|-------|--------|---------|
| [Date] | [Task] | [Issue] | [Action] | [Outcome] |

---

## 8. COMPLETION CHECKLIST

### 8.1 Exit Criteria

**MUST (Blockers for Release):**
- [ ] 16.0: All accounts set up and verified
- [ ] 16.1a-e: Core documentation complete
- [ ] 16.3: API finalized, mypy passes
- [ ] 16.4: PyPI package published and verified
- [ ] 16.8: Pre-release checklist passed
- [ ] 16.9: Fresh install passes on Ubuntu 22.04 + 1 other

**SHOULD (Before Announcing):**
- [ ] 16.5: Docker image published
- [ ] 16.6: GitHub release created
- [ ] 16.10: Pattern versioning working

**COULD (Nice to Have):**
- [ ] 16.7: GitHub Marketplace listing
- [ ] 16.11: CODEOWNERS defined

### 8.2 Artifacts Produced

| Artifact | Location | Purpose |
|----------|----------|---------|
| PyPI Package | pypi.org/project/alphaswarm | Primary distribution |
| Docker Image | hub.docker.com/r/truevkg/alphaswarm | Container distribution |
| GitHub Release | github.com/[org]/alphaswarm/releases | Release notes |
| Fresh Install Scripts | scripts/test_fresh_install_*.sh | Platform validation |
| Test Report | docs/release/test-report-4.0.md | Evidence of testing |

### 8.3 Post-Release Monitoring

**First 48 Hours:**
- Monitor GitHub issues
- Check PyPI download stats
- Review error reports
- Respond to questions quickly

**First Week:**
- Gather user feedback
- Track common issues
- Plan 4.0.1 patch if needed
- Update FAQ based on questions

---

## 9. APPENDICES

### 9.1 Account Information Template

```markdown
# BSKG Release Accounts (PRIVATE - Do not commit)

## PyPI
- Account: [username]
- 2FA: Enabled
- Trusted Publisher: Configured

## Docker Hub
- Account: [username]
- Organization: truevkg
- Repository: truevkg/alphaswarm

## GitHub
- Organization: [org]
- Repository: [org]/alphaswarm
- Release Environment: Configured
```

### 9.2 Release Checklist Summary

```markdown
## Pre-Release
[ ] All tests pass
[ ] Benchmark stable
[ ] Documentation complete
[ ] Version set to 4.0.0
[ ] CHANGELOG updated
[ ] Security reviewed

## Release
[ ] Test PyPI verified
[ ] Real PyPI published
[ ] Docker built and pushed
[ ] GitHub release created
[ ] Tags pushed

## Post-Release
[ ] Fresh install verified
[ ] Documentation accessible
[ ] Monitoring in place
```

---

*Phase 16 Tracker | Version 4.0 | 2026-01-07*
*Improved with brutal technical review*
*Task files in: `tasks/` directory*

---

## Alignment Addendum (Workstream P)

### Workstream P: Alignment Tasks

| ID | Objective | Start here | Dependencies | Deliverables | Validation | Conflicts | Spawn Triggers |
|----|-----------|------------|--------------|--------------|------------|-----------|----------------|
| P16.P.1 | Add philosophy sync to release checklist | `docs/PHILOSOPHY.md`, `task/4.0/phases/phase-16/TRACKER.md` | - | Release checklist update | Required before RC | Docs must stay aligned | New release checklist item |
| P16.P.2 | Add schema validation to packaged builds | `docs/PHILOSOPHY.md`, `src/true_vkg/` | P3.P.1 | Validation criteria | Included in release gate | Evidence packet versioned | Schema mismatch |

### Review Tasks (Required + Phase-Specific)

| ID | Objective | Start here | Dependencies | Deliverables | Validation | Conflicts | Spawn Triggers |
|----|-----------|------------|--------------|--------------|------------|-----------|----------------|
| P16.R.1 | Phase necessity review (keep/cut/modify) | `task/4.0/MASTER.md`, `docs/PHILOSOPHY.md` | - | Decision log in tracker | Decision referenced in alignment sweep | None | Phase outputs no longer needed |
| P16.R.2 | Task necessity review for P16.P.* | `task/4.0/phases/phase-16/TRACKER.md`, `task/codex/vkg_4_0_alignment_super_task.md` | P16.P.1-P16.P.2 | Task justification log | Each task has keep/merge decision | Avoid overlap with Phase 20 | Redundant task discovered |
| P16.R.3 | Conflict review with downstream phases | `task/4.0/MASTER.md` | P16.P.1-P16.P.2 | Conflict notes in tracker | Conflicts resolved or escalated | Tier A/Tier B separation | Conflict discovered |
| P16.R.4 | Ensure RC does not bypass Phase 20 gate | `task/4.0/MASTER.md` | P16.P.1 | Gate compliance note | Gate 4 enforced | No GA before Phase 20 | Gate bypass risk |

### Dynamic Task Spawning (Alignment)

**Trigger:** Schema mismatch in packaged build.
**Spawn:** Add schema migration task.
**Example spawned task:** P16.P.3 Add migration notes for a schema mismatch.
