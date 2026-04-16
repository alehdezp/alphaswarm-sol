# Unified Agentic Testing Engine

## The Vision: Claude Code as Human QA Operator

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    AGENTIC TESTING ENGINE                                   │
│                                                                             │
│   Claude Code acting as a HUMAN QA OPERATOR that:                           │
│   • Launches workflows via claude-code-agent-teams (like a human in terminal)                  │
│   • Observes execution (reads transcripts, watches progress)                │
│   • Evaluates quality (compares to expectations, judges correctness)        │
│   • Debugs failures (investigates root cause, proposes fixes)               │
│   • Improves iteratively (learns from failures, refines tests)              │
│   • Reports honestly (produces real metrics, admits gaps)                   │
│                                                                             │
│   NOT a test script. NOT a CI pipeline. A THINKING OPERATOR.                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## How The Phases Align

### Current State Analysis

| Phase | Purpose | Status | Key Innovation |
|-------|---------|--------|----------------|
| **7.3.1.5** | Execution orchestrator | Planned (16 plans) | claude-code-controller + 70 scenarios |

**Full claude-code-controller documentation:** See `.planning/testing/rules/claude-code-controller-REFERENCE.md` and `.planning/testing/rules/canonical/claude-code-controller-instructions.md`
| **7.3.2** | Evidence collection | Design complete | Cryptographic proof tokens |
| **7.3.3** | Adversarial validation | Design complete | Binary gauntlet challenges |
| **7.3.4** | User perspective | Design complete | Fresh user simulation |
| **7.3.5** | External benchmarking | Design complete | Tool comparison + CVEs |
| **7.3.6** | Continuous operation | Design complete | Perpetual pipeline |

### The Synthesis

```
                    7.3.1.5: EXECUTION LAYER
                    ━━━━━━━━━━━━━━━━━━━━━━━━
                    claude-code-controller orchestration
                    70+ scenario matrix
                    worktree isolation
                    debug mode artifacts
                    evidence packs
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
  ┌───────────┐      ┌───────────┐      ┌───────────┐
  │  7.3.2    │      │  7.3.3    │      │  7.3.4    │
  │ Evidence  │      │ Gauntlet  │      │ User      │
  │ Protocol  │      │           │      │ Journey   │
  └─────┬─────┘      └─────┬─────┘      └─────┬─────┘
        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
                           ▼
                    ┌───────────┐
                    │  7.3.5    │
                    │ Benchmark │
                    └─────┬─────┘
                          │
                          ▼
                    ┌───────────┐
                    │  7.3.6    │
                    │ Continuous│
                    └───────────┘
```

**7.3.1.5 is the HOW. 7.3.2-7.3.6 are the WHAT.**

---

## Unified Architecture

### The Agentic Testing Engine

```yaml
name: AlphaSwarm Agentic Testing Engine (ATE)
version: "1.0"

entry_point: /vrs-full-testing

layers:
  execution:
    component: Phase 7.3.1.5
    responsibility: "Run workflows via claude-code-controller in alphaswarm-claude-code-agent-teams-session"
    tools: [claude-code-controller, worktrees, snapshots]

  evidence:
    component: Phase 7.3.2
    responsibility: "Collect and validate execution proofs"
    outputs: [bskg_proof, agent_proof, debate_proof, detection_proof]

  validation:
    component: Phase 7.3.3
    responsibility: "Run adversarial gauntlet challenges"
    challenges: [reentrancy, needle_haystack, fp_trap, multi_agent, economic]

  perspective:
    component: Phase 7.3.4
    responsibility: "Validate from fresh user perspective"
    tests: [readme_install, silent_mode, error_recovery, cross_platform]

  benchmarking:
    component: Phase 7.3.5
    responsibility: "Compare to external ground truth"
    comparisons: [slither, mythril, audits, cves, dvd]

  continuity:
    component: Phase 7.3.6
    responsibility: "Maintain perpetual validation"
    triggers: [git_hook, nightly, weekly, cve_new, user_feedback]
```

---

## The Human Operator Model

### What A Human QA Operator Does

```
1. PLAN: "Today I'm going to test the reentrancy detection"
2. SETUP: Opens terminal, navigates to project, prepares test contract
3. EXECUTE: Runs the tool, watches output
4. OBSERVE: Notes what happens, captures interesting output
5. EVALUATE: "Did it detect the bug? Was the finding correct?"
6. DEBUG: If something fails, investigates why
7. FIX: Either fixes the test or reports a product bug
8. REPEAT: Tries again, moves to next test
9. REPORT: Summarizes findings, metrics, gaps
```

### How Claude Code Replicates This

```yaml
human_action: "Opens terminal"
claude_code: |
  Uses claude-code-controller to create session: alphaswarm-claude-code-agent-teams-session
  Creates worktree for isolation

human_action: "Runs the tool"
claude_code: |
  Sends command via claude-code-agent-teams: /vrs-audit contracts/
  Waits for completion or timeout

human_action: "Watches output"
claude_code: |
  Captures transcript via claude-code-agent-teams-capture-pane
  Parses for stage markers, errors, findings

human_action: "Evaluates results"
claude_code: |
  Compares findings to ground truth
  Validates evidence chain
  Checks proof tokens

human_action: "Debugs failures"
claude_code: |
  Reads debug-mode artifacts
  Traces through execution log
  Identifies root cause

human_action: "Fixes issues"
claude_code: |
  If test issue: Updates test
  If product issue: Reports with evidence
  If config issue: Fixes and re-runs

human_action: "Reports findings"
claude_code: |
  Generates metrics (precision, recall)
  Produces honest assessment
  Documents gaps and improvements
```

---

## Novel Creative Ideas for the Unified Engine

### Idea 1: The Cognitive Workflow Graph

Instead of linear test execution, model workflows as a directed graph where the operator (Claude Code) can:

```yaml
cognitive_workflow_graph:
  nodes:
    - id: start
      type: decision
      question: "What should I test next?"
      options: [scenario, gauntlet, benchmark, regression]

    - id: scenario_runner
      type: execution
      uses: 7.3.1.5
      produces: [evidence_pack, debug_artifacts]

    - id: evidence_validator
      type: evaluation
      uses: 7.3.2
      consumes: evidence_pack
      produces: [proof_validation_result]

    - id: failure_investigator
      type: analysis
      triggers_on: failure
      uses: [debug_artifacts, transcripts]
      produces: [root_cause_hypothesis]

    - id: fix_proposer
      type: reasoning
      consumes: root_cause_hypothesis
      produces: [fix_proposal]

    - id: improvement_executor
      type: execution
      consumes: fix_proposal
      modifies: [patterns, agents, skills]

  edges:
    - from: start
      to: scenario_runner
      condition: "next_action == scenario"

    - from: scenario_runner
      to: evidence_validator
      condition: "execution_complete"

    - from: evidence_validator
      to: failure_investigator
      condition: "validation_failed"

    - from: failure_investigator
      to: fix_proposer
      condition: "root_cause_identified"

    - from: fix_proposer
      to: improvement_executor
      condition: "fix_approved"

    - from: improvement_executor
      to: start
      condition: "always"  # Loop back
```

### Idea 2: The Self-Aware Testing Agent

An agent that not only runs tests but reasons about testing strategy:

```yaml
self_aware_testing_agent:
  capabilities:
    - "I know which patterns have been tested recently"
    - "I know which scenarios have failed before"
    - "I can prioritize based on risk and coverage gaps"
    - "I can explain my testing decisions"

  reasoning_examples:
    - input: "What should I test next?"
      reasoning: |
        Looking at coverage map:
        - Reentrancy patterns: 85% covered, last tested 2 days ago
        - Oracle patterns: 60% covered, last tested 1 week ago
        - Access control: 95% covered, regression yesterday

        Priority: Oracle patterns (lowest coverage, oldest test)
        Decision: Run S17-S24 from scenario matrix

    - input: "Test S17 failed. What now?"
      reasoning: |
        Failure: Expected oracle staleness detection, got nothing
        Debug artifacts show:
        - Graph built successfully (245 nodes)
        - Pattern matched but confidence = 0.3 (below threshold)
        - Agent investigation found no evidence

        Root cause hypothesis: Pattern threshold too strict
        Proposed fix: Lower threshold from 0.5 to 0.3 for oracle patterns
        OR: Improve oracle label detection in graph builder

        Decision: Investigate label overlay first, then adjust threshold
```

### Idea 3: The Observability-First Design

Every layer produces observable metrics that the operator can reason about:

```yaml
observability_layers:
  execution_layer:
    metrics:
      - scenario_completion_rate
      - average_execution_time
      - claude-code-agent-teams_session_health
      - worktree_snapshot_count
    alerts:
      - "Execution taking > 5 minutes (expected < 2)"
      - "claude-code-agent-teams session crashed"
      - "Worktree disk space low"

  evidence_layer:
    metrics:
      - proof_validation_rate
      - evidence_completeness_score
      - cross_reference_validity
    alerts:
      - "BSKG proof missing for last 3 runs"
      - "Agent spawn proof has gaps"
      - "Detection proof chain broken"

  validation_layer:
    metrics:
      - gauntlet_pass_rate
      - per_challenge_scores
      - improvement_trend
    alerts:
      - "Reentrancy gauntlet dropped from 10/10 to 8/10"
      - "FP trap gauntlet failing consistently"

  benchmark_layer:
    metrics:
      - precision
      - recall
      - f1_score
      - vs_slither_delta
      - vs_mythril_delta
    alerts:
      - "Precision dropped > 5% from last week"
      - "Recall below target threshold"

operator_dashboard: |
  ╔══════════════════════════════════════════════════════════════╗
  ║  AGENTIC TESTING ENGINE DASHBOARD                            ║
  ╠══════════════════════════════════════════════════════════════╣
  ║                                                              ║
  ║  Current Status: ◆ INVESTIGATING FAILURE                    ║
  ║                                                              ║
  ║  ┌────────────────────────────────────────────────────────┐ ║
  ║  │ Execution Layer                                         │ ║
  ║  │ Scenarios: 58/70 passed │ Avg time: 1m 42s │ Health: ✓  │ ║
  ║  └────────────────────────────────────────────────────────┘ ║
  ║                                                              ║
  ║  ┌────────────────────────────────────────────────────────┐ ║
  ║  │ Evidence Layer                                          │ ║
  ║  │ Proofs: 95% valid │ Completeness: 88% │ Chains: ✓      │ ║
  ║  └────────────────────────────────────────────────────────┘ ║
  ║                                                              ║
  ║  ┌────────────────────────────────────────────────────────┐ ║
  ║  │ Validation Layer                                        │ ║
  ║  │ Gauntlets: 4/5 ✓ │ FP Trap: FAILING (2 FPs) │ ⚠        │ ║
  ║  └────────────────────────────────────────────────────────┘ ║
  ║                                                              ║
  ║  ┌────────────────────────────────────────────────────────┐ ║
  ║  │ Benchmark Layer                                         │ ║
  ║  │ Precision: 73.2% │ Recall: 66.1% │ vs Slither: +15%    │ ║
  ║  └────────────────────────────────────────────────────────┘ ║
  ║                                                              ║
  ║  Current Investigation:                                      ║
  ║  └─ FP Trap gauntlet failing on contracts 3, 7             ║
  ║     Root cause: Guard detection missing inherited guards    ║
  ║     Proposed fix: Update graph builder to traverse parents  ║
  ║                                                              ║
  ╚══════════════════════════════════════════════════════════════╝
```

### Idea 4: The Learning Memory System

The operator remembers past failures and learns from them:

```yaml
learning_memory:
  storage: .vrs/testing/memory/

  failure_patterns:
    - pattern: "Guard detection fails on inherited guards"
      first_seen: "2026-01-15"
      occurrences: 5
      fixed: true
      fix_applied: "Graph builder now traverses inheritance tree"
      verification: "S03, S06, S30 now pass"

    - pattern: "Cross-function reentrancy missed"
      first_seen: "2026-01-20"
      occurrences: 3
      fixed: false
      investigation_notes: |
        - Pattern only checks single-function CEI
        - Need to add cross-function call graph tracking
        - Agent investigation also doesn't cross function boundaries
      priority: HIGH

  success_patterns:
    - pattern: "Classic reentrancy detection reliable"
      success_rate: 100%
      scenarios: [S01, S06, S07]
      confidence: HIGH

  operator_heuristics:
    - "When FP on guarded contract → check inheritance tree first"
    - "When miss on cross-contract → check call graph completeness"
    - "When oracle detection fails → check label overlay presence"
    - "When agent timeout → check graph size, may need pagination"
```

### Idea 5: The Adversarial Self-Play

Two Claude Code instances: Attacker tries to make tests fail, Defender tries to make them pass:

```yaml
adversarial_self_play:
  attacker_role: |
    Your job is to find inputs that will make AlphaSwarm:
    - Produce false positives (flag safe code)
    - Miss vulnerabilities (false negatives)
    - Crash or hang
    - Produce incorrect evidence chains

    Design contracts that exploit weaknesses in:
    - Pattern matching
    - Graph construction
    - Agent reasoning
    - Debate protocol

  defender_role: |
    Your job is to:
    - Run the attacker's adversarial inputs
    - Identify failures
    - Propose fixes
    - Verify fixes work
    - Prevent the same failure pattern

  game_loop:
    round_1:
      attacker: Creates 10 adversarial contracts
      defender: Runs them, 3 fail
      defender: Investigates, fixes 2, documents 1 as known limitation

    round_2:
      attacker: Creates 10 more, targeting the known limitation
      defender: Runs them, 5 fail on same issue
      defender: Escalates for product fix, not test fix

    round_3:
      product_team: Fixes the limitation
      defender: Re-runs all 20 adversarial contracts
      result: 19/20 pass, 1 is intentionally out of scope

  benefits:
    - Discovers edge cases humans wouldn't think of
    - Forces continuous improvement
    - Creates robust adversarial test corpus
    - Documents known limitations honestly
```

### Idea 6: The Staged Reality Check

Progressive validation from easy to hard:

```yaml
staged_reality_check:
  stage_1_smoke:
    duration: "< 5 minutes"
    tests:
      - alphaswarm --version works
      - Build graph on single contract
      - Query graph works
    pass_requirement: 100%
    failure_action: "Stop immediately, fix fundamentals"

  stage_2_basic:
    duration: "< 30 minutes"
    tests:
      - 5 simple vulnerability detections
      - 5 safe contract non-detections
      - Basic agent spawning
    pass_requirement: 80%
    failure_action: "Investigate, fix, re-run"

  stage_3_comprehensive:
    duration: "1-2 hours"
    tests:
      - Full 70-scenario matrix
      - All gauntlet challenges
      - Evidence validation
    pass_requirement: 70%
    failure_action: "Document gaps, prioritize fixes"

  stage_4_benchmark:
    duration: "2-4 hours"
    tests:
      - Slither comparison
      - CVE reproduction
      - DVD benchmark
    pass_requirement: "Meet targets"
    failure_action: "Honest assessment, improvement plan"

  stage_5_endurance:
    duration: "24 hours"
    tests:
      - Run 100+ audits continuously
      - Monitor for memory leaks
      - Check for degradation
    pass_requirement: "Stable performance"
    failure_action: "Performance optimization"
```

---

## Implementation Roadmap

### Phase Integration Order

```
Week 1: Unify 7.3.1.5 + 7.3.2
├── Execute scenarios via claude-code-agent-teams (7.3.1.5)
├── Collect evidence proofs (7.3.2)
└── Validate proof chain

Week 2: Add 7.3.3 Gauntlet
├── Create gauntlet contracts
├── Run via unified engine
└── Implement failure investigation

Week 3: Add 7.3.4 User Journey
├── Fresh user simulation
├── Error recovery testing
└── Cross-platform validation

Week 4: Add 7.3.5 Benchmarking
├── Tool comparison runs
├── CVE reproduction
└── Honest metrics report

Week 5: Add 7.3.6 Continuous
├── Git hooks
├── Nightly pipeline
└── Dashboard deployment

Week 6+: Self-Improvement Loop
├── Learning memory system
├── Adversarial self-play
└── Continuous refinement
```

---

## Success Criteria for Unified Engine

The Agentic Testing Engine is READY when:

1. ✓ `/vrs-full-testing` runs complete pipeline
2. ✓ Claude Code acts as operator via claude-code-agent-teams
3. ✓ All 70+ scenarios execute with evidence
4. ✓ All 5 gauntlets pass
5. ✓ Fresh user succeeds on first try
6. ✓ External benchmarks meet targets
7. ✓ Continuous pipeline operational
8. ✓ Self-improvement loop demonstrably working
9. ✓ Honest metrics report produced
10. ✓ At least 3 bugs fixed via adversarial discovery

---

## The Ultimate Test

**Can we trust the Agentic Testing Engine to tell us when AlphaSwarm is NOT ready to ship?**

If YES → We have a real QA operator
If NO → We're still fooling ourselves

The engine must be willing to:
- Fail the build when metrics drop
- Block releases when gauntlets fail
- Admit gaps in coverage
- Report false positives honestly
- Say "not ready" when appropriate

**An honest test engine is more valuable than a passing test suite.**

## Engine + Suites + Ops Map

**Engine (HOW):** 7.3.1.5 + 7.3.2
- claude-code-agent-teams-driven orchestration
- evidence pack schema + proof tokens
- gate enforcement

**Suites (WHAT):** 7.3.3–7.3.5
- adversarial gauntlets
- user journeys
- comparative benchmarks

**Ops (WHEN):** 7.3.6
- continuous validation pipeline
- regression tracking

Each suite must use the same evidence contract and output layout.
