# T1: Graph Reality Assessment

## Executive Summary

The BSKG graph builder is **real, substantial engineering** that extracts genuinely useful security properties from Solidity code (150+ properties per function, 20 semantic operations, behavioral signatures, call confidence scoring). However, there is **zero evidence that agents actually use graph queries in real audits**. The graph-first mandate exists only as documentation — no transcripts, no logs, no audit artifacts demonstrate the query → evidence → conclusion pipeline working end-to-end. The ablation study that would prove graph value was **designed but never executed**.

**Verdict: PARTIALLY WORKING — Builder is solid, consumption is theoretical.**

## Evidence Found

### Graph Construction

**Status: GENUINELY WORKING (high confidence)**

The builder (`src/alphaswarm_sol/kg/builder/core.py`) is a well-engineered modular system:

- **VKGBuilder** orchestrates 6 processors: ContractProcessor, StateVarProcessor, FunctionProcessor, CallTracker, ProxyResolver, CompletenessReporter (`core.py:45-191`)
- **FunctionProcessor** computes **150+ security properties** per function node, organized into 15+ groups (`functions.py:50-249`):
  - Basic identity (8 props)
  - Access control (18 props): `has_access_gate`, `has_only_owner`, `has_reentrancy_guard`, etc.
  - State operations (14 props): `state_write_before_external_call`, `writes_privileged_state`, etc.
  - External calls (20 props): `uses_delegatecall`, `call_target_user_controlled`, etc.
  - User input (18 props): parameter type classification
  - Context variables (12 props): `uses_tx_origin`, `uses_msg_value`
  - Token operations (24 props): ERC20/721/1155/777/4626 detection
  - Oracle & price (22 props): Chainlink validation completeness
  - Deadline & slippage (12 props)
  - Loop analysis (12+ props)

- **Semantic Operations** (`kg/operations.py:28-64`): 20 well-defined operations (TRANSFERS_VALUE_OUT, READS_USER_BALANCE, CHECKS_PERMISSION, etc.) with CFG-order tracking and behavioral signatures (e.g., `R:bal→X:out→W:bal` for CEI violations)

- **Operation detection** is legitimate: `detect_transfers_value_out()` walks Slither IR nodes, checking Transfer/Send/LowLevelCall/HighLevelCall types (`operations.py:204-249`). Not name-based; actually reads IR.

- **Call confidence scoring** (HIGH/MEDIUM/LOW) for target resolution
- **Proxy pattern detection** (Transparent, UUPS, Diamond, Beacon, Minimal)
- **Rich edges** and **meta edges** for higher-order relationships
- **Completeness reporting** tracks build quality metrics

**Assessment: The builder produces genuinely rich structured data that goes beyond raw Slither AST. It adds semantic operations, behavioral signatures, operation ordering, call confidence, proxy resolution, and cross-function reentrancy surface detection. This is real value.**

### Query System

**Status: WORKING CODE, UNTESTED IN PRACTICE (medium confidence)**

The query system has multiple layers:
- **VQL grammar** (`queries/vql_grammar.py`): Custom query language
- **QueryExecutor** (`queries/executor.py`): Executes plans against graphs, supports label overlays, caching, pattern matching, semgrep integration
- **VQL 2.0** (experimental): Newer parser with `MATCH`, `FLOW FROM`, `WITH` syntax (`cli/main.py:580-581`)
- **Pattern engine**: PatternStore, PatternDefinition with Conditions, EdgeRequirements, PathRequirements
- **CLI command**: `uv run alphaswarm query "..."` is implemented (`cli/main.py:562-572`)

The query CLI loads from `.vrs/graphs/graph.json`, supports compact output, explanations, intent display, and validation mode.

**Concern: The query system is complex and feature-rich, but there's no evidence it has been exercised in a real audit workflow. Tests validate query execution against test contracts (see below), but not agent-driven query→analysis→verdict flows.**

### Agent Graph Usage

**Status: THEORETICAL ONLY (high confidence in this assessment)**

**What the agents SAY they do:**

- `vrs-attacker.md` (line 31): "**Graph-first analysis** - Use BSKG queries and semantic operations, NOT manual code reading"
- `vrs-attacker/AGENT.md` (lines 37-58): Detailed "Required Investigation Steps" with BSKG queries, evidence packets, unknowns, conclusions
- `vrs-defender.md`: References `has_access_gate`, `has_reentrancy_guard`, `state_write_before_external_call` properties
- `vrs-verifier.md`: Synthesizes attacker/defender evidence packets
- `graph-first-template.md`: Elaborate 373-line template mandating query-before-analysis

**What the agents CAN do:**

- Attacker/defender/verifier agents have `Bash(uv run python*)` tool access — **NOT** `Bash(uv run alphaswarm*)`. Only `vrs-real-world-auditor` has `Bash(uv run alphaswarm*)`.
- This means the core debate agents **cannot run `alphaswarm query`** commands. They can only run Python scripts.
- The agents receive an `AgentContext` dataclass with a `subgraph: nx.DiGraph` — this implies the orchestrator is supposed to pre-extract a subgraph and pass it in. But there's no evidence this pipeline works.

**What actually happens:**

- **Zero audit transcripts exist.** `.vrs/` contains only benchmark corpora (Code4rena contracts) and test artifacts. No `.vrs/testing/runs/` directory. No `transcript.txt` files. No `report.json` files.
- Grep for "transcript", "audit_log", "run_log" in `.vrs/` returns **zero results**.
- The ablation study (`IMP-G1-ablation.yaml`) was **designed** with detailed claude-code-controller commands but **never executed** — no results directory exists.

**Critical gap: The `AgentContext` dataclass includes `subgraph: nx.DiGraph` which suggests a pre-extraction pipeline, but agents only have `Bash(uv run python*)` tools. The connection between "build graph → extract subgraph → pass to agent → agent queries → agent outputs evidence" is entirely theoretical. No code wires this together end-to-end.**

### Test Coverage

**Status: TESTS VALIDATE CONSTRUCTION AND QUERY MECHANICS, NOT DETECTION VALUE (high confidence)**

Graph-related tests: **223 test functions across 8 files**

| File | Tests | What It Tests |
|------|-------|---------------|
| `test_subgraph.py` (29) | Schema, extraction, serialization | SubGraph data structures work correctly |
| `test_ppr_subgraph.py` (37) | PPR scoring algorithm | Personalized PageRank computation |
| `test_graph_slicer.py` (34) | Graph slicing | Extracting relevant subsets |
| `test_subgraph_omissions.py` (29) | Omission tracking | What gets cut from subgraphs |
| `test_queries_call_graph.py` (5) | Cross-contract path queries | **GENUINE: Tests real graphs from test contracts** |
| `test_cache_graph_queries.py` (30) | Query caching | Cache hit/miss/TTL mechanics |
| `test_causal_exploitation_graph.py` (43) | CEG construction | Causal chain data structures |
| `test_langgraph.py` (16) | LangGraph adapter | Integration adapter correctness |

**Honest breakdown:**

- **~5-10% test actual detection value**: `test_queries_call_graph.py` tests like `test_cross_contract_chain_path` actually build a graph from `ValueMovementProtocolChain.sol`, run a path query, and verify it finds `deposit(uint256)` but not `depositSafe(uint256)`. This is genuine detection testing.

- **~20% test operation sequencing**: `test_sequencing.py` validates that operation ordering pairs are computed correctly from semantic operations, and that `detect_vulnerable_reentrancy_pattern` works. These are real security-relevant unit tests.

- **~70% test data structure mechanics**: Most tests verify schemas serialize/deserialize, caches work, subgraph extraction produces correct structures, PPR scores compute correctly, etc. Valuable for code quality but says nothing about detection value.

- **0% test agent-driven detection**: No test exercises the flow "agent receives context → runs graph query → produces evidence-grounded verdict."

### Graph vs Raw Code

**Status: NO EMPIRICAL EVIDENCE (high confidence in absence)**

**Arguments FOR graph value (theoretical):**
1. Semantic operations abstract away naming — `TRANSFERS_VALUE_OUT` works whether the function is called `withdraw`, `emergencyExit`, or `pullFunds`
2. Behavioral signatures (`R:bal→X:out→W:bal`) enable pattern-matching across functions with different implementations
3. 150+ properties pre-computed means agents don't need to re-derive (e.g., `has_reentrancy_guard`, `state_write_after_external_call`)
4. Cross-function reentrancy surface detection requires multi-function analysis the graph enables
5. Call confidence scoring helps assess exploit feasibility

**Arguments AGAINST graph value (observed):**
1. Claude/GPT can read Solidity directly and reason about reentrancy patterns with high accuracy without a graph
2. Slither already detects many of these patterns — the graph may be duplicating Slither's work in a different format
3. The 150+ properties are heuristic-based (string matching on variable names like `BALANCE_PATTERNS = frozenset({"balance", "balances", "fund", "funds", ...})` in `operations.py:103-124`). This is fragile.
4. No A/B test exists comparing graph-aided vs graph-free detection quality

**The ablation study was designed** (`.planning/testing/decision-trees/IMP-G1-graph-ablation.yaml`) with clear metrics:
- Finding delta: `(test_findings - control_findings) / max(control_findings, 1)`
- Evidence delta: relative improvement in evidence quality
- Graph usage: distinct graph nodes cited per finding
- Four verdict levels: GRAPH_ESSENTIAL / HELPFUL / MARGINAL / NOT_VALUABLE

**But it was never run.** This is the single most important missing piece of evidence.

## Honest Verdict

**PARTIALLY WORKING**

| Component | Status | Confidence |
|-----------|--------|------------|
| Graph builder | Working, real engineering | High |
| Semantic operations (20) | Working, IR-based detection | High |
| Behavioral signatures | Working, correct computation | High |
| 150+ function properties | Working, heuristic-based | Medium |
| Query system (VQL) | Code works, never used by agents | Medium |
| Agent graph consumption | Theoretical only | High (in absence) |
| End-to-end pipeline | Non-existent | High (in absence) |
| Ablation evidence | Designed, never executed | High (in absence) |

## Specific Gaps

1. **No agent-executable query pipeline**: Core agents (attacker/defender/verifier) have `Bash(uv run python*)` but NOT `Bash(uv run alphaswarm*)`. They literally cannot run graph queries.

2. **No orchestrator wiring**: The orchestrator is supposed to build graph → extract subgraph → pass to agents as `AgentContext.subgraph`. No code implements this pipeline end-to-end.

3. **Zero real audit evidence**: No transcripts, no reports, no audit artifacts demonstrate graph-aided detection working in practice.

4. **Ablation study never executed**: The IMP-G1 study was designed with clear metrics and abort criteria but no results exist.

5. **Heuristic name matching**: Operation detection relies partly on variable name patterns (BALANCE_PATTERNS, OWNER_PATTERNS). The claim of "name-agnostic detection" is partially undermined — operations ARE derived from IR, but state variable classification uses name heuristics.

6. **No comparative benchmarks**: No data comparing BSKG-aided detection vs raw-code-aided detection vs Slither-only detection.

7. **Graph-first enforcement is aspirational**: `graph-first-template.md` says "CRITICAL: You MUST run BSKG queries before making any claims" but no code enforces this — it's just a prompt instruction that agents may or may not follow.

8. **SubGraph → Agent Context gap**: The SubgraphExtractor exists and works, but there's no code that creates an `AgentContext` from an extracted subgraph and passes it to a spawned agent.

9. **Query result format mismatch**: CLI query outputs JSON to stdout. Agent prompts expect structured `AgentContext` dataclasses. No adapter bridges these formats.

10. **No detection regression tests**: No test says "given this vulnerable contract, the graph-aided pipeline should detect vulnerability X with confidence >= Y."

## Recommendations for Milestone 6.0

### Must-Have (P0)

1. **Run the ablation study NOW**: Execute IMP-G1-ablation.yaml against the 3 test contracts. This single experiment will determine whether the graph adds value. If L4 (no improvement), redesign before building more.

2. **Fix agent tool access**: Give core agents `Bash(uv run alphaswarm*)` permission so they can actually run graph queries. Current `Bash(uv run python*)` is insufficient.

3. **Build the orchestrator wiring**: Implement the `build_graph → extract_subgraph → create_agent_context → spawn_agent` pipeline in actual code, not just documentation.

4. **Add detection regression tests**: Create tests that prove "graph + agent → correct vulnerability identification" for known-vulnerable contracts.

### Should-Have (P1)

5. **Reduce name-heuristic dependency**: The BALANCE_PATTERNS / OWNER_PATTERNS approach is fragile. Use Slither's type system and data flow analysis instead of string matching on variable names.

6. **Simplify the query interface**: Agents shouldn't need to learn VQL. Provide pre-built query templates for common patterns (reentrancy, access control, oracle manipulation) that agents can call with one command.

7. **Create a "graph summary" format**: Instead of dumping the full subgraph to agents, produce a concise security-relevant summary (3-5 key findings, operation sequences, missing guards) that fits in agent context windows.

### Nice-to-Have (P2)

8. **Graph caching and incremental builds**: For large projects, the full graph rebuild is expensive. Cache per-file results and rebuild incrementally.

9. **Benchmark against Slither detectors**: For every vulnerability the graph claims to detect, verify whether Slither alone already catches it. Focus graph development on what Slither misses.

10. **End-to-end CI test**: A single CI test that builds a graph from a vulnerable contract, runs a query, and verifies the correct finding emerges. This would catch regressions.
