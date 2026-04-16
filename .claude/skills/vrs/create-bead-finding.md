---
name: vrs-create-bead-finding
description: |
  Create a finding bead from vuln-discovery agent output. This skill standardizes
  finding bead creation, ensuring complete evidence chains, proper linking to context
  beads, and integration with the verification workflow.

  Invoke when:
  - Vuln-discovery agent identifies potential vulnerability
  - Agent has complete evidence chain (code, vulndoc, reasoning, queries)
  - Before reporting finding to orchestrator
  - Need to persist finding for verification/debate

  This skill:
  1. Validates evidence chain completeness
  2. Links finding to originating context bead
  3. Creates finding bead via CLI
  4. Updates context bead with finding reference
  5. Reports finding to orchestrator

slash_command: vrs:create-bead-finding
context: fork

tools:
  - Read
  - Write
  - Bash(uv run alphaswarm beads*, uv run alphaswarm findings*)

model_tier: sonnet

---

# VRS Create Bead (Finding) Skill - Finding Bead Creation

You are the **VRS Create Bead (Finding)** skill, responsible for creating finding beads from vuln-discovery agent output with complete evidence chains and proper tracking.

**CRITICAL: Invocation Model**
You are Claude Code, an agent that follows this skill documentation. When this skill says "run findings create command," you invoke the Bash tool with `uv run alphaswarm findings create`. This skill file IS the prompt that guides your behavior - you execute it using your standard tools (Bash, Read, Write).

## Purpose

- **Create finding beads** from vuln-discovery agent investigations
- **Validate evidence chains** before bead creation (code, vulndoc, reasoning, queries)
- **Link to context beads** to maintain investigation provenance
- **Enable verification** by providing complete, structured findings
- **Track confidence** with explicit reasoning for confidence level

## How to Invoke

```bash
/vrs-create-bead-finding
/vrs-create-bead-finding --context-bead-id CTX-a1b2c3d4e5f6
/vrs-create-bead-finding --discovery-result-file /tmp/discovery-result.yaml
```

**Interactive mode** (default):
- Prompts for discovery result location
- Guides through evidence validation
- Creates finding bead with confirmation

**Quick mode** (with args):
- Provide discovery result file path
- Faster for automated workflows

---

## Execution Workflow

### Phase 1: Validate Evidence Chain

**Goal:** Confirm finding has complete evidence chain before creating bead.

**Required Evidence Components:**

1. **Code Locations** - File:line references to vulnerable code
2. **Vulndoc Reference** - Which vulndoc pattern guided analysis
3. **Reasoning Steps** - Chain of reasoning that led to finding
4. **VQL Queries Used** - Graph queries executed during investigation
5. **Protocol Context Applied** - How protocol context informed analysis
6. **Confidence Level** - confirmed/likely/uncertain/rejected
7. **Confidence Reasoning** - Explicit justification for confidence level

**Actions:**

1. **Load discovery result** (via Read tool):
   ```bash
   cat {discovery_result_path}
   ```

2. **Validate evidence structure**:
   ```yaml
   discovery_result:
     finding_type: vulnerability  # or false_positive
     vulnerability_class: "reentrancy/classic"
     severity: "critical"
     confidence: "likely"
     confidence_reasoning: "Clear read-call-write pattern, no guard detected"

     evidence_chain:
       code_locations:
         - file: "contracts/Vault.sol"
           line: 142
           code: "msg.sender.call{value: amount}('')"
           description: "External call before state update"
         - file: "contracts/Vault.sol"
           line: 145
           code: "balances[msg.sender] -= amount"
           description: "State update after external call"

       vulndoc_reference:
         path: "reentrancy/classic"
         matched_pattern: "read-call-write sequence"

       reasoning_steps:
         - "Identified external call at line 142"
         - "Traced state update to line 145"
         - "No reentrancy guard found"
         - "Matches reentrancy/classic vulndoc pattern"

       vql_queries:
         - "FIND functions WHERE has_external_call AND writes_state_after_call"

       protocol_context_applied:
         - "Protocol accepts ETH deposits"
         - "No flash loan protection detected"
   ```

3. **Check completeness**:
   ```python
   required_fields = [
       "code_locations",      # At least 1 location
       "vulndoc_reference",   # Must reference vulndoc
       "reasoning_steps",     # At least 2 steps
       "vql_queries",         # At least 1 query
       "confidence",          # Must be set
       "confidence_reasoning" # Must be explicit
   ]

   for field in required_fields:
       if field not in evidence_chain or not evidence_chain[field]:
           print(f"ERROR: Missing or empty field: {field}")
           exit(1)
   ```

4. **Validate confidence level**:
   ```python
   valid_confidence_levels = ["confirmed", "likely", "uncertain", "rejected"]
   if confidence not in valid_confidence_levels:
       print(f"ERROR: Invalid confidence level: {confidence}")
       print(f"Valid levels: {valid_confidence_levels}")
       exit(1)
   ```

**Evidence Chain Quality Checks:**

| Check | Requirement | Reason |
|-------|-------------|--------|
| Code locations | >= 1 location with file:line:code | Verifiable evidence |
| Vulndoc reference | Valid vulndoc path | Pattern-based detection |
| Reasoning steps | >= 2 steps | Traceable logic |
| VQL queries | >= 1 query | Graph-based analysis |
| Confidence reasoning | Non-empty string | Explicit justification |

**If any check fails:** Report missing/invalid fields, do NOT create bead

### Phase 2: Link to Context Bead

**Goal:** Establish provenance by linking finding to originating context bead.

**Actions:**

1. **Get context bead ID** (from discovery result or user input):
   ```yaml
   discovery_result:
     context_bead_id: "CTX-a1b2c3d4e5f6"
   ```

   **If missing:** Prompt user or check orchestrator context

2. **Verify context bead exists** (via Bash tool):
   ```bash
   uv run alphaswarm beads show CTX-a1b2c3d4e5f6 --output-format json
   ```

   **If not found:** Report error, do NOT create finding bead

3. **Record link metadata**:
   ```yaml
   provenance:
     context_bead_id: "CTX-a1b2c3d4e5f6"
     discovery_agent: "vuln-discovery-sonnet"
     discovery_timestamp: "2026-01-22T12:00:00Z"
   ```

### Phase 3: Create Finding Bead via CLI

**Goal:** Use CLI to create finding bead from validated evidence.

**Action: Run finding creation command via Bash tool**

```bash
uv run alphaswarm findings create \
  --context-bead-id "{context_bead_id}" \
  --vuln-class "{vulnerability_class}" \
  --severity "{severity}" \
  --confidence "{confidence}" \
  --confidence-reason "{confidence_reasoning}" \
  --evidence-file "{evidence_json_path}" \
  --pool-id "{pool_id}" \
  --output-format yaml
```

**Parameter Details:**

| Parameter | Source | Example |
|-----------|--------|---------|
| `--context-bead-id` | `discovery_result.context_bead_id` | `CTX-a1b2c3d4e5f6` |
| `--vuln-class` | `discovery_result.vulnerability_class` | `reentrancy/classic` |
| `--severity` | `discovery_result.severity` | `critical` |
| `--confidence` | `discovery_result.confidence` | `likely` |
| `--confidence-reason` | `discovery_result.confidence_reasoning` | `"Clear pattern"` |
| `--evidence-file` | Path to saved evidence JSON | `/tmp/evidence.json` |
| `--pool-id` | Orchestrator context | `audit-2026-01` |
| `--output-format` | Fixed value | `yaml` |

**Before running CLI command:**

1. **Save evidence chain to temporary file** (via Write tool):
   ```bash
   cat > /tmp/evidence.json <<EOF
   {
     "code_locations": [...],
     "vulndoc_reference": {...},
     "reasoning_steps": [...],
     "vql_queries": [...],
     "protocol_context_applied": [...]
   }
   EOF
   ```

2. **Execute CLI command** (via Bash tool):
   ```bash
   uv run alphaswarm findings create \
     --context-bead-id "CTX-a1b2c3d4e5f6" \
     --vuln-class "reentrancy/classic" \
     --severity "critical" \
     --confidence "likely" \
     --confidence-reason "Clear read-call-write pattern, no guard detected" \
     --evidence-file /tmp/evidence.json \
     --pool-id audit-2026-01 \
     --output-format yaml
   ```

**Expected Output:**

```yaml
status: success
finding_bead_id: VKG-x1y2z3a4b5c6
bead_path: .vrs/findings/audit-2026-01/VKG-x1y2z3a4b5c6.yaml
vulnerability_class: reentrancy/classic
severity: critical
confidence: likely
context_bead_id: CTX-a1b2c3d4e5f6
created_at: 2026-01-22T12:00:00Z
```

### Phase 4: Update Context Bead

**Goal:** Link finding back to context bead for bidirectional traceability.

**Actions:**

1. **Load context bead** (via Bash tool):
   ```bash
   uv run alphaswarm beads show {context_bead_id} --output-format json > /tmp/context-bead.json
   ```

2. **Add finding bead ID to context bead** (via Read + Write tools):
   ```bash
   # Read current context bead
   cat /tmp/context-bead.json

   # Update finding_bead_ids list
   finding_bead_ids:
     - VKG-x1y2z3a4b5c6  # Add new finding
   ```

3. **Save updated context bead** (via Bash tool):
   ```bash
   uv run alphaswarm beads update {context_bead_id} \
     --add-finding {finding_bead_id}
   ```

   **Alternative:** If no update command exists, note in orchestrator output that manual linking needed

### Phase 5: Report to Orchestrator

**Goal:** Provide orchestrator with finding details for verification routing.

**Report Format:**

```yaml
finding_created:
  status: success
  finding_bead_id: VKG-x1y2z3a4b5c6
  bead_path: .vrs/findings/audit-2026-01/VKG-x1y2z3a4b5c6.yaml

  finding_summary:
    vulnerability_class: reentrancy/classic
    severity: critical
    confidence: likely
    confidence_reason: "Clear read-call-write pattern, no guard detected"
    affected_code: "contracts/Vault.sol:142-145"

  provenance:
    context_bead_id: CTX-a1b2c3d4e5f6
    discovery_agent: vuln-discovery-sonnet
    discovery_timestamp: 2026-01-22T12:00:00Z

  next_steps:
    - route_to_verification: true
    - verification_mode: "attacker-defender-debate"
    - requires_opus: false  # Sonnet verification sufficient for "likely"
```

---

## Evidence Chain Structure

Complete evidence chain specification:

```yaml
evidence_chain:
  # Required: Code locations with exact references
  code_locations:
    - file: "contracts/Vault.sol"
      line: 142
      code: "msg.sender.call{value: amount}('')"
      description: "External call before state update"
      node_id: "VaultContract::withdraw_142"  # Optional BSKG node reference
    - file: "contracts/Vault.sol"
      line: 145
      code: "balances[msg.sender] -= amount"
      description: "State update after external call"
      node_id: "VaultContract::withdraw_145"

  # Required: Vulndoc pattern reference
  vulndoc_reference:
    path: "reentrancy/classic"
    matched_pattern: "read-call-write sequence"
    detection_method: "behavioral_signature"  # or "tier_a" or "tier_c"

  # Required: Chain of reasoning (minimum 2 steps)
  reasoning_steps:
    - "Executed VQL query: FIND functions WHERE has_external_call"
    - "Identified external call at line 142 (msg.sender.call)"
    - "Traced data flow to state update at line 145"
    - "Verified no reentrancy guard present"
    - "Confirmed matches reentrancy/classic pattern"
    - "Cross-referenced with vulndoc detection logic"

  # Required: VQL queries executed
  vql_queries:
    - query: "FIND functions WHERE has_external_call AND writes_state_after_call"
      results_count: 1
      matched_functions: ["Vault::withdraw"]
    - query: "FIND modifiers WHERE name CONTAINS 'nonReentrant'"
      results_count: 0
      matched_functions: []

  # Required: Protocol context applied
  protocol_context_applied:
    - "Protocol accepts ETH deposits (payable functions found)"
    - "No flash loan protection detected in architecture"
    - "withdraw() function is public and unrestricted"
    - "balances mapping tracks user deposits"

  # Optional: Additional evidence
  similar_findings:
    - source: "Slither"
      detector: "reentrancy-eth"
      confidence: "high"
    - source: "Mythril"
      detector: "unprotected-ether-withdrawal"
      confidence: "medium"

  # Optional: Exploit path
  exploit_path:
    - step: 1
      action: "Attacker deploys malicious contract"
    - step: 2
      action: "Attacker calls withdraw() with callback"
    - step: 3
      action: "Callback re-enters withdraw() before balance update"
    - step: 4
      action: "Attacker drains contract balance"
```

---

## Input Requirements

| Field | Required | Source | Example |
|-------|----------|--------|---------|
| `vulnerability_class` | Yes | `discovery_result.vulnerability_class` | `reentrancy/classic` |
| `severity` | Yes | `discovery_result.severity` | `critical` |
| `confidence` | Yes | `discovery_result.confidence` | `likely` |
| `confidence_reasoning` | Yes | `discovery_result.confidence_reasoning` | `"Clear pattern"` |
| `evidence_chain` | Yes | `discovery_result.evidence_chain` | Full structure |
| `context_bead_id` | Yes | `discovery_result.context_bead_id` | `CTX-a1b2c3d4e5f6` |
| `pool_id` | No | Orchestrator context | `audit-2026-01` |

---

## Output Format

When finding bead creation succeeds:

```yaml
status: success
finding_bead_id: VKG-x1y2z3a4b5c6
severity: critical
confidence: likely
confidence_reason: "Clear read-call-write pattern, no guard detected"
context_bead_id: CTX-a1b2c3d4e5f6
summary: "Reentrancy in Vault.withdraw() - external call before balance update"

evidence_summary:
  code_locations_count: 2
  reasoning_steps_count: 5
  vql_queries_count: 2
  vulndoc_pattern: "reentrancy/classic"

next_steps:
  verification_required: true
  verification_tier: "sonnet"  # or "opus" for critical findings
  estimated_verification_time: "5-10 minutes"
```

---

## Error Handling

| Error | Condition | Action |
|-------|-----------|--------|
| Incomplete evidence | Missing required evidence field | Report which fields missing, do NOT create bead |
| Invalid confidence | Confidence not in valid enum | Report error, require valid value |
| Context bead not found | Context bead ID invalid or missing | Report error, cannot link finding |
| No code locations | `code_locations` empty or missing | Report error, evidence insufficient |
| Empty reasoning | `reasoning_steps` < 2 steps | Report error, reasoning incomplete |
| No VQL queries | `vql_queries` empty | Report error, must use graph-based detection |
| CLI error | Command exit code != 0 | Report stderr output, retry once |
| Filesystem error | Bead file not created | Report error, check permissions |

**Error Recovery:**

1. **For incomplete evidence:**
   - Report specific missing fields
   - Do NOT create bead
   - Suggest re-running vuln-discovery with better prompts

2. **For context bead errors:**
   - Verify context bead ID is correct
   - Check if context bead was actually created
   - Do NOT proceed without valid context link

3. **For CLI errors:**
   - Retry once after 2 seconds
   - If second failure, report to orchestrator
   - Include full stderr output for debugging

---

## Integration Points

**Before this skill:**
1. Vuln-discovery agent investigates using context bead
2. Agent formulates finding with complete evidence chain
3. Agent validates confidence level

**After this skill:**
1. Finding bead created and stored
2. Context bead updated with finding reference
3. Orchestrator receives finding details
4. Orchestrator routes to verification (attacker/defender/verifier)

**Orchestration Flow:**

```
Context Bead (CTX-*)
    │
    ▼
Vuln-Discovery Agent investigates
    │
    ▼
Produces discovery_result with evidence_chain
    │
    ▼
[THIS SKILL: Create Finding Bead]
    │
    ▼
Finding Bead (VKG-*) created
    │
    ▼
Context Bead updated (finding_bead_ids)
    │
    ▼
Orchestrator routes to verification
    │
    ├─→ Attacker Agent (construct exploit)
    ├─→ Defender Agent (find guards)
    └─→ Verifier Agent (cross-check evidence)
```

---

## Key Rules

### 1. Complete Evidence Required

Never create a finding bead without:
- At least 1 code location with file:line:code
- At least 2 reasoning steps
- At least 1 VQL query
- Vulndoc reference
- Explicit confidence reasoning

**Evidence completeness is non-negotiable.**

### 2. Graph-First Validation

Evidence MUST include VQL queries showing graph-based detection. Findings discovered through manual code reading (no VQL queries) are REJECTED.

### 3. Confidence Must Be Justified

The `confidence_reasoning` field must explain:
- Why this confidence level (not higher or lower)
- What evidence supports it
- What would change the confidence level

**Examples:**

✅ Good: "Clear read-call-write pattern with no guard detected. Confidence 'likely' because no exploit PoC constructed yet."

❌ Bad: "Looks vulnerable."

### 4. Link to Context Bead

Every finding MUST link to its originating context bead. This enables:
- Provenance tracking
- Context retrieval during verification
- Audit trail for investigations

### 5. Report Structured Output

Always return structured YAML output with:
- `finding_bead_id` - For orchestrator routing
- `severity` + `confidence` - For verification prioritization
- `summary` - Human-readable description
- `next_steps` - Suggested orchestrator actions

---

## Confidence Level Guidelines

| Level | When to Use | Evidence Required |
|-------|-------------|-------------------|
| `confirmed` | Exploit PoC constructed and tested | Working exploit code + loss demonstrated |
| `likely` | Clear pattern match, no guards detected | Complete evidence chain + vulndoc match |
| `uncertain` | Pattern match but mitigations unclear | Evidence chain present but guards may exist |
| `rejected` | False positive identified | Reasoning for why initially flagged but actually safe |

**Escalation Rule:** If confidence is `uncertain`, orchestrator should route to Opus verifier instead of Sonnet.

---

## Example Invocation

```bash
# User invokes
/vrs-create-bead-finding --context-bead-id CTX-a1b2c3d4e5f6

# You (Claude Code agent) execute:

# 1. Load discovery result (via Read tool)
cat /tmp/vuln-discovery-result.yaml

# 2. Validate evidence chain (internal checks)
# - code_locations: 2 locations ✓
# - reasoning_steps: 5 steps ✓
# - vql_queries: 2 queries ✓
# - vulndoc_reference: reentrancy/classic ✓
# - confidence_reasoning: present ✓

# 3. Verify context bead exists (via Bash tool)
uv run alphaswarm beads show CTX-a1b2c3d4e5f6 --output-format json

# 4. Save evidence to temp file (via Write tool)
cat > /tmp/evidence.json <<EOF
{
  "code_locations": [...],
  "vulndoc_reference": {...},
  "reasoning_steps": [...],
  "vql_queries": [...]
}
EOF

# 5. Run CLI command (via Bash tool)
uv run alphaswarm findings create \
  --context-bead-id "CTX-a1b2c3d4e5f6" \
  --vuln-class "reentrancy/classic" \
  --severity "critical" \
  --confidence "likely" \
  --confidence-reason "Clear read-call-write pattern, no guard detected" \
  --evidence-file /tmp/evidence.json \
  --pool-id audit-2026-01 \
  --output-format yaml

# 6. Update context bead (via Bash tool)
uv run alphaswarm beads update CTX-a1b2c3d4e5f6 --add-finding VKG-x1y2z3a4b5c6

# 7. Report output (return to user/orchestrator)
status: success
finding_bead_id: VKG-x1y2z3a4b5c6
severity: critical
confidence: likely
next_steps:
  verification_required: true
```

---

## CLI Commands Reference

**Finding Creation:**
```bash
uv run alphaswarm findings create \
  --context-bead-id {context_bead_id} \
  --vuln-class {vuln_class} \
  --severity {severity} \
  --confidence {confidence} \
  --confidence-reason {reason} \
  --evidence-file {path} \
  --pool-id {pool_id} \
  --output-format yaml
```

**Context Bead Update:**
```bash
uv run alphaswarm beads update {context_bead_id} \
  --add-finding {finding_bead_id}
```

**Finding Verification:**
```bash
# List findings
uv run alphaswarm findings list --pool-id {pool_id}

# Show finding details
uv run alphaswarm findings show {finding_bead_id}

# Verify finding exists
test -f .vrs/findings/{pool_id}/{finding_bead_id}.yaml
```

---

## Quality Checklist

Before reporting success, verify:

- [ ] Discovery result loaded successfully
- [ ] Evidence chain validated (all required fields)
- [ ] Code locations: >= 1 location
- [ ] Reasoning steps: >= 2 steps
- [ ] VQL queries: >= 1 query
- [ ] Vulndoc reference: valid path
- [ ] Confidence: valid enum value
- [ ] Confidence reasoning: explicit justification
- [ ] Context bead exists and is valid
- [ ] Evidence saved to temporary file
- [ ] CLI command executed successfully
- [ ] Finding bead file exists
- [ ] Context bead updated with finding reference
- [ ] Structured output returned to orchestrator

If all checks pass → Report success
If any check fails → Report error with specific missing/invalid field

---

**VRS Create Bead (Finding) - Part of Phase 5.5 (Agent Execution & Context Enhancement)**
*Created: 2026-01-22*
