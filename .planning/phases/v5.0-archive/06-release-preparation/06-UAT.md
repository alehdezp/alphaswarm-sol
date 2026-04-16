---
status: testing
phase: 06-release-preparation
source: [06-01-SUMMARY.md, 06-02-SUMMARY.md, 06-03-SUMMARY.md, 06-04-SUMMARY.md, 06-05-SUMMARY.md]
started: 2026-01-22T20:58:00Z
updated: 2026-01-22T20:58:00Z
---

## Current Test

number: 3
name: Build Knowledge Graph
expected: |
  Running `uv run alphaswarm build-kg tests/contracts/ReentrancyVuln.sol` builds a graph successfully and shows completion message with node/edge counts
awaiting: user response

## Tests

### 1. CLI Version Check
expected: Running `uv run alphaswarm --version` shows "AlphaSwarm.sol 0.5.0"
result: pass

### 2. Short Alias Works
expected: Running `uv run aswarm --version` shows same version output as alphaswarm
result: pass

### 3. Build Knowledge Graph
expected: Running `uv run alphaswarm build-kg tests/contracts/ReentrancyVuln.sol` builds a graph successfully and shows completion message with node/edge counts
result: [pending]

### 4. Query Graph
expected: Running `uv run alphaswarm query "FIND functions" --graph .vrs/graph.json` returns function results (or appropriate error if no graph)
result: [pending]

### 5. Agent Discovery File
expected: File `.vrs/AGENTS.md` exists and contains `vrs-` prefixed agent definitions (vrs-attacker, vrs-defender, vrs-verifier, etc.)
result: [pending]

### 6. No true_vkg References
expected: Running `grep -r "true_vkg" src/ --include="*.py" | head -5` returns no results (complete rebrand)
result: [pending]

### 7. Docker CLI Image Builds
expected: Running `docker build -t alphaswarm-test .` completes successfully (may take a while)
result: [pending]

### 8. Docker Image Runs Version
expected: After build, `docker run --rm alphaswarm-test --version` shows "AlphaSwarm.sol 0.5.0"
result: [pending]

### 9. MkDocs Builds
expected: Running `uv run mkdocs build` completes successfully (may show warnings but no errors)
result: [pending]

### 10. Documentation Pages Exist
expected: Files exist: `docs/index.md`, `docs/getting-started/installation.md`, `docs/reference/cli.md`
result: [pending]

### 11. GitHub Workflows Valid
expected: Files `.github/workflows/release.yml`, `.github/workflows/ci.yml`, `.github/workflows/docker.yml`, `.github/workflows/docs.yml` exist and are valid YAML
result: [pending]

### 12. Smoke Test Passes
expected: Running `./scripts/smoke_test.sh` shows all 8 tests passing
result: [pending]

### 13. Agent Discovery Tests Pass
expected: Running `uv run pytest tests/test_agent_discovery.py -v` shows all 14 tests passing
result: [pending]

## Summary

total: 13
passed: 2
issues: 0
pending: 11
skipped: 0

## Gaps

[none yet]
