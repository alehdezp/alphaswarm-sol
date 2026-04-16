# Skill Tool Policies Reference

**Version:** 1.0
**Phase:** 07.1.2-skill-subagent-design-system
**Purpose:** Role-based tool gating and guardrail policies for skills and subagents

---

## Overview

Tool policies define which tools each role can use and what data they can access. These policies:

1. **Prevent unsafe tool usage** - Block dangerous operations for untrusted roles
2. **Enforce data boundaries** - Prevent access to secrets, credentials, protected files
3. **Enable cost control** - Require validation before expensive model usage
4. **Support evidence-first reasoning** - Enforce graph-first requirements per role

**Policy File:** `configs/skill_tool_policies.yaml`
**Schema:** `schemas/skill_tool_policy_v1.json`
**Validator:** `src/alphaswarm_sol/skills/guardrails.py`

---

## Role Definitions

### Role Properties

Each role has:

| Property | Description |
|----------|-------------|
| `description` | Role purpose and responsibilities |
| `model_tier` | Default model (haiku/sonnet/opus) |
| `allowed_tools` | List of permitted tools |
| `data_access` | File path access rules (allowed/forbidden) |
| `constraints` | Execution limits (reads, writes, budget, evidence) |

### Defined Roles

#### 1. Attacker
- **Purpose:** Exploit construction and vulnerability discovery
- **Model:** Opus (deep analysis)
- **Tools:** Read, Glob, Grep, BSKG queries, graph building, context viewing
- **Budget:** 8000 tokens
- **Constraints:** Graph-first required, evidence required, max 50 file reads

#### 2. Defender
- **Purpose:** Guard discovery and mitigation construction
- **Model:** Sonnet (standard reasoning)
- **Tools:** Read, Glob, Grep, BSKG queries, graph building, context viewing
- **Budget:** 6000 tokens
- **Constraints:** Graph-first required, evidence required, max 40 file reads

#### 3. Verifier
- **Purpose:** Evidence cross-checking and verdict synthesis
- **Model:** Opus (deep verification)
- **Tools:** Read, Glob, Grep, BSKG queries, graph building
- **Budget:** 8000 tokens
- **Constraints:** Graph-first required, evidence required, max 30 file reads

#### 4. Auditor
- **Purpose:** Skill quality assessment and validation
- **Model:** Sonnet (code review)
- **Tools:** Read, Glob, Grep, pytest, schema validation
- **Budget:** 6000 tokens
- **Constraints:** Evidence required, max 100 file reads (broad access for audits)

#### 5. Researcher
- **Purpose:** Vulnerability discovery and knowledge synthesis
- **Model:** Sonnet (research)
- **Tools:** Read, Glob, Grep, VulnDocs operations, BSKG queries, Exa web search
- **Budget:** 6000 tokens
- **Constraints:** Evidence required, max 80 file reads, max 10 web searches

#### 6. Triage
- **Purpose:** Initial assessment and routing
- **Model:** Haiku (fast, cost-efficient)
- **Tools:** Read, Glob, Grep, BSKG queries
- **Budget:** 3000 tokens
- **Constraints:** Graph-first required, max 20 file reads

#### 7. Orchestrator
- **Purpose:** Pool management and workflow coordination
- **Model:** Sonnet (coordination)
- **Tools:** Read, Glob, Grep, pool operations, BSKG queries, context operations
- **Budget:** 5000 tokens
- **Constraints:** Max 60 file reads

#### 8. Architect
- **Purpose:** Skill and subagent design
- **Model:** Sonnet (design)
- **Tools:** Read, Write, Edit, Glob, Grep, schema validation
- **Budget:** 6000 tokens
- **Constraints:** Max 100 reads, max 20 writes, cannot modify protected files

#### 9. Curator
- **Purpose:** Knowledge base management and corpus validation
- **Model:** Sonnet (curation)
- **Tools:** Read, Write, Edit, Glob, Grep, VulnDocs validation, pytest
- **Budget:** 6000 tokens
- **Constraints:** Evidence required, max 150 reads, max 50 writes

#### 10. Tester
- **Purpose:** Pattern and validation testing
- **Model:** Haiku (testing)
- **Tools:** Read, Glob, Grep, pytest, BSKG queries/building
- **Budget:** 4000 tokens
- **Constraints:** Max 80 file reads

---

## Tool Patterns

### File Operations
- `Read` - Read files from allowed paths
- `Write` - Create new files (architect, curator only)
- `Edit` - Modify existing files (architect, curator only)
- `Glob` - Find files by pattern
- `Grep` - Search file contents

### Command Execution
- `Bash(uv run alphaswarm query*)` - Query BSKG
- `Bash(uv run alphaswarm build-kg*)` - Build knowledge graph
- `Bash(uv run alphaswarm context*)` - Context operations
- `Bash(uv run alphaswarm orchestrate*)` - Pool management
- `Bash(uv run alphaswarm vulndocs*)` - VulnDocs operations
- `Bash(uv run pytest*)` - Run tests
- `Bash(python scripts/validate_skill_schema.py*)` - Validate schemas

### MCP Tools
- `mcp__exa-search__web_search_exa` - Deep web research (researcher only)

---

## Data Access Policies

### Allowed Paths (Common)
- `**/*.sol` - Solidity contracts
- `**/*.json` - JSON data files
- `**/*.toon` - TOON graph files
- `.vrs/**` - Graph cache
- `vulndocs/**` - Vulnerability knowledge
- `context/**` - Protocol context packs
- `docs/**` - Documentation
- `tests/**` - Test files

### Forbidden Paths (All Roles)
- `**/.env` - Environment variables
- `**/secrets/**` - Secrets directory
- `**/*key*` - Key files
- `**/*credential*` - Credential files

### Protected Files (Cannot Modify)
- `src/alphaswarm_sol/kg/builder_legacy.py`
- `src/alphaswarm_sol/beads/executor.py`

---

## Constraints

### File Access Limits

| Role | Max Reads | Max Writes | Rationale |
|------|-----------|------------|-----------|
| Attacker | 50 | - | Deep exploit analysis |
| Defender | 40 | - | Focused guard discovery |
| Verifier | 30 | - | Evidence validation only |
| Auditor | 100 | - | Broad audit coverage |
| Researcher | 80 | - | Knowledge synthesis |
| Triage | 20 | - | Fast initial assessment |
| Orchestrator | 60 | - | Workflow coordination |
| Architect | 100 | 20 | Skill design and creation |
| Curator | 150 | 50 | Corpus management |
| Tester | 80 | - | Pattern testing |

### Token Budgets

| Tier | Budget | Roles |
|------|--------|-------|
| Fast (Haiku) | 3000-4000 | Triage, Tester |
| Standard (Sonnet) | 5000-6000 | Defender, Auditor, Researcher, Orchestrator, Architect, Curator |
| Deep (Opus) | 8000 | Attacker, Verifier |

### Evidence Requirements

| Requirement | Roles |
|-------------|-------|
| **Evidence required** | Attacker, Defender, Verifier, Auditor, Researcher, Curator |
| **Evidence optional** | Triage, Orchestrator, Architect, Tester |

### Graph-First Requirements

| Requirement | Roles |
|-------------|-------|
| **Graph-first required** | Attacker, Defender, Verifier, Triage |
| **Graph-first optional** | Auditor, Researcher, Orchestrator, Architect, Curator, Tester |

---

## Escalation Rules

### Require Guardrail Validation

Execution requires approval from a validator role when:

| Condition | Validator | Reason |
|-----------|-----------|--------|
| `token_budget > 6000` | Triage | High token budget |
| `model_tier == opus` | Triage | Expensive model |
| `max_file_reads > 50` | Auditor | Broad file access |

### Block Execution

Execution is blocked entirely when:

| Condition | Reason |
|-----------|--------|
| `forbidden_path_access` | Attempted access to secrets, env vars, etc. |
| `tool_not_in_allowed_list` | Tool not permitted for this role |
| `evidence_required && !evidence_provided` | Missing required evidence |

---

## Usage

### Validate Skill Against Policy

```bash
# Load and validate a skill's tool usage
python -c "
from alphaswarm_sol.skills.guardrails import validate_tool_policy
result = validate_tool_policy('path/to/skill.md', role='attacker')
print(result)
"
```

### Check Policy for Role

```bash
# View policy for a specific role
python -c "
from alphaswarm_sol.skills.guardrails import load_tool_policy
policy = load_tool_policy()
import json
print(json.dumps(policy['roles']['attacker'], indent=2))
"
```

### Enforce During Orchestration

```python
from alphaswarm_sol.skills.guardrails import validate_tool_policy

# Before executing a skill
validation = validate_tool_policy(
    skill_path="skills/vrs-attacker.md",
    role="attacker"
)

if not validation["valid"]:
    raise ValueError(f"Tool policy violation: {validation['errors']}")
```

---

## Integration Points

### 1. Skill Schema Validation
- **Tool:** `scripts/validate_skill_schema.py`
- **Check:** Skill frontmatter `tools` array matches role's `allowed_tools`
- **Action:** Fail validation if disallowed tools present

### 2. Guardrail Policy Loader
- **Module:** `src/alphaswarm_sol/skills/guardrails.py`
- **Function:** `validate_tool_policy(skill_path, role)`
- **Returns:** `{"valid": bool, "errors": [], "warnings": []}`

### 3. Orchestration Layer
- **Module:** `src/alphaswarm_sol/orchestration/`
- **Hook:** Before bead execution
- **Action:** Validate role's tool policy, block if violations

---

## Examples

### Example 1: Valid Attacker Skill

```yaml
---
role: attacker
model: claude-opus-4-5
tools:
  - Read
  - Glob
  - Bash(uv run alphaswarm query*)
evidence_requirements:
  must_link_code: true
  cite_graph_nodes: true
  graph_first: true
---
```

**Validation:** ✅ PASS - All tools allowed, evidence requirements match

### Example 2: Invalid Attacker Skill

```yaml
---
role: attacker
model: claude-opus-4-5
tools:
  - Read
  - Write  # ❌ Not in allowed_tools for attacker
  - Bash(rm -rf*)  # ❌ Dangerous command
---
```

**Validation:** ❌ FAIL - `Write` not allowed, dangerous bash command

### Example 3: Escalation Trigger

```yaml
---
role: defender
model: claude-opus-4-5  # ❌ Defender default is sonnet
token_budget: 8000      # ❌ Exceeds defender budget (6000)
---
```

**Validation:** ⚠️ ESCALATION REQUIRED - Opus model + high budget requires triage approval

---

## Policy Maintenance

### Adding New Roles

1. Define role in `configs/skill_tool_policies.yaml`
2. Specify `allowed_tools`, `data_access`, `constraints`
3. Update `schemas/skill_tool_policy_v1.json` if needed
4. Document role in this reference
5. Update validator tests

### Modifying Role Permissions

1. Update `configs/skill_tool_policies.yaml`
2. Test with existing skills using that role
3. Update documentation
4. Run validation tests

### Adding Tool Patterns

1. Add pattern to role's `allowed_tools` array
2. Document pattern in this reference
3. Update schema validation if new tool type
4. Test with sample skills

---

## Anti-Patterns

### ❌ Overbroad Tool Permissions

**Bad:**
```yaml
allowed_tools:
  - Bash(*)  # Allows ANY bash command
```

**Good:**
```yaml
allowed_tools:
  - Bash(uv run alphaswarm query*)  # Specific command pattern
  - Bash(uv run pytest*)            # Specific command pattern
```

### ❌ Missing Evidence Requirements

**Bad:**
```yaml
constraints:
  evidence_required: false  # For verification role
```

**Good:**
```yaml
constraints:
  evidence_required: true   # All claims need evidence
```

### ❌ Unbounded File Access

**Bad:**
```yaml
constraints:
  max_file_reads: 999999  # Effectively unbounded
```

**Good:**
```yaml
constraints:
  max_file_reads: 50      # Reasonable limit
```

---

## Security Considerations

1. **Secrets Protection:** All roles forbidden from accessing `.env`, `secrets/`, credential files
2. **Protected Files:** `builder_legacy.py` and `executor.py` cannot be modified by any role
3. **Command Injection:** Only specific bash patterns allowed, not arbitrary commands
4. **Path Traversal:** Forbidden paths checked before allowing file access
5. **Cost Control:** Escalation rules prevent expensive model usage without validation

---

## Future Enhancements

1. **Dynamic Policy Loading:** Load policies from database instead of YAML
2. **Runtime Enforcement:** Hook into tool execution to enforce policies at runtime
3. **Audit Logging:** Log all tool usage and policy checks
4. **Policy Testing:** Automated tests for policy compliance
5. **Role Inheritance:** Define base roles and inherit permissions

---

## References

- **Policy File:** `configs/skill_tool_policies.yaml`
- **Schema:** `schemas/skill_tool_policy_v1.json`
- **Validator:** `src/alphaswarm_sol/skills/guardrails.py`
- **Skill Schema:** `docs/reference/skill-schema-v2.md`
- **Graph-First Template:** `docs/reference/graph-first-template.md`

---

**Version:** 1.0
**Last Updated:** 2026-01-29
**Phase:** 07.1.2-skill-subagent-design-system
