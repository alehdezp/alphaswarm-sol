# Self-Improvement, Self-Evolution, and Automated Optimization of AI Agent Systems

**Research Date:** March 1, 2026
**Scope:** Latest techniques (2025-March 2026) for building self-improving AI agent testing and evaluation systems
**Applicability Focus:** Claude Code testing framework with sandbox isolation for prompt experiments

---

## Table of Contents

1. [Automated Prompt Optimization Frameworks](#1-automated-prompt-optimization-frameworks)
2. [Self-Play, Self-Critique, and Constitutional AI](#2-self-play-self-critique-and-constitutional-ai)
3. [Curriculum Learning for Agents](#3-curriculum-learning-for-agents)
4. [Automated Test Generation from Failures](#4-automated-test-generation-from-failures)
5. [Reflection and Metacognition](#5-reflection-and-metacognition)
6. [Continuous Improvement Loops](#6-continuous-improvement-loops)
7. [Safe Experimentation](#7-safe-experimentation)
8. [Agent Skill Evolution](#8-agent-skill-evolution)
9. [Synthesis: Applicability to AlphaSwarm Testing Framework](#9-synthesis)

---

## 1. Automated Prompt Optimization Frameworks

### 1.1 DSPy 3.0 (Stanford NLP, Aug 2025)

**URL:** https://dspy.ai/ | https://pypi.org/project/dspy/3.0.0/
**Paper:** "Optimizing Instructions and Demonstrations for Multi-Stage Language Model Programs"
**Status:** Released v3.0.0, active development toward 3.x

DSPy 3.0 represents the most mature automated prompt optimization framework. Key capabilities:

- **Declarative Signatures**: Define input/output schemas as Python code rather than natural language prompts. The system compiles these into optimized prompts automatically.
- **Optimizers (formerly "Teleprompters")**: Algorithms that improve prompt quality against measurable metrics. MIPROv2 is the current state-of-the-art optimizer for multi-stage programs.
- **Module Composition**: Build complex pipelines by composing simple modules (ChainOfThought, ReAct, etc.), each independently optimizable.
- **Framework-agnostic**: Produces prompt strings usable with any LLM provider.
- **MCP Integration**: Listed as an extra dependency (`dspy[mcp]`), suggesting MCP tool support.
- **Evaluation-driven**: Built-in evaluators create feedback loops between performance measurement and optimization.

**Applicability (HIGH):** DSPy's evaluate-then-optimize pattern maps directly to our testing framework. Agent prompts (skill instructions, investigation prompts) could be defined as DSPy signatures, optimized against evaluation metrics (graph value scores, reasoning decomposition scores), and compiled into improved versions. The sandbox isolation via worktrees provides the safe experimentation environment DSPy optimizers need.

### 1.2 TextGrad (Stanford HAI, 2024-2025, continued development)

**URL:** https://hai.stanford.edu/news/textgrad-autograd-text
**Paper:** "TextGrad: Automatic Differentiation via Text"
**Status:** Stable framework, active research extensions through Jan 2026

TextGrad applies the backpropagation paradigm to text optimization:

- **Textual Gradients**: LLMs generate "gradient-like" feedback describing how to improve text inputs, analogous to numerical gradients in neural networks.
- **Computation Graphs**: Builds a computational graph of text transformations where each node receives textual feedback about improvements.
- **Multi-domain**: Works across prompts, code, molecular design, and multi-agent workflows.
- **Iterative Refinement**: Uses projected gradient descent and Monte Carlo sampling to map continuous gradients to discrete text operations.

**Applicability (MEDIUM):** TextGrad's approach could optimize individual agent prompts (e.g., attacker, defender, verifier instructions) by treating evaluation scores as the loss function and generating textual improvement suggestions. However, the framework is more suited for single-prompt optimization than multi-stage pipeline optimization.

### 1.3 promptolution (ELLIS Institute / AutoML, Dec 2025)

**URL:** https://github.com/automl/promptolution | https://arxiv.org/html/2512.02840v2
**Paper:** "promptolution: A Unified, Modular Framework for Prompt Optimization"
**Status:** v1.x, Apache-2.0, 102 GitHub stars

A unified framework integrating multiple prompt optimization algorithms:

- **Integrated Optimizers**: EvoPrompt (evolutionary), OPRO (optimization by prompting), PromptBreeder (self-referential evolution), and others in a single codebase.
- **Modular Architecture**: Swap optimizers, evaluation functions, and LLM backends independently.
- **Reproducible Benchmarking**: Standardized evaluation protocols for comparing optimization methods.
- **Framework-agnostic Output**: Returns plain prompt strings, enabling integration into any LLM pipeline.

**Applicability (HIGH):** This is the "meta-framework" we could use to experiment with different optimization strategies without committing to one. Test OPRO vs PromptBreeder vs EvoPrompt on our evaluation prompts in isolated worktrees, measure which produces better reasoning scores.

### 1.4 GREATERPROMPT (Apr 2025)

**URL:** https://arxiv.org/abs/2504.03975
**Paper:** "GREATERPROMPT: A Unified, Customizable, and High-Performing Open-Source Toolkit for Prompt Optimization"

Another unified toolkit competing with promptolution. Emphasizes customizability and high performance across diverse task types.

### 1.5 PromptGrad and ContraPrompt (VizopsAI, Feb 2026)

**URL:** https://vizops.ai/blog/prompt-optimization-playbook/
**Status:** Research + practical comparison (Feb 2026)

A critical finding: **there is no universal best prompt optimizer**. The right choice depends on the task:

| Method | Approach | Best For | Result |
|--------|----------|----------|--------|
| **PromptGrad** | Gradient-based: analyze failures, extract targeted correction rules, validate independently | Diverse failure modes, auditability needed | +18% over GEPA baseline |
| **ContraPrompt** | Contrastive: compare failed vs successful retries, extract what changed | Tasks with self-correction potential | +14% over GEPA baseline |
| **GEPA** | Evolutionary baseline | Unknown failure patterns (starting point) | Baseline |

**Decision heuristic:**
1. Test 20 failed examples with "Think more carefully"
2. If >25% retry success: use ContraPrompt
3. If <15% retry success: use PromptGrad
4. 15-25%: test both (~$1 total cost)

**Applicability (HIGH):** This decision framework maps directly to our evaluation system. When agent reasoning scores are low, we can characterize failures (diverse vs consistent patterns) and apply the appropriate optimizer. ContraPrompt is especially relevant because our Dual-Opus evaluator already generates "failed vs succeeded" comparisons.

### 1.6 Hierarchical Attribution Prompt Optimization (HAPO, Aug 2025 / arXiv Jan 2026)

**URL:** https://arxiv.org/html/2601.02683v1
**Paper:** "Learning from Prompt itself: the Hierarchical Attribution Prompt Optimization"

Addresses **prompt drift** -- the common failure mode where optimized prompts fix prior failures but break previously successful cases. Uses hierarchical attribution to identify which prompt components affect which test cases.

**Applicability (HIGH):** This directly addresses our regression detection problem. When improving agent prompts for one vulnerability category, HAPO's attribution approach could prevent degradation on other categories.

---

## 2. Self-Play, Self-Critique, and Constitutional AI

### 2.1 Constitutional AI: 2026 State of the Art

**URL:** https://zylos.ai/research/2026-02-01-constitutional-ai-alignment-alternatives
**Status:** Matured significantly by 2026

Key developments since the original Anthropic paper:

- **Collective Constitutional AI**: Public input democratizes AI values selection. Principles aren't fixed by researchers but evolved through community feedback.
- **DPO (Direct Preference Optimization)**: Emerged as a computationally efficient alternative that eliminates reinforcement learning entirely. Directly optimizes the policy from preference data without training a separate reward model.
- **RLAIF Scaling**: AI-generated feedback now matches or exceeds human feedback quality for many alignment tasks, enabling vastly larger training datasets.

### 2.2 Self-Improving AI Agents through Self-Play (Chojecki, Dec 2025)

**URL:** https://arxiv.org/html/2512.02731v1
**Paper:** "Self-Improving AI Agents through Self-Play"

Formalizes self-improvement mathematically:

- **Generator-Verifier-Updater (GVU) Operator**: Recursive operator where an agent generates solutions, verifies them, and updates its own parameters.
- **Variance Inequality**: A spectral condition sufficient for stable self-improvement. If the combined noise of generation and verification is below a threshold, self-improvement is provably stable.
- **Coefficient of Self-Improvement (kappa)**: Defined as the Lie derivative of the capability functional along the improvement flow. kappa > 0 means the agent is genuinely improving.

**Applicability (MEDIUM):** The mathematical framework could inform our evaluation metrics. We could define a "kappa" for our testing system -- measuring whether successive evaluation rounds show genuine improvement or just noise.

### 2.3 Runtime Constitutional AI (ODEI, Feb 2026)

**URL:** https://dev.to/zer0h1ro/runtime-constitutional-ai-validating-every-agent-action-before-execution-546c
**Paper/Post:** "Runtime Constitutional AI: Validating Every Agent Action Before Execution"

Extends constitutional AI from training-time to runtime:

- **Pre-action validation**: Every consequential agent action is validated against constitutional principles before execution.
- **Training-Time Gap**: Training-time CAI cannot prevent: duplicate actions, hallucinated references, unauthorized operations.
- **Runtime enforcement**: Validation layer intercepts agent actions and checks against a constitutional rule set.

**Applicability (HIGH):** Our evaluation framework already has this pattern (hooks, evidence gates). This research validates our approach and provides formal grounding for runtime constraint enforcement during agent evaluations.

---

## 3. Curriculum Learning for Agents

### 3.1 Self-Evolving Curriculum (SEC) (Mila / ServiceNow, 2025-2026)

**URL:** https://arxiv.org/html/2505.14970v3
**Paper:** "Self-Evolving Curriculum for LLM Reasoning"

The most directly applicable curriculum learning approach:

- **MAB-based Curriculum**: Treats training data categories as arms in a Multi-Armed Bandit problem. Uses Boltzmann sampling with temperature-controlled exploration.
- **Advantage-based Rewards**: Uses absolute advantage values as proxy for learning gain. Maximized when success rate = 0.5 (Zone of Proximal Development).
- **Dynamic Adaptation**: Curriculum automatically shifts toward harder problems as model capability improves.
- **Results**: 13-33% improvement on out-of-distribution tasks vs random curricula.

**Applicability (HIGH):** Our evaluation framework could implement SEC for test case scheduling. Categorize test contracts by difficulty (simple reentrancy vs complex cross-function bugs), start with easier cases, and automatically advance difficulty as agent performance improves. The MAB formulation is simple enough to implement in Python without deep learning infrastructure.

### 3.2 TAROT: Test-Driven Curriculum Reinforcement Fine-Tuning (Feb 2026)

**URL:** https://arxiv.org/abs/2602.15449
**Paper:** "TAROT: Test-driven and Capability-adaptive Curriculum Reinforcement Fine-tuning for Code Generation"

Key insight: **optimal curriculum depends on model capability**.

- **Four-tier test suites**: basic, intermediate, complex, edge cases
- **Capability-conditioned evaluation**: Less capable models benefit from easy-to-hard; stronger models from hard-first
- **Principled curriculum portfolio**: Rather than one fixed schedule, selects from multiple curriculum policies based on current model capability

**Applicability (HIGH):** Directly maps to our tiered vulnerability detection system (Tier A/B/C). Start agents on Tier A (deterministic, graph-only) patterns, progress to Tier B (LLM-verified), then Tier C (label-dependent). TAROT's capability-adaptive selection means we don't need to manually decide when to advance.

### 3.3 AdaCuRL: Adaptive Curriculum RL (Sep 2025)

**URL:** https://arxiv.org/html/2511.09478v1
**Paper:** "Adaptive Curriculum Reinforcement Learning with Invalid Sample Mitigation and Historical Revisiting"

Addresses three specific curriculum learning failures:
- **Difficulty mismatch**: Training on too-hard problems wastes compute
- **Catastrophic forgetting**: Moving to new difficulty levels erases learned capabilities
- **Invalid samples**: Some training examples are inherently unsolvable and poison learning

Uses historical revisiting to prevent forgetting -- periodically re-testing on previously mastered difficulty levels.

**Applicability (MEDIUM):** The "historical revisiting" pattern maps to our regression detection. After improving agent performance on complex vulnerabilities, periodically re-test on simple ones to catch capability degradation.

### 3.4 Interactive LLM-assisted Curriculum Learning (Feb 2026)

**URL:** https://arxiv.org/pdf/2602.10891
**Paper:** "Interactive LLM-assisted Curriculum Learning for Multi-Task Evolutionary Policy Search"

Uses an LLM as the curriculum designer itself. The optimizer LLM examines performance metrics, visualizes behavior, and generates the next training case. This is a meta-level approach where the curriculum is itself AI-generated.

---

## 4. Automated Test Generation from Failures

### 4.1 DoVer: Intervention-Driven Auto Debugging (Microsoft, Dec 2025)

**URL:** https://arxiv.org/html/2512.06749v2
**Paper:** "DoVer: Intervention-Driven Auto Debugging for LLM Multi-Agent Systems"

The most sophisticated approach to automated debugging of multi-agent failures:

- **Hypothesize-Intervene-Verify Loop**: Instead of just analyzing logs, DoVer actively modifies agent traces to test causal hypotheses about failures.
- **Multi-point Attribution**: Rejects single-agent/single-step attribution; finds that multiple interventions can independently fix a failure.
- **Fix Rates**: 17.6-27.5% of failed tasks fixed automatically on AssistantBench/GAIA; 49% on GSMPlus.
- **Hypothesis Validation**: Validates or refutes 30-60% of fault hypotheses through active intervention.

**Applicability (HIGH):** This is exactly what we need for our evaluation framework. When an agent evaluation fails, DoVer's approach suggests: (1) generate hypotheses about why, (2) modify specific parts of the prompt/context, (3) re-run to verify. Our worktree isolation provides the perfect sandboxed environment for these interventions.

### 4.2 Agentic QA: Self-Generating Test Suites (PractiTest, Dec 2025)

**URL:** https://www.practitest.com/resource-center/blog/agentic-ai-automated-software-testing/
**Status:** Industry adoption pattern

Key capabilities emerging in production testing:

- **Dynamic test generation**: Generate new tests when applications change, not just when humans write them
- **Automated root cause analysis**: AI identifies why tests fail, not just that they fail
- **Code change impact evaluation**: Automatically determine which tests need updating when code changes
- **Adaptive execution**: Adjust test suites in real-time based on observed failure patterns

### 4.3 Self-Healing Test Frameworks (EJCSIT, Jun 2025)

**URL:** https://eajournals.org/ejcsit/vol13-issue34-2025/
**Paper:** "AI-Driven Quality Assurance: Integrating Generative Models, Predictive Analytics, and Self-Healing Frameworks"

Three integrated innovations:
1. **Generative AI for test script creation**: LLMs generate test scripts from specifications
2. **Predictive defect analytics**: ML models predict where defects are likely based on code change patterns
3. **Self-healing test automation**: Tests that automatically adapt when the system under test changes

---

## 5. Reflection and Metacognition

### 5.1 MARS: Metacognitive Agent Reflective Self-Improvement (NTU, Jan 2026)

**URL:** https://arxiv.org/abs/2601.11974
**Paper:** "Learn Like Humans: Use Meta-cognitive Reflection for Efficient Self-Improvement"
**Status:** arXiv, Jan 2026

The most practical metacognitive framework for AI agents:

- **Dual Reflection Model**:
  - **Principle-based**: Abstracts normative rules to prevent errors ("Always verify graph queries return results before drawing conclusions")
  - **Procedural**: Derives step-by-step strategies for success ("When querying for access control, check both modifier presence AND function visibility")
- **Single Recurrence Cycle**: Achieves self-improvement in ONE reflection pass, not multi-turn recursive loops. Drastically reduces computational cost.
- **Outperforms SOTA**: Superior performance across six benchmarks while using substantially fewer compute resources.

**Applicability (VERY HIGH):** This maps almost perfectly to our evaluation framework's self-improvement cycle. After each agent evaluation batch:
1. Extract principle-based reflections: "What rules should the agent follow?"
2. Extract procedural reflections: "What step-by-step approach works best?"
3. Synthesize into improved agent instructions
4. Re-evaluate with improved instructions

The single-recurrence property is critical -- it means we can run this after each evaluation batch without exponential cost growth.

### 5.2 ICML 2025 Position Paper: Truly Self-Improving Agents Require Intrinsic Metacognitive Learning

**URL:** https://openreview.net/forum?id=4KhDd0Ozqe
**Paper:** Tennison Liu, Mihaela van der Schaar (ICML 2025)

Argues that current self-improvement approaches are limited because:
- Self-improvement processes are rigid and fail to generalize across task domains
- They struggle to scale with increasing agent capabilities
- **Intrinsic metacognitive learning** is required: the agent must learn to learn, not just learn to solve

### 5.3 Metacognitive Skills for LLM Error Reduction (Alignment Forum, Feb 2026)

**URL:** https://www.alignmentforum.org/posts/m5d4sYgHbTxBnFeat/
**Author:** Seth Herd
**Status:** Position paper, Feb 2026

Argues LLMs lack metacognitive skills that help humans catch errors:
- Better metacognition would **stabilize alignment** by catching actions the system wouldn't "endorse on reflection"
- LLM "slop" (low-quality outputs) stems from insufficient self-monitoring
- Proposes metacognitive training as net-positive for alignment despite capability improvement

### 5.4 Verbal Reinforcement in Agent Loops (Better ML, Feb 2026)

**URL:** https://medium.com/better-ml/verbal-reinforcement-in-agent-loops-generate-evaluate-revise-042d7ba634e0
**Status:** Blog post, Feb 28, 2026

Frames generate-evaluate-revise loops as "verbal reinforcement learning at test time":
- A one-shot LLM breaks when tasks are brittle, constraints are tight, or costs of errors are high
- The evaluate-revise loop acts as test-time RL, where verbal feedback replaces numerical rewards
- This is theoretically grounded: verbal critique functions as a policy gradient signal

---

## 6. Continuous Improvement Loops

### 6.1 The 7-Step Agent Feedback Loop (Dev.to, Jan 2026)

**URL:** https://dev.to/imshashank/the-ai-agent-feedback-loop-from-evaluation-to-continuous-improvement-5hm4

A practical production architecture:

| Step | Action | AlphaSwarm Mapping |
|------|--------|-------------------|
| 1. Evaluate at Scale | Run evaluations on all interactions | Batch evaluation runner |
| 2. Identify Failure Patterns | Find systematic failures, not individual cases | Tier-weighted regression detection |
| 3. Diagnose Root Cause | Ambiguous prompts? Knowledge gaps? Tool defects? | Interactive feedback via SendMessage |
| 4. Generate Recommendations | Specific, testable hypotheses | MARS-style dual reflections |
| 5. Implement Change | Modify prompts, swap models, fix tools | Worktree-isolated modifications |
| 6. Re-evaluate and Compare | Same interactions, new changes | Regression suite re-run |
| 7. Iterate | Deploy or refine and repeat | Tier promotion/demotion |

### 6.2 The Evaluator-Optimizer Loop (Hopx.ai, Nov 2025)

**URL:** https://hopx.ai/blog/ai-agents/evaluator-optimizer-loop/

Architectural pattern separating evaluation from generation:
- **Generator**: Creates initial output
- **Evaluator**: Scores and identifies issues
- **Optimizer**: Improves based on evaluation feedback
- **Termination**: Quality threshold met OR max iterations reached

Best suited for: critical output quality, clear quality standards, sufficient token budget.
Avoid when: speed matters more than quality, criteria are unclear.

### 6.3 The Agent CI Loop (AvestaLabs, Sep 2025)

**URL:** https://avestalabs.ai/blog/continuous-improvement-ci-loop-for-ai-agents

Core insight: "Shipping an AI agent is the easy half. Improving it is the hard half."

The CI loop for agents parallels software CI/CD:
- **Build**: Define agent behavior and guardrails
- **Measure**: Track performance, collect feedback, monitor drift
- **Learn**: Analyze failures, extract patterns, update instructions
- **Repeat**: Deploy improvements, measure again

### 6.4 Arize: Self-Improving Agents via Telemetry (Feb 2026)

**URL:** https://arize.com/blog/closing-the-loop-coding-agents-telemetry-and-the-path-to-self-improving-software/
**Author:** Mikyo King (Arize AI)

Critical insights from production agent systems:

- **The Agent Harness > The Model**: The wrapper infrastructure (tool orchestration, context management, verification checkpoints) matters more than model capability. Bare model loops cannot produce production-quality output.
- **Traces as Documentation**: "In software, the code documents the app; in AI, the traces do." Agent traces are the ground truth for debugging and improvement.
- **OpenAI's Harness Experience**: Built an internal product entirely with Codex agents (~1M lines, 1,500 PRs, zero manual code). Key finding: "Monolithic instruction files fail. Knowledge must be a structured system with pointers to deeper truth -- skills."
- **Shifted Engineer Role**: Human responsibility transitions from reviewing every change to auditing the verification systems themselves.

**Applicability (VERY HIGH):** This validates our entire evaluation architecture. Our BSKG traces, evaluation observations, and agent debrief transcripts ARE the documentation. The self-improvement loop needs to operate on these traces.

---

## 7. Safe Experimentation

### 7.1 Runtime Constitutions for Self-Governing Agents (Blake Crosley, Feb 2026)

**URL:** https://blakecrosley.com/blog/agent-self-governance
**Status:** Comprehensive synthesis of six research papers (Feb 22, 2026)

The most relevant single source for safe self-improvement. Six research efforts converge on **runtime governance**:

**The Core Problem:** "How do you let an agent learn new capabilities without letting it unlearn the constraints that keep it safe?"

**Four Architectural Subsystems:**

| Subsystem | Function | Our Mapping |
|-----------|----------|-------------|
| **Normative Prior Engineering** | Define acceptable behavior boundaries | CLAUDE.md constraints, evidence gate criteria |
| **Constitutional Attention** | Route governance rules to relevant contexts | Progressive disclosure, selective skill loading |
| **Competence Modulation** | Manage skill acquisition safely | Tier promotion/demotion, approval gates |
| **Value Alignment Verification** | Runtime compliance checking | Agent execution validator, anti-fabrication checks |

**Three-File Runtime Constitution:**
1. `constitution.md` -- Immutable constraints and behavioral norms
2. `capabilities.json` -- Skill inventory with provenance and approval status
3. `constraints-registry.json` -- Maps every constraint to its canonical source

**Active vs Passive Governance:**
- **Passive**: Inject rules in CLAUDE.md and hope the agent follows them
- **Active**: Verify compliance at runtime via hooks, gates, and monitors

**Key Research Finding (SkillsBench):** Testing 7,308 agent trajectories across 86 tasks, self-generated skills showed **zero average improvement** while curated skills improved performance by 16.2 percentage points. This means unconstrained self-improvement is actively harmful -- governance is not optional.

**Applicability (CRITICAL):** This is the safety framework our testing system needs. Our worktree isolation is the "Competence Modulation" layer. Our evidence gates are "Value Alignment Verification." We need to add a formal constraints-registry to prevent prompt modifications from degrading established capabilities.

### 7.2 Prompt Testing Tools in Production (Adaline, Jan 2026)

**URL:** https://www.adaline.ai/blog/best-prompt-testing-tools-in-2026

Production-grade prompt testing infrastructure as of 2026:

| Tool | Best For | Key Feature |
|------|----------|-------------|
| **Adaline** | End-to-end release discipline | Datasets + regression + thresholds + approvals + rollback |
| **Promptfoo** | Repo-native CI integration (open source) | Red teaming + CI pipeline integration |
| **LangSmith** | LangChain ecosystem | Dataset-based regression + experiment comparison |
| **Braintrust** | Structured evaluation programs | A/B testing via playground comparison |
| **Langfuse** | A/B testing + tracing (open source) | Prompt version labeling + canary deployment |

**Regression Testing Protocol (7 steps):**
1. Define quality criteria
2. Assemble 30-80 baseline test cases
3. Implement multi-method scoring (rubric, LLM-as-judge, keyword, custom code)
4. Establish pass thresholds
5. Wire tests into CI
6. Create environment promotion workflows
7. Convert production incidents into new test cases

**Applicability (HIGH):** Step 7 is the automated test generation from failures pattern. We should implement this: every failed evaluation becomes a new regression test case.

### 7.3 A/B Testing for LLM Prompts (Braintrust / Langfuse / LangWatch, 2025-2026)

**URLs:**
- https://www.braintrust.dev/articles/ab-testing-llm-prompts
- https://langfuse.com/docs/prompts/a-b-testing
- https://docs.langwatch.ai/prompt-management/features/advanced/a-b-testing

Converging best practices for safe prompt modification:

- **Version Labeling**: Label prompt versions (e.g., `prod-a`, `prod-b`) and randomly alternate
- **Canary Deployment**: Test with small user subset before full rollout
- **Multi-dimensional Tracking**: Quality scores, latency, cost, token usage per variant
- **Statistical Significance**: Wait for sufficient sample size before declaring a winner
- **Rollback Capability**: Instant revert if quality drops below threshold

**Applicability (MEDIUM):** Our system doesn't have "production traffic" in the traditional sense, but the canary pattern maps to our evaluation batches. Run improved prompts on a subset of test contracts first, compare against baseline, then promote if metrics improve.

### 7.4 Governance at the Speed of Self-Modification (Jason Stanley, Feb 2026)

**URL:** https://jasonstanley.substack.com/p/governance-at-the-speed-of-self-modification

Position paper arguing that the traditional assumption -- "human decision-makers remain the governors and technical tools play an advisory role" -- is no longer safe for agents whose behavior evolves during deployment. Proposes extending technical AI governance from advisory tooling to **autonomous enforcement**.

---

## 8. Agent Skill Evolution

### 8.1 Darwin Godel Machine (DGM) (Sakana AI / UBC, ICLR 2026)

**URL:** https://arxiv.org/abs/2505.22954 | https://sakana.ai/dgm/ | https://github.com/jennyzzt/dgm
**Paper:** "Darwin Godel Machine: Open-Ended Evolution of Self-Improving Agents"
**Status:** Accepted at ICLR 2026 (poster), 1,825 GitHub stars, Apache 2.0

The most ambitious self-improvement system:

- **Self-modifying code**: The agent iteratively modifies its own codebase, including the code responsible for making modifications.
- **Evolutionary approach**: Multiple code variants compete. Successful modifications survive and propagate (Darwinian selection).
- **Empirical validation**: Each change is validated against coding benchmarks rather than requiring mathematical proofs (the original Godel Machine required formal proofs, which is impractical).
- **Open-ended**: The search space expands as the agent discovers new modification strategies.

**Key limitation for our use:** DGM operates at the model/code level, requiring weight modifications or substantial code rewrites. Our system operates at the prompt/instruction level. However, the evolutionary validation pattern is directly applicable.

### 8.2 EvoAgentX (University of Glasgow, EMNLP 2025 Demos)

**URL:** https://github.com/EvoAgentX/EvoAgentX | https://arxiv.org/html/2507.03616v2
**Paper:** "EvoAgentX: An Automated Framework for Evolving Agentic Workflows"
**Status:** v0.1.0, 2,582 GitHub stars, active development

Self-evolving multi-agent system framework:

- **Workflow Evolution**: Automatically generates, executes, and optimizes multi-agent workflows.
- **Five-layer Architecture**: Basic components -> Agent -> Workflow -> Evolution -> Application.
- **Evolution Algorithms**: Integrates multiple optimization algorithms for evolving agent configurations.
- **Modular**: Swap agents, tools, and optimization strategies independently.

**Applicability (HIGH):** EvoAgentX's architecture could be adapted for evolving our evaluation workflows. Instead of fixed evaluation protocols, let the system evolve which evaluation patterns work best for different vulnerability categories.

### 8.3 EvolveR: Self-Evolving LLM Agents through Experience (Oct 2025)

**URL:** https://arxiv.org/abs/2510.16079
**Paper:** "EvolveR: Self-Evolving LLM Agents through an Experience-Driven Lifecycle"

Introduces a closed-loop experience lifecycle:

- **Offline Self-Distillation**: Agent interaction trajectories are analyzed and distilled into improved strategies.
- **Experience Library**: Accumulates successful problem-solving patterns.
- **Strategy Refinement**: Iteratively refines strategies based on outcome analysis.

### 8.4 SkillRL: Agentic Memory via Skill Distillation (Feb 2026)

**URL:** https://binaryverseai.com/agentic-memory-skillrl-rl-policy-evo/
**Status:** Framework description, Feb 2026

Addresses "agent amnesia" -- the inability to retain learning across episodes:

- **Skill Distillation**: Converts noisy interaction logs into distilled skill representations
- **GRPO LLM Training**: Uses Group Relative Policy Optimization to train on distilled skills
- **Persistent Memory**: Skills persist across sessions as structured knowledge, not raw logs

### 8.5 Agent Skills Survey (Zhejiang University, Feb 2026)

**URL:** https://arxiv.org/abs/2602.12430
**Paper:** "Agent Skills for Large Language Models: Architecture, Acquisition, Security, and the Path Forward"

Comprehensive survey covering:

- **SKILL.md Specification**: Standardized format for portable skill definitions
- **Progressive Disclosure**: Skills loaded on demand to manage context window
- **MCP Integration**: Skills complement Model Context Protocol tools
- **Security Finding**: 26.1% of community-contributed skills contain vulnerabilities
- **Skill Trust Framework**: Four-tier, gate-based permission system for skill deployment

**Applicability (HIGH):** Our skill system already uses SKILL.md. The security finding (26.1% vulnerability rate) validates our strict governance approach. The four-tier trust framework could inform our tier promotion/demotion system.

### 8.6 Yunjue Agent: In-Situ Self-Evolving Tool Creation (Jan 2026)

**URL:** https://www.co-r-e.com/method/yunjue-agent-self-evolving-20260128

Agent that creates and refines its own tools as it encounters new challenges, without pre-defined tool libraries. The "In-Situ Self-Evolving" pattern means tools are generated at the point of need.

### 8.7 Recursive Knowledge Crystallization (Feb 2026)

**URL:** https://tanaikech.github.io/2026/02/21/recursive-knowledge-crystallization-a-framework-for-persistent-autonomous-agent-self-evolution/

Framework where agents continuously record and refine operational guidelines and technical knowledge, overcoming context window limits and session fragmentation barriers.

---

## 9. Synthesis: Applicability to AlphaSwarm Testing Framework

### 9.1 Recommended Architecture: The Safe Self-Improvement Loop

Based on the research above, the optimal architecture for our testing framework combines:

```
                                    GOVERNANCE LAYER (Immutable)
                                    - constitution.md (behavioral constraints)
                                    - constraints-registry.json (canonical sources)
                                    - Evidence gates (mandatory proof criteria)
                                    - Agent execution validator (12 checks)
                                         |
                                         v
 +-----------+    +-----------+    +-----------+    +-----------+
 |  EVALUATE |    |  REFLECT  |    |  OPTIMIZE |    | RE-TEST   |
 |           |--->|           |--->|           |--->|           |--+
 | Batch run |    | MARS dual |    | DSPy/     |    | Worktree  |  |
 | evaluation|    | reflection|    | promptolu-|    | isolated  |  |
 | (current  |    | (principle|    | tion      |    | re-run    |  |
 |  prompts) |    |  + proced-|    | optimizer |    |           |  |
 |           |    |  ural)    |    |           |    |           |  |
 +-----------+    +-----------+    +-----------+    +-----------+  |
      ^                                                           |
      |                                                           |
      +---[promote if improved / reject if regressed]-------------+
```

### 9.2 Specific Techniques to Implement

**Phase 1 (Immediate, low effort):**

1. **MARS-style Dual Reflection** after each evaluation batch:
   - Extract principle-based rules from failures
   - Extract procedural strategies from successes
   - Store in structured format for prompt modification proposals

2. **Failure-to-Test-Case Pipeline** (Adaline Step 7):
   - Every failed evaluation becomes a new regression test
   - Failed evaluations categorized by failure mode
   - New test cases added to regression suite automatically

3. **Active Governance Verification**:
   - Formalize our existing hooks/gates as a constraints-registry
   - Mark governance files as immutable to automated modification
   - Ensure single canonical source for each constraint

**Phase 2 (Medium effort):**

4. **SEC-style Curriculum Scheduling**:
   - Categorize test contracts by difficulty (simple/intermediate/complex/edge)
   - Use MAB algorithm (Thompson Sampling or UCB) to select test contracts
   - Track success rates per category, auto-advance difficulty
   - Historical revisiting to prevent forgetting

5. **promptolution Integration for Prompt Optimization**:
   - Define agent prompts as optimizable signatures
   - Use promptolution to test OPRO vs PromptBreeder vs EvoPrompt
   - Run optimization in worktree-isolated environments
   - Measure against graph value scores and reasoning decomposition

6. **DoVer-style Intervention Debugging**:
   - When evaluations fail, generate hypotheses about why
   - Create targeted prompt modifications for each hypothesis
   - Re-run in isolation to test each hypothesis independently
   - Track hypothesis validation rates

**Phase 3 (High effort, high reward):**

7. **PromptGrad/ContraPrompt Decision Framework**:
   - Characterize evaluation failures (diverse vs consistent patterns)
   - Apply PromptGrad for diverse failure modes, ContraPrompt for consistent ones
   - Use Dual-Opus evaluator disagreements as the retry signal for ContraPrompt

8. **EvoAgentX-style Workflow Evolution**:
   - Allow evaluation protocols themselves to evolve
   - Different vulnerability categories may need different evaluation workflows
   - Evolutionary selection of optimal evaluation strategies per category

### 9.3 Critical Safety Constraints (from SkillsBench + Runtime Constitution research)

1. **Self-generated improvements require approval**: SkillsBench showed zero average improvement from uncurated self-generated skills. All prompt modifications must pass through an approval gate.

2. **Immutable governance layer**: constitution.md, evidence gates, and validator checks cannot be modified by the optimization loop.

3. **Worktree isolation is mandatory**: All experimental prompt modifications run in isolated worktrees, never in the project root.

4. **Regression detection before promotion**: Any prompt modification must pass ALL existing regression tests before it can be promoted. HAPO's anti-drift approach can be applied here.

5. **Canonical source registry**: Each constraint maps to exactly one authoritative definition, preventing the "SEO vs citation-verifier" confusion described in Crosley's blog.

### 9.4 Key Metrics for the Self-Improvement Loop

| Metric | Source | Purpose |
|--------|--------|---------|
| **Kappa (self-improvement coefficient)** | Self-play paper | Is the system genuinely improving? |
| **Graph Value Score delta** | Our evaluator | Did prompt changes improve graph use? |
| **Reasoning decomposition scores** | 7-move scoring | Did individual reasoning steps improve? |
| **Regression rate** | Existing test suite | Did improvements break anything? |
| **Dual-Opus agreement rate** | Evaluator consistency | Are evaluations themselves reliable? |
| **Hypothesis validation rate** | DoVer-style debugging | Are our failure diagnoses accurate? |
| **Curriculum difficulty distribution** | SEC/MAB | Is the system appropriately challenging agents? |

### 9.5 Implementation Priority Matrix

| Technique | Effort | Impact | Risk | Priority |
|-----------|--------|--------|------|----------|
| MARS dual reflection | Low | High | Low | **P0** |
| Failure-to-test-case pipeline | Low | High | Low | **P0** |
| Active governance (constraints-registry) | Low | Medium | Low | **P0** |
| SEC curriculum scheduling | Medium | High | Low | **P1** |
| promptolution integration | Medium | High | Medium | **P1** |
| DoVer intervention debugging | Medium | High | Medium | **P1** |
| PromptGrad/ContraPrompt | High | High | Medium | **P2** |
| EvoAgentX workflow evolution | High | Medium | High | **P2** |
| DGM-style code self-modification | Very High | Very High | Very High | **P3 (research)** |

---

## Key Papers & Resources Index

| # | Title | Year | URL |
|---|-------|------|-----|
| 1 | DSPy 3.0 | 2025 | https://dspy.ai/ |
| 2 | TextGrad: Automatic Differentiation via Text | 2024-2025 | https://hai.stanford.edu/news/textgrad-autograd-text |
| 3 | promptolution: Unified Framework for Prompt Optimization | Dec 2025 | https://arxiv.org/html/2512.02840v2 |
| 4 | GREATERPROMPT: Unified Toolkit for Prompt Optimization | Apr 2025 | https://arxiv.org/abs/2504.03975 |
| 5 | The Prompt Optimization Playbook (PromptGrad/ContraPrompt) | Feb 2026 | https://vizops.ai/blog/prompt-optimization-playbook/ |
| 6 | HAPO: Hierarchical Attribution Prompt Optimization | Jan 2026 | https://arxiv.org/html/2601.02683v1 |
| 7 | Self-Improving AI Agents through Self-Play | Dec 2025 | https://arxiv.org/html/2512.02731v1 |
| 8 | Runtime Constitutional AI (ODEI) | Feb 2026 | https://dev.to/zer0h1ro/runtime-constitutional-ai-validating-every-agent-action-before-execution-546c |
| 9 | Constitutional AI Alignment Alternatives: Beyond RLHF | Feb 2026 | https://zylos.ai/research/2026-02-01-constitutional-ai-alignment-alternatives |
| 10 | Self-Evolving Curriculum (SEC) for LLM Reasoning | 2025-2026 | https://arxiv.org/html/2505.14970v3 |
| 11 | TAROT: Test-driven Curriculum Reinforcement Fine-tuning | Feb 2026 | https://arxiv.org/abs/2602.15449 |
| 12 | AdaCuRL: Adaptive Curriculum RL | Sep 2025 | https://arxiv.org/html/2511.09478v1 |
| 13 | DoVer: Intervention-Driven Auto Debugging | Dec 2025 | https://arxiv.org/html/2512.06749v2 |
| 14 | MARS: Metacognitive Agent Reflective Self-Improvement | Jan 2026 | https://arxiv.org/abs/2601.11974 |
| 15 | Truly Self-Improving Agents Require Intrinsic Metacognition | May 2025 | https://openreview.net/forum?id=4KhDd0Ozqe |
| 16 | Metacognitive Skills for LLM Error Reduction | Feb 2026 | https://www.alignmentforum.org/posts/m5d4sYgHbTxBnFeat/ |
| 17 | Self-Governing Agents: Runtime Constitutions | Feb 2026 | https://blakecrosley.com/blog/agent-self-governance |
| 18 | Agent Constitution Pattern | Feb 2026 | https://asdlc.io/patterns/agent-constitution/ |
| 19 | Governance at the Speed of Self-Modification | Feb 2026 | https://jasonstanley.substack.com/p/governance-at-the-speed-of-self-modification |
| 20 | Darwin Godel Machine (DGM) | ICLR 2026 | https://arxiv.org/abs/2505.22954 |
| 21 | EvoAgentX: Evolving Agentic Workflows | EMNLP 2025 | https://github.com/EvoAgentX/EvoAgentX |
| 22 | EvolveR: Self-Evolving LLM Agents | Oct 2025 | https://arxiv.org/abs/2510.16079 |
| 23 | SkillRL: Agentic Memory via Skill Distillation | Feb 2026 | https://binaryverseai.com/agentic-memory-skillrl-rl-policy-evo/ |
| 24 | Agent Skills for LLMs: Survey | Feb 2026 | https://arxiv.org/abs/2602.12430 |
| 25 | Yunjue Agent: In-Situ Self-Evolving | Jan 2026 | https://www.co-r-e.com/method/yunjue-agent-self-evolving-20260128 |
| 26 | Self-Improving Agents Harness (Arize) | Feb 2026 | https://arize.com/blog/closing-the-loop-coding-agents-telemetry-and-the-path-to-self-improving-software/ |
| 27 | 7-Step Agent Feedback Loop | Jan 2026 | https://dev.to/imshashank/the-ai-agent-feedback-loop-from-evaluation-to-continuous-improvement-5hm4 |
| 28 | Evaluator-Optimizer Loop | Nov 2025 | https://hopx.ai/blog/ai-agents/evaluator-optimizer-loop/ |
| 29 | Agent CI Loop | Sep 2025 | https://avestalabs.ai/blog/continuous-improvement-ci-loop-for-ai-agents |
| 30 | Best Prompt Testing Tools in 2026 | Jan 2026 | https://www.adaline.ai/blog/best-prompt-testing-tools-in-2026 |
| 31 | A/B Testing for LLM Prompts (Braintrust) | Nov 2025 | https://www.braintrust.dev/articles/ab-testing-llm-prompts |
| 32 | A/B Testing of LLM Prompts (Langfuse) | 2025 | https://langfuse.com/docs/prompts/a-b-testing |
| 33 | Self-Evolving Agent Skill (Playbooks/Plurigrid) | Jan 2026 | https://playbooks.com/skills/plurigrid/asi/self-evolving-agent |
| 34 | Recursive Knowledge Crystallization | Feb 2026 | https://tanaikech.github.io/2026/02/21/recursive-knowledge-crystallization/ |
| 35 | 2026 Agentic Coding Trends Report (Anthropic) | 2026 | https://resources.anthropic.com/hubfs/2026%20Agentic%20Coding%20Trends%20Report.pdf |
| 36 | Automatic Debugging in AI Agent Systems (DoVer survey) | Dec 2025 | https://saulius.io/blog/automatic-debugging-and-failure-detection-in-ai-agent-systems |
| 37 | DSPy + MIPROv2 for Agent Optimization | Nov 2025 | https://building.theatlantic.com/scaling-ai-agents-with-dspy-and-miprov2 |
| 38 | Evaluating AI Agents at Amazon | 2025-2026 | https://aws.amazon.com/blogs/machine-learning/evaluating-ai-agents/ |

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|-----------|-------|
| Prompt optimization landscape (DSPy, promptolution) | **High** | Multiple corroborating sources, active development |
| Metacognitive self-improvement (MARS) | **High** | Published paper with benchmarks |
| Curriculum learning (SEC, TAROT) | **High** | Multiple recent papers with experimental validation |
| Runtime constitutions / safe governance | **High** | Six converging research efforts identified |
| Self-play mathematics (kappa coefficient) | **Medium** | Single paper, theoretical framework not yet widely validated |
| PromptGrad/ContraPrompt specifics | **Medium** | Single blog post, limited independent validation |
| Production continuous improvement patterns | **High** | Multiple industry sources (Arize, Amazon, Anthropic) converge |
| SkillRL framework | **Low-Medium** | Blog post only, no peer-reviewed paper found |
| DGM practical applicability to prompt-level systems | **Low** | Designed for code-level self-modification, not prompt optimization |
