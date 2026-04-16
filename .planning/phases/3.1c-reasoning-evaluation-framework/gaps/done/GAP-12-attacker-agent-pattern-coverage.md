# GAP-12: Attacker Agent Current Pattern Coverage Approach

**Created by:** improve-phase
**Source:** P7-IMP-16
**Priority:** MEDIUM
**Status:** resolved
**depends_on:** []

## Question

When the CC LLM attacker agent (vrs-attacker.md) is spawned for evaluation, what pattern context does it receive? The Python AttackerAgent class is irrelevant to the evaluation framework — Phase 3.1c evaluates the CC LLM agent path exclusively. How does the vrs-audit skill prompt instruct CC to pass pattern/bead context to the LLM attacker subagent, and what does the attacker actually see in its Task prompt?

## Reframed By: adversarial review (pass 1)

Original question: "What is the attacker agent's current approach to pattern coverage? Does it iterate through patterns one-by-one, receive a batch?"

Reframe reason: The original research answered about the Python AttackerAgent class and SpawnAttackersHandler, which is a parallel execution path that the evaluation framework does NOT test. Phase 3.1c evaluates the CC LLM agent (vrs-attacker.md prompt), which is spawned via Task tool by Claude Code following the vrs-audit skill instructions. The Python path is prompt-insensitive and cannot inform improvement loop metaprompting. The correct question focuses on the CC orchestration layer.

## Original Question

## Context

P7-IMP-16 asks whether pattern grouping is needed — "group patterns/nodes/sub-agents instead of spawning a sub-agent for each pattern?" The answer depends on understanding what the attacker agent currently does. With 461 patterns (95 B-tier requiring cross-function analysis), per-pattern spawning would be prohibitively expensive. But if the agent already receives patterns in batches, the scaling concern may be overblown.

Affects: Deferred Ideas (pattern grouping experiments), Plan 12 (improvement loop hypothesis).

## Research Approach

- Read the attacker agent prompt/skill: `src/alphaswarm_sol/shipping/agents/` or `.claude/agents/`
- Read the `/vrs-audit` skill to understand how it dispatches work to agents
- Check how patterns are selected and passed to agents during investigation
- Examine the orchestration flow: does it use pattern-based routing or agent-decides-what-to-check?

## Findings (Pass 2 — CC LLM Agent Path Only)

**Confidence: HIGH** — based on reading all shipping agent `.md` files, all orchestration skill `.md` files, evaluation contracts, and use-case scenarios end-to-end.

**Previous findings (Pass 1)** analyzed the Python `AttackerAgent` class and `SpawnAttackersHandler`. Those findings are IRRELEVANT to Phase 3.1c evaluation, which tests the CC LLM agent path exclusively. This pass corrects that.

### 1. What vrs-attacker.md Expects to Receive

The agent prompt (`src/alphaswarm_sol/shipping/agents/vrs-attacker.md`) documents an `AgentContext` dataclass at lines 81-96:

```python
@dataclass
class AgentContext:
    subgraph: nx.DiGraph          # Relevant portion of VKG
    focal_nodes: List[str]        # Key nodes to analyze
    pattern_hints: List[str]      # Matched patterns
    graph_context: Dict[str, Any] # Additional context
    # From bead
    bead_id: str
    severity: str
    code_locations: List[str]
    behavioral_signature: str
```

The agent expects: a subgraph slice, focal nodes, pattern hints (matched pattern IDs), a bead ID, severity, code locations, and a behavioral signature string like `R:bal->X:out->W:bal`.

### 2. What the /vrs-audit Skill Actually Instructs CC to Pass

The audit skill (`src/alphaswarm_sol/shipping/skills/audit.md`) is **extremely vague** about agent spawning. Phase 4 (EXECUTE) says only:

> "Use the orchestration system to spawn verification agents: Attackers - construct exploit paths, Defenders - find guards and mitigations, Verifiers - synthesize verdicts"

It provides NO specific instructions for:
- What context to include in the Task prompt when spawning an attacker
- How to assemble bead context into a Task call
- What fields from the `AgentContext` dataclass to populate
- How many beads to pass per agent invocation
- Whether to use the orch-spawn skill or direct Task tool calls

The skill references `alphaswarm orchestrate start` CLI commands for pool creation and `alphaswarm query "pattern:*"` for pattern detection, but the bridge between "pattern matches found" and "attacker agent spawned with context" is a **prompt gap** — CC must improvise this step.

### 3. What the /vrs-orch-spawn Skill Specifies

The orch-spawn skill (`src/alphaswarm_sol/shipping/skills/orch-spawn.md`) provides the most concrete specification of the context bundle (lines 87-106):

```json
{
  "bead_id": "bd-a3f5b912",
  "investigation_type": "reentrancy",
  "target": {
    "contract": "Vault.sol",
    "function": "withdrawAll",
    "location": "line 45-67"
  },
  "graph_subset": {
    "node_id": "Vault.withdrawAll",
    "properties": { /* relevant properties */ },
    "edges": [ /* relevant edges */ ]
  },
  "patterns": ["reentrancy-classic"],
  "prior_findings": []
}
```

This is the **intended** context bundle format. It includes a `patterns` field with matched pattern IDs. However:
- The orch-spawn skill calls `alphaswarm orch spawn attacker $BEAD_ID --context "$CONTEXT_BUNDLE"` — a CLI command that does NOT currently exist (the CLI has no `orch spawn` subcommand).
- The actual spawning mechanism for CC LLM agents is the `Task` tool (Claude Code's subagent mechanism), not a CLI command.

### 4. The Fundamental Gap: No Concrete Spawning Protocol

There are **three layers of indirection** between "pattern matched" and "attacker receives context":

| Layer | What It Says | Gap |
|-------|-------------|-----|
| **vrs-audit.md** | "Spawn multi-agent verification" | No specifics on HOW to spawn or WHAT to pass |
| **vrs-orch-spawn.md** | Context bundle JSON schema with patterns field | References non-existent CLI command; does not describe Task tool usage |
| **vrs-attacker.md** | Expects `AgentContext` with `pattern_hints`, `subgraph`, `bead_id`, etc. | Describes Python dataclass, not a prompt/JSON format for CC Task tool |
| **vrs-verify.md** | "SpawnAttackersHandler -> SpawnDefendersHandler -> SpawnVerifiersHandler" | References Python handler classes, not CC Task tool calls |

**Result:** When CC follows the `/vrs-audit` skill, it must improvise the spawning step. The skill does not specify:
1. Whether to use Task tool directly or invoke `/vrs-orch-spawn`
2. What to put in the Task prompt for the attacker subagent
3. How to serialize bead/pattern context into a text prompt
4. Whether to pass one bead per agent or batch multiple beads

### 5. What the Attacker Actually Sees in Practice

In the CC LLM path, the attacker subagent is spawned via Claude Code's `Task` tool. The Task tool accepts a `prompt` parameter (free text). The attacker sees:
- Its own agent `.md` file (loaded as system context by Claude Code's agent machinery)
- Whatever prompt text CC writes into the Task call

Since the audit skill provides no template for this prompt text, CC will improvise something like: "Investigate this contract for reentrancy. The bead is bd-xxx. The function is Vault.withdrawAll." The amount of pattern context depends entirely on what CC decides to include, which is **non-deterministic and uncontrolled**.

### 6. How Many Patterns/Beads Would the Attacker See?

This depends on what CC improvises, but the evaluation use-case scenarios (e.g., `UC-ATK-001-find-reentrancy.yaml`) suggest the typical invocation is:
- **One contract** passed to the agent
- **One investigation type** (e.g., "reentrancy")
- **Zero explicit pattern hints** — the agent is expected to discover patterns via its own BSKG queries

The use-case scenario `UC-ATK-001` specifies the command as `/vrs-audit tests/contracts/ReentrancyClassic.sol --agent attacker`, which implies the attacker receives the whole contract scope, not a pre-filtered bead. The expected behavior is that the agent itself runs `alphaswarm build-kg` and `alphaswarm query` to discover vulnerabilities — a **self-directed investigation** rather than a pre-packaged bead dispatch.

### 7. Two Distinct Execution Models Exist (Unreconciled)

| Model | Described In | How Attacker Gets Context |
|-------|-------------|--------------------------|
| **Bead-dispatch model** | vrs-orch-spawn.md, vrs-verify.md, vrs-attacker.md (AgentContext) | Orchestrator assembles context bundle per bead, passes to agent |
| **Self-directed model** | UC-ATK-001 scenario, graph-first-template.md | Agent receives contract scope, runs its own queries, discovers patterns |

These two models are **not reconciled**. The evaluation framework (Phase 3.1c) tests the self-directed model (UC-ATK-001: agent builds graph, queries, discovers). The agent prompt describes the bead-dispatch model (expects AgentContext with pre-populated fields). No skill explicitly bridges these.

### Source Files Examined (Pass 2)

- `src/alphaswarm_sol/shipping/agents/vrs-attacker.md` — LLM agent prompt (full read)
- `src/alphaswarm_sol/shipping/agents/vrs-defender.md` — LLM defender prompt (full read)
- `src/alphaswarm_sol/shipping/agents/vrs-verifier.md` — LLM verifier prompt (full read)
- `src/alphaswarm_sol/shipping/skills/audit.md` — vrs-audit skill (full read)
- `src/alphaswarm_sol/shipping/skills/orch-spawn.md` — spawn skill with context bundle spec (full read)
- `src/alphaswarm_sol/shipping/skills/verify.md` — verify skill (full read)
- `src/alphaswarm_sol/shipping/skills/investigate.md` — investigate skill (full read)
- `src/alphaswarm_sol/shipping/skills/debate.md` — debate skill (full read)
- `src/alphaswarm_sol/shipping/skills/context-pack.md` — PCP builder skill (full read)
- `src/alphaswarm_sol/shipping/skills/bead-create.md` — bead creation skill (full read)
- `src/alphaswarm_sol/testing/evaluation/contracts/agent-vrs-attacker.yaml` — evaluation contract
- `src/alphaswarm_sol/testing/evaluation/contracts/skill-vrs-verify.yaml` — verify eval contract
- `.planning/testing/scenarios/use-cases/agents/UC-ATK-001-find-reentrancy.yaml` — attacker use case
- `docs/reference/graph-first-template.md` — graph-first reasoning protocol

## Recommendation

### Verdict: There is a significant prompt gap between what the attacker agent expects and what the audit skill instructs CC to provide. Two unreconciled execution models exist.

**Confidence: HIGH** that this gap is real and affects evaluation fidelity.

### Prescriptive Actions

**1. Reconcile the two execution models — pick one and make it explicit.**

The bead-dispatch model (orch-spawn context bundle) and the self-directed model (agent queries graph itself) serve different purposes:
- **Self-directed**: Better for initial discovery (audit phase). Agent has autonomy to explore.
- **Bead-dispatch**: Better for verification (verify/debate phase). Agent focuses on a specific finding.

**Decision to record:** The audit skill should use self-directed mode for Phase 4 (EXECUTE) and bead-dispatch mode for Phase 5 (VERIFY/DEBATE). Currently the skill makes no distinction.

**2. Add a concrete spawning template to vrs-audit.md.**

The audit skill Phase 4 needs an explicit Task tool template. Example:

```markdown
### Phase 4: EXECUTE — Spawn Attacker Subagent

Use the Task tool to spawn an attacker agent:

Task(subagent_type="BSKG Attacker", prompt="""
You are investigating {contract_scope} for security vulnerabilities.

**Scope:** {contract files}
**Graph location:** {path to built graph}
**Pattern matches found:** {list of pattern IDs from Phase 3}
**Bead IDs:** {list of bead IDs created in Phase 3}

Follow the graph-first reasoning template. Run BSKG queries before any analysis.
Report findings with evidence packets.
""")
```

Without this template, CC improvises the prompt content non-deterministically, making evaluation results unreliable across runs.

**3. Update vrs-attacker.md to describe BOTH modes.**

Replace the Python `AgentContext` dataclass (which is never instantiated in the CC path) with a description of what the agent will actually receive in its Task prompt:

```markdown
## Input Context

You will be invoked in one of two modes:

### Discovery Mode (from /vrs-audit Phase 4)
You receive: contract scope, graph path, and optional pattern match hints.
Your job: Run BSKG queries, discover vulnerabilities, construct exploit paths.

### Verification Mode (from /vrs-verify or /vrs-debate)
You receive: a specific bead ID, target function, behavioral signature, and pattern context.
Your job: Construct an exploit path for THIS specific finding.
```

**4. For Phase 3.1c evaluation specifically:**

The evaluation use-case scenarios (UC-ATK-001) already test the self-directed model. This is correct for evaluating the attacker's reasoning quality. However, the evaluation contract (`agent-vrs-attacker.yaml`) should document which mode is being tested, so that future bead-dispatch mode tests can be added separately.

Add to the evaluation contract metadata:
```yaml
metadata:
  execution_mode: self-directed  # vs bead-dispatch
```

**5. Pattern coverage question (original P7-IMP-16): Resolved differently than Pass 1 suggested.**

In the CC LLM path, pattern grouping is a **non-issue** because:
- In self-directed mode, the agent queries the graph itself and sees all matches from its queries
- In bead-dispatch mode, the context bundle already includes a `patterns` array per the orch-spawn spec
- The `AdaptiveBatcher` (Python infrastructure) is irrelevant to the CC LLM path

The real issue is not "how many patterns does the agent see?" but "does the agent receive ANY structured pattern context at all, or must it discover everything from scratch?" Answer: currently it must discover from scratch (self-directed mode with no hints), which is expensive but thorough.

### Plans Affected

- **P7-IMP-16 (Deferred Ideas)**: Resolve as "non-issue for CC LLM path; agent self-discovers via graph queries. The Python `AdaptiveBatcher` is irrelevant to this path."
- **Plan 12 (improvement loop)**: The improvement loop should target the Task prompt template (action 2 above) as the primary metaprompting surface. Pattern hints in the prompt are the lever for guiding attacker focus.
- **Evaluation contracts**: Add `execution_mode` metadata to distinguish self-directed vs bead-dispatch test scenarios.
- **vrs-audit.md**: Needs concrete Phase 4 spawning template (highest priority action).
