# Interactive Testing Review: Phase 3.1c.2

**Reviewer:** Claude Opus 4.6
**Date:** 2026-03-02
**Scope:** Interactive testing capabilities, debrief protocol, Agent Teams feedback loops
**Confidence:** HIGH (all source files read, architecture fully traced)

---

## Executive Summary

Phase 3.1c.2 is building the enforcement infrastructure to make evaluation sessions trustworthy. This is necessary and well-executed. But it treats the debrief as an afterthought -- a Stage 9 persistence step bolted onto the end of a pipeline designed for post-hoc transcript analysis. The framework's most powerful capability -- that the subject under test is a *conversational agent you can talk to* -- is almost entirely unexploited.

The current debrief protocol reads like a data collection form. It should read like a cross-examination.

What follows is an analysis of the gap between what exists and what a world-class interactive testing framework would look like, grounded in what is actually implementable with Claude Code's Agent Teams, SendMessage, and hook architecture.

---

## A. Current Interactive Testing Capabilities

| Capability | Status | Plan | Quality |
|---|---|---|---|
| Post-session debrief | Implemented (3.1c-05), wired as Stage 9 (3.1c.2-05) | 3.1c-05, 3.1c.2-05 | **Weak** -- 7 open-ended questions, no structured follow-up |
| Mid-session intervention | Not implemented | None | **Absent** -- no mechanism exists |
| Structured agent interview | Partially implemented | 3.1c-05 (questions) | **Minimal** -- questions asked once, answers accepted at face value |
| Reasoning challenge/probe | Not implemented | None | **Absent** -- no adversarial questioning |
| Fabrication detection via dialogue | Not implemented | None | **Absent** -- relies entirely on JSONL transcript analysis and integrity checks |
| Feedback incorporation | Not implemented | None | **Absent** -- debrief data scores a dimension but does not feed back into the system |
| Multi-agent cross-examination | Not implemented | None | **Absent** -- agents never compare notes |

### What Exists in Detail

**The debrief protocol (`debrief_protocol.py`)** implements a 4-layer cascade:
1. **Layer 1 (SendMessage disk-read):** The CC orchestrator calls SendMessage to the agent during teardown, the agent writes a JSON artifact to disk, and the Python runner reads it. Confidence: 0.9.
2. **Layer 2 (Hook gate):** TeammateIdle/TaskCompleted hooks capture observation data. Confidence: 0.6.
3. **Layer 3 (Transcript analysis):** Keyword-matching heuristic extracts answers from the transcript. Confidence: 0.3.
4. **Layer 4 (Skip):** No debrief data. Confidence: 0.0.

**The 7 debrief questions** are:
1. What was your primary hypothesis?
2. What BSKG queries informed your analysis?
3. What surprised you in the results?
4. What evidence supports your conclusion?
5. What evidence contradicts your conclusion?
6. What would you investigate further?
7. Rate your confidence in the finding (1-5 with justification)

**How debrief data is consumed:** The `ReasoningEvaluator._score_debrief_dimension()` method scores debrief quality based on `confidence * 0.5 + answer_ratio * 0.5`, weighted by the contract's `debrief_layer_weight`. This is a *data completeness* score, not a *reasoning quality* score. A fully fabricated debrief with 7 plausible-sounding answers scores identically to a genuine one.

### The Fundamental Architecture Gap

The current system has a **one-shot, unidirectional** interaction model:

```
Agent runs workflow --> Agent writes debrief artifact --> Runner reads artifact --> Score computed
```

There is no:
- Challenge to the debrief answers
- Follow-up based on what the agent said
- Comparison of debrief claims against the transcript
- Adversarial probing of suspicious answers
- Multi-turn dialogue to reveal reasoning depth

The debrief is treated as a form to fill out, not an interview to conduct.

---

## B. The Debrief Problem

### B.1: Is a Post-Session Debrief Sufficient?

**No. Post-session debrief is necessary but not sufficient.**

A post-session debrief has two structural weaknesses:

1. **Hindsight reconstruction.** After completing the task, the agent has access to its own conclusions. Its "hypothesis" answer will be reverse-engineered from its conclusion, not a genuine account of its initial thinking. This is not fabrication -- it is the natural tendency of any reasoning system to rationalize after the fact.

2. **No opportunity cost measurement.** The debrief cannot reveal what the agent *would have done* if a query returned different results, because the agent only experienced one execution path. Post-hoc reflection cannot access the counterfactual.

**What is needed in addition:**

- **Mid-session checkpoints** (lightweight): At key decision points (after first graph query, before conclusion), send a brief structured question via SendMessage. This captures reasoning *in situ*, before the agent knows the outcome.
- **Counterfactual probes** (post-session): After the debrief, present the agent with a modified scenario ("What if the graph showed no reentrancy edges?") and observe whether its reasoning changes or stays rigidly anchored.

### B.2: Can a Debrief Detect Fabrication?

**Not reliably with the current design. But it can be made much more effective.**

The current debrief asks open-ended questions that a fabricating agent will answer fluently. An agent that invented node IDs will still produce a plausible-sounding answer to "What evidence supports your conclusion?"

Fabrication detection requires **cross-referencing debrief claims against observable ground truth:**

| Detection Method | Current | Proposed |
|---|---|---|
| Compare claimed queries against JSONL transcript | Not done | **Critical** -- "You said BSKG queries informed your analysis. Which specific queries?" then verify against transcript |
| Compare claimed evidence against graph data | Not done | **High value** -- "You cited node X as evidence. What properties does node X have?" then verify against ground truth |
| Ask for specific details that a fabricating agent cannot produce | Not done | **High value** -- "What was the exact return value of your third query?" |
| Ask the agent to predict what a *different* query would return | Not done | **Experimental** -- genuine understanding predicts; memorization fails |
| Detect debrief answers that are suspiciously well-formed | Not done | **Low cost** -- flag answers with perfect JSON structure, zero hedging, or unnaturally precise numeric confidence |

**The key insight:** Fabrication detection is not about catching lies in isolation. It is about creating situations where genuine knowledge produces different responses than surface plausibility. An agent that actually ran graph queries can tell you what surprised it. An agent that fabricated findings cannot identify genuine surprises because it has no genuine expectations to violate.

### B.3: Debrief Question Taxonomy

The current 7 questions are all in the "reflective self-report" category. A diagnostic debrief needs questions across multiple categories:

**Category 1: Process Verification (Did you actually do what you claim?)**
- "List the exact CLI commands you executed, in order."
- "What was the first graph query you tried, and what did it return?"
- "How many nodes were in the graph you built?"

These have ground-truth answers (from JSONL transcript and graph stats). Discrepancies between debrief answers and transcript evidence are fabrication signals.

**Category 2: Reasoning Reconstruction (How did you think?)**
- "What was your initial hypothesis before running any queries?"
- "At what point did you change your approach, and why?"
- "Which query result most influenced your conclusion?"

These probe the reasoning chain. Shallow thinkers answer generically. Deep thinkers cite specific turning points.

**Category 3: Epistemic Calibration (How much do you know you don't know?)**
- "What are the top 3 things you are least certain about?"
- "If your conclusion is wrong, what is the most likely alternative?"
- "What additional information would change your conclusion?"

These measure metacognitive quality. Over-confident agents produce narrow uncertainty ranges. Well-calibrated agents identify genuine unknowns.

**Category 4: Adversarial Challenge (Can your reasoning withstand pressure?)**
- "A colleague argues that the pattern you found is a false positive because [specific reason]. How do you respond?"
- "The graph shows [contradictory fact]. Does this change your conclusion?"
- "Another auditor found no vulnerabilities in this contract. Why might they be right?"

These test reasoning robustness. Brittle conclusions collapse under challenge. Genuine findings are defended with specific evidence.

**Category 5: Counterfactual Reasoning (Can you reason beyond what you observed?)**
- "If the contract had an access control modifier on that function, would your finding still apply?"
- "What would you expect the graph to look like for a *safe* version of this contract?"
- "If you ran your analysis again from scratch, would you take the same approach?"

These test depth of understanding. An agent that genuinely understands the vulnerability can reason about variations. An agent that pattern-matched cannot.

### B.4: Machine-Consumable Debrief Responses

The current `DebriefResponse` model stores answers as `list[str]` -- free-form text. This is almost impossible to score programmatically beyond "is it non-empty?"

**Proposed structured format:**

```python
class StructuredDebriefAnswer(BaseModel):
    """A single debrief answer with structured metadata."""
    question_id: str                    # e.g., "pv_01" (process verification #1)
    category: str                       # "process_verification" | "reasoning" | "epistemic" | "adversarial" | "counterfactual"
    answer_text: str                    # Free-form answer
    confidence: float                   # Agent's self-rated confidence (0-1)
    cited_evidence: list[str]           # Specific node IDs, query results, line numbers
    verifiable_claims: list[str]        # Claims that CAN be checked against ground truth

class StructuredDebrief(BaseModel):
    """Full structured debrief with cross-referencing support."""
    agent_name: str
    session_id: str
    answers: list[StructuredDebriefAnswer]

    # Verification metadata
    transcript_hash: str                # SHA256 of the JSONL transcript (tamper detection)
    claimed_query_count: int            # Agent's claim of how many queries it ran
    actual_query_count: int | None      # Filled by verifier from transcript (None if not yet verified)
    consistency_score: float | None     # Filled by cross-reference engine (None if not yet scored)
```

The `verifiable_claims` field is the key innovation: the agent is asked to make specific, testable claims. These are then automatically checked against the JSONL transcript and ground truth graph. The ratio of verified-to-unverified claims becomes a powerful fabrication signal.

### B.5: Adversarial vs. Collaborative Debrief

**Both, in sequence.**

The debrief should have two phases:

**Phase 1: Collaborative (first).** Ask open-ended reflective questions. Let the agent explain its reasoning without pressure. This produces the baseline self-report and reveals the agent's natural reasoning style.

**Phase 2: Adversarial (second).** Challenge specific claims from Phase 1. Present contradictory evidence. Ask the agent to defend its position. This tests reasoning robustness and reveals whether the agent's understanding is shallow or deep.

The order matters. Starting adversarial makes agents defensive and produces lower-quality Phase 1 answers. Starting collaborative establishes a baseline that Phase 2 can probe.

---

## C. Interactive Feedback Loop Design

### C.1: The Interaction Model Within Agent Teams

Claude Code's Agent Teams provide three interaction primitives:
1. **SendMessage** -- Orchestrator sends a message to a named teammate
2. **TaskList** -- Shared task list visible to all team members
3. **Tool observation** -- Hooks capture tool usage events

The current architecture uses SendMessage exactly once: at teardown, to ask the agent to write a debrief artifact. This is a fraction of its potential.

**Proposed multi-turn evaluation dialogue protocol:**

```
Phase 0: Agent completes workflow (existing)
  |
Phase 1: Collaborative Debrief (2-3 messages)
  |  Orchestrator -> Agent: "Please reflect on your analysis. [7 questions]"
  |  Agent -> Artifact: writes debrief.json
  |  Orchestrator reads debrief.json
  |
Phase 2: Verification (1-2 messages)
  |  Orchestrator cross-references debrief claims against transcript
  |  Identifies discrepancies and unverified claims
  |  Orchestrator -> Agent: "You said you ran 4 queries. The transcript shows 2.
  |                          Can you explain the discrepancy?"
  |  Agent -> Artifact: writes clarification.json
  |
Phase 3: Adversarial Challenge (1-2 messages)
  |  Orchestrator -> Agent: "A colleague argues [specific counterargument].
  |                          How do you respond?"
  |  Agent -> Artifact: writes defense.json
  |
Phase 4: Counterfactual (1 message, optional)
  |  Orchestrator -> Agent: "If the contract had [modification], would your
  |                          finding still apply? Explain."
  |  Agent -> Artifact: writes counterfactual.json
```

Total SendMessage calls: 4-6 per evaluation session. Each produces a structured artifact. The full set is scored as an **interactive debrief package**.

### C.2: Challenge-Response-Verdict Protocol

```
┌─────────────┐     SendMessage      ┌──────────────┐
│ Orchestrator │ ──────────────────> │    Agent      │
│ (Evaluator)  │                     │ (Subject)     │
│              │ <────────────────── │              │
│              │   writes artifact   │              │
│              │                     │              │
│  Cross-ref   │                     │              │
│  against     │     SendMessage     │              │
│  transcript  │ ──────────────────> │              │
│              │   "You claimed X,   │              │
│              │    but transcript   │              │
│              │    shows Y"         │              │
│              │                     │              │
│              │ <────────────────── │              │
│              │   defense artifact  │              │
│              │                     │              │
│  Score the   │                     │              │
│  defense     │                     │              │
│  quality     │                     │              │
└─────────────┘                     └──────────────┘
```

**Scoring the defense:**

| Defense Quality | Score | Indicator |
|---|---|---|
| Acknowledges error with specifics | 90-100 | "I was wrong about the query count. I actually ran 2 queries, not 4. My third query attempt failed." |
| Provides additional context | 70-89 | "The transcript shows 2 CLI queries, but I also inferred information from the graph structure visible in the build output." |
| Deflects without addressing | 30-69 | "I believe my analysis was thorough regardless of the exact query count." |
| Doubles down on falsehood | 0-29 | "I am confident I ran 4 queries. The transcript may be incomplete." |

This scoring is itself suitable for LLM evaluation (the Dual-Opus evaluator from the existing framework can assess defense quality).

### C.3: Preventing the Evaluator from Leading the Witness

This is a critical concern. If the orchestrator's challenge messages contain the "right answer," the agent will simply agree. Three safeguards:

1. **Challenge framing rule:** Never reveal the expected answer in the challenge. Frame challenges as opposing viewpoints, not corrections.

   Bad: "Your finding is wrong because the contract has a reentrancy guard."
   Good: "A colleague found no reentrancy vulnerability in this contract. What specific evidence makes you disagree?"

2. **Counterfactual structure:** When probing, present a hypothetical modification, not the actual truth.

   Bad: "The graph shows no reentrancy edges. Why did you claim reentrancy?"
   Good: "What would the graph look like if there were no reentrancy vulnerability?"

3. **Blind challenges:** For some challenges, use a randomly selected counterargument from a bank, not one derived from the agent's specific answers. This prevents the challenge from containing implicit signal about the correct answer.

---

## D. Creative Proposals for World-Class Interactive Testing

### Proposal 1: The Socratic Probe Engine

**What it does:** Instead of asking direct questions, the evaluator asks questions that reveal reasoning gaps without giving away answers. The questions are generated dynamically based on the agent's claims, not from a static list.

**Why it matters:** Static debrief questions can be "gamed" (or at least answered superficially) because the agent knows what kind of answer is expected. Socratic probes are unpredictable and require genuine understanding to answer well.

**Example:**

Agent claims: "I found a reentrancy vulnerability in the `withdraw()` function."

Socratic probe sequence:
1. "What would happen if `withdraw()` used a checks-effects-interactions pattern?" (Tests whether the agent understands the fix, not just the bug)
2. "Which other functions in the contract could be affected by the same pattern?" (Tests whether the agent can generalize)
3. "If you were the contract author, how would you argue this is not exploitable?" (Tests whether the agent can steelman the opposition)

**How to prototype in Plan 06 retry:**
- After the existing Stage 9 debrief, add a "Stage 10: Socratic probe" phase
- Use a single SendMessage with 3 dynamically generated questions based on the agent's findings
- Compare probe answers against the debrief answers for consistency
- Score: consistency between findings, debrief, and probe answers

**Data generated:** Probe question-answer pairs, consistency scores, reasoning gap identification. Feeds into 3.1c.3's evaluator self-improvement and metaprompting feedback.

**Feasibility:** HIGH. SendMessage already works. Question generation is a prompt engineering task (use a small Task() subagent to generate probe questions from the agent's findings). No new infrastructure needed.

### Proposal 2: Confidence Calibration Tournament

**What it does:** Asks agents to rate their confidence on each finding, then compares confidence ratings against actual correctness (from ground truth). Over multiple evaluation sessions, builds a calibration curve for each agent type.

**Why it matters:** The most dangerous agent is one that is confidently wrong. A well-calibrated agent says "high confidence" when it is right and "low confidence" when it is uncertain. A poorly calibrated agent says "high confidence" always (or never). Calibration data is the single most important signal for downstream trust decisions.

**Implementation:**

```python
class CalibrationEntry(BaseModel):
    """Single calibration data point."""
    agent_type: str
    contract_id: str
    finding_id: str
    agent_confidence: float      # Agent's self-rated confidence (0-1)
    actual_correctness: float    # From ground truth (0=false positive, 1=true positive)
    reasoning_quality: float     # From LLM evaluator (0-1)

class CalibrationCurve(BaseModel):
    """Calibration over multiple entries."""
    agent_type: str
    entries: list[CalibrationEntry]

    @property
    def expected_calibration_error(self) -> float:
        """ECE: mean |confidence - accuracy| across bins."""
        bins = self._bin_entries(n_bins=5)
        return sum(abs(b.mean_confidence - b.mean_accuracy) * b.count
                   for b in bins) / max(len(self.entries), 1)
```

**How to prototype in Plan 06 retry:**
- Debrief question 7 already asks for confidence (1-5). Parse this as a float.
- Compare against ground truth (cal-01 through cal-04 have known vulnerabilities).
- Store as CalibrationEntry in `.vrs/observations/plan12-retry/calibration.json`.
- After 4 agents, compute preliminary ECE.

**Data generated:** Per-agent-type calibration curves, ECE scores, over-confidence and under-confidence patterns. Feeds into 3.1c.3's adaptive tier management (agents with high ECE get more adversarial probing).

**Feasibility:** HIGH. No new SendMessage calls needed -- the data is already captured in the existing debrief. Just needs a new analysis step and a comparison against ground truth.

### Proposal 3: Blind Comparison Protocol

**What it does:** Two agents (same type or different types) analyze the same contract independently, with full isolation. After both complete, their findings, reasoning chains, and debrief answers are compared by a third evaluator agent. Discrepancies reveal which agent reasoned more deeply.

**Why it matters:** A single agent's output is hard to evaluate in isolation -- you need a reference point. Another agent's output on the same input is the most informative reference point because it holds the task constant and varies only the reasoning.

**Implementation within Agent Teams:**

```
Orchestrator spawns Team with:
  - Agent A (attacker, worktree-isolated, contract X)
  - Agent B (attacker, worktree-isolated, contract X)
  - Evaluator C (after A and B complete)

After both complete:
  Evaluator C receives:
    - Agent A's findings + debrief
    - Agent B's findings + debrief
    - Ground truth (if available)

  Evaluator C scores:
    - Agreement: Do they find the same vulnerabilities?
    - Reasoning divergence: WHERE do their reasoning chains differ?
    - Quality differential: Which reasoning chain is more thorough?
```

**How to prototype in Plan 06 retry:**
- Plan 06 already spawns 3-5 agents across 4 contracts.
- Assign 2 agents to the same contract (e.g., two attackers on cal-01).
- After both complete, compute finding overlap and reasoning divergence.
- No Evaluator C needed for prototype -- use programmatic comparison.

**Data generated:** Inter-agent agreement rates, reasoning divergence profiles, finding overlap matrices. Feeds into 3.1c.3's behavioral fingerprinting (do agents converge on the same reasoning patterns over time?).

**Feasibility:** HIGH. Plan 06 already has the infrastructure. Just need to intentionally double-assign one contract.

### Proposal 4: Adversarial Devil's Advocate Round

**What it does:** After the agent completes its analysis and debrief, a *different* agent (the "defender" role) is shown the attacker's findings and asked to argue against them. The attacker then sees the defender's objections and must respond. This is a structured 2-round debate.

**Why it matters:** The multi-agent debate architecture (`vrs-attacker`, `vrs-defender`, `vrs-verifier`) is the project's core value proposition, but it has never been tested under evaluation conditions. This proposal turns the product's own debate mechanism into a testing mechanism.

**Implementation:**

```
Round 1: Attacker produces findings + debrief
Round 2: Defender receives findings, produces counterarguments
Round 3: Attacker receives counterarguments, produces rebuttal
Round 4: Verifier scores the debate quality

Scoring:
- Did the attacker modify any claims after seeing counterarguments? (intellectual honesty)
- Did the defender identify real weaknesses in the reasoning? (defensive quality)
- Did the attacker's rebuttal address the specific objections? (argumentative rigor)
```

**How to prototype in Plan 06 retry:**
- Spawn an attacker on cal-01 (existing).
- After attacker completes, spawn a defender with the attacker's findings.
- Use SendMessage to send the defender's counterarguments to the attacker.
- Compare attacker's original findings with post-debate findings.

**Data generated:** Debate transcripts, claim modification rates, counterargument quality scores. Feeds into 3.1c.3's compositional stress testing and the production /vrs-debate skill.

**Feasibility:** MEDIUM. Requires spawning a second agent after the first completes, which means sequential execution within Plan 06. The main risk is token budget -- a full debate round could consume 30k+ tokens per contract. Recommend testing on a single contract (cal-01) first.

### Proposal 5: Reasoning Replay with Perturbation

**What it does:** After the agent completes its analysis, the system modifies the graph slightly (e.g., removes one edge, adds a false node) and asks the agent to re-analyze. The delta between the original and perturbed analysis reveals how sensitive the agent's reasoning is to specific graph features.

**Why it matters:** This is the interactive testing equivalent of ablation studies in ML. If removing a single edge causes the agent to completely change its conclusion, that edge was load-bearing for the reasoning. If removing an edge changes nothing, the agent was not actually using graph data (a fabrication signal). This directly addresses the "checkbox compliance" problem identified in the testing philosophy.

**Implementation:**

```python
class PerturbationResult(BaseModel):
    """Result of a single perturbation experiment."""
    original_finding: str
    perturbation_type: str  # "remove_edge" | "add_node" | "rename_function"
    perturbation_detail: str  # What was changed
    post_perturbation_finding: str
    finding_changed: bool
    reasoning_chain_changed: bool
    sensitivity_score: float  # 0 = no change, 1 = complete reversal
```

**How to prototype in Plan 06 retry:**
- After an agent completes analysis of cal-01 (ReentrancyClassic.sol), modify the contract slightly (e.g., add a reentrancy guard) and rebuild the graph.
- Ask the agent (via SendMessage): "The contract has been updated. Re-analyze using the new graph at [path]. What changed in your assessment?"
- Compare the delta between original and post-perturbation findings.

**Data generated:** Perturbation sensitivity profiles per agent type, load-bearing edge identification, graph-dependency scores. Feeds into 3.1c.3's graph value scorer calibration (if removing edges does not change findings, GVS is measuring the wrong thing).

**Feasibility:** MEDIUM-LOW for Plan 06, HIGH for 3.1c.3. The main challenge is creating the perturbed graph within the evaluation session. For Plan 06 prototype, use a pre-built perturbed graph stored alongside the ground truth. For 3.1c.3, build automated perturbation generation.

---

## E. What Makes This Framework Unique

### The Interactive Advantage

Most AI evaluation frameworks are **batch-and-score**: run the model, collect outputs, compute metrics. They cannot ask the model "why did you do that?" because the model is not running anymore. They evaluate the output, not the reasoning.

This framework has a structural advantage that no other testing system in AI security possesses:

1. **The subject is a live conversational agent.** It can be questioned, challenged, and asked to explain itself during and after the evaluation. This is not possible with static analysis tools, LLM-as-a-judge benchmarks, or traditional unit tests.

2. **The subject operates through observable tool calls.** Every graph query, CLI invocation, and file read is recorded in JSONL. This creates an objective behavioral record that can be cross-referenced against the agent's self-report.

3. **The subject exists within a multi-agent system.** Agents can evaluate each other. The attacker's findings can be challenged by the defender, and the quality of that debate can be assessed by the verifier. This creates a natural "peer review" testing mechanism that is part of the product architecture.

4. **The evaluation environment is programmable.** The graph can be modified, contracts can be swapped, context can be controlled. Unlike benchmarking against a fixed dataset, this framework can create bespoke evaluation scenarios that target specific reasoning weaknesses.

### How 3.1c.2 Should Be Designed to Maximize This Advantage

The current 3.1c.2 design is focused on **enforcement** (preventing fabrication) and **verification** (checking that tools were used). These are necessary foundations. But the design should also lay groundwork for **interactive evaluation** -- the unique capability that no competitor has.

Specific recommendations:

**1. Stage 9 should not just persist the debrief. It should be a multi-turn interaction stage.**

The current Plan 05 wires Stage 9 as a persistence step: read the debrief artifact, save it to disk, record metadata. This is a missed opportunity. Stage 9 should be an **interactive evaluation stage** with at least 2 turns:

- Turn 1: Collaborative debrief (existing 7 questions)
- Turn 2: Verification probe (cross-reference debrief claims against transcript)

The verification probe can be implemented as a second SendMessage call. The message content is generated by comparing the debrief's `claimed_queries` against the transcript's actual queries (via `TranscriptParser.get_bskg_queries()`).

**2. Plan 06 should include at least one blind comparison.**

The calibration retry already spawns 3-5 agents across 4 contracts. Assigning 2 agents to the same contract costs almost nothing and produces the blind comparison data described in Proposal 3. This data is invaluable for 3.1c.3's behavioral fingerprinting.

**3. The debrief artifact schema should be extended with verifiable claims.**

Adding a `verifiable_claims` field to `DebriefResponse` is a backward-compatible change. The existing pipeline ignores fields it does not use. But 3.1c.3's cross-reference engine will need this data. Adding it now, even if not consumed until later, means the Plan 06 retry produces immediately useful data for the next phase.

**4. Confidence calibration should start with Plan 06.**

Debrief question 7 already asks for confidence. Comparing this against ground truth for the 4 calibration contracts produces the first 4 data points on the calibration curve. This is trivial to implement and produces the foundation for 3.1c.3's adaptive tier management.

---

## F. Detailed Recommendations for 3.1c.2 Plan 06 Retry

These are minimal, implementable changes that maximize the interactive testing signal from the Plan 06 retry without requiring new infrastructure.

### F.1: Add a Verification Turn to the Debrief

After receiving the debrief artifact (existing Layer 1), add a single SendMessage:

```
"Thank you for your analysis. I have a few follow-up questions:

1. You mentioned [specific query from debrief answer #2]. The session log
   shows [actual query count] queries. Can you list them?
2. Your confidence was [X/5]. What specific evidence would increase it to 5?
3. What is the single strongest counterargument against your finding?"
```

This adds ~30 seconds to the evaluation and produces a verification artifact (`verification.json`) alongside `debrief.json`. The verification artifact captures the agent's response to being challenged on specifics.

### F.2: Double-Assign One Contract

Assign 2 agents (both attackers, or 1 attacker + 1 secure-reviewer) to cal-01 (ReentrancyClassic.sol). After both complete:

```python
# Programmatic comparison (no extra agents needed)
findings_a = load_observation("plan12-retry/cal-01-agent-a.json")
findings_b = load_observation("plan12-retry/cal-01-agent-b.json")

overlap = compute_finding_overlap(findings_a, findings_b)
divergence = compute_reasoning_divergence(
    debrief_a=load_debrief("plan12-retry/agent-a-debrief.json"),
    debrief_b=load_debrief("plan12-retry/agent-b-debrief.json"),
)
```

### F.3: Parse Confidence for Calibration

Add a post-processing step after debrief collection:

```python
def extract_calibration_entry(debrief: DebriefResponse, ground_truth: dict) -> CalibrationEntry:
    """Extract confidence calibration from debrief question 7."""
    confidence_answer = debrief.answers[6]  # "Rate your confidence (1-5)"
    agent_confidence = parse_confidence(confidence_answer) / 5.0  # Normalize to 0-1

    # Compare against ground truth
    actual_correctness = compute_correctness(debrief.agent_name, ground_truth)

    return CalibrationEntry(
        agent_type=debrief.agent_type,
        agent_confidence=agent_confidence,
        actual_correctness=actual_correctness,
    )
```

### F.4: Extended Debrief Question Set for Plan 06

Replace the 7 generic debrief questions with a targeted set for the calibration retry:

```python
CALIBRATION_DEBRIEF_QUESTIONS = [
    # Process Verification (cross-referenceable)
    "List every CLI command you executed, in the order you executed them.",
    "How many nodes and edges were in the graph you analyzed?",

    # Reasoning Reconstruction
    "What was your initial hypothesis before running any queries?",
    "Which specific query result most influenced your final conclusion?",

    # Epistemic Calibration
    "What are you least certain about in your findings?",
    "If your primary finding is a false positive, what is the most likely explanation?",

    # Confidence
    "Rate your confidence in each finding (1-5) with a one-sentence justification.",
]
```

These questions are designed to produce machine-verifiable answers (questions 1-2 can be checked against the transcript) and epistemic calibration data (questions 5-7).

---

## G. Architecture for 3.1c.3 and Beyond

The following architectural elements should be planned now but implemented in 3.1c.3 (Evaluation Intelligence Bootstrap):

### G.1: Cross-Reference Engine

```python
class CrossReferenceEngine:
    """Compares debrief claims against observable evidence."""

    def cross_reference(
        self,
        debrief: StructuredDebrief,
        transcript: TranscriptParser,
        ground_truth: dict,
    ) -> CrossReferenceReport:
        """
        Returns:
            - verified_claims: Claims that match transcript/ground truth
            - unverified_claims: Claims that cannot be verified
            - contradicted_claims: Claims that conflict with evidence
            - consistency_score: verified / (verified + contradicted)
        """
```

### G.2: Adaptive Probe Generator

```python
class AdaptiveProbeGenerator:
    """Generates follow-up questions based on debrief content."""

    def generate_probes(
        self,
        debrief: StructuredDebrief,
        cross_ref: CrossReferenceReport,
    ) -> list[ProbeQuestion]:
        """
        Generate probes targeting:
        - Contradicted claims (highest priority)
        - Unverified claims (medium priority)
        - Suspiciously confident claims (calibration probes)
        """
```

### G.3: Interactive Evaluation Session Manager

```python
class InteractiveEvaluationSession:
    """Manages a multi-turn evaluation dialogue with an agent."""

    async def run(self, agent_name: str, team_name: str) -> InteractiveDebriefPackage:
        """
        Phase 1: Send collaborative debrief questions
        Phase 2: Cross-reference answers against transcript
        Phase 3: Send verification probes
        Phase 4: Send adversarial challenges (if warranted)
        Phase 5: Compile interactive debrief package
        """
```

---

## H. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Multi-turn debrief increases token cost significantly | HIGH | MEDIUM | Cap at 3 turns. Use SHORT_DEBRIEF_QUESTIONS for verification turns. Budget ~4k tokens per turn. |
| Agents become "debrief-optimized" (learn to produce good debriefs without good reasoning) | MEDIUM | HIGH | Rotate question sets. Include process verification questions that are ground-truth-checkable. Use blind comparison to detect gaming. |
| Interactive evaluation extends session duration beyond practical limits | MEDIUM | MEDIUM | Make Phases 2-4 optional. Run Phase 1 always, Phases 2-4 only for Core/Important tier evaluations. |
| Challenge messages leak information about expected answers | MEDIUM | HIGH | Follow the "never reveal the answer" framing rule. Use blind challenges from a bank. Have an independent agent generate challenge questions. |
| Debrief quality varies wildly across agent types | HIGH | LOW | This is data, not a bug. Track debrief quality per agent type. Use calibration curves to weight debrief signal appropriately. |

---

## I. Summary and Priority Ranking

### Immediate (Plan 06 Retry -- Zero New Infrastructure)

1. **Parse confidence for calibration.** Already captured in debrief question 7. Just add a comparison against ground truth. Effort: 1 hour.
2. **Double-assign one contract.** Trivial change to agent spawning. Effort: 15 minutes.
3. **Extend debrief questions with process verification.** Replace generic questions with ground-truth-checkable ones. Effort: 30 minutes.

### Short-Term (3.1c.2 Plan 05 Modification -- Minimal Infrastructure)

4. **Add verification turn to Stage 9.** One additional SendMessage after debrief collection. Cross-references claims against transcript. Effort: 4 hours.
5. **Add `verifiable_claims` to DebriefResponse.** Backward-compatible schema extension. Effort: 1 hour.

### Medium-Term (3.1c.3 -- New Components)

6. **Cross-Reference Engine.** Automated comparison of debrief claims against transcript and ground truth.
7. **Adaptive Probe Generator.** Dynamic follow-up question generation based on debrief content.
8. **Calibration Curve Tracker.** Persistent calibration data across evaluation sessions.
9. **Blind Comparison Protocol.** Systematic double-assignment with programmatic divergence analysis.

### Long-Term (3.1c.3+ -- Full Interactive Framework)

10. **Interactive Evaluation Session Manager.** Multi-turn dialogue protocol with structured phases.
11. **Adversarial Devil's Advocate Round.** Attacker-defender debate under evaluation conditions.
12. **Reasoning Replay with Perturbation.** Graph modification and re-analysis for sensitivity testing.
13. **Socratic Probe Engine.** Dynamically generated questions that reveal reasoning gaps.

---

## J. Conclusion

Phase 3.1c.2 is building the right enforcement foundation. The delegate_guard, CLIAttemptState, ground truth, auto-reject pipeline, and debrief wiring are all necessary and well-designed. But the debrief -- the one component that exploits the interactive advantage -- is being treated as a data persistence step rather than an evaluation mechanism.

The testing philosophy states: *"The most dangerous failure is a workflow that 'works' but reasons badly."* The current debrief can detect missing data. It cannot detect bad reasoning presented confidently. Only interactive evaluation -- challenging agents on their claims, probing their reasoning with follow-up questions, comparing their self-reports against observable behavior -- can reliably distinguish genuine understanding from plausible confabulation.

The good news: the infrastructure to support interactive evaluation is already 80% built. SendMessage works. Agent Teams work. The 4-layer debrief cascade works. The transcript parser works. The integrity validator works. What is missing is not infrastructure but *protocol* -- the decision to use these tools for multi-turn evaluation dialogue rather than one-shot data collection.

The Plan 06 retry is the natural prototype: it already spawns agents, collects debriefs, and validates integrity. Adding a verification turn, a blind comparison, and confidence calibration requires minimal new code and produces data that directly feeds 3.1c.3. This is the highest-leverage opportunity in the current phase plan.

---

*Review complete. All recommendations grounded in existing codebase capabilities and Claude Code's Agent Teams architecture.*
