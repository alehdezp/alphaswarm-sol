# Research Plan: Interactive Agent Testing Improvements (March 2026)

## Main Question
What are the latest techniques, frameworks, and approaches (as of late March 2026) that could improve interactive testing of AI agents in Claude Code — specifically for evaluating agent reasoning quality, workflow testing, transcript analysis, self-evolution, and self-improvement loops?

## Current Framework Summary
- Two-tier evaluation: Tier 1 (deterministic engine) + Tier 2 (adaptive intelligence)
- Agent Teams with worktree isolation for blind evaluation
- 7-move reasoning decomposition (HYPOTHESIS → SELF_CRITIQUE)
- Dual-Opus evaluator with disagreement detection
- Graph Value Scorer for compliance vs genuine use
- Safe sandbox prompt improvement with regression detection
- JSONL hook observation + evaluation contracts per workflow

## Research Subtopics

### 1. Claude Code Latest Features & Agent Testing (March 2026)
- New Claude Code features released in March 2026
- Agent Teams improvements, new hooks, evaluation APIs
- Claude Code SDK updates for programmatic testing
- Any new isolation or sandboxing capabilities
- MCP server testing capabilities

### 2. Agent Evaluation Frameworks & LLM-as-Judge Advances
- Latest LLM-as-judge techniques and calibration methods
- Multi-evaluator consensus protocols beyond dual-evaluator
- Rubric-based vs rubric-free evaluation approaches
- Pairwise comparison vs absolute scoring advances
- Meta-evaluation (evaluating the evaluators)
- Agent reasoning trace evaluation state-of-the-art

### 3. Self-Improvement & Self-Evolution Techniques
- Constitutional AI / RLAIF advances for self-correction
- Automated prompt optimization (DSPy, TextGrad, etc.) March 2026 state
- Self-play and self-critique architectures for agents
- Curriculum learning for progressively harder test cases
- Automated test generation from failure modes
- Reflection and metacognition patterns in agentic systems

### 4. Workflow Testing & Transcript Analysis
- Structured transcript analysis techniques
- Agent trajectory evaluation methods
- Workflow replay and differential testing
- Behavioral fingerprinting and drift detection
- Multi-agent coordination testing patterns
- Chaos engineering for agentic systems

## Synthesis Plan
- Map findings to current framework gaps
- Prioritize by implementation effort vs impact
- Identify quick wins (< 1 week) vs strategic improvements
- Produce actionable recommendations with references
