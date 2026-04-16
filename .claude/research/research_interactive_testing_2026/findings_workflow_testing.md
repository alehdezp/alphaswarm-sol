# Workflow Testing, Transcript Analysis & Multi-Agent Coordination Testing
## Research Findings -- March 2026

**Research date**: 2026-03-01
**Scope**: Latest techniques for testing agentic AI systems, transcript analysis, behavioral fingerprinting, agent observability, and multi-agent coordination testing.
**Relevance**: Direct applicability to AlphaSwarm.sol's JSONL-hook-based observation + evaluation contract testing system.

---

## Table of Contents

1. [Structured Transcript Analysis](#1-structured-transcript-analysis)
2. [Agent Trajectory Evaluation](#2-agent-trajectory-evaluation)
3. [Workflow Replay and Differential Testing](#3-workflow-replay-and-differential-testing)
4. [Behavioral Fingerprinting and Drift Detection](#4-behavioral-fingerprinting-and-drift-detection)
5. [Multi-Agent Coordination Testing](#5-multi-agent-coordination-testing)
6. [Chaos Engineering for Agents](#6-chaos-engineering-for-agents)
7. [Observability for Agentic Systems](#7-observability-for-agentic-systems)
8. [Test Contract Patterns](#8-test-contract-patterns)
9. [Agentic Testing Frameworks](#9-agentic-testing-frameworks)
10. [Synthesis: Recommendations for AlphaSwarm.sol](#10-synthesis-recommendations-for-alphaswarmol)

---

## 1. Structured Transcript Analysis

### 1.1 UK AISI Transcript Analysis (October 2025 -- ongoing)

**Source**: UK AI Security Institute (AISI)
**URL**: https://www.aisi.gov.uk/blog/transcript-analysis-for-ai-agent-evaluations
**Status**: Active, with ongoing tool development

The UK AISI systematically analyzes thousands of agent evaluation transcripts (each equivalent to dozens of pages of text). Their approach goes beyond pass-rate metrics to identify:

**Three Major Failure Modes Identified**:
1. **Policy compliance refusals**: One agent refused tasks in 10% of attempts; another triggered provider safety violations in 30% of cases.
2. **Task resignation**: Agents varied in perseverance -- some declared tasks "unsolvable" in ~30% of communications on difficult challenges.
3. **Scaffold non-compliance**: Tool-calling compliance varied significantly -- some agents called tools in fewer than 50% of turns despite explicit instructions.

**Methodology**: Analyzed 6,390 transcripts from 9 AI models on 71 capture-the-flag cybersecurity tasks using the ReAct framework (reasoning traces + action logs interleaved).

**Key Insight for AlphaSwarm.sol**: The three failure modes map directly to evaluation concerns:
- Policy refusals = agent refusing to analyze "dangerous" vulnerability patterns
- Task resignation = agent giving up on complex cross-function analysis
- Scaffold non-compliance = agent not using BSKG CLI tools as instructed

### 1.2 NIST CAISI Transcript Analysis (February 2026)

**Source**: NIST Center for AI Standards and Innovation
**URL**: https://www.nist.gov/blogs/caisi-research-blog/analyzing-transcripts-ai-agent-evaluations
**Status**: Published February 18, 2026

NIST CAISI built transcript analysis tools specifically to detect **agent cheating on evaluations** -- a critical concern for any evaluation framework. Their collaborative work with UK AISI establishes:

**Multi-step pipeline for transcript review tools**:
1. Preparing log data from agent evaluations
2. Designing scanner rules (what to look for)
3. Validating scanners in an iterative loop
4. Scaling analysis across thousands of transcripts

**Key Tool**: **Inspect Scout** -- open-source transcript analysis framework developed by UK AISI and Meridian Labs, designed to work directly with Inspect AI evaluation logs.

**Companion Publications**:
- NIST AI 800-2: "Practices for Automated Benchmark Evaluations of Language Models" (draft, comments through March 31, 2026)
- NIST AI 800-3: "Expanding the AI Evaluation Toolbox with Statistical Models" (February 2026)
- NIST "AI Agent Standards Initiative" (launched February 17, 2026)

**Key Insight for AlphaSwarm.sol**: Our JSONL hook observations are essentially transcripts. The Inspect Scout approach of iterative scanner design maps well to building detection rules for our anti-fabrication checks (100% pass rate, identical outputs, scores at 100, duration < 5s triggers).

### 1.3 Inspect AI Framework (UK AISI)

**Source**: UK AISI
**URL**: https://inspect.aisi.org.uk/
**GitHub**: https://github.com/UKGovernmentBEIS/inspect_evals
**Status**: Active, production-grade

Open-source Python framework for building and running LLM evaluations. Key primitives: Dataset -> Task -> Solver -> Scorer.

**Relevant capabilities**:
- Multi-turn/agent workflow evaluation
- Structured log format with full transcript capture
- `@subtask` and `transcript` decorators for granular observability
- **Inspect Scout**: Dedicated transcript analysis tool for log files
- **Inspect Viz**: Data visualization framework for evaluation logs

**Key Insight for AlphaSwarm.sol**: The `@subtask` decorator pattern for recording specific events within evaluations is analogous to our JSONL hook approach, but with more structured event taxonomy.

---

## 2. Agent Trajectory Evaluation

### 2.1 DeepEval Agent Metrics Suite (February 2026)

**Source**: Confident AI / DeepEval
**URL**: https://deepeval.com/guides/guides-ai-agent-evaluation-metrics
**Status**: Production-ready, actively updated (last update Feb 23, 2026)

DeepEval provides the most comprehensive set of agentic evaluation metrics as of March 2026, organized in three layers:

**Reasoning Layer**:
- **Plan Quality Metric**: Extracts task + plan from agent traces, LLM-judge evaluates plan quality
- **Plan Adherence Metric**: Compares stated plan vs actual execution steps, detects mid-execution deviations

**Action Layer**:
- **Tool Correctness Metric**: Compares called tools vs expected tools, configurable strictness (name match, parameter validation, output verification)
- **Argument Correctness Metric**: LLM-based assessment of parameter validity from context (not predetermined values)
- **Tool Use Metric** (multi-turn): Evaluates tool selection + argument generation across conversation turns

**Execution Layer**:
- **Task Completion Metric**: Extracts objective + outcome from traces, evaluates alignment
- **Step Efficiency Metric**: Identifies redundant tool calls and circuitous reasoning
- **Goal Accuracy Metric** (multi-turn): Evaluates planning AND execution across multi-turn agent conversations

**Technical approach**: All metrics use trace-based analysis via `@observe` decorator. Traces capture the full execution tree including tool calls, LLM calls, and intermediate reasoning.

**Key Insight for AlphaSwarm.sol**: Our 7-move reasoning decomposition (HYPOTHESIS_FORMATION through SELF_CRITIQUE) maps directly to DeepEval's Plan Quality + Plan Adherence + Step Efficiency combination. We could adopt their trace-based `@observe` pattern to complement our JSONL hooks.

### 2.2 Microsoft Agent-Pex (January 2026)

**Source**: Microsoft Research
**URL**: https://www.microsoft.com/en-us/research/project/agent-pex-automated-evaluation-and-testing-of-ai-agents/
**Status**: Active research project

Agent-Pex solves three problems relevant to our evaluation framework:

1. **Specification Extraction**: Automatically analyzes agent prompts + execution traces to identify explicit and implicit behavioral rules. Example: "When the query mentions access control, the agent MUST query the BSKG for modifier patterns."

2. **Automated Evaluation**: Given a trace and extracted specification, determines rule violations with compliance scores (e.g., `output_spec_eval_score: 95.0`).

3. **Scalable Analysis**: Supports evaluation across thousands of traces using the Tau-squared benchmark (5,000+ traces across multiple domains).

**Technical Approach**: Builds on PromptPex (automatic test generation for LLM prompts), extended to agentic contexts. Uses extracted specifications to generate adversarial tests that expose weaknesses.

**Key Insight for AlphaSwarm.sol**: The specification extraction approach could automate our evaluation contract creation. Instead of manually writing expected behaviors, extract them from the skill SKILL.md files and agent prompts.

### 2.3 Agent-Testing Agent (ATA) -- Meta-Agent for Automated Testing (June 2025)

**Source**: arXiv:2508.17393 (University of Illinois / Grammarly)
**URL**: https://arxiv.org/abs/2508.17393
**Status**: Published, open-source implementation

A meta-agent that automates testing of conversational AI agents through four techniques:

1. **Static code analysis** of the target agent
2. **Designer interrogation** (gathering insights from agent creators)
3. **Literature mining** for relevant test cases
4. **Persona-driven adversarial test generation** with adaptive difficulty

**Key Result**: Completed evaluation in 20-30 minutes vs ten-annotator rounds taking days. Surfaced "more diverse and severe failures than expert annotators while matching severity."

**Key Insight for AlphaSwarm.sol**: The adaptive difficulty mechanism (judge feedback steers subsequent tests toward weakest capabilities) could improve our calibration batch approach. Instead of static test contracts, generate progressively harder challenges.

---

## 3. Workflow Replay and Differential Testing

### 3.1 agent-replay (February 2026)

**Source**: clay-good/agent-replay
**URL**: https://github.com/clay-good/agent-replay
**License**: MIT
**Status**: New (created Feb 28, 2026), early-stage

A local, SQLite-powered CLI tool for time-travel debugging AI agents. **Most directly relevant tool found.**

**Core Capabilities**:

| Feature | Description |
|---------|-------------|
| **Replay** | Step-by-step execution animation at configurable speed |
| **Diff** | Side-by-side trace comparison with AI-powered divergence analysis |
| **Fork** | Branch at any step, modify inputs, test alternatives without rerunning |
| **Eval** | Deterministic + AI-powered evaluation presets |
| **Guard** | Pattern-based safety policies (allow/deny/warn/require_review) |
| **Export** | Output traces as JSON/JSONL or golden datasets |

**Trace Schema** (8 step types):
`thought`, `tool_call`, `llm_call`, `retrieval`, `output`, `decision`, `error`, `guard_check`

**Evaluation Presets**:
- Deterministic (no cost): hallucination-check, safety-check, completeness-check
- AI-powered (~$0.01/trace): root-cause analysis, quality review, security audit, optimization
- Custom YAML rubrics with weighted criteria

**Key Insight for AlphaSwarm.sol**: The diff + fork paradigm is exactly what we need for regression testing. Record a known-good evaluation run, then diff against new runs to detect behavioral drift. The YAML rubric system could replace our evaluation contracts.

### 3.2 Replayable Agent Runs Pattern (January 2026)

**Source**: Medium / Thinking Loop
**URL**: https://medium.com/@ThinkingLoop/replayable-agent-runs-the-debugging-trick-that-ships-f5460ebf390a
**Status**: Architecture pattern (not a tool)

Key architectural principles for replayable agent debugging:

1. **Trace everything**: Every tool response, model choice, and state transition
2. **Snapshot state**: Capture full agent state at each step (not just inputs/outputs)
3. **Deterministic replay**: Pin model responses during replay for exact reproduction
4. **Step-level re-execution**: Allow re-running from any checkpoint

**Key Insight for AlphaSwarm.sol**: Our JSONL hooks already capture tool calls and outputs. Adding state snapshots (graph state, query results) would enable full replay capability.

---

## 4. Behavioral Fingerprinting and Drift Detection

### 4.1 Fingerprinting AI Coding Agents on GitHub (January 2026)

**Source**: arXiv:2601.17406 (Trent University)
**URL**: https://arxiv.org/abs/2601.17406
**Status**: Published 2026

**Most relevant behavioral fingerprinting research found.**

Analyzed 33,580 PRs from 5 major AI coding agents (OpenAI Codex, GitHub Copilot, Devin, Cursor, Claude Code) to identify behavioral signatures.

**41 features across 3 categories**:
- Commit message patterns
- PR structure characteristics
- Code-level attributes

**Results**: 97.2% F1-score in multi-class agent identification.

**Distinctive fingerprints**:
- OpenAI Codex: "unique multiline commit patterns" (67.5% feature importance)
- Claude Code: "distinctive code structure" (27.2% importance of conditional statements)

**Key Insight for AlphaSwarm.sol**: We can build behavioral fingerprints for our agent evaluations. If an agent's behavioral signature changes (different tool call patterns, different reasoning structure), that signals drift. This directly supports our regression detection system.

### 4.2 Agent Drift Framework (January 2026)

**Source**: arXiv:2601.04170 (Independent Researcher, Abhishek Rath)
**URL**: https://arxiv.org/abs/2601.04170
**Status**: Published January 7, 2026

Introduces formal framework for understanding agent drift in multi-agent LLM systems.

**Three Categories of Drift**:
1. **Semantic Drift**: Progressive deviation from original intended purpose/meaning
2. **Coordination Drift**: Breakdown in multi-agent consensus and alignment mechanisms
3. **Behavioral Drift**: Emergence of unintended strategies during operation

**Agent Stability Index (ASI)** -- composite metric across 12 dimensions:
- Response consistency patterns
- Tool usage patterns
- Reasoning pathway stability
- Inter-agent agreement rates

**Mitigation Strategies**:
1. Episodic memory consolidation
2. Drift-aware routing protocols
3. Adaptive behavioral anchoring

**Key Insight for AlphaSwarm.sol**: All three drift categories apply to our attacker/defender/verifier debate system. Coordination drift is particularly relevant -- if agents start agreeing too easily (rubber-stamping), that signals degraded verification quality. The ASI metric could be adapted as a composite score for our dual-Opus evaluator.

### 4.3 Goal Drift in Language Model Agents (October 2025)

**Source**: AAAI AIES 2025 (MATS / Apollo Research)
**URL**: https://ojs.aaai.org/index.php/AIES/article/download/36541/38679
**Status**: Published

Focuses on detecting when agents' goals gradually shift from human-assigned objectives during extended autonomous operation. Key concern: "goals can shift gradually, causing only subtle changes."

**Key Insight for AlphaSwarm.sol**: Extended evaluation sessions (our calibration batches) are vulnerable to goal drift. An agent might start by genuinely analyzing vulnerabilities but gradually shift to pattern-matching or satisficing behavior.

### 4.4 Maxim AI: Managing Agent Drift (November 2025)

**Source**: Maxim AI
**URL**: https://www.getmaxim.ai/articles/managing-ai-agent-drift-how-to-maintain-consistent-performance-over-time/
**Status**: Production framework

Practical framework with four pillars:
1. **Session-level observability** (not just request-level)
2. **Scenario-based simulation** for regression detection
3. **Unified evaluations** across development and production
4. **Controlled rollouts** with canary deployments

**Key Insight for AlphaSwarm.sol**: Session-level observability aligns with our transcript-based evaluation approach. We should track drift across evaluation sessions, not just individual runs.

---

## 5. Multi-Agent Coordination Testing

### 5.1 Agent Behavioral Contracts (ABC) Framework (February 2026)

**Source**: arXiv:2602.22302 (Accenture, patent pending)
**URL**: https://arxiv.org/abs/2602.22302
**Status**: Published February 25, 2026 -- **the most relevant paper for our evaluation contracts**

Formal framework applying Design-by-Contract principles to autonomous AI agents.

**Contract Structure**: C = (P, I, G, R)
- **P**: Preconditions (required initial states)
- **I**: Invariants (must hold throughout execution)
- **G**: Governance policies (operational rules)
- **R**: Recovery mechanisms (corrective actions on violation)

**Key Technical Contributions**:

1. **Probabilistic Compliance**: (p, delta, k)-satisfaction -- accounts for LLM unpredictability and recovery capabilities. Not binary pass/fail but probabilistic compliance measurement.

2. **Drift Bounds Theorem**: Contracts with recovery rate gamma > alpha bound behavioral drift to D* = alpha/gamma in expectation. Mathematical guarantees about behavioral consistency.

3. **Safe Composition**: Conditions enabling multi-agent chains with "probabilistic degradation bounds" for composed systems (directly applicable to attacker -> defender -> verifier chains).

**Implementation**: AgentAssert runtime enforcement library, tested on AgentContract-Bench (200 scenarios, 7 models). Contracted agents detected 5.2-6.8 soft violations per session that uncontracted baselines miss entirely. 88-100% hard constraint compliance. <10ms overhead per action.

**Key Insight for AlphaSwarm.sol**: This is the theoretical foundation our evaluation contract system needs. The probabilistic compliance notion replaces binary pass/fail with nuanced scoring. The Safe Composition theorem directly addresses our multi-agent debate chain reliability.

### 5.2 Relari Agent Contracts (Open Source)

**Source**: Relari AI
**URL**: https://github.com/relari-ai/agent-contracts
**Docs**: https://agent-contracts.relari.ai/
**Status**: Active, production-ready

Practical implementation of agent contract testing with three-layer architecture:

**Contract Structure**:
- **Preconditions**: Requirements before execution
- **Pathconditions**: Constraints on the process (not just outcome)
- **Postconditions**: Must hold after execution

**Specification Hierarchy**:
```
Specification (collection) -> Scenarios (test cases) -> Contracts (individual requirements)
```

**Two Verification Modes**:
1. **Offline Verification**: Fixed scenarios, saved as JSON/YAML, run through Docker-based verification server
2. **Runtime Certification**: Live monitoring with `certification_enabled=True`, real-time compliance certificates

**Technical Stack**:
- Instrumentation via `relari-otel` (OpenTelemetry-compatible)
- Trace collection in standard OTel format
- Verification server for offline batch analysis

**Key Insight for AlphaSwarm.sol**: The precondition -> pathcondition -> postcondition pattern maps perfectly to our two-stage testing (capability contract check FIRST, reasoning evaluation ONLY if capability passes). Preconditions = capability check. Pathconditions = reasoning quality. Postconditions = correct verdict.

### 5.3 AgentSpec: Runtime Enforcement (March 2025)

**Source**: arXiv:2503.18666
**URL**: https://arxiv.org/abs/2503.18666
**Status**: Published

Customizable runtime enforcement framework for safe and reliable LLM agents. Complements the ABC framework with practical enforcement mechanisms.

### 5.4 MAFBench: Multi-Agent Framework Benchmark (August 2025)

**Source**: CoDS-GCS/MAFBench
**URL**: https://github.com/CoDS-GCS/MAFBench
**Status**: Active (last push Feb 2026)

Unified benchmark for evaluating architectural design choices in LLM-based single-agent and multi-agent frameworks across:
- Orchestration patterns
- Memory systems
- Planning strategies
- Specialization approaches
- Coordination mechanisms

**Key Insight for AlphaSwarm.sol**: Can use MAFBench's evaluation dimensions to assess our attacker/defender/verifier coordination quality.

### 5.5 Nexus: Execution-Grounded Multi-Agent Test Oracle Synthesis (October 2025)

**Source**: arXiv:2510.26423
**URL**: https://arxiv.org/abs/2510.26423
**Status**: Under review

Framework where four specialized agents collaborate to generate test oracles through structured deliberation + execution validation.

**Two-Phase Approach**:
1. **Deliberation Phase**: 4 agents with distinct testing philosophies critique and refine test oracles
2. **Validation Phase**: Generate plausible implementation, execute oracles in sandbox, use runtime errors for iterative refinement

**Results**: Test-level oracle accuracy improved from 46.30% to 57.73%. Bug detection rates on HumanEval: 90.91% -> 95.45%.

**Key Insight for AlphaSwarm.sol**: The multi-agent deliberation for test oracle generation is analogous to our multi-agent debate for vulnerability verification. The validation-through-execution pattern (execute, check, refine) could improve our evaluation contract quality.

---

## 6. Chaos Engineering for Agents

### 6.1 Agents of Chaos (February 2026)

**Source**: arXiv:2602.20021 (Stanford/Harvard, multi-institution)
**URL**: https://arxiv.org/abs/2602.20021
**Full Report**: https://agentsofchaos.baulab.info/report.html
**Status**: Published February 23, 2026

**The most comprehensive chaos engineering study for AI agents to date.**

Live laboratory environment with persistent memory, email, Discord, file systems, and shell execution. 20 AI researchers tested agents for two weeks under benign and adversarial conditions.

**Vulnerability Categories Discovered** (11 case studies):
1. Unauthorized compliance with non-owners
2. Disclosure of sensitive information
3. Execution of destructive system-level actions
4. Denial-of-service conditions / uncontrolled resource consumption
5. Identity spoofing vulnerabilities
6. Cross-agent propagation of unsafe practices
7. Partial system takeover
8. **Agents claimed task completion while actual system state contradicted those claims** (critical for evaluation reliability)

**Key Insight for AlphaSwarm.sol**: Vulnerability #8 (false completion claims) is exactly the anti-fabrication concern in our evaluation framework. The study validates our approach of verifying agent claims against actual system state (graph queries returning real data vs fabricated results).

### 6.2 UDora: Unified Red Teaming Framework (February 2025)

**Source**: arXiv:2503.01908
**URL**: https://arxiv.org/abs/2503.01908
**Status**: Published, code available on GitHub

Red teaming framework that hijacks agent reasoning by:
1. Generating the model's reasoning trace for a task
2. Automatically identifying optimal insertion points for perturbations
3. Iteratively optimizing perturbed reasoning patterns

**Key Innovation**: Attacks the intermediate reasoning steps rather than inputs/outputs, compelling agents to execute malicious actions or invoke malicious tools.

**Key Insight for AlphaSwarm.sol**: Could be adapted as an adversarial testing tool -- inject perturbations into agent reasoning to test whether our verifier agent catches manufactured evidence or fabricated tool outputs.

### 6.3 Adversarial Robustness of LLM-Based Multi-Agent Systems (Under review, ICLR 2026)

**Source**: OpenReview (ICLR 2026 submission)
**URL**: https://openreview.net/pdf/a925b93f4a7a4621347d246dc2bfbff0956b2bc4.pdf
**Status**: Under double-blind review

First systematic study of adversarial robustness in multi-agent LLM systems for engineering problems. Highlights that "engineering workflows demand formal rigor and numerical accuracy, meaning adversarial perturbations can cause not just degraded performance but systematically incorrect or unsafe results."

**Key Insight for AlphaSwarm.sol**: Security analysis is an engineering workflow demanding formal rigor. Adversarial perturbations to our agents could produce systematically incorrect vulnerability assessments -- false positives and false negatives with high confidence.

---

## 7. Observability for Agentic Systems

### 7.1 Tool Landscape (February 2026)

Based on multiple comparative reviews published in January-February 2026:

| Tool | Key Strength | Agent-Specific Features | Status |
|------|-------------|------------------------|--------|
| **Arize Phoenix** | Open-source, OTel-native | Embedding clustering, decision graphs, MCP tracing | Active, self-hosted |
| **Braintrust** | Evaluation-first, 80x query speed | Loop AI (NL evaluator generation), composite metrics, CI/CD integration | Active, free tier (1M spans/mo) |
| **LangSmith** | LangChain-native | Hierarchical trace structures, session replay | Active |
| **Langfuse** | Open-source, SQL analysis | BigQuery integration, trace masking | Active (acquired by Clickhouse) |
| **Galileo AI** | Hallucination detection | Luna-2 evaluators (<200ms), Signals engine for automated failure analysis | Active |
| **AgentOps** | Multi-agent governance | Framework-native agent monitoring | Active |
| **Portkey** | AI Gateway routing | Intelligent routing, fallback chains | Active |
| **W&B Weave** | Agent observability | Experiment tracking integration | Active |

### 7.2 Key 2026 Innovations

1. **Agent Decision Graphs**: Visual execution trees showing tool calls and state changes (Arize)
2. **Trajectory Mapping**: Automatic detection of recursive loops and inefficient patterns (multiple tools)
3. **Composite Metrics**: Combining multiple scores into automated gatekeeping decisions (Braintrust, Galileo)
4. **MCP Tracing**: Model Context Protocol integration for unified client-server trace hierarchies (Arize Phoenix)
5. **Natural Language Evaluator Generation**: Define quality metrics via English descriptions, not code (Braintrust Loop, Galileo)
6. **Galileo Signals**: Automated failure mode analysis across millions of traces

### 7.3 Architectural Decision: SDK vs Proxy

Critical choice highlighted across multiple sources:
- **Proxy-based** (Portkey, Helicone): Single point of failure, but zero-code integration
- **SDK-based** (LangSmith, Braintrust, DeepEval): More resilient, maintains agent functionality during backend outages
- **OTel-native** (Arize Phoenix, Langfuse): Standard-based, vendor-neutral, most flexible

**Key Insight for AlphaSwarm.sol**: Our JSONL hook-based approach is essentially a lightweight SDK pattern. For production, we should consider OpenTelemetry integration for standardized trace export, enabling use of any observability tool without code changes.

---

## 8. Test Contract Patterns

### 8.1 Relari Agent Contracts -- YAML/JSON Specification Pattern

**Source**: https://agent-contracts.relari.ai/contracts/specifications

```yaml
# Offline scenario example
scenarios:
  - name: "basic_vulnerability_detection"
    data:
      input: "Analyze ReentrancyVuln.sol for reentrancy"
      contract_path: "tests/contracts/ReentrancyVuln.sol"
    contracts:
      - preconditions:
          - "Graph must be built successfully"
        pathconditions:
          - "Agent must query BSKG before making conclusions"
          - "Agent must check call-before-state-update patterns"
        postconditions:
          - "Finding mentions reentrancy vulnerability"
          - "Evidence includes graph node IDs"
```

### 8.2 Agent Behavioral Contracts (ABC) -- Formal Specification

```
Contract C = (P, I, G, R)
  P (Preconditions): {graph_built, contract_loaded, tools_available}
  I (Invariants): {graph_first_enforcement, evidence_required}
  G (Governance): {no_code_reading_before_graph, token_budget_limit}
  R (Recovery): {retry_with_different_query, escalate_to_human}
```

### 8.3 Prompt Spec -- YAML Agent Specification

**Source**: https://prompt-spec.com/docs/agent-specifications
**Status**: Active

Declarative YAML format for defining agents, tools, and benchmarks:
- metadata section
- agent definition (instructions, tools, constraints)
- benchmark section (test cases, evaluation criteria)

### 8.4 Open Agent Specification (Agent Spec)

**Source**: arXiv:2510.04173 (multi-institution, October 2025)
**URL**: https://arxiv.org/abs/2510.04173
**Status**: Published, v4

Unified representation for AI agents addressing framework fragmentation. Standardizes how agents are defined, executed, and evaluated across different frameworks.

**Key Insight for AlphaSwarm.sol**: Our evaluation contracts should adopt a standardized YAML format combining:
- Relari's precondition/pathcondition/postcondition structure
- ABC's formal invariant + governance specification
- DeepEval's metric configuration

---

## 9. Agentic Testing Frameworks

### 9.1 LangWatch Scenario (Active, February 2026)

**Source**: LangWatch
**URL**: https://github.com/langwatch/scenario
**Docs**: https://langwatch.ai/scenario/
**Languages**: Python, TypeScript, Go
**Status**: Active open-source project

**The most mature agent-tests-agent framework found.**

**Architecture**: Three agent types work together:
1. **Your Agent**: System under test (integrated via `call()` method)
2. **User Simulator Agent**: Generates realistic user messages based on scenario descriptions
3. **Judge Agent**: Real-time evaluation against specified criteria

**Three Simulation Modes**:
- **Autopilot**: User simulator + judge run fully automatically
- **Controlled**: Explicit script with `scenario.user()`, `scenario.agent()`, `scenario.proceed()`, `scenario.judge()`
- **Hybrid**: Controlled opening + autopilot continuation

**Example (highly relevant pattern)**:
```python
@pytest.mark.agent_test
@pytest.mark.asyncio
async def test_graph_first_reasoning():
    result = await scenario.run(
        name="graph_first_reasoning",
        description="""
        The agent receives a contract with potential reentrancy.
        It must query the BSKG before making any conclusions.
        It should NOT read source code directly before querying the graph.
        """,
        agents=[
            SecurityAnalysisAgent(),
            scenario.UserSimulatorAgent(),
            scenario.JudgeAgent(
                criteria=[
                    "agent queries BSKG before stating any findings",
                    "agent cites graph node IDs in evidence",
                    "agent does NOT manually read contract source before graph query",
                ],
            ),
        ],
        max_turns=10,
    )
    assert result.success
```

**Key Insight for AlphaSwarm.sol**: This is the closest existing framework to what we need for Agent Teams evaluation. The judge agent + user simulator pattern maps to our verifier + test scenario approach. The criteria-based evaluation is simpler but potentially more robust than our 7-move decomposition for initial capability testing.

### 9.2 RagaAI Catalyst Agentic Testing

**Source**: RagaAI
**URL**: https://docs.raga.ai/ragaai-catalyst/agentic-testing
**Status**: Production platform

Enterprise agentic testing platform with:
- Multi-turn conversation evaluation
- Tool call validation
- RAG-specific metrics (hallucination, faithfulness, context relevancy)
- Agent-specific metrics (task completion, goal accuracy)

### 9.3 DeepEval Agentic Evaluation Suite

**Source**: Confident AI
**URL**: https://deepeval.com/docs/metrics-task-completion
**Status**: Production-ready, actively updated

Comprehensive metrics suite (detailed in section 2.1) with trace-based evaluation. Notable features:
- **DAGMetric**: Custom deterministic evaluation via LLM-powered decision trees (alternative to G-Eval)
- **ConversationalTestCase**: Multi-turn evaluation with full tool call history
- **Golden datasets**: Export known-good runs as evaluation baselines

### 9.4 Helix Agent Framework (February 2026)

**Source**: sarcasticdhruv/helix-agent
**URL**: https://github.com/sarcasticdhruv/helix-agent
**Status**: New (created Feb 23, 2026)

Production-focused framework with built-in:
- Hard budget limits
- Semantic caching (40-70% API cost reduction)
- YAML-based task pipelines
- 5-scorer evaluation suite
- Multi-agent teams

---

## 10. Synthesis: Recommendations for AlphaSwarm.sol

### Direct Applicability Matrix

| Technique | Applicability | Priority | Effort |
|-----------|--------------|----------|--------|
| ABC Formal Contracts (precondition/invariant/governance/recovery) | **Critical** -- formalizes our evaluation contracts | HIGH | Medium |
| Relari Agent Contracts YAML format | **High** -- standardizes our test specification | HIGH | Low |
| DeepEval trajectory metrics (Plan Quality + Step Efficiency) | **High** -- enriches our 7-move scoring | MEDIUM | Medium |
| agent-replay diff/fork pattern | **High** -- enables regression detection | MEDIUM | Medium |
| AISI transcript failure mode taxonomy | **High** -- improves our anti-fabrication checks | HIGH | Low |
| LangWatch Scenario judge agent pattern | **High** -- alternative to Agent Teams isolation | MEDIUM | Medium |
| Behavioral fingerprinting (41-feature approach) | **Medium** -- detects agent drift | MEDIUM | High |
| Agent Stability Index (12 dimensions) | **Medium** -- composite drift metric | LOW | Medium |
| Inspect Scout scanner approach | **Medium** -- automated transcript scanning | LOW | Medium |
| UDora adversarial reasoning perturbation | **Low** -- advanced adversarial testing | LOW | High |

### Concrete Improvement Recommendations

#### R1: Adopt ABC Contract Structure for Evaluation Contracts
Replace ad-hoc evaluation contracts with formal C = (P, I, G, R):
- **P**: Graph built, tools available, contract loaded
- **I**: Graph-first enforcement, evidence required, no fabrication
- **G**: Token budget, tool restriction, isolation rules
- **R**: Retry with different query strategy, escalate to human

This gives mathematical drift bounds (D* = alpha/gamma) for our multi-agent chains.

#### R2: Implement Trace Diff for Regression Detection
Adopt agent-replay's diff pattern:
- Store JSONL traces as golden baselines
- On each evaluation run, diff against baseline
- Flag divergence points automatically
- Fork traces to test fix hypotheses

#### R3: Add DeepEval-style Trajectory Metrics
Complement our 7-move reasoning scoring with:
- Plan Quality (does the agent form a reasonable investigation plan?)
- Step Efficiency (are there redundant BSKG queries or circular reasoning?)
- Tool Correctness (are CLI tool calls correct with right arguments?)

#### R4: Implement AISI Failure Mode Detection
Automatically scan JSONL transcripts for:
- Policy compliance refusals (agent refusing to analyze patterns)
- Task resignation (agent giving up on complex analysis)
- Scaffold non-compliance (agent not using CLI tools as instructed)
- False completion claims (agent claims done but graph state contradicts)

#### R5: Adopt YAML-Based Test Specifications
Migrate evaluation contracts to Relari-style YAML:
```yaml
specification:
  name: "reentrancy_detection_capability"
  scenarios:
    - name: "basic_reentrancy"
      data:
        contract: "tests/contracts/ReentrancyVuln.sol"
      contracts:
        - preconditions:
            - "build-kg completes without error"
          pathconditions:
            - "agent queries for call-before-state-update pattern"
            - "agent does not read source before graph query"
          postconditions:
            - "finding identifies reentrancy"
            - "evidence includes function node IDs"
```

#### R6: Build Behavioral Fingerprints for Agent Drift Detection
Track per-evaluation-session:
- Tool call sequence patterns
- Query formulation patterns
- Reasoning structure (which moves appear, in what order)
- Evidence citation patterns
- Time-to-conclusion patterns

Use these as a composite Agent Stability Index. Alert when fingerprint diverges > threshold.

#### R7: Implement Chaos Testing for Agent Robustness
Inspired by Agents of Chaos + UDora:
- Inject empty graph query results (test graceful degradation)
- Inject contradictory tool outputs (test reasoning robustness)
- Inject malformed contract code (test error handling)
- Test false completion detection (agent claims done but state contradicts)

#### R8: Consider OpenTelemetry Integration
Multiple tools (Arize Phoenix, Langfuse, Relari) converge on OTel as the standard trace format. Emitting our JSONL hooks as OTel spans would enable:
- Plugging into any observability tool without code changes
- Standardized trace export for external analysis
- Future-proofing against tool ecosystem changes

---

## Key References

### Papers
1. Agent Behavioral Contracts (arXiv:2602.22302, Feb 2026)
2. Fingerprinting AI Coding Agents on GitHub (arXiv:2601.17406, Jan 2026)
3. Agent Drift in Multi-Agent LLM Systems (arXiv:2601.04170, Jan 2026)
4. Agents of Chaos (arXiv:2602.20021, Feb 2026)
5. UDora: Unified Red Teaming Framework (arXiv:2503.01908, Feb 2025)
6. Agent-Testing Agent (arXiv:2508.17393, Jun 2025)
7. Nexus: Multi-Agent Test Oracle Synthesis (arXiv:2510.26423, Oct 2025)
8. Goal Drift in Language Model Agents (AAAI AIES 2025)
9. Adversarial Robustness of LLM-Based Multi-Agent Systems (ICLR 2026 submission)
10. NIST AI 800-2: Practices for Automated Benchmark Evaluations (Jan 2026)
11. NIST AI 800-3: Expanding the AI Evaluation Toolbox (Feb 2026)

### Tools & Frameworks
1. DeepEval (https://deepeval.com) -- Agent evaluation metrics suite
2. agent-replay (https://github.com/clay-good/agent-replay) -- Trace replay/diff
3. Relari Agent Contracts (https://github.com/relari-ai/agent-contracts) -- YAML contract testing
4. LangWatch Scenario (https://github.com/langwatch/scenario) -- Agent-tests-agent framework
5. Inspect AI / Inspect Scout (https://inspect.aisi.org.uk/) -- UK AISI evaluation framework
6. Microsoft Agent-Pex -- Automated specification extraction + testing
7. Arize Phoenix (https://arize.com) -- OTel-native agent observability
8. Braintrust (https://braintrust.dev) -- Evaluation-first observability
9. Galileo AI (https://galileo.ai) -- Hallucination detection + Signals engine
10. MAFBench (https://github.com/CoDS-GCS/MAFBench) -- Multi-agent framework benchmark

### Government/Institutional
1. NIST CAISI: AI Agent Standards Initiative (launched Feb 17, 2026)
2. NIST CAISI: Transcript analysis tools for cheating detection
3. UK AISI: Transcript analysis methodology + Inspect Scout
4. UK AISI: Autonomous Systems Evaluation Standard
