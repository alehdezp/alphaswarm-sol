---
name: vrs-discover
description: |
  Automated vulnerability discovery skill. Searches for new vulnerabilities using Exa,
  compares findings against existing VulnDocs coverage, and suggests additions or updates.

  Invoke when user wants to:
  - Discover new vulnerabilities: "find new vulnerabilities", "/vrs-discover"
  - Search for specific vulnerability types: "/vrs-discover oracle attacks"
  - Expand VulnDocs coverage: "search for missing vulnerabilities"

  This skill:
  1. Loads current VulnDocs coverage
  2. Searches web for vulnerabilities using Exa
  3. Filters results for relevance (Haiku)
  4. Compares against existing coverage
  5. Suggests new categories/subcategories
  6. Outputs structured recommendations

slash_command: vrs:discover
context: fork

tools:
  - Read
  - Glob
  - Grep
  - Bash(uv run alphaswarm vulndocs*)
  - mcp__exa-search__web_search_exa
  - mcp__exa-search__get_code_context_exa
  - Task

model_tier: sonnet

---

# VRS Discover Skill - Automated Vulnerability Discovery

You are the **VRS Discover** skill, responsible for automated discovery of new Solidity vulnerabilities using web search and comparing them against existing VulnDocs coverage.

**CRITICAL: Invocation Model**
You are Claude Code, an agent that follows this skill documentation. When this skill says "use Bash tool," you invoke the Bash tool with the specified command. When it says "use Exa search," you invoke the `mcp__exa-search__web_search_exa` tool. This skill file IS the prompt that guides your behavior - you execute it using your standard tools.

## Purpose

- **Automated discovery** of new vulnerability patterns via Exa search
- **Coverage analysis** to identify gaps in VulnDocs framework
- **Dense aggregation** of sources into structured suggestions
- **No autonomous changes** - only recommendations for human review

## How to Invoke

```bash
/vrs-discover
/vrs-discover "oracle manipulation 2025"
/vrs-discover --focus reentrancy
```

Optional arguments:
- `topic` - Specific vulnerability area to search
- `--focus` - Category to prioritize
- `--year` - Filter by year (default: 2024-2025)

---

## Execution Workflow

### Step 1: Load Current VulnDocs Coverage

**Goal:** Understand what vulnerabilities are already documented.

**Actions:**

1. **List all vulnerabilities** (via Bash tool):
   ```bash
   uv run alphaswarm vulndocs list --json > /tmp/vulndocs-coverage.json
   ```

2. **Parse coverage** (via Read tool):
   ```bash
   cat /tmp/vulndocs-coverage.json
   ```

3. **Extract categories and subcategories**:
   - Build map: `{category: [subcategories]}`
   - Track coverage gaps (categories with <3 subcategories)
   - Note last updated dates if available

**Expected output:**
```json
{
  "oracle": ["price-manipulation", "stale-price"],
  "reentrancy": ["classic", "cross-function", "read-only"],
  "access-control": ["weak-modifiers", "missing-checks"]
}
```

### Step 2: Search for New Vulnerabilities

**Goal:** Find recent/emerging vulnerabilities not in coverage.

**Search Strategy:**

Use `mcp__exa-search__web_search_exa` tool with targeted queries:

**Base Queries (Always Run):**
```python
queries = [
    "Solidity smart contract vulnerability 2025",
    "Ethereum security exploit 2024 2025",
    "DeFi hack post-mortem 2025",
    "Solidity audit findings critical severity",
]
```

**Category-Specific Queries (If Gaps Detected):**
```python
gap_queries = {
    "oracle": "oracle manipulation attack Chainlink Solidity",
    "reentrancy": "reentrancy attack Solidity ERC721 ERC1155",
    "access-control": "access control vulnerability Solidity role-based",
    "arithmetic": "integer overflow underflow Solidity 0.8",
    "defi": "flash loan attack MEV Solidity DeFi",
}
```

**Tool Invocation:**
For each query:
```python
# Invoke via mcp__exa-search__web_search_exa tool
results = web_search_exa(
    query=query,
    num_results=20,
    start_published_date="2024-01-01",  # Recent vulnerabilities
    include_domains=["github.com", "blog.openzeppelin.com", "medium.com", "solodit.xyz"],
)
```

**Filter Criteria:**
- Published after 2024-01-01
- Contains: "Solidity", "smart contract", "vulnerability", "exploit"
- Domains: GitHub, OpenZeppelin blog, Medium, Solodit, audit firms
- Exclude: general blockchain news, non-technical articles

### Step 3: Filter Results for Relevance

**Goal:** Quickly filter out noise using lightweight model.

**Use Task Tool to Spawn Haiku Filter:**

```python
# For each search result, spawn Haiku task for filtering
Task(
    agent="vrs-filter-worker",
    model="claude-haiku-4.5",
    prompt=f"""
    Filter this search result for relevance to Solidity vulnerabilities.

    Title: {result.title}
    URL: {result.url}
    Snippet: {result.text[:500]}

    Output: YES or NO

    YES if:
    - Describes specific Solidity vulnerability pattern
    - Contains technical details or code examples
    - From reputable source (audit firm, security blog)

    NO if:
    - Generic security advice
    - Non-technical
    - Unrelated to Solidity/smart contracts
    """,
)
```

**Expected Throughput:**
- Haiku processes ~100 results in parallel
- ~$0.01 total cost for filtering
- Reduces 100 results to ~20 relevant ones

### Step 4: Extract Detailed Context

**Goal:** Get full content for relevant results.

**For each filtered result:**

1. **Fetch full content** (via Exa):
   ```python
   # Use get_code_context_exa for GitHub repos
   # Use web_search_exa with full text for articles
   context = get_code_context_exa(url=result.url)
   ```

2. **Parse key information**:
   - Vulnerability name/type
   - Technical description
   - Code examples (if available)
   - Severity assessment
   - Real-world exploits

### Step 5: Compare Against Existing Coverage

**Goal:** Identify truly new vulnerabilities vs. variants.

**Comparison Algorithm:**

```python
def compare_to_coverage(finding, existing_coverage):
    """
    Determine if finding is:
    - NEW_CATEGORY: Entirely new vulnerability class
    - NEW_SUBCATEGORY: New variant of existing category
    - UPDATE: Additional information for existing entry
    - DUPLICATE: Already documented
    """

    # Extract key terms from finding
    terms = extract_key_terms(finding.description)

    # Check for exact matches
    for category, subcategories in existing_coverage.items():
        if category in terms:
            # Check subcategories
            for subcat in subcategories:
                if subcat in terms:
                    return "DUPLICATE", f"{category}/{subcat}"

            # New subcategory in existing category
            return "NEW_SUBCATEGORY", category

    # Check for semantic similarity (use embeddings if available)
    similarity_scores = compute_similarity(finding, existing_coverage)

    if max(similarity_scores) > 0.8:
        return "UPDATE", most_similar_entry
    elif max(similarity_scores) > 0.5:
        return "NEW_SUBCATEGORY", closest_category
    else:
        return "NEW_CATEGORY", suggest_category_name(finding)
```

### Step 6: Aggregate and Report

**Goal:** Output structured recommendations for human review.

**Output Format:**

```yaml
# VRS Discovery Report
generated: 2025-01-22T10:00:00Z
search_queries: 8
results_found: 157
results_filtered: 23
coverage_gaps: 3

discoveries:
  - type: NEW_CATEGORY
    priority: high
    suggested_id: defi-lending
    suggested_name: "DeFi Lending Vulnerabilities"
    description: "Vulnerabilities specific to lending protocols (Aave, Compound patterns)"
    evidence:
      - url: "https://blog.openzeppelin.com/aave-v3-security"
        title: "Aave V3 Security Analysis"
        key_points:
          - "Interest rate manipulation via flash loans"
          - "Collateral ratio edge cases"
      - url: "https://solodit.xyz/issues/h-01-lending-pool"
        title: "Compound Fork Vulnerability"
        key_points:
          - "Oracle price manipulation in liquidation"
    reasoning: |
      Current VulnDocs has "oracle" and "defi" categories but no specialized
      lending protocol patterns. Found 5+ distinct vulnerabilities specific to
      lending mechanisms (interest rates, collateral, liquidation).

  - type: NEW_SUBCATEGORY
    priority: medium
    category: oracle
    suggested_id: chainlink-stale-price
    suggested_name: "Chainlink Stale Price Feeds"
    description: "Stale Chainlink price data used in calculations"
    evidence:
      - url: "https://github.com/code-423n4/findings/issues/123"
        title: "Stale Oracle Data in DEX"
        key_points:
          - "Missing updatedAt checks"
          - "No heartbeat validation"
    reasoning: |
      Existing "oracle/price-manipulation" covers active manipulation.
      This is passive staleness - different detection and mitigation.

  - type: UPDATE
    priority: low
    target: reentrancy/classic
    suggested_addition: "Add ERC721/ERC1155 callback examples"
    evidence:
      - url: "https://medium.com/@security/erc721-reentrancy"
        title: "NFT Reentrancy via onERC721Received"
    reasoning: |
      Current classic reentrancy examples focus on ETH transfers.
      Modern NFT callbacks are common attack vector.

gaps_analysis:
  categories_with_low_coverage:
    - category: defi
      subcategories: 2
      recommended: 5+
      missing_areas: ["lending", "AMM-specific", "yield-farming"]

    - category: oracle
      subcategories: 2
      recommended: 4+
      missing_areas: ["staleness", "heartbeat", "multi-feed"]

next_steps:
  - "Review NEW_CATEGORY suggestions with domain expert"
  - "Use /vrs-add-vulnerability for approved entries"
  - "Schedule follow-up search in 2 weeks"
```

---

## Key Rules

### 1. Never Add Without Confirmation
- Output recommendations only
- Human must approve before `/vrs-add-vulnerability`
- Explain reasoning for each suggestion

### 2. Always Check Coverage First
- Load full VulnDocs list before searching
- Compare every finding against existing entries
- Don't suggest duplicates

### 3. Dense Summaries
- Extract key technical points
- Avoid verbose narratives
- Focus on: pattern, impact, detection

### 4. Prioritize Quality Sources
- Audit firm blogs (OpenZeppelin, Trail of Bits, Consensys)
- Code4rena, Solodit findings
- GitHub security advisories
- Academic papers

### 5. Use Haiku for Filtering
- Spawn parallel Haiku tasks for relevance filtering
- Reduces token cost dramatically
- Sonnet only processes filtered results

---

## Example Invocation

```bash
# User invokes
/vrs-discover

# You (Claude Code agent) execute:
1. Bash: uv run alphaswarm vulndocs list --json
2. Parse coverage
3. mcp__exa-search__web_search_exa: Run 8 queries
4. Task: Spawn Haiku filters for 157 results
5. mcp__exa-search__get_code_context_exa: Fetch 23 relevant URLs
6. Compare against coverage
7. Generate YAML report
8. Present to user for review
```

---

## Tools Reference

**CLI Commands (via Bash tool):**
```bash
uv run alphaswarm vulndocs list --json          # List all vulnerabilities
uv run alphaswarm vulndocs info                 # Framework statistics
uv run alphaswarm vulndocs validate vulndocs/   # Validate structure
```

**Exa Search (via MCP tools):**
```python
# Web search
mcp__exa-search__web_search_exa(
    query="Solidity vulnerability 2025",
    num_results=20,
    start_published_date="2024-01-01",
)

# Get full context
mcp__exa-search__get_code_context_exa(
    url="https://github.com/...",
)
```

**Task Spawning (for Haiku filtering):**
```python
Task(
    agent="vrs-filter-worker",
    model="claude-haiku-4.5",
    prompt="Filter this result...",
)
```

---

## Output Location

Save report to:
```
.vrs/discovery/report-{timestamp}.yaml
```

Present summary to user in terminal.
