# Trajectory Replay & Counterfactual Analysis in Multi-Agent LLM Evaluation

**Research Date:** 2026-02-12
**Context:** Building evaluation framework for AlphaSwarm.sol multi-agent security analysis
**Goal:** Determine feasibility of replay-based debugging and controlled variable testing for multi-agent workflows

---

## Executive Summary

**Feasibility: HIGH** — Trajectory replay is actively used in production LLM systems and has mature tooling.

**Key Finding:** The field has converged on a pattern:
1. **Record** complete execution state (not just outputs)
2. **Checkpoint** at decision boundaries
3. **Replay with interventions** to test hypotheses
4. **Measure intermediate progress** (not just final outcomes)

**Critical Insight:** Attribution in multi-agent systems is often **ill-posed** — multiple distinct interventions can independently fix failures. Therefore, evaluation should focus on **causally validated improvements** rather than "which component failed."

**Recommended Approach:** Intervention-driven evaluation with milestone-based scoring (see DoVer framework).

---

## 1. Trajectory Replay in LLM Systems

### What's Feasible

**Full State Replay:**
- ✅ Complete conversation history
- ✅ Tool call sequences + responses
- ✅ Environment variables + session state
- ✅ Intermediate reasoning traces
- ✅ Agent internal state (memory, context)
- ✅ Checkpoint-based "time travel"

**Replay with Modifications:**
- ✅ Edit messages at specific steps
- ✅ Replace agent decisions
- ✅ Inject alternative tool responses
- ✅ Branch from checkpoints
- ✅ Skip previously completed steps
- ⚠️ Non-deterministic LLM calls (requires seeding or caching)

### What to Save in Trajectory

Based on production systems (LangSmith, Maxim AI, DoVer, AgentGit):

```json
{
  "trajectory_id": "uuid",
  "task_spec": {...},
  "checkpoints": [
    {
      "checkpoint_id": "cp-001",
      "step_number": 5,
      "agent": "attacker",
      "state": {
        "conversation_history": [...],
        "tool_invocations": [...],
        "environment_vars": {...},
        "memory": {...},
        "reasoning_trace": "..."
      },
      "decision": {
        "thought": "...",
        "action": "query_graph",
        "action_input": {...}
      },
      "observation": {...},
      "metadata": {
        "timestamp": "...",
        "model": "claude-opus-4",
        "temperature": 0.7,
        "tokens_used": 1234
      }
    }
  ],
  "graph_state": {
    "contract_hash": "...",
    "graph_version": "1.2.3",
    "node_count": 450
  },
  "final_outcome": {
    "success": false,
    "error_type": "no_vulnerability_found"
  }
}
```

**Critical Components:**

1. **Pre-Condition State** (input that led to decision)
2. **Decision + Rationale** (what the agent chose and why)
3. **Post-Condition State** (result of that decision)
4. **External Dependencies** (tool responses, graph state, model config)

### Production Frameworks

| Framework | Capabilities | Maturity |
|-----------|-------------|----------|
| **LangSmith** | Distributed tracing, visual replay, debugging UI | Production (LangChain) |
| **Maxim AI** | Agent simulation, replay debugging, failure injection | Production |
| **LangGraph** | Checkpoints, interrupts, time-travel branching | Production |
| **DoVer** | Intervention-driven debugging, milestone scoring | Research (ICLR 2026) |
| **AgentGit** | Git-like rollback/branching for MAS | Research |
| **AgentRR** | Record-and-replay for experience reuse | Research (2025) |
| **ALAS** | Transactional planning with versioned logs | Research |

**Takeaway:** Replay is not experimental — it's how teams debug production agents.

---

## 2. Counterfactual Evaluation in Multi-Agent Systems

### Core Challenge: Ill-Posed Attribution

**Key Research Finding (DoVer, AgenTracer):**

> Single-step or single-agent attribution is often **ill-posed**, as multiple distinct interventions can independently repair the failed task.

**Implication:** Don't ask "which component failed?" Ask "which intervention creates measurable progress?"

### Counterfactual Reasoning Framework

From "Abstract Counterfactuals for Language Model Agents" (NeurIPS 2025):

**Three Steps:**
1. **Abduction:** Infer latent variables from observations (what led to this state?)
2. **Intervention:** Construct alternative situation (what if X were different?)
3. **Prediction:** Predict outcome of alternative (would it have succeeded?)

**Application to AlphaSwarm:**

| Counterfactual | Question | Method |
|----------------|----------|--------|
| **Prompt change** | "Would better instructions fix this?" | Replay with modified agent prompt |
| **Graph quality** | "Did poor graph coverage cause failure?" | Replay with enhanced graph |
| **Agent composition** | "Would different debate order help?" | Replay with reordered agents |
| **Contract difficulty** | "Is this contract too hard?" | Replay same agent on easier contract |

### Validation Strategy: Intervention + Replay

**DoVer Framework (Intervention-Driven Debugging):**

```
1. Hypothesis Generation
   - "Attacker agent failed to query graph effectively"

2. Intervention Design
   - Replace attacker's graph query at step 12
   - Alternative: Edit prompt to emphasize graph-first reasoning

3. Replay from Checkpoint
   - Restore state at step 11
   - Apply intervention
   - Re-execute steps 12-N

4. Milestone Scoring
   - Did agent make progress toward vulnerability discovery?
   - Metrics: queries run, nodes examined, evidence collected

5. Causality Claim
   - If milestone score improves significantly → intervention was causal
   - If no change → hypothesis refuted
```

**Critical:** Measure **intermediate progress**, not just final success/failure.

### Multi-Level Counterfactual Analysis

From "Understanding Individual Agent Importance in Multi-Agent Systems" (2024):

**Shapley Value-Based Attribution:**
- Compute marginal contribution of each agent to team performance
- Test all possible agent subsets (exponential, requires approximation)
- Identifies which agents are truly critical vs. redundant

**Practical for AlphaSwarm:**
- Baseline: Single attacker agent
- +Defender: Does adding defender improve outcomes?
- +Verifier: Does verifier reduce false positives?
- Full team: Is the composition optimal?

---

## 3. Ablation Studies in Multi-Agent Systems

### Component Isolation Methodology

**Standard Ablation Approach:**

1. **Full System Baseline** (attacker + defender + verifier)
2. **Remove One Component** at a time:
   - Attacker only
   - Defender only
   - Verifier only
   - Attacker + Defender (no verifier)
3. **Measure Impact** on key metrics
4. **Control Variables:**
   - Same contracts
   - Same graph
   - Same evaluation criteria

**Confounding Factors to Control:**

| Variable | Why It Matters | Control Method |
|----------|----------------|----------------|
| **Contract difficulty** | Hard contracts hide component benefits | Stratify by difficulty tiers |
| **Graph quality** | Poor graph makes all agents fail | Test on validated graphs |
| **Model variability** | Different runs produce different results | Multiple runs per condition (n≥30) |
| **Prompt wording** | Subtle changes affect behavior | Version control prompts |
| **Evaluation criteria** | Subjective scoring varies | Use objective + LLM-as-judge |

### Credit Assignment Problem

**Research Finding (from Multi-Agent RL):**

> The credit assignment problem scales poorly with team size. MAPPO struggles to determine which agent's actions caused success/failure in teams of 5+.

**Solution: Partial Reward Decoupling**
- Decompose team reward into per-agent contributions
- Use counterfactual baselines: "What would team score be without agent A?"

**AlphaSwarm Application:**
- Track which agent provided the **evidence** that led to verdict
- Measure **evidence quality** per agent (precision, recall, graph coverage)
- Score **reasoning chain** separately from final output

---

## 4. Causal Inference in LLM Evaluation

### Beyond Correlation

**The Problem:**
- Observation: "Score went down after prompt change"
- Correlation: Prompt change associated with lower score
- Causation: Prompt change **caused** score drop (or did it?)

**Confounders:**
- Model version changed
- Test set changed
- Graph changed
- Evaluation criteria changed

### Causal Validation Methods

**1. Controlled Experiments (A/B Testing)**

Requirements:
- **Randomization:** Randomly assign contracts to prompt A vs. B
- **Sufficient sample size:** n ≥ 30 per group (more for small effects)
- **Hold constants:** Same model, graph, evaluator, criteria
- **Statistical significance:** p < 0.05 (with multiple testing correction)

**2. Counterfactual Replay**

From DoVer:
- Intervene at suspected cause
- Re-run **same trajectory** from checkpoint
- If outcome changes → evidence of causality
- If no change → refute hypothesis

**3. Directed Acyclic Graphs (DAGs)**

Model causal relationships:
```
Graph Quality → Query Success → Evidence Quality → Verdict Accuracy
                      ↑
Prompt Quality ──────┘
```

**Causal Claims:**
- "Prompt affects verdict via query success" (mediation)
- "Graph quality is a confounder" (must control)

### Statistical Methods for LLM Evaluation

From "ReliableEval: A Recipe for Stochastic LLM Evaluation via Method of Moments":

**Challenge:** LLMs are stochastic — same input produces different outputs.

**Solution: Method of Moments**
- Run each test case **multiple times** (5-10 runs)
- Compute distribution of outcomes
- Compare distributions (not single values)
- Use Kolmogorov-Smirnov test or Welch's t-test

**Practical for AlphaSwarm:**
- Run each agent configuration 5x on same contract
- Measure mean + variance of scores
- Determine if difference is statistically significant
- Report confidence intervals

---

## 5. Controlled Variable Testing in Multi-Agent Security

### Test Matrix Design

**Factorial Experimental Design:**

| Factor | Levels | Purpose |
|--------|--------|---------|
| **Prompt** | Current, Improved | Isolate prompt effect |
| **Contract** | Easy, Medium, Hard | Measure generalization |
| **Agent Team** | A-only, A+D, A+D+V | Test composition |
| **Graph** | Full, Degraded (80%), Degraded (60%) | Test graph dependency |

**Total Conditions:** 2 × 3 × 3 × 3 = 54 combinations

**Per Condition:** 5 replications (270 total runs)

**Analysis:** 3-way ANOVA with interaction terms

### Isolating Component Effects

**Scenario 1: Prompt Quality**
- **Control:** Same contract, same graph, same agent team
- **Vary:** Prompt version A vs. B
- **Measure:** Reasoning chain quality, evidence discovery rate
- **Conclusion:** Pure prompt effect

**Scenario 2: Generalization**
- **Control:** Same prompt, same graph, same team
- **Vary:** Contract difficulty
- **Measure:** Success rate vs. difficulty
- **Conclusion:** Does agent overfit to easy contracts?

**Scenario 3: Composition Sensitivity**
- **Control:** Same prompt, same contract, same graph
- **Vary:** Agent team composition
- **Measure:** Verdict quality, false positive rate
- **Conclusion:** Is verifier adding value or just overhead?

**Scenario 4: Graph Dependency**
- **Control:** Same prompt, same contract, same team
- **Vary:** Graph completeness (100%, 80%, 60%)
- **Measure:** Query success rate, evidence quality
- **Conclusion:** Graceful degradation or cliff?

### Confound Mitigation Strategies

**Problem: Model Version Drift**
- OpenAI/Anthropic update models silently
- Same API call produces different behavior

**Solution:**
- Log model version + date for every run
- Re-run baseline periodically
- Use deterministic models when possible (temperature=0, seed)

**Problem: Order Effects**
- In multi-agent debates, order matters (attacker first vs. defender first)

**Solution:**
- Randomize order across trials
- Test order explicitly as a factor

**Problem: Learning Effects**
- Agent might "remember" if run multiple times (if using persistent memory)

**Solution:**
- Fresh session for each run
- Clear context between runs

---

## 6. Replay-Based Debugging Tools

### LangSmith (Production-Ready)

**Features:**
- Automatic distributed tracing
- Visual trace explorer
- Playground for editing + re-running
- Dataset curation from production
- LLM-as-judge evaluations

**Integration:**
```python
# One env var enables tracing
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = "..."

# Automatic capture of:
# - LLM calls
# - Tool invocations
# - Agent reasoning
# - State transitions
```

**Replay:**
- Save production trace as dataset
- Edit any step in playground
- Re-run from that point
- Compare before/after

**Limitations:**
- Tied to LangChain ecosystem
- No built-in A/B testing framework
- Manual replay (not automated)

### Maxim AI (Production-Ready)

**Features:**
- Agent simulation (100s of scenarios)
- Failure injection
- Circuit breakers
- Regression testing
- Automated evaluations

**Testing Workflow:**
1. Capture production failure
2. Reproduce in simulation
3. Apply fix
4. Re-run simulation to verify
5. Deploy with confidence

**Strengths:**
- Purpose-built for agents
- Handles non-determinism
- Scalable to large test suites

**Limitations:**
- Commercial platform
- Requires integration effort

### DoVer (Research Framework)

**Key Innovation: Intervention-Driven Debugging**

**Workflow:**
1. **Trial Segmentation:** Break trajectory into trials (based on replanning)
2. **Failure Attribution:** Generate hypothesis about cause
3. **Intervention Generation:** Design minimal edit to test hypothesis
4. **Intervention Execution:** Replay from checkpoint with edit
5. **Milestone Scoring:** Measure intermediate progress

**Results (on GAIA, AssistantBench):**
- Flipped 18-28% of failures into successes
- Validated/refuted 30-60% of hypotheses
- Up to 16% milestone progress on hard cases

**Strengths:**
- Validates fixes (not just diagnoses)
- Measures intermediate progress
- Handles multiple valid fixes

**Limitations:**
- Research code (not production-hardened)
- Requires milestone definitions
- Computationally expensive (many replays)

### AgentGit (Research Framework)

**Key Innovation: Git-Like Version Control for Agents**

**Features:**
- Commit after each step
- Rollback to any checkpoint
- Branch to explore alternatives
- Merge successful branches

**Use Cases:**
- A/B testing: Branch at checkpoint, test prompt A vs. B
- Error recovery: Rollback on failure, retry with different strategy
- Parallel exploration: Multiple branches with different agent configs

**Results:**
- 1.82× faster than full re-execution
- Enables localized repair
- Supports deterministic replay

**Limitations:**
- Built on LangGraph (ecosystem lock-in)
- Persistent storage overhead
- Complex state serialization

---

## 7. What to Save for Effective Replay

### Minimal Viable Trajectory (MVT)

**Core Data:**
```json
{
  "trajectory_id": "uuid",
  "task": {...},
  "steps": [
    {
      "step_id": 1,
      "agent": "attacker",
      "input_state": {...},
      "decision": {...},
      "output_state": {...},
      "external_calls": [...]
    }
  ],
  "final_result": {...}
}
```

**Not Enough for Replay** — Missing:
- How to restore `input_state`?
- What if `external_calls` are non-deterministic?
- What if agent uses model that changes?

### Full Replayable Trajectory

**Essential Components:**

1. **Deterministic Context**
   - Model version + parameters (temperature, seed)
   - Prompt version (hash or reference)
   - Tool versions
   - Graph version + hash

2. **State Snapshots**
   - Full conversation history
   - Memory/context store
   - Environment variables
   - Session metadata

3. **External Interaction Logs**
   - Tool call inputs + outputs (for mocking)
   - Graph query results (for caching)
   - Model responses (for deterministic replay)

4. **Branching Points**
   - Checkpoint IDs
   - Parent checkpoint (for DAG navigation)
   - Branch metadata (which intervention applied)

**Storage Strategy:**

| Component | Storage | Why |
|-----------|---------|-----|
| Trajectory metadata | Database (Postgres) | Fast querying |
| State snapshots | Object store (S3) | Large binary data |
| Model responses | Cache (Redis) | Fast lookup for replay |
| Tool outputs | Object store | Deterministic tool replay |

### Replay Modes

**1. Deterministic Replay**
- Use cached model responses
- Mock tool calls with recorded outputs
- Exact reproduction of original trajectory
- **Use case:** Debugging, forensics

**2. Counterfactual Replay**
- Branch from checkpoint
- Apply intervention (new prompt, different agent)
- Re-run with actual model calls
- **Use case:** A/B testing, optimization

**3. Partial Replay**
- Skip unchanged prefix
- Replay only affected suffix
- **Use case:** Efficient fix validation

---

## 8. Recommended Approach for AlphaSwarm.sol

### Architecture: Evaluation Pipeline with Replay

```
┌─────────────────────────────────────────────────────────────────┐
│                     EVALUATION FRAMEWORK                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. EXECUTION + CAPTURE                                          │
│     - Run agent workflow on test contract                       │
│     - Capture full trajectory (hooks into Claude Code)          │
│     - Save checkpoints at decision boundaries                   │
│                                                                  │
│  2. SCORING                                                      │
│     - Multi-tier evaluation (capability + reasoning + debrief)  │
│     - Generate scores + evidence quality metrics                │
│     - Store results with trajectory_id                          │
│                                                                  │
│  3. COUNTERFACTUAL ANALYSIS (on failures)                       │
│     - Generate intervention hypotheses                          │
│     - Replay from checkpoint with interventions                 │
│     - Measure milestone progress                                │
│     - Validate causality                                        │
│                                                                  │
│  4. CONTROLLED EXPERIMENTS                                       │
│     - A/B test prompt changes                                   │
│     - Ablate agent components                                   │
│     - Vary graph quality                                        │
│     - Statistical significance testing                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Implementation: Trajectory Storage

**File Structure:**
```
/tests/trajectories/
  {trajectory_id}/
    metadata.json          # Task, agents, config
    checkpoints/
      cp-001.json          # State snapshot at step 1
      cp-005.json
      ...
    interactions/
      step-001.json        # Input, decision, output
      step-002.json
      ...
    external/
      graph_queries.json   # Graph query results
      tool_calls.json      # Tool invocation logs
    evaluation/
      scores.json          # Multi-tier scores
      evidence.json        # Evidence quality metrics
```

**Key Classes:**

```python
# src/alphaswarm_sol/testing/trajectory/

class TrajectoryRecorder:
    """Capture agent execution as replayable trajectory."""

    def checkpoint(self, step_id: str, state: AgentState) -> CheckpointID:
        """Save full state snapshot."""

    def record_decision(self, agent: str, decision: Decision,
                       observation: Observation):
        """Log agent decision + result."""

    def save(self) -> TrajectoryID:
        """Persist trajectory to disk."""

class TrajectoryReplayer:
    """Replay trajectories with interventions."""

    def load(self, trajectory_id: str) -> Trajectory:
        """Load trajectory from disk."""

    def replay_deterministic(self, traj: Trajectory) -> Outcome:
        """Exact replay with cached responses."""

    def replay_counterfactual(self, traj: Trajectory,
                              checkpoint: CheckpointID,
                              intervention: Intervention) -> Outcome:
        """Branch from checkpoint with intervention."""

    def compare(self, original: Outcome,
                counterfactual: Outcome) -> Comparison:
        """Statistical comparison of outcomes."""

class InterventionGenerator:
    """Generate testable hypotheses about failures."""

    def analyze_failure(self, traj: Trajectory) -> List[Hypothesis]:
        """Identify potential causes."""

    def design_intervention(self, hyp: Hypothesis) -> Intervention:
        """Create minimal edit to test hypothesis."""
```

### Controlled Experiment Design

**Test Suite Structure:**

```yaml
# tests/workflow_harness/experiments/prompt_ablation.yaml

experiment:
  name: "Attacker Prompt Optimization"
  type: "A/B"

  factors:
    - name: "prompt_version"
      levels: ["baseline", "graph_first", "pattern_aware"]
    - name: "contract_difficulty"
      levels: ["easy", "medium", "hard"]

  constants:
    agent_team: ["attacker", "defender", "verifier"]
    graph_version: "1.2.3"
    model: "claude-opus-4"

  test_cases:
    - contract: "tests/contracts/reentrancy_simple.sol"
      difficulty: "easy"
    - contract: "tests/contracts/reentrancy_complex.sol"
      difficulty: "hard"

  replications: 5

  metrics:
    - name: "evidence_discovery_rate"
      type: "objective"
    - name: "reasoning_quality"
      type: "llm_judge"
    - name: "verdict_accuracy"
      type: "ground_truth"

  analysis:
    method: "ANOVA"
    alpha: 0.05
    correction: "bonferroni"
```

**Execution:**

```bash
# Run experiment
uv run alphaswarm experiment run prompt_ablation.yaml

# Produces:
# - Trajectories for all conditions
# - Statistical analysis report
# - Visualizations (box plots, interaction plots)
# - Causal claims with confidence intervals
```

### Counterfactual Analysis Workflow

**Scenario: Attacker Failed to Find Vulnerability**

```python
# 1. Load failed trajectory
traj = replayer.load("traj-failed-001")

# 2. Generate hypotheses
hypotheses = intervention_gen.analyze_failure(traj)
# [
#   "Attacker did not query graph for access control patterns",
#   "Attacker queried graph but misinterpreted results",
#   "Graph lacked coverage of vulnerable function"
# ]

# 3. Test each hypothesis
for hyp in hypotheses:
    intervention = intervention_gen.design_intervention(hyp)
    # Example: Insert graph query at step 5

    # Replay from checkpoint before suspected failure
    checkpoint = traj.get_checkpoint_before(intervention.step)
    result = replayer.replay_counterfactual(traj, checkpoint, intervention)

    # Measure progress
    progress = milestone_scorer.score(result)

    if progress > baseline:
        print(f"✓ Hypothesis validated: {hyp.description}")
        print(f"  Progress: {progress.improvement}%")
    else:
        print(f"✗ Hypothesis refuted: {hyp.description}")
```

**Output:**

```
Counterfactual Analysis: traj-failed-001
=========================================

Baseline:
  - Evidence nodes discovered: 0
  - Graph queries executed: 1 (generic)
  - Verdict: No vulnerability found

Hypothesis 1: "Attacker did not query graph for access control patterns"
  Intervention: Insert access control pattern query at step 5
  Result:
    - Evidence nodes discovered: 3
    - Graph queries executed: 4 (2 pattern-specific)
    - Verdict: Weak access control identified (Medium severity)
  ✓ VALIDATED: +300% evidence discovery, +3 graph queries

Hypothesis 2: "Attacker queried graph but misinterpreted results"
  Intervention: Replace reasoning prompt with interpretation guidance
  Result:
    - Evidence nodes discovered: 0
    - Graph queries executed: 1 (same as baseline)
    - Verdict: No vulnerability found
  ✗ REFUTED: No improvement

Hypothesis 3: "Graph lacked coverage of vulnerable function"
  Intervention: Enhance graph with function relationship edges
  Result:
    - Evidence nodes discovered: 2
    - Graph queries executed: 3
    - Verdict: Potential vulnerability (requires verification)
  ✓ VALIDATED: +200% evidence discovery, +2 graph queries

Causal Conclusion:
  Primary cause: Lack of pattern-specific graph queries (Hypothesis 1)
  Contributing cause: Insufficient graph coverage (Hypothesis 3)
  Non-cause: Prompt interpretation (Hypothesis 2)

Recommendation:
  - Update attacker prompt to emphasize pattern-based graph exploration
  - Enhance graph builder with richer function relationship edges
  - Expected improvement: +250% evidence discovery rate
```

---

## 9. What's NOT Feasible (Limitations)

### 1. Perfect Determinism

**Challenge:** LLMs are inherently stochastic.

**Limitations:**
- Temperature > 0 → different outputs each run
- Even temperature = 0 is not truly deterministic (model internals change)
- External APIs (OpenAI, Anthropic) don't guarantee reproducibility

**Mitigation:**
- Cache model responses for deterministic replay
- Use seeds when available
- Accept variance, test distributions (not single values)

### 2. Causal Isolation in Complex Systems

**Challenge:** Multi-agent systems have many interacting components.

**Limitations:**
- Changing one component affects others (cascading effects)
- Interaction effects are hard to disentangle
- Full factorial experiments explode combinatorially

**Mitigation:**
- Prioritize main effects over interactions
- Use partial factorial designs (trade coverage for feasibility)
- Accept that some effects will be confounded

### 3. Generalization from Controlled Tests

**Challenge:** Test set performance ≠ real-world performance.

**Limitations:**
- Test contracts are curated → may not represent real diversity
- Agents overfit to test patterns
- New vulnerability types emerge → agents fail

**Mitigation:**
- Holdout sets (never used for development)
- Continuous evaluation on new contracts
- User feedback loop

### 4. Scalability of Replay

**Challenge:** Replaying trajectories is computationally expensive.

**Limitations:**
- Each counterfactual replay costs $ (LLM calls)
- Full factorial experiments require hundreds of runs
- Storage grows linearly with trajectory length

**Mitigation:**
- Prioritize high-value replays (focus on failures)
- Use partial replay (skip unchanged prefix)
- Cache aggressively

### 5. Human-in-the-Loop Bottlenecks

**Challenge:** Some evaluations require human judgment.

**Limitations:**
- LLM-as-judge has biases and blind spots
- Ground truth labels are expensive to obtain
- Subjective metrics (reasoning quality) vary by rater

**Mitigation:**
- Combine automated + human evaluation
- Use multi-rater agreement (Krippendorff's alpha)
- Invest in high-quality ground truth datasets

---

## 10. Practical Recommendations for AlphaSwarm.sol

### Phase 1: Instrumentation (Immediate)

**Goal:** Capture trajectories from existing tests.

**Actions:**
1. Add `TrajectoryRecorder` to workflow harness
2. Hook into agent execution to capture:
   - Decisions + rationale
   - Graph queries + results
   - Tool calls + responses
3. Save trajectories to `tests/trajectories/`
4. Build basic viewer (JSON → readable format)

**Deliverable:** Can replay any test execution deterministically.

### Phase 2: Counterfactual Analysis (Short-Term)

**Goal:** Debug failures systematically.

**Actions:**
1. Implement `TrajectoryReplayer` with checkpoint support
2. Build `InterventionGenerator` for common hypotheses:
   - "Graph query missing"
   - "Prompt unclear"
   - "Agent order suboptimal"
3. Add `MilestoneScorer` to measure intermediate progress
4. Automate counterfactual replay on failed tests

**Deliverable:** When test fails, automatically generate + test fix hypotheses.

### Phase 3: Controlled Experiments (Medium-Term)

**Goal:** A/B test prompts, agents, and configurations.

**Actions:**
1. Build experiment runner (YAML config → execution)
2. Implement statistical analysis (ANOVA, t-tests)
3. Add visualization (box plots, interaction plots)
4. Create standard experiment templates:
   - Prompt ablation
   - Agent composition
   - Graph dependency

**Deliverable:** Data-driven optimization of agent configurations.

### Phase 4: Continuous Evaluation (Long-Term)

**Goal:** Track agent quality over time.

**Actions:**
1. Define benchmark suite (diverse contracts, ground truth labels)
2. Run benchmark on every major change (prompt, agent, graph)
3. Monitor for regressions
4. Build dashboard (historical trends, confidence intervals)

**Deliverable:** Confidence that changes improve (not degrade) agent quality.

### Integration with Phase 3.1c (Testing Framework)

**Current Framework Capabilities:**
- Multi-tier evaluation (capability + reasoning + debrief)
- Reasoning move decomposition (7 move types)
- Graph value scoring
- Scenario synthesis
- Interactive agent debrief

**Proposed Extension:**

```python
# src/alphaswarm_sol/testing/trajectory/evaluator.py

class TrajectoryEvaluator:
    """Extends existing evaluator with replay capabilities."""

    def evaluate_with_replay(self, scenario: TestScenario) -> EvaluationResult:
        """Run scenario, capture trajectory, evaluate, analyze counterfactuals."""

        # 1. Execute + capture
        traj = self.recorder.run_and_capture(scenario)

        # 2. Existing multi-tier evaluation
        scores = self.evaluator.evaluate(traj)

        # 3. If failure, analyze counterfactuals
        if scores.capability_score < threshold:
            cf_results = self.counterfactual_analyzer.analyze(traj, scores)
            scores.add_counterfactual_analysis(cf_results)

        # 4. Store for later replay
        self.storage.save(traj, scores)

        return scores
```

**Benefit:** Evaluation now provides:
- **What happened** (existing capability + reasoning assessment)
- **Why it happened** (counterfactual analysis identifies causes)
- **How to fix it** (interventions that demonstrably improve outcomes)

---

## 11. Key Takeaways

### ✅ What Works

1. **Trajectory Replay is Production-Ready**
   - LangSmith, Maxim AI, LangGraph all support it
   - Standard pattern: checkpoints + state snapshots + replay

2. **Counterfactual Analysis is Feasible**
   - DoVer shows 18-28% failure recovery with interventions
   - Replay from checkpoint + apply edit + measure progress

3. **A/B Testing Prompts is Standard Practice**
   - Controlled experiments with statistical rigor
   - n ≥ 30 per condition, significance testing, hold constants

4. **Causal Claims Require Validation**
   - Correlation ≠ causation
   - Use interventions to test hypotheses
   - Measure intermediate progress (not just final outcomes)

### ⚠️ What's Hard

1. **Determinism is Aspirational**
   - LLMs are stochastic → embrace variance
   - Cache for replay, but test distributions in experiments

2. **Attribution is Often Ill-Posed**
   - Multiple fixes may work → don't obsess over single cause
   - Focus on validated improvements

3. **Scalability Requires Tradeoffs**
   - Full factorial experiments explode → prioritize main effects
   - Replay is expensive → cache aggressively

### 🎯 Recommended Strategy

**For AlphaSwarm.sol:**

1. **Instrument Everything**
   - Capture trajectories from all tests (baseline data)

2. **Replay-Based Debugging**
   - When failure occurs, generate intervention hypotheses
   - Replay with edits, measure progress
   - Validate fixes before deploying

3. **Controlled Experiments**
   - A/B test prompt changes (prompt_old vs. prompt_new)
   - Ablate components (full team vs. subsets)
   - Vary graph quality (100% vs. degraded)

4. **Statistical Rigor**
   - Multiple runs per condition (n ≥ 5)
   - Significance testing (ANOVA, t-tests)
   - Report confidence intervals

5. **Iterate Based on Data**
   - Don't guess what works
   - Let counterfactual analysis guide optimization
   - Build feedback loop: test → analyze → improve → test

---

## 12. References

### Key Papers

1. **DoVer: Intervention-Driven Auto Debugging for LLM Multi-Agent Systems**
   Ma et al., ICLR 2026 (under review)
   https://arxiv.org/html/2512.06749v3

2. **AgenTracer: Who Is Inducing Failure in the LLM Agentic Systems?**
   Zhang et al., 2025
   https://arxiv.org/abs/2509.03312

3. **Abstract Counterfactuals for Language Model Agents**
   Pona et al., NeurIPS 2025
   https://arxiv.org/abs/2506.02946

4. **Interactive Debugging and Steering of Multi-Agent AI Systems**
   Epperson et al., CHI 2025
   https://dl.acm.org/doi/full/10.1145/3706598.3713581

5. **AgentGit: A Framework for Reliable and Scalable LLM-Powered Multi-Agent Systems**
   2025
   https://arxiv.org/html/2511.00628v1

6. **Get Experience from Practice: LLM Agents with Record & Replay**
   Feng et al., 2025
   https://arxiv.org/html/2505.17716v1

7. **Understanding Individual Agent Importance in Multi-Agent Systems via Counterfactual Reasoning**
   Chen et al., 2024
   https://arxiv.org/abs/2412.15619

### Production Tools

- **LangSmith:** https://www.langchain.com/langsmith
- **Maxim AI:** https://www.getmaxim.ai/
- **LangGraph:** https://github.com/langchain-ai/langgraph
- **Braintrust:** https://www.braintrust.dev/

### Testing Frameworks

- **Statsig (A/B testing):** https://www.statsig.com/
- **Langfuse (Prompt A/B testing):** https://langfuse.com/
- **SWE-agent (Trajectory logging):** https://github.com/SWE-agent/SWE-agent

---

## Appendix: Glossary

**Trajectory:** Sequence of (state, action, observation) tuples representing agent execution.

**Checkpoint:** Snapshot of full agent state at a point in time, enabling replay from that point.

**Counterfactual:** Alternative scenario where one variable is changed ("what if X were different?").

**Intervention:** Targeted edit to a trajectory (change prompt, replace decision, inject data).

**Replay:** Re-executing a trajectory, either deterministically (cached) or with interventions.

**Milestone:** Intermediate progress metric (e.g., evidence discovered, queries run), distinct from final success/failure.

**Attribution:** Identifying which component (agent, prompt, tool) caused a failure.

**Ill-Posed Attribution:** When multiple distinct interventions can independently fix a failure, making single-cause attribution ambiguous.

**Ablation:** Removing a component to measure its contribution to overall performance.

**A/B Testing:** Controlled experiment comparing two variants (A vs. B) with statistical significance testing.

**Confound:** Variable that affects both treatment and outcome, creating spurious correlation.

**Causal Validation:** Using interventions + replay to establish causation (not just correlation).

---

**End of Research Summary**

**Next Steps:**
1. Share with team for review
2. Design trajectory storage schema
3. Implement `TrajectoryRecorder` hook
4. Build counterfactual analyzer prototype
5. Run pilot experiment (prompt ablation on 3 contracts)
