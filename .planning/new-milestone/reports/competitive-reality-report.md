# T6: Competitive Reality Report

**Date:** 2026-02-08
**Version:** 2.0 (expanded with Feb 2026 research)
**Confidence Level:** HIGH (web research + codebase analysis + prior internal audit)

---

## Executive Summary

AlphaSwarm.sol occupies a **genuinely novel niche** — Claude Code orchestration for multi-agent smart contract security — but its competitive position is weaker than internal documentation suggests. The gap between architecture and evidence is the core problem.

**The honest picture:**
- Tool integration is **solid and complete** (runs Slither/Mythril/Aderyn with real orchestration value)
- The BSKG knowledge graph is the **strongest genuine differentiator** but unproven in benchmarks
- Multi-agent debate is **architecturally interesting** but relies on rented orchestration (Claude Code)
- The pattern library (562 YAML files) is **large but unvalidated** — only 80/562 have explicit status ratings, and only ~6 patterns have evidence of working correctly
- **No public benchmarks exist** comparing AlphaSwarm to any competitor
- **No real-world vulnerability has been discovered** — meanwhile Sherlock AI found a $2.4M bug on mainnet
- Academic research (LLM-SmartAudit in IEEE TSE, CKG-LLM, Agent4Vul) is converging on similar multi-agent + knowledge-graph approaches, creating a narrowing window for differentiation

**The competitive reality: AlphaSwarm is an ambitious orchestration framework with ~6 proven detection patterns. Slither alone has 100 battle-tested detectors. Sherlock AI has already found real bugs on mainnet. LLM-SmartAudit has published in top-tier venues.**

**Rating: 5/10** — Genuinely innovative architecture, but zero external evidence of superiority over running existing tools directly.

---

## Tool Landscape (Feb 2026)

### Slither (Trail of Bits)

**The dominant tool. Industry standard. Period.**

| Metric | Value |
|--------|-------|
| Detectors | 100 built-in |
| Parse success | 99.9% of public Solidity |
| Speed | < 1 second per contract |
| GitHub stars | 6,100+ |
| SmartBugs recall | 48% (highest among static tools) |
| SmartBugs precision | 20% (392 false positives / 100 true positives) |
| Reentrancy recall | 93.5% |
| Maturity | 7+ years, actively maintained |
| Framework support | Hardhat, Foundry, Truffle auto-detected |

**What Slither actually detects:**
- Reentrancy (5 variants: eth, no-eth, benign, events, read-before-write)
- Access control (arbitrary sends, tx.origin, suicidal contracts)
- Uninitialized state/storage/local variables
- Unchecked return values (transfer, low-level, send)
- Arithmetic (divide-before-multiply, incorrect shift)
- Proxy/upgrade issues (unprotected upgrade)
- Dangerous patterns (selfdestruct, delegatecall-in-loop)
- Shadowing, dead code, unused variables

**Critical note:** Slither's SlithIR already does behavioral analysis via intermediate representation — it's not naive string matching. The AlphaSwarm BSKG is more sophisticated, but Slither is not as simple as AlphaSwarm's docs suggest.

**Relevance to AlphaSwarm:** AlphaSwarm uses Slither's Python API directly as its graph builder foundation. The BSKG is built ON TOP of Slither's AST. This means AlphaSwarm inherits both Slither's strengths (comprehensive AST) and limitations (same parse).

### Mythril (ConsenSys Diligence)

| Metric | Value |
|--------|-------|
| SmartBugs recall | 53% (highest single-tool recall) |
| Approach | Symbolic execution + SMT solving (Z3) |
| Analysis depth | Configurable (default max-depth: 22) |
| Speed | Slow (minutes to hours per contract) |
| Maturity | 7+ years |
| Key strength | Generates concrete exploit inputs |

**What Mythril finds that static analysis misses:**
- Path-dependent vulnerabilities (conditional execution chains)
- Concrete exploit generation (specific input values that trigger bugs)
- Bytecode-level analysis (works without source code)

**Weaknesses:** Path explosion on complex contracts, very slow, resource-intensive, limited to SWC categories.

**Relevance to AlphaSwarm:** Mythril integrated as secondary validator via CLI adapter. AlphaSwarm adds parallel execution, timeout management, and finding normalization — genuine value-add.

### Aderyn (Cyfrin)

| Metric | Value |
|--------|-------|
| Detectors | 100+ built-in |
| Language | Rust (very fast) |
| IDE integration | VS Code extension with real-time detection |
| Focus | Foundry-optimized |
| Maturity | 2024-2026, rapidly growing |
| Key feature | Inline diagnostics with tooltips |

**2025 developments:** Cyfrin released the Aderyn VS Code Extension — real-time static analysis in-editor with project-wide vulnerability tree-view. All analysis runs locally.

**Note:** OpenZeppelin Defender is sunsetting (final shutdown July 2026), creating a gap in integrated security platforms.

---

## AI-Powered Competitors (The Real Threat)

### Sherlock AI (Beta, launched Sept 2025)

**The most commercially significant AI security tool.**

| Aspect | Details |
|--------|---------|
| Training data | Top Web3 security researchers' knowledge |
| Integration | Built into Sherlock audit contest platform |
| Real-world proof | **Found Critical vulnerability affecting $2.4M in live lending protocol** |
| Positioning | Augmentation layer alongside human auditors |
| Metrics published | None (no precision/recall data) |

**Significance:** First known instance of an AI uncovering a multi-million-dollar bug on mainnet. This is the credibility bar AlphaSwarm must clear.

### LLM-SmartAudit (IEEE TSE, Oct 2025)

**Academic framework most architecturally similar to AlphaSwarm.**

| Aspect | Details |
|--------|---------|
| Publication | IEEE Transactions on Software Engineering (top-tier) |
| Approach | Multi-agent conversational architecture + buffer-of-thought |
| Accuracy | 98% on common vulnerabilities |
| CVE detection | 12/13 CVEs identified, surpassing other LLM methods |
| Agents | Specialized collaborative agents iteratively refine assessments |

**Why this matters for AlphaSwarm:** This is essentially AlphaSwarm's multi-agent concept — published in a top venue with metrics. AlphaSwarm has no publication and no metrics.

### CKG-LLM (arXiv, Dec 2025)

**Knowledge graph + LLM for vulnerability detection — directly overlaps AlphaSwarm's core approach.**

| Aspect | Details |
|--------|---------|
| Approach | Knowledge graphs + LLM queries for access control vulnerability detection |
| Method | Translates NL vulnerability patterns into executable queries over contract KGs |
| Focus | Access control vulnerabilities |
| Status | Research paper (Dec 2025) |

**Why this matters:** This is conceptually the same as AlphaSwarm's BSKG + pattern queries. The differentiation window is closing.

### Other Notable Tools

| Tool | Approach | Key Metric | Status |
|------|----------|-----------|--------|
| **LLMBugScanner** (Georgia Tech) | Ensemble of 5 fine-tuned LLMs | 60% top-5 accuracy, ~10% hallucination | Research |
| **SmartLLM** | LLaMA 3.1 + RAG | 100% recall, 70% accuracy | Research |
| **Agent4Vul** | Multimodal LLM agents | Commentator + Vectorizer agents | Published (Springer) |
| **Smartify** | Multi-agent repair framework | Detects + repairs vulnerabilities | Research |
| **AuditBase** | LLM-based, trained on 13K+ issues | "90% value of traditional audit in 30 seconds" | Commercial |

### Graph-Based Academic Tools

Multiple research teams pursuing graph-based analysis that overlaps AlphaSwarm's approach:

| Method | Approach | Reentrancy Accuracy |
|--------|----------|---------------------|
| GNN + Expert Knowledge (2021) | CFG/DFG → GNN | 89.15% |
| HGAT (2023) | AST/CFG → hierarchical graph attention | 93.72% |
| SCVHunter (2024) | Heterogeneous graph attention | ~90% |
| CKG-LLM (Dec 2025) | Knowledge graph + LLM queries | N/A |
| CTVD (2025) | Comprehensive code graph + temporal | 92.19% |
| SliSE (2024) | Combined symbolic + static | 78.65% F1 |

---

## AlphaSwarm's Actual Position

### What It Claims (From CLAUDE.md)

1. "Multi-agent orchestration framework for smart contract security"
2. "Human-like security assessments that go far beyond static analysis"
3. "Complex authorization bugs, logic flaws, and novel vulnerabilities"
4. "Graph-first reasoning + economic protocol context"
5. "680+ vulnerability detection patterns"
6. "World's best AI-powered Solidity security tool"

### What It Can Prove

| Claim | Evidence | Verdict |
|-------|----------|---------|
| Runs external tools | `runner.py` subprocess execution, parallel thread pool | **PROVEN** |
| Builds knowledge graph | `builder/core.py` Slither integration, 50+ properties/function | **PROVEN** |
| 562 YAML patterns exist | File count verified | **PROVEN** (not 680+) |
| Patterns are validated | Only 80/562 have status ratings; ~6 have evidence of working | **WEAKLY PROVEN** |
| Multi-agent debate works | Data structures in `orchestration/` exist | **UNPROVEN** (rented from Claude Code) |
| Better than running tools directly | No benchmarks | **UNPROVEN** |
| Finds novel vulnerabilities | No published findings | **UNPROVEN** |
| "Human-like" assessments | No comparison data | **UNPROVEN** |
| "84.6% DVDeFi detection rate" | YAML annotation, not measured result | **UNSUBSTANTIATED** |

### Real Differentiators (Genuinely Working)

1. **Behavioral Semantic Knowledge Graph (BSKG)**
   - 50+ function properties extracted from Slither AST (208 semantic properties computed)
   - Semantic operations (TRANSFERS_VALUE_OUT, CHECKS_PERMISSION, etc.)
   - Natural language query interface
   - **Strongest genuine differentiator** — no commercial tool does exactly this
   - BUT: Only 172/562 patterns actually use computed properties; 385+ reference non-existent properties
   - AND: CKG-LLM (Dec 2025) is exploring same knowledge graph + LLM approach

2. **Intelligent Tool Coordination**
   - Project-aware tool selection (proxy detection, DeFi pattern matching)
   - Parallel execution with grouped I/O vs compute (max 4 workers)
   - Pattern skip optimization (80% precision threshold for tool-pattern dedup)
   - Idempotent execution with on-disk caching
   - **This is real, working, tested engineering**

3. **Claude Code Orchestration Pattern**
   - 47 production skills for security workflows
   - Structured debate protocol (attacker/defender/verifier)
   - Evidence packet format with graph traceability
   - Persistent investigation pools with budget tracking
   - No competitor has this specific integration pattern (yet)
   - BUT: Claude Flow, Agentrooms, and others building similar frameworks

4. **VulnDocs Pattern Library**
   - 562 YAML-defined patterns across 20+ vulnerability categories
   - Semantic, name-agnostic detection approach
   - Two-tier detection (Tier A deterministic + Tier B LLM-verified)
   - BUT: Quality distribution is **dismal**:
     - 16 rated "excellent"
     - 25 rated "ready"
     - 15 rated "draft"
     - 20 rated "deprecated"
     - **482 have no rating at all** (86%)

### Unfounded Claims

| Claim | Why It's Unfounded |
|-------|-------------------|
| "World's best AI-powered Solidity security tool" | No benchmarks, no comparisons, no external validation |
| "Far beyond static analysis" | Core detection uses Slither (static analysis) |
| "Finds novel vulnerabilities" | Zero published discovered vulnerabilities (Sherlock AI found $2.4M bug) |
| "680+ patterns" | Actual count is 562; 385+ reference non-existent properties |
| "Human-like assessments" | No evidence of human-comparable performance |
| "84.6% DVDeFi detection rate" | YAML annotation, DVDeFi ground truth file is TODO placeholders |

---

## Feature Comparison Matrix

| Feature | Slither | Aderyn | Mythril | Sherlock AI | LLM-SmartAudit | AlphaSwarm |
|---------|---------|--------|---------|-------------|----------------|------------|
| **Working detectors** | 100 | 100+ | ~35 | Unknown | Unknown | ~6 proven |
| **Years in production** | 7+ | 2+ | 7+ | 0.5 | 0 (research) | 0 |
| **Real-world validation** | Thousands of audits | Growing | Industry + academic | $2.4M bug found | IEEE TSE publication | None |
| **Speed** | < 1 sec | Seconds | Minutes-hours | Real-time | Research | Minutes |
| **Published benchmarks** | SmartBugs, papers | Growing | SmartBugs, papers | None (yet) | IEEE TSE paper | None |
| **CI/CD integration** | Yes | Yes (VS Code, CLI) | Yes | Yes | N/A | No |
| **Cross-function analysis** | Limited | Limited | Path-sensitive | Unknown | Multi-agent | Architecture exists |
| **LLM reasoning** | No | No | No | Yes | Yes | Architecture exists |
| **Multi-agent debate** | No | No | No | No | Yes (similar) | Architecture exists |
| **Knowledge graph** | No (SlithIR is close) | No | No | Unknown | No | Yes (BSKG) |
| **Cost** | Free | Free | Free | Platform fee | N/A | Claude API costs |

**Pattern:** AlphaSwarm's differentiation is consistently in "architecture exists" — features designed but not proven.

---

## Industry Benchmarks

### SmartBugs Curated Dataset (Standard Benchmark)

143 contracts, 206 tagged vulnerabilities. Published tool results:

| Tool | True Positives | Precision | Recall | F1 |
|------|---------------|-----------|--------|-----|
| Slither | 100 | 0.20 | 0.48 | 0.28 |
| Mythril | — | — | 0.53 | — |
| Confuzzius | — | 0.34 | 0.45 | 0.39 (best) |
| **AlphaSwarm** | **Unknown** | **Unknown** | **Unknown** | **Unknown** |

**AlphaSwarm has never been evaluated on any standard benchmark.**

### AI Tool Performance (Reported Metrics)

| Tool/Study | Accuracy | Recall | FP Rate | Benchmark | Venue |
|------------|----------|--------|---------|-----------|-------|
| LLM-SmartAudit | 98% | — | — | Common vulns | IEEE TSE |
| SmartLLM | 70% | 100% | — | Reentrancy + AC | arXiv |
| LLMBugScanner | 60% (top-5) | — | ~10% hallucination | 775 contracts | Help Net Security |
| AI Agent (study) | 84% | — | 12% | SWC 174 types | DEV article |
| Human auditor (study) | 78% | — | 8% | Same benchmark | DEV article |
| AI + Human (study) | 94% | — | 4% | Same benchmark | DEV article |
| CTVD (2025) | 92.19% (reentrancy) | — | — | Custom | ScienceDirect |
| **AlphaSwarm** | **No data** | **No data** | **No data** | **Never tested** | **None** |

### Recent Benchmark Developments

- **ReEP Framework (2024):** Combined 8 tools, improved precision from 0.5% to 73% without sacrificing recall, max 83.6% with multi-tool integration
- **SliSE (2024):** F1 score 78.65%, recall > 90% (dramatically better than any individual tool's 9.26% F1)
- **Insight:** Tool combination works. But AlphaSwarm hasn't proven its combination is better than simpler ensembles.

---

## Gap Analysis

### What AlphaSwarm Needs to Actually Compete

**Tier 1: Critical Gaps (Must fix for credibility)**

| Gap | Why It Matters | Current State |
|-----|---------------|---------------|
| **No public benchmarks** | Cannot claim superiority without data | Phase 07.3.5 planned, never executed |
| **No SmartBugs evaluation** | Standard benchmark all tools are measured against | Never run |
| **No real-world finding** | Sherlock AI found $2.4M bug; AlphaSwarm has 0 discoveries | Zero |
| **Pattern quality unknown** | 482/562 patterns have no rating | 86% unrated |
| **No comparison data** | "Better than Slither alone" is unproven | Never tested |
| **No publication** | LLM-SmartAudit has IEEE TSE; AlphaSwarm has nothing | Zero academic presence |

**Tier 2: Competitive Gaps (Needed to differentiate before window closes)**

| Gap | Why It Matters |
|-----|---------------|
| **CKG-LLM convergence** | Knowledge graph + LLM approach published Dec 2025; differentiation narrowing |
| **Standalone execution** | Requires Claude Code (paid API) — limits accessibility vs free tools |
| **No continuous monitoring** | Sherlock AI runs in real-time; AlphaSwarm is batch-only |
| **DeFi-specific reasoning** | Claims economic context but unclear if implemented beyond architecture |
| **Cross-contract analysis** | Most tools limited here — real opportunity, but unproven |

**Tier 3: Market Gaps**

| Gap | Why It Matters |
|-----|---------------|
| IDE integration | Aderyn has VS Code real-time; AlphaSwarm doesn't |
| Foundry native integration | Foundry is dominant framework |
| Community/brand | Zero public presence, no users, no mindshare |

---

## Market Reality

### Demand

**Yes, strong and growing:**
- $3.8B lost to smart contract exploits in 2024-2025
- Audit firms have multi-month backlogs
- AI-augmented auditing actively deployed (Sherlock AI)
- Research community publishing heavily on LLM + smart contract security
- OpenZeppelin Defender shutting down (July 2026) creates platform gap
- Key insight from research: "AI agents + humans > either alone"

### What Users Actually Need

| Need | Priority | AlphaSwarm Covers? |
|------|----------|-------------------|
| Fewer false positives | Highest | Partially (debate architecture, unproven) |
| Business logic bugs | High | Claimed but unproven |
| Faster than manual audit | High | Yes (tool orchestration) |
| Continuous monitoring | High | No |
| Proven track record | High | No |
| Integrated into workflow | Medium | Yes (Claude Code) |
| Affordable | Medium | Depends on API costs |
| Standard benchmarks | Medium | No |

### Competitive Moat Assessment

| Moat Factor | Strength | Notes |
|-------------|----------|-------|
| BSKG graph | **Medium** (narrowing) | Novel but CKG-LLM (Dec 2025) converging |
| Claude Code integration | **Low** | Others building similar (Claude Flow, Agentrooms) |
| Pattern library | **Medium** (if validated) | Large but 86% unrated; proprietary knowledge base |
| Multi-agent debate | **Low** | LLM-SmartAudit published similar in IEEE TSE |
| Tool coordination | **Medium** | Real engineering value, but not defensible long-term |
| Brand/reputation | **None** | No public presence, no users, no publications |

---

## Honest Verdict

### Where AlphaSwarm Really Stands: 5/10

| Dimension | Score | Reasoning |
|-----------|-------|-----------|
| **Architecture** | 8/10 | BSKG + multi-agent + Claude Code is genuinely novel and well-designed |
| **Implementation** | 7/10 | Real code that runs; tools integration is solid |
| **Proven Effectiveness** | 2/10 | No benchmarks, no published findings, no external validation |
| **Competitive Position** | 4/10 | Unique niche but competitors converging fast (CKG-LLM, LLM-SmartAudit) |
| **Market Readiness** | 3/10 | Requires paid API, no standalone mode, no continuous monitoring |
| **Pattern Quality** | 3/10 | 562 patterns, ~6 proven working, 385+ reference missing properties |
| **Community/Brand** | 1/10 | Zero public presence, zero users, zero publications |

**Overall: 5/10** — Technically interesting framework with genuine innovation, but zero external evidence that it works better than running Slither + Mythril + human review directly.

### The Uncomfortable Truths

1. **AlphaSwarm has never found a real vulnerability** that existing tools missed (or if it has, it's undocumented)
2. **Sherlock AI has already found a $2.4M bug** on mainnet — that's the credibility bar
3. **LLM-SmartAudit published in IEEE TSE** with a conceptually similar multi-agent approach — AlphaSwarm has no academic presence
4. **CKG-LLM (Dec 2025) overlaps AlphaSwarm's core KG approach** — the differentiation window is closing
5. **Running Slither + Mythril + Aderyn directly costs $0** while AlphaSwarm adds Claude API costs with unproven ROI
6. **The ~6 proven patterns cover categories Slither already handles** (reentrancy, access control, unchecked returns) — no evidence of finding things Slither misses
7. **ReEP Framework achieved 83.6% precision** just by combining existing tools — simpler than AlphaSwarm's approach with published results

### What Would Change This Score

To reach **8/10**, AlphaSwarm would need:
- [ ] SmartBugs benchmark results showing improvement over individual tools
- [ ] At least 1 documented real-world vulnerability discovery
- [ ] All 562 patterns rated; deprecate bad ones (100 excellent patterns > 562 unknown)
- [ ] Published comparison: AlphaSwarm vs Slither-alone vs Mythril-alone
- [ ] External user validation (not just internal testing)
- [ ] Academic publication or preprint establishing priority on BSKG approach
- [ ] BSKG ablation study proving the graph actually helps LLM reasoning

---

## Recommendations for Milestone 6.0

### Priority 1: Prove It Works (Credibility)

1. **Run SmartBugs benchmark** — evaluate AlphaSwarm against the standard 143-contract dataset. Publish precision, recall, F1. Even poor results are better than no results.

2. **Find a real bug** — run against live DeFi protocols (with permission), recent audit contest targets (Code4rena, Sherlock), or known-vulnerable contracts. One documented real finding = more credibility than 562 untested patterns.

3. **Rate all patterns** — audit the 482 unrated patterns. Implement the missing 337 orphan properties to activate dead patterns. Deprecate non-functional ones. Target: 100 "ready" or better patterns.

4. **BSKG ablation study** — run the same audit with and without the knowledge graph. Prove (or disprove) that the graph helps LLM reasoning quantitatively.

### Priority 2: Differentiate (Before the window closes)

5. **Publish a preprint** — even a short paper comparing multi-agent + BSKG approach to running tools individually. Establish priority before CKG-LLM and LLM-SmartAudit ecosystems mature.

6. **Cross-contract analysis** — this is genuinely hard and few tools do it well. If AlphaSwarm can demonstrate cross-contract vulnerability detection, that's a defensible moat.

7. **DeFi-specific reasoning** — flash loans, oracle manipulation, MEV — these are the bugs that cause real losses and that static tools fundamentally cannot find. Prove this works.

### Priority 3: Ship (User access)

8. **Stop claiming superiority** — replace "world's best" with honest positioning: "Augments static analyzers with multi-agent AI reasoning." Ship a working demo.

9. **Reduce API dependency** — explore cheaper models for routine analysis, reserve Opus for complex reasoning only.

10. **Create demo flow** — `/vrs-audit` running against a known-vulnerable contract (Damn Vulnerable DeFi) with documented, reproducible output.

### What NOT to Do in Milestone 6.0

- Don't add more patterns without validating existing ones
- Don't expand to more tools without proving current integration value
- Don't claim superiority without benchmarks
- Don't build IDE integration before proving core effectiveness
- Don't compete on speed (Slither < 1s per contract — LLM calls can't beat that)
- Don't ignore CKG-LLM and LLM-SmartAudit — they are the real competitive threat, not Slither

---

## Sources

### Tool Documentation
- [Slither GitHub Repository](https://github.com/crytic/slither) — 100 detectors, 6.1k stars
- [Mythril GitHub Repository](https://github.com/ConsenSysDiligence/mythril) — Symbolic execution, Z3 solver
- [Aderyn GitHub / Cyfrin](https://github.com/Cyfrin/aderyn) — Rust-based, 100+ detectors
- [Cyfrin 2025 Wrap-Up](https://www.cyfrin.io/blog/cyfrin-2025-wrap-up-advancing-web3-security-audits-and-blockchain-education)
- [OpenZeppelin Defender Sunsetting](https://www.openzeppelin.com/news/doubling-down-on-open-source-and-phasing-out-defender) — Shutdown July 2026

### AI Security Tools
- [Sherlock AI](https://sherlock.xyz/solutions/ai) — $2.4M bug discovery, beta launched Sept 2025
- [AuditBase](https://dev.to/ohmygod/how-ai-agents-can-audit-smart-contracts-in-2026-a-technical-deep-dive-5gl) — Claims "90% audit value"
- [LLM-SmartAudit (IEEE TSE)](https://ieeexplore.ieee.org/document/11121619/) — Multi-agent, 98% accuracy
- [LLMBugScanner (Help Net Security)](https://www.helpnetsecurity.com/2025/12/19/llmbugscanner-llm-smart-contract-auditing/) — Ensemble approach, 60% top-5
- [SmartLLM (arXiv)](https://arxiv.org/abs/2502.13167) — LLaMA 3.1 + RAG, 70% accuracy
- [Agent4Vul (Springer)](https://link.springer.com/article/10.1007/s11432-024-4402-2) — Multimodal LLM agents
- [CKG-LLM (arXiv Dec 2025)](https://arxiv.org/html/2512.06846) — Knowledge graph + LLM for access control

### Benchmarks & Research
- [SmartBugs 2.0 Framework](https://www.researchgate.net/publication/375503644) — 20 tools benchmark
- [ReEP Framework (Unity is Strength)](https://arxiv.org/abs/2402.09094) — Multi-tool precision improved to 83.6%
- [GNN + Expert Knowledge](https://arxiv.org/abs/2107.11598) — Graph-based, 89% accuracy
- [HGAT Hierarchical Graph Attention](https://journalofcloudcomputing.springeropen.com/articles/10.1186/s13677-023-00459-x) — 93.72% reentrancy
- [CTVD Code Graph + Temporal](https://www.sciencedirect.com/science/article/pii/S2096720925001435) — 92.19% reentrancy
- [SCVHunter (ICSE 2024)](https://dl.acm.org/doi/10.1145/3597503.3639213) — Heterogeneous graph attention
- [SliSE (2024)](https://dl.acm.org/doi/10.1145/3643734) — F1 78.65%, recall >90%

### Market & Competition
- [AI Agents for Smart Contract Auditing 2026](https://dev.to/ohmygod/how-ai-agents-can-audit-smart-contracts-in-2026-a-technical-deep-dive-5gl) — Performance benchmarks
- [Claude Code Multi-Agent 2026](https://shipyard.build/blog/claude-code-multi-agent/) — Ecosystem overview
- [Sherlock Audit Contests](https://sherlock.xyz/audit-contests) — Competitive audit platform
