# BSKG 4.0: Master Production Roadmap

**The Definitive Guide to Building the World's First LLM-Native Solidity Security Orchestrator**

**Version:** 4.0 Final
**Date:** January 5, 2026
**Status:** PLANNING DOCUMENT

---

> **IMPORTANT: This is a PLANNING document describing the vision for BSKG 4.0.**
>
> **For current implementation status, see:**
> - `docs/STATUS.md` - What's actually implemented
> - `task/4.0/MASTER.md` - Current roadmap with honest metrics
> - `task/4.0/PHILOSOPHY_GAP_ANALYSIS.md` - Gap analysis vs PHILOSOPHY.md
>
> **Note:** The "VKG 3.5" metrics in Part 2 (Gap Analysis) are outdated.
> The actual current status is 84.6% DVDeFi detection with core KG working.

---

---

## Executive Summary

AlphaSwarm.sol 3.5 has achieved **88.73% precision and 89.15% recall** with 2,424+ tests, significantly exceeding industry averages (~26% for typical SAST tools). However, **the path to production readiness lies not in improving detection accuracy but in building the infrastructure that enterprises and agentic LLMs require.**

**The Critical Insight:** No unified Solidity security orchestrator exists today. By implementing agentic discovery (AGENTS.md), task orchestration (Beads), multi-tool integration, and confidence-calibrated output, BSKG can become the integration platform that audit firms and development teams currently build through custom scripts.

**Core Architecture Decision:** BSKG should use **graph-native retrieval** (PPR/traversal), not document-centric retrieval (GraphRAG). The knowledge graph we've built is a stronger substrate than what GraphRAG typically constructs from text. Our job is to make it navigable by LLMs, not to rebuild it from documents.

### What This Document Contains

1. **Philosophy** - The core principles driving BSKG 4.0
2. **Gap Analysis** - What exists vs. what's needed
3. **Priority Stack** - Ordered by actual blockers, not technical elegance
4. **Detailed Phase Plans** - Week-by-week implementation guides
5. **Technical Specifications** - Schemas, algorithms, and interfaces
6. **Risk Assessment** - What could go wrong and how to mitigate
7. **Success Metrics** - How to know when we're done

---

## Part 1: The BSKG Philosophy

### Core Principles

1. **Names Lie, Behavior Doesn't**
   - Traditional tools detect `withdraw()` patterns; rename to `process()` and detection fails
   - BSKG detects behavioral signatures: `R:bal→X:out→W:bal` (read balance, external call, write balance)
   - This is the **core innovation** that must be preserved

2. **Deterministic Foundation, Semantic Enhancement**
   - **Tier A (Deterministic):** Same code = same graph = same findings. No LLM variance.
   - **Tier B (Semantic):** LLM-guided investigation for context-dependent vulnerabilities
   - Never conflate these two modes

3. **Graph-Native Retrieval, Not Document-Centric**
   - BSKG already has a typed knowledge graph with 50+ properties per function
   - Use PPR/traversal to navigate it, not GraphRAG to reconstruct it
   - Target: 5-10x context reduction while preserving vulnerability semantics

4. **Orchestrator, Not Replacement**
   - BSKG orchestrates Slither, Aderyn, Medusa, Halmos, Foundry
   - Intelligent deduplication and gap analysis
   - Be the integration platform, not another siloed tool

5. **Build the Boring Stuff First**
   - Agentic discovery infrastructure before retrieval optimization
   - Task persistence before advanced reasoning
   - SARIF output before custom reporting

### The Two Fundamental Questions

For any feature decision, ask:

1. **Does this help an LLM agent discover and use VKG?**
   - If no, it's not Priority 0

2. **Does this turn findings into actionable, trackable work?**
   - If no, findings remain ephemeral and useless

---

## Part 2: Comprehensive Gap Analysis

### What BSKG 3.5 Has (Preserve)

| Component | Status | Lines | Why It Matters |
|-----------|--------|-------|----------------|
| Semantic Operations | EXCELLENT | 800+ | 20 behavior-based operations - THE core innovation |
| Behavioral Signatures | EXCELLENT | 500+ | `R:bal→X:out→W:bal` pattern detection |
| Multi-Agent System | GOOD | 11K | Attacker/Defender/Verifier/Arbiter debate |
| Rich Edge Intelligence | GOOD | 2K | risk_score, guards, taint on edges |
| LLM Infrastructure | SOLID | 4K | 6 providers, caching, cost tracking |
| Pattern Engine | SOLID | 2K | 119 YAML patterns with operation matchers |
| Test Coverage | VALUABLE | 55K | 92 test files protecting core functionality |
| Detection Accuracy | EXCELLENT | - | 88.73% precision, 89.15% recall |

### What BSKG 3.5 Lacks (Priority Order)

| Gap | Impact | Priority | Why |
|-----|--------|----------|-----|
| **Agentic Discovery** | LLMs can't find/use BSKG | **CRITICAL** | Without this, nothing else matters |
| **Beads Task Orchestration** | Findings are ephemeral | **CRITICAL** | No persistence across sessions |
| **Multi-Tool Orchestration** | Reinventing existing tools | **CRITICAL** | Not integrating with ecosystem |
| **Two-Tier Pattern System** | Conflated detection modes | HIGH | Deterministic vs semantic unclear |
| **Confidence Calibration** | Unquantified uncertainty | HIGH | Enterprises need calibrated scores |
| **PPR Context Optimization** | Token waste | HIGH | 5-10x context reduction possible |
| **SARIF Output** | No enterprise integration | HIGH | GitHub Code Scanning blocked |
| **Test Scaffold Generation** | Manual verification | MEDIUM | Should auto-generate PoC tests |
| **Cross-Contract Analysis** | Limited scope | MEDIUM | State Dependency Graphs needed |
| **Economic Attack Modeling** | Business logic gaps | MEDIUM | Flash loan, oracle, MEV detection |

### State-of-the-Art Comparison

| Capability | BSKG 3.5 | State-of-the-Art | Gap |
|------------|---------|------------------|-----|
| Agentic tool discovery | ❌ Missing | AGENTS.md standard (60K+ repos) | **CRITICAL** |
| Token-optimized retrieval | ⚠️ Basic | 67-90% reduction via slicing | HIGH |
| Confidence calibration | ❌ Not explicit | ECE metrics, conformal prediction | HIGH |
| Tool orchestration | ⚠️ Slither only | Multi-tool pipeline + dedup | **CRITICAL** |
| Task persistence | ❌ Missing | Beads DAG-based Git tracking | **CRITICAL** |
| SARIF output | ❌ Missing | OASIS standard, GitHub integration | HIGH |
| CWE/SWC mapping | ⚠️ Partial | Complete mapping with taxonomy | MEDIUM |
| Cross-contract analysis | ⚠️ Limited | State Dependency Graphs, I-PDG | MEDIUM |
| Economic attack modeling | ❌ Missing | Flash loan, oracle, MEV detection | MEDIUM |
| Test scaffold generation | ❌ Missing | Foundry/Medusa/Halmos templates | HIGH |

---

## Part 3: Priority Stack

### The Correct Priority Order

**Common Mistake:** Prioritizing technical elegance (PPR, HypergraphRAG, PRoH) over infrastructure blockers.

**Correct Order:**

```
PRIORITY 0: BLOCKING INFRASTRUCTURE
├── 0.1 Agentic Discovery (AGENTS.md, CLAUDE.md, skills/)
├── 0.2 Beads Task Orchestration
├── 0.3 Multi-Tool Orchestration (Slither, Aderyn, Medusa, Halmos)
└── 0.4 Foundation Hardening (builder.py bugs)

PRIORITY 1: TWO-TIER PATTERN SYSTEM
├── 1.1 Pattern Schema Enhancement (tier field, verification_steps)
├── 1.2 Tier B Verification Engine
├── 1.3 Confidence Calibration
└── 1.4 Test Scaffold Generation

PRIORITY 2: CONTEXT OPTIMIZATION (PPR)
├── 2.1 VKG-PPR Algorithm
├── 2.2 Query-to-Seed Mapping
├── 2.3 Token-Optimized Serialization
└── 2.4 Dynamic Scaffold Generation

PRIORITY 3: ADAPTIVE INVESTIGATION
├── 3.1 PRoH-style Subgoal Decomposition (optional)
├── 3.2 GeAR-style Iterative Retrieval (optional)
└── 3.3 ToG-2 Integration (future)

PRIORITY 4: PRODUCTION HARDENING
├── 4.1 SARIF Output
├── 4.2 Enterprise Compliance
├── 4.3 Session Management
└── 4.4 Self-Evolution Loop
```

### Why This Order?

1. **Without Priority 0, nothing else matters**
   - No LLM can discover or use VKG
   - Findings are ephemeral, not actionable
   - We're siloed from the tool ecosystem

2. **Priority 1 formalizes what we already do**
   - We have patterns, but Tier A vs B is implicit
   - Confidence is unquantified
   - Verification is ad-hoc

3. **Priority 2 optimizes LLM usage**
   - PPR is a nice-to-have optimization
   - Only matters after LLMs can actually use VKG
   - 5-10x context reduction is significant but not blocking

4. **Priority 3 is future enhancement**
   - PRoH/GeAR are research-grade
   - Our multi-agent system already does similar decomposition
   - Don't over-engineer before basics work

5. **Priority 4 is production polish**
   - SARIF is required for enterprise
   - Self-evolution is ongoing improvement

---

## Part 4: Phase 0 - Blocking Infrastructure (Weeks 1-6)

### Critical Gate

**No work on Phases 1-4 until Phase 0 is complete.**

Phase 0 addresses the actual blockers preventing BSKG from being useful to agentic LLMs. Everything else is optimization.

---

### Phase 0.1: Agentic Discovery Infrastructure (Weeks 1-2)

**Goal:** Make BSKG discoverable and usable by Claude Code, Cursor, Aider, Windsurf, OpenAI Codex, and any AGENTS.md-compliant tool.

#### The AGENTS.md Standard

AGENTS.md is now stewarded by the Linux Foundation's Agentic AI Foundation with adoption across 60,000+ repositories. It's the universal standard for AI agent tool discovery.

#### File Structure

```
project_root/
├── .vrs/                           # BSKG workspace
│   ├── AGENTS.md                   # Universal agentic discovery
│   ├── CLAUDE.md                   # Claude Code specific instructions
│   ├── skills/                     # Discoverable skills (44 patterns)
│   │   ├── reentrancy.skill.yaml
│   │   ├── access-control.skill.yaml
│   │   ├── oracle.skill.yaml
│   │   └── ... (44 total)
│   ├── beads/                      # Task orchestration
│   │   └── .beads.db               # Git-backed task DAG
│   ├── graphs/                     # Generated knowledge graphs
│   ├── reports/                    # SARIF output, audit reports
│   └── config.yaml                 # Tool orchestration config
```

#### AGENTS.md Specification

```yaml
# .vrs/AGENTS.md
---
name: BSKG Security Analyzer
version: 4.0.0
description: |
  Vulnerability Knowledge Graph for Solidity security analysis.
  The world's first LLM-native security orchestrator.

  Core Capabilities:
  - Build semantic knowledge graphs from Solidity code
  - Run 44 deterministic vulnerability patterns (Tier A)
  - Guide LLM-driven semantic verification (Tier B)
  - Orchestrate Slither, Aderyn, Medusa, Halmos, Foundry
  - Track findings as persistent tasks via Beads

capabilities:
  - build_knowledge_graph
  - run_deterministic_patterns
  - run_semantic_patterns
  - orchestrate_security_tools
  - generate_test_scaffolds
  - manage_verification_tasks

entry_points:
  - command: vkg init
    description: Initialize BSKG workspace in current project

  - command: vkg build
    description: Build knowledge graph for Solidity project
    output: .vrs/graphs/graph.json

  - command: vkg analyze
    description: Run all Tier A patterns (deterministic)
    output: Confirmed findings as Beads tasks

  - command: vkg verify
    description: Run Tier B verification (LLM-guided)
    requires: LLM context
    output: Verified/refuted findings

  - command: vkg tools run
    description: Run external security tools
    tools: [slither, aderyn, medusa, halmos]
    output: Unified SARIF report

  - command: vkg tasks list
    description: List all verification tasks
    output: Beads task list

  - command: vkg tasks next
    description: Get highest priority task for verification
    output: Single task with context

skills:
  path: .vrs/skills/
  auto_load: true
  description: |
    44 vulnerability detection skills, each with:
    - Pattern definition (YAML)
    - Verification steps (for Tier B)
    - Test templates (Foundry/Medusa/Halmos)
    - Evidence requirements

integrations:
  - name: slither
    version: ">=0.10.0"
    purpose: Fast static analysis, dependency

  - name: foundry
    version: ">=0.2.0"
    purpose: Test execution, fuzzing

  - name: medusa
    version: ">=1.0.0"
    purpose: Coverage-guided fuzzing

  - name: halmos
    version: ">=0.3.0"
    purpose: Symbolic execution

output_formats:
  - sarif  # GitHub Code Scanning compatible
  - json   # Machine-readable
  - text   # Human-readable
```

#### CLAUDE.md Specification

```markdown
# .vrs/CLAUDE.md
---
# BSKG Security Analyzer - Claude Code Integration

## Quick Start

1. **Initialize VKG** (first time only)
   ```bash
   vkg init
   ```

2. **Build Knowledge Graph**
   ```bash
   vkg build
   ```

3. **Run Deterministic Patterns** (Tier A)
   ```bash
   vkg analyze
   ```
   - These findings are CONFIRMED - trust them
   - Creates Beads tasks for tracking

4. **Verify Semantic Findings** (Tier B)
   ```bash
   vkg tasks next
   ```
   - Follow the verification steps provided
   - Use your reasoning to confirm/refute
   - Update task status when done

5. **Run External Tools**
   ```bash
   vkg tools run --all
   ```
   - Runs Slither, Aderyn, Medusa (if configured)
   - Deduplicates findings against BSKG patterns

## When to Use VKG

✅ **Use BSKG for:**
- Security audit of Solidity contracts
- Vulnerability pattern detection
- Verification of potential findings
- Test generation for vulnerability hypotheses
- Tracking audit progress across sessions

❌ **Don't use BSKG for:**
- Non-Solidity code
- Runtime monitoring (use tenderly, etc.)
- Gas optimization (use other tools)

## Understanding Tiers

### Tier A (Deterministic)
- Graph traversal only, no LLM needed
- High precision (>90%)
- **Trust these findings**
- Example: `state_write_after_external_call + !has_reentrancy_guard`

### Tier B (Semantic Reasoning)
- Requires LLM-guided verification
- Follow the verification_steps in the task
- May require test generation
- **Investigate these findings**
- Example: Business logic vulnerabilities, economic attacks

## Verification Workflow

When you get a Tier B task:

1. **Read the context bundle** - Contains relevant code and relationships
2. **Follow verification_steps** - Each step has a specific goal
3. **Gather evidence** - Code locations, traces, calculations
4. **Make a verdict** - CONFIRMED, FALSE_POSITIVE, or NEEDS_HUMAN
5. **Update the task** - `vkg tasks update <id> --verdict <verdict>`

## Important Commands

```bash
# See all tasks
vkg tasks list

# Get next task with full context
vkg tasks next --with-context

# Update task verdict
vkg tasks update bd-a1b2 --verdict confirmed --reasoning "..."

# Generate test for hypothesis
vkg test generate --finding bd-a1b2 --type foundry

# Run generated tests
vkg test run

# Export SARIF report
vkg report --format sarif --output findings.sarif
```

## Session Handoff

At the end of your session, run:
```bash
vkg tasks handoff
```

This generates a summary for the next session, preserving context across the "50 First Dates" problem.
```

#### Skill File Specification

```yaml
# .vrs/skills/reentrancy.skill.yaml
---
id: vm-001
name: Classic Reentrancy Detection
description: |
  Detect reentrancy vulnerabilities where state writes occur after external calls
  without reentrancy guards.

tier: A  # Deterministic - no LLM needed for detection
type: deterministic

# When this skill should be invoked
triggers:
  - "reentrancy"
  - "state write after call"
  - "CEI violation"
  - "check-effects-interactions"

# Pattern matching conditions
pattern:
  ALL:
    - property: state_write_after_external_call
      value: true
    - property: has_reentrancy_guard
      value: false
  NONE:
    - property: uses_transfer  # 2300 gas limit prevents reentrancy

# For Tier A, findings go directly to CONFIRMED
confidence: HIGH
output_state: CONFIRMED

# Evidence requirements
evidence:
  required:
    - code_location: "Function with external call"
    - code_location: "State write after call"
  optional:
    - trace: "Call graph showing reentry path"

# Related exploits (for context)
related_exploits:
  - name: "The DAO"
    amount: "$60M"
    year: 2016
  - name: "Lendf.Me"
    amount: "$25M"
    year: 2020

# SWC mapping
swc_id: SWC-107
cwe_id: CWE-841

# Test template (for verification or PoC)
test_template: |
  // SPDX-License-Identifier: MIT
  pragma solidity ^0.8.0;
  import "forge-std/Test.sol";

  contract ReentrancyTest is Test {
      {{contract_name}} target;

      function setUp() public {
          target = new {{contract_name}}();
          // Setup initial state
      }

      function testReentrancy() public {
          // Attack contract calls target
          // Re-enters during callback
          // Verify state inconsistency
      }

      receive() external payable {
          if (address(target).balance > 0) {
              target.{{function_name}}();
          }
      }
  }
```

#### Implementation Tasks

```python
# Pseudocode: Agentic discovery implementation

class AgenticDiscovery:
    """Generate and manage agentic discovery files."""

    def init_workspace(self, project_path: Path):
        """Initialize .vkg workspace with all discovery files."""
        vkg_path = project_path / ".vkg"
        vkg_path.mkdir(exist_ok=True)

        # Generate AGENTS.md
        self._generate_agents_md(vkg_path)

        # Generate CLAUDE.md
        self._generate_claude_md(vkg_path)

        # Generate skill files from patterns
        skills_path = vkg_path / "skills"
        skills_path.mkdir(exist_ok=True)
        for pattern in self.pattern_registry.all():
            self._generate_skill_file(skills_path, pattern)

        # Initialize Beads database
        beads_path = vkg_path / "beads"
        beads_path.mkdir(exist_ok=True)
        self._init_beads_db(beads_path)

        # Create config
        self._generate_config(vkg_path)

    def _generate_agents_md(self, vkg_path: Path):
        """Generate AGENTS.md from template + current config."""
        template = self.load_template("agents.md.jinja")
        content = template.render(
            version=self.version,
            capabilities=self.capabilities,
            entry_points=self.entry_points,
            skills_count=len(self.pattern_registry.all()),
        )
        (vkg_path / "AGENTS.md").write_text(content)

    def _generate_skill_file(self, skills_path: Path, pattern: Pattern):
        """Convert pattern to skill file."""
        skill = {
            "id": pattern.id,
            "name": pattern.name,
            "description": pattern.description,
            "tier": "A" if pattern.is_deterministic else "B",
            "type": "deterministic" if pattern.is_deterministic else "semantic",
            "triggers": self._extract_triggers(pattern),
            "pattern": pattern.match,
            "confidence": pattern.confidence,
            "output_state": "CONFIRMED" if pattern.is_deterministic else "POTENTIAL",
            "evidence": pattern.evidence_requirements,
            "swc_id": pattern.swc_id,
            "test_template": pattern.test_template,
        }

        skill_path = skills_path / f"{pattern.id}.skill.yaml"
        with open(skill_path, "w") as f:
            yaml.dump(skill, f, default_flow_style=False)
```

#### Deliverables

- [ ] `src/true_vkg/agentic/discovery.py` - Discovery file generation
- [ ] `src/true_vkg/agentic/templates/` - Jinja templates for AGENTS.md, CLAUDE.md
- [ ] CLI `vkg init` command
- [ ] CLI `vkg skills list` command
- [ ] Skill file schema and validator
- [ ] Tests for agentic discovery

#### Validation Gate

- [ ] Claude Code can discover BSKG via `cat .vrs/AGENTS.md`
- [ ] Claude Code can list skills via `vkg skills list`
- [ ] Skill files validate against schema
- [ ] `vkg init` creates complete workspace structure

---

### Phase 0.2: Beads Task Orchestration (Weeks 2-3)

**Goal:** Implement Git-backed task persistence so findings become trackable work items that survive across LLM sessions.

#### The "50 First Dates" Problem

Every LLM session starts fresh with no memory of prior work. Beads solves this by:
1. Storing tasks as JSONL files in `.vrs/beads/`
2. Using Git for version control and distributed state
3. Generating session handoff prompts for continuity

#### Vulnerability Bead Schema

```python
@dataclass
class VulnerabilityBead:
    """A vulnerability finding represented as a Beads task."""

    # Identity
    id: str  # bd-{hash} format for collision-free merging
    created_at: datetime
    updated_at: datetime

    # Vulnerability metadata
    vulnerability_class: str  # "reentrancy", "access_control", etc.
    swc_id: str  # "SWC-107"
    pattern_id: str  # "vm-001"
    tier: Literal["A", "B"]

    # Location
    contract: str
    function: str
    file_path: str
    line_start: int
    line_end: int

    # State machine
    verification_state: VerificationState
    # unverified → llm_reviewing → human_reviewing → confirmed|false_positive

    # Confidence and scoring
    confidence_score: float  # 0.0 - 1.0
    severity: Literal["critical", "high", "medium", "low", "info"]

    # Discovery metadata
    discovered_by: str  # "vkg_pattern", "slither", "medusa", "llm_reasoning"
    requires_llm_reasoning: bool

    # Verification (for Tier B)
    verification_steps: List[VerificationStep]
    current_verification_step: int
    verification_log: List[VerificationLogEntry]

    # Test generation
    test_scaffold_type: Optional[str]  # "foundry", "medusa", "halmos"
    test_scaffold_generated: bool
    test_result: Optional[TestResult]

    # Evidence
    evidence: Evidence
    reasoning: Optional[str]  # LLM's reasoning for verdict

    # Dependencies (Beads core feature)
    deps: List[str]  # ["blocks:remediation-{id}", "related:similar-{id}"]

    # Priority (Beads core feature)
    priority: int  # 0 (highest) to 4 (lowest)

    def to_bead_format(self) -> dict:
        """Convert to Beads-compatible JSONL format."""
        return {
            "id": self.id,
            "type": "vulnerability",
            "priority": self.priority,
            "state": self.verification_state.value,
            "created": self.created_at.isoformat(),
            "updated": self.updated_at.isoformat(),
            "metadata": {
                "vuln_class": self.vulnerability_class,
                "swc_id": self.swc_id,
                "pattern_id": self.pattern_id,
                "tier": self.tier,
                "confidence": self.confidence_score,
                "severity": self.severity,
                "discovered_by": self.discovered_by,
                "requires_llm": self.requires_llm_reasoning,
                "location": {
                    "contract": self.contract,
                    "function": self.function,
                    "file": self.file_path,
                    "lines": [self.line_start, self.line_end],
                },
            },
            "verification": {
                "steps": [s.to_dict() for s in self.verification_steps],
                "current_step": self.current_verification_step,
                "log": [e.to_dict() for e in self.verification_log],
            },
            "evidence": self.evidence.to_dict(),
            "reasoning": self.reasoning,
            "deps": self.deps,
        }


class VerificationState(Enum):
    """Task state machine."""
    UNVERIFIED = "unverified"          # Initial state
    LLM_REVIEWING = "llm_reviewing"    # LLM is investigating
    HUMAN_REVIEWING = "human_reviewing" # Escalated to human
    CONFIRMED = "confirmed"            # Verified as true positive
    FALSE_POSITIVE = "false_positive"  # Verified as false positive
    REMEDIATED = "remediated"          # Fix has been applied
```

#### Beads Task Manager

```python
class BeadsTaskManager:
    """Manage vulnerability findings as Beads tasks."""

    def __init__(self, vkg_path: Path):
        self.beads_path = vkg_path / "beads"
        self.tasks_file = self.beads_path / "tasks.jsonl"
        self._ensure_initialized()

    def create_from_pattern_result(self, result: PatternResult) -> VulnerabilityBead:
        """Convert pattern finding to Beads task."""
        bead_id = self._generate_id(result)

        bead = VulnerabilityBead(
            id=bead_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            vulnerability_class=result.pattern.vulnerability_class,
            swc_id=result.pattern.swc_id,
            pattern_id=result.pattern.id,
            tier=result.pattern.tier,
            contract=result.node.contract,
            function=result.node.name,
            file_path=result.evidence.file,
            line_start=result.evidence.line_start,
            line_end=result.evidence.line_end,
            verification_state=(
                VerificationState.CONFIRMED if result.pattern.tier == "A"
                else VerificationState.UNVERIFIED
            ),
            confidence_score=result.confidence,
            severity=result.pattern.severity,
            discovered_by="vkg_pattern",
            requires_llm_reasoning=(result.pattern.tier == "B"),
            verification_steps=result.pattern.verification_steps,
            current_verification_step=0,
            verification_log=[],
            evidence=result.evidence,
            priority=self._calculate_priority(result),
            deps=[],
        )

        self._append_task(bead)
        return bead

    def create_from_external_tool(self, finding: ExternalFinding,
                                   tool: str) -> VulnerabilityBead:
        """Convert external tool finding to Beads task."""
        bead_id = self._generate_id(finding)

        # Check for duplicates
        existing = self._find_duplicate(finding)
        if existing:
            # Merge: add tool to discovered_by, update confidence
            self._merge_finding(existing, finding, tool)
            return existing

        bead = VulnerabilityBead(
            id=bead_id,
            # ... similar to above
            discovered_by=tool,
            requires_llm_reasoning=True,  # External findings need verification
            verification_state=VerificationState.UNVERIFIED,
        )

        self._append_task(bead)
        return bead

    def get_ready_tasks(self,
                        filter: Optional[str] = None) -> List[VulnerabilityBead]:
        """
        Get highest-priority unblocked tasks.

        Filters:
        - "all": All tasks
        - "llm_actionable": Unverified + LLM can handle
        - "needs_human": Escalated to human
        - "blocked": Tasks with unmet dependencies
        """
        tasks = self._load_all_tasks()

        # Filter by state
        if filter == "llm_actionable":
            tasks = [t for t in tasks
                    if t.verification_state == VerificationState.UNVERIFIED
                    and t.requires_llm_reasoning]
        elif filter == "needs_human":
            tasks = [t for t in tasks
                    if t.verification_state == VerificationState.HUMAN_REVIEWING]
        elif filter == "blocked":
            tasks = [t for t in tasks if self._is_blocked(t)]

        # Filter out blocked tasks (unless explicitly requested)
        if filter != "blocked":
            tasks = [t for t in tasks if not self._is_blocked(t)]

        # Sort by priority (0 = highest)
        tasks.sort(key=lambda t: (t.priority, t.created_at))

        return tasks

    def update_verification_state(self, bead_id: str,
                                   state: VerificationState,
                                   reasoning: Optional[str] = None,
                                   evidence: Optional[Evidence] = None):
        """Update task state after verification."""
        task = self._load_task(bead_id)
        task.verification_state = state
        task.updated_at = datetime.utcnow()

        if reasoning:
            task.reasoning = reasoning
        if evidence:
            task.evidence = self._merge_evidence(task.evidence, evidence)

        # Add to verification log
        task.verification_log.append(VerificationLogEntry(
            timestamp=datetime.utcnow(),
            state=state,
            reasoning=reasoning,
        ))

        self._update_task(task)

    def generate_session_handoff(self) -> str:
        """
        Generate prompt for next LLM session ('land the plane').

        This is CRITICAL for the Beads pattern - it preserves context
        across the "50 First Dates" problem.
        """
        tasks = self._load_all_tasks()

        summary = {
            "total_tasks": len(tasks),
            "by_state": {},
            "by_severity": {},
            "next_priority": [],
        }

        # Count by state
        for state in VerificationState:
            count = len([t for t in tasks if t.verification_state == state])
            if count > 0:
                summary["by_state"][state.value] = count

        # Count by severity
        for sev in ["critical", "high", "medium", "low"]:
            count = len([t for t in tasks if t.severity == sev])
            if count > 0:
                summary["by_severity"][sev] = count

        # Top 5 priority tasks
        ready = self.get_ready_tasks(filter="llm_actionable")[:5]
        for task in ready:
            summary["next_priority"].append({
                "id": task.id,
                "type": task.vulnerability_class,
                "location": f"{task.contract}.{task.function}",
                "severity": task.severity,
            })

        # Generate prompt
        prompt = f"""# BSKG Audit Session Handoff

## Summary
- Total findings: {summary['total_tasks']}
- States: {summary['by_state']}
- Severities: {summary['by_severity']}

## Next Priority Tasks
"""
        for task in summary["next_priority"]:
            prompt += f"- [{task['severity'].upper()}] {task['id']}: {task['type']} in {task['location']}\n"

        prompt += """
## To Continue
1. Run `vkg tasks next` to get the highest priority task with full context
2. Follow the verification steps in the task
3. Update verdict: `vkg tasks update <id> --verdict <confirmed|false_positive>`
"""

        return prompt

    def _generate_id(self, finding) -> str:
        """Generate collision-free Beads ID."""
        # Hash of: pattern + location + key properties
        content = f"{finding.pattern_id}:{finding.file}:{finding.line}:{finding.function}"
        hash_val = hashlib.sha256(content.encode()).hexdigest()[:8]
        return f"bd-{hash_val}"

    def _is_blocked(self, task: VulnerabilityBead) -> bool:
        """Check if task has unmet dependencies."""
        for dep in task.deps:
            if dep.startswith("blocks:"):
                blocking_id = dep.split(":")[1]
                blocking_task = self._load_task(blocking_id)
                if blocking_task and blocking_task.verification_state not in [
                    VerificationState.CONFIRMED,
                    VerificationState.FALSE_POSITIVE,
                    VerificationState.REMEDIATED,
                ]:
                    return True
        return False
```

#### CLI Commands

```python
# CLI implementation sketch

@click.group()
def tasks():
    """Manage verification tasks."""
    pass

@tasks.command()
@click.option("--filter", type=click.Choice(["all", "llm_actionable", "needs_human", "blocked"]))
@click.option("--format", type=click.Choice(["table", "json"]), default="table")
def list(filter, format):
    """List all verification tasks."""
    manager = BeadsTaskManager(get_vkg_path())
    tasks = manager.get_ready_tasks(filter=filter)

    if format == "json":
        click.echo(json.dumps([t.to_bead_format() for t in tasks], indent=2))
    else:
        # Pretty table output
        for task in tasks:
            click.echo(f"[{task.severity.upper()}] {task.id}: {task.vulnerability_class}")
            click.echo(f"    Location: {task.contract}.{task.function}")
            click.echo(f"    State: {task.verification_state.value}")
            click.echo()

@tasks.command()
@click.option("--with-context/--no-context", default=True)
def next(with_context):
    """Get highest priority task for verification."""
    manager = BeadsTaskManager(get_vkg_path())
    tasks = manager.get_ready_tasks(filter="llm_actionable")

    if not tasks:
        click.echo("No tasks ready for verification.")
        return

    task = tasks[0]
    click.echo(f"# Task: {task.id}")
    click.echo(f"Type: {task.vulnerability_class}")
    click.echo(f"Severity: {task.severity}")
    click.echo(f"Location: {task.file_path}:{task.line_start}-{task.line_end}")
    click.echo()

    if with_context:
        # Get optimized context via PPR (Phase 2)
        # For now, just show the relevant code
        context = get_context_for_task(task)
        click.echo("## Context")
        click.echo(context)

    if task.verification_steps:
        click.echo("## Verification Steps")
        for i, step in enumerate(task.verification_steps):
            marker = "→" if i == task.current_verification_step else " "
            click.echo(f"{marker} Step {i+1}: {step.action}")
            click.echo(f"    {step.description}")

@tasks.command()
@click.argument("task_id")
@click.option("--verdict", type=click.Choice(["confirmed", "false_positive", "needs_human"]))
@click.option("--reasoning", help="Explanation for the verdict")
def update(task_id, verdict, reasoning):
    """Update task verification state."""
    manager = BeadsTaskManager(get_vkg_path())

    state_map = {
        "confirmed": VerificationState.CONFIRMED,
        "false_positive": VerificationState.FALSE_POSITIVE,
        "needs_human": VerificationState.HUMAN_REVIEWING,
    }

    manager.update_verification_state(task_id, state_map[verdict], reasoning)
    click.echo(f"Updated {task_id} to {verdict}")

@tasks.command()
def handoff():
    """Generate session handoff prompt."""
    manager = BeadsTaskManager(get_vkg_path())
    prompt = manager.generate_session_handoff()
    click.echo(prompt)
```

#### Deliverables

- [ ] `src/true_vkg/beads/schema.py` - VulnerabilityBead schema
- [ ] `src/true_vkg/beads/manager.py` - BeadsTaskManager
- [ ] `src/true_vkg/beads/storage.py` - JSONL storage with Git integration
- [ ] CLI `vkg tasks list` command
- [ ] CLI `vkg tasks next` command
- [ ] CLI `vkg tasks update` command
- [ ] CLI `vkg tasks handoff` command
- [ ] Tests for Beads integration

#### Validation Gate

- [ ] Tasks persist to `.vrs/beads/tasks.jsonl`
- [ ] `vkg tasks handoff` generates valid session prompt
- [ ] Dependency blocking works correctly
- [ ] Duplicate detection prevents redundant tasks

---

### Phase 0.3: Multi-Tool Orchestration (Weeks 3-5)

**Goal:** Integrate Slither, Aderyn, Medusa, Halmos, and Foundry with intelligent deduplication and unified output.

#### Why This Matters

Currently, BSKG is a siloed tool. To be "the best security suite," we must:
1. Run existing tools (not reinvent them)
2. Deduplicate findings across tools
3. Compare BSKG patterns against tool coverage
4. Provide unified output (SARIF)

#### Tool Integration Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     TOOL ORCHESTRATION LAYER                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  STATIC ANALYSIS TIER (Fast, CI/CD compatible)                    │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐         │   │
│  │  │ Slither  │  │ Aderyn   │  │ Solhint  │  │ Semgrep  │         │   │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘         │   │
│  │       └──────────────┴──────────────┴──────────────┘              │   │
│  │                           │                                        │   │
│  │                  FINDING NORMALIZER                                │   │
│  │                  • Map to SWC IDs                                  │   │
│  │                  • Normalize locations                             │   │
│  │                  • Extract confidence                              │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                           │                                              │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  DYNAMIC ANALYSIS TIER (Fuzzing, slower)                          │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐                        │   │
│  │  │ Medusa   │  │ Echidna  │  │ Foundry  │                        │   │
│  │  │  (v1)    │  │          │  │  fuzz    │                        │   │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘                        │   │
│  │       └──────────────┴──────────────┘                              │   │
│  │                           │                                        │   │
│  │                  COUNTEREXAMPLE COLLECTOR                          │   │
│  │                  • Extract failing inputs                          │   │
│  │                  • Generate reproduction tests                     │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                           │                                              │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  FORMAL VERIFICATION TIER (Proofs, slowest)                       │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐                        │   │
│  │  │ Halmos   │  │ Certora  │  │ Mythril  │                        │   │
│  │  │  (v0.3)  │  │          │  │          │                        │   │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘                        │   │
│  │       └──────────────┴──────────────┘                              │   │
│  │                           │                                        │   │
│  │                  PROOF COLLECTOR                                   │   │
│  │                  • Extract counterexamples                         │   │
│  │                  • Verified = no bugs in scope                     │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                           │                                              │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  AGGREGATION & DEDUPLICATION                                      │   │
│  │  • Normalize all findings to unified schema                       │   │
│  │  • Deduplicate by: location + vuln_type + SWC_ID                 │   │
│  │  • Compare against BSKG pattern coverage                           │   │
│  │  • Flag: VKG-only, tool-only, both detected                      │   │
│  │  • Output: SARIF 2.1.0                                           │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

#### Tool Interface

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path

@dataclass
class NormalizedFinding:
    """Unified finding format across all tools."""

    # Identity
    id: str
    tool: str

    # Classification
    swc_id: Optional[str]
    vulnerability_type: str
    severity: str  # "critical", "high", "medium", "low", "info"
    confidence: float  # 0.0 - 1.0

    # Location
    file_path: str
    line_start: int
    line_end: int
    contract: Optional[str]
    function: Optional[str]

    # Description
    title: str
    description: str
    recommendation: Optional[str]

    # Evidence
    code_snippet: Optional[str]
    trace: Optional[List[dict]]

    # Metadata
    raw_output: dict  # Original tool output


class SecurityTool(ABC):
    """Base interface for security tool integration."""

    name: str
    version: str
    tier: str  # "static", "dynamic", "formal"

    @abstractmethod
    def is_available(self) -> bool:
        """Check if tool is installed and runnable."""
        pass

    @abstractmethod
    def analyze(self, project_path: Path,
                config: Optional[dict] = None) -> List[NormalizedFinding]:
        """Run analysis and return normalized findings."""
        pass

    @abstractmethod
    def normalize_finding(self, raw: dict) -> NormalizedFinding:
        """Convert tool-specific output to normalized format."""
        pass


class SlitherTool(SecurityTool):
    """Slither integration."""

    name = "slither"
    version = "0.10.0+"
    tier = "static"

    # SWC mapping for Slither detectors
    DETECTOR_TO_SWC = {
        "reentrancy-eth": "SWC-107",
        "reentrancy-no-eth": "SWC-107",
        "arbitrary-send-eth": "SWC-105",
        "controlled-delegatecall": "SWC-112",
        "unprotected-upgrade": "SWC-105",
        # ... complete mapping
    }

    def analyze(self, project_path: Path,
                config: Optional[dict] = None) -> List[NormalizedFinding]:
        """Run Slither and normalize output."""
        # Run Slither with JSON output
        result = subprocess.run(
            ["slither", str(project_path), "--json", "-"],
            capture_output=True,
            text=True
        )

        raw_output = json.loads(result.stdout)
        findings = []

        for detector_result in raw_output.get("results", {}).get("detectors", []):
            finding = self.normalize_finding(detector_result)
            findings.append(finding)

        return findings

    def normalize_finding(self, raw: dict) -> NormalizedFinding:
        """Convert Slither output to normalized format."""
        # Extract first element for location
        elements = raw.get("elements", [])
        first_elem = elements[0] if elements else {}
        source = first_elem.get("source_mapping", {})

        return NormalizedFinding(
            id=f"slither-{raw.get('check')}-{source.get('start', 0)}",
            tool="slither",
            swc_id=self.DETECTOR_TO_SWC.get(raw.get("check")),
            vulnerability_type=raw.get("check", "unknown"),
            severity=raw.get("impact", "medium").lower(),
            confidence=self._confidence_to_float(raw.get("confidence", "Medium")),
            file_path=source.get("filename_relative", ""),
            line_start=source.get("lines", [0])[0],
            line_end=source.get("lines", [0])[-1] if source.get("lines") else 0,
            contract=first_elem.get("type_specific_fields", {}).get("parent", {}).get("name"),
            function=first_elem.get("name"),
            title=raw.get("check", ""),
            description=raw.get("description", ""),
            recommendation=raw.get("recommendation"),
            code_snippet=None,  # Could extract from source
            trace=None,
            raw_output=raw,
        )


class AderynTool(SecurityTool):
    """Aderyn integration (Cyfrin's Rust-based analyzer)."""

    name = "aderyn"
    version = "0.1.0+"
    tier = "static"

    def analyze(self, project_path: Path,
                config: Optional[dict] = None) -> List[NormalizedFinding]:
        """Run Aderyn and normalize output."""
        # Aderyn outputs JSON by default
        result = subprocess.run(
            ["aderyn", str(project_path), "--output", "json"],
            capture_output=True,
            text=True
        )

        raw_output = json.loads(result.stdout)
        return [self.normalize_finding(f) for f in raw_output.get("findings", [])]


class MedusaTool(SecurityTool):
    """Medusa v1 integration (Trail of Bits fuzzer)."""

    name = "medusa"
    version = "1.0.0+"
    tier = "dynamic"

    def analyze(self, project_path: Path,
                config: Optional[dict] = None) -> List[NormalizedFinding]:
        """Run Medusa fuzzing campaign."""
        # Medusa requires configuration
        medusa_config = config or self._generate_config(project_path)

        result = subprocess.run(
            ["medusa", "fuzz", "--config", medusa_config],
            capture_output=True,
            text=True,
            timeout=config.get("timeout", 300)  # 5 min default
        )

        # Parse Medusa output for property violations
        return self._parse_output(result.stdout)


class HalmosTool(SecurityTool):
    """Halmos v0.3 integration (symbolic execution)."""

    name = "halmos"
    version = "0.3.0+"
    tier = "formal"

    def analyze(self, project_path: Path,
                targets: Optional[List[str]] = None,
                config: Optional[dict] = None) -> List[NormalizedFinding]:
        """Run Halmos symbolic execution."""
        cmd = ["halmos", "--root", str(project_path)]

        if targets:
            for target in targets:
                cmd.extend(["--function", target])

        result = subprocess.run(cmd, capture_output=True, text=True)
        return self._parse_counterexamples(result.stdout)
```

#### Deduplication Engine

```python
class FindingDeduplicator:
    """Deduplicate findings across multiple tools."""

    def deduplicate(self, findings: List[NormalizedFinding]) -> DeduplicationResult:
        """
        Deduplicate findings by location + type.

        Returns unified findings with source tracking.
        """
        # Group by location signature
        location_groups = {}
        for finding in findings:
            sig = self._location_signature(finding)
            if sig not in location_groups:
                location_groups[sig] = []
            location_groups[sig].append(finding)

        unified = []
        for sig, group in location_groups.items():
            if len(group) == 1:
                unified.append(UnifiedFinding.from_single(group[0]))
            else:
                # Multiple tools found the same issue
                unified.append(self._merge_findings(group))

        return DeduplicationResult(
            unified_findings=unified,
            total_raw=len(findings),
            duplicates_removed=len(findings) - len(unified),
            by_tool={tool: len([f for f in findings if f.tool == tool])
                    for tool in set(f.tool for f in findings)},
        )

    def _location_signature(self, finding: NormalizedFinding) -> str:
        """Generate deduplication signature."""
        # Normalize: same file + overlapping lines + same vuln type
        return f"{finding.file_path}:{finding.line_start}-{finding.line_end}:{finding.swc_id or finding.vulnerability_type}"

    def _merge_findings(self, group: List[NormalizedFinding]) -> UnifiedFinding:
        """Merge multiple findings for same location."""
        # Take highest severity
        severities = ["critical", "high", "medium", "low", "info"]
        best_severity = min(severities.index(f.severity) for f in group)

        # Average confidence
        avg_confidence = sum(f.confidence for f in group) / len(group)

        # Combine descriptions
        tools = [f.tool for f in group]

        return UnifiedFinding(
            id=group[0].id,  # Use first ID
            tools=tools,
            swc_id=group[0].swc_id,  # Should be same
            vulnerability_type=group[0].vulnerability_type,
            severity=severities[best_severity],
            confidence=avg_confidence,
            file_path=group[0].file_path,
            line_start=min(f.line_start for f in group),
            line_end=max(f.line_end for f in group),
            descriptions={f.tool: f.description for f in group},
        )

    def compare_with_vkg(self,
                         unified: List[UnifiedFinding],
                         vkg_results: List[PatternResult]) -> CoverageComparison:
        """Compare external tool findings with BSKG patterns."""
        vkg_sigs = {self._vkg_signature(r) for r in vkg_results}
        tool_sigs = {self._unified_signature(f) for f in unified}

        both = vkg_sigs & tool_sigs
        vkg_only = vkg_sigs - tool_sigs
        tool_only = tool_sigs - vkg_sigs

        return CoverageComparison(
            detected_by_both=len(both),
            vkg_only=len(vkg_only),
            tools_only=len(tool_only),
            vkg_coverage_gaps=[sig for sig in tool_only],  # Patterns we should add
            tool_coverage_gaps=[sig for sig in vkg_only],  # BSKG advantage
        )
```

#### Tool Orchestrator

```python
class ToolOrchestrator:
    """Orchestrate multiple security analysis tools."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config = self._load_config(config_path)
        self.tools = self._initialize_tools()
        self.deduplicator = FindingDeduplicator()

    def _initialize_tools(self) -> Dict[str, SecurityTool]:
        """Initialize available tools."""
        tools = {}

        tool_classes = [
            SlitherTool,
            AderynTool,
            MedusaTool,
            HalmosTool,
            FoundryTool,
        ]

        for tool_class in tool_classes:
            tool = tool_class()
            if tool.is_available():
                tools[tool.name] = tool
            else:
                logging.warning(f"{tool.name} not available")

        return tools

    async def run_static_analysis(self,
                                   project_path: Path) -> List[NormalizedFinding]:
        """Run fast static analyzers in parallel."""
        static_tools = [t for t in self.tools.values() if t.tier == "static"]

        tasks = [
            asyncio.to_thread(tool.analyze, project_path)
            for tool in static_tools
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        findings = []
        for result in results:
            if isinstance(result, Exception):
                logging.error(f"Tool failed: {result}")
            else:
                findings.extend(result)

        return findings

    async def run_dynamic_analysis(self,
                                    project_path: Path,
                                    targets: Optional[List[str]] = None,
                                    timeout: int = 300) -> List[NormalizedFinding]:
        """Run fuzzers on targeted functions."""
        dynamic_tools = [t for t in self.tools.values() if t.tier == "dynamic"]

        findings = []
        for tool in dynamic_tools:
            try:
                result = await asyncio.wait_for(
                    asyncio.to_thread(tool.analyze, project_path, {"targets": targets}),
                    timeout=timeout
                )
                findings.extend(result)
            except asyncio.TimeoutError:
                logging.warning(f"{tool.name} timed out after {timeout}s")

        return findings

    async def run_formal_verification(self,
                                       project_path: Path,
                                       hypotheses: List[Finding]) -> List[NormalizedFinding]:
        """Run formal verification on specific hypotheses."""
        formal_tools = [t for t in self.tools.values() if t.tier == "formal"]

        # Generate verification targets from hypotheses
        targets = [self._hypothesis_to_target(h) for h in hypotheses]

        findings = []
        for tool in formal_tools:
            result = tool.analyze(project_path, targets=targets)
            findings.extend(result)

        return findings

    async def run_full_pipeline(self,
                                 project_path: Path,
                                 vkg_results: List[PatternResult]) -> PipelineResult:
        """Run complete analysis pipeline."""

        # Stage 1: Static analysis (fast)
        logging.info("Running static analysis...")
        static_findings = await self.run_static_analysis(project_path)

        # Deduplicate static findings
        deduped = self.deduplicator.deduplicate(static_findings)

        # Compare with VKG
        comparison = self.deduplicator.compare_with_vkg(deduped.unified_findings, vkg_results)

        # Stage 2: Dynamic analysis on high-priority targets
        high_priority = [f for f in deduped.unified_findings
                        if f.severity in ["critical", "high"]]

        if high_priority:
            logging.info(f"Running dynamic analysis on {len(high_priority)} targets...")
            dynamic_findings = await self.run_dynamic_analysis(
                project_path,
                targets=[f.function for f in high_priority if f.function]
            )
            static_findings.extend(dynamic_findings)

        # Final deduplication
        final_deduped = self.deduplicator.deduplicate(static_findings)

        return PipelineResult(
            findings=final_deduped.unified_findings,
            coverage=comparison,
            tools_run=[t.name for t in self.tools.values()],
            duration_seconds=None,  # Track
        )
```

#### SARIF Output

```python
class SARIFGenerator:
    """Generate SARIF 2.1.0 compliant output."""

    SARIF_VERSION = "2.1.0"
    SCHEMA_URI = "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json"

    def generate(self,
                 findings: List[UnifiedFinding],
                 tool_info: dict) -> dict:
        """Generate SARIF report."""
        return {
            "$schema": self.SCHEMA_URI,
            "version": self.SARIF_VERSION,
            "runs": [{
                "tool": {
                    "driver": {
                        "name": "VKG Security Analyzer",
                        "version": tool_info.get("version", "4.0.0"),
                        "informationUri": "https://github.com/your-org/vkg",
                        "rules": self._generate_rules(findings),
                    }
                },
                "results": [self._finding_to_result(f) for f in findings],
                "invocations": [self._generate_invocation(tool_info)],
            }]
        }

    def _finding_to_result(self, finding: UnifiedFinding) -> dict:
        """Convert unified finding to SARIF result."""
        return {
            "ruleId": finding.swc_id or finding.vulnerability_type,
            "level": self._severity_to_level(finding.severity),
            "message": {
                "text": self._combine_descriptions(finding.descriptions)
            },
            "locations": [{
                "physicalLocation": {
                    "artifactLocation": {
                        "uri": finding.file_path,
                        "uriBaseId": "%SRCROOT%"
                    },
                    "region": {
                        "startLine": finding.line_start,
                        "endLine": finding.line_end
                    }
                }
            }],
            "partialFingerprints": {
                "primaryLocationLineHash": self._hash_location(finding)
            },
            "properties": {
                "swcId": finding.swc_id,
                "tools": finding.tools,
                "confidence": finding.confidence,
                "severity": finding.severity,
            }
        }

    def _severity_to_level(self, severity: str) -> str:
        """Map severity to SARIF level."""
        mapping = {
            "critical": "error",
            "high": "error",
            "medium": "warning",
            "low": "note",
            "info": "none",
        }
        return mapping.get(severity, "warning")

    def _generate_rules(self, findings: List[UnifiedFinding]) -> List[dict]:
        """Generate SARIF rule definitions."""
        rules = {}
        for finding in findings:
            rule_id = finding.swc_id or finding.vulnerability_type
            if rule_id not in rules:
                rules[rule_id] = {
                    "id": rule_id,
                    "name": finding.vulnerability_type,
                    "shortDescription": {
                        "text": finding.vulnerability_type
                    },
                    "fullDescription": {
                        "text": f"SWC ID: {finding.swc_id}" if finding.swc_id else finding.vulnerability_type
                    },
                    "help": {
                        "text": "See SWC Registry for details"
                    },
                    "properties": {
                        "tags": [f"CWE-{finding.swc_id[-3:]}" if finding.swc_id else "security"]
                    }
                }
        return list(rules.values())
```

#### Deliverables

- [ ] `src/true_vkg/tools/base.py` - SecurityTool interface
- [ ] `src/true_vkg/tools/slither.py` - Slither integration
- [ ] `src/true_vkg/tools/aderyn.py` - Aderyn integration
- [ ] `src/true_vkg/tools/medusa.py` - Medusa integration
- [ ] `src/true_vkg/tools/halmos.py` - Halmos integration
- [ ] `src/true_vkg/tools/foundry.py` - Foundry integration
- [ ] `src/true_vkg/tools/deduplicator.py` - Deduplication engine
- [ ] `src/true_vkg/tools/orchestrator.py` - Tool orchestrator
- [ ] `src/true_vkg/tools/sarif.py` - SARIF generator
- [ ] CLI `vkg tools run` command
- [ ] CLI `vkg tools list` command
- [ ] CLI `vkg report` command (SARIF output)
- [ ] Tests for tool orchestration

#### Validation Gate

- [ ] Slither integration produces normalized findings
- [ ] Aderyn integration produces normalized findings
- [ ] Deduplication reduces findings by >20% on typical project
- [ ] SARIF output passes GitHub Code Scanning validation
- [ ] Comparison correctly identifies BSKG vs tool coverage

---

### Phase 0.4: Foundation Hardening (Week 5-6)

**Goal:** Fix builder.py extraction bugs to improve real-world detection rate.

#### Known Issues

From STATUS.md:

| Bug | Location | Impact | Priority |
|-----|----------|--------|----------|
| High-level call target tracking | builder.py:1446 | Misses delegatecall patterns | HIGH |
| High-level call data analysis | builder.py:1448 | Call data not tracked | HIGH |
| Strict equality detection | builder.py | Only checks require() | MEDIUM |
| Library call handling | builder.py | Address.functionCall() fails | MEDIUM |

#### Detection Targets (Damn Vulnerable DeFi)

| Challenge | Current | Target | Root Cause |
|-----------|---------|--------|------------|
| Truster | FAIL | PASS | Call target tracking bug |
| Unstoppable | FAIL | PASS | Strict equality bug |
| Side Entrance | FAIL | PASS | Callback detection |
| Free Rider | FAIL | PASS | Flash loan detection |
| Climber | FAIL | PASS | Complex multi-step |

#### Deliverables

- [ ] Fix call target tracking (builder.py:1446)
- [ ] Fix call data analysis (builder.py:1448)
- [ ] Improve strict equality detection
- [ ] Fix library call handling
- [ ] Run Damn Vulnerable DeFi benchmark
- [ ] Document detection rate improvement

#### Validation Gate

- [ ] Detection rate on DeFiHackLabs > 50% (up from ~30%)
- [ ] All builder.py bugs in STATUS.md addressed
- [ ] No regression in existing test suite (2,424+ tests)

---

## Phase 0 Summary

| Sub-Phase | Duration | Key Deliverable | Validation |
|-----------|----------|-----------------|------------|
| 0.1 Agentic Discovery | 2 weeks | AGENTS.md, skills/ | Claude Code discovers BSKG |
| 0.2 Beads Integration | 2 weeks | Task persistence | Tasks survive sessions |
| 0.3 Tool Orchestration | 2 weeks | Multi-tool pipeline | SARIF output valid |
| 0.4 Foundation Hardening | 2 weeks | builder.py fixes | Detection > 50% |

**Total Phase 0: 6 weeks** (can parallelize 0.1+0.2 and 0.3+0.4)

**Critical Gate:** No Phase 1 work until Phase 0 is complete.

---

## Part 5: Phase 1 - Two-Tier Pattern System (Weeks 7-10)

### Goal

Formalize the distinction between deterministic patterns (Tier A) and semantic reasoning patterns (Tier B).

---

### Phase 1.1: Pattern Schema Enhancement (Week 7)

#### Extended Pattern Schema

```yaml
# Full pattern schema with Tier A/B distinction

# Required fields
id: string                    # Unique identifier (e.g., "vm-001")
name: string                  # Human-readable name
description: string           # Detailed description

# Tier classification
tier: "A" | "B"               # Deterministic vs Semantic
type: "deterministic" | "semantic"

# Severity
severity: "critical" | "high" | "medium" | "low" | "info"

# Classification
swc_id: string                # SWC-107, etc.
cwe_id: string                # CWE-841, etc.
vulnerability_class: string   # "reentrancy", "access_control", etc.
lens: string[]                # ["value-movement", "authority"]

# Pattern matching (existing)
match:
  ALL: []                     # All conditions must match
  ANY: []                     # Any condition must match
  NONE: []                    # No condition must match

# Confidence (Tier A: fixed, Tier B: hypothesis)
confidence:
  initial: float              # Starting confidence (0.0-1.0)
  calibrated: bool            # Whether ECE-calibrated

# Output state (what happens when pattern matches)
output_state: "CONFIRMED" | "POTENTIAL" | "NEEDS_VERIFICATION"

# Verification steps (Tier B only)
verification_steps:
  - step: int
    action: string            # "analyze_*", "construct_*", "generate_*", "human_*"
    goal: string              # What this step accomplishes
    prompt: string            # LLM prompt template
    queries: string[]         # VQL queries to run
    evidence_required: string[] # What evidence to collect
    success_criteria: string  # What constitutes success
    branching:
      if_found: string        # "continue" | "goto_step_N" | "verdict_*"
      if_not_found: string
      if_inconclusive: string

# LLM reasoning hints (Tier B only)
llm_hints:
  domain_context: string      # Domain background
  related_exploits: []        # Real-world examples
  key_questions: string[]     # Questions LLM should answer
  common_false_positives: string[] # Known FP triggers

# Test scaffolds
test_templates:
  foundry: string             # Foundry test template
  medusa: string              # Medusa config template
  halmos: string              # Halmos spec template

# Evidence requirements
evidence:
  required: []                # Must be present for finding
  optional: []                # Nice to have

# Remediation
remediation:
  description: string         # How to fix
  code_example: string        # Example fix
  references: string[]        # Links to docs
```

#### Pattern Classification

Migrate existing 119 patterns to Tier A/B:

```python
TIER_CLASSIFICATION = {
    # Tier A: Deterministic (high precision, graph-only)
    "A": [
        "reentrancy-basic",           # state_write_after_external_call
        "weak-access-control",        # public + writes_state + !access_gate
        "unprotected-selfdestruct",   # selfdestruct + !access_gate
        "delegatecall-to-untrusted",  # delegatecall + !trusted_target
        "missing-reentrancy-guard",   # external_call + state_write + !guard
        # ... ~30 total
    ],

    # Tier B: Semantic (needs LLM verification)
    "B": [
        "flash-loan-price-manipulation",  # Needs economic analysis
        "business-logic-flaw",            # Needs intent understanding
        "oracle-manipulation",            # Needs market analysis
        "governance-attack",              # Needs voting power analysis
        "mev-extraction",                 # Needs economic modeling
        # ... ~89 total
    ],
}
```

---

### Phase 1.2: Confidence Calibration (Week 8)

#### Why Calibration Matters

Research shows LLM security predictions require explicit uncertainty quantification. A model that says "90% confident" should be correct 90% of the time.

#### Implementation

```python
class ConfidenceCalibrator:
    """Calibrate confidence scores for findings."""

    def __init__(self):
        self.calibration_data = []  # Historical predictions vs outcomes

    def calibrate_tier_a(self, finding: Finding) -> CalibratedConfidence:
        """
        Tier A: Fixed confidence based on pattern precision.

        We know from testing that vm-001 has 98% precision,
        so all vm-001 findings get 0.98 confidence.
        """
        pattern_precision = self.pattern_registry.get_precision(finding.pattern_id)

        return CalibratedConfidence(
            raw=1.0,  # Pattern matched
            calibrated=pattern_precision,
            method="pattern_precision",
        )

    def calibrate_tier_b(self,
                         finding: Finding,
                         llm_confidence: float,
                         reasoning_paths: List[str]) -> CalibratedConfidence:
        """
        Tier B: Self-consistency + ECE calibration.

        1. Run multiple reasoning paths (self-consistency)
        2. Apply ECE calibration from historical data
        """
        # Self-consistency: majority vote across reasoning paths
        verdicts = [self._extract_verdict(path) for path in reasoning_paths]
        agreement = max(verdicts.count(v) for v in set(verdicts)) / len(verdicts)

        # Base confidence from LLM
        base_confidence = llm_confidence

        # Apply self-consistency adjustment
        consistency_adjusted = base_confidence * agreement

        # Apply ECE calibration
        calibrated = self._apply_ece_calibration(consistency_adjusted)

        return CalibratedConfidence(
            raw=llm_confidence,
            self_consistency=agreement,
            calibrated=calibrated,
            method="self_consistency_ece",
            reasoning_paths_count=len(reasoning_paths),
        )

    def _apply_ece_calibration(self, confidence: float) -> float:
        """
        Apply Expected Calibration Error adjustment.

        Based on historical data: if we predict 0.8, how often are we right?
        Adjust so predicted confidence matches actual accuracy.
        """
        if not self.calibration_data:
            return confidence  # No data yet

        # Bin predictions and calculate actual accuracy per bin
        bins = self._calculate_calibration_bins()

        # Find appropriate bin
        for bin_lower, bin_upper, actual_accuracy in bins:
            if bin_lower <= confidence < bin_upper:
                return actual_accuracy

        return confidence

    def record_outcome(self, finding_id: str,
                       predicted_confidence: float,
                       actual_outcome: bool):
        """Record prediction vs outcome for calibration."""
        self.calibration_data.append({
            "finding_id": finding_id,
            "predicted": predicted_confidence,
            "actual": 1.0 if actual_outcome else 0.0,
            "timestamp": datetime.utcnow(),
        })

    def calculate_ece(self) -> float:
        """Calculate Expected Calibration Error."""
        if not self.calibration_data:
            return 0.0

        bins = self._calculate_calibration_bins()
        ece = 0.0
        total = len(self.calibration_data)

        for bin_lower, bin_upper, actual_accuracy in bins:
            bin_data = [d for d in self.calibration_data
                       if bin_lower <= d["predicted"] < bin_upper]
            if bin_data:
                avg_predicted = sum(d["predicted"] for d in bin_data) / len(bin_data)
                bin_weight = len(bin_data) / total
                ece += bin_weight * abs(actual_accuracy - avg_predicted)

        return ece
```

---

### Phase 1.3: Tier B Verification Engine (Week 9)

#### Verification Step Execution

```python
class TierBVerificationEngine:
    """Execute verification steps for Tier B patterns."""

    def __init__(self, llm: LLMClient, vkg: KnowledgeGraph, calibrator: ConfidenceCalibrator):
        self.llm = llm
        self.vkg = vkg
        self.calibrator = calibrator
        self.ppr = None  # Set in Phase 2

    async def verify(self, finding: PotentialFinding) -> VerifiedFinding:
        """Execute full verification workflow."""
        pattern = self.pattern_registry.get(finding.pattern_id)

        if pattern.tier == "A":
            # Tier A: Direct confirmation
            return VerifiedFinding(
                finding=finding,
                verdict="CONFIRMED",
                confidence=self.calibrator.calibrate_tier_a(finding),
            )

        # Tier B: Execute verification steps
        context = await self._get_context(finding)
        verification_results = []

        for step in pattern.verification_steps:
            result = await self._execute_step(step, finding, context)
            verification_results.append(result)

            # Handle branching
            if result.verdict == "REFUTED":
                return VerifiedFinding(
                    finding=finding,
                    verdict="FALSE_POSITIVE",
                    confidence=result.confidence,
                    verification_chain=verification_results,
                )

            if step.action.startswith("human_"):
                if self._should_escalate(step, result):
                    return VerifiedFinding(
                        finding=finding,
                        verdict="NEEDS_HUMAN",
                        confidence=result.confidence,
                        escalation_reason=step.goal,
                        verification_chain=verification_results,
                    )

        # Aggregate results with self-consistency
        final_confidence = self.calibrator.calibrate_tier_b(
            finding,
            llm_confidence=self._aggregate_confidence(verification_results),
            reasoning_paths=[r.reasoning for r in verification_results],
        )

        return VerifiedFinding(
            finding=finding,
            verdict="CONFIRMED" if final_confidence.calibrated > 0.8 else "POTENTIAL",
            confidence=final_confidence,
            verification_chain=verification_results,
        )

    async def _execute_step(self,
                            step: VerificationStep,
                            finding: PotentialFinding,
                            context: str) -> StepResult:
        """Execute single verification step."""

        # Build prompt from step template
        prompt = step.prompt.format(
            function=finding.function,
            contract=finding.contract,
            context=context,
            evidence=finding.evidence,
        )

        # Add domain hints
        if step.pattern.llm_hints:
            prompt += f"\n\nDomain Context: {step.pattern.llm_hints.domain_context}"
            if step.pattern.llm_hints.related_exploits:
                prompt += f"\n\nRelated Exploits: {', '.join(step.pattern.llm_hints.related_exploits)}"

        # Self-consistency: 3 reasoning paths
        responses = await asyncio.gather(*[
            self.llm.reason(prompt, temperature=0.3)
            for _ in range(3)
        ])

        # Majority vote
        verdicts = [self._extract_verdict(r) for r in responses]
        majority_verdict = max(set(verdicts), key=verdicts.count)
        agreement = verdicts.count(majority_verdict) / len(verdicts)

        return StepResult(
            step_id=step.step,
            action=step.action,
            verdict=majority_verdict,
            confidence=agreement,
            reasoning=responses[0].reasoning,  # Use first for explanation
            evidence=self._extract_evidence(responses),
        )

    async def _get_context(self, finding: PotentialFinding) -> str:
        """Get optimized context for finding."""
        if self.ppr:
            # Phase 2: PPR-based context
            seeds = self.ppr.seeds_from_finding(finding)
            scores = self.ppr.run(seeds)
            subgraph = self.ppr.extract_subgraph(scores)
            return self.ppr.serialize(subgraph)
        else:
            # Fallback: VQL-based extraction
            return self.vkg.extract_context(finding.function, max_depth=2)
```

---

### Phase 1.4: Test Scaffold Generation (Week 10)

#### Test Generation

```python
class TestScaffoldGenerator:
    """Generate test scaffolds for vulnerability verification."""

    def __init__(self, templates_path: Path):
        self.templates = self._load_templates(templates_path)
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(templates_path)
        )

    def generate_foundry_test(self, finding: Finding) -> str:
        """Generate Foundry test for vulnerability hypothesis."""
        template = self.jinja_env.get_template(
            f"{finding.vulnerability_class}/foundry.sol.jinja"
        )

        return template.render(
            contract_name=finding.contract,
            function_name=finding.function,
            function_signature=finding.signature,
            vulnerability_type=finding.vulnerability_class,
            attack_setup=self._generate_attack_setup(finding),
            attack_execution=self._generate_attack_execution(finding),
            attack_assertion=self._generate_attack_assertion(finding),
        )

    def generate_medusa_config(self, finding: Finding) -> dict:
        """Generate Medusa fuzzing configuration."""
        return {
            "fuzzing": {
                "testLimit": 10000,
                "corpusDirectory": f".vrs/corpus/{finding.id}",
                "targetContracts": [finding.contract],
            },
            "testing": {
                "propertyTesting": {
                    "enabled": True,
                    "testPrefixes": ["invariant_", "test_"],
                },
            },
            "compilation": {
                "platform": "foundry",
            },
        }

    def generate_halmos_spec(self, finding: Finding) -> str:
        """Generate Halmos specification."""
        template = self.jinja_env.get_template(
            f"{finding.vulnerability_class}/halmos.sol.jinja"
        )

        return template.render(
            contract_name=finding.contract,
            function_name=finding.function,
            preconditions=self._generate_preconditions(finding),
            postconditions=self._generate_postconditions(finding),
        )

    def _generate_attack_setup(self, finding: Finding) -> str:
        """Generate attack setup code."""
        setups = {
            "reentrancy": """
        // Deploy attacker contract
        Attacker attacker = new Attacker(address(target));
        // Fund target with ETH
        vm.deal(address(target), 10 ether);
        // Fund attacker
        vm.deal(address(attacker), 1 ether);
            """,
            "flash_loan": """
        // Setup flash loan provider
        MockFlashLoanProvider flashLoan = new MockFlashLoanProvider();
        flashLoan.setPool(address(target));
        // Fund pool
        deal(address(token), address(flashLoan), 1000000 ether);
            """,
            # ... more templates
        }
        return setups.get(finding.vulnerability_class, "// Setup here")
```

---

## Part 6: Phase 2 - Context Optimization (Weeks 11-14)

### Goal

Implement PPR-based retrieval for 5-10x context reduction while preserving vulnerability semantics.

---

### Phase 2.1: VKG-PPR Algorithm (Weeks 11-12)

See detailed specification in article analysis section.

Key points:
- Edge weighting using risk_score, guards_at_source, taint propagation
- Sequencing-aware traversal (temporal ordering preserved)
- Token-bounded subgraph extraction

---

### Phase 2.2: Query-to-Seed Mapping (Week 13)

Automatic seed selection from VQL queries and pattern matches.

---

### Phase 2.3: Serialization for LLM (Week 14)

Relation-path format optimized for multi-hop reasoning:

```
ENTRY: withdraw(uint256)
PATH 1: withdraw → CALLS_EXTERNAL → target.call{value}
        → WRITES_STATE → balances[msg.sender]
RISK: state_write_after_external_call = true
```

---

## Part 7: Phase 3-4 - Production Hardening (Weeks 15-20)

### Phase 3: Integration & Testing (Weeks 15-17)

- End-to-end workflow validation
- Performance benchmarking
- Real-world testing on DeFiHackLabs

### Phase 4: Documentation & Release (Weeks 18-20)

- User documentation
- API documentation
- Video tutorials
- Public release

---

## Part 8: Risk Assessment

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| PPR doesn't improve accuracy | Medium | Medium | Benchmark before full integration |
| Beads integration complexity | Low | High | Start simple, iterate |
| Tool orchestration flakiness | Medium | Medium | Graceful degradation |
| False positive increase from Tier B | Medium | High | Strict confidence thresholds |
| Token budget exceeded | Medium | Medium | Adaptive compression |

### Process Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Scope creep | Medium | High | Strict phase gates |
| builder.py not fixed first | High | Critical | Hard gate: Phase 0.4 before Phase 1 |
| Over-engineering retrieval | Medium | Medium | Tier 1 PPR only initially |

---

## Part 9: Success Metrics

### Phase 0 Success

- [ ] Claude Code discovers BSKG via AGENTS.md
- [ ] Tasks persist across LLM sessions
- [ ] SARIF output validates with GitHub
- [ ] Detection rate > 50% on real exploits

### Phase 1 Success

- [ ] 44 patterns classified Tier A/B
- [ ] Confidence calibration ECE < 0.1
- [ ] Test scaffolds compile 90%
- [ ] Tier B verification accuracy > 75%

### Phase 2 Success

- [ ] 5x context reduction
- [ ] No accuracy regression
- [ ] < 100ms retrieval time

### Ultimate Success

- [ ] **Detection rate > 80%** on known exploits
- [ ] **False positive rate < 15%** on production contracts
- [ ] **3x faster** than manual audit with same accuracy
- [ ] **70% LLM autonomy** (findings resolved without human)
- [ ] **GitHub Marketplace listing**

---

## Conclusion

VKG 4.0 represents a transformation from a "static analyzer with graph capabilities" to "the world's first LLM-native Solidity security orchestrator."

The key insight: **No unified Solidity security orchestrator exists today.** By implementing agentic discovery, task orchestration, multi-tool integration, and confidence-calibrated output, BSKG fills this gap.

**Build the boring stuff first. Then make it fast.**

The path to production is:
1. Make BSKG discoverable (AGENTS.md)
2. Make findings persistent (Beads)
3. Make BSKG comprehensive (tool orchestration)
4. Make BSKG reliable (foundation hardening)
5. Make BSKG intelligent (two-tier patterns)
6. Make BSKG efficient (PPR retrieval)

This is achievable in 20 weeks of focused work.

---

*Document Version: 4.0 Final | January 5, 2026*
