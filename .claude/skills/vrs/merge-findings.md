---
name: vrs-merge-findings
description: |
  Consolidate similar vulnerability findings skill. Identifies duplicates and related
  vulnerabilities, merges them into unified entries, reduces redundancy in VulnDocs.

  Invoke when user wants to:
  - Deduplicate vulnerabilities: "merge similar vulnerabilities"
  - Consolidate findings: "/vrs-merge-findings oracle category"
  - Reduce redundancy: "find and merge duplicate entries"

  This skill:
  1. Identifies similar/duplicate vulnerability entries
  2. Analyzes semantic overlap (triggers, patterns, reasoning)
  3. Proposes merge strategy
  4. Consolidates content into unified entry
  5. Validates merged result
  6. Preserves all unique information

slash_command: vrs:merge-findings
context: fork

tools:
  - Read
  - Write
  - Glob
  - Grep
  - Bash(uv run alphaswarm vulndocs*)

model_tier: sonnet

---

# VRS Merge Findings Skill - Vulnerability Deduplication

You are the **VRS Merge Findings** skill, responsible for identifying and consolidating similar or duplicate vulnerability entries in VulnDocs. You reduce redundancy while preserving all unique information and improving knowledge density.

**CRITICAL: Invocation Model**
You are Claude Code, an agent that follows this skill documentation. When this skill says "validate," you invoke the Bash tool with `uv run alphaswarm vulndocs validate`. When it says "read index.yaml," you use the Read tool. When it says "update entry," you use the Write tool. This skill file IS the prompt that guides your behavior - you execute it using your standard tools (Bash, Read, Write, Glob, Grep).

## Purpose

- **Deduplicate similar vulnerabilities** across VulnDocs
- **Merge related patterns** into unified entries
- **Consolidate verbose information** into dense context
- **Reduce maintenance burden** by eliminating redundancy
- **Preserve unique knowledge** during consolidation
- **Improve discoverability** by organizing related content

## How to Invoke

```bash
/vrs-merge-findings
/vrs-merge-findings --category oracle
/vrs-merge-findings --target oracle/price-manipulation
```

**Arguments:**

- `--category` - Focus on specific category (default: all)
- `--target` - Specific entry to check for merges
- `--dry-run` - Show merge suggestions without applying

**Interactive mode** (default):
- Scans all VulnDocs
- Presents merge candidates
- Asks for confirmation before each merge

---

## Execution Workflow

### Step 1: Identify Merge Candidates

**Goal:** Find similar/duplicate vulnerability entries.

**Actions:**

1. **List all vulnerabilities** (via Bash tool):
   ```bash
   uv run alphaswarm vulndocs list --json > /tmp/vulndocs-all.json
   ```

2. **Scan for similar entries** (via Glob/Grep):
   ```bash
   # Find all index.yaml files
   find vulndocs/ -name "index.yaml" -type f
   ```

3. **Load each entry for comparison** (via Read tool):
   - Read index.yaml (metadata, semantic_triggers, vql_queries)
   - Read overview.md (description)
   - Read detection.md (detection logic)

**Similarity Metrics:**

```python
def compute_similarity(entry_a, entry_b):
    """
    Compare two vulnerability entries across multiple dimensions.
    Returns similarity score 0.0-1.0.
    """
    scores = []

    # 1. Category/subcategory overlap
    if entry_a.category == entry_b.category:
        scores.append(0.5)
        if entry_a.subcategory == entry_b.subcategory:
            scores.append(1.0)  # Exact duplicate!

    # 2. Semantic triggers overlap
    triggers_a = set(entry_a.semantic_triggers)
    triggers_b = set(entry_b.semantic_triggers)
    trigger_overlap = len(triggers_a & triggers_b) / len(triggers_a | triggers_b)
    scores.append(trigger_overlap)

    # 3. VQL query similarity (semantic, not string match)
    vql_similarity = compare_vql_queries(entry_a.vql_queries, entry_b.vql_queries)
    scores.append(vql_similarity)

    # 4. Graph pattern similarity
    pattern_similarity = compare_graph_patterns(
        entry_a.graph_patterns, entry_b.graph_patterns
    )
    scores.append(pattern_similarity)

    # 5. Description similarity (text analysis)
    desc_similarity = compare_descriptions(
        entry_a.overview, entry_b.overview
    )
    scores.append(desc_similarity * 0.5)  # Lower weight for text

    return sum(scores) / len(scores)
```

**Similarity Thresholds:**

- **> 0.90**: Exact duplicate (merge immediately)
- **0.70-0.90**: Very similar (likely merge)
- **0.50-0.70**: Related (consider merge)
- **< 0.50**: Different (keep separate)

### Step 2: Analyze Merge Candidates

**Goal:** Determine if entries should be merged and how.

**For each candidate pair:**

1. **Compare semantic_triggers**:
   ```yaml
   Entry A triggers: [READS_ORACLE, MISSING_STALENESS_CHECK]
   Entry B triggers: [READS_ORACLE, MISSING_TIMESTAMP_VALIDATION]

   Analysis:
   - Both check oracle staleness
   - Different terminology, same concept
   - Recommendation: MERGE
   ```

2. **Compare reasoning_templates**:
   ```python
   # Entry A reasoning:
   1. Identify oracle reads
   2. Check for updatedAt validation
   3. Verify heartbeat checks

   # Entry B reasoning:
   1. Locate price feed calls
   2. Check timestamp validation
   3. Ensure staleness protection

   # Analysis: Same logic, different wording → MERGE
   ```

3. **Compare graph_patterns**:
   ```yaml
   Entry A: oracle_read → calculation → state_write
   Entry B: price_fetch → compute → storage_update

   Analysis:
   - Identical structure, different labels
   - Recommendation: MERGE, use Entry A terminology
   ```

4. **Identify unique content**:
   ```yaml
   Entry A unique:
   - Chainlink-specific details
   - updatedAt field specifics

   Entry B unique:
   - Pyth oracle examples
   - Heartbeat validation code

   Merge plan:
   - Combine into single entry
   - Add sections for Chainlink and Pyth specifics
   ```

### Step 3: Propose Merge Strategy

**Goal:** Present merge plan to user for confirmation.

**Merge Proposal Format:**

```yaml
# Merge Proposal

candidate_pair:
  entry_a: oracle/chainlink-stale-price
  entry_b: oracle/pyth-stale-price
  similarity_score: 0.85
  recommendation: MERGE

analysis:
  shared_aspects:
    - Both detect stale oracle data
    - Same semantic triggers (READS_ORACLE, MISSING_STALENESS_CHECK)
    - Identical graph pattern
    - Same severity (high)

  unique_aspects:
    entry_a_unique:
      - Chainlink-specific: updatedAt field
      - answeredInRound field checks
      - Heartbeat per feed configuration
    entry_b_unique:
      - Pyth-specific: confidence intervals
      - Exponential moving average handling
      - Network-specific staleness windows

  merge_strategy:
    primary_entry: oracle/stale-oracle-data
    action: create_unified_entry
    deprecate:
      - oracle/chainlink-stale-price → redirect to unified
      - oracle/pyth-stale-price → redirect to unified

    unified_structure:
      index.yaml:
        id: oracle-stale-data
        category: oracle
        subcategory: stale-data
        semantic_triggers:
          - READS_ORACLE
          - MISSING_STALENESS_CHECK
          - USES_UNVALIDATED_TIMESTAMP
        vql_queries:
          - "FIND functions WHERE reads_oracle AND NOT checks_timestamp"
        reasoning_template: |
          1. Identify oracle data reads (any oracle type)
          2. Check for staleness validation
          3. Verify network-specific staleness thresholds

      overview.md:
        - General stale oracle vulnerability description
        - Applies to all oracle types (Chainlink, Pyth, etc.)

      detection.md:
        sections:
          - general_detection: Common patterns across oracles
          - chainlink_specific: updatedAt, answeredInRound checks
          - pyth_specific: confidence, EMA handling

      patterns/:  # Co-located in vulndocs/{category}/{subcategory}/patterns/
        - oracle-stale-001-general.yaml
        - oracle-stale-002-chainlink.yaml
        - oracle-stale-003-pyth.yaml

reason: |
  Both entries describe the same vulnerability (stale oracle data) with
  oracle-specific implementation details. Merging creates single source of truth
  while preserving oracle-specific nuances in dedicated sections.

preserve:
  - All Chainlink-specific validation logic
  - All Pyth-specific confidence handling
  - All existing exploits from both entries
  - All pattern YAML files (consolidated into vulndocs/{category}/{subcategory}/patterns/ folder)

benefits:
  - Single entry for "stale oracle" searches
  - Easier maintenance (update once, applies to all oracles)
  - Clearer mental model for users
  - Reduced redundancy (both had ~80% identical content)

risks:
  - May lose some oracle-specific discoverability
  - Mitigation: Add oracle-type tags, cross-references

next_steps:
  1. Create unified entry at oracle/stale-data
  2. Migrate content from both old entries
  3. Add oracle-specific sections
  4. Update all pattern YAML vulndoc references
  5. Add redirects from old locations
  6. Validate merged entry
  7. Delete old entries (preserve in git history)
```

**User Confirmation Required:**
```
Review merge proposal above.

Type 'yes' to proceed with merge
Type 'no' to skip
Type 'edit' to modify merge strategy
```

### Step 4: Execute Merge (After Confirmation)

**Goal:** Apply merge strategy to create unified entry.

**Actions:**

1. **Create new unified entry** (via Bash tool):
   ```bash
   uv run alphaswarm vulndocs scaffold \
     --category oracle \
     --subcategory stale-data \
     --severity high
   ```

2. **Populate index.yaml** (via Write tool):
   ```yaml
   # Merge semantic_triggers from both entries
   semantic_triggers:
     - READS_ORACLE
     - MISSING_STALENESS_CHECK
     - USES_UNVALIDATED_TIMESTAMP

   # Merge VQL queries
   vql_queries:
     - "FIND functions WHERE reads_oracle AND NOT checks_timestamp"
     - "FIND functions WHERE reads_chainlink AND NOT checks_updatedAt"
     - "FIND functions WHERE reads_pyth AND NOT checks_confidence"

   # Unified reasoning template
   reasoning_template: |
     1. Identify oracle data reads (any oracle type)
     2. Check for staleness validation:
        - Chainlink: updatedAt, answeredInRound
        - Pyth: publishTime, confidence
        - Custom: timestamp fields
     3. Verify network-specific staleness thresholds
     4. Check for fallback mechanisms
   ```

3. **Merge overview.md** (via Write tool):
   ```markdown
   # Stale Oracle Data Vulnerability

   ## Overview

   Smart contracts using oracle price feeds without validating data staleness
   can operate on outdated information, leading to incorrect calculations,
   exploitable arbitrage, and protocol manipulation.

   This vulnerability applies to all oracle types: Chainlink, Pyth, custom oracles.

   [General content from both entries merged...]

   ## Oracle-Specific Details

   ### Chainlink Price Feeds
   [Content from Entry A...]

   ### Pyth Network Feeds
   [Content from Entry B...]
   ```

4. **Merge detection.md** (via Write tool):
   - General detection section (merged common logic)
   - Oracle-specific sections (preserved unique content)

5. **Merge exploits.md** (via Write tool):
   - Combine all real-world exploits from both entries
   - Organize by oracle type if relevant

6. **Consolidate patterns/** (via Write tool):
   - Copy all pattern YAML files to unified entry's patterns/ subdirectory
   - Location: `vulndocs/{category}/{subcategory}/patterns/`
   - Update `vulndoc:` field to point to new location
   - Ensure no pattern IDs conflict

7. **Add cross-references** (via Write tool):
   ```markdown
   # In old entries (before deletion):
   ## DEPRECATED - Merged Into oracle/stale-data

   This entry has been merged into `oracle/stale-data` for better organization.

   See: vulndocs/oracle/stale-data/
   ```

### Step 5: Validate Merged Entry

**Goal:** Ensure merged entry is valid and complete.

**Actions:**

1. **Run validation** (via Bash tool):
   ```bash
   uv run alphaswarm vulndocs validate vulndocs/oracle/stale-data/
   ```

2. **Check for information loss**:
   - Compare merged entry to originals
   - Verify all semantic_triggers preserved
   - Verify all patterns included
   - Verify all exploits documented

3. **Verify pattern references** (via Grep):
   ```bash
   # Check if any patterns still reference old locations
   grep -r "oracle/chainlink-stale-price\|oracle/pyth-stale-price" vulndocs/
   ```

4. **Test build** (via Bash tool):
   ```bash
   # Ensure no broken references
   uv run alphaswarm build-kg tests/contracts/ --with-labels
   ```

**Validation Checklist:**
- [ ] index.yaml valid and complete
- [ ] All sections present (overview, detection, verification, exploits)
- [ ] All patterns moved and references updated
- [ ] All unique information preserved
- [ ] No duplicate content
- [ ] Validation passes
- [ ] No broken references

### Step 6: Cleanup and Report

**Goal:** Remove old entries and document merge.

**Actions:**

1. **Archive old entries**:
   ```bash
   # Add deprecation notice (via Write tool)
   echo "DEPRECATED: Merged into oracle/stale-data" > vulndocs/oracle/chainlink-stale-price/DEPRECATED.md

   # Or delete (preserves git history)
   rm -rf vulndocs/oracle/chainlink-stale-price/
   rm -rf vulndocs/oracle/pyth-stale-price/
   ```

2. **Commit merge** (via Bash tool):
   ```bash
   git add vulndocs/oracle/
   git commit -m "refactor(vulndocs): merge oracle staleness entries

   - Merged oracle/chainlink-stale-price + oracle/pyth-stale-price
   - Created unified oracle/stale-data entry
   - Preserved all unique oracle-specific content
   - Consolidated 3 patterns into single location
   - Reduces redundancy, improves discoverability
   "
   ```

3. **Generate merge report**:
   ```yaml
   # Merge Report
   timestamp: 2025-01-22T10:30:00Z
   merged_entries: 2

   merges:
     - id: merge-oracle-stale
       entries_merged:
         - oracle/chainlink-stale-price
         - oracle/pyth-stale-price
       unified_entry: oracle/stale-data
       similarity_score: 0.85
       information_preserved: 100%
       patterns_consolidated: 3
       exploits_consolidated: 5
       lines_reduced: 247 (from 653 to 406)
       benefits:
         - Single source of truth for oracle staleness
         - Easier to maintain and update
         - Clearer for users searching for oracle vulnerabilities

   statistics:
     total_entries_scanned: 47
     merge_candidates_found: 3
     merges_completed: 1
     merges_skipped: 2 (user declined)
     validation_errors: 0
   ```

4. **Present report to user**:
   ```
   ✅ Merge Complete

   Merged: oracle/chainlink-stale-price + oracle/pyth-stale-price
   Into: oracle/stale-data

   Preserved:
   - All semantic triggers
   - All 3 pattern YAMLs
   - All 5 real-world exploits
   - Oracle-specific detection logic

   Reduced:
   - 247 lines of redundant content removed
   - 2 maintenance points → 1

   Validation: PASSED

   Next merge candidate:
   - reentrancy/cross-function + reentrancy/callback
   - Similarity: 0.72
   - Review? (yes/no)
   ```

---

## Key Rules

### 1. Always Require Confirmation
- Present full merge proposal before executing
- User must explicitly approve each merge
- Provide option to edit merge strategy

### 2. Never Delete Information
- Consolidate, don't remove
- If unsure if content is duplicate, preserve it
- "When in doubt, keep it separate"

### 3. Preserve Unique Aspects
- Identify what makes each entry unique
- Create sections/variants for unique content
- Don't force-fit content that doesn't align

### 4. Maintain Git History
- Commit merges with clear messages
- Old entries preserved in git history
- Use descriptive commit messages explaining rationale

### 5. Validate After Every Merge
- Run `vulndocs validate` on merged entry
- Check for broken pattern references
- Verify no information lost

### 6. Update All Cross-References
- Pattern YAML `vulndoc:` fields
- Test file references
- Any documentation links

### 7. Use Semantic Similarity, Not String Matching
- Compare semantic_triggers (concepts)
- Compare graph patterns (structure)
- Don't merge based on similar words alone

---

## Merge Decision Matrix

```
Similarity Score | Action | Rationale
-----------------|--------|----------
> 0.90           | Auto-suggest merge | Almost certainly duplicate
0.70 - 0.90      | Suggest merge | Very likely should be merged
0.50 - 0.70      | Flag for review | May be related, user decides
< 0.50           | Keep separate | Different vulnerabilities
```

**Exception Cases (Keep Separate Even If Similar):**

1. **Different severity levels**: High vs. Medium
2. **Different detection complexity**: Simple vs. Complex reasoning
3. **Different contexts**: DeFi-specific vs. General
4. **User preference**: User wants granular separation

---

## Example Invocation

```bash
# User invokes
/vrs-merge-findings --category oracle

# You (Claude Code agent) execute:
1. List all vulnerabilities:
   - Bash: uv run alphaswarm vulndocs list --json

2. Filter to oracle category:
   - Parse JSON for category == "oracle"

3. Load all oracle entries:
   - Read: vulndocs/oracle/*/index.yaml (all)
   - Read: vulndocs/oracle/*/overview.md (all)

4. Compute similarity:
   - Compare semantic_triggers
   - Compare graph_patterns
   - Compare reasoning_templates
   - Generate similarity matrix

5. Identify candidates:
   - Found: chainlink-stale-price + pyth-stale-price (0.85)
   - Found: price-manipulation + twap-manipulation (0.68)

6. Present proposals:
   - Show merge proposal for highest similarity pair
   - Wait for user confirmation

7. If approved, execute merge:
   - Create unified entry
   - Migrate content
   - Update patterns
   - Validate
   - Cleanup
   - Commit

8. Repeat for next candidate or exit
```

---

## Tools Reference

**CLI Commands (via Bash tool):**
```bash
uv run alphaswarm vulndocs list --json          # List all vulnerabilities
uv run alphaswarm vulndocs scaffold ...         # Create new unified entry
uv run alphaswarm vulndocs validate vulndocs/   # Validate merged entry
uv run alphaswarm build-kg tests/contracts/     # Test for broken references
```

**File Operations:**
```python
# Read existing entries
Read(file_path="vulndocs/oracle/chainlink-stale-price/index.yaml")

# Write merged content
Write(file_path="vulndocs/oracle/stale-data/overview.md", content="...")

# Find all index.yaml files
Glob(pattern="vulndocs/**/index.yaml")

# Search for references
Grep(pattern="chainlink-stale-price", path="vulndocs/", output_mode="content")
```

---

## Output Location

Save merge report to:
```
.vrs/merges/report-{timestamp}.yaml
```

Present merge summary to user in terminal.
