# Honest Limitations

This document is brutally honest about what AlphaSwarm.sol cannot do. Understanding these limits makes you a better user of the system.

---

## What We Are (And Aren't)

**AlphaSwarm.sol IS:**
- A multi-agent orchestration framework for security audits
- A Claude Code workflow-first system where CLI commands are subordinate tooling
- A behavioral detection system that ignores function names
- A knowledge graph that captures what code *does*, not what it *should do*
- A force multiplier for human auditors

**AlphaSwarm.sol IS NOT:**
- A replacement for human security auditors
- A guarantee of contract safety
- A scanner you run and trust blindly
- Liable for missed vulnerabilities

---

## The Hard Problems (What AI Security Can't Solve)

### 1. The Intent Gap

We detect **what code does**. We cannot detect **what code should do**.

```solidity
// Is this a bug or a feature?
function withdraw(uint amount) external {
    balances[msg.sender] -= amount;
    payable(msg.sender).transfer(amount);
}
```

Without a specification, we can't know:
- Should users only withdraw their own funds? (yes, obviously... but the code doesn't say)
- Should there be a withdrawal limit? (depends on protocol)
- Should withdrawals be pausable? (depends on threat model)

**The limit:** Business logic bugs require specifications. No spec → no ground truth → uncertain findings.

### 2. Economic Context is Infinite

We use Exa MCP to research protocol economics, historical exploits, and attack vectors. But:

- **Flash loan attacks** depend on available liquidity across all DeFi
- **Oracle manipulation** depends on DEX depth and price impact
- **MEV attacks** depend on mempool state at execution time
- **Governance attacks** depend on token distribution and voter apathy

We can research that "Compound-style lending protocols are vulnerable to oracle manipulation" but we cannot simulate every possible market condition.

**The limit:** Economic attacks have infinite state space. We surface risks, not proofs.

### 3. The Unknown Unknown Problem

Our 466 active patterns detect known vulnerability classes. But:

| What We Know | What We Don't |
|--------------|---------------|
| Reentrancy variants | The next novel attack vector |
| Access control patterns | Protocol-specific permission models |
| Oracle manipulation types | New oracle designs |
| Flash loan attack shapes | Creative economic exploits |

**Honest status:** No benchmarks have been run yet. Detection rates are unknown until Phase 5 (Benchmark Reality). The miss rate for novel attacks is expected to be significant — you can't pattern-match the unprecedented.

**The limit:** You can't pattern-match the unprecedented.

### 4. Cross-Protocol Blindness

We analyze **your contracts**. We don't analyze:

- Every contract you call
- Every protocol you integrate with
- Every token users might deposit
- External protocol upgrades after your audit

```solidity
// We see this call
IERC20(token).transfer(to, amount);

// We don't see what 'token' actually does
// Could be: rebasing, fee-on-transfer, pausable, upgradeable, malicious
```

**The limit:** Composability bugs require analyzing the entire DeFi stack. We analyze your slice.

### 5. The Confidence Trap

Multi-agent debate reduces errors but doesn't eliminate them:

| Failure Mode | Why It Happens |
|--------------|----------------|
| Collective hallucination | All agents trained on similar data |
| Confirmation bias | Attacker finds "exploit", Defender finds "weak guard", Verifier confirms |
| Evidence fabrication | Graph queries return what we look for |
| Consensus ≠ correctness | 3 agents agreeing doesn't make it true |

**The limit:** High confidence is not the same as correct. "Confirmed" findings still need human verification.

### 6. Temporal Blindness

Static analysis sees code at a point in time. It cannot see:

- Admin key compromise next week
- Governance attack during holiday
- Market conditions during exploit
- Gas prices affecting attack viability
- Sequencer downtime on L2s

**The limit:** Security is a continuous process. Audits are snapshots.

---

## When to Override the System

| Signal | What It Means | Your Action |
|--------|---------------|-------------|
| "confirmed" but gut says wrong | Agents found evidence but context is missing | Investigate manually, trust your experience |
| "rejected" but pattern looks dangerous | Guards exist but might be bypassable | Deeper manual review |
| "uncertain" with high severity | Not enough evidence either way | Escalate to senior auditor |
| Perfect 100%/100% metrics | Fabrication or test contamination | Re-run with fresh environment |
| Debate stuck in loops | Ambiguous code, no clear answer | Human judgment required |

---

## What Always Requires Human Judgment

These decisions **cannot be delegated** to AI agents:

### Protocol-Specific Invariants
- "Total deposits should equal sum of balances" — we don't know your invariants
- "Only whitelisted tokens allowed" — we don't know your whitelist
- "Liquidation should preserve solvency" — we don't know your math

### Risk Acceptance
- Is 0.1% chance of exploit acceptable? Depends on TVL
- Is admin key risk acceptable? Depends on your threat model
- Is upgrade delay sufficient? Depends on your response capability

### Business Impact
- Which finding is actually critical for YOUR protocol?
- What's the realistic attack cost vs. reward?
- What fixes are compatible with your architecture?

### Fix Verification
- Does the fix actually work?
- Does it introduce new issues?
- Is it compatible with existing integrations?

---

## Detection Rates (Unknown — Benchmarks Not Yet Run)

**No benchmarks have been executed.** The numbers below are theoretical expectations based on pattern coverage, NOT measured results. Phase 5 (Benchmark Reality) will produce honest, reproducible metrics.

| Category | Expected Range | Why Uncertain |
|----------|---------------|---------------|
| Reentrancy (classic CEI) | High | Well-covered by patterns, but untested on real benchmarks |
| Reentrancy (cross-function) | Medium | Requires deep call graph analysis |
| Access control (missing) | Medium-High | Intentional public functions create false positive risk |
| Access control (weak) | Medium | "Weak" is context-dependent |
| Oracle manipulation | Medium | Requires economic context |
| Flash loan attacks | Low-Medium | Highly protocol-specific |
| Business logic | Low | Requires specification |
| Novel attacks | ~0% | By definition, no pattern exists |

**What we DO know:**
- 9/10 "rescued" patterns produce true positives on real contracts (90% TP rate — Phase 2.1)
- PatternEngine loads and matches 466 patterns on real contracts (Phase 1.1)
- 90.5% of emitted properties are consumed by active patterns (Phase 2.1)

**What we DON'T know:**
- Overall precision/recall/F1 on any benchmark suite
- Comparative performance vs Slither/Aderyn alone
- Whether the graph adds detection value (ablation study needed)

---

## The Fundamental Limit

**AlphaSwarm.sol makes auditors faster, not obsolete.**

An LLM swarm can:
- Query a knowledge graph faster than humans
- Remember 466+ vulnerability patterns perfectly
- Debate without ego or fatigue
- Generate evidence-linked findings systematically

An LLM swarm cannot:
- Know your threat model
- Understand your users' trust assumptions
- Predict novel attack vectors
- Accept liability for missed vulnerabilities
- Replace the judgment that comes from experience

---

## When NOT to Use AlphaSwarm.sol

| Situation | Why | Alternative |
|-----------|-----|-------------|
| High-value launch (>$100M TVL) | Too much at stake for any automated tool | Multiple independent human audits |
| Novel protocol design | No patterns exist for unprecedented code | First-principles security review |
| Post-exploit forensics | Need chain state, not static analysis | Tenderly, Phalcon, manual tracing |
| Compliance/certification | Regulators want human attestation | Certified audit firms |
| "Quick check before deploy" | False sense of security | At minimum, run full 9-stage pipeline |

---

## Improving These Limits

We're actively working on:

- [ ] Better cross-contract analysis
- [ ] Economic simulation integration
- [ ] Specification inference from tests
- [ ] Novel attack synthesis (not just pattern matching)
- [ ] Continuous monitoring (not just point-in-time)

But some limits are fundamental to static analysis and AI reasoning. They won't disappear.

---

## The Bottom Line

**Trust but verify.**

AlphaSwarm.sol aims to find a significant portion of vulnerabilities through behavioral pattern matching and multi-agent reasoning. Detection rates have not been benchmarked yet (Phase 5 target).

The portion it misses could be the one that drains your protocol.

Use AlphaSwarm.sol to accelerate your security process, not to replace it.

---

*"The goal is not to eliminate human auditors. The goal is to make them 10x more effective."*
