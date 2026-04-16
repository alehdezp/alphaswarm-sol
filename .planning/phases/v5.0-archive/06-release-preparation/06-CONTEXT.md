# Phase 6: Release Preparation - Context

**Gathered:** 2026-01-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Prepare AlphaSwarm.sol for public 0.5.0 release with comprehensive rebrand from "AlphaSwarm.sol" identity. This includes:
- Full rebrand to AlphaSwarm.sol with VRS (Vulnerability Reasoning System) internal naming
- Research-style documentation explaining architecture with academic rigor
- PyPI publishing, Docker images, and GitHub release automation
- Fresh install validation

Case studies, detailed walkthroughs, and performance benchmarks are deferred to post-Phase 7.

</domain>

<decisions>
## Implementation Decisions

### Naming & Identity

**Product Identity:**
- **System name:** AlphaSwarm.sol
- **Tagline:** "Behavioral vulnerability detection through semantic reasoning"
- **Full description:** Multi-agent Vulnerability Reasoning System (VRS) powered by BSKG
- **Graph name:** BSKG (Behavioral Security Knowledge Graph) — replaces "VKG"

**Rationale:** "Alpha" = finding security edge others miss. "Swarm" = multi-agent orchestration. ".sol" = Solidity-specific. BSKG differentiates from structural knowledge graphs (AST/CFG-based) used in competing approaches.

**Rebrand Scope:**

| Component | From | To |
|-----------|------|-----|
| Product name | AlphaSwarm.sol | AlphaSwarm.sol |
| Package (PyPI) | alphaswarm | alphaswarm-sol |
| Python import | `true_vkg` | `alphaswarm_sol` |
| CLI commands | `alphaswarm` | `alphaswarm` + `aswarm` |
| Config folder | `.vrs/` | `.vrs/` |
| Skills | `/vkg:*` | `/vrs-*` |
| Agents | `vkg-*` | `vrs-*` |
| Graph reference | BSKG | BSKG |

**All references updated:** docs/, .planning/, .claude/, src/, tests/, README, imports

### Positioning

- **Strategy:** Hybrid — research-style technical documentation with academic citations; product-style marketing materials
- **Competitor comparison:** No direct naming of competitors — describe AlphaSwarm capabilities and let readers draw conclusions
- **Target audiences:** Security researchers (technical docs), audit firms (product docs), developers (getting started)

### Documentation Style

**Format:** Research paper style
- Abstract
- Introduction (problem statement, contributions)
- Related Work (key differentiators only)
- Architecture (BSKG, Agents, Patterns, Orchestration)
- Conclusion

**Related Work:** 3-5 most relevant papers for differentiation:
- CKG-LLM (2025) — structural KG, access control only
- SmartGuard (2025) — LLM-enhanced, single-pass
- LLM-SmartAudit (2025) — multi-agent but no structured debate

**Evaluation:** Deferred entirely to post-Phase 7. No performance claims in 0.5.0 docs.

**Tone:** Formal academic
- Third person ("The system proposes...", "AlphaSwarm detects...")
- Passive voice where appropriate
- Technical precision over accessibility

### Architecture Narrative

**BSKG (Graph) Explanation:** Signature-centric approach
- Lead with behavioral signatures (`R:bal→X:out→W:bal`) as the novel contribution
- Emphasize ordered semantic operations over syntactic patterns
- Position as key differentiator from structural KGs (AST, CFG-based)

**Multi-Agent Debate:** Framed as "Adversarial Verification Protocol"
- Attacker agent constructs exploit paths
- Defender agent finds guards and mitigations
- Verifier agent arbitrates with evidence cross-checking
- All claims must reference code locations (evidence anchoring)

**Pattern Tiers:** Human-in-loop spectrum
- Tier A = fully automated (graph-only, deterministic)
- Tier B = LLM-assisted (exploratory, requires verification)
- Tier C = semantic reasoning required (label-dependent)

**Diagrams:** Full architecture diagram showing end-to-end flow:
```
Source → BSKG Builder → Pattern Engine → Beads → Agent Pool → Verdicts
```
Professional figure style suitable for academic publication.

### Unique Claims (No Benchmarks Yet)

**Primary differentiators to emphasize:**

1. **Behavioral Signatures** — FIRST framework to use ordered semantic operations for vulnerability detection
   - Traditional: match syntactic patterns (external call before state update)
   - AlphaSwarm: behavioral signatures encode temporal ordering of semantic operations
   - Detects vulnerabilities regardless of implementation variation

2. **Protocol Context** — ONLY framework that captures economic context for logic bug detection
   - Oracle trust assumptions
   - Role capabilities and permissions
   - Accepted risks (auto-filtered from findings)
   - Off-chain input tracking

**Evidence approach:** Architecture description only for 0.5.0. Performance claims deferred to Phase 7 validation.

### Versioning

- **Version scheme:** SemVer 0.x.0 (pre-1.0 signals maturing, not yet stable API)
- **This release:** 0.5.0
- **Single source of truth:** pyproject.toml (dynamic versioning)
- **Pre-releases:** None — go straight to 0.5.0 final

### Distribution

- **PyPI:** alphaswarm-sol
  - Wheel (.whl) + source tarball (.tar.gz)
  - GitHub Artifact Attestations
  - Trusted Publishing (OIDC, secretless)
- **Cross-platform:** Single universal wheel `py3-none-any.whl`
- **GitHub Releases:** Auto-deployed via GitHub Actions on tag
- **Docker:** ghcr.io/[org]/alphaswarm-sol:0.5.0

### Install Validation

- **Test environments:** macOS ARM, macOS Intel, Ubuntu/Debian, Docker
- **Smoke tests:**
  - `alphaswarm --version` returns 0.5.0
  - `alphaswarm build-kg` on sample contract
  - `alphaswarm query` with VQL and NL
- **Automation:** Manual checklist (CI matrix deferred)

### Claude's Discretion

- Exact MkDocs theme configuration
- Changelog format and git tag management
- Smoke test contract selection
- pyproject.toml metadata fields beyond required
- Diagram rendering tool/style

</decisions>

<specifics>
## Specific Ideas

### Research Context (State of the Art 2024-2026)

Based on comprehensive research, AlphaSwarm.sol addresses gaps in existing approaches:

| Existing Approach | Limitation | AlphaSwarm Solution |
|-------------------|------------|---------------------|
| Structural KGs (CKG-LLM) | AST/CFG patterns miss behavioral variations | Behavioral signatures via semantic operations |
| Single-pass LLM (SmartGuard) | No verification, hallucination risk | Adversarial verification protocol |
| Multi-agent (LLM-SmartAudit) | No structured debate, no evidence anchoring | iMAD-inspired claim/rebuttal/arbitration |
| Symbolic (SymGPT) | ERC rules only, not logic bugs | Protocol context for economic reasoning |
| Invariant synthesis (FLAMES) | Limited to invariants | Three-tier pattern system |

### Key Research Papers for Related Work

1. **CKG-LLM** (Li et al., 2025) — "LLM-Assisted Detection of Smart Contract Access Control Vulnerabilities Based on Knowledge Graphs"
2. **SmartGuard** (Ding et al., 2025) — "An LLM-enhanced framework for smart contract vulnerability detection"
3. **LLM-SmartAudit** (Wei et al., 2025) — "Advanced Smart Contract Vulnerability Detection via LLM-Powered Multi-Agent Systems"
4. **iMAD** (Fan et al., 2025) — "Intelligent Multi-Agent Debate for Efficient and Accurate LLM Inference"
5. **Anthropic SCONE-bench** (Dec 2025) — AI agents finding $4.6M in smart contract exploits

### Identity Rationale

- **AlphaSwarm.sol** captures:
  1. Finding security "alpha" (edge others miss)
  2. Multi-agent "swarm" orchestration
  3. Solidity-specific (.sol)

- **BSKG (Behavioral Security Knowledge Graph)** differentiates from:
  - CKG (Contract Knowledge Graph) — structural, AST-based
  - Generic program KGs — not security-focused
  - CFG/DFG approaches — no semantic operations

- **VRS (Vulnerability Reasoning System)** emphasizes:
  - Reasoning over detection
  - System over tool
  - Multi-agent architecture

</specifics>

<deferred>
## Deferred Ideas

### Evaluation & Benchmarks (→ Phase 7)
- DVDeFi challenge results
- Precision/recall metrics
- Comparison tables with competitors
- Real-world exploit coverage statistics

### Case Studies (→ Post-Phase 7)
- Real protocol audit walkthrough
- Multi-agent debate example
- Pattern authoring guide
- Step-by-step tutorials

### API Documentation (→ 0.6.0)
- Auto-generated from docstrings
- Full Python API reference

### CI Install Validation (→ Future)
- GitHub Actions matrix testing all platforms

### Academic Publication (→ Future)
- Full research paper submission
- Formal evaluation methodology
- Peer review process

</deferred>

---

*Phase: 06-release-preparation*
*Context gathered: 2026-01-22*
*Research sources: Exa search on AI vulnerability detection frameworks (2024-2026)*
