---
name: vrs-create-bead-context-merge
description: |
  Create a bead from verified context-merge output. This skill standardizes bead creation
  from context-merge agent results, ensuring proper validation, tracking, and integration
  with the orchestration layer.

  Invoke when:
  - Context-merge agent completes merge operation
  - Context-merge verifier passes validation
  - Before spawning vuln-discovery agent
  - Need to persist context for investigation tracking

  This skill:
  1. Validates merge and verification results
  2. Extracts required fields from context bundle
  3. Creates bead via CLI command
  4. Verifies bead creation success
  5. Reports bead ID to orchestrator

slash_command: vrs:create-bead-context-merge
context: fork

tools:
  - Read
  - Write
  - Bash(uv run alphaswarm beads*)

model_tier: sonnet

---

# VRS Create Bead (Context-Merge) Skill - Context Bead Creation

You are the **VRS Create Bead (Context-Merge)** skill, responsible for creating beads from verified context-merge output to enable proper investigation tracking and orchestration.

**CRITICAL: Invocation Model**
You are Claude Code, an agent that follows this skill documentation. When this skill says "run beads generate command," you invoke the Bash tool with `uv run alphaswarm beads generate`. This skill file IS the prompt that guides your behavior - you execute it using your standard tools (Bash, Read, Write).

## Purpose

- **Create context beads** from verified context-merge output
- **Ensure validation** before bead creation (merge + verification must pass)
- **Enable tracking** of investigation context across agent sessions
- **Link to orchestration** by providing bead IDs to pool orchestrator
- **Persist evidence** for future vuln-discovery and verification agents

## How to Invoke

```bash
/vrs-create-bead-context-merge
/vrs-create-bead-context-merge --pool-id audit-2026-01
/vrs-create-bead-context-merge --merge-result-file /tmp/merge-result.yaml
```

**Interactive mode** (default):
- Prompts for merge result location
- Guides through validation checks
- Creates bead with confirmation

**Quick mode** (with args):
- Provide merge result file path
- Faster for automated workflows

---

## Execution Workflow

### Phase 1: Validate Inputs

**Goal:** Confirm merge and verification results are valid before creating bead.

**Actions:**

1. **Locate merge result** (via Read tool or user input):
   ```bash
   # User provides path or default location
   merge_result_path = "/tmp/context-merge-result.yaml"
   ```

2. **Load and validate merge result** (via Read tool):
   ```bash
   cat {merge_result_path}
   ```

3. **Check merge success**:
   ```yaml
   merge_result:
     success: true  # REQUIRED
     bundle:
       vulnerability_class: "reentrancy/classic"
       protocol_name: "MyProtocol"
       target_scope: {...}
       # ... full context bundle
   ```

   **If `success != true`:** Report error, do NOT create bead

4. **Check verification result** (if exists):
   ```yaml
   verification_result:
     valid: true  # REQUIRED
     quality_score: 0.95
     warnings: []
   ```

   **If `valid != true`:** Report error, do NOT create bead

5. **Extract required fields**:
   - `vulnerability_class` - From bundle
   - `protocol_name` - From bundle
   - `target_scope` - From bundle (JSON serialized)
   - `verification_score` - From verification_result
   - `pool_id` - From orchestrator context or user input

**Validation Checklist:**

```python
required_checks = [
    merge_result.success == True,
    merge_result.bundle is not None,
    merge_result.bundle.vulnerability_class is not None,
    merge_result.bundle.protocol_name is not None,
]

if not all(required_checks):
    print("ERROR: Invalid merge result. Cannot create bead.")
    exit(1)
```

### Phase 2: Create Bead via CLI

**Goal:** Use CLI to create bead from validated merge result.

**Action: Run bead generation command via Bash tool**

```bash
uv run alphaswarm beads generate \
  --source context-merge \
  --vuln-class "{vulnerability_class}" \
  --protocol "{protocol_name}" \
  --bundle-file "{bundle_yaml_path}" \
  --verification-score {verification_score} \
  --pool-id "{pool_id}" \
  --output-format yaml
```

**Parameter Details:**

| Parameter | Source | Example |
|-----------|--------|---------|
| `--source` | Fixed value | `context-merge` |
| `--vuln-class` | `bundle.vulnerability_class` | `reentrancy/classic` |
| `--protocol` | `bundle.protocol_name` | `MyProtocol` |
| `--bundle-file` | Path to saved bundle YAML | `/tmp/bundle.yaml` |
| `--verification-score` | `verification_result.quality_score` | `0.95` |
| `--pool-id` | Orchestrator context or user input | `audit-2026-01` |
| `--output-format` | Fixed value | `yaml` |

**Before running CLI command:**

1. **Save bundle to temporary file** (via Write tool):
   ```bash
   # Extract bundle from merge result
   bundle_data = merge_result.bundle

   # Write to temp file
   cat > /tmp/context-bundle.yaml <<EOF
   {bundle_yaml_content}
   EOF
   ```

2. **Execute CLI command** (via Bash tool):
   ```bash
   uv run alphaswarm beads generate \
     --source context-merge \
     --vuln-class "reentrancy/classic" \
     --protocol "MyProtocol" \
     --bundle-file /tmp/context-bundle.yaml \
     --verification-score 0.95 \
     --pool-id audit-2026-01 \
     --output-format yaml
   ```

**Expected Output:**

```yaml
status: success
bead_id: CTX-a1b2c3d4e5f6
bead_path: .vrs/beads/audit-2026-01/CTX-a1b2c3d4e5f6.yaml
vulnerability_class: reentrancy/classic
protocol_name: MyProtocol
verification_score: 0.95
created_at: 2026-01-22T12:00:00Z
```

### Phase 3: Verify Creation

**Goal:** Confirm bead was created successfully and is accessible.

**Actions:**

1. **Check CLI command exit code**:
   ```bash
   if [ $? -ne 0 ]; then
     echo "ERROR: Bead creation failed"
     exit 1
   fi
   ```

2. **Verify bead file exists** (via Bash tool):
   ```bash
   test -f {bead_path} && echo "Bead file exists" || echo "ERROR: Bead file not found"
   ```

3. **Validate bead YAML structure** (via Read tool):
   ```bash
   cat {bead_path}
   ```

   Confirm required fields present:
   - `id` - Bead identifier (CTX-*)
   - `type` - Should be "context-merge"
   - `vulnerability_class`
   - `protocol_name`
   - `bundle` - Full context bundle
   - `created_at`
   - `status` - Should be "pending"

4. **Report bead ID to orchestrator**:
   ```yaml
   bead_creation_result:
     success: true
     bead_id: CTX-a1b2c3d4e5f6
     bead_path: .vrs/beads/audit-2026-01/CTX-a1b2c3d4e5f6.yaml
     ready_for_discovery: true
   ```

---

## Input Requirements

| Field | Required | Source | Example |
|-------|----------|--------|---------|
| `vulnerability_class` | Yes | `merge_result.bundle.vulnerability_class` | `reentrancy/classic` |
| `protocol_name` | Yes | `merge_result.bundle.protocol_name` | `MyProtocol` |
| `target_scope` | Yes | `merge_result.bundle.target_scope` | `{contracts: [...]}` |
| `bundle` | Yes | `merge_result.bundle` (serialized) | Full YAML bundle |
| `verification_score` | Yes | `verification_result.quality_score` | `0.95` |
| `pool_id` | No | Orchestrator context | `audit-2026-01` |

**If pool_id not provided:** Use `default` or prompt user

---

## Output Format

When bead creation succeeds, return:

```yaml
status: success
bead_id: CTX-a1b2c3d4e5f6
bead_path: .vrs/beads/audit-2026-01/CTX-a1b2c3d4e5f6.yaml
vulnerability_class: reentrancy/classic
protocol_name: MyProtocol
verification_score: 0.95
warnings: []
ready_for_discovery: true
```

**If warnings exist** (non-fatal):
```yaml
warnings:
  - "Verification score below 0.90 - consider re-running context-merge"
  - "Missing optional field: exploit_history"
```

---

## Error Handling

| Error | Condition | Action |
|-------|-----------|--------|
| Merge failed | `merge_result.success != true` | Report error, do NOT create bead |
| Verification failed | `verification_result.valid != true` | Report error, do NOT create bead |
| Missing bundle | `merge_result.bundle is None` | Report error, do NOT create bead |
| Missing required field | Any required field missing from bundle | Report error, list missing fields |
| CLI error | Command exit code != 0 | Report stderr output, retry once |
| Filesystem error | Bead file not created | Report error, check permissions |
| Invalid bead structure | Created bead missing required fields | Report error, delete invalid bead |

**Error Recovery Strategy:**

1. **For transient errors** (filesystem, CLI timeout):
   - Retry once after 2 seconds
   - If second failure, report to orchestrator

2. **For validation errors** (merge failed, missing fields):
   - Do NOT retry
   - Report to orchestrator with error details
   - Suggest re-running context-merge

3. **For partial creation** (file created but invalid):
   - Delete invalid bead file
   - Report error
   - Do NOT leave corrupt artifacts

---

## Integration Points

**Before this skill:**
1. Context-merge agent runs and produces `merge_result`
2. Context-merge verifier validates and produces `verification_result`
3. Orchestrator collects both results

**After this skill:**
1. Orchestrator reads bead ID from output
2. Orchestrator spawns vuln-discovery agent with bead ID
3. Vuln-discovery agent loads bead and uses context for investigation

**Orchestration Flow:**

```
Context-Merge Agent
    │
    ▼
Produces merge_result
    │
    ▼
Context-Merge Verifier
    │
    ▼
Produces verification_result
    │
    ▼
[THIS SKILL: Create Bead]
    │
    ▼
Bead stored at .vrs/beads/{pool_id}/{bead_id}.yaml
    │
    ▼
Orchestrator reads bead_id
    │
    ▼
Vuln-Discovery Agent spawned with bead_id
```

---

## Key Rules

### 1. Always Validate Before Creating

Never create a bead without validating:
- Merge success
- Verification pass (if verification ran)
- All required fields present

**Validation first, creation second.**

### 2. Use CLI Command, Not Direct File Write

Always use `uv run alphaswarm beads generate` instead of manually creating YAML files. This ensures:
- Proper bead ID generation
- Schema validation
- Index updates
- Proper permissions

### 3. Deletion Protection

**CRITICAL:** Sonnet agents (including this skill) CANNOT delete beads without Opus confirmation.

If bead creation fails and cleanup needed:
- Report to orchestrator
- Request Opus agent for cleanup
- Do NOT attempt `rm` or `beads clear`

### 4. Report to Orchestrator

After successful creation, ALWAYS return structured output with:
- `bead_id` - For orchestrator to track
- `bead_path` - For verification
- `ready_for_discovery: true` - Signal next step

### 5. Handle Pool Context

If `pool_id` provided:
- Use it for bead storage location
- Include in bead metadata
- Pass to CLI command

If NOT provided:
- Use `default` pool
- Warn user about missing pool context

---

## Example Invocation

```bash
# User invokes
/vrs-create-bead-context-merge --pool-id audit-2026-01

# You (Claude Code agent) execute:

# 1. Read merge result (via Read tool)
cat /tmp/context-merge-result.yaml

# 2. Validate (internal check)
# - merge_result.success == true ✓
# - bundle.vulnerability_class present ✓
# - bundle.protocol_name present ✓

# 3. Save bundle to temp file (via Write tool)
cat > /tmp/bundle.yaml <<EOF
vulnerability_class: reentrancy/classic
protocol_name: MyProtocol
...
EOF

# 4. Run CLI command (via Bash tool)
uv run alphaswarm beads generate \
  --source context-merge \
  --vuln-class "reentrancy/classic" \
  --protocol "MyProtocol" \
  --bundle-file /tmp/bundle.yaml \
  --verification-score 0.95 \
  --pool-id audit-2026-01 \
  --output-format yaml

# 5. Verify creation (via Bash tool)
test -f .vrs/beads/audit-2026-01/CTX-a1b2c3d4e5f6.yaml

# 6. Report output (return to user/orchestrator)
status: success
bead_id: CTX-a1b2c3d4e5f6
ready_for_discovery: true
```

---

## CLI Commands Reference

**Bead Generation:**
```bash
uv run alphaswarm beads generate \
  --source {source_type} \
  --vuln-class {vuln_class} \
  --protocol {protocol_name} \
  --bundle-file {path} \
  --verification-score {score} \
  --pool-id {pool_id} \
  --output-format yaml
```

**Bead Verification:**
```bash
# List beads
uv run alphaswarm beads list --pool-id {pool_id}

# Show bead details
uv run alphaswarm beads show {bead_id}

# Verify bead exists
test -f .vrs/beads/{pool_id}/{bead_id}.yaml
```

---

## Quality Checklist

Before reporting success, verify:

- [ ] Merge result validated (success == true)
- [ ] Verification result validated (valid == true)
- [ ] All required fields extracted
- [ ] Bundle saved to temporary file
- [ ] CLI command executed successfully
- [ ] Bead file exists at returned path
- [ ] Bead YAML structure valid
- [ ] Bead ID returned to orchestrator
- [ ] `ready_for_discovery` flag set

If all checks pass → Report success
If any check fails → Report error with details

---

**VRS Create Bead (Context-Merge) - Part of Phase 5.5 (Agent Execution & Context Enhancement)**
*Created: 2026-01-22*
