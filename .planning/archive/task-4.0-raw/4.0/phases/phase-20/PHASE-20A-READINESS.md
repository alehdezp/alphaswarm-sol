# Phase 20.A: Readiness, Environment Control, Instrumentation

**Goal:** Make the test environment reproducible, observable, and auditable before final testing validation.

---

## A.1 Objectives

1. Freeze toolchain, dependencies, and dataset versions.
2. Establish a consistent execution environment (local + CI baseline).
3. Produce a single source of truth for test runs (commands, configs, logs).
4. Ensure Claude Code agent sessions are stable and repeatable.

---

## A.2 Inputs

- Completed phases 1-19.
- Local VulnDocs snapshots and knowledge store.
- Pattern packs and query system ready.
- Offline snapshot of target repos (remove `.git`).

---

## A.3 Output Artifacts

- `task/4.0/phases/phase-20/artifacts/ENVIRONMENT.md`
- `task/4.0/phases/phase-20/artifacts/RUNBOOK.md`

---

## A.4 Runbook (Mandatory)

Document every run with:
- Date/time
- Machine info (CPU, RAM, OS)
- Git commit/hash
- Environment variables
- Command line used
- Output files generated

**Rule:** If a run is not logged, it does not count.

---

## A.5 Readiness Checklist

- [ ] `uv sync` succeeds
- [ ] `uv run alphaswarm build-kg` works on at least one contract set
- [ ] `uv run alphaswarm query` returns expected results
- [ ] VulnDocs knowledge store readable
- [ ] Claude Code agent available and can access skills
- [ ] Logs directory exists: `task/4.0/phases/phase-20/logs/`

---

## A.6 Instrumentation Standards

- All logs stored in `task/4.0/phases/phase-20/logs/`
- Logs named `YYYY-MM-DD_testname_runX.log`
- Every test case gets a log file

Capture at minimum:
- Start/end timestamps
- Commands and tool outputs
- Errors and stack traces
- Agent reasoning snapshots (Claude Code)

---

## A.7 Agent Session Policy

- Use a dedicated Claude Code session for Phase 20.
- Disable any non-essential tools.
- Maintain a session transcript for each run.
- Explicitly log model names and tool selections.

---

## A.8 Failure Policy

- Missing dependency = **Blocker**
- Tool crash = **Critical**
- Missing logs = **Major**

Every failure must include:
- Root cause
- Reproduction steps
- Suggested remediation

---

## A.9 Artifact Initialization

Before any runs, ensure the following templates exist and are writable:

- `task/4.0/phases/phase-20/artifacts/ORCHESTRATION_TRACE.md`
- `task/4.0/phases/phase-20/artifacts/BEAD_LOG.md`
- `task/4.0/phases/phase-20/artifacts/PILLAR_COVERAGE.md`
