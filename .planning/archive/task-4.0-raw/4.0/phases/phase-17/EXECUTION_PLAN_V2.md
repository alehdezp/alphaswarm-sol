# Phase 17 Execution Plan V2 (Corrected)

**Date:** 2026-01-09 (Ralph Loop Iteration 1 - Restart)
**Status:** RESTARTED with correct constraints

---

## CRITICAL CONSTRAINTS (User Requirements)

1. **ALWAYS use subagents** - Main agent orchestrates, subagents do the work
2. **Docker REQUIRED** - Install/start Docker if not available
3. **crawl4ai ONLY** - NO WebFetch, NO WebSearch for scraping
4. **Solidity focus** - Discard images, focus on Solidity/security content
5. **Parallel execution** - Spawn multiple subagents to speed up processing
6. **Existing crawled data** - 38 sources already downloaded in `.true_vkg/crawl_cache/`

---

## DISCOVERED STATUS

### Already Crawled (38 sources in `.true_vkg/crawl_cache/snapshots/`):

```
aave-docs, ackee, arbitrum-docs, building-secure-contracts, cantina,
capture-the-ether, code4rena, compound-docs, consensys-diligence, cyfrin,
damn-vulnerable-defi, defi-vulns, eips, ethernaut, hackernoon-web3-security,
immunefi, medium-blockchain-security, mixbytes, not-so-smart-contracts,
openzeppelin, openzeppelin-audits, openzeppelin-docs, peckshield, rekt,
samczsun, secureum, sherlock, slither-detector-docs, slowmist, solcurity,
solodit, spearbit, swc-registry, trailofbits, uniswap-docs, yearn-docs,
zellic, zksync-docs
```

### Processing Status:
- **Downloaded:** 38/87 sources (44%)
- **Processed (extracted):** 0/38 (0%) ← **NEED TO DO THIS**
- **Integrated into VulnDocs:** 0/38 (0%)

---

## CORRECTED WORKFLOW

### Phase 1: Setup (DONE)

✅ Docker installed and running (OrbStack)
✅ 38 sources already crawled with crawl4ai
✅ Snapshots in `.true_vkg/crawl_cache/snapshots/`

### Phase 2: Create Tools

- [ ] Create `scripts/crawl4ai_wrapper.sh` for easy crawling
- [ ] Create `scripts/process_crawl_batch.sh` for batch processing
- [ ] Document tool usage in Phase 17

### Phase 3: Process Existing Crawled Data (PRIORITY)

**Strategy:** Spawn 4 parallel `knowledge-aggregation-worker` subagents

**Subagent Assignment:**

| Subagent | Sources (Count) | Focus |
|----------|----------------|-------|
| 1 | 10 sources | Vulnerability DBs (solodit, rekt, slowmist, immunefi, defi-vulns) + Audit Contests (code4rena, sherlock, cantina) |
| 2 | 10 sources | Audit Firms (trailofbits, openzeppelin-audits, consensys-diligence, cyfrin, spearbit, peckshield, zellic, mixbytes, ackee) |
| 3 | 10 sources | Education + CTFs (secureum, swc-registry, damn-vulnerable-defi, ethernaut, capture-the-ether, samczsun, hackernoon-web3-security, medium-blockchain-security) |
| 4 | 8 sources | Technical (slither-detector-docs, solcurity, building-secure-contracts, not-so-smart-contracts, openzeppelin-docs, eips) + Protocol Docs (aave-docs, compound-docs, uniswap-docs, yearn-docs, arbitrum-docs, zksync-docs) |

**Each subagent will:**
1. Read assigned snapshot markdown files
2. Extract vulnerability signals (7 components per vuln)
3. Make ACCEPT/MERGE/REJECT/CREATE decisions
4. Integrate into VulnDocs structure
5. Generate patterns where applicable
6. Log progress to `.true_vkg/discovery/subagent_{N}_log.yaml`

### Phase 4: Crawl Remaining Sources (49 sources)

**After Phase 3 complete**, crawl remaining 49/87 sources using crawl4ai:

**Tier 1-2 Remaining (6 sources):**
- [ ] DefiLlama Hacks
- [ ] CodeHawks
- [ ] Secure3
- [ ] Hats Finance

**Tier 3 Remaining (10 sources):**
- [ ] Sigma Prime
- [ ] Dedaub
- [ ] CertiK
- [ ] Quantstamp
- [ ] Runtime Verification
- [ ] yAudit
- [ ] ChainSecurity
- [ ] Halborn
- [ ] BlockSec
- [ ] Nethermind
- [ ] a16z Crypto

**Tier 4-10 Remaining (33 sources):**
- Security Researchers (cmichel, Tincho, Patrick Collins, officer_cia, pcaversaccio, transmissions11, 0xWeiss, Christoph Michel, Josselin Feist, Gustavo Grieco, Mudit Gupta)
- Educational Resources (Smart Contract Programmer, Owen Thurm, Andy Li, BSDB, Solidity by Example)
- GitHub Repos (Web3Bugs, immunefi Web3 Security Library, smart-contract-sanctuary)
- Protocol Docs (MakerDAO, Curve, Balancer, Chainlink)
- Formal Verification (Certora, Halmos, Echidna, Foundry Invariants, Scribble)
- Emerging/L2 (Optimism, LayerZero, ERC-4337, Flashbots, EigenLayer)

### Phase 5: Validation & Cleanup

- [ ] Run integration tests
- [ ] Validate all VulnDocs files
- [ ] Generate patterns for all documented vulns
- [ ] Update TRACKER.md
- [ ] Clean up cache files

---

## TOOL: crawl4ai Wrapper

**Location:** `scripts/crawl4ai_wrapper.sh`

```bash
#!/bin/bash
# Crawl4AI Docker Wrapper for Phase 17

URL="$1"
SOURCE_ID="$2"
OUTPUT_DIR=".true_vkg/crawl_cache"

if [ -z "$URL" ] || [ -z "$SOURCE_ID" ]; then
    echo "Usage: $0 <url> <source_id>"
    exit 1
fi

# Ensure Docker is running
if ! docker ps >/dev/null 2>&1; then
    echo "Starting Docker..."
    open -a OrbStack
    sleep 5
fi

# Check if crawl4ai container exists
if ! docker ps -a | grep -q crawl4ai; then
    echo "Pulling crawl4ai image..."
    docker pull unclecode/crawl4ai:latest
fi

# Start container if not running
if ! docker ps | grep -q crawl4ai; then
    echo "Starting crawl4ai container..."
    docker run -d -p 11235:11235 --name crawl4ai unclecode/crawl4ai:latest
    sleep 3
fi

# Crawl URL
TIMESTAMP=$(date -u +"%Y-%m-%dT%H-%M-%S")
OUTPUT_FILE="${OUTPUT_DIR}/${SOURCE_ID}_${TIMESTAMP}.json"

echo "Crawling ${URL}..."
curl -X POST http://localhost:11235/crawl \
  -H "Content-Type: application/json" \
  -d "{
    \"url\": \"${URL}\",
    \"source_id\": \"${SOURCE_ID}\",
    \"js_code\": [],
    \"wait_for\": \"\"
  }" \
  -o "${OUTPUT_FILE}"

echo "Saved to: ${OUTPUT_FILE}"
```

---

## PARALLEL SUBAGENT INVOCATION

```bash
# Spawn 4 parallel knowledge-aggregation-worker subagents

# Subagent 1: Process sources 1-10
Task(
  subagent_type="knowledge-aggregation-worker",
  description="Process Tier 1-2: Vuln DBs + Contests",
  prompt="""
    Process these 10 sources from .true_vkg/crawl_cache/snapshots/:
    solodit, rekt, slowmist, immunefi, defi-vulns,
    code4rena, sherlock, cantina, openzeppelin-audits, trailofbits

    For EACH source:
    1. Read all markdown files in source directory
    2. Extract vulnerabilities (7 components each)
    3. Make ACCEPT/MERGE/REJECT/CREATE decisions
    4. Integrate into VulnDocs
    5. Generate patterns
    6. Log to .true_vkg/discovery/subagent_1_log.yaml
  """,
  run_in_background=true
)

# Subagent 2: Process sources 11-20
Task(
  subagent_type="knowledge-aggregation-worker",
  description="Process Tier 3: Audit Firms",
  prompt="""
    Process these 10 sources from .true_vkg/crawl_cache/snapshots/:
    consensys-diligence, cyfrin, spearbit, peckshield, zellic,
    mixbytes, ackee, openzeppelin, openzeppelin-docs, slither-detector-docs

    [Same instructions as Subagent 1]
    Log to .true_vkg/discovery/subagent_2_log.yaml
  """,
  run_in_background=true
)

# Subagent 3: Process sources 21-30
Task(
  subagent_type="knowledge-aggregation-worker",
  description="Process Tier 4-6: Education + CTFs",
  prompt="""
    Process these 10 sources from .true_vkg/crawl_cache/snapshots/:
    secureum, swc-registry, damn-vulnerable-defi, ethernaut,
    capture-the-ether, samczsun, hackernoon-web3-security,
    medium-blockchain-security, solcurity, building-secure-contracts

    [Same instructions as Subagent 1]
    Log to .true_vkg/discovery/subagent_3_log.yaml
  """,
  run_in_background=true
)

# Subagent 4: Process sources 31-38
Task(
  subagent_type="knowledge-aggregation-worker",
  description="Process Tier 7-10: Docs + Technical",
  prompt="""
    Process these 8 sources from .true_vkg/crawl_cache/snapshots/:
    not-so-smart-contracts, eips, aave-docs, compound-docs,
    uniswap-docs, yearn-docs, arbitrum-docs, zksync-docs

    [Same instructions as Subagent 1]
    Log to .true_vkg/discovery/subagent_4_log.yaml
  """,
  run_in_background=true
)
```

---

## SUCCESS CRITERIA

- [ ] All 38 existing crawled sources processed
- [ ] Remaining 49 sources crawled and processed
- [ ] All vulnerabilities extracted and integrated
- [ ] Patterns generated for detectable vulnerabilities
- [ ] VulnDocs complete with 100+ specific vulnerabilities
- [ ] Zero manual WebFetch/WebSearch usage
- [ ] All work done by subagents (not main agent)

---

## NEXT STEPS (Immediate)

1. **Create crawl4ai wrapper tool**
2. **Spawn 4 parallel subagents** to process existing 38 sources
3. **Monitor subagent progress** via log files
4. **Aggregate results** after completion
5. **Crawl remaining 49 sources** using wrapper tool
6. **Process new sources** with subagents
7. **Final validation** and TRACKER update

---

*Phase 17 Execution Plan V2 | Corrected with User Constraints | 2026-01-09*
