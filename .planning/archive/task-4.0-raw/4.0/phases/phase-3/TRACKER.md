# Phase 3: Basic CLI & Task System

**Status:** COMPLETE (17/17 tasks complete)
**Priority:** HIGH
**Last Updated:** 2026-01-08
**Author:** BSKG Team

---

## Quick Reference

| Field | Value |
|-------|-------|
| Entry Gate | Phase 2 complete (benchmarks working) |
| Exit Gate | LLM can discover BSKG and complete full audit workflow autonomously |
| Philosophy Pillars | Agentic Automation (LLM-usable CLI), NL Query (AGENTS.md discovery) |
| Threat Model Categories | Output stability for all attack surface detections |
| Estimated Hours | 58h |
| Actual Hours | TBD |
| Task Count | 16 tasks + 1 research task |
| Test Count Target | 40+ tests (CLI, schema, output validation) |

---

## 1. OBJECTIVES

### 1.1 Primary Objective

**Create CLI interface that AI coding agents (Claude Code, OpenCode, Cursor, etc.) can discover and use autonomously to complete a full vulnerability audit workflow.**

### 1.2 Secondary Objectives

1. **LLM Discoverability**: AGENTS.md enables tool discovery without prior context
2. **Findings Management**: Persistent task tracking across sessions
3. **Output Stability**: Versioned schemas, stable IDs, accurate locations
4. **Session Handoff**: New LLM sessions can resume audits seamlessly
5. **Evidence-First Output**: Every finding includes behavioral signatures and verification steps

### 1.3 Philosophy Alignment

| Pillar | How This Phase Contributes |
|--------|---------------------------|
| Knowledge Graph | CLI exposes graph queries to LLMs |
| NL Query System | AGENTS.md documents NL query capabilities |
| Agentic Automation | LLM can complete audit < 15 tool calls |
| Self-Improvement | Findings enable feedback collection |
| Task System (Beads) | Findings data model is foundation for Beads |

### 1.4 Success Metrics

| Metric | Target | Minimum | How to Measure |
|--------|--------|---------|----------------|
| Claude Code Discovery | Claude finds BSKG in fresh session | - | Manual test |
| OpenCode Discovery | OpenCode finds BSKG in fresh session | - | Manual test |
| Workflow Completion | < 15 tool calls for audit | < 20 | Count in test |
| SARIF Validation | GitHub accepts output | - | Upload test |
| Schema Validation | 100% outputs validated | 95% | CI check |
| Location Accuracy | file:line:column | file:line | Test contracts |

### 1.5 Non-Goals (Explicit Scope Boundaries)

- **NOT building scaffolds**: Scaffold generation is Phase 4
- **NOT LLM integration**: Tier B analysis is Phase 11
- **NOT metrics dashboard**: Metrics are Phase 8
- **NOT learning system**: Learning is Phase 7
- **NOT MCP integration**: MCP is Phase 13

---

## 2. RESEARCH REQUIREMENTS

### 2.1 Required Research Before Implementation

| ID | Research Topic | Output | Est. Hours | Status |
|----|---------------|--------|------------|--------|
| R3.1 | LLM Tool Discovery Patterns | Best practices for AGENTS.md | 3h | ✅ DONE |
| R3.2 | OpenCode SDK Integration | SDK capabilities, config patterns | 2h | ✅ DONE |
| R3.3 | Codex Noninteractive Mode | `codex exec` for CI/CD pipelines | 2h | ✅ DONE |

### 2.2 Knowledge Gaps

- [ ] How do LLMs discover available tools?
- [ ] What makes AGENTS.md effective?
- [ ] What command patterns are LLM-friendly?
- [ ] How to structure error messages for LLM recovery?
- [ ] How does OpenCode discover and use CLI tools?
- [ ] What config file format does OpenCode use for tool integration?
- [ ] Codex `codex exec` output format for BSKG integration?
- [ ] Codex `--output-schema` for structured finding output?
- [ ] Codex `codex exec resume` for multi-stage audits?

### 2.3 External References

| Reference | URL/Path | Purpose |
|-----------|----------|---------|
| SARIF 2.1.0 Spec | sarifweb.azurewebsites.net | Schema compliance |
| Claude Tool Use | docs.anthropic.com | LLM patterns |
| OpenCode SDK Docs | opencode.ai/docs/sdk/ | OpenCode integration |
| OpenCode Providers | opencode.ai/docs/providers/ | 75+ LLM providers |
| Codex Noninteractive | developers.openai.com/codex/noninteractive | CLI automation mode |
| AGENTS.md Examples | Various projects | Best practices |

### 2.4 Research Completion Criteria

- [ ] Research task R3.1 completed
- [ ] AGENTS.md structure finalized
- [ ] Error message patterns documented

---

## 3. TASK DECOMPOSITION

### 3.1 Task Dependency Graph

```
R3.1 (Research) ──┬── 3.1 (AGENTS.md)
                  │          │
                  │          ▼
                  │       3.3 (Findings CLI)
                  │          │
                  │    ┌─────┴─────┬─────────┐
                  │    ▼           ▼         ▼
                  │  3.4         3.5       3.6
                  │  (Priority)  (Handoff) (SARIF)
                  │
                  ├── 3.2 (Findings Data Model) ← Independent
                  ├── 3.7 (Error Quality) ← Independent
                  ├── 3.8 (LLM Integration Test) ← After all above
                  │
                  ├── WORKSTREAM: Output Stability
                  │   3.9 → 3.10 → 3.11 → 3.12 → 3.13 → 3.14 → 3.15 → 3.16
                  │
```

### 3.2 Task Registry

#### Core CLI Tasks (3.1-3.8)

| ID | Task | Est. | Priority | Depends On | Status | Validation |
|----|------|------|----------|------------|--------|------------|
| R3.1 | Research LLM patterns | 3h | - | - | ✅ DONE | Best practices doc |
| R3.2 | Research OpenCode SDK | 2h | - | - | ✅ DONE | [R3.2-OPENCODE-SDK-RESEARCH.md](R3.2-OPENCODE-SDK-RESEARCH.md) |
| 3.1 | AGENTS.md Generation | 4h | MUST | R3.1 | ✅ DONE | [Detailed Task](tasks/3.1-agents-md.md) |
| 3.1b | OpenCode Config Generation | 3h | MUST | R3.2 | ✅ DONE | 39 tests, `vkg init --opencode` |
| 3.2 | Findings Data Model | 4h | MUST | - | ✅ DONE | 51 tests, [Detailed Task](tasks/3.2-findings-data-model.md) |
| 3.3 | Findings CLI Commands | 6h | MUST | 3.2 | ✅ DONE | 28 tests, [Detailed Task](tasks/3.3-findings-cli.md) |
| 3.4 | Priority Queue Logic | 3h | MUST | 3.3 | ✅ DONE | Included in 3.2/3.3 |
| 3.5 | Session Handoff | 4h | MUST | 3.3 | ✅ DONE | `vkg findings status` command |
| 3.6 | SARIF Report Output | 4h | MUST | 3.3 | ✅ DONE | SARIF 2.1.0, included in export cmd |
| 3.7 | Error Message Quality | 3h | SHOULD | - | ✅ DONE | 21 tests, errors.py module |
| 3.8 | LLM Integration Test | 4h | MUST | All above | ✅ DONE | 7 tests, < 15 tool calls |
| 3.8b | OpenCode Integration Test | 3h | MUST | 3.1b, 3.8 | ✅ DONE | 66 tests, `test_opencode_integration.py` |
| 3.8c | Codex Noninteractive Test | 3h | SHOULD | R3.3 | ✅ DONE | 63 tests, `test_codex_integration.py` |
| 3.17 | BSKG Output Schema for Codex | 3h | SHOULD | R3.3 | ✅ DONE | 58 tests, `schemas/vkg-codex-output.json` |

#### Output Stability Tasks (3.9-3.16)

| ID | Task | Est. | Priority | Depends On | Status | Validation |
|----|------|------|----------|------------|--------|------------|
| 3.9 | Output Schema Versioning | 3h | MUST | - | ✅ DONE | FINDING_SCHEMA_VERSION in model |
| 3.10 | Tier Labels in Findings | 2h | MUST | 3.2 | ✅ DONE | FindingTier enum (tier_a/tier_b) |
| 3.11 | Location Stability | 4h | MUST | - | ✅ DONE | file:line:column, format_range(), is_valid() |
| 3.12 | Build Failure Diagnostics | 4h | SHOULD | - | ✅ DONE | 7 diagnostic functions in errors.py |
| 3.13 | Proxy Resolution Enforcement | 4h | MUST | - | ✅ DONE | ERC-1967/ERC-2535 resolution required or explicit block |
| 3.14 | Evidence-First Output | 4h | MUST | 3.2 | ✅ DONE | EvidenceRef, why_vulnerable, attack_scenario |
| 3.15 | Verification Checklist | 3h | SHOULD | 3.14 | ✅ DONE | 24 tests, pattern-specific generators |
| 3.16 | Pattern Taxonomy Mapping (SWC, CWE) | 3h | SHOULD | - | ✅ DONE | 42 tests, 80+ patterns mapped |

### 3.3 Dynamic Task Spawning

**Tasks may be added during execution when:**
- LLM testing reveals confusion points
- SARIF validation reveals missing fields
- Error messages prove insufficient

**Process for adding tasks:**
1. Document reason for new task
2. Assign ID: 3.X where X is next available (17+)
3. Update this registry
4. Re-estimate phase completion

### 3.4 Task Details

#### Task 3.1: AGENTS.md Generation

**Objective:** LLM can discover BSKG without prior hints

**Implementation:**
```bash
vkg init  # Generates .vrs/AGENTS.md
```

**AGENTS.md Content:**
```markdown
# BSKG - Solidity Vulnerability Detector

## Quick Start
vkg build contracts/     # Build knowledge graph
vkg analyze              # Find vulnerabilities
vkg findings list        # See all findings
vkg findings next        # Get next priority finding

## Available Commands
| Command | Purpose | When to Use |
|---------|---------|-------------|
| `vkg build <path>` | Build graph | First step |
| `vkg analyze` | Run detection | After build |
| `vkg findings list` | List findings | See overview |
| `vkg findings next` | Priority finding | Start investigation |
| `vkg findings show <id>` | Show details | Investigate specific |
| `vkg findings update <id>` | Update verdict | After investigation |
| `vkg report --format sarif` | Generate report | End of audit |

## Workflow
1. `vkg build contracts/`
2. `vkg analyze`
3. For each: `vkg findings next` → investigate → `vkg findings update`
4. `vkg report --format sarif`
```

**Validation Criteria:**
- [ ] Claude discovers BSKG in fresh session
- [ ] Workflow completable with just AGENTS.md
- [ ] Commands are idempotent

**Estimated Hours:** 4h

---

#### Task 3.2: Findings Data Model

**Objective:** Persistent finding tracking across sessions

**Schema:**
```python
@dataclass
class Finding:
    id: str                    # VKG-001
    pattern_id: str            # vm-001
    tier: str                  # tier_a or tier_b
    contract: str              # Vault.sol
    function: str              # withdraw
    line: int                  # 45
    column: int                # 9
    severity: str              # critical, high, medium, low
    confidence: float          # 0.0-1.0
    behavioral_signature: str  # R:bal→X:out→W:bal
    description: str           # What was detected
    evidence: List[Evidence]   # Code snippets, properties
    status: str                # pending, investigating, confirmed, rejected
    notes: List[str]           # Investigation notes
    verdict_reason: str        # Why confirmed/rejected
```

**Storage:**
```
.vrs/findings/
├── index.json      # Summary of all findings
├── VKG-001.json    # Full finding detail
├── VKG-002.json
└── ...
```

**Validation Criteria:**
- [ ] Findings survive `vkg build`
- [ ] Old findings marked stale on graph change
- [ ] JSON is human-readable

**Estimated Hours:** 4h

---

#### Task 3.14: Evidence-First Finding Output

**Objective:** Each finding includes behavioral signature and verification steps

**Specification:** See [docs/architecture/two-layer-output.md](../../../docs/architecture/two-layer-output.md)

**Finding Output Schema:**
```json
{
  "id": "VKG-001",
  "pattern_id": "reentrancy-classic",
  "tier": "tier_a",
  "behavioral_signature": "R:bal→X:out→W:bal",
  "location": {
    "file": "Vault.sol",
    "line": 45,
    "column": 9,
    "function": "withdraw"
  },
  "evidence": [
    {"type": "code", "ref": "Vault.sol:45-52", "snippet": "..."},
    {"type": "property", "name": "state_write_after_external_call", "value": true}
  ],
  "why_vulnerable": "External call transfers ETH before balance update",
  "minimal_repro_steps": [
    "1. Attacker deposits funds",
    "2. Attacker calls withdraw()",
    "3. In receive(), attacker re-enters withdraw()",
    "4. Balance not yet decremented, full amount withdrawn again"
  ]
}
```

**Validation Criteria:**
- [ ] Behavioral signature in every finding
- [ ] Evidence array with code refs
- [ ] Why vulnerable explanation
- [ ] Minimal reproduction steps
- [ ] CI: 100% of findings have non-empty behavioral_signature

**Estimated Hours:** 4h

---

## 4. TEST SUITE REQUIREMENTS

### 4.1 Test Categories

| Category | Count Target | Location |
|----------|--------------|----------|
| AGENTS.md Generation | 5 | `tests/test_agents_md.py` |
| Findings CRUD | 12 | `tests/test_findings_cli.py` |
| SARIF Output | 8 | `tests/test_sarif.py` |
| Schema Validation | 10 | `tests/test_output_schema.py` |
| Evidence-First | 8 | `tests/test_evidence_first.py` |
| **Total** | **43** | - |

### 4.2 Test Matrix

| Feature | Happy Path | Edge Cases | Error Cases | Regression |
|---------|-----------|------------|-------------|------------|
| AGENTS.md | TODO | TODO | TODO | TODO |
| Findings CLI | TODO | TODO | TODO | TODO |
| SARIF Output | TODO | TODO | TODO | TODO |
| Schema Validation | TODO | TODO | TODO | TODO |
| Evidence Output | TODO | TODO | TODO | TODO |
| Location Stability | TODO | TODO | TODO | TODO |

### 4.3 Test Fixtures

| Fixture | Purpose | Location |
|---------|---------|----------|
| Sample contracts | CLI testing | `tests/contracts/cli/` |
| Expected SARIF | Validation | `tests/fixtures/sarif/` |
| Schema files | Validation | `schemas/` |

### 4.4 Test Commands

```bash
# All Phase 3 tests
uv run pytest tests/test_agents_md.py tests/test_findings_cli.py tests/test_sarif.py tests/test_output_schema.py tests/test_evidence_first.py -v

# SARIF validation
vkg report --format sarif | jq . > test.sarif
# Upload to GitHub Security tab for validation
```

---

## 5. IMPLEMENTATION GUIDELINES

### 5.1 Code Standards

- [ ] Type hints on all public functions
- [ ] Docstrings with examples
- [ ] Schema validation on all outputs
- [ ] Error messages guide recovery

### 5.2 File Locations

| Component | Location | Purpose |
|-----------|----------|---------|
| CLI entry | `src/true_vkg/cli/main.py` | Command routing |
| Findings module | `src/true_vkg/findings/` | CRUD operations |
| SARIF generator | `src/true_vkg/report/sarif.py` | Report output |
| AGENTS.md template | `src/true_vkg/templates/` | Discovery |
| Schemas | `schemas/` | Validation |

### 5.3 Dependencies

| Dependency | Version | Purpose | Optional? |
|------------|---------|---------|-----------|
| click | existing | CLI framework | No |
| jsonschema | existing | Schema validation | No |
| sarif-tools | TBD | SARIF validation | No |

### 5.4 Configuration

```yaml
# ~/.vrs/config.yaml
cli:
  output_format: json  # json, toon
  color: auto
  verbose: false

findings:
  storage_path: .vrs/findings/
  auto_refresh: true

report:
  sarif_version: "2.1.0"
  include_completeness: true
```

---

## 6. REFLECTION PROTOCOL

### 6.1 Brutal Self-Critique Checklist

**Answer after each task:**

- [ ] Does this actually work on real-world code, not just test fixtures?
- [ ] Would a skeptical reviewer find obvious flaws?
- [ ] Are we testing the right thing, or just what's easy to test?
- [ ] Does this add unnecessary complexity?
- [ ] Could this be done simpler?
- [ ] Are we measuring what matters, or what's convenient?
- [ ] Would this survive adversarial input?
- [ ] Is the documentation accurate, or aspirational?

### 6.2 Known Limitations

| Limitation | Impact | Mitigation | Future Fix? |
|------------|--------|------------|-------------|
| SARIF line-only locations | Some IDEs need column | Add column in 3.11 | This phase |
| Schema v1 may change | Breaking changes | Versioning in 3.9 | Ongoing |
| No proxy resolution | Missed vulns | Warning in 3.13 | Phase 5 |

### 6.3 Alternative Approaches Considered

| Approach | Pros | Cons | Why Not Chosen |
|----------|------|------|----------------|
| Single-file findings | Simple | No history | Need versioning |
| Database storage | Scalable | Complexity | JSON is sufficient |
| No AGENTS.md | Less maintenance | LLM can't discover | Discovery critical |
| Custom report format | Flexible | No ecosystem | SARIF is standard |

### 6.4 What If Current Approach Fails?

**Trigger:** If LLM can't complete workflow in 3 test sessions

**Fallback Plan:**
1. Simplify AGENTS.md further
2. Reduce command count
3. Add more examples
4. Consider guided mode

**Escalation:** User testing with real auditors

---

## 7. ITERATION PROTOCOL

### 7.1 Success Measurement

| Checkpoint | Frequency | Pass Criteria | Action on Fail |
|------------|-----------|---------------|----------------|
| Unit tests | Every commit | 100% pass | Fix immediately |
| LLM test | Per task | < 20 tool calls | Simplify interface |
| SARIF valid | Per PR | GitHub accepts | Fix schema |
| Schema valid | Per PR | 100% outputs | Add validation |

### 7.2 Iteration Triggers

**Iterate (same approach):**
- LLM test takes 16-20 calls instead of < 15
- SARIF missing optional fields
- Error messages unclear

**Re-approach (different approach):**
- LLM test takes > 30 calls
- Fundamental confusion about workflow
- SARIF schema incompatible

### 7.3 Maximum Iterations

| Task Type | Max Iterations | Escalation |
|-----------|---------------|------------|
| CLI command | 3 | Simplify scope |
| Output format | 2 | Use standard |
| LLM integration | 5 | User testing |

### 7.4 Iteration Log

| Date | Task | Issue | Action | Outcome |
|------|------|-------|--------|---------|
| - | - | - | - | - |

---

## 8. COMPLETION CHECKLIST

### 8.1 Exit Criteria

- [ ] `vkg init` generates usable AGENTS.md
- [ ] All findings CLI commands work
- [ ] Session handoff enables resumption
- [ ] SARIF output accepted by GitHub
- [ ] Fresh Claude Code session completes audit
- [ ] Output schema versioning implemented
- [ ] Tier labels in all findings
- [ ] Location includes column
- [ ] Proxy resolution enforced
- [ ] Evidence-first output with behavioral signatures
- [ ] Verification checklist per finding

### 8.2 Artifacts Produced

| Artifact | Location | Purpose |
|----------|----------|---------|
| CLI commands | `src/true_vkg/cli/` | User interface |
| Findings module | `src/true_vkg/findings/` | Data management |
| SARIF generator | `src/true_vkg/report/sarif.py` | Reporting |
| Schemas | `schemas/*.json` | Validation |
| AGENTS.md template | `src/true_vkg/templates/` | Discovery |

### 8.3 Metrics Progress

| Metric | Target | Current | Notes |
|--------|--------|---------|-------|
| LLM Tool Calls | < 15 | ✅ 11 calls | Task 3.8 complete |
| SARIF Validation | Pass | ✅ Pass | SARIF 2.1.0 export |
| Schema Coverage | 100% | ✅ 100% | Schema versioning implemented |
| Tasks Complete | 17/17 | 17/17 | All tasks complete including OpenCode/Codex integration |
| Tests Added | 40+ | 451 | Exceeds target (225 base + 39 opencode + 58 codex + 66 opencode-int + 63 codex-int) |

### 8.4 Lessons Learned

_[To be filled on completion]_

### 8.5 Recommendations for Future Phases

1. **Phase 4**: Use findings schema for scaffold generation
2. **Phase 6**: Extend findings to Beads
3. **Phase 8**: Track CLI usage metrics
4. **Phase 11**: LLM uses same CLI for Tier B

---

## 9. APPENDICES

### 9.1 SARIF Schema Requirements

```json
{
  "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
  "version": "2.1.0",
  "runs": [{
    "tool": {
      "driver": {
        "name": "VKG",
        "version": "4.0.0",
        "informationUri": "https://github.com/...",
        "rules": [...]
      }
    },
    "results": [...]
  }]
}
```

### 9.2 Error Message Pattern

```
Error: [What went wrong]

Location: [Where it happened]
Details: [Why it happened]

Fix: [Primary solution]

If this persists:
  1. [Alternative 1]
  2. [Alternative 2]
  3. [Get help]: vkg --help
```

### 9.3 Troubleshooting Guide

| Problem | Cause | Solution |
|---------|-------|----------|
| Claude doesn't find BSKG | No AGENTS.md | Run `vkg init` |
| Findings disappear | Graph rebuilt | Check .vrs/findings/ |
| SARIF invalid | Schema mismatch | Update vkg version |
| Stale findings | Code changed | Run `vkg findings refresh` |

---

*Phase 3 Tracker | Version 3.0 | 2026-01-07*
*Template: PHASE_TEMPLATE.md v1.0*
*Status: BLOCKED (by Phase 2)*

---

## Alignment Addendum (Workstream P)

### Workstream P: Alignment Tasks

| ID | Objective | Start here | Dependencies | Deliverables | Validation | Conflicts | Spawn Triggers |
|----|-----------|------------|--------------|--------------|------------|-----------|----------------|
| P3.P.1 | Enforce evidence packet fields in CLI JSON/SARIF outputs | `docs/PHILOSOPHY.md`, `src/true_vkg/cli.py` | P1.P.1 | Output contract + schema versioning notes | Schema validation test list | JSON canonical; schema versioned | New output format |
| P3.P.2 | Define stable finding IDs + SARIF fingerprints | `docs/PHILOSOPHY.md`, `src/true_vkg/enterprise/reports.py` | P1.P.2 | ID spec + SARIF fingerprint mapping | Rerun stability criteria | Determinism applies Tier A only | ID collision or drift |
| P3.P.3 | Add convoy/hook CLI commands and outputs | `docs/PHILOSOPHY.md`, `src/true_vkg/cli.py` | - | CLI command list + output fields | CLI routing output tests | Keep Tier A/Tier B separate | New convoy type |
| P3.P.4 | Enforce proxy/upgradeability resolution outputs | `docs/PHILOSOPHY.md`, `src/true_vkg/cli.py` | - | Resolution mode definitions | Proxy tests required | Proxy resolution is required, not warning | New proxy standard |
| P3.P.5 | Define early LLM safety controls and schema gates | `docs/PHILOSOPHY.md`, `task/4.0/protocols/TEST-SANDBOX.md` | - | LLM safety checklist in tracker | Referenced by Phase 11 tasks | Context minimization required | New LLM provider |

### Review Tasks (Required + Phase-Specific)

| ID | Objective | Start here | Dependencies | Deliverables | Validation | Conflicts | Spawn Triggers |
|----|-----------|------------|--------------|--------------|------------|-----------|----------------|
| P3.R.1 | Phase necessity review (keep/cut/modify) | `task/4.0/MASTER.md`, `docs/PHILOSOPHY.md` | - | Decision log in tracker | Decision referenced in alignment sweep | None | Phase outputs no longer needed |
| P3.R.2 | Task necessity review for P3.P.* | `task/4.0/phases/phase-3/TRACKER.md`, `task/codex/vkg_4_0_alignment_super_task.md` | P3.P.1-P3.P.5 | Task justification log | Each task has keep/merge decision | Avoid overlap with Phase 9 | Redundant task discovered |
| P3.R.3 | Conflict review with downstream phases | `task/4.0/MASTER.md` | P3.P.1-P3.P.5 | Conflict notes in tracker | Conflicts resolved or escalated | Tier A/Tier B separation | Conflict discovered |
| P3.R.4 | Confirm evidence packet contract covers bucket + rationale | `docs/PHILOSOPHY.md`, `task/4.0/phases/phase-3/TRACKER.md` | P3.P.1 | Contract coverage note | Referenced by CLI schema | No missing rationale fields | Missing field discovered |
| P3.R.5 | Conflict check with Phase 9 PPR formats | `task/4.0/phases/phase-9/TRACKER.md` | P3.P.1, P9.P.1 | Format compatibility note | No duplicate formats | JSON canonical conflict | New format added |

### Dynamic Task Spawning (Alignment)

**Trigger:** New output format or client integration.
**Spawn:** Add schema extension task + compatibility tests.
**Example spawned task:** P3.P.6 Add evidence packet mapping for a new output format (e.g., SARIF extension).
