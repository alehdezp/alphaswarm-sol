# VulnDocs - Unified Vulnerability Knowledge Framework

**Version:** 1.1 (Phase 5.7)
**Status:** Unified structure complete, data quality improvement ongoing

## Purpose

VulnDocs is the **single source of truth** for vulnerability knowledge in AlphaSwarm.sol. It unifies:
- Vulnerability documentation (detection, verification, exploits)
- Pattern definitions (graph-based detection logic)
- Test generation support (Phase 7 semantic triggers and reasoning templates)

All vulnerability knowledge lives here in a structured, LLM-optimized format.

## Folder Structure

```
vulndocs/
├── .meta/                         # Meta files (templates, instructions)
│   ├── templates/                 # Skeleton templates for new entries
│   │   ├── category.yaml         # New category template
│   │   ├── subcategory/          # Subcategory folder template
│   │   │   └── index.yaml        # Template for index.yaml
│   │   ├── pattern.yaml          # Pattern template
│   │   └── provenance.yaml       # Provenance tracking template
│   └── instructions/              # Per-section maintenance guidance
│       ├── index.md              # How to write index.yaml
│       ├── detection.md          # How to write detection.md
│       ├── verification.md       # How to write verification.md
│       ├── exploits.md           # How to write exploits.md
│       └── patterns.md           # How to write patterns
│
├── category/                      # Vulnerability category (e.g., reentrancy, oracle)
│   ├── overview.md               # Category overview (optional)
│   ├── subcategory/              # Vulnerability subcategory (e.g., classic, read-only)
│   │   ├── index.yaml            # REQUIRED: Machine-readable metadata
│   │   ├── overview.md           # Optional: Human-readable description
│   │   ├── detection.md          # Optional: Detection approach (graph-first)
│   │   ├── verification.md       # Optional: Verification workflow
│   │   ├── exploits.md           # Optional: Real-world exploits (condensed)
│   │   └── patterns/             # Embedded patterns for this vulnerability
│   │       ├── pattern-001.yaml
│   │       └── pattern-002.yaml
│   └── ...
└── ...
```

## Key Concepts

### 1. Co-Located Patterns
Patterns are **embedded inside vulnerability folders**, not in a separate hierarchy. This enables:
- Better discoverability (patterns next to their vulndoc)
- Bidirectional linking (pattern → vulndoc, vulndoc → pattern)
- Simpler maintenance (no duplicate documentation)

### 2. Progressive Validation
**Minimal quality enforced, more files unlock more features:**

| Level | Requirements | Features Unlocked |
|-------|--------------|-------------------|
| MINIMAL | index.yaml with required fields | Basic detection |
| STANDARD | index.yaml + at least one .md file | Documentation |
| COMPLETE | All recommended .md files | Full knowledge |
| EXCELLENT | Patterns with test coverage | Validated patterns |

CI warns on incomplete entries but doesn't block.

### 3. Graph-First Enforcement
**Agents MUST use BSKG graph queries, NOT manual code reading.**

All detection logic is based on:
- BSKG semantic operations (e.g., `TRANSFERS_VALUE_OUT`, `READS_ORACLE`)
- VQL queries (e.g., `FIND functions WHERE ...`)
- Graph patterns (e.g., `read -> call -> write`)

### 4. Phase 7 Test Generation Support
Every `index.yaml` includes fields for automated test generation:
- **semantic_triggers**: BSKG operations to look for
- **vql_queries**: Example queries for detection
- **graph_patterns**: Structural patterns in graph
- **reasoning_template**: Pseudocode logic for LLM reasoning

These fields enable Phase 7 to generate high-quality adversarial tests.

## Quick Start

### Add a New Category
```bash
# Copy template
cp vulndocs/.meta/templates/category.yaml vulndocs/new-category/

# Edit vulndocs/new-category/category.yaml
# Add subcategories
```

### Add a New Vulnerability
```bash
# Use CLI (recommended)
uv run alphaswarm vulndocs scaffold oracle price-manipulation

# Or manually copy template
cp -r vulndocs/.meta/templates/subcategory vulndocs/oracle/price-manipulation/

# Edit vulndocs/oracle/price-manipulation/index.yaml
```

### Add a Pattern
```bash
# Copy template
cp vulndocs/.meta/templates/pattern.yaml vulndocs/oracle/price-manipulation/patterns/oracle-001.yaml

# Edit pattern with detection logic
# CRITICAL: Set vulndoc field to link back to vulnerability folder
```

### Validate Structure
```bash
# Validate entire framework
uv run alphaswarm vulndocs validate vulndocs/

# Validate specific category
uv run alphaswarm vulndocs validate vulndocs/oracle/

# Check framework info
uv run alphaswarm vulndocs info
```

## Validation

Validate the entire framework:
```bash
uv run alphaswarm vulndocs validate vulndocs/
```

**Progressive validation levels:**
- **MINIMAL**: Required fields present in index.yaml
- **STANDARD**: At least one .md file exists
- **COMPLETE**: All recommended .md files present
- **EXCELLENT**: Patterns with test coverage

**Validation suggests:**
- Missing files
- Exa research opportunities when content gaps detected
- Pattern quality improvements

## Agent Skills

Skills for maintaining and improving VulnDocs are located in `.claude/skills/vrs/`:

| Skill | Purpose | Model | When to Use |
|-------|---------|-------|-------------|
| `/vrs-discover` | Automated Exa search for new vulnerabilities | Sonnet 4.5 + Haiku 4.5 | Weekly or on-demand |
| `/vrs-research` | Guided research for specific topics | Sonnet 4.5 | User-directed investigation |
| `/vrs-refine` | Improve patterns, generate tests, fix failures | Opus 4.5 | After test failures |
| `/vrs-add-vulnerability` | Add new vulnerability with proper structure | Sonnet 4.5 | After approving findings |
| `/vrs-merge-findings` | Deduplicate and merge similar findings | Sonnet 4.5 | Periodic deduplication |
| `/vrs-generate-tests` | Create Phase 7-ready test cases | Sonnet 4.5 | Phase 7 preparation |
| `/vrs-test-pattern` | Validate patterns against real projects | Sonnet 4.5 | Before promoting patterns |

**Skill Invocation Model:**
Skills are documentation files that guide agent behavior. When you invoke `/vrs-discover`, Claude Code loads `.claude/skills/vrs/discover.md` and follows its workflow using standard tools (Bash, Read, Write).

**CLI commands are invoked via Bash tool:**
- Skills document WHICH commands to run
- Agent executes them via Bash tool
- No separate "skill execution engine"

**Model tier assignments:**
- **Haiku 4.5**: Mechanical tasks (URL filtering, extraction)
- **Sonnet 4.5**: Research, reasoning, pattern refinement
- **Opus 4.5**: Novel attack vectors, quality gates, verification

See `.claude/skills/vrs/README.md` for complete skill documentation.

## Phase 7 Test Generation

`index.yaml` fields support automated test generation:

### semantic_triggers
VKG operations that indicate this vulnerability:
```yaml
semantic_triggers:
  - READS_EXTERNAL_VALUE
  - READS_ORACLE
  - USES_IN_CALCULATION
```

### vql_queries
Example queries for detection:
```yaml
vql_queries:
  - "FIND functions WHERE reads_oracle AND NOT has_staleness_check"
```

### graph_patterns
Structural patterns in graph:
```yaml
graph_patterns:
  - "external_price_read -> calculation -> state_write"
```

### reasoning_template
Pseudocode logic for LLM reasoning:
```yaml
reasoning_template: |
  1. Identify oracle reads (getPrice, latestAnswer, etc.)
  2. Trace value flow to calculations
  3. Check for manipulation windows (single-block, no TWAP)
  4. Verify bounds checking or staleness checks
```

**Test Quality Focus:**
1. **Semantic complexity**: Tests require graph-based reasoning, not name matching
2. **Real-world patterns**: Derived from actual exploits and audits
3. **Adversarial**: Obfuscation, edge cases, false-positive traps

## Design Principles

### 1. Framework-First
Build empty structure, templates, validation, and agents **before** migrating content.

### 2. Single Source of Truth
No duplicate knowledge. Patterns embedded in vulnerability folders.

### 3. LLM-Optimized
Dense context, semantic triggers, reasoning templates for effective LLM use.

### 4. Progressive Quality
Minimal quality enforced, incremental improvements encouraged.

### 5. Graph Operations
All detection uses BSKG queries. No manual code reading.

## File Requirements

### Required
- **index.yaml**: Every vulnerability subcategory MUST have this

### Recommended
- **overview.md**: Brief description (human-readable)
- **detection.md**: Detection approach (graph queries)
- **verification.md**: Verification workflow
- **exploits.md**: Real-world exploits (condensed)
- **patterns/**: At least one pattern YAML

### Optional
- Additional .md files for specific needs
- category/overview.md for category context

## Best Practices

### DO
✅ Use semantic operations (`TRANSFERS_VALUE_OUT`, not `transfer()`)
✅ Write VQL queries for detection
✅ Keep exploits.md condensed (one-line per exploit)
✅ Link patterns to vulndocs via `vulndoc:` field
✅ Include Phase 7 fields in index.yaml

### DON'T
❌ Use function names for detection
❌ Tell agents to "read source code"
❌ Write verbose exploit narratives
❌ Create patterns without vulndoc field
❌ Forget semantic_triggers and reasoning_template

## Migration Status

**Phase 5.7 - Content Migration Complete**

Structure is unified under `vulndocs/`:
- ✅ 18 vulnerability categories
- ✅ 74+ subcategories with index.yaml
- ✅ 556+ patterns co-located with vulndocs
- ✅ Templates in `.meta/templates/`
- ✅ Instructions in `.meta/instructions/`

**Data Quality:**
- Some index.yaml files need field updates (missing required fields)
- Patterns are present and discoverable
- Framework correctly validates and reports issues

**Legacy Paths (Being Removed):**
- `patterns/` root directory - patterns moved to `vulndocs/*/*/patterns/`
- `knowledge/vulndocs/` - content merged into `vulndocs/`
- `vulndocs/_templates/` - moved to `vulndocs/.meta/templates/`
- `vulndocs/_instructions/` - moved to `vulndocs/.meta/instructions/`

## Architecture Integration

VulnDocs integrates with:
- **Pattern Engine**: Loads patterns from `vulndocs/*/patterns/*.yaml`
- **VQL Queries**: Uses semantic_triggers and vql_queries for detection
- **Test Generator**: Uses reasoning_template for Phase 7 test creation
- **Agent Skills**: `/vrs-*` skills for knowledge maintenance

## Documentation

- **Templates**: See `.meta/templates/` for skeleton files
- **Instructions**: See `.meta/instructions/` for per-section guidance
- **Example**: See `reentrancy/classic/` for reference vulnerability
- **Skills**: See `.claude/skills/vrs/README.md` for agent skill documentation
- **Verification**: See `.planning/phases/05.7-vulndocs-knowledge-consolidation/05.7-VERIFICATION.md`

## CLI Commands

All commands available via `uv run alphaswarm vulndocs`:

### Validation
```bash
# Validate entire framework
uv run alphaswarm vulndocs validate vulndocs/

# Validate specific category
uv run alphaswarm vulndocs validate vulndocs/oracle/

# Output formats
uv run alphaswarm vulndocs validate vulndocs/ --format json
uv run alphaswarm vulndocs validate vulndocs/ --format yaml
```

### Scaffolding
```bash
# Create new vulnerability structure
uv run alphaswarm vulndocs scaffold oracle price-manipulation

# Creates:
# vulndocs/oracle/price-manipulation/index.yaml
# vulndocs/oracle/price-manipulation/overview.md
# vulndocs/oracle/price-manipulation/detection.md
# vulndocs/oracle/price-manipulation/verification.md
# vulndocs/oracle/price-manipulation/exploits.md
# vulndocs/oracle/price-manipulation/patterns/
```

### Information
```bash
# Framework statistics
uv run alphaswarm vulndocs info

# Shows:
# - Total vulnerabilities
# - Validation level distribution
# - Pattern coverage
# - Test coverage

# List all vulnerabilities
uv run alphaswarm vulndocs list
uv run alphaswarm vulndocs list --json
uv run alphaswarm vulndocs list --category oracle
```

### Export
```bash
# Export labels/overlays
uv run alphaswarm vulndocs export vulndocs/oracle/ --format yaml
uv run alphaswarm vulndocs export vulndocs/oracle/ --format json
```

---

**Questions?** See `.meta/instructions/` for detailed per-section guidance.

**Contributing:** Follow templates and validation requirements. All PRs must pass validation (warnings allowed, errors block).

**License:** Same as AlphaSwarm.sol project.
