# VRS Skills - BSKG Vulnerability Research System

**VRS** = **V**KG **V**ulnerability **R**esearch **S**ystem

This directory contains skills for automated vulnerability discovery, knowledge management, and test generation within the AlphaSwarm.sol framework.

## Prefix Rationale

The `vrs:` prefix was chosen in Phase 6 rebrand decision to:
- Distinguish vulnerability research skills from general BSKG operations
- Enable clear namespace separation (`vkg:*` for core operations, `vrs:*` for research)
- Support future skill categorization and discovery

Reference: `.planning/phases/06-release-preparation/06-CONTEXT.md`

## Skill Invocation Model

**IMPORTANT: How Skills Work**

Skills in AlphaSwarm.sol are **documentation files that define agent behavior**. They are NOT separate executable programs or plugins.

**When a user invokes a skill:**

1. User types: `/vrs-discover`
2. Claude Code (the agent) loads: `.claude/skills/vrs/discover.md`
3. Agent follows the documented workflow in that file
4. Agent uses **standard tools** (Bash, Read, Write, etc.) to execute the workflow

**Example:**

```markdown
# In discover.md skill file:
"Run vulndocs list command via Bash tool"

# Agent executes:
Bash tool with command: uv run alphaswarm vulndocs list --json
```

**CLI Commands Are Invoked via Bash Tool:**

Skills document WHICH commands to run, but the agent uses the standard Bash tool to execute them. There is no separate "skill execution engine" - skills ARE prompts that guide agent behavior.

## Available Skills

### `/vrs-discover`

**Purpose:** Automated vulnerability discovery via Exa search.

**What it does:**
1. Loads current VulnDocs coverage
2. Searches web for new vulnerabilities using Exa MCP
3. Filters results for relevance (Haiku for cost efficiency)
4. Compares against existing coverage
5. Outputs structured recommendations

**When to use:**
- "Find new vulnerabilities"
- "Search for oracle attacks 2025"
- "Discover missing vulnerability patterns"

**Model:** Sonnet 4.5 (coordinator) + Haiku 4.5 (filtering)

**Outputs:** YAML discovery report at `.vrs/discovery/report-{timestamp}.yaml`

**Key feature:** Never adds without human confirmation - only suggests.

---

### `/vrs-add-vulnerability`

**Purpose:** Add new vulnerability to VulnDocs framework with proper structure.

**What it does:**
1. Gathers inputs (category, subcategory, severity, description)
2. Checks for duplicate entries
3. Creates folder structure via `vulndocs scaffold` CLI command
4. Populates templates with Phase 7 test generation fields
5. Validates structure and content
6. Reports next steps (patterns, tests)

**When to use:**
- "Add new oracle vulnerability"
- "Create entry for chainlink stale price"
- After approving `/vrs-discover` findings

**Model:** Sonnet 4.5

**Key fields populated:**
- `semantic_triggers` - BSKG operations for detection
- `vql_queries` - Example VQL queries
- `graph_patterns` - Vulnerable vs. safe patterns
- `reasoning_template` - Detection pseudocode

**Validation:** Always runs `vulndocs validate` before completion.

---

### `/vrs-research`

**Purpose:** Guided vulnerability research on specific topics.

**What it does:**
1. Parses research request (topic, scope, depth)
2. Researches using Exa search and existing VulnDocs
3. Synthesizes findings into vulnerability patterns
4. Maps to semantic operations and graph patterns
5. Suggests integration actions (new entry, update, pattern)
6. Reports with comprehensive references

**When to use:**
- "Research ERC-4626 vault vulnerabilities"
- "Investigate MEV attacks in AMMs"
- "Deep dive on oracle manipulation techniques"

**Model:** Sonnet 4.5

**Outputs:** Research report at `.vrs/research/report-{timestamp}.yaml`

**Key feature:** User-directed deep investigation vs. automated discovery.

---

### `/vrs-test-pattern`

**Purpose:** Pattern testing and validation against real-world projects.

**What it does:**
1. Selects test corpus (DVDeFi, Code4rena, benchmarks)
2. Builds knowledge graphs via `build-kg` CLI command
3. Runs pattern queries
4. Validates matches against ground truth
5. Calculates precision/recall metrics
6. Reports FP/FN for refinement

**When to use:**
- "Test pattern accuracy"
- "Validate reentrancy-classic pattern"
- Before promoting pattern from draft to ready
- After pattern refinement to verify improvement

**Model:** Sonnet 4.5

**Outputs:** Test report at `.vrs/test-results/{pattern-id}-{timestamp}.yaml`

**Key feature:** Identifies specific false positives and false negatives with suggested fixes.

---

### `/vrs-graph-retrieve`

**Purpose:** Evidence-first graph retrieval with complex VQL queries.

**What it does:**
1. Translates intent into VQL or structured graph queries
2. Retrieves minimal, high-signal context with evidence refs
3. Surfaces omissions and unknowns (taint/guard/path gaps)
4. Supports pattern-scoped label focus + counter-signals
5. Returns a compact retrieval pack for LLM reasoning

**When to use:**
- "Find source->sink vulnerable paths"
- "Need path-qualified ordering evidence"
- "Retrieve graph context for a specific pattern"
- "Run complex VQL with explain mode"

**Model:** Sonnet 4.5

**Outputs:** Retrieval pack in the response (evidence refs + omissions)

**Key feature:** Evidence-first, no manual code reading.

---

### `/vrs-refine`

**Purpose:** Pattern improvement based on test feedback.

**What it does:**
1. Loads target pattern and associated vulndoc
2. Analyzes test failures (FP/FN)
3. Proposes refinements to pattern conditions
4. Tests refinements against corpus
5. Updates pattern YAML and vulndoc metrics
6. Tracks before/after precision/recall

**When to use:**
- "Refine pattern after test failures"
- "Improve precision on reentrancy-classic"
- After `/vrs-test-pattern` reveals issues
- To reduce false positives while maintaining recall

**Model:** Opus 4.5 (quality-critical)

**Outputs:** Refinement report at `.vrs/refinement/report-{pattern-id}-{timestamp}.yaml`

**Key rules:**
- Never reduce recall below 0.70
- Always test before committing changes
- Mark as draft if precision < 0.70
- Use semantic operations, not function names

---

### `/vrs-merge-findings`

**Purpose:** Consolidate similar or duplicate vulnerability entries.

**What it does:**
1. Identifies similar/duplicate vulnerability entries
2. Analyzes semantic overlap (triggers, patterns, reasoning)
3. Proposes merge strategy with similarity scores
4. Consolidates content into unified entry
5. Validates merged result
6. Preserves all unique information

**When to use:**
- "Merge similar vulnerabilities"
- "Consolidate oracle category findings"
- "Reduce redundancy in VulnDocs"

**Model:** Sonnet 4.5

**Outputs:** Merge report at `.vrs/merges/report-{timestamp}.yaml`

**Key feature:** Multi-dimensional similarity analysis with user confirmation required.

---

### `/vrs-generate-tests`

**Purpose:** Generate Phase 7 test cases from vulndoc reasoning templates.

**What it does:**
1. Loads vulndoc (index.yaml, reasoning_template, exploits)
2. Generates test contracts (vulnerable, safe, adversarial, edge cases)
3. Creates test assertions and VQL queries
4. Outputs properly structured test files
5. Updates vulndoc test_coverage
6. Validates test quality

**When to use:**
- "Generate tests for reentrancy/classic"
- "Create Phase 7 tests for oracle/stale-data"
- "Build test corpus for oracle category"

**Model:** Sonnet 4.5

**Outputs:** Test contracts at `tests/contracts/{category}/{subcategory}/`, test files at `tests/test_{category}_{subcategory}.py`

**Key feature:** All three quality focuses (semantic complexity, real-world patterns, adversarial scenarios).

---

### `/vrs-create-bead-context-merge`

**Purpose:** Create bead from verified context-merge output.

**What it does:**
1. Validates merge and verification results
2. Extracts required fields from context bundle
3. Creates bead via CLI command
4. Verifies bead creation success
5. Reports bead ID to orchestrator

**When to use:**
- "Create bead from context-merge result"
- After context-merge agent + verifier complete
- Before spawning vuln-discovery agent

**Model:** Sonnet 4.5

**Outputs:** Bead YAML at `.vrs/beads/{pool_id}/{bead_id}.yaml`

**Key feature:** Ensures proper validation, tracking, and integration with orchestration layer.

---

### `/vrs-create-bead-finding`

**Purpose:** Create finding bead from vuln-discovery agent output.

**What it does:**
1. Validates evidence chain completeness
2. Links finding to originating context bead
3. Creates finding bead via CLI
4. Updates context bead with finding reference
5. Reports finding to orchestrator for verification routing

**When to use:**
- "Create finding bead from discovery result"
- After vuln-discovery identifies potential vulnerability
- Before reporting to orchestrator for verification

**Model:** Sonnet 4.5

**Outputs:** Finding bead YAML at `.vrs/findings/{pool_id}/{finding_bead_id}.yaml`

**Key feature:** Complete evidence chain validation (code locations, vulndoc reference, reasoning steps, VQL queries, protocol context).

---

### `/vrs-vql-help`

**Purpose:** On-demand VQL syntax and query examples for agents.

**What it does:**
1. Provides VQL syntax reference
2. Shows semantic operation usage
3. Gives vulnerability-specific query examples
4. Explains common pitfalls

**When to use:**
- "Help me query for reentrancy"
- "What VQL syntax do I need?"
- "Show me oracle manipulation queries"
- Agent needs to formulate VQL query

**Model:** Haiku 4.5 (fast, cost-efficient)

**Outputs:** Text response with syntax and examples (under 500 tokens)

**Key feature:** Fast reference enabling agents to formulate correct graph queries without full VQL documentation.

---

## Workflow Diagram

The VRS skills support two main workflows:

### Workflow A: Vulnerability Knowledge Development

The VRS skills form an iterative improvement cycle:

```
Discovery/Research → Creation → Testing → Refinement → Testing
    ↓        ↓          ↓          ↓           ↓           ↓
discover  research → add-vuln → test-pat → refine → test-pat
                         │          │          ↑           │
                         │          │          │___________│
                         │          │        (iterate until
                         │          │         quality met)
                         ↓          ↓
                   generate-tests  merge-findings
                         ↓              ↓
                   Phase 7 corpus   Consolidation

Quality Gates:
- draft:     precision < 0.70 OR recall < 0.50
- ready:     precision >= 0.70 AND recall >= 0.50
- excellent: precision >= 0.90 AND recall >= 0.85
```

### Workflow B: Agent Execution & Investigation (Phase 5.5)

The bead creation skills enable structured agent investigations:

```
Context-Merge Agent
    │
    ▼
Produces merge_result + verification_result
    │
    ▼
create-bead-context-merge → Context Bead (CTX-*)
    │
    ▼
Vuln-Discovery Agent investigates
    │
    ▼
Produces discovery_result with evidence_chain
    │                                      ┌─→ vql-help (on-demand)
    ▼                                      │
create-bead-finding → Finding Bead (VKG-*) ┘
    │
    ▼
Verification Agents (attacker/defender/verifier)
    │
    ▼
Verdict + Evidence Packet

Integration:
- create-bead-context-merge: Persists context for investigation tracking
- create-bead-finding: Captures evidence chain for verification
- vql-help: Assists agents with graph query formulation
```

**Typical Usage Flow:**

1. **Discover** new vulnerability via `/vrs-discover` (automated) or `/vrs-research` (guided)
2. **Add** approved finding via `/vrs-add-vulnerability`
3. **Test** initial pattern via `/vrs-test-pattern`
4. **Refine** if metrics below target via `/vrs-refine`
5. **Re-test** to verify improvement via `/vrs-test-pattern`
6. **Iterate** steps 4-5 until quality gate met
7. **Generate tests** for Phase 7 via `/vrs-generate-tests`
8. **Consolidate** similar findings periodically via `/vrs-merge-findings`

---

## Skill Summary Table

| Skill | Purpose | Model | Input | Output | When to Use |
|-------|---------|-------|-------|--------|-------------|
| `/vrs-discover` | Automated vulnerability discovery | Sonnet 4.5 + Haiku | Search terms (optional) | Discovery report | Weekly or on-demand for new vulnerabilities |
| `/vrs-add-vulnerability` | Create vulndoc structure | Sonnet 4.5 | Category, severity, description | Vulndoc folder | After approving discovery findings |
| `/vrs-research` | Guided vulnerability research | Sonnet 4.5 | Topic, scope, depth | Research report | User-directed deep investigations |
| `/vrs-test-pattern` | Validate pattern accuracy | Sonnet 4.5 | Pattern ID, test corpus | Test report + metrics | Before promoting pattern from draft |
| `/vrs-refine` | Improve pattern precision/recall | Opus 4.5 | Pattern ID, test results | Refined pattern + report | After test failures or low metrics |
| `/vrs-merge-findings` | Consolidate similar entries | Sonnet 4.5 | Category (optional) | Merge report | Periodic deduplication |
| `/vrs-generate-tests` | Create Phase 7 test cases | Sonnet 4.5 | Vulndoc target | Test contracts + files | Phase 7 test corpus building |
| `/vrs-create-bead-context-merge` | Create context bead | Sonnet 4.5 | Merge result + verification | Context bead YAML | After context-merge agent completes |
| `/vrs-create-bead-finding` | Create finding bead | Sonnet 4.5 | Discovery result + evidence | Finding bead YAML | After vuln-discovery identifies vulnerability |
| `/vrs-vql-help` | VQL syntax assistance | Haiku 4.5 | Query type or vuln class | Syntax + examples | When agent needs VQL query help |

## Model Tier Assignments

Skills use different Claude models based on task complexity and quality requirements:

### Haiku 4.5 (Fast, Cost-Efficient)
**Use for:** Mechanical tasks requiring minimal reasoning
- URL filtering and extraction in `/vrs-discover`
- VQL syntax reference and examples in `/vrs-vql-help`
- Simple data transformations
- Repetitive operations

**Cost:** ~$0.03 per 1M input tokens
**Rationale:** Most cost-effective for structured tasks

**Skills using Haiku:**
- `/vrs-discover` (URL filtering)
- `/vrs-vql-help` (syntax reference)

### Sonnet 4.5 (Balanced)
**Use for:** General-purpose research and reasoning
- Vulnerability discovery and research
- Pattern testing and validation
- Test generation
- Content consolidation

**Cost:** ~$0.30 per 1M input tokens
**Rationale:** Best balance of quality and cost for standard tasks

**Skills using Sonnet:**
- `/vrs-discover` (coordinator)
- `/vrs-add-vulnerability`
- `/vrs-research`
- `/vrs-test-pattern`
- `/vrs-merge-findings`
- `/vrs-generate-tests`
- `/vrs-create-bead-context-merge`
- `/vrs-create-bead-finding`

### Opus 4.5 (Premium Quality)
**Use for:** Complex reasoning requiring highest quality
- Novel attack vector discovery
- Pattern refinement (quality-critical)
- Verification and quality gates
- Complex vulnerability analysis

**Cost:** ~$1.50 per 1M input tokens
**Rationale:** Justified for tasks where quality directly impacts security

**Skills using Opus:**
- `/vrs-refine` (pattern improvement is quality-critical)

### When to Escalate

**Haiku → Sonnet:**
- Task requires semantic reasoning
- Need to synthesize information from multiple sources
- Output quality affects downstream work

**Sonnet → Opus:**
- Pattern precision/recall below targets (< 0.70/0.50)
- Novel vulnerability requiring deep analysis
- Final verification before production use
- User explicitly requests higher quality

---

## Relationship to VulnDocs Framework

Skills interact with the VulnDocs framework located at `vulndocs/` (root level).

**VulnDocs Structure:**
```
vulndocs/
├── .meta/
│   ├── templates/        # Skeleton templates (pattern.yaml, index.yaml, etc.)
│   └── instructions/     # Maintenance guidance
├── oracle/
│   ├── price-manipulation/
│   │   ├── index.yaml
│   │   ├── overview.md
│   │   ├── detection.md
│   │   ├── verification.md
│   │   ├── exploits.md
│   │   └── patterns/*.yaml  # Patterns co-located with vulndoc
│   └── stale-price/
├── reentrancy/
└── access-control/
```

**Skills use CLI commands:**
- `uv run alphaswarm vulndocs list` - List all vulnerabilities
- `uv run alphaswarm vulndocs scaffold` - Create new structure
- `uv run alphaswarm vulndocs validate` - Validate content
- `uv run alphaswarm vulndocs info` - Framework statistics

All CLI commands are invoked by agents via the Bash tool.

## Phase 7 Integration

Skills in this directory prepare vulnerabilities for Phase 7 test generation by:

1. **Semantic Triggers** (`semantic_triggers` in index.yaml)
   - BSKG operations that indicate vulnerability presence
   - Example: `[READS_ORACLE, MISSING_STALENESS_CHECK]`

2. **VQL Queries** (`vql_queries` in index.yaml)
   - Example queries agents can run against knowledge graph
   - Example: `"FIND functions WHERE reads_oracle AND NOT checks_timestamp"`

3. **Graph Patterns** (`graph_patterns` in index.yaml)
   - Visual representation of vulnerable vs. safe patterns
   - Example: `oracle_read -> calculation -> state_write`

4. **Reasoning Templates** (`reasoning_template` in index.yaml)
   - Pseudocode for detection logic
   - Used by test generation to create semantic tests

These fields enable Phase 7 to generate:
- Semantically complex tests (graph-based reasoning required)
- Real-world patterns (derived from exploits)
- Adversarial cases (obfuscation, edge cases)

## Knowledge Access Patterns

**Agents MUST use graph queries, not manual code reading:**

✅ **Correct:**
```vql
FIND functions WHERE
  reads_oracle
  AND uses_external_value_in_calculation
  AND NOT checks_timestamp
```

❌ **Incorrect:**
```python
# Manual code reading
for func in contract.functions:
    if "getPrice" in func.name:
        # Check code manually
```

**Why:** Graph-based detection is:
- Name-agnostic (semantic operations)
- Consistent across agents
- Scales to large codebases
- Enables automated reasoning

## Best Practices

### Graph-First Enforcement
✅ **Always** use BSKG semantic operations for detection
✅ **Always** write VQL queries instead of manual code analysis
✅ **Always** validate patterns against graph structure

❌ **Never** rely on function/variable names
❌ **Never** tell agents to "read source code directly"
❌ **Never** use string matching for vulnerability detection

### Dense Context Over Verbose
✅ **Do:** Write condensed exploits.md entries (1-2 lines per exploit)
✅ **Do:** Use semantic triggers and reasoning templates
✅ **Do:** Focus on "what to look for" not "why it's bad"

❌ **Don't:** Write long narratives about vulnerability impact
❌ **Don't:** Duplicate information across files
❌ **Don't:** Include unnecessary background in detection logic

### Always Validate After Changes
✅ **After adding vulnerability:** Run `vulndocs validate`
✅ **After modifying pattern:** Run `/vrs-test-pattern`
✅ **After refinement:** Verify precision/recall improved
✅ **Before promoting to ready:** Ensure metrics meet thresholds

### Quality Gates
Pattern quality levels:
- **draft**: precision < 0.70 OR recall < 0.50
- **ready**: precision >= 0.70 AND recall >= 0.50
- **excellent**: precision >= 0.90 AND recall >= 0.85

**Never promote a pattern from draft to ready without testing.**

## Quick Reference

### Common Invocations

```bash
# Discover new vulnerabilities
/vrs-discover "oracle manipulation 2025"

# Add approved finding
/vrs-add-vulnerability

# Research specific topic
/vrs-research "ERC-4626 vault vulnerabilities"

# Test pattern accuracy
/vrs-test-pattern oracle-001-stale-price

# Refine draft pattern
/vrs-refine oracle-001-stale-price

# Generate Phase 7 tests
/vrs-generate-tests oracle/stale-price

# Merge similar findings
/vrs-merge-findings oracle
```

### Expected Outputs

| Skill | Output Location | Format |
|-------|----------------|--------|
| discover | `.vrs/discovery/report-{timestamp}.yaml` | YAML report |
| add-vulnerability | `vulndocs/{category}/{subcategory}/` | Folder structure |
| research | `.vrs/research/report-{timestamp}.yaml` | YAML report |
| test-pattern | `.vrs/test-results/{pattern-id}-{timestamp}.yaml` | YAML + metrics |
| refine | `.vrs/refinement/report-{pattern-id}-{timestamp}.yaml` | YAML + before/after |
| merge-findings | `.vrs/merges/report-{timestamp}.yaml` | YAML report |
| generate-tests | `tests/contracts/{category}/{subcategory}/` | Test files |
| create-bead-context-merge | `.vrs/beads/{pool_id}/{bead_id}.yaml` | Context bead YAML |
| create-bead-finding | `.vrs/findings/{pool_id}/{finding_bead_id}.yaml` | Finding bead YAML |
| vql-help | (response text) | Text output |

## Completed Skills

### Phase 5.4 VRS Skills - Knowledge Development

| Skill | Purpose | Status | Plan |
|-------|---------|--------|------|
| `/vrs-discover` | Automated vulnerability discovery via Exa | ✅ COMPLETE | 05.4-05 |
| `/vrs-add-vulnerability` | Create vulndoc structure with validation | ✅ COMPLETE | 05.4-05 |
| `/vrs-test-pattern` | Validate patterns against real projects | ✅ COMPLETE | 05.4-06 |
| `/vrs-refine` | Improve draft patterns/vulndocs | ✅ COMPLETE | 05.4-06 |
| `/vrs-research` | Guided research on specific topic | ✅ COMPLETE | 05.4-07 |
| `/vrs-merge-findings` | Deduplicate similar findings | ✅ COMPLETE | 05.4-07 |
| `/vrs-generate-tests` | Create Phase 7-ready test cases | ✅ COMPLETE | 05.4-07 |

**Subtotal:** 7 skills across 3 plans (05.4-05, 05.4-06, 05.4-07)

### Phase 5.5 VRS Skills - Agent Execution & Context Enhancement

| Skill | Purpose | Status | Plan |
|-------|---------|--------|------|
| `/vrs-create-bead-context-merge` | Create bead from context-merge output | ✅ COMPLETE | 05.5-04 |
| `/vrs-create-bead-finding` | Create finding bead with evidence chain | ✅ COMPLETE | 05.5-04 |
| `/vrs-vql-help` | On-demand VQL syntax assistance | ✅ COMPLETE | 05.5-04 |

**Subtotal:** 3 skills in 1 plan (05.5-04)

### Phase 5.11 VRS Skills - Economic Context & Game-Theoretic Analysis

| Skill | Purpose | Status | Plan |
|-------|---------|--------|------|
| `/vrs-protocol-dossier` | Build protocol dossier from docs/audits/config | NEW | 05.11-05 |
| `/vrs-passport` | Generate contract passports + lifecycle stages | NEW | 05.11-05 |
| `/vrs-policy-diff` | Compare expected policy vs access-control graph | NEW | 05.11-05 |
| `/vrs-econ-probes` | Run economic probes and record evidence refs | NEW | 05.11-05 |
| `/vrs-misconfig-radar` | Scan for known misconfiguration patterns | NEW | 05.11-05 |
| `/vrs-context-refresh` | Detect drift and expire stale facts | NEW | 05.11-05 |
| `/vrs-attack-ev` | Compute game-theoretic expected value of attack | NEW | 05.11-05 |
| `/vrs-causal-trace` | Build and validate causal exploitation chains | NEW | 05.11-05 |
| `/vrs-counterfactual` | Explore "what if" scenarios for mitigations | NEW | 05.11-05 |
| `/vrs-cascade-risk` | Analyze cross-protocol cascade failures | NEW | 05.11-05 |
| `/vrs-loss-amplify` | Compute loss amplification from causal edges | NEW | 05.11-05 |

**Subtotal:** 11 skills in 1 plan (05.11-05)

**Total:** 21 VRS skills across 5 plans

## Development Notes

**When adding new VRS skills:**

1. Follow existing skill format (YAML frontmatter + markdown body)
2. Include "CRITICAL: Invocation Model" section explaining agent execution
3. Document all CLI commands via Bash tool invocation
4. Specify model tier for cost optimization
5. Add entry to this README
6. Update CLAUDE.md with skill listing

**Skill File Structure:**
```yaml
---
name: vrs-{skill-name}
description: |
  Brief description
slash_command: vrs:{skill-name}
context: fork
tools:
  - Read
  - Write
  - Bash(uv run alphaswarm*)
model_tier: sonnet-4.5
---

# Skill Documentation

**CRITICAL: Invocation Model**
[Explanation of how agent executes this skill]

## Purpose
[What problem this solves]

## How to Invoke
[Usage examples]

## Execution Workflow
[Detailed step-by-step process]

## Key Rules
[Important constraints and guidelines]
```

## VRS Agents

VRS agents are defined in `src/alphaswarm_sol/skills/shipped/agents/` (shipped) and `.claude/subagents/` (development).

**New in Phase 7.1.2:**
- **vrs-secure-reviewer** (claude-sonnet-4.5) - Creative attack thinking + adversarial skepticism with strict evidence-first and graph-first reasoning. Operates in two modes: creative (attack discovery) and adversarial (claim refutation). Output contract: `schemas/secure_reviewer_output.json`. Reference: `docs/reference/secure-reviewer.md`.

## Related Documentation

- **VulnDocs Framework:** `vulndocs/` directory
- **Phase 5.4 Context:** `.planning/phases/05.4-vulndocs-patterns-unification/05.4-CONTEXT.md`
- **VKG Skills:** `.claude/skills/vkg/` (core audit skills)
- **Pattern Forge:** `.claude/skills/pattern-forge/` (pattern development)
- **Test Builder:** `.claude/skills/test-builder/` (test authoring)
- **Secure Reviewer:** `docs/reference/secure-reviewer.md` (evidence-first review agent)

---

*VRS Skills - Part of AlphaSwarm.sol Phase 5.4 (VulnDocs-Patterns Unification)*
*Created: 2026-01-22*
