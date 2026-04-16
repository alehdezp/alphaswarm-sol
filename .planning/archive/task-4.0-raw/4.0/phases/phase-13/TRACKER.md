# Phase 13: Grimoires & Skills

**Status:** ✅ COMPLETE (9 grimoires, 4 investigation patterns, 138 tests)
**Priority:** MEDIUM - Per-vulnerability testing playbooks
**Last Updated:** 2026-01-08
**Author:** BSKG Team

---

## Quick Reference

| Field | Value |
|-------|-------|
| Entry Gate | Phase 12 complete (Agent SDK micro-agents work) |
| Exit Gate | Grimoires exist for top 10 vulnerability classes, skills are invocable |
| Philosophy Pillars | Skills & Grimoires, Multi-Agent Debate, Agentic Automation |
| Threat Model Categories | All (Grimoires cover each attack surface) |
| Estimated Hours | 60h |
| Actual Hours | [Tracked as work progresses] |
| Task Count | 12 tasks |
| Test Count Target | 70+ tests |

---

## 1. OBJECTIVES

### 1.1 Primary Objective

Create **Grimoires** - per-vulnerability testing playbooks that encode expert knowledge for how to properly verify, test, and exploit each vulnerability class. Each grimoire is a skill that LLM agents can invoke.

### 1.2 Secondary Objectives

1. Create grimoires for top 10 vulnerability classes
2. Make grimoires invocable as skills (`/test-reentrancy`, `/verify-access-control`)
3. Enable subagent spawning for complex verification procedures
4. Provide cost-transparent grimoire execution
5. Support manual and automated grimoire invocation

### 1.3 Philosophy Alignment

| Pillar | How This Phase Contributes |
|--------|---------------------------|
| Knowledge Graph | Grimoires query graph for context |
| NL Query System | N/A |
| Agentic Automation | Core focus - grimoires ARE agentic verification |
| Self-Improvement | Grimoire results feed back to pattern confidence |
| Task System (Beads) | Grimoire results update task status |
| Skills & Grimoires | **THIS IS THE CORE PILLAR** |

### 1.4 Success Metrics

| Metric | Target | Minimum | How to Measure |
|--------|--------|---------|----------------|
| Grimoire Coverage | 10 vuln classes | 5 classes | Count of grimoires |
| Verification Accuracy | >= 85% | >= 70% | Grimoire verdict vs manual review |
| Test Compilation Rate | >= 80% | >= 60% | Generated tests that compile |
| Skill Invocability | 100% | 100% | All grimoires callable as skills |

### 1.5 Non-Goals (Explicit Scope Boundaries)

- Grimoires are NOT fully autonomous - human review still needed
- No custom LLM training (use prompts + context)
- No grimoire persistence across sessions (use Beads for that)
- Grimoires don't replace multi-agent debate, they FEED it

### 1.6 Grimoire = Bead + Tools + Procedure

**A Grimoire is a complete testing playbook powered by Beads and pre-configured tools:**

```
┌─────────────────────────────────────────────────────────────────┐
│  GRIMOIRE STRUCTURE                                             │
│  Per-vulnerability testing playbook                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  CONTEXT (from VulnerabilityBead)                              │
│  ├── Code context (vulnerable function + dependencies)         │
│  ├── Pattern context (why flagged, evidence)                   │
│  ├── Historical exploits (real-world examples)                 │
│  └── Investigation steps (what to check)                       │
│                                                                 │
│  TOOLS (pre-configured, ready to use)                          │
│  ├── Foundry test scaffold (ready-to-run)                      │
│  ├── Medusa fuzzing config (property-based)                    │
│  ├── Fork RPC (mainnet state for testing)                      │
│  ├── Testnet deployment (live testing)                         │
│  └── Graph queries (deeper analysis)                           │
│                                                                 │
│  PROCEDURE (category-specific expert steps)                     │
│  ├── Step 1: Initial verification (static checks)              │
│  ├── Step 2: Test generation (exploit construction)            │
│  ├── Step 3: Execution (run tests, fuzzing)                    │
│  ├── Step 4: Analysis (interpret results)                      │
│  └── Step 5: Verdict (confirm/refute/uncertain)                │
│                                                                 │
│  SKILLS (invocable actions)                                     │
│  ├── /run-test: Execute the generated test                     │
│  ├── /fuzz: Run fuzzing campaign                               │
│  ├── /fork-test: Test on mainnet fork                          │
│  ├── /deploy-testnet: Deploy for live testing                  │
│  └── /simulate: Tenderly transaction simulation                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Grimoire Invocation:**
```bash
# Invoke grimoire as skill (agent can call this)
/test-reentrancy --finding <finding-id>

# What happens:
# 1. Load VulnerabilityBead for finding
# 2. Load reentrancy grimoire procedure
# 3. Execute procedure steps with available tools
# 4. Return verdict with evidence
```

**Per-Category Grimoires:**

| Grimoire | Skill | Tools Used | Key Tests |
|----------|-------|------------|-----------|
| Reentrancy | `/test-reentrancy` | Foundry, fork | CEI order, guard presence, callback |
| Access Control | `/test-access` | Foundry, fuzz | Auth bypass, role escalation |
| Oracle | `/test-oracle` | Foundry, fork | Staleness, manipulation |
| DoS | `/test-dos` | Medusa, fuzz | Unbounded loops, gas limits |
| MEV | `/test-mev` | Fork, simulate | Sandwich, frontrun |
| Token | `/test-token` | Foundry, fuzz | Return values, fee-on-transfer |
| Upgrade | `/test-upgrade` | Foundry | Storage collision, initializer |

**Grimoire Procedure Example (Reentrancy):**
```yaml
# grimoires/reentrancy.yaml
id: grimoire-reentrancy
name: Reentrancy Testing Grimoire
skill: /test-reentrancy
category: reentrancy

procedure:
  - step: 1
    name: Static Verification
    action: check_graph
    queries:
      - "Has reentrancy guard?"
      - "CEI order correct?"
      - "External calls before state writes?"

  - step: 2
    name: Generate Exploit Test
    action: generate_test
    template: foundry_reentrancy
    tools: [foundry]

  - step: 3
    name: Run Test
    action: execute
    command: forge test --match-test testReentrancy -vvv
    tools: [foundry]

  - step: 4
    name: Fuzz for Edge Cases
    action: fuzz
    tool: medusa
    config: medusa_reentrancy.yaml
    duration: 60s

  - step: 5
    name: Fork Test (Real State)
    action: fork_test
    rpc: ${FORK_RPC}
    block: latest
    tools: [anvil]

  - step: 6
    name: Analyze & Verdict
    action: analyze
    outputs: [test_results, fuzz_results, fork_results]
    verdict_rules:
      - if: test_passes_exploit
        then: VULNERABLE
      - if: fuzz_finds_violation
        then: VULNERABLE
      - if: all_tests_pass_safe
        then: SAFE
      - else: UNCERTAIN
```

---

## 2. RESEARCH REQUIREMENTS

### 2.1 Required Research Before Implementation

| ID | Research Topic | Output | Est. Hours | Status |
|----|---------------|--------|------------|--------|
| R13.1 | Expert Verification Procedures | Per-vuln verification steps | 4h | DONE |
| R13.2 | Skill Framework Patterns | Skill invocation patterns | 2h | DONE |

### 2.2 Knowledge Gaps

- [ ] What are the expert verification steps for each vulnerability class?
- [ ] How to structure grimoire prompts for best LLM performance?
- [ ] What context does each grimoire need from the graph?
- [ ] How to handle grimoire failures gracefully?

### 2.3 External References

| Reference | URL/Path | Purpose |
|-----------|----------|---------|
| Audit Reports | Solodit, Code4rena | Verification procedures |
| Foundry Book | [book.getfoundry.sh](https://book.getfoundry.sh) | Test generation |
| Trail of Bits Guidelines | [ToB blog](https://blog.trailofbits.com) | Security testing |
| Claude Agent SDK | anthropic.com/docs/agent-sdk | Grimoire subagent spawning |
| Codex SDK | developers.openai.com/codex/sdk/ | Alternative subagent provider |
| OpenCode SDK | opencode.ai/docs/sdk/ | 75+ provider access |

### 2.4 Research Completion Criteria

- [ ] Verification procedures documented for top 10 vuln classes
- [ ] Skill framework pattern selected
- [ ] Findings documented in `phases/phase-13/research/`

---

## 3. TASK DECOMPOSITION

### 3.1 Task Dependency Graph

```
R13.1 ── R13.2 ── 13.1 (Grimoire Schema)
                       │
                       ├── 13.2 (Reentrancy Grimoire)
                       ├── 13.3 (Access Control Grimoire)
                       ├── 13.4 (Oracle Manipulation Grimoire)
                       ├── 13.5 (Flash Loan Grimoire)
                       ├── 13.6 (MEV Grimoire)
                       │
                       └── 13.7 (Skill Invocation System)
                                │
                                └── 13.8 (Cost Tracking) ── 13.9 (Integration Test)
                                                                    │
                                                            13.10 (Additional Grimoires)
```

### 3.2 Task Registry

| ID | Task | Est. | Priority | Depends On | Status | Validation |
|----|------|------|----------|------------|--------|------------|
| R13.1 | Expert Verification Research | 4h | MUST | - | ✅ DONE | Procedures documented |
| R13.2 | Skill Framework Research | 2h | MUST | R13.1 | ✅ DONE | Framework selected |
| 13.1 | Grimoire Schema | 3h | MUST | R13.2 | ✅ DONE | Schema defined (schema.py) |
| 13.2 | Reentrancy Grimoire | 4h | MUST | 13.1 | ✅ DONE | reentrancy.json |
| 13.3 | Access Control Grimoire | 4h | MUST | 13.1 | ✅ DONE | access_control.json |
| 13.4 | Oracle Manipulation Grimoire | 4h | MUST | 13.1 | ✅ DONE | oracle.json |
| 13.5 | Flash Loan Grimoire | 4h | MUST | 13.1 | ✅ DONE | flash_loan.json |
| 13.6 | DoS Grimoire | 4h | SHOULD | 13.1 | ✅ DONE | dos.json |
| 13.7 | Skill Invocation System | 4h | MUST | 13.2 | ✅ DONE | skill.py |
| 13.8 | Cost Tracking | 2h | MUST | 13.7 | ✅ DONE | cost.py (20 tests) |
| 13.9 | Integration Test | 3h | MUST | 13.8 | ✅ DONE | 87 tests passing |
| 13.10 | Additional Grimoires | 6h | SHOULD | 13.9 | ✅ DONE | mev.json, token.json, upgrade.json, crypto.json |
| 13.11 | LLM Investigation Patterns | 20h | **MUST** | 13.0, 11.16, 9.1 | ✅ DONE | 51 tests, 4 investigation patterns |

### 3.3 Task Details

#### Task R13.1: Expert Verification Research

**Objective:** Document expert verification procedures for each vulnerability class

**Vulnerability Classes to Cover:**
1. Reentrancy (classic, cross-function, read-only)
2. Access Control (missing gates, permissive gates, privilege escalation)
3. Oracle Manipulation (stale prices, TWAP manipulation, sandwich attacks)
4. Flash Loan Attacks (reward draining, governance manipulation)
5. MEV Vulnerabilities (sandwich, frontrunning, backrunning)
6. Upgrade Safety (uninitialized proxy, storage collision, selfdestruct)
7. Token Issues (fee-on-transfer, rebasing, ERC777 hooks)
8. DoS (unbounded loops, block gas limit, strict equality)
9. Cryptographic Issues (signature malleability, ecrecover zero)
10. Business Logic (invariant violations, economic attacks)

**Deliverables:**
- Per-class verification procedure document
- Required graph context per class
- Expected test patterns per class

**Estimated Hours:** 4h
**Actual Hours:** [Tracked]

---

#### Task 13.1: Grimoire Schema

**Objective:** Define the schema for grimoire definitions

**Schema:**
```yaml
# grimoires/reentrancy.yaml
id: grimoire-reentrancy
name: Reentrancy Verification Grimoire
description: |
  Expert procedure for verifying reentrancy vulnerabilities.
  Generates Foundry tests, runs them, interprets results.

vulnerability_classes:
  - reentrancy-classic
  - reentrancy-cross-function
  - reentrancy-read-only

required_context:
  - function_code
  - external_call_sites
  - state_writes_after_calls
  - reentrancy_guard_status
  - call_graph_1_hop

steps:
  - name: analyze_call_pattern
    description: Identify the external call and state modification ordering
    type: analysis
    prompt: |
      Analyze this function for reentrancy:

      ## Function Code
      {function_code}

      ## External Call Sites
      {external_call_sites}

      ## State Writes After External Calls
      {state_writes_after_calls}

      Identify:
      1. Which external call could be exploited?
      2. What state is modified after the call?
      3. Is there a reentrancy guard?

  - name: generate_test
    description: Generate Foundry test with malicious callback
    type: code_generation
    prompt: |
      Generate a Foundry test that exploits the reentrancy in:

      {function_code}

      The test should:
      1. Deploy an attacker contract with receive()/fallback()
      2. Call the vulnerable function
      3. Reenter in the callback
      4. Assert funds were drained

    output_file: test_{function_name}_reentrancy.t.sol

  - name: run_test
    description: Execute the generated test
    type: bash
    command: forge test -vvv --match-test test_{function_name}_reentrancy

  - name: interpret_results
    description: Determine if vulnerability is confirmed
    type: analysis
    prompt: |
      The test output is:

      {test_output}

      Determine:
      1. Did the test pass (exploit successful)?
      2. If failed, why? (compilation error, assertion failed, revert)
      3. Is this a TRUE POSITIVE or FALSE POSITIVE?

      Return structured verdict:
      - verdict: CONFIRMED | REJECTED | UNCERTAIN
      - confidence: 0-100
      - evidence: [list of supporting facts]
      - reasoning: [explanation]

output_schema:
  verdict: string  # CONFIRMED, REJECTED, UNCERTAIN
  confidence: number  # 0-100
  evidence: array
  reasoning: string
  test_file: string  # Path to generated test
  test_result: string  # Pass/Fail/Error

tools_needed:
  - Read
  - Write
  - Bash

max_budget_usd: 1.50
max_iterations: 3
```

**Files to Create/Modify:**
- `src/true_vkg/grimoires/schema.py` - Grimoire schema definition
- `grimoires/` - Directory for grimoire YAML files

**Validation Criteria:**
- [ ] Schema captures all grimoire components
- [ ] Schema is YAML-parseable
- [ ] Schema supports all step types (analysis, code_generation, bash)
- [ ] Output schema is well-defined

**Estimated Hours:** 3h
**Actual Hours:** [Tracked]

---

#### Task 13.2: Reentrancy Grimoire

**Objective:** Create grimoire for reentrancy verification

**Prerequisites:**
- Task 13.1 complete

**Grimoire Steps:**
1. **Analyze**: Identify external call and state write ordering
2. **Generate**: Create Foundry test with malicious callback
3. **Execute**: Run `forge test`
4. **Interpret**: Determine verdict based on test result

**Implementation:**
```python
# src/true_vkg/grimoires/reentrancy.py
from true_vkg.grimoires.base import Grimoire, GrimoireResult

class ReentrancyGrimoire(Grimoire):
    """Grimoire for verifying reentrancy vulnerabilities."""

    id = "grimoire-reentrancy"

    async def execute(self, finding: Finding, context: GrimoireContext) -> GrimoireResult:
        # Step 1: Analyze call pattern
        analysis = await self.analyze_step(
            prompt=self.get_prompt("analyze_call_pattern"),
            context=context
        )

        if analysis.no_vulnerability:
            return GrimoireResult(
                verdict="REJECTED",
                confidence=80,
                reasoning="No exploitable reentrancy pattern found"
            )

        # Step 2: Generate test
        test_code = await self.generate_step(
            prompt=self.get_prompt("generate_test"),
            context=context,
            analysis=analysis
        )

        # Write test file
        test_path = await self.write_test(test_code, finding)

        # Step 3: Run test
        result = await self.bash_step(
            command=f"forge test -vvv --match-test {test_path}"
        )

        # Step 4: Interpret
        verdict = await self.interpret_step(
            prompt=self.get_prompt("interpret_results"),
            test_output=result.stdout
        )

        return GrimoireResult(
            verdict=verdict.verdict,
            confidence=verdict.confidence,
            evidence=verdict.evidence,
            reasoning=verdict.reasoning,
            test_file=test_path,
            test_result=result.status
        )
```

**Files to Create/Modify:**
- `grimoires/reentrancy.yaml` - Grimoire definition
- `src/true_vkg/grimoires/reentrancy.py` - Grimoire implementation

**Validation Criteria:**
- [ ] Grimoire loads from YAML
- [ ] All steps execute
- [ ] Test generation works
- [ ] Verdict is structured
- [ ] Confidence is calibrated

**Test Requirements:**
- [ ] Unit test: `test_grimoires.py::test_reentrancy_grimoire`
- [ ] Integration test: Full grimoire execution on known vulnerable contract

**Estimated Hours:** 4h
**Actual Hours:** [Tracked]

---

#### Task 13.7: Skill Invocation System

**Objective:** Make grimoires invocable as skills

**Prerequisites:**
- At least one grimoire complete (13.2)

**Skill Definition:**
```yaml
# .claude/skills/test-reentrancy.yaml
skill: test-reentrancy
description: Verify reentrancy vulnerability via expert grimoire
grimoire: grimoire-reentrancy
invocation:
  - "/test-reentrancy <finding-id>"
  - "test this finding for reentrancy"
```

**Implementation:**
```python
# src/true_vkg/skills/registry.py
class SkillRegistry:
    """Registry of available skills backed by grimoires."""

    def __init__(self, grimoire_loader: GrimoireLoader):
        self.grimoires = grimoire_loader
        self.skills = self._load_skills()

    def _load_skills(self) -> Dict[str, Skill]:
        """Load skill definitions from .claude/skills/."""
        skills = {}
        for path in glob.glob(".claude/skills/*.yaml"):
            skill = Skill.from_yaml(path)
            skill.grimoire = self.grimoires.get(skill.grimoire_id)
            skills[skill.name] = skill
        return skills

    async def invoke(self, skill_name: str, args: str) -> SkillResult:
        """Invoke a skill by name."""
        if skill_name not in self.skills:
            raise SkillNotFoundError(f"Skill '{skill_name}' not found")

        skill = self.skills[skill_name]
        finding_id = self._parse_args(args)
        finding = await self._get_finding(finding_id)
        context = await self._build_context(finding, skill.grimoire)

        result = await skill.grimoire.execute(finding, context)

        # Log cost
        self.telemetry.log_skill_invocation(
            skill=skill_name,
            finding=finding_id,
            cost=result.cost_usd
        )

        return SkillResult(
            skill=skill_name,
            finding=finding_id,
            grimoire_result=result
        )
```

**CLI Integration:**
```bash
# Manual skill invocation
vkg skill test-reentrancy VKG-001

# List available skills
vkg skill list

# Skill help
vkg skill help test-reentrancy
```

**Files to Create/Modify:**
- `src/true_vkg/skills/registry.py` - Skill registry
- `src/true_vkg/skills/__init__.py` - Module init
- `.claude/skills/` - Skill definitions

**Validation Criteria:**
- [ ] Skills loadable from YAML
- [ ] CLI invocation works
- [ ] Grimoire executes via skill
- [ ] Results returned structured

**Estimated Hours:** 4h
**Actual Hours:** [Tracked]

---

## 4. TEST SUITE REQUIREMENTS

### 4.1 Test Categories

| Category | Count Target | Coverage Target | Location |
|----------|--------------|-----------------|----------|
| Unit Tests | 30 | 85% | `tests/test_grimoires.py` |
| Integration Tests | 15 | - | `tests/integration/test_grimoire_execution.py` |
| Skill Tests | 10 | - | `tests/test_skills.py` |

### 4.2 Test Matrix

| Grimoire | Happy Path | Edge Cases | Error Cases | Performance |
|----------|-----------|------------|-------------|-------------|
| Reentrancy | [ ] | [ ] | [ ] | [ ] |
| Access Control | [ ] | [ ] | [ ] | [ ] |
| Oracle Manipulation | [ ] | [ ] | [ ] | [ ] |
| Flash Loan | [ ] | [ ] | [ ] | [ ] |
| MEV | [ ] | [ ] | [ ] | [ ] |

### 4.3 Test Fixtures Required

- [ ] Known vulnerable contracts for each grimoire
- [ ] Known safe contracts (false positive testing)
- [ ] Mock LLM responses for deterministic testing
- [ ] Pre-generated test files

---

## 5. IMPLEMENTATION GUIDELINES

### 5.1 Code Standards

- [ ] Type hints on all public functions
- [ ] Docstrings with examples
- [ ] No hardcoded values (use config)
- [ ] Error messages guide recovery
- [ ] All grimoire executions logged with timing and cost

### 5.2 File Locations

| Component | Location | Naming Convention |
|-----------|----------|-------------------|
| Grimoire Definitions | `grimoires/` | `[vuln-class].yaml` |
| Grimoire Implementations | `src/true_vkg/grimoires/` | `[vuln_class].py` |
| Skill Definitions | `.claude/skills/` | `[skill-name].yaml` |
| Tests | `tests/test_grimoires.py` | `test_[grimoire].py` |

### 5.3 Configuration

```yaml
# .vrs/config.yaml
grimoires:
  enabled: true
  max_budget_per_grimoire_usd: 2.00
  max_iterations: 3
  test_output_dir: ".vrs/generated_tests/"

  # Per-grimoire overrides
  reentrancy:
    max_budget_usd: 1.50

  oracle_manipulation:
    max_budget_usd: 2.50  # More complex

skills:
  enabled: true
  auto_register: true  # Auto-register grimoires as skills
```

---

## 6. REFLECTION PROTOCOL

### 6.1 Brutal Self-Critique Checklist

**After EACH grimoire completion, answer honestly:**

- [ ] Does this grimoire actually find the vulnerability?
- [ ] Does it produce false positives on safe code?
- [ ] Are the generated tests compilable?
- [ ] Would an expert auditor approve the verification procedure?
- [ ] Is the cost reasonable?
- [ ] Could this be done simpler?

**Self-Critique Protocol (per grimoire):**
1. Test on 3 known vulnerable contracts
2. Test on 3 known safe contracts
3. Measure: TP, TN, FP, FN
4. If precision < 80%: iterate
5. If test compilation < 60%: improve generation

### 6.2 Known Limitations

| Limitation | Impact | Mitigation | Future Fix? |
|------------|--------|------------|-------------|
| LLM hallucination | Wrong tests | Multi-step verification | Better prompts |
| Complex setups | Test won't compile | Iterative fixing | Scaffold library |
| Context limits | Missing info | Targeted context extraction | Chunking |

---

## 7. COMPLETION CHECKLIST

### 7.1 Exit Criteria

- [ ] All tasks completed
- [ ] All tests passing
- [ ] At least 5 grimoires working
- [ ] Skills invocable via CLI
- [ ] Cost tracking visible
- [ ] Integration test passes

**Phase 13 is COMPLETE when:**
- [ ] Grimoire schema defined
- [ ] 5+ grimoires implemented
- [ ] Skill invocation works
- [ ] Verification accuracy >= 70%
- [ ] Test compilation >= 60%

### 7.2 Artifacts Produced

| Artifact | Location | Purpose |
|----------|----------|---------|
| Grimoire Schema | `src/true_vkg/grimoires/schema.py` | Schema definition |
| Grimoire Definitions | `grimoires/*.yaml` | Per-vuln playbooks |
| Skill Registry | `src/true_vkg/skills/registry.py` | Skill management |
| Generated Tests | `.vrs/generated_tests/` | Test outputs |

---

## 8. FUTURE: MCP INTEGRATION (OPTIONAL)

**Note:** MCP integration was previously planned for this phase but has been deprioritized. The config structure supports future MCP if needed:

```yaml
# Future MCP config (not implemented)
mcp:
  foundry:
    enabled: false  # Future: use Foundry MCP for test execution
  etherscan:
    enabled: false  # Future: fetch contracts via MCP
```

**Rationale:** Grimoires and Skills provide the core value. MCP is optional optimization that can be added later without changing the grimoire architecture.

---

*Phase 13 Tracker | Version 3.0 | 2026-01-07*
*Changed: MCP → Grimoires & Skills (per Philosophy v2.0)*
*Template: PHASE_TEMPLATE.md v1.0*

---

## Alignment Addendum (Workstream P)

### Workstream P: Alignment Tasks

| ID | Objective | Start here | Dependencies | Deliverables | Validation | Conflicts | Spawn Triggers |
|----|-----------|------------|--------------|--------------|------------|-----------|----------------|
| P13.P.1 | Map grimoire test outputs to bead verdict + bucket | `docs/PHILOSOPHY.md`, `task/4.0/phases/phase-13/TRACKER.md` | P4.P.1 | Mapping rules | Phase 4 scaffold rules reference these | Keep Tier A/Tier B separate | New grimoire result |
| P13.P.2 | Link grimoire outputs to VulnDocs sources | `docs/PHILOSOPHY.md`, `task/4.0/phases/phase-17/TRACKER.md` | P17.P.2 | Linkage spec | Phase 17 uses linkage for updates | Evidence packet schema versioned | New VulnDocs source |

### Review Tasks (Required + Phase-Specific)

| ID | Objective | Start here | Dependencies | Deliverables | Validation | Conflicts | Spawn Triggers |
|----|-----------|------------|--------------|--------------|------------|-----------|----------------|
| P13.R.1 | Phase necessity review (keep/cut/modify) | `task/4.0/MASTER.md`, `docs/PHILOSOPHY.md` | - | Decision log in tracker | Decision referenced in alignment sweep | None | Phase outputs no longer needed |
| P13.R.2 | Task necessity review for P13.P.* | `task/4.0/phases/phase-13/TRACKER.md`, `task/codex/vkg_4_0_alignment_super_task.md` | P13.P.1-P13.P.2 | Task justification log | Each task has keep/merge decision | Avoid overlap with Phase 4/17 | Redundant task discovered |
| P13.R.3 | Conflict review with downstream phases | `task/4.0/MASTER.md` | P13.P.1-P13.P.2 | Conflict notes in tracker | Conflicts resolved or escalated | Tier A/Tier B separation | Conflict discovered |
| P13.R.4 | Verify grimoire schema compatibility with evidence packets | `docs/PHILOSOPHY.md`, `src/true_vkg/` | P13.P.1 | Schema compatibility note | Evidence packet mapping intact | Schema mismatch | Conflict detected |

### Dynamic Task Spawning (Alignment)

**Trigger:** New grimoire added.
**Spawn:** Add schema extension task.
**Example spawned task:** P13.P.3 Extend bead mapping for a new grimoire output.
