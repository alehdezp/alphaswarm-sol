# Graph-First Reasoning Template

**Purpose:** Enforce BSKG queries and evidence packets before making any security claims.

**Context:** This template is used by VRS agents (attacker, defender, verifier) and skills to ensure graph-first analysis. All vulnerability investigations must use BSKG queries, not manual code reading.

---

## Strict Rule: Query Before Analysis

**CRITICAL:** You MUST run BSKG queries before making any claims about code behavior.

- ❌ **NEVER** manually read contract source files to analyze vulnerabilities
- ❌ **NEVER** make assumptions about code behavior without graph evidence
- ✅ **ALWAYS** run graph queries before conclusions (via Claude Code tool calls or direct CLI in dev mode)
- ✅ **ALWAYS** reference specific graph nodes and properties in your claims

---

## Required Investigation Workflow

Every vulnerability investigation follows this sequence:

### Step 1: BSKG Queries (MANDATORY)

**Before any analysis**, run queries to understand the code through the graph:

```bash
# Example 1: Find public functions with dangerous operation ordering
uv run alphaswarm query "FIND functions WHERE visibility IN [public, external] AND has_all_operations([TRANSFERS_VALUE_OUT, WRITES_USER_BALANCE])"

# Example 2: Check for missing guards
uv run alphaswarm query "FIND functions WHERE transfers_eth = true AND NOT has_reentrancy_guard"

# Example 3: Look for access control issues
uv run alphaswarm query "FIND functions WHERE modifies_critical_state = true AND NOT has_access_gate"

# Example 4: Pattern-based search
uv run alphaswarm query "pattern:weak-access-control"
```

**Query Intent Documentation:**

For each query you run, document:
- **What you're looking for** (e.g., "public functions that transfer value")
- **Why this matters** (e.g., "reentrancy attack vectors require external calls")
- **What graph properties you're checking** (e.g., `visibility`, `transfers_eth`, `has_reentrancy_guard`)

---

### Step 2: Evidence Packet (MANDATORY)

After running queries, build an evidence packet with:

#### Required Fields

```yaml
evidence_packet:
  finding_id: "VKG-{id}"
  query_results: "{brief summary of query output}"

  evidence_items:
    - type: "{code_property|operation_sequence|missing_guard|behavioral_signature}"
      graph_node_id: "{Contract.function}"
      property_checked: "{property name from BSKG}"
      property_value: "{actual value or presence}"
      code_location: "{file}:{line}"
      confidence: {0.0-1.0}
      source: "{attacker|defender|graph_query}"

    - type: "{...}"
      # ... more evidence items

  operation_sequences:
    - signature: "{behavioral signature, e.g., R:bal->X:out->W:bal}"
      operations: ["{OPERATION_1}", "{OPERATION_2}", ...]
      code_locations: ["{file}:{line}", ...]

  missing_guards:
    - guard_type: "{reentrancy_guard|access_control|slippage_check|...}"
      expected_property: "{has_reentrancy_guard|has_access_gate|...}"
      checked_at: "{Contract.function}"
```

#### Evidence Type Definitions

| Type | When to Use | Example |
|------|-------------|---------|
| `code_property` | A BSKG property is present or absent | `visibility = public`, `has_reentrancy_guard = false` |
| `operation_sequence` | Dangerous operation ordering detected | `TRANSFERS_VALUE_OUT` before `WRITES_USER_BALANCE` |
| `missing_guard` | Expected protection not found | No `nonReentrant` modifier |
| `behavioral_signature` | Pattern of operations indicates risk | `R:bal->X:out->W:bal` (CEI violation) |

---

### Step 3: Unknowns/Gaps (MANDATORY)

**Explicitly list what you DON'T know** from the graph:

```yaml
unknowns:
  - type: "{missing_context|unclear_property|insufficient_evidence}"
    description: "{what's missing}"
    impact: "{how this affects analysis}"
    recommendation: "{what's needed to resolve}"

gaps_in_evidence:
  - query: "{VQL query that didn't return results}"
    reason: "{why no results}"
    alternative_approach: "{what to try instead}"
```

#### Common Unknowns to Check

- **Taint analysis unavailable**: If dataflow tracking is not modeled
- **Cross-contract interactions**: If external calls lead outside the analyzed scope
- **Dynamic behavior**: If behavior depends on runtime state not captured in graph
- **Guard implementation details**: If custom guard logic is opaque to BSKG
- **Protocol context missing**: If assumptions, invariants, or role specifications are unavailable

**Rule:** If something is unknown, mark it explicitly. Never assume "no evidence = safe".

---

### Step 4: Conclusion (MANDATORY)

Only after Steps 1-3, state your conclusion:

```markdown
## Conclusion

**Claim:** {Your security finding or rebuttal}

**Evidence References:**
- Evidence item #1: {graph_node_id} shows {property} = {value}
- Evidence item #2: {behavioral_signature} indicates {risk}
- Evidence item #3: Missing guard: {guard_type} not found in {location}

**Confidence:** {0.0-1.0}

**Reasoning:** {Brief explanation linking evidence to conclusion}

**Caveats:**
- Unknown: {unknown_item_1}
- Gap: {gap_item_1}
```

**Confidence Calculation:**

```python
def calculate_confidence(evidence_items, unknowns):
    base_confidence = sum(item.confidence for item in evidence_items) / len(evidence_items)

    # Decrease for unknowns
    unknown_penalty = len(unknowns) * 0.1

    # Decrease for missing context
    if missing_protocol_context:
        unknown_penalty += 0.2

    return max(0.0, base_confidence - unknown_penalty)
```

---

## Integration Points

### For VRS Agents

**Attacker Agent:**
```markdown
### BSKG Queries
{Run queries to find attack vectors}

### Evidence Packet
{Build attack evidence with graph node IDs}

### Unknowns
{List what's unclear or missing}

### Attack Conclusion
{Construct exploit path with evidence references}
```

**Defender Agent:**
```markdown
### BSKG Queries
{Run queries to find guards and mitigations}

### Evidence Packet
{Build defense evidence with graph node IDs}

### Unknowns
{List unclear or missing defenses}

### Defense Conclusion
{Build defense argument with evidence references}
```

**Verifier Agent:**
```markdown
### Evidence Synthesis
{Compare attacker and defender evidence packets}

### Confidence Assessment
{Calculate confidence based on evidence quality}

### Verdict
{CONFIRMED|LIKELY|UNCERTAIN|REJECTED with evidence references}
```

---

### For VRS Skills

Skills like `/vrs-graph-retrieve` should output retrieval packs that match this evidence format:

```yaml
retrieval_pack:
  query: "{VQL query executed}"
  results_summary: {functions: N, findings: M}
  evidence_refs:
    - graph_node_id: "{Contract.function}"
      property: "{property_name}"
      value: "{property_value}"
      file: "{path}"
      line: {line_number}
  omissions:
    cut_set: []
    excluded_labels: []
  notes: ["{unknowns or gaps}"]
```

---

## Anti-Patterns (FORBIDDEN)

### ❌ Manual Code Reading

```markdown
BAD:
"I read the withdraw function and see it calls msg.sender before updating balance."

GOOD:
"BSKG query shows Vault.withdraw has operation sequence [TRANSFERS_VALUE_OUT, WRITES_USER_BALANCE]
with behavioral signature R:bal->X:out->W:bal (evidence ref: Vault.sol:L45)"
```

### ❌ Assumptions Without Evidence

```markdown
BAD:
"This function is probably safe because it's internal."

GOOD:
"BSKG query shows Vault._internalTransfer has visibility=internal (evidence ref: node Vault._internalTransfer,
property visibility=internal). However, it's called by public function withdraw (evidence ref: edge
Vault.withdraw->Vault._internalTransfer), so public attack surface exists."
```

### ❌ Claims Without Graph References

```markdown
BAD:
"The contract has reentrancy protection."

GOOD:
"BSKG query shows Vault.withdraw has has_reentrancy_guard=true (evidence ref: Vault.sol:L42, modifier nonReentrant).
Guard implemented via OpenZeppelin ReentrancyGuard.sol:L15."
```

---

## Tool Command Reference (Subagent/Dev)

### Core Commands

```bash
# Build knowledge graph (required first step)
uv run alphaswarm build-kg contracts/

# Build with semantic labels (Tier C patterns)
uv run alphaswarm build-kg contracts/ --with-labels

# Query with VQL
uv run alphaswarm query "FIND functions WHERE {conditions}"

# Query with natural language (translates to VQL)
uv run alphaswarm query "public functions that write state without access control"

# Query with pattern ID
uv run alphaswarm query "pattern:reentrancy-classic"

# Add explainability to query results
uv run alphaswarm query "FIND functions WHERE visibility=public explain"
```

### Common Query Patterns

```bash
# Reentrancy candidates
uv run alphaswarm query "FIND functions WHERE has_all_operations([TRANSFERS_VALUE_OUT, WRITES_USER_BALANCE]) AND NOT has_reentrancy_guard"

# Access control issues
uv run alphaswarm query "FIND functions WHERE modifies_critical_state = true AND NOT has_access_gate"

# Oracle manipulation risks
uv run alphaswarm query "FIND functions WHERE reads_oracle = true AND writes_user_balance = true"

# Unchecked external calls
uv run alphaswarm query "FIND functions WHERE calls_external = true AND NOT checks_return_value"

# CEI violations
uv run alphaswarm query "FIND functions WHERE sequence_order(before: TRANSFERS_VALUE_OUT, after: WRITES_USER_BALANCE)"
```

---

## Semantic Operations Reference

Use these operations in queries and evidence packets:

### Value Operations
- `TRANSFERS_VALUE_OUT` - Sends ETH or tokens out
- `READS_USER_BALANCE` - Reads user's balance
- `WRITES_USER_BALANCE` - Updates user's balance

### Access Operations
- `CHECKS_PERMISSION` - Verifies authorization
- `MODIFIES_OWNER` - Changes ownership
- `MODIFIES_ROLES` - Updates role assignments

### External Operations
- `CALLS_EXTERNAL` - Calls external contract
- `CALLS_UNTRUSTED` - Calls untrusted contract
- `READS_EXTERNAL_VALUE` - Reads from external source

### State Operations
- `MODIFIES_CRITICAL_STATE` - Updates important state
- `READS_ORACLE` - Reads oracle data
- `INITIALIZES_STATE` - Sets up initial state

**See:** `docs/reference/operations.md` for full list of 20+ semantic operations.

---

## Enforcement

This template is enforced through:

1. **Agent prompts**: Core agents (attacker, defender, verifier) include this template verbatim or by reference
2. **Skill contracts**: Skills reference this template in their workflow documentation
3. **Code review**: Any investigation that bypasses BSKG queries is flagged for revision
4. **Quality gates**: Verdicts without evidence packets are rejected by confidence enforcement

**See:**
- `src/alphaswarm_sol/shipping/agents/vrs-attacker.md`
- `src/alphaswarm_sol/shipping/agents/vrs-defender.md`
- `src/alphaswarm_sol/shipping/agents/vrs-verifier.md`
- `src/alphaswarm_sol/orchestration/confidence.py` (ORCH-09, ORCH-10)

---

## Related Documentation

- **Semantic Operations**: `docs/reference/operations.md`
- **Graph Properties**: `docs/reference/properties.md`
- **Skills Basics**: `docs/guides/skills-basics.md`
- **Skills Authoring**: `docs/guides/skills-authoring.md`
- **Pattern Basics**: `docs/guides/patterns-basics.md`
- **Pattern Advanced**: `docs/guides/patterns-advanced.md`
- **PHILOSOPHY.md**: `docs/PHILOSOPHY.md` (Pillar 5: Graph-First)
