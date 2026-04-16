# Phase 3.1b: Gap Improvement Plan

**Created:** 2026-02-12
**Purpose:** Address all MEDIUM+ gaps found during assumption analysis that are NOT covered in `3.1b-RESEARCH.md`
**Scope:** Infrastructure gaps that would cause 3.1c friction, plus adversarial test corpus strategy
**Status:** ALL 11 GAPS RESOLVED (2026-02-12). Resolutions in `gap-resolutions/` directory, integrated into `context.md`.

---

## Gap Registry

| ID | Gap | Impact | Confidence | Affects Plans |
|----|-----|--------|------------|---------------|
| GAP-01 | Multi-agent observation correlation model | HIGH | HIGH | 3.1b-02, 3.1b-04 |
| GAP-02 | Graph query structured extraction | HIGH | HIGH | 3.1b-02 |
| GAP-03 | Companion plan ordering risk | MEDIUM | HIGH | 3.1b-01 (all) |
| GAP-04 | TranscriptParser extension mechanism | MEDIUM | MEDIUM | 3.1b-02 |
| GAP-05 | No orchestration scenario in corpus | MEDIUM | MEDIUM | 3.1b-06 |
| GAP-06 | Adversarial/trick test scenarios | HIGH | HIGH | 3.1b-06 |
| GAP-07 | Pattern-derived scenario generation | HIGH | HIGH | 3.1b-06 |
| GAP-08 | External vulnerability source integration | MEDIUM | HIGH | 3.1b-06 |
| GAP-09 | EvaluationGuidance adaptive escalation | MEDIUM | MEDIUM | 3.1b-05 |
| GAP-10 | Workflow category taxonomy as data | MEDIUM | MEDIUM | 3.1b-05, 3.1b-06 |
| GAP-11 | Failure classification model | MEDIUM | MEDIUM | 3.1b-02 |

---

## GAP-01: Multi-Agent Observation Correlation Model

### Problem

`OutputCollector.collect(workspace, session_id)` is designed for single-agent observation. A 3-agent debate (attacker + defender + verifier) produces 3+ transcripts, N cross-agent SendMessage exchanges, 3+ task histories. 3.1c-11 (orchestrator flow evaluation) needs to correlate observations across agents to evaluate:
- Evidence passing chains (attacker finding → verifier evaluation)
- Agreement quality (did agents converge through debate or rubber-stamp?)
- Coordination patterns (task handoffs, message timing)
- Per-agent reasoning quality within team context

### What Exists

- `EventStream` (controller_events.py, 159 LOC) already has `agents_spawned()`, `messages()`, `agent_by_type()`, `events_between()` — these handle event-level correlation
- `WorkspaceManager.get_transcript_paths()` maps agent_id → JSONL path
- Inbox files at `~/.claude/teams/{name}/inboxes/{agent}.json` contain full message history

### What's Missing

A `TeamObservation` model that links individual agent observations:

```python
@dataclass
class AgentObservation:
    agent_id: str
    agent_type: str  # attacker, defender, verifier
    transcript: TranscriptParser
    tool_calls: list[ToolCall]
    messages_sent: list[dict]  # from inbox
    messages_received: list[dict]
    task_history: list[dict]  # snapshots before completion

@dataclass
class TeamObservation:
    team_name: str
    agents: dict[str, AgentObservation]  # by agent_type
    message_graph: list[tuple[str, str, str]]  # (from, to, content_hash)
    task_flow: list[dict]  # ordered task state transitions

    def evidence_chain(self, finding_id: str) -> list[str]:
        """Trace which agents touched a finding and in what order."""
        ...

    def agreement_depth(self) -> float:
        """How many rounds of genuine debate before convergence?"""
        ...
```

### Investigation Steps

1. Read existing `EventStream` and `WorkspaceManager` code to understand what cross-agent data is already accessible
2. Examine real inbox file format from Research Spike 03 findings
3. Design `TeamObservation` as extension of `OutputCollector`, not replacement
4. Write unit tests with fixture data from 2-agent team (already verified in spike 03)
5. Verify backward compatibility — `OutputCollector` still works for single-agent scenarios

### Resolution Target

Add `TeamObservation` to `OutputCollector` scope in 3.1b-02. The `collect()` method detects team vs single-agent and returns appropriate model. 3.1c-11 gets structured team data without needing to parse raw inbox files.

### Tests

- Create 2-agent fixture: attacker sends finding → verifier evaluates → verdict
- Assert `TeamObservation.evidence_chain()` returns correct agent sequence
- Assert `TeamObservation.agents["attacker"].messages_sent` is non-empty
- Assert single-agent scenario still returns valid `CollectedOutput` (not `TeamObservation`)

---

## GAP-02: Graph Query Structured Extraction

### Problem

PHILOSOPHY.md's core differentiator is "graph-first reasoning." 3.1c-04 (Graph Value Scorer) must distinguish:
- **Checkbox compliance** (score < 30): Agent runs `alphaswarm query` but ignores results
- **Genuine graph use** (score > 70): Agent queries, cites results, builds conclusions from graph data

Current `TranscriptParser` has only `has_bskg_query() -> bool` and `bskg_query_index() -> int | None`. No structured extraction of what was queried, what came back, or whether results were cited.

### What Exists

- `has_bskg_query()` checks for `alphaswarm` in Bash commands
- `bskg_query_index()` returns the index of first such call
- `first_conclusion_index()` returns index of first text block after tools
- `get_bash_commands()` returns raw command strings

### What's Missing

```python
@dataclass
class BSKGQuery:
    query_text: str           # The actual query string
    query_type: str           # "pattern", "nl", "property"
    tool_call_index: int      # Position in transcript
    result_snippet: str       # First 500 chars of result
    result_node_count: int    # How many nodes returned (if parseable)
    cited_in_conclusion: bool # Was this result referenced later?

class TranscriptParser:
    # NEW methods
    def get_bskg_queries(self) -> list[BSKGQuery]:
        """Extract all BSKG queries with structured metadata."""
        ...

    def get_text_between_tools(self, start_idx: int, end_idx: int) -> str:
        """Extract reasoning text between tool calls."""
        ...

    def graph_citation_rate(self) -> float:
        """Fraction of BSKG queries whose results appear in subsequent text."""
        ...
```

### Investigation Steps

1. Read real transcripts from `~/.claude/projects/` to understand exact format of `alphaswarm query` calls and their results
2. Identify query types: `alphaswarm query "pattern:..."` vs `alphaswarm query "functions without..."` vs property queries
3. Design `BSKGQuery` extraction from `ToolCall` data (command parsing + result parsing)
4. Implement `cited_in_conclusion` by searching subsequent text blocks for result terms
5. Test with at least 2 real transcript fixtures (one with genuine graph use, one with checkbox compliance)

### Resolution Target

Add to 3.1b-02 TranscriptParser extensions. These methods are the single most important extension for 3.1c-04's Graph Value Scorer. Without them, the scorer must parse raw Bash commands and manually correlate with text — fragile and error-prone.

### Tests

- Parse transcript with `alphaswarm query "pattern:weak-access-control"` → assert `BSKGQuery.query_type == "pattern"`
- Parse transcript with NO alphaswarm calls → assert `get_bskg_queries()` returns empty list
- Parse transcript where query result is cited → assert `cited_in_conclusion == True`
- Parse transcript where query result is ignored → assert `cited_in_conclusion == False`
- Assert `graph_citation_rate()` is 0.0 for checkbox compliance, > 0.5 for genuine use

---

## GAP-03: Companion Plan Ordering Risk

### Problem

3.1b-01 (Companion bridge) is the first plan but has zero 3.1c consumers. No 3.1c plan depends on `CompanionBridge`. The 7 explicit API contracts for 3.1c readiness are: TranscriptParser, hooks, OutputCollector, EvaluationGuidance, observation directory, debrief research, SendMessage capture — none involve Companion.

If Companion integration hits issues (v0.19.1 → v0.20.3 version mismatch already noted in research, macOS platform quirks, `bun` dependency), it delays the critical-path plans that 3.1c actually needs.

### What the Research Says

3.1b-RESEARCH.md says Companion makes "Plan 3.1b-01 lower-risk than expected" — but this is about implementation risk, not schedule risk. The risk is that a non-critical plan blocks critical ones.

### Recommendation

**Reorder execution:** Start with plans that have direct 3.1c dependencies, parallelize Companion.

Proposed order:
```
Wave 1 (parallel):  02 (parser+collector) + 03 (hooks) + 06 (corpus)
Wave 2 (sequential): 04 (Agent Teams) — depends on 02, 03
Wave 3 (sequential): 05 (DSL) — depends on 04
Wave 4 (parallel):  01 (Companion) — independent, can run alongside Wave 2-3
Wave 5 (sequential): 07 (smoke test) — depends on all
```

### Resolution Target

Document this reordering recommendation in context.md. The `/gsd:plan-phase` executor should respect this order. Companion becomes non-blocking for the critical path.

---

## GAP-04: TranscriptParser Extension Mechanism

### Problem

3.1b-02 says `_records must remain accessible` for 3.1c to extend. But 3.1c needs to add 3+ methods (`get_text_between_tools`, `get_debrief_response`, `get_bskg_queries`). Without a documented extension pattern, this could be fragile.

### Investigation Steps

1. Read current `TranscriptParser.__init__` to understand how `_records` is populated
2. Check if any code instantiates `TranscriptParser` directly (vs through a factory)
3. Decide between: (a) direct method addition to class, (b) subclassing, (c) mixin pattern
4. Document the chosen pattern in 3.1b-02's plan

### Recommendation

**Direct method addition** is simplest and Python-idiomatic. Document that:
- `_records` is a stable internal attribute (list of parsed JSONL dicts)
- New methods should follow the existing naming pattern (`get_*`, `has_*`, `*_index`)
- No subclassing needed — 3.1c adds methods directly to `TranscriptParser`
- Add a version property: `TranscriptParser.API_VERSION = "3.1b"` so 3.1c can assert compatibility

---

## GAP-05: No Orchestration Scenario in Corpus

### Problem

The 10 curated scenarios are: 3 workflow, 5 Tier A vulnerability, 2 FP controls. All single-agent or single-skill. But 3.1c-11 needs to test full 3-agent team lifecycle — no scenario exists for this.

### Recommendation

Replace one Tier A slot or add an 11th scenario: **multi-agent-reentrancy-debate**.

```
examples/testing/multi-agent-reentrancy-debate/
  contracts/
    VulnerableVault.sol     # Classic reentrancy
    SafeVault.sol           # CEI pattern (FP control within same scenario)
  ground-truth.yaml
    expected_findings:
      - pattern_id: reentrancy-001
        function: withdraw
        line_range: [45, 52]
    expected_team_behavior:
      - attacker_identifies_vulnerability: true
      - defender_checks_for_guards: true
      - verifier_arbitrates: true
      - evidence_passes_between_agents: true
  scenario.yaml
    agent_team:
      roles: [attacker, defender, verifier]
      model: sonnet
    evaluation_guidance:
      reasoning_questions:
        - "Did the attacker construct a concrete exploit path?"
        - "Did the defender check for reentrancy guards?"
        - "Did the verifier cite evidence from both sides?"
```

### Resolution Target

Add to 3.1b-06 corpus scope. This is the only scenario that exercises the team observation model (GAP-01).

---

## GAP-06: Adversarial / Trick Test Scenarios

### Problem

The current corpus only tests "can the framework detect real vulnerabilities?" It does NOT test "can the framework resist being tricked?" A robust testing framework must include adversarial scenarios that test the framework's reasoning depth vs surface-level pattern matching.

### Training Data Contamination (CRITICAL)

**All well-known vulnerable contracts are in LLM training data.** Ethernaut, DamnVulnerableDeFi, Capture the Ether, kadenzipfel examples, SWC test cases — any LLM from early 2025 onward has memorized these. This means:

- Testing with known examples tests **recall of memorized answers**, NOT reasoning ability
- An agent that "detects" the Ethernaut reentrancy challenge may be pattern-matching from training data, not actually analyzing the code
- Even modified names/comments won't help if the contract structure is recognizable
- **Every curated scenario must be ORIGINAL** — contracts that don't exist in any public repo

**Implication:** External sources (GAP-08) should be used for INSPIRATION and category coverage, but the actual test contracts must be novel compositions that cannot be memorized. The adversarial guidelines must produce truly new contracts where the ONLY way to detect the vulnerability is through genuine behavioral analysis.

### What the Research Doesn't Cover

3.1b-RESEARCH.md covers standard evaluation patterns (tasks + trials + graders) but says nothing about adversarial testing, honeypot-style contracts, or name-obfuscation attacks.

### Adversarial Scenario Categories

#### Category A: Name Obfuscation (Behavior vs Names)
The core philosophy is "Names lie. Behavior does not." Test this directly.

| Trick | What It Tests | Example |
|-------|---------------|---------|
| Renamed withdraw | Name-independence | `processPayment()` does `R:bal -> X:out -> W:bal` |
| Misleading function names | Semantic operation detection | `safeTransfer()` that is actually unsafe |
| Internal function hiding | Cross-function analysis | Vulnerability hidden 3 calls deep: `public A() → internal B() → private C()` where C has the bug |
| Dead code red herring | Reachability analysis | Vulnerable function exists but is never callable |
| Safe pattern that looks vulnerable | False positive resistance | CEI pattern with confusing variable names |

#### Category B: Protocol Complexity Tricks
| Trick | What It Tests | Example |
|-------|---------------|---------|
| Multi-contract vulnerability | Cross-contract reasoning | Bug only appears when Contract A calls Contract B |
| Proxy pattern vulnerability | Upgrade-aware analysis | Vulnerability in implementation, not proxy |
| Callback exploitation | Call graph analysis | ERC777 callbacks enabling reentrancy |
| State machine violation | State ordering analysis | Functions callable in wrong order |
| Economic attack hidden in math | Economic reasoning | Rounding error that enables profit extraction |

#### Category C: Honeypot Inversions
Contracts that LOOK vulnerable but ARE safe (or vice versa).

| Trick | What It Tests | Example |
|-------|---------------|---------|
| Fake vulnerability bait | FP rate under pressure | Contract has `selfdestruct` but it's behind proper access control |
| Hidden guard deep in inheritance | Guard discovery | `onlyOwner` is in a grandparent contract, 4 levels up |
| Reentrancy with hidden mutex | Guard detection | Custom reentrancy lock using storage slot, not OpenZeppelin |
| "Vulnerable" function that reverts | Dead path analysis | Withdraw function always reverts due to impossible require condition |

### Guidelines for Generating Adversarial Scenarios

Create `examples/testing/guidelines/adversarial-template.md`:

```markdown
# Adversarial Scenario Generation Guide

## Purpose
Create contracts designed to TRICK the detection framework.
A good adversarial scenario exposes a specific weakness in the detection pipeline.

## Generation Process

### Step 1: Pick a Target Pattern
Choose a pattern from vulndocs/ (e.g., `reentrancy-001-classic`).

### Step 2: Choose a Trick Category
- A: Name obfuscation (rename functions, mislead with comments)
- B: Protocol complexity (hide across contracts, add proxies)
- C: Honeypot inversion (make safe look vulnerable, or vulnerable look safe)

### Step 3: Write the Contract
- START from a known-vulnerable template from the pattern's test contracts
- APPLY the trick (rename, restructure, add dead code, etc.)
- DOCUMENT what specifically was changed and WHY it should trick the tool

### Step 4: Define Ground Truth
ground-truth.yaml must specify:
- `adversarial_category`: A/B/C
- `trick_applied`: description of the obfuscation
- `expected_detection`: true/false (should the framework find this?)
- `detection_difficulty`: what reasoning depth is needed
- `false_positive_expected`: true/false (is this a FP trap?)

### Step 5: Define Success Criteria
- If expected_detection=true: Framework finds the real vulnerability despite the trick
- If expected_detection=false (FP trap): Framework correctly reports NO vulnerability
- Framework's reasoning should EXPLAIN why it wasn't tricked (or was)

## Quality Criteria for Adversarial Scenarios
- Contract compiles without errors
- Trick is non-obvious (a human reviewer would need > 30 seconds to see through it)
- At least one false path exists (something that looks like a vulnerability but isn't)
- Ground truth is specific (pattern_id, function_name, line_range)
- The trick tests a SPECIFIC detection capability, not general "hardness"
```

### Resolution Target

Add adversarial scenario guidelines to 3.1b-06. Create at least 2-3 adversarial scenarios in the 10 curated set (replacing generic Tier A slots). This directly validates the "names lie, behavior does not" philosophy.

### Tests

- Adversarial scenario with renamed `withdraw` → framework still detects reentrancy
- FP trap scenario with unreachable vulnerable code → framework reports no finding
- Hidden guard scenario → framework identifies the guard and reports safe

---

## GAP-07: Pattern-Derived Scenario Generation

### Problem

466 active patterns exist across 18 categories. The 10 curated scenarios can only cover a fraction. The dynamic generation guidelines need a concrete method to CREATE scenarios FROM patterns.

### What Exists

Each pattern in vulndocs/ has:
- `detection_logic` — BSKG queries that should match
- `required_properties` — Properties the vulnerable function must have
- `exploit_scenario` — Narrative description of the attack
- `remediation` — How to fix it
- `tier` — A (deterministic), B (LLM-verified), C (label-dependent)

### Pattern-to-Scenario Generation Pipeline

```
For each pattern P:
  1. Read P.detection_logic → extract required_properties
  2. Read P.exploit_scenario → extract attack narrative
  3. Generate VULNERABLE contract:
     - Create function with required_properties (R:bal, X:out, W:bal for reentrancy)
     - Name functions with domain-appropriate names (not generic)
     - Add realistic context (other functions, state variables, events)
  4. Generate SAFE variant:
     - Same structure but with proper guards (CEI, mutex, access control)
     - OR: Pattern not applicable (different behavioral signature)
  5. Generate ground-truth.yaml:
     - pattern_id: P.id
     - expected_properties: P.required_properties
     - expected_behavioral_signature: P.detection_logic.signature
     - severity: P.severity
  6. Generate evaluation_guidance:
     - reasoning_questions derived from P.exploit_scenario
     - check_graph_usage: true if P.tier in [A, B]
     - expected_reasoning_chain from P's detection logic
```

### Category-Specific Guidelines

| Category | Pattern Count | Generation Strategy |
|----------|--------------|---------------------|
| access-control (212) | Sample 5 representative subcategories: missing-access, tx-origin, ownership-transfer, role-escalation, initialize-front-run | Each gets vulnerable + safe variant |
| reentrancy (105) | Sample 3: classic, cross-function, read-only | Vary CEI ordering, mutex patterns |
| logic (57) | Sample 3: state-machine, business-logic, edge-case | Complex multi-step scenarios |
| dos (49) | Sample 2: unbounded-loop, griefing | Gas limit edge cases |
| oracle (19) | Sample 2: stale-price, manipulation | Requires economic context |
| upgrade (35) | Sample 2: uninitialized-proxy, storage-collision | Requires proxy pattern understanding |
| Others (188) | Sample 1 per remaining major category | Tier A only for initial coverage |

### External Sources for Inspiration

| Source | URL | Vulnerability Count | Use Case |
|--------|-----|-------------------|----------|
| kadenzipfel/smart-contract-vulnerabilities | github.com/kadenzipfel/smart-contract-vulnerabilities | ~30 categories | Real-world vulnerability descriptions with code examples |
| SWC Registry | swcregistry.io | 37 weakness types | Standardized weakness classification with test cases |
| Ethernaut | ethernaut.openzeppelin.com | 40 levels | Progressive difficulty, includes delegatecall, privacy, proxy |
| DamnVulnerableDeFi | damnvulnerabledefi.xyz | 18 challenges | Already in examples/testing/ (53 contracts) |
| Capture the Ether | capturetheether.com | 20 challenges | Randomness, math, accounts, miscellaneous |
| not-so-smart-contracts | github.com/crytic/not-so-smart-contracts | ~15 categories | Trail of Bits curated, minimal examples |
| SmartBugs | github.com/smartbugs/smartbugs | 143 contracts | Curated dataset with ground truth labels |

### Training Data Contamination Rule

**No test contract may be a recognizable derivative of a public CTF/educational contract.** External sources provide CATEGORY COVERAGE and INSPIRATION, not templates. The generation pipeline must:

1. Use pattern detection_logic as the behavioral specification (not a known contract as template)
2. Invent novel business contexts (lending, staking, DAO voting, NFT marketplace, etc.)
3. Add realistic surrounding code (events, view functions, admin logic) that doesn't exist anywhere
4. Vary Solidity patterns (custom errors vs require strings, named returns vs explicit, assembly vs high-level)
5. Verify novelty: the contract should NOT be findable via code search on GitHub/Etherscan

### Integration Strategy

1. **Mine external sources for CATEGORY GAPS** — identify vulnerability types not in vulndocs, not contract templates
2. **Cross-reference with SWC** — map each vulndocs pattern to SWC ID where applicable (vulndocs/.meta/references/swc-mapping.yaml already exists)
3. **NEVER copy external contracts** — use them to understand vulnerability mechanics, then write original code with novel business logic
4. **Combine vulnerability types** — e.g., reentrancy + access control in a single contract with novel context
5. **Create "impossible to memorize" variants** — scenarios where structural recognition fails and only behavioral analysis works

### Resolution Target

Enhance 3.1b-06 guidelines with:
1. Pattern-to-scenario generation pipeline in `examples/testing/guidelines/pattern-derived-template.md`
2. External source mapping in `examples/testing/guidelines/external-sources.yaml`
3. Category coverage matrix showing which patterns each scenario tests

### Tests

- For each curated scenario, verify pattern_id in ground-truth maps to active pattern in vulndocs/
- For dynamic generation guidelines, verify at least 1 sample scenario can be generated from template
- Verify SWC mapping covers all 10 curated scenario vulnerabilities

---

## GAP-08: External Vulnerability Source Integration

### Problem

3.1b-RESEARCH.md covers automation infrastructure but says nothing about WHERE vulnerability scenarios come from. The existing examples/testing/ has 18 DVDeFi challenges but zero ground-truth files. External sources (kadenzipfel, SWC, Ethernaut, SmartBugs) have hundreds of categorized vulnerabilities that could enrich the corpus.

### Investigation Steps

1. **Clone/fetch kadenzipfel/smart-contract-vulnerabilities** — inventory categories and code examples
2. **Map kadenzipfel categories → vulndocs categories** — identify overlap and gaps
3. **Identify "hard to detect" vulnerabilities** from external sources:
   - Cross-function reasoning required
   - Protocol context required
   - Economic reasoning required
   - Proxy/upgrade pattern understanding required
4. **Create conversion script** for external → scenario format:
   - Extract Solidity code
   - Generate ground-truth.yaml from description
   - Classify by tier (A/B/C)
5. **Select top 5 external examples** that are NOT in DVDeFi and add to curated corpus

### External Vulnerability Categories NOT Well Covered by DVDeFi

| Category | External Source | Why Needed |
|----------|---------------|------------|
| tx.origin phishing | kadenzipfel, Ethernaut Level 4 | Tests auth pattern detection |
| Storage collision (proxy) | Ethernaut Levels 6, 16, 24 | Tests upgrade-aware analysis |
| Predictable randomness | CTE Lotteries, Ethernaut Level 3 | Tests crypto pattern detection |
| Signature replay | SWC-121, kadenzipfel | Tests crypto reasoning |
| Delegatecall abuse | Ethernaut Levels 6, 16 | Tests cross-contract analysis |
| Integer overflow (pre-0.8) | SWC-101, Ethernaut Level 5 | Tests arithmetic detection |
| Force-feeding ether | Ethernaut Level 7 | Tests assumption detection |
| Privacy misconceptions | Ethernaut Level 12 | Tests state visibility understanding |
| Storage array manipulation | Ethernaut Level 19 | Tests deep EVM knowledge |

### Resolution Target

Add external source integration to 3.1b-06:
1. `examples/testing/guidelines/external-sources.yaml` — maps external vulnerability CATEGORIES to vulndocs categories (not contracts)
2. At least 3 of the 10 curated scenarios should cover vulnerability types FROM external sources — but with **100% original contracts** (see GAP-06 Training Data Contamination Rule)
3. Ground-truth files include `inspiration_source` field (e.g., "SWC-107 reentrancy pattern") but the contract itself must be novel
4. **No contract from any external source should be used directly or modified** — only the vulnerability mechanics inform original contract creation

---

## GAP-09: EvaluationGuidance Adaptive Escalation

### Problem

Current `evaluation_guidance` is static YAML. The evaluator brain (Claude Code in 3.1c) would benefit from conditional escalation rules: "if X observed, also check Y."

### Proposed Schema Extension

```yaml
evaluation_guidance:
  reasoning_questions: [...]
  hooks_if_failed: [...]
  check_graph_usage: true

  # NEW: Adaptive escalation (optional)
  escalation_rules:
    - condition: no_bskg_queries
      actions:
        - enable_hooks: [PreToolUse, PostToolUse]
        - add_questions:
          - "Why were no graph queries executed?"
          - "What alternative evidence sources were used?"
    - condition: all_findings_low_confidence
      actions:
        - enable_hooks: [SubagentStart, SubagentStop]
        - add_questions:
          - "Were agents given sufficient context?"
    - condition: execution_under_10_seconds
      actions:
        - flag: possible_fabrication
        - add_questions:
          - "Was real analysis performed or cached results returned?"
```

### Resolution Target

Add `escalation_rules` as an **optional** field in the scenario DSL schema (3.1b-05). 3.1b parses and preserves it; 3.1c implements the execution logic. This costs nothing to add to the schema now but enables truly adaptive evaluation later.

---

## GAP-10: Workflow Category Taxonomy as Data

### Problem

3.1c's smart selection matrix depends on categorizing workflows (investigation, tool integration, orchestration, support). This taxonomy exists only in prose.

### Proposed Data Structure

```yaml
# examples/testing/guidelines/workflow-categories.yaml
categories:
  investigation:
    description: "Deep vulnerability analysis with graph reasoning"
    skills: [vrs-audit, vrs-investigate, vrs-verify, vrs-discover]
    agents: [vrs-attacker, vrs-defender, vrs-verifier]
    evaluation_dimensions:
      - graph_utilization
      - evidence_quality
      - reasoning_depth
      - hypothesis_testing
    required_hooks: [PreToolUse, PostToolUse, SubagentStart, SubagentStop]

  tool_integration:
    description: "External tool coordination and result synthesis"
    skills: [vrs-tool-slither, vrs-tool-aderyn, vrs-tool-mythril, vrs-tool-coordinator]
    agents: []
    evaluation_dimensions:
      - tool_selection
      - result_interpretation
      - finding_deduplication
    required_hooks: [PreToolUse, PostToolUse]

  orchestration:
    description: "Multi-agent coordination and team lifecycle"
    skills: [vrs-audit, vrs-debate]
    agents: [vrs-attacker, vrs-defender, vrs-verifier, vrs-integrator]
    evaluation_dimensions:
      - coordination_quality
      - evidence_passing
      - verdict_grounding
      - debate_depth
    required_hooks: [SubagentStart, SubagentStop, TeammateIdle, TaskCompleted]

  support:
    description: "Utility workflows with deterministic expected output"
    skills: [vrs-health-check, vrs-bead-create, vrs-bead-update, vrs-bead-list, vrs-orch-spawn]
    agents: []
    evaluation_dimensions:
      - output_correctness
      - error_handling
    required_hooks: []
```

### Resolution Target

Add to 3.1b-06 guidelines as `workflow-categories.yaml`. This becomes the source of truth that 3.1c-06 (evaluation contracts) references for smart selection.

---

## GAP-11: Failure Classification Model

### Problem

When a scenario fails, the framework needs to classify WHY to route the failure correctly. Without classification, every failure requires manual triage.

### Proposed Model

```python
from enum import Enum

class FailureCategory(Enum):
    INFRASTRUCTURE = "infrastructure"    # Hook didn't fire, Companion crashed, CLI error
    CAPABILITY = "capability"            # Agent crashed, wrong tools, output schema violation
    REASONING = "reasoning"              # Agent ran but reasoned poorly, missed vulnerability
    GROUND_TRUTH = "ground_truth"        # Expected finding was wrong, scenario needs update
    FLAKY = "flaky"                      # Passed sometimes, failed sometimes (stochastic)

@dataclass
class ClassifiedFailure:
    category: FailureCategory
    evidence: str               # What observation led to this classification
    suggested_action: str       # What to do about it
    confidence: float           # How confident in classification (0-1)

def classify_failure(output: CollectedOutput, ground_truth: dict) -> ClassifiedFailure:
    """Basic rule-based failure classifier."""

    # Infrastructure failures
    if output.exit_code != 0:
        return ClassifiedFailure(INFRASTRUCTURE, f"Exit code {output.exit_code}", "Fix CLI/hook setup", 0.9)
    if output.total_cost_usd == 0:
        return ClassifiedFailure(INFRASTRUCTURE, "Zero cost = no API call", "Check API connectivity", 0.95)

    # Capability failures
    if len(output.tool_calls) == 0:
        return ClassifiedFailure(CAPABILITY, "No tools used", "Check skill prompt", 0.8)
    if output.transcript_chars < 200:
        return ClassifiedFailure(CAPABILITY, "Minimal output", "Check agent prompt/permissions", 0.7)

    # Reasoning failures (everything else where output exists but findings don't match)
    return ClassifiedFailure(REASONING, "Output produced but incorrect", "Review reasoning chain", 0.6)
```

### Resolution Target

Add `FailureCategory` enum and basic `classify_failure()` to OutputCollector module (3.1b-02). The full classification logic belongs in 3.1c, but the data model and basic heuristic should be in infrastructure.

---

## Execution Priority

### Must-Have Before Planning (resolve during `/gsd:plan-phase`)

| Priority | Gap | Action |
|----------|-----|--------|
| P0 | GAP-03 | Reorder plans: 02+03+06 first, 01 parallel later |
| P0 | GAP-06 | Add adversarial guidelines to 3.1b-06 scope |
| P0 | GAP-07 | Add pattern-derived generation pipeline to 3.1b-06 |
| P0 | GAP-01 | Add TeamObservation to 3.1b-02 OutputCollector scope |
| P0 | GAP-02 | Add BSKGQuery extraction to 3.1b-02 parser scope |

### Should-Have (include in plans if feasible)

| Priority | Gap | Action |
|----------|-----|--------|
| P1 | GAP-08 | Add external source mapping to 3.1b-06 guidelines |
| P1 | GAP-05 | Add 1 orchestration scenario to curated 10 |
| P1 | GAP-10 | Add workflow-categories.yaml to 3.1b-06 |
| P1 | GAP-11 | Add FailureCategory to 3.1b-02 OutputCollector |

### Nice-to-Have (add schema slots, implement in 3.1c)

| Priority | Gap | Action |
|----------|-----|--------|
| P2 | GAP-09 | Add escalation_rules schema slot to 3.1b-05 |
| P2 | GAP-04 | Document extension pattern in 3.1b-02 |

---

## Verification Criteria

This gap plan is resolved when:

1. Every P0 gap has a concrete resolution documented in the plan for its affected 3.1b plan
2. Every P1 gap is either incorporated or explicitly deferred with rationale
3. The adversarial scenario guidelines exist and include at least 3 trick categories
4. The pattern-derived generation pipeline is documented with at least 1 worked example
5. The plan execution order reflects GAP-03 (Companion deprioritized)
6. 3.1c dependency matrix shows zero unresolved API contracts

---

*Gap analysis based on: 3.1b context.md, 3.1b PHILOSOPHY.md, 3.1c PHILOSOPHY.md, docs/PHILOSOPHY.md, 3.1b-RESEARCH.md, codebase exploration (686 patterns, 53 contracts, 1,003 LOC harness), and external vulnerability source research.*
