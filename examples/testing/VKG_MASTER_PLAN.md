# AlphaSwarm.sol Master Plan: From 0% to Industry-Leading Detection

## The Brutal Reality Check

**Date:** 2025-12-31
**Current State:** 1315+ tests passing, 22 phases complete, **0 real-world bugs detected**

---

## Executive Summary

After exhaustive testing against Damn Vulnerable DeFi's 18 challenges:

| Metric | Claimed | Actual | Gap |
|--------|---------|--------|-----|
| Direct Vulnerability Detection | 18/18 | **0/18** | -100% |
| Critical Property Accuracy | 95%+ | **<50%** | Dangerously wrong |
| Pattern Match Rate | High | **0%** | Complete failure |
| Actionable Findings | Many | **Zero** | Total failure |

**Root Cause:** Not a design flaw - **4 specific bugs in builder.py** cause most failures.

---

## Part 1: The Evidence (What We Know)

### 1.1 Tested Challenges & Results

| Challenge | Bug Type | BSKG Detected | Root Cause |
|-----------|----------|--------------|------------|
| Unstoppable | DoS via donation | NO | `has_strict_equality_check` too narrow |
| Naive Receiver | Auth bypass | NO | Missing property: `allows_action_on_behalf_of` |
| Truster | Arbitrary call | NO | `call_target_user_controlled` misses high-level calls |
| Side Entrance | Accounting bypass | WRONG | Flags wrong function, wrong reason |
| The Rewarder | Flash loan rewards | NO | Missing: `balance_used_for_rewards` |
| Selfie | Governance manipulation | NO | Cross-contract temporal attack not modeled |
| Compromised | Leaked keys | N/A | Off-chain bug - wrong tool category |
| Puppet 1/2/3 | Oracle manipulation | PARTIAL | Identifies oracle, not manipulation risk |
| Free Rider | Payment logic bug | NO | Logic bug - fundamentally hard |
| Backdoor | Callback exploitation | NO | External contract analysis missing |
| Climber | Execute before validate | NO | Temporal ordering not tracked |
| Wallet Mining | CREATE2 prediction | N/A | Deployment attack - wrong abstraction |
| ABI Smuggling | Calldata manipulation | NO | Too specialized for patterns |
| Shards | Fractionalization bug | NO | Domain-specific math not modeled |
| Curvy Puppet | Curve oracle | NO | Protocol-specific oracle |
| Withdrawal | Bridge validation | NO | L1/L2 not modeled |

### 1.2 Identified Bugs in builder.py

**Bug #1: `call_target_user_controlled` Only Checks Low-Level Calls**
```
Location: builder.py:1446, 2020-2066
Impact: CRITICAL - Misses Truster's arbitrary call vulnerability
Cause: Only checks `.call()`, not `Address.functionCall()` (high-level)
```

**Bug #2: No High-Level Call DATA Analysis**
```
Location: builder.py:2068-2092
Impact: CRITICAL - Misses Truster's user-controlled calldata
Cause: High-level call argument checking not implemented
```

**Bug #3: `has_strict_equality_check` Too Narrow**
```
Location: builder.py:4853-4862
Impact: HIGH - Misses Unstoppable's DoS vulnerability
Cause: Only checks `require` with `==`, not `if` with `!=`
```

**Bug #4: `_callsite_destination` Fails for Library Calls**
```
Location: builder.py:5276-5283
Impact: HIGH - Wrong target extraction for Address.functionCall
Cause: Doesn't handle library function first argument as target
```

### 1.3 False Negative Evidence

```python
# Truster flashLoan - ACTUAL BSKG OUTPUT:
{
    "parameter_names": ["amount", "borrower", "target", "data"],
    "call_target_user_controlled": False,   # WRONG - target IS user param
    "call_data_user_controlled": False,     # WRONG - data IS user param
    "has_untrusted_external_call": True,    # Only correct property
}
```

**Reality:** `target` and `data` are DIRECT function parameters = 100% user controlled

---

## Part 2: The Fix Plan (Prioritized)

### Phase F1: Critical Bug Fixes (Week 1)

**Goal:** Fix the 4 identified bugs to achieve baseline detection

#### F1-T1: Fix `call_target_user_controlled` for High-Level Calls

```python
# builder.py:1446 - Change from:
"call_target_user_controlled": low_level_summary["call_target_user_controlled"],

# To:
"call_target_user_controlled": (
    low_level_summary["call_target_user_controlled"]
    or external_call_target_user_controlled  # Already computed at line 926!
),
```

**Test:** Truster should now have `call_target_user_controlled: true`

#### F1-T2: Add High-Level Call DATA Analysis

```python
# New function in builder.py
def _external_call_data_user_controlled(
    self, external_calls, high_level_calls, parameter_names
) -> bool:
    for _, call in high_level_calls:
        arguments = getattr(call, "arguments", []) or []
        for arg in arguments:
            if self._is_user_controlled_expression(arg, parameter_names):
                return True
    return False

# Add property:
"call_data_user_controlled": (
    low_level_summary["call_data_user_controlled"]
    or external_call_data_user_controlled
),
```

**Test:** Truster should now have `call_data_user_controlled: true`

#### F1-T3: Expand `has_strict_equality_check`

```python
# builder.py:4853 - Replace entire function
def _has_strict_equality_check(self, fn) -> bool:
    """Detect strict equality checks that could break invariants."""
    # Check ALL nodes, not just require expressions
    for node in fn.nodes or []:
        source = str(getattr(node, 'expression', ''))

        # Match various balance/supply/shares comparisons
        patterns = [
            r'(balance|supply|shares|total)\w*\s*(==|!=)',
            r'(==|!=)\s*\w*(balance|supply|shares|total)',
            r'convertToShares.*!=',
            r'!=.*convertToShares',
        ]
        for pattern in patterns:
            if re.search(pattern, source, re.IGNORECASE):
                return True
    return False
```

**Test:** Unstoppable should now have `has_strict_equality_check: true`

#### F1-T4: Fix `_callsite_destination` for Library Calls

```python
# builder.py:5276 - Improve target extraction
def _callsite_destination(self, call: Any) -> str | None:
    # Standard destination
    destination = getattr(call, "destination", None)
    if destination is not None:
        name = getattr(destination, "name", None)
        if name:
            return str(name)

    # For library calls (Address.functionCall), first arg is target
    func_name = getattr(call, "function_name", "")
    if func_name in ("functionCall", "functionCallWithValue", "functionDelegateCall"):
        arguments = getattr(call, "arguments", []) or []
        if arguments:
            first_arg = arguments[0]
            name = getattr(first_arg, "name", None)
            if name:
                return str(name)

    return str(destination) if destination else None
```

**Test:** Truster target should be `target` parameter, not Address library

#### F1-Verification

```bash
# After all fixes, run:
cd .

# Rebuild Truster
uv run alphaswarm build-kg examples/damm-vuln-defi/src/truster/

# Verify properties
python3 -c "
import json
with open('examples/damm-vuln-defi/src/truster/.true_vkg/graphs/graph.json') as f:
    data = json.load(f)
    funcs = [n for n in data['graph']['nodes'] if n.get('type') == 'Function']
    fl = [f for f in funcs if 'flashLoan' in f.get('label', '')][0]
    p = fl['properties']
    assert p.get('call_target_user_controlled') == True, 'BUG #1 NOT FIXED'
    assert p.get('call_data_user_controlled') == True, 'BUG #2 NOT FIXED'
    print('Truster: FIXED')
"

# Rebuild Unstoppable
uv run alphaswarm build-kg examples/damm-vuln-defi/src/unstoppable/

# Verify
python3 -c "
import json
with open('examples/damm-vuln-defi/src/unstoppable/.true_vkg/graphs/graph.json') as f:
    data = json.load(f)
    funcs = [n for n in data['graph']['nodes'] if n.get('type') == 'Function']
    fl = [f for f in funcs if 'flashLoan' in f.get('label', '')][0]
    p = fl['properties']
    assert p.get('has_strict_equality_check') == True, 'BUG #3 NOT FIXED'
    print('Unstoppable: FIXED')
"
```

**Success Criteria Phase F1:**
- Truster: `call_target_user_controlled: true`, `call_data_user_controlled: true`
- Unstoppable: `has_strict_equality_check: true`
- All existing 1315 tests still passing

---

### Phase F2: Pattern Updates (Week 2)

**Goal:** Create patterns that USE the fixed properties

#### F2-T1: Arbitrary External Call Pattern

```yaml
# patterns/core/arbitrary-call.yaml
- id: arbitrary-external-call-critical
  name: User-Controlled External Call Target and Data
  severity: critical
  description: |
    Function allows user to control both the target and data of an external call.
    This enables arbitrary code execution in the contract's context.

  match:
    tier_a:
      all:
        - property: visibility
          op: in
          value: [public, external]
        - property: call_target_user_controlled
          value: true
        - property: call_data_user_controlled
          value: true
      none:
        - property: has_access_gate
          value: true

  attack_scenario: |
    1. Attacker calls function with:
       - target = token contract address
       - data = abi.encodeWithSignature("approve(address,uint256)", attacker, MAX)
    2. Contract executes call in its own context
    3. Attacker now has approval to drain all tokens

  fix: |
    - Validate target against whitelist
    - Never pass user-controlled data to external calls
    - If required, use specific function signatures only

  cve_references:
    - "Truster Challenge - DVDeFi"
    - "Arbitrary External Call Vulnerability Class"
```

#### F2-T2: DoS Strict Equality Pattern

```yaml
# patterns/core/dos-strict-equality.yaml
- id: dos-strict-equality-invariant
  name: Strict Equality Check on Manipulable Balance
  severity: high
  description: |
    Function uses strict equality (== or !=) to compare balances, shares, or supplies.
    External deposits/transfers can break these invariants causing permanent DoS.

  match:
    tier_a:
      all:
        - property: visibility
          op: in
          value: [public, external]
        - property: has_strict_equality_check
          value: true
      any:
        - property: is_flash_loan_function
          value: true
        - property: is_vault_function
          value: true

  attack_scenario: |
    1. Contract checks: `if (totalBalance != expectedBalance) revert()`
    2. Attacker sends 1 wei directly to contract (bypassing accounting)
    3. Check permanently fails -> function is DoS'd

  fix: |
    - Use >= or <= instead of == or !=
    - Account for donation attacks in invariant checks
    - Use shares-based accounting that handles direct transfers

  cve_references:
    - "Unstoppable Challenge - DVDeFi"
    - "ERC4626 Donation Attack"
```

#### F2-T3: Side Entrance Flash Loan Pattern

```yaml
# patterns/core/flash-loan-accounting-bypass.yaml
- id: flash-loan-accounting-bypass
  name: Flash Loan Repayment via Side Effect
  severity: critical
  description: |
    Flash loan repayment check only verifies final balance, not source of funds.
    Deposit during callback satisfies check while adding to user balance.

  match:
    tier_a:
      all:
        - property: is_flash_loan_function
          value: true
        - property: checks_balance_after_callback
          value: true
      none:
        - property: tracks_loan_repayment_source
          value: true

  attack_scenario: |
    1. Flash borrow X tokens
    2. In callback: deposit(X) - adds X to user balance
    3. Flash loan check passes (balance >= before)
    4. Withdraw X - steal funds

  fix: |
    - Track specific repayment, not just balance
    - Use pull-based repayment (transferFrom borrower)
    - Block reentrancy into deposit during flash loan
```

---

### Phase F3: DVDeFi Benchmark Suite (Week 3)

**Goal:** Automated testing against all 18 challenges

#### F3-T1: Benchmark Runner

```python
# scripts/benchmark_dvdefi.py
#!/usr/bin/env python3
"""
DVDeFi Benchmark Runner - Measures BSKG detection rate against known vulnerabilities.
"""

import json
import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

@dataclass
class Challenge:
    name: str
    vulnerability_type: str
    expected_property: str
    expected_pattern: Optional[str]
    affected_function: str
    description: str

CHALLENGES = [
    Challenge(
        name="unstoppable",
        vulnerability_type="DoS",
        expected_property="has_strict_equality_check",
        expected_pattern="dos-strict-equality-invariant",
        affected_function="flashLoan",
        description="Direct transfer breaks balance invariant"
    ),
    Challenge(
        name="naive-receiver",
        vulnerability_type="Auth Bypass",
        expected_property="allows_third_party_action",
        expected_pattern="flash-loan-third-party",
        affected_function="flashLoan",
        description="Anyone can initiate flash loan for any receiver"
    ),
    Challenge(
        name="truster",
        vulnerability_type="Arbitrary Call",
        expected_property="call_target_user_controlled",
        expected_pattern="arbitrary-external-call-critical",
        affected_function="flashLoan",
        description="User controls external call target and data"
    ),
    Challenge(
        name="side-entrance",
        vulnerability_type="Accounting Bypass",
        expected_property="flash_loan_repayment_bypassable",
        expected_pattern="flash-loan-accounting-bypass",
        affected_function="flashLoan",
        description="Deposit during flash loan satisfies repayment"
    ),
    Challenge(
        name="the-rewarder",
        vulnerability_type="Flash Loan Snapshot",
        expected_property="reward_based_on_instant_balance",
        expected_pattern="flash-loan-snapshot-manipulation",
        affected_function="claimRewards",
        description="Flash loan tokens to get disproportionate rewards"
    ),
    Challenge(
        name="selfie",
        vulnerability_type="Governance Manipulation",
        expected_property="governance_quorum_flash_loanable",
        expected_pattern="governance-vote-without-snapshot",
        affected_function="queueAction",
        description="Flash loan tokens to pass governance proposals"
    ),
    Challenge(
        name="compromised",
        vulnerability_type="Oracle Manipulation",
        expected_property="N/A",
        expected_pattern="N/A",
        affected_function="N/A",
        description="OFF-CHAIN: Leaked private keys (not detectable by static analysis)"
    ),
    Challenge(
        name="puppet",
        vulnerability_type="Oracle Manipulation",
        expected_property="reads_spot_price_manipulable",
        expected_pattern="oracle-spot-price-manipulation",
        affected_function="borrow",
        description="Uses DEX spot price as oracle"
    ),
    Challenge(
        name="puppet-v2",
        vulnerability_type="Oracle Manipulation",
        expected_property="reads_spot_price_manipulable",
        expected_pattern="oracle-spot-price-manipulation",
        affected_function="borrow",
        description="Uses Uniswap V2 reserves as oracle"
    ),
    Challenge(
        name="puppet-v3",
        vulnerability_type="Oracle Manipulation",
        expected_property="twap_period_too_short",
        expected_pattern="oracle-twap-manipulation",
        affected_function="borrow",
        description="Uses short TWAP period"
    ),
    Challenge(
        name="free-rider",
        vulnerability_type="Logic Bug",
        expected_property="N/A",
        expected_pattern="N/A",
        affected_function="buyMany",
        description="LOGIC BUG: Payment sent to buyer not seller (hard to detect statically)"
    ),
    Challenge(
        name="backdoor",
        vulnerability_type="Callback Exploitation",
        expected_property="allows_arbitrary_callback_delegatecall",
        expected_pattern="delegatecall-in-callback",
        affected_function="proxyCreated",
        description="Setup callback allows arbitrary delegatecall"
    ),
    Challenge(
        name="climber",
        vulnerability_type="Temporal Ordering",
        expected_property="executes_before_validates",
        expected_pattern="execute-before-check",
        affected_function="execute",
        description="Executes operations before checking if scheduled"
    ),
    Challenge(
        name="wallet-mining",
        vulnerability_type="CREATE2 Prediction",
        expected_property="N/A",
        expected_pattern="N/A",
        affected_function="N/A",
        description="DEPLOYMENT ATTACK: CREATE2 address prediction (wrong abstraction)"
    ),
    Challenge(
        name="abi-smuggling",
        vulnerability_type="Calldata Manipulation",
        expected_property="manual_calldata_parsing",
        expected_pattern="calldata-offset-manipulation",
        affected_function="execute",
        description="Reads selector at wrong calldata offset"
    ),
    Challenge(
        name="shards",
        vulnerability_type="Math Bug",
        expected_property="N/A",
        expected_pattern="N/A",
        affected_function="N/A",
        description="DOMAIN-SPECIFIC: NFT fractionalization math"
    ),
    Challenge(
        name="curvy-puppet",
        vulnerability_type="Protocol-Specific Oracle",
        expected_property="reads_curve_virtual_price",
        expected_pattern="curve-oracle-manipulation",
        affected_function="borrow",
        description="Curve-specific price manipulation"
    ),
    Challenge(
        name="withdrawal",
        vulnerability_type="Bridge Validation",
        expected_property="N/A",
        expected_pattern="N/A",
        affected_function="N/A",
        description="L1/L2 BRIDGE: Cross-chain message validation"
    ),
]

def run_benchmark():
    results = {
        "timestamp": "2025-12-31",
        "vkg_version": "22-phase",
        "challenges": [],
        "summary": {}
    }

    detected = 0
    detectable = 0

    for challenge in CHALLENGES:
        print(f"Testing {challenge.name}...")

        # Skip non-detectable
        if challenge.expected_property == "N/A":
            results["challenges"].append({
                "name": challenge.name,
                "status": "NOT_APPLICABLE",
                "reason": challenge.description
            })
            continue

        detectable += 1

        # Build graph
        src_path = f"examples/damm-vuln-defi/src/{challenge.name}/"
        subprocess.run(["uv", "run", "alphaswarm", "build-kg", src_path],
                      capture_output=True)

        graph_path = f"{src_path}.true_vkg/graphs/graph.json"

        # Check property
        try:
            with open(graph_path) as f:
                data = json.load(f)

            funcs = [n for n in data["graph"]["nodes"] if n.get("type") == "Function"]
            target_func = None
            for f in funcs:
                if challenge.affected_function in f.get("label", ""):
                    target_func = f
                    break

            if target_func:
                props = target_func.get("properties", {})
                property_value = props.get(challenge.expected_property)

                if property_value == True:
                    detected += 1
                    status = "DETECTED"
                else:
                    status = "MISSED"
            else:
                status = "FUNCTION_NOT_FOUND"

        except Exception as e:
            status = f"ERROR: {e}"

        results["challenges"].append({
            "name": challenge.name,
            "vulnerability_type": challenge.vulnerability_type,
            "expected_property": challenge.expected_property,
            "affected_function": challenge.affected_function,
            "status": status
        })

    results["summary"] = {
        "total_challenges": len(CHALLENGES),
        "detectable_by_static_analysis": detectable,
        "detected": detected,
        "detection_rate": f"{detected/detectable*100:.1f}%" if detectable > 0 else "N/A",
        "not_applicable": len(CHALLENGES) - detectable
    }

    # Save results
    with open("benchmarks/dvdefi_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n=== RESULTS ===")
    print(f"Detected: {detected}/{detectable} ({detected/detectable*100:.1f}%)")
    print(f"Not applicable (off-chain/logic bugs): {len(CHALLENGES) - detectable}")

    return results

if __name__ == "__main__":
    run_benchmark()
```

#### F3-T2: Success Targets

| Phase | Detection Rate | Status |
|-------|---------------|--------|
| Pre-fix | 0% (0/14) | Current |
| Post-F1 | 30%+ (4/14) | Minimum after bug fixes |
| Post-F2 | 50%+ (7/14) | After pattern updates |
| Post-F3 | 70%+ (10/14) | Target for v1.0 release |

**Note:** 4 challenges are fundamentally not detectable by static analysis:
- Compromised (off-chain key leak)
- Free Rider (pure logic bug)
- Wallet Mining (CREATE2 deployment)
- Shards/Withdrawal (domain-specific)

---

### Phase F4: Missing Properties (Week 4)

**Goal:** Add properties for vulnerability classes BSKG can't detect yet

#### F4-T1: Flash Loan Properties

```python
# New properties to add in builder.py
"allows_third_party_flash_loan": self._allows_third_party_flash_loan(fn),
"flash_loan_repayment_bypassable": self._flash_loan_repayment_bypassable(fn),
"reward_based_on_instant_balance": self._reward_based_on_instant_balance(fn),
```

#### F4-T2: Governance Properties

```python
"governance_quorum_flash_loanable": self._governance_quorum_flash_loanable(fn),
"executes_before_validates": self._executes_before_validates(fn),
```

#### F4-T3: Oracle Properties

```python
"reads_spot_price_manipulable": self._reads_spot_price_manipulable(fn),
"twap_period_too_short": self._twap_period_too_short(fn),
"reads_curve_virtual_price": self._reads_curve_virtual_price(fn),
```

---

### Phase F5: Competitive Benchmark (Week 5-6)

**Goal:** Compare BSKG to Slither/Mythril on same contracts

#### F5-T1: Tool Comparison Matrix

```bash
# Run each tool on DVDeFi
for challenge in unstoppable truster side-entrance; do
    echo "=== $challenge ==="

    # VKG
    uv run alphaswarm build-kg "src/$challenge/"
    uv run alphaswarm query "pattern:*" --graph "src/$challenge/.true_vkg/graphs/graph.json" > "results/vkg_$challenge.json"

    # Slither
    slither "src/$challenge/" --json "results/slither_$challenge.json"

    # Mythril (if applicable)
    myth analyze "src/$challenge/*.sol" -o json > "results/mythril_$challenge.json"
done
```

#### F5-T2: Comparison Metrics

| Tool | Unstoppable | Truster | Side Entrance | Avg |
|------|-------------|---------|---------------|-----|
| BSKG | ? | ? | ? | ? |
| Slither | ? | ? | ? | ? |
| Mythril | ? | ? | ? | ? |

**Goal:** Identify where BSKG provides unique value

---

## Part 3: The Hard Problems (Months 2-4)

### What BSKG Fundamentally Cannot Detect (Currently)

| Bug Class | Why Hard | Possible Solution |
|-----------|----------|-------------------|
| Pure Logic Bugs | Requires understanding intent | LLM reasoning in Tier B |
| Cross-Contract Temporal | Multi-tx state evolution | Symbolic execution |
| Economic Attacks | Requires financial modeling | Economic invariant solver |
| Off-Chain Issues | Not in code | Out of scope |

### H1: LLM-Powered Logic Bug Detection

**Current Tier B:** Placeholder - not actually working

**Needed:**
```python
# Prompt for LLM analysis
prompt = f"""
Analyze this function for logic bugs:

```solidity
{function_source}
```

The function has these properties:
- Transfers value: {transfers_value}
- Writes state: {writes_state}
- Has access control: {has_access_control}

Consider:
1. Is the order of operations correct?
2. Are there assumptions that can be violated?
3. Could an attacker benefit from calling this in unexpected ways?
4. Are payment/balance calculations correct?

Known vulnerability patterns to check:
- Payment to wrong recipient
- Stale state reads after writes
- Assumptions about caller behavior
"""
```

### H2: Cross-Contract Analysis

**Current:** Single contract analysis only

**Needed:**
```
SelfiePool.flashLoan()
  → IFlashLoanReceiver(receiver).onFlashLoan()
    → SimpleGovernance.queueAction()
      → [2 days later] SimpleGovernance.execute()
        → SelfiePool.emergencyExit()
          → DRAIN ALL FUNDS
```

### H3: Economic Modeling

**Current:** No economic understanding

**Needed:**
- "No free money" invariant checking
- Flash loan profitability analysis
- MEV opportunity detection

---

## Part 4: Success Metrics & Timeline

### Week-by-Week Targets

| Week | Phase | Target | Verification |
|------|-------|--------|--------------|
| 1 | F1 | Fix 4 builder.py bugs | Truster/Unstoppable properties correct |
| 2 | F2 | Create patterns for fixed properties | Pattern matches on test contracts |
| 3 | F3 | DVDeFi benchmark automation | 30%+ detection rate |
| 4 | F4 | Add missing properties | 50%+ detection rate |
| 5-6 | F5 | Competitive benchmark | Know BSKG vs Slither positioning |

### Milestone Targets

| Milestone | Detection Rate | Unique Value |
|-----------|---------------|--------------|
| v0.1 (Current) | 0% | None - broken |
| v0.2 (Post F1-F2) | 30% | Basic arbitrary call detection |
| v0.3 (Post F3-F4) | 50% | Flash loan pattern detection |
| v1.0 (Production) | 70%+ | Name-agnostic + multi-agent consensus |

### Ultimate Success Definition

**VKG is ready for production when:**

```
[ ] 70%+ detection on DVDeFi detectable challenges
[ ] <15% false positive rate on real protocols
[ ] Finds bugs Slither misses
[ ] $10K+ in bug bounty earnings validated
[ ] 2+ audit firm testimonials
```

---

## Part 5: Honest Assessment of Limitations

### What BSKG Can Become Good At

1. **Arbitrary external call detection** - After F1/F2 fixes
2. **Flash loan pattern recognition** - After F4
3. **Name-agnostic detection** - Core strength, needs bug fixes
4. **Multi-agent consensus** - Reduce false positives
5. **Evidence-linked findings** - Already works

### What BSKG Will Struggle With

1. **Pure logic bugs** - Requires intent understanding (LLM helps)
2. **Cross-protocol composition** - Needs external contract modeling
3. **Economic attacks** - Needs financial reasoning
4. **Novel vulnerability classes** - Pattern-based = known bugs only

### What BSKG Should Not Claim To Do

1. Replace human auditors
2. Find all vulnerabilities
3. Understand business logic
4. Detect off-chain issues

---

## Part 6: Action Items (Copy-Paste Ready)

### Immediate (This Week)

```bash
# 1. Create branch for fixes
cd .
git checkout -b fix/critical-detection-bugs

# 2. Apply Bug #1 fix
# Edit builder.py:1446

# 3. Apply Bug #2 fix
# Add new function and property

# 4. Apply Bug #3 fix
# Rewrite has_strict_equality_check

# 5. Apply Bug #4 fix
# Improve _callsite_destination

# 6. Run all tests
uv run pytest tests/ -v

# 7. Rebuild DVDeFi graphs
for c in truster unstoppable; do
    uv run alphaswarm build-kg "examples/damm-vuln-defi/src/$c/"
done

# 8. Verify fixes
python3 scripts/verify_fixes.py
```

### This Month

1. Complete F1-F4 phases
2. Achieve 50%+ DVDeFi detection
3. Create competitive benchmark
4. Document all findings

### This Quarter

1. Reach 70%+ detection rate
2. Test on real protocols (Uniswap, Aave)
3. Submit to bug bounty programs
4. Publish benchmark results

---

## Appendix A: File Locations for Fixes

| Fix | File | Lines |
|-----|------|-------|
| Bug #1 | `src/true_vkg/kg/builder.py` | 1446 |
| Bug #2 | `src/true_vkg/kg/builder.py` | 2068-2092 (new function) |
| Bug #3 | `src/true_vkg/kg/builder.py` | 4853-4862 |
| Bug #4 | `src/true_vkg/kg/builder.py` | 5276-5283 |

---

## Appendix B: Commands Reference

```bash
# Build single challenge
uv run alphaswarm build-kg examples/damm-vuln-defi/src/<challenge>/

# Query patterns
uv run alphaswarm query "pattern:*" --graph <path>

# Query properties
uv run alphaswarm query "FIND functions WHERE <property> = true" --graph <path>

# Run benchmark
python3 scripts/benchmark_dvdefi.py

# Compare tools
python3 scripts/compare_tools.py
```

---

## Appendix C: DVDeFi Challenge Quick Reference

| # | Challenge | Bug Type | Detectable? |
|---|-----------|----------|-------------|
| 1 | Unstoppable | DoS/Donation | YES (after fix) |
| 2 | Naive Receiver | Auth Bypass | YES (needs property) |
| 3 | Truster | Arbitrary Call | YES (after fix) |
| 4 | Side Entrance | Accounting | YES (needs property) |
| 5 | The Rewarder | Flash Snapshot | YES (needs property) |
| 6 | Selfie | Governance | PARTIAL |
| 7 | Compromised | Off-Chain | NO |
| 8 | Puppet | Oracle | YES (needs property) |
| 9 | Puppet V2 | Oracle | YES (needs property) |
| 10 | Puppet V3 | Oracle TWAP | YES (needs property) |
| 11 | Free Rider | Logic Bug | NO |
| 12 | Backdoor | Callback | PARTIAL |
| 13 | Climber | Temporal | PARTIAL |
| 14 | Wallet Mining | CREATE2 | NO |
| 15 | ABI Smuggling | Calldata | PARTIAL |
| 16 | Shards | Domain Math | NO |
| 17 | Curvy Puppet | Curve Oracle | YES (needs property) |
| 18 | Withdrawal | Bridge | NO |

**Theoretical Maximum:** 12-14/18 (67-78%) with static analysis
**Current:** 0/18 (0%)
**Post-Fix Target:** 10/14 detectable (71%)

---

*This plan was created from brutal honest assessment. The goal is making BSKG actually useful, not pretending it already is.*

*Last Updated: 2025-12-31*
