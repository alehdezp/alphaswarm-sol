---
name: vrs-ingest-url
description: |
  Ingest vulnerability knowledge from URL into vulndocs/.
  Auto-categorize content, extract patterns and documentation,
  track provenance, and enforce quality gates.

  Invoke when user wants to:
  - Add knowledge from URL: "/vrs-ingest-url https://..."
  - Batch ingest from file: "/vrs-ingest-url --batch urls.txt"
  - Dry-run ingestion: "/vrs-ingest-url https://... --dry-run"

  This skill:
  1. Fetches URL content
  2. Filters for Solidity relevance (Haiku pre-filter)
  3. Extracts vulnerability patterns and documentation
  4. Auto-categorizes into vulndocs/ hierarchy
  5. Checks for duplicates against existing content
  6. Inserts content with quality assessment
  7. Updates provenance.yaml for tracking

slash_command: vrs:ingest-url
context: fork

tools:
  - Read
  - Write
  - Glob
  - Grep
  - Bash(uv run alphaswarm vulndocs*)
  - Task
  - WebFetch

model_tier: sonnet

---

# VRS Ingest URL Skill - Semantic Insertion into VulnDocs

You are the **VRS Ingest URL** skill, responsible for automated ingestion of vulnerability knowledge from URLs into the VulnDocs framework. You fetch content, extract patterns and documentation, auto-categorize, and maintain provenance tracking.

**CRITICAL: Invocation Model**
You are Claude Code, an agent that follows this skill documentation. When this skill says "fetch URL," you invoke WebFetch or appropriate tools. When it says "update provenance," you read and write the provenance.yaml file. This skill file IS the prompt that guides your behavior - you execute it using your standard tools.

## Purpose

- **Automated ingestion** of vulnerability knowledge from URLs
- **Smart categorization** into vulndocs/ hierarchy
- **Pattern extraction** from source content
- **Quality gates** to prevent low-quality insertion
- **Provenance tracking** for source attribution
- **Deduplication** to avoid duplicate content

## How to Invoke

```bash
# Single URL ingestion
/vrs-ingest-url https://blog.openzeppelin.com/reentrancy-after-istanbul

# Force category
/vrs-ingest-url https://example.com/oracle-vuln --category oracle

# Dry-run (show planned actions without inserting)
/vrs-ingest-url https://example.com/vuln --dry-run

# Batch processing from file
/vrs-ingest-url --batch urls.txt

# Quality threshold (skip if below quality)
/vrs-ingest-url https://example.com/vuln --quality ready
```

**Arguments:**

| Argument | Required | Description |
|----------|----------|-------------|
| `url` | Yes* | URL to ingest (* or --batch) |
| `--category` | No | Force category (auto-categorize if not provided) |
| `--dry-run` | No | Show planned actions without inserting |
| `--batch` | No | File containing URLs (one per line) |
| `--quality` | No | Quality threshold: draft/ready/excellent (default: draft) |

---

## Execution Workflow

### Step 1: Fetch URL Content

**Goal:** Retrieve content from the URL.

**Action: Fetch via WebFetch tool**

```python
# Single URL
content = WebFetch(url=url)
```

**For Batch Processing:**

```python
# Read URL file
with open(batch_file) as f:
    urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]

# Process each URL
for url in urls:
    result = await ingest_single(url, category, dry_run, quality_threshold)
    results.append(result)
```

**Handle Errors:**
- 404/unavailable: Skip with warning
- Rate limited: Wait and retry
- Paywall/blocked: Report and skip

### Step 2: Pre-Filter for Solidity Relevance (Haiku)

**Goal:** Quickly filter out non-Solidity content using lightweight model.

**Use Task Tool to Spawn Haiku Filter:**

```python
Task(
    model="claude-haiku-4",
    prompt=f"""
    Is this content relevant to Solidity smart contract security?

    URL: {url}
    Content snippet: {content[:2000]}

    Output ONLY: YES or NO

    YES if:
    - Discusses Solidity vulnerability patterns
    - Contains smart contract security information
    - Describes DeFi/blockchain exploits with technical detail
    - From audit report, security blog, or postmortem

    NO if:
    - General blockchain/crypto news without technical depth
    - Non-Solidity content (Python, JavaScript security, etc.)
    - Marketing content without vulnerability details
    - Unrelated to smart contract security
    """,
)
```

**Decision:**
- YES: Continue to extraction
- NO: Skip with reason "Not Solidity relevant"

### Step 3: Extract Patterns and Documentation

**Goal:** Extract vulnerability patterns, descriptions, and semantic operations.

**Extraction Process (Sonnet-level reasoning):**

```python
# Extract structured content from the URL
extracted = ContentExtractor().extract(content)

# Expected output structure:
extracted = {
    "vulnerability_type": "reentrancy",
    "suggested_name": "Cross-function Reentrancy",
    "description": "Reentrancy via callbacks between different functions...",
    "severity": "critical",

    # Patterns (if extractable)
    "patterns": [
        {
            "id": "cross-function-reentrancy",
            "tier": "A",
            "conditions": ["CALLS_EXTERNAL", "WRITES_USER_BALANCE"],
            "sequence": ["external_call", "state_write"]
        }
    ],

    # Semantic operations identified
    "semantic_ops": ["TRANSFERS_VALUE_OUT", "CALLS_EXTERNAL", "WRITES_USER_BALANCE"],

    # Graph signals
    "graph_signals": {
        "behavioral_signature": "R:bal->X:out->W:bal",
        "vulnerable_pattern": "external_call before state_update"
    },

    # Documentation content
    "documentation": {
        "overview": "...",
        "detection": "...",
        "mitigation": "...",
        "exploits": [...]
    },

    # Quality assessment
    "quality": "ready",  # draft/ready/excellent
    "quality_reasons": ["Has code examples", "Missing real-world exploit reference"]
}
```

**Quality Assessment Criteria:**

| Quality | Requirements |
|---------|--------------|
| `draft` | Basic description, category identifiable |
| `ready` | Technical detail, code examples, detection guidance |
| `excellent` | Real exploits, full detection/mitigation, multiple sources |

### Step 4: Auto-Categorize into VulnDocs Hierarchy

**Goal:** Determine the correct location in vulndocs/.

**Categorization Logic:**

```python
CATEGORY_KEYWORDS = {
    "reentrancy": ["reentrant", "reentrancy", "callback", "CEI"],
    "oracle": ["oracle", "price feed", "chainlink", "twap", "stale price"],
    "access-control": ["access", "authorization", "admin", "owner", "modifier", "role"],
    "arithmetic": ["overflow", "underflow", "precision", "rounding", "division"],
    "flash-loan": ["flash loan", "flash mint", "atomic arbitrage"],
    "dos": ["denial of service", "gas griefing", "unbounded loop", "gas limit"],
    "governance": ["governance", "voting", "proposal", "timelock", "quorum"],
    "token": ["ERC20", "ERC721", "ERC1155", "token transfer", "approval"],
    "upgrade": ["proxy", "upgrade", "UUPS", "transparent", "diamond", "beacon"],
    "vault": ["vault", "deposit", "withdrawal", "share", "inflation"],
    "cross-chain": ["bridge", "cross-chain", "message passing", "LayerZero"],
    "logic": ["business logic", "state machine", "invariant", "condition"],
    "mev": ["MEV", "frontrun", "backrun", "sandwich", "arbitrage"],
    "crypto": ["signature", "ECDSA", "keccak", "hash collision", "randomness"],
    "precision-loss": ["precision", "decimal", "truncation", "rounding error"],
    "restaking": ["restaking", "liquid staking", "LST", "validator"],
    "account-abstraction": ["ERC-4337", "account abstraction", "paymaster", "bundler"],
    "zk-rollup": ["zkSNARK", "zkSTARK", "validity proof", "data availability"],
}

def categorize(extracted, hint=None):
    if hint:
        return validate_category(hint)

    # Score categories by keyword matches
    scores = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in extracted.description.lower())
        if score > 0:
            scores[category] = score

    if not scores:
        return ("uncategorized", extracted.suggested_name)

    best_category = max(scores, key=scores.get)

    # Suggest subcategory from extracted content
    subcategory = slugify(extracted.suggested_name)

    return (best_category, subcategory)
```

**Subcategory Determination:**
- Use extracted `suggested_name` as base
- Convert to kebab-case
- Check for existing similar subcategory
- If conflict, suggest merge or new name

### Step 5: Check for Duplicates

**Goal:** Prevent duplicate content insertion.

**Deduplication Checks:**

```python
def check_duplicates(url, category, subcategory, vulndocs_root):
    duplicates = []

    # 1. Check URL already processed
    provenance_files = glob(f"{vulndocs_root}/*/*/provenance.yaml")
    for prov_file in provenance_files:
        provenance = yaml.load(prov_file)
        if url in provenance.get("processed_urls", []):
            duplicates.append(("URL already processed", prov_file))

    # 2. Check exact subcategory exists
    target_path = vulndocs_root / category / subcategory
    if target_path.exists():
        duplicates.append(("Subcategory already exists", target_path))

    # 3. Check semantic similarity with existing content
    existing_docs = discover_vulnerabilities(category)
    for doc in existing_docs:
        similarity = compute_similarity(extracted.description, doc.description)
        if similarity > 0.8:
            duplicates.append(("Similar content exists", doc.path, similarity))

    return duplicates
```

**Duplicate Resolution:**
- URL already processed: Skip (unless --force)
- Subcategory exists: Suggest update instead of new entry
- Similar content: Present comparison and ask for decision

### Step 6: Insert Content (if not dry-run)

**Goal:** Create or update vulndocs content.

**Insertion Flow:**

```python
def insert_content(extracted, category, subcategory, dry_run=False):
    target_path = vulndocs_root / category / subcategory

    if dry_run:
        return DryRunResult(
            action="Would create" if not target_path.exists() else "Would update",
            path=target_path,
            files=["index.yaml", "overview.md", "detection.md", "verification.md", "exploits.md"],
            quality=extracted.quality
        )

    # Create structure if new
    if not target_path.exists():
        # Use scaffold command
        Bash(f"uv run alphaswarm vulndocs scaffold {category} {subcategory}")

    # Update files with extracted content
    update_index_yaml(target_path, extracted)
    update_overview(target_path, extracted)
    update_detection(target_path, extracted)

    # If patterns extracted, create pattern files
    for pattern in extracted.patterns:
        create_pattern_file(target_path / "patterns", pattern)

    return InsertResult(
        action="created" if not target_path.exists() else "updated",
        path=target_path,
        files_modified=[...],
        quality=extracted.quality
    )
```

**Quality Gate Enforcement:**

```python
def check_quality_gate(extracted, threshold):
    quality_levels = {"draft": 1, "ready": 2, "excellent": 3}

    if quality_levels[extracted.quality] < quality_levels[threshold]:
        return QualityGateResult(
            passed=False,
            reason=f"Content quality '{extracted.quality}' below threshold '{threshold}'",
            suggestion="Try additional research passes or lower threshold"
        )

    return QualityGateResult(passed=True)
```

### Step 7: Update Provenance Tracking

**Goal:** Record source for attribution and deduplication.

**Provenance Update:**

```python
def update_provenance(target_path, url, extracted):
    prov_file = target_path / "provenance.yaml"

    if prov_file.exists():
        provenance = yaml.load(prov_file)
    else:
        provenance = {
            "schema_version": "1.0",
            "sources": [],
            "processed_urls": [],
            "last_updated": ""
        }

    # Add source entry
    source_entry = {
        "url": url,
        "type": classify_source_type(url),  # exploit, audit, research, education, advisory, postmortem
        "fetched": datetime.now().isoformat()[:10],
        "quality": extracted.quality,
        "extracted": {
            "docs": list(extracted.documentation.keys()),
            "patterns": [p["id"] for p in extracted.patterns]
        },
        "notes": f"Auto-ingested via /vrs-ingest-url"
    }
    provenance["sources"].append(source_entry)

    # Add to processed URLs
    provenance["processed_urls"].append({
        "url": url,
        "hash": hash_content(extracted),
        "processed_date": datetime.now().isoformat()[:10]
    })

    provenance["last_updated"] = datetime.now().isoformat()[:10]

    yaml.dump(provenance, prov_file)
```

**Source Type Classification:**

```python
def classify_source_type(url):
    if "rekt.news" in url or "postmortem" in url.lower():
        return "postmortem"
    if "solodit" in url or "code4rena" in url or "audit" in url.lower():
        return "audit"
    if "github.com" in url and "security" in url.lower():
        return "advisory"
    if "exploit" in url.lower() or "hack" in url.lower():
        return "exploit"
    if "blog" in url or "medium.com" in url:
        return "research"
    return "research"  # default
```

---

## Model Tiering

This skill uses tiered model selection for cost efficiency:

| Stage | Model | Purpose |
|-------|-------|---------|
| Pre-filter | Haiku | Quick relevance check (YES/NO) |
| Extraction | Sonnet | Pattern/doc extraction (main work) |
| Quality Control | Opus (optional) | Final quality assessment |

**Token Budget:**
- Haiku filter: ~500 tokens per URL
- Sonnet extraction: ~4,000 tokens per URL
- Total per URL: ~$0.02

---

## Output Format

### Single URL Success

```yaml
Ingestion Result:
  url: https://blog.openzeppelin.com/reentrancy-after-istanbul
  status: success
  action: created
  path: vulndocs/reentrancy/after-istanbul/

  Files Created:
    - index.yaml (populated)
    - overview.md (from extraction)
    - detection.md (with graph patterns)
    - provenance.yaml (updated)

  Patterns Extracted:
    - reentrancy-after-istanbul.yaml

  Quality Assessment:
    level: ready
    reasons:
      - Has technical detail
      - Includes code examples
      - Missing: real-world exploit reference

  Provenance:
    source_type: research
    fetched: 2026-01-23
```

### Dry-Run Output

```yaml
Dry-Run Result:
  url: https://example.com/vulnerability
  would_create: vulndocs/oracle/stale-price/

  Planned Actions:
    1. Create directory: vulndocs/oracle/stale-price/
    2. Scaffold via CLI: uv run alphaswarm vulndocs scaffold oracle stale-price
    3. Populate files:
       - index.yaml (with semantic_triggers, vql_queries)
       - overview.md (from extraction)
       - detection.md (graph-first approach)
    4. Create pattern: vulndocs/oracle/stale-price/patterns/oracle-stale-price.yaml
    5. Update provenance.yaml

  Categorization:
    category: oracle (confidence: 0.85)
    subcategory: stale-price (extracted from content)

  Quality Gate:
    threshold: draft
    actual: ready
    passed: true

  No changes made (dry-run mode).
```

### Batch Output

```yaml
Batch Ingestion Results:
  total_urls: 10
  processed: 8
  skipped: 2

  Results:
    - url: https://url1.com
      status: success
      path: vulndocs/reentrancy/classic/

    - url: https://url2.com
      status: skipped
      reason: Not Solidity relevant

    - url: https://url3.com
      status: skipped
      reason: URL already processed

    - url: https://url4.com
      status: success
      path: vulndocs/oracle/manipulation/

  Summary:
    new_entries: 3
    updated_entries: 5
    patterns_created: 4
    quality_avg: ready
```

---

## Key Rules

### 1. Always Pre-Filter with Haiku

Never skip the relevance filter. This saves cost and prevents junk insertion.

```python
# Always spawn Haiku filter first
if not haiku_filter(content):
    return IngestionResult(skipped=True, reason="Not Solidity relevant")
```

### 2. Enforce Quality Gates

Don't insert content below quality threshold (unless explicitly requested).

```python
if quality_level < threshold:
    if not force:
        return QualityGateFailure(...)
```

### 3. Always Update Provenance

Every successful insertion MUST update provenance.yaml for tracking.

### 4. Never Overwrite Without Warning

If subcategory exists, warn user before updating:

```
Warning: vulndocs/reentrancy/classic/ already exists.
Options:
  1. Update existing entry (merge content)
  2. Create new subcategory: reentrancy/classic-v2
  3. Skip this URL
```

### 5. Use Graph-First Detection

Extracted detection content must use BSKG operations, not function names:

- Good: "READS_ORACLE without CHECKS_TIMESTAMP"
- Bad: "Functions named getPrice() without timestamp check"

---

## Error Handling

```yaml
Error Cases:

  - case: URL unreachable
    action: Skip with warning
    message: "Failed to fetch: connection timeout"

  - case: Content not relevant
    action: Skip
    message: "Haiku filter: Not Solidity relevant"

  - case: Quality below threshold
    action: Skip
    message: "Quality 'draft' below threshold 'ready'"

  - case: Duplicate URL
    action: Skip
    message: "URL already processed (see vulndocs/oracle/manipulation/provenance.yaml)"

  - case: Similar content exists
    action: Prompt user
    message: "Similar to existing: vulndocs/oracle/price-manipulation (similarity: 85%)"
```

---

## Integration with Other Skills

- **After ingestion:** Use `/vrs-generate-tests` to create Phase 7 tests
- **For discovery:** Use `/vrs-discover` to find URLs to ingest
- **For updates:** Use `/vrs-add-vulnerability` for manual additions
- **For refinement:** Use `/vrs-refine` to improve pattern quality

---

## Example Invocation

```bash
# User invokes
/vrs-ingest-url https://blog.openzeppelin.com/reentrancy-after-istanbul --dry-run

# You (Claude Code agent) execute:
1. WebFetch: Fetch URL content
2. Task (Haiku): Pre-filter for relevance -> YES
3. ContentExtractor: Extract patterns, docs, semantic ops
4. Categorizer: Determine category -> reentrancy/after-istanbul
5. DuplicateChecker: Check for duplicates -> None found
6. (Dry-run) Report planned actions
7. Present result to user

# User approves, runs without --dry-run
/vrs-ingest-url https://blog.openzeppelin.com/reentrancy-after-istanbul

# You execute:
1-5. Same as above
6. Bash: uv run alphaswarm vulndocs scaffold reentrancy after-istanbul
7. Write: Populate index.yaml, overview.md, detection.md
8. Write: Create pattern file
9. Write: Update provenance.yaml
10. Bash: uv run alphaswarm vulndocs validate vulndocs/reentrancy/after-istanbul
11. Report success
```
