# Skill Registry Reference

**Version:** v1.0
**Last Updated:** 2026-01-29
**Purpose:** Single source of truth for skill versioning, lifecycle status, and deprecation policy

---

## Overview

The skill registry (`src/alphaswarm_sol/skills/registry.yaml`) tracks all VRS skills with versioning metadata, lifecycle status, and deprecation information. This enables safe skill evolution, clear migration paths, and discovery of shipped vs development skills.

### Key Benefits

- **Version tracking** - Know which version of a skill you're using
- **Lifecycle management** - Clear status (active, experimental, deprecated, sunset)
- **Deprecation transparency** - Know when skills will be removed
- **Migration guidance** - Replacement skills and migration notes
- **Discovery** - Find skills by category, status, or location

---

## Registry Structure

### Entry Schema

```yaml
- id: skill-id              # Unique identifier (kebab-case)
  name: "Skill Name"        # Human-readable name
  version: 1.0.0            # Semantic version (major.minor.patch)
  status: active            # Lifecycle status
  category: orchestration   # Category for organization
  description: "..."        # One-line description
  location:
    shipped: path/to/shipped.md  # Shipped location (null if dev-only)
    dev: path/to/dev.md           # Dev location (null if shipped-only)
  replaces: old-skill-id    # Skill this replaces (optional)
  deprecated_by: new-skill  # Skill deprecating this one (optional)
  sunset_date: 2026-06-01   # Removal date (optional, ISO 8601)
  migration_notes: "..."    # Migration guidance (optional)
```

### Lifecycle Status Values

| Status | Meaning | Action Required |
|--------|---------|-----------------|
| `active` | Production-ready, stable | Use freely |
| `experimental` | Under development, API may change | Use with caution, expect changes |
| `deprecated` | Marked for removal, replacement available | Migrate to replacement |
| `sunset` | Removed or scheduled for imminent removal | Stop using immediately |

### Categories

| Category | Purpose | Example Skills |
|----------|---------|----------------|
| `orchestration` | Workflow and pool management | audit, orch-spawn, orch-resume |
| `investigation` | Vulnerability analysis | investigate, verify, debate |
| `validation` | Testing and quality assurance | test-full, validate-vulndocs |
| `discovery` | Knowledge extraction | discover, research, ingest-url |
| `pattern-development` | Pattern creation and refinement | pattern-forge, refine, test-pattern |
| `tool-integration` | External tool coordination | tool-slither, tool-aderyn |
| `context` | Context extraction and analysis | context-pack, evidence-audit |
| `development` | Internal development tools | test-builder, agent-skillcraft |
| `legacy` | Deprecated legacy implementations | (to be migrated) |

---

## Deprecation Policy

### Lifecycle Stages

The deprecation workflow follows a **announce → warn → sunset** progression:

#### 1. Announcement (Initial Deprecation)

- Skill status changed to `deprecated`
- `deprecated_by` field set to replacement skill
- `migration_notes` provided with migration guidance
- Announced in release notes and CHANGELOG
- **Minimum duration:** 90 days

**Example:**
```yaml
- id: old-investigate
  status: deprecated
  deprecated_by: investigate
  migration_notes: "Migrate to `investigate` skill which uses graph-first template"
```

#### 2. Warning Period

- Warnings added to skill documentation
- CLI warnings when deprecated skill is loaded
- Integration tests start failing if deprecated skills used
- **Minimum duration:** 60 days after announcement

#### 3. Sunset (Removal)

- Skill status changed to `sunset`
- `sunset_date` set to removal date (ISO 8601 format)
- Final warning period before file deletion
- **Minimum duration:** 30 days after warning period

**Example:**
```yaml
- id: old-investigate
  status: sunset
  sunset_date: 2026-06-01
  migration_notes: "Removed. Use `investigate` skill instead."
```

#### 4. Removal

- Skill files deleted from repository
- Registry entry remains with `status: sunset` for historical reference
- Documentation updated to reference replacement

### Timeline Summary

| Stage | Duration | Status | Total Time |
|-------|----------|--------|------------|
| Announcement | 90 days | `deprecated` | 90 days |
| Warning | 60 days | `deprecated` | 150 days |
| Sunset | 30 days | `sunset` | 180 days |
| Removal | — | `sunset` (kept in registry) | — |

**Total deprecation period: Minimum 180 days (6 months)**

---

## Skill Categories

### Orchestration (9 skills)

High-level workflow coordination and pool management.

| ID | Name | Status | Location |
|----|------|--------|----------|
| `audit` | VRS Audit | active | shipped |
| `orch-spawn` | Orchestrate Spawn | active | shipped |
| `orch-resume` | Orchestrate Resume | active | shipped |
| `health-check` | Health Check | active | shipped |
| `bead-create` | Bead Create | active | shipped |
| `bead-list` | Bead List | active | shipped |
| `bead-update` | Bead Update | active | shipped |
| `create-bead-finding` | Create Bead Finding | active | dev |
| `create-bead-context-merge` | Create Bead Context Merge | active | dev |

### Investigation (3 skills)

Core vulnerability investigation workflow.

| ID | Name | Status | Location |
|----|------|--------|----------|
| `investigate` | VRS Investigate | active | shipped + dev |
| `verify` | VRS Verify | active | shipped + dev |
| `debate` | VRS Debate | active | shipped + dev |

### Validation (6 skills)

Testing, benchmarking, and quality assurance.

| ID | Name | Status | Location |
|----|------|--------|----------|
| `test-full` | Test Full | active | shipped |
| `test-quick` | Test Quick | active | shipped |
| `test-component` | Test Component | active | shipped |
| `validate-vulndocs` | Validate VulnDocs | active | shipped |
| `benchmark-model` | Benchmark Model | active | shipped |
| `mutate-contract` | Mutate Contract | active | shipped |

### Discovery (5 skills)

Vulnerability knowledge discovery and ingestion.

| ID | Name | Status | Location |
|----|------|--------|----------|
| `discover` | VRS Discover | active | dev |
| `research` | VRS Research | active | dev |
| `ingest-url` | VRS Ingest URL | active | dev |
| `add-vulnerability` | VRS Add Vulnerability | active | dev |
| `merge-findings` | VRS Merge Findings | active | dev |

### Pattern Development (5 skills)

Pattern creation, refinement, and testing.

| ID | Name | Status | Location |
|----|------|--------|----------|
| `pattern-forge` | Pattern Forge | active | dev |
| `refine` | VRS Refine | active | dev |
| `test-pattern` | VRS Test Pattern | active | dev |
| `pattern-verify` | Pattern Verify | active | shipped |
| `pattern-batch` | Pattern Batch | active | shipped |

### Tool Integration (3 skills)

External static analysis tool coordination.

| ID | Name | Status | Location |
|----|------|--------|----------|
| `tool-slither` | Tool Slither | active | shipped + dev |
| `tool-aderyn` | Tool Aderyn | active | shipped + dev |
| `tool-coordinator` | Tool Coordinator | active | dev |

### Context (11 skills)

Context extraction, evidence, and graph operations.

| ID | Name | Status | Location |
|----|------|--------|----------|
| `context-pack` | Context Pack | active | shipped |
| `evidence-audit` | Evidence Audit | active | shipped |
| `graph-contract-validate` | Graph Contract Validate | active | shipped |
| `ordering-proof` | Ordering Proof | active | shipped |
| `slice-unify` | Slice Unify | active | shipped |
| `taint-extend` | Taint Extend | active | shipped |
| `taxonomy-migrate` | Taxonomy Migrate | active | shipped |
| `track-gap` | Track Gap | active | shipped |
| `economic-context` | Economic Context | active | dev |
| `graph-retrieve` | Graph Retrieve | active | dev |
| `vql-help` | VQL Help | active | dev |

### Development (5 skills)

Internal development and design tools.

| ID | Name | Status | Location |
|----|------|--------|----------|
| `test-builder` | Test Builder | active | dev |
| `agent-skillcraft` | Agent Skillcraft | active | dev |
| `gsd-research-context` | GSD Research Context | active | dev |
| `today-date` | Today Date | active | dev |
| `generate-tests` | VRS Generate Tests | active | dev |

---

## Registry Statistics

- **Total skills:** 47
- **Active skills:** 47
- **Experimental skills:** 0
- **Deprecated skills:** 0
- **Sunset skills:** 0
- **Shipped skills:** 29 (shipped location exists)
- **Dev-only skills:** 18 (dev location only)
- **Dual-location skills:** 3 (both shipped and dev)

### By Category

| Category | Count |
|----------|-------|
| Orchestration | 9 |
| Context | 11 |
| Validation | 6 |
| Discovery | 5 |
| Pattern Development | 5 |
| Development | 5 |
| Investigation | 3 |
| Tool Integration | 3 |
| Legacy | 0 |

---

## Usage

### Load Registry Programmatically

```python
from alphaswarm_sol.skills.registry import list_registry, get_skill_entry

# List all skills
skills = list_registry()
print(f"Total skills: {len(skills)}")

# Get specific skill
audit = get_skill_entry("audit")
print(f"Skill: {audit['name']}, Version: {audit['version']}, Status: {audit['status']}")

# Filter by status
active_skills = [s for s in skills if s['status'] == 'active']
deprecated_skills = [s for s in skills if s['status'] == 'deprecated']

# Filter by location
shipped_skills = [s for s in skills if s['location'].get('shipped')]
dev_only_skills = [s for s in skills if s['location'].get('shipped') is None]
```

### Validate Registry

```bash
# Validate registry schema and entries
uv run python -m alphaswarm_sol.skills.registry validate

# Check for duplicate IDs
uv run python -m alphaswarm_sol.skills.registry check-duplicates

# List deprecated skills
uv run python -m alphaswarm_sol.skills.registry list-deprecated
```

---

## Adding New Skills

When adding a new skill to the system:

1. **Create skill file** in appropriate location (`shipped/` or `.claude/skills/`)
2. **Add registry entry** to `src/alphaswarm_sol/skills/registry.yaml`
3. **Set initial version** to `1.0.0` for new skills
4. **Set status** to `experimental` for new skills under development
5. **Provide description** - one-line summary of purpose
6. **Categorize correctly** - choose appropriate category
7. **Validate registry** - run `uv run python -m alphaswarm_sol.skills.registry validate`

### Example New Skill Entry

```yaml
- id: new-skill
  name: "New Skill"
  version: 1.0.0
  status: experimental
  category: investigation
  description: "Experimental skill for new investigation pattern"
  location:
    shipped: null
    dev: .claude/skills/vrs/new-skill.md
```

---

## Deprecating Skills

When deprecating a skill:

1. **Create replacement skill** (if not already exists)
2. **Update registry entry:**
   - Change `status` to `deprecated`
   - Set `deprecated_by` to replacement skill ID
   - Add `migration_notes` with clear migration path
3. **Announce deprecation:**
   - Add to release notes
   - Update CHANGELOG.md
   - Notify in documentation
4. **Set sunset date** (minimum 180 days from deprecation):
   ```yaml
   sunset_date: 2026-06-01
   ```
5. **Update documentation** to reference replacement

### Example Deprecation

```yaml
- id: old-audit
  name: "Old Audit (Deprecated)"
  version: 1.5.0
  status: deprecated
  deprecated_by: audit
  sunset_date: 2026-07-01
  migration_notes: "Migrate to `audit` skill (v2.0) which uses improved orchestration layer. See docs/guides/migration/old-audit-to-audit.md for migration guide."
  category: legacy
  location:
    shipped: null  # Removed from shipped
    dev: .claude/skills/vrs-legacy/old-audit.md
```

---

## Version Bumping

Use semantic versioning (MAJOR.MINOR.PATCH):

- **MAJOR** - Breaking changes (API changes, removed features)
- **MINOR** - New features (backward compatible)
- **PATCH** - Bug fixes (backward compatible)

### When to Bump

| Change Type | Version Bump | Example |
|-------------|--------------|---------|
| Bug fix | PATCH | 1.0.0 → 1.0.1 |
| New feature (backward compatible) | MINOR | 1.0.1 → 1.1.0 |
| Breaking change | MAJOR | 1.1.0 → 2.0.0 |
| Deprecation announcement | MINOR | 1.5.0 → 1.6.0 |
| Skill sunset | MAJOR (final) | 1.6.0 → 2.0.0 (sunset) |

---

## Integration with Subagent Catalog

Skills and subagents are tracked separately:

- **Skills** - Reusable investigation and orchestration workflows
- **Subagents** - Individual agents with specific roles and model tiers

**Cross-references:**
- Skills may spawn subagents (referenced by ID in skill documentation)
- Subagent catalog tracks which skills each agent supports
- Registry and catalog share similar versioning and deprecation policies

---

## Schema Validation

Registry entries are validated against `schemas/skill_registry_v1.json`.

### Validation Checks

1. **Required fields present:** id, name, version, status
2. **ID format:** kebab-case (lowercase with hyphens)
3. **Version format:** Semantic version (X.Y.Z)
4. **Status enum:** One of active, deprecated, experimental, sunset
5. **Category enum:** Valid category from schema
6. **Sunset date format:** ISO 8601 (YYYY-MM-DD) if present
7. **No duplicate IDs:** Each skill ID unique
8. **File existence:** Location paths exist (if specified)
9. **Replacement references:** `replaces` and `deprecated_by` reference valid skill IDs

---

## Future Enhancements

1. **Automatic sunset warnings** - CLI warns when using skills near sunset
2. **Migration automation** - Scripts to assist with skill migration
3. **Version compatibility** - Track which skill versions work together
4. **Dependency tracking** - Skills that depend on other skills
5. **Usage analytics** - Track which skills are most used
6. **Auto-generate docs** - Generate skill tables from registry
7. **CI/CD integration** - Block merges if deprecated skills added

---

## Related Documentation

- **Skill Schema:** `docs/reference/skill-schema-v2.md` - Skill frontmatter and structure
- **Subagent Catalog:** `docs/reference/subagent-catalog.md` - Agent registry and metadata
- **Tooling Guide:** `.planning/TOOLING.md` - When to use which skill
- **Skills Guide:** `docs/guides/skills-basics.md` - How to create and use skills

---

**Maintained by:** AlphaSwarm.sol Core Team
**Updates:** Registry updated with each skill addition, modification, or deprecation
**Questions:** See `.planning/TOOLING.md` or docs/guides/skills-basics.md
