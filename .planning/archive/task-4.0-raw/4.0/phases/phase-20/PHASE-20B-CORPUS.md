# Phase 20.B: Real-World Corpus and Ground Truth

**Goal:** Build the largest, most realistic test corpus and create reliable ground truth labels.

---

## B.1 Corpus Requirements

The corpus must include:
- Audited contracts (known findings)
- Exploited contracts (postmortems)
- Open-source repos (with and without known bugs)
- Proxy and upgradeable systems
- Multi-contract protocols (governance + treasury + token)

Minimum targets:
- 20+ protocols
- 100+ contracts
- 200+ known findings
- 200+ known safe functions (false-positive control)

---

## B.2 Required Source Types

- Audit platforms: Solodit, Code4rena, Sherlock
- Incident reports: Immunefi, Rekt News
- Official docs: Solidity docs, OpenZeppelin advisories
- Standards/checklists: SWC, SCSVS, EthTrust

### B.2.1 Known-Ground-Truth Suites (Preferred)

Use suites where the vulnerability set is complete or nearly complete:

- Damn Vulnerable DeFi (latest, The Red Guild): `https://github.com/theredguild/damn-vulnerable-defi`
- Damn Vulnerable DeFi v3 baseline: `https://github.com/tinchoabbate/damn-vulnerable-defi` (tag/branch `v3.0.0`)
- Ethernaut (OpenZeppelin CTF): `https://github.com/OpenZeppelin/ethernaut`
- Paradigm CTF 2021/2022/2023: `https://github.com/paradigmxyz/paradigm-ctf-2021`,
  `https://github.com/paradigmxyz/paradigm-ctf-2022`, `https://github.com/paradigmxyz/paradigm-ctf-2023`
- SmartBugs Curated (academic ground truth): `https://github.com/smartbugs/smartbugs-curated`
- Not So Smart Contracts (classic vuln suite): `https://github.com/crytic/not-so-smart-contracts`
- SWC Registry (per-SWC PoCs): `https://github.com/SmartContractSecurity/SWC-registry`

### B.2.2 Audit-Backed Protocols (Partial Ground Truth)

Use the local ground-truth set in `validation/ground-truth/`:

- Uniswap v3 (Trail of Bits, ABDK)
- Compound v3
- ENS
- Yearn v3
- Blur Exchange

### B.2.3 Exploit Reproduction Corpora (Partial)

- DeFiHackLabs (real exploit PoCs): `https://github.com/SunWeb3Sec/DeFiHackLabs`

### B.2.4 PoC Libraries and Micro-Cases (Partial)

Use these for targeted stress tests and edge-case logic checks:

- Smart Contract Attack Vectors: `https://github.com/harendra-shakya/smart-contract-attack-vectors`
- CryptoVulhub exploit PoCs: `https://github.com/Rivaill/CryptoVulhub`
- Smart Contract Vulnerabilities (catalog + examples):
  `https://github.com/kadenzipfel/smart-contract-vulnerabilities`
- ConsenSys Academy Bootcamp security modules:
  `https://github.com/ConsenSys-Academy/Blockchain-Developer-Bootcamp`

### B.2.5 Audit-Backed Repos With In-Repo Reports (Recent)

Prefer repos that include their audit reports alongside code so the
ground truth can be pinned to a commit snapshot.

- Taiko protocol + Code4rena report:
  `https://github.com/taikoxyz/taiko-mono` (audit report in repo)
- Reserve protocol + Code4rena report:
  `https://github.com/reserve-protocol/protocol` (audit report in repo)
- Alchemix v2 contest target:
  `https://github.com/alchemix-finance/v2-foundry` (pair with contest findings)

### B.2.6 Findings Indexes (Map to Code Snapshots)

Use these to locate high-severity logic/auth issues and map them to
protocol repos at the vulnerable commit.

- Immunefi Past Audit Competitions:
  `https://github.com/immunefi-team/Past-Audit-Competitions`
- Pashov audits (reports + PoCs):
  `https://github.com/pashov/audits`
- MixBytes audits (reports):
  `https://github.com/mixbytes/audits_public`

### B.2.7 Curated 2025 High-Risk Logic/Auth Targets (Preferred)

Use these when you need non-trivial logic or authorization failures
with explicit high-risk findings:

- Virtuals Protocol (Code4rena 2025-04)
  - Repo: `https://github.com/code-423n4/2025-04-virtuals-protocol`
  - Report: `https://code4rena.com/reports/2025-04-virtuals-protocol`
  - High-risk examples:
    - Lack of access control in `AgentNftV2::addValidator()`
    - Anyone can control a user's delegate via `AgentVeToken.stake()` with 1 wei
    - Public `ServiceNft::updateImpact` leads to cascading issues

- Blackhole (Code4rena 2025-05)
  - Repo: `https://github.com/code-423n4/2025-05-blackhole`
  - Report: `https://code4rena.com/reports/2025-05-blackhole`
  - High-risk examples:
    - Router address validation logic error prevents valid router assignment
    - Reward token in `GaugeFactoryCL` can be drained by anyone

- Sequence (Code4rena 2025-10)
  - Repo: `https://github.com/code-423n4/2025-10-sequence`
  - Report: `https://code4rena.com/reports/2025-10-sequence`
  - High-risk examples:
    - Chained signature with checkpoint usage disabled bypasses validation
    - Partial signature replay / frontrunning on session calls

- Hybra Finance (Code4rena 2025-10)
  - Repo: `https://github.com/code-423n4/2025-10-hybra-finance`
  - Report: `https://code4rena.com/reports/2025-10-hybra-finance`
  - High-risk example:
    - Assets deposited before share calculation cause under-minted shares

- Panoptic Hypovault (Code4rena 2025-06)
  - Repo: `https://github.com/code-423n4/2025-06-panoptic`
  - Report: `https://code4rena.com/reports/2025-06-panoptic-hypovault`
  - High-risk examples:
    - `poolExposure` for token1 miscalculated as shortPremium - longPremium
    - NAV calculation inconsistency due to underlying token position

**Local clone names (from download script):**
- `c4-2025-04-virtuals`
- `c4-2025-05-blackhole`
- `c4-2025-06-panoptic`
- `c4-2025-10-sequence`
- `c4-2025-10-hybra`

---

## B.3 Corpus Composition Targets

- At least 5 protocols with real exploit history
- At least 5 protocols with upgradeable proxies
- At least 3 bridges or cross-chain systems
- At least 3 governance-heavy protocols
- At least 3 oracle-heavy protocols
- At least 25 logic/auth findings at medium/high/critical severity
- At least 10 findings tagged as “permission drift” or “business logic mismatch”

---

## B.4 Ground Truth Protocol

1. Extract findings from reports and map to:
   - category
   - subcategory
   - specific vulnerability
2. For each finding, store:
   - source URL
   - affected contracts/functions
   - exploit steps
   - impact
3. Label safe samples explicitly to measure false positives.

---

## B.5 Corpus Manifest Template

Store in `task/4.0/phases/phase-20/artifacts/CORPUS_MANIFEST.md`:

```
- protocol: <name>
  repo_url: <url>
  category: <lending|dex|bridge|nft|governance|infra>
  contracts: <count>
  findings: <count>
  safe_samples: <count>
  reports:
    - <audit/report url>
```

---

## B.6 Ground Truth Template

Store in `task/4.0/phases/phase-20/artifacts/GROUND_TRUTH.md`:

```
- id: GT-001
  protocol: <name>
  contract: <file.sol>
  function: <fn>
  vuln_category: <category>
  vuln_subcategory: <subcategory>
  specific_vuln: <specific name>
  severity: <high|critical|medium|low>
  exploit_summary: <short>
  source: <url>
  behavioral_signature: <sig>
  semantic_operations: [op1, op2]
  evidence_locations: [path:line]
```

---

## B.7 Quality Checks

- [ ] At least 30 percent of corpus is safe code
- [ ] Every category has at least 10 findings
- [ ] At least 5 protocols have real exploit history
- [ ] At least 5 protocols are upgradeable/proxy-based
- [ ] Every finding maps to a specific vulnerability
- [ ] At least 10 findings are logic/auth “non-obvious” cases (not trivial access checks)

---

## B.8 PHILOSOPHY Alignment (Behavior-First Labels)

For every ground truth item, add the following annotations:

- **Behavioral signature** (e.g., `R:bal -> X:out -> W:bal`)
- **Semantic operations** involved (from PHILOSOPHY core vocabulary only)
- **Evidence pointers** (code locations + graph signals)

Ground truth is invalid without behavior-first annotations.

---

## B.9 Corpus Download and Refresh Plan

1. Run the download script to fetch the latest corpora:
   - `scripts/download_benchmark_corpus.sh .vrs/benchmarks/corpora`
2. Record repository URL, commit hash, and dataset size in
   `task/4.0/phases/phase-20/artifacts/CORPUS_MANIFEST.md`.
3. Refresh quarterly and whenever a new major CTF or exploit suite drops.
4. Add new sources only if they provide explicit ground truth or
   audit-backed findings.
5. For offline runs, re-clone with `STRIP_GIT=1` to remove history.

---

## B.10 Real-Time Logic/Auth Test Pack

Use the time-boxed pack for complex, less-obvious logic and
authorization flaws:

- `task/4.0/phases/phase-20/REALTIME_LOGIC_AUTH_TEST_PACK.md`

Prioritize recent audit-backed repos and contest targets that include
high/critical permission drift or business-logic mismatches.
