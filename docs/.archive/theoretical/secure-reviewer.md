# Secure Solidity Reviewer - Reference

## Overview

The Secure Solidity Reviewer is a specialized agent that blends **creative attack thinking** with **adversarial skepticism** while enforcing evidence-first and graph-first reasoning. It operates in two distinct modes that serve different purposes in the vulnerability review process.

## Output Contract

All secure reviewer outputs must conform to the JSON schema defined in `schemas/secure_reviewer_output.json`.

**Core Requirements:**
- **Evidence-anchored**: Every finding must link to code locations or graph node IDs
- **Graph-first**: Must execute BSKG queries before drawing conclusions
- **Explicit uncertainty**: Must declare known unknowns
- **Mode-specific behavior**: Creative vs adversarial modes have different output requirements

## Review Modes

### Creative Mode

**Purpose:** Brainstorm potential attack vectors and vulnerabilities without initial constraints.

**Mindset:** "What could an attacker do?"

**Behavior:**
- Generate creative attack hypotheses
- Explore unconventional attack paths
- Consider multi-step and cross-function attacks
- Think about MEV and front-running opportunities
- Propose edge cases and adversarial scenarios

**Output Requirements:**
- `mode: "creative"`
- Must include `creative_hypotheses` array
- Each hypothesis includes attack path and feasibility
- Supporting evidence must be graph-anchored

**When to Use:**
- Initial vulnerability discovery
- Brainstorming new attack vectors
- Exploring unknown code territories
- Pre-audit reconnaissance

**Guardrails:**
- Must still anchor all claims to evidence
- Must execute graph queries first
- Feasibility ratings must be realistic
- Cannot invent properties not in graph

---

### Adversarial Mode

**Purpose:** Challenge and refute existing claims with evidence-backed counterarguments.

**Mindset:** "Why might this NOT be vulnerable?"

**Behavior:**
- Challenge attack feasibility
- Identify missing preconditions
- Find protective guards and mitigations
- Point out evidence gaps in attacker claims
- Provide counter-signals and contradictions

**Output Requirements:**
- `mode: "adversarial"`
- Must include `refutations` array
- Each refutation targets specific claim
- Must provide strength rating (STRONG, MODERATE, WEAK)

**When to Use:**
- Reviewing attacker findings
- Debate protocol (defender role)
- Verification stage
- False positive reduction

**Guardrails:**
- Must provide evidence for refutations
- Cannot dismiss without graph-backed reasoning
- Must acknowledge when refutation is weak
- Cannot ignore strong attack evidence

---

## Mode Switching

**When to switch from Creative to Adversarial:**
1. After initial hypotheses generated
2. When verifying attacker claims
3. During debate protocol
4. When reducing false positives

**When to switch from Adversarial to Creative:**
1. When refutations fail (vulnerability confirmed)
2. When exploring related attack vectors
3. After successful defense identified
4. During pattern discovery

**Note:** Mode switching should be explicit and documented in the output.

---

## Required Fields

### Summary
**Type:** String (20-500 characters)
**Purpose:** Concise overview of findings
**Example:** "Identified potential reentrancy in withdraw function due to CEI violation. No guards found."

### Risk Level
**Type:** Enum
**Values:** CRITICAL, HIGH, MEDIUM, LOW, INFORMATIONAL, NONE
**Purpose:** Overall risk assessment based on evidence

### Evidence Array
**Type:** Array of Evidence Objects
**Purpose:** Anchor all claims to code or graph

**Evidence Types:**
- `code_property` - Specific code property (e.g., visibility)
- `semantic_operation` - Operation detection (e.g., TRANSFERS_VALUE_OUT)
- `behavioral_signature` - Operation sequence (e.g., R:bal->X:out->W:bal)
- `missing_guard` - Absence of protection
- `operation_sequence` - Ordering of operations
- `graph_structure` - Graph topology feature
- `counter_signal` - Evidence against vulnerability

**Required Evidence Fields:**
- `type` - Evidence type
- `description` - Clear description
- `confidence` - Score from 0.0 to 1.0
- Either `code_location` OR `graph_node_id` (at least one required)

**Example:**
```json
{
  "type": "semantic_operation",
  "description": "Function transfers value out via external call",
  "code_location": "Vault.sol:L45",
  "graph_node_id": "Vault.withdraw",
  "confidence": 0.95,
  "property": "TRANSFERS_VALUE_OUT",
  "value": true
}
```

### Graph Queries
**Type:** Array of Query Objects
**Purpose:** Enforce graph-first analysis (minimum 1 query required)

**Required for each query:**
- `query` - VQL or structured query
- `rationale` - Why this query was needed
- `results_count` - Number of results (optional)

**Example:**
```json
{
  "query": "FIND functions WHERE visibility IN [public, external] AND has_operation: TRANSFERS_VALUE_OUT AND NOT has_reentrancy_guard",
  "rationale": "Identify public functions with external calls lacking reentrancy protection",
  "results_count": 3
}
```

### Gaps
**Type:** Array of Gap Objects
**Purpose:** Identify missing information or unclear aspects

**Gap Types:**
- `missing_guard` - Expected guard not found
- `unclear_intent` - Code intent unclear
- `incomplete_context` - Missing protocol context
- `undocumented_invariant` - Assumption not documented
- `missing_taint_flow` - Taint analysis incomplete
- `unknown_external_behavior` - External dependency behavior unknown

**Impact Levels:**
- `blocks_verification` - Cannot verify without this
- `reduces_confidence` - Lowers confidence in findings
- `informational` - Nice to have but not critical

### Recommendations
**Type:** Array of Recommendation Objects
**Purpose:** Provide actionable next steps

**Required Fields:**
- `priority` - CRITICAL, HIGH, MEDIUM, LOW
- `action` - Specific action to take
- `rationale` - Why this is recommended
- `code_location` - Where to apply (optional)

### Known Unknowns
**Type:** Object
**Purpose:** Explicit uncertainty declaration

**Required:**
- `has_uncertainty` - Boolean flag
- `uncertainties` - Array (required if has_uncertainty is true)

**Example:**
```json
{
  "has_uncertainty": true,
  "uncertainties": [
    {
      "area": "External contract behavior",
      "reason": "Target contract source not available in graph",
      "needs_human_review": true
    }
  ]
}
```

---

## Graph-First Enforcement

**CRITICAL REQUIREMENT:** Reviewers MUST execute BSKG queries before conclusions.

### Correct Workflow
1. ✅ Formulate graph query based on vulnerability hypothesis
2. ✅ Execute query via BSKG
3. ✅ Analyze query results
4. ✅ Draw evidence-backed conclusions
5. ✅ Document queries in `graph_queries` array

### Incorrect Workflow
1. ❌ Read source code manually
2. ❌ Look for function names
3. ❌ Pattern match on strings
4. ❌ Draw conclusions without graph queries

### Example Graph-First Query Sequence

**Hypothesis:** "Potential reentrancy vulnerability"

**Query 1: Find entry points**
```vql
FIND functions WHERE
  visibility IN [public, external]
  AND has_operation: TRANSFERS_VALUE_OUT
```

**Query 2: Check for guards**
```vql
FIND functions WHERE
  id IN <results_from_query_1>
  AND has_reentrancy_guard = true
```

**Query 3: Check operation ordering**
```vql
FIND functions WHERE
  id IN <results_from_query_1>
  AND behavioral_signature CONTAINS "R:bal->X:out->W:bal"
```

**Conclusion:** Based on queries 1-3, identify functions with CEI violations and no guards.

---

## Mode-Specific Output Requirements

### Creative Mode Only

**Must Include:**
- `creative_hypotheses` array

**Hypothesis Structure:**
```json
{
  "hypothesis": "Attacker can drain vault via reentrancy",
  "attack_path": [
    "1. Attacker deposits minimum amount to vault",
    "2. Attacker calls withdraw() with full balance",
    "3. Fallback re-enters withdraw() before balance update",
    "4. Balance check passes (stale value)",
    "5. Attacker receives ETH twice",
    "6. Repeat until vault drained"
  ],
  "feasibility": "HIGH",
  "supporting_evidence": [0, 1, 3]
}
```

### Adversarial Mode Only

**Must Include:**
- `refutations` array

**Refutation Structure:**
```json
{
  "claim_being_refuted": "Function is vulnerable to reentrancy",
  "refutation": "Function uses ReentrancyGuard from OpenZeppelin, confirmed in graph as has_reentrancy_guard=true at node Vault.withdraw",
  "strength": "STRONG",
  "supporting_evidence": [2, 4]
}
```

---

## Confidence Guidelines

**Evidence Confidence Levels:**
- **0.9-1.0:** Direct graph property confirmed
- **0.7-0.89:** Strong inference from multiple signals
- **0.5-0.69:** Moderate confidence, some uncertainty
- **0.3-0.49:** Weak signal, needs verification
- **0.0-0.29:** Speculative, low confidence

**Risk Level Mapping:**
- **CRITICAL:** High confidence (>0.85) + severe impact + high feasibility
- **HIGH:** High confidence (>0.7) + significant impact
- **MEDIUM:** Moderate confidence (>0.5) OR moderate impact
- **LOW:** Lower confidence (<0.5) OR minimal impact
- **INFORMATIONAL:** Best practice violation, no direct risk
- **NONE:** No evidence of vulnerability

---

## Anti-Patterns

### DO NOT:
❌ Make claims without graph queries
❌ Rely on function/variable names
❌ Invent properties not in graph
❌ Skip uncertainty declaration
❌ Mix creative and adversarial modes without switching
❌ Use evidence from one mode in the other without re-validation

### DO:
✅ Execute queries before conclusions
✅ Anchor every claim to code locations or graph nodes
✅ Declare known unknowns explicitly
✅ Use semantic operations, not names
✅ Switch modes explicitly when needed
✅ Provide confidence scores for all evidence

---

## Validation Rules

**Schema Validation:**
- All outputs must validate against `schemas/secure_reviewer_output.json`
- Required fields must be present
- Evidence must have code_location OR graph_node_id
- graph_queries array must have at least 1 entry

**Consistency Checks:**
- Evidence confidence must match risk_level
- Supporting evidence indices must be valid
- Mode must match output structure (creative_hypotheses OR refutations)
- Gaps should be reflected in known_unknowns

**Quality Gates:**
- High risk requires high confidence evidence (>0.7)
- Critical risk requires very high confidence (>0.85)
- Uncertainty must be acknowledged if confidence < 0.7
- Recommendations must align with findings

---

## Integration with VRS

The Secure Reviewer can be used in several VRS workflows:

### Standalone Review
```bash
# Invoke secure reviewer on contract
/vrs-review contracts/Vault.sol --mode creative
```

### Debate Protocol
```bash
# Creative mode (attacker perspective)
vrs-secure-reviewer --mode creative --context bead-ctx-001

# Adversarial mode (defender perspective)
vrs-secure-reviewer --mode adversarial --refute findings-001
```

### Pattern Discovery
```bash
# Explore new attack vectors
vrs-secure-reviewer --mode creative --pattern-hint reentrancy
```

### Verification Stage
```bash
# Challenge existing findings
vrs-secure-reviewer --mode adversarial --verify findings-001
```

---

## Cost Optimization

**Model Selection:**
- **Creative Mode:** Sonnet 4.5 (balanced creativity + cost)
- **Adversarial Mode:** Sonnet 4.5 (sufficient for refutation)
- **Escalate to Opus 4.5:** Only when confidence thresholds fail or novel patterns detected

**Query Optimization:**
- Batch related queries when possible
- Use targeted queries (specific node IDs) over broad scans
- Cache graph results for repeated queries
- Minimize evidence token count (concise descriptions)

---

## Examples

### Creative Mode Example Output

```json
{
  "summary": "Identified CEI violation in withdraw function with no reentrancy guard. High feasibility reentrancy attack path.",
  "risk_level": "CRITICAL",
  "mode": "creative",
  "evidence": [
    {
      "type": "semantic_operation",
      "description": "External call transfers ETH",
      "code_location": "Vault.sol:L45",
      "confidence": 0.95,
      "property": "TRANSFERS_VALUE_OUT"
    },
    {
      "type": "behavioral_signature",
      "description": "Balance read before call, write after",
      "graph_node_id": "Vault.withdraw",
      "confidence": 0.90,
      "property": "operation_sequence",
      "value": "R:bal->X:out->W:bal"
    },
    {
      "type": "missing_guard",
      "description": "No reentrancy guard detected",
      "graph_node_id": "Vault.withdraw",
      "confidence": 0.95,
      "property": "has_reentrancy_guard",
      "value": false
    }
  ],
  "graph_queries": [
    {
      "query": "FIND functions WHERE visibility IN [public, external] AND has_operation: TRANSFERS_VALUE_OUT",
      "rationale": "Identify external entry points that transfer value",
      "results_count": 2
    },
    {
      "query": "GET function Vault.withdraw PROPERTIES has_reentrancy_guard, behavioral_signature",
      "rationale": "Check withdraw function for guards and operation ordering",
      "results_count": 1
    }
  ],
  "gaps": [],
  "recommendations": [
    {
      "priority": "CRITICAL",
      "action": "Add ReentrancyGuard modifier or implement checks-effects-interactions pattern",
      "rationale": "Prevents reentrancy attacks via callback",
      "code_location": "Vault.sol:L40-L48"
    }
  ],
  "known_unknowns": {
    "has_uncertainty": false
  },
  "creative_hypotheses": [
    {
      "hypothesis": "Attacker drains vault via reentrancy callback",
      "attack_path": [
        "Deposit minimum amount to establish balance",
        "Call withdraw(balance)",
        "Fallback callback re-enters withdraw()",
        "Balance check passes (not yet updated)",
        "Receive ETH twice",
        "Repeat until vault empty"
      ],
      "feasibility": "HIGH",
      "supporting_evidence": [0, 1, 2]
    }
  ]
}
```

### Adversarial Mode Example Output

```json
{
  "summary": "Reentrancy claim refuted. ReentrancyGuard modifier confirmed via graph query. CEI pattern also verified.",
  "risk_level": "NONE",
  "mode": "adversarial",
  "evidence": [
    {
      "type": "counter_signal",
      "description": "ReentrancyGuard modifier present",
      "code_location": "Vault.sol:L40",
      "graph_node_id": "Vault.withdraw",
      "confidence": 0.95,
      "property": "has_reentrancy_guard",
      "value": true
    },
    {
      "type": "code_property",
      "description": "Balance updated before external call",
      "code_location": "Vault.sol:L43-L45",
      "confidence": 0.90,
      "property": "cei_pattern_followed",
      "value": true
    }
  ],
  "graph_queries": [
    {
      "query": "GET function Vault.withdraw PROPERTIES has_reentrancy_guard, behavioral_signature, modifiers",
      "rationale": "Verify protection mechanisms",
      "results_count": 1
    }
  ],
  "gaps": [],
  "recommendations": [
    {
      "priority": "LOW",
      "action": "Document CEI pattern usage in code comments",
      "rationale": "Improve code readability and auditability"
    }
  ],
  "known_unknowns": {
    "has_uncertainty": false
  },
  "refutations": [
    {
      "claim_being_refuted": "Vault.withdraw is vulnerable to reentrancy",
      "refutation": "Graph query confirms has_reentrancy_guard=true and cei_pattern_followed=true. OpenZeppelin ReentrancyGuard modifier prevents re-entry.",
      "strength": "STRONG",
      "supporting_evidence": [0, 1]
    }
  ]
}
```

---

## See Also

- **Output Schema:** `schemas/secure_reviewer_output.json`
- **Agent Definitions:** `.claude/subagents/secure-solidity-reviewer.md`, `src/alphaswarm_sol/skills/shipped/agents/vrs-secure-reviewer.md`
- **Graph-First Principles:** `docs/PHILOSOPHY.md`
- **VRS Workflow:** `docs/guides/skills-basics.md`
