# Guide Pattern Lattice Verification

**Purpose:** Define lattice-based, context-rich verification for Tier B/C patterns using graph + VQL reasoning.

## When To Use

- Any Tier B or Tier C pattern validation.
- Any time you need to prove human-like reasoning beyond static analysis.
- When building scenario packs for complex logic, authorization, or economic-loss bugs.

## Lattice Model (Scenario Design)

Use a lattice of dimensions to build non-lazy, high-signal scenarios.
Each scenario must explicitly select values on each axis.

| Axis | Options (examples) |
|---|---|
| Scope | single-contract, multi-contract, cross-module |
| Auth Model | owner-only, role-based, multi-sig, timelock |
| State Complexity | linear, state-machine, multi-stage init |
| Asset Flow | native, ERC20, ERC777 hooks, LP token |
| Externality | oracle, bridge, governance, callback |
| Economic Context | real context, simulated context, none |
| Adversary | EOA, malicious contract, MEV/frontrun |
| Temporal | no time, time-locked, epoch-based |
| Upgradeability | proxy, beacon, immutable |

## Contextual Reasoning Checklist

A valid Tier B/C test must show all of the following in transcripts and evidence packs:

- VQL query usage (query strings or command markers).
- Graph node references in reasoning.
- Protocol context pack reference.
- Economic context reference (real or simulated).
- Economic behavior model reference when economic loss is central (see `.planning/testing/scenarios/economic/ECONOMIC-MODEL-LIBRARY.md`).
- TaskCreate and TaskUpdate markers.
- Progress guidance markers (stage + next step + resume hint).

## Scenario Selection Heuristics (High-Value Cases)

Select scenarios that require multi-step reasoning and cross-function analysis:

- Cross-function auth bypass (setter + action split across functions).
- State machine violations (unexpected transitions or missing guards).
- Economic invariant drift (share price, accounting mismatch).
- Oracle manipulation or stale price usage.
- Fee-on-transfer or deflationary token accounting mismatch.
- Callback reentrancy via hooks (ERC777, ERC1363).
- Timelock or upgrade initialization misuse.
- Governance queue bypass or privilege escalation.
- Rounding/precision causing liquidation or collateral errors.
- Flash-loan assisted state manipulation.

## Scenario Families (Non-Lazy Requirement)

For each pattern, create a family of scenarios:

- **Base case:** known vulnerable contract.
- **Safe variant:** same structure, correct guard.
- **Counterfactual:** same pattern but a different failure mechanism.

Each family must include a negative control (safe) to prevent overfitting.

## VQL Query Requirements

- At least one structural query (e.g., functions lacking access control).
- At least one path query (e.g., value transfer before state update).
- At least one context query (e.g., economic or role dependencies).

## Economic Context Handling

If the scenario uses simulated economic context:

- Set `context.simulated: true` in settings or scenario metadata.
- Emit a bypass marker (e.g., `ECON_CONTEXT_BYPASS`).
- Attach the mock context artifact to the evidence pack.

If the scenario uses real context:

- Generate protocol + economic context packs.
- Require transcript markers showing context generation steps.
- Require `behavior_model_ref` in scenario metadata (Tier B/C economic scenarios).

## Path Exploration Artifact

Cross-contract or multi-function paths must be recorded using
`.planning/testing/templates/PATH-EXPLORATION-TEMPLATE.md` and attached to the
evidence pack.

## Evidence Requirements

Each scenario must produce:

- Transcript with VQL usage and TaskCreate/TaskUpdate markers.
- Evidence pack containing graph references and context artifacts.
- A short reasoning summary that links findings to graph nodes.

## Failure Modes (Must Be Recorded)

- Missing VQL usage or graph references.
- Missing TaskCreate/TaskUpdate sequence.
- Context bypass without explicit marker.
- Tier C gating ignored or not enforced.

## Usage Notes

- Always run in a dedicated demo claude-code-agent-teams session.
- Use the alignment ledger to map scenario → pattern → workflow → evidence.
- When a scenario fails, follow the iteration protocol and re-run with a new session.
