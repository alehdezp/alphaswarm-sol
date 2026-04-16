# Adversarial Corpus Generation Pipeline

8-step pipeline for generating hostile Solidity test projects with embedded vulnerabilities,
adversarial obfuscation, ground truth, and safe variants.

**Executor:** `corpus-generator` Opus-powered Claude Code subagent.

---

## Step 1: Select Target Patterns

**Input:** Pattern selection parameters (explicit list or random selection criteria).
**Output:** List of 5-10 pattern specs from `pattern-catalog.yaml`.

### Process

1. If explicit patterns provided, look up each in `pattern-catalog.yaml`.
2. If `--patterns random`, select based on:
   - Protocol theme from `combination-rules.yaml` `selection_strategy.protocol_themes`
   - High-affinity patterns for the theme
   - Compatible combinations from `combination-rules.yaml`
   - Avoid interference patterns
3. Validate: minimum 5 patterns, check no interference conflicts.
4. Record selected patterns and rationale.

### Quality Checklist

- [ ] 5-10 distinct pattern IDs selected
- [ ] All pattern IDs exist in `pattern-catalog.yaml`
- [ ] No interference pattern conflicts (or conflicts explicitly resolved)
- [ ] At least 2 different vulnerability categories represented
- [ ] At least 1 high-severity pattern included

---

## Step 2: Extract Behavioral Specifications

**Input:** Selected pattern specs from Step 1.
**Output:** Behavioral specification document for each pattern.

### Process

1. For each selected pattern, extract from catalog:
   - `semantic_operations`: What the vulnerable code DOES
   - `ordering_constraints`: Required operation ordering for the vulnerability
   - `tier`: Detection tier (A=deterministic, B=LLM-verified, C=label-dependent)
2. Read the full vulndocs entry at `vulndoc_path` for detailed description.
3. Extract from vulndocs:
   - `match` rules (property conditions)
   - `description` (attack scenario, fix recommendations)
   - `severity` level
4. Create a behavioral spec summarizing what code must DO (not what it must LOOK like).

### Quality Checklist

- [ ] Every selected pattern has a behavioral spec
- [ ] Specs describe behaviors (operations, ordering), not names or syntax
- [ ] Specs include the attack scenario (how exploitation works)
- [ ] Fix recommendations captured (needed for safe variant generation)

---

## Step 3: Design Realistic Project Structure

**Input:** Behavioral specs from Step 2 + protocol theme.
**Output:** Project architecture with file layout, contract hierarchy, and interfaces.

### Process

1. Choose a realistic DeFi protocol archetype:
   - Lending pool, DEX, staking system, governance, bridge, vault, marketplace, etc.
2. Design multi-file project structure:
   ```
   contracts/
     interfaces/
       ILendingPool.sol
       IPriceOracle.sol
     core/
       LendingPool.sol
       CollateralManager.sol
     periphery/
       LiquidationBot.sol
       PriceOracle.sol
     libraries/
       MathLib.sol
     governance/
       Governor.sol
   ```
3. Map each vulnerability pattern to a specific contract/function location.
4. Ensure cross-function and cross-contract distribution per complexity targets.

### Quality Checklist

- [ ] At least 3 Solidity files (multi-file project, not monolith)
- [ ] Realistic business logic structure (interfaces, libraries, core/periphery)
- [ ] Each vulnerability mapped to a specific contract:function location
- [ ] Cross-function minimum met (3+ vulns in different functions)
- [ ] Cross-contract minimum met (1+ vuln spanning contracts) for Tier 2+

---

## Step 4: Generate Novel Contract Code

**Input:** Project structure + behavioral specs.
**Output:** Solidity source files implementing all selected vulnerability patterns.

### Process

1. Write each contract with realistic business logic.
2. Embed vulnerability patterns naturally in the business logic.
3. **CRITICAL: Training data contamination protocol:**
   - NO Ethernaut challenge contracts
   - NO Damn Vulnerable DeFi contracts
   - NO SWC test cases or example contracts
   - NO known CTF challenges (Paradigm CTF, Secureum, etc.)
   - Contract names, function names, and variable names must be ORIGINAL
   - Business logic must represent a NOVEL protocol, not a copy
4. Add realistic supporting code:
   - Event emissions, NatSpec comments, error messages
   - Constructor arguments, initializer patterns
   - View functions, getters, administrative functions
5. Use Solidity 0.8.x (overflow protection built-in, focus on logic bugs).

### Quality Checklist

- [ ] All contracts use `pragma solidity ^0.8.20;` or compatible
- [ ] Business logic is realistic and internally consistent
- [ ] Vulnerability patterns are embedded naturally (not obviously planted)
- [ ] No recognizable CTF/challenge contract structures
- [ ] Contract names and function names are original

---

## Step 5: Apply Adversarial Obfuscation

**Input:** Generated contracts + adversarial category specification.
**Output:** Obfuscated contracts with applied techniques from `adversarial-taxonomy.md`.

### Process

1. Read specified category (A, B, C, or combination) from `adversarial-taxonomy.md`.
2. Apply techniques from the specified categories:
   - **Tier 1:** 1-2 techniques from Category A
   - **Tier 2:** 2-3 techniques from Categories A and B
   - **Tier 3:** 3+ techniques from all categories including C (honeypots)
3. For each technique applied:
   - Transform the relevant code according to the technique specification
   - Verify the transformation preserves the vulnerability's exploitability
   - Record which technique was applied and where
4. For Category C (honeypots), ADD safe code that looks suspicious.

### Quality Checklist

- [ ] Specified adversarial category/categories applied
- [ ] Each applied technique documented with location
- [ ] Vulnerability patterns preserved after obfuscation
- [ ] For Tier 3: at least 1 honeypot (safe code that looks vulnerable) included
- [ ] Obfuscation is realistic (not gratuitously obfuscated)

---

## Step 6: Create Ground Truth

**Input:** Obfuscated contracts + pattern mapping from Steps 3-5.
**Output:** `ground-truth.yaml` with per-pattern findings and expected reasoning chains.

### Process

1. For each embedded vulnerability pattern, document:
   - `pattern_id`: Pattern identifier from catalog
   - `contract`: Contract name containing the vulnerability
   - `function`: Function name (after obfuscation)
   - `line_range`: Approximate line range in the obfuscated source
   - `severity`: From pattern catalog
   - `adversarial_techniques`: Which obfuscation techniques were applied to this pattern
   - `expected_reasoning_chain`: Ordered list of reasoning steps a correct detector should follow
2. For each honeypot (Category C), document as `safe_patterns`:
   - Same fields but with `expected_verdict: safe` and reasoning for WHY it's safe
3. Include a summary with total counts and detection difficulty assessment.

### Ground Truth Format

```yaml
project:
  name: "hostile-lending-v1"
  theme: "lending"
  tier: 2
  adversarial_categories: ["A", "B"]

findings:
  - pattern_id: "balance-update-after-transfer"
    contract: "CollateralManager"
    function: "processRedemption"
    line_range: "45-62"
    severity: high
    adversarial_techniques: ["A1-function-renaming", "B5-library-mediated"]
    expected_reasoning_chain:
      - "Identify external call via TransferLib.safeTransfer at line 52"
      - "Notice collateral balance update at line 58 occurs AFTER library call"
      - "Trace TransferLib.safeTransfer to find msg.sender.call{value:} at library line 12"
      - "Verify no reentrancy guard (no nonReentrant modifier)"
      - "Conclude: reentrancy via library-mediated external call in processRedemption"

safe_patterns:
  - technique: "C1-safe-dangerous-names"
    contract: "LendingPool"
    function: "withdraw"
    expected_verdict: safe
    reasoning: "Has nonReentrant modifier and follows CEI pattern"

summary:
  total_findings: 7
  total_safe_patterns: 2
  difficulty: "hard"
  notes: "Cross-contract reentrancy via library requires tracing through TransferLib"
```

### Quality Checklist

- [ ] Every embedded vulnerability has a ground truth entry
- [ ] Every ground truth entry has an `expected_reasoning_chain` with 3+ steps
- [ ] Honeypots documented as `safe_patterns` with reasoning
- [ ] Line ranges are accurate to the obfuscated source
- [ ] No fabricated findings (every entry maps to real embedded code)

---

## Step 7: Generate Safe Variant

**Input:** Vulnerable contracts + ground truth.
**Output:** `contracts/*_safe.sol` files with all vulnerabilities properly fixed.

### Process

1. For each vulnerable contract, create a `_safe.sol` copy.
2. For each finding in ground truth, apply the fix:
   - Reentrancy: Add `nonReentrant` modifier OR reorder to CEI pattern
   - Access control: Add `onlyOwner` / role check
   - Oracle: Add freshness check, TWAP, or circuit breaker
   - DoS: Add pagination or gas limits
   - Flash loan: Add same-block restrictions
   - etc.
3. Preserve the same business logic, names, structure -- ONLY fix the vulnerabilities.
4. Keep honeypot patterns UNCHANGED (they are already safe).

### Quality Checklist

- [ ] Every vulnerable contract has a corresponding `_safe.sol`
- [ ] Every finding from ground truth is fixed in the safe variant
- [ ] Business logic and structure preserved (only security fixes applied)
- [ ] Honeypot patterns are identical in both variants
- [ ] Safe variants are independently compilable

---

## Step 8: Compile and Validate

**Input:** Both vulnerable and safe contract variants.
**Output:** Compilation results + `project-manifest.yaml` + `build-verification.sh`.

### Process

1. Write `build-verification.sh`:
   ```bash
   #!/bin/bash
   set -e
   echo "Compiling vulnerable contracts..."
   solc --bin --abi contracts/*.sol 2>&1
   echo "Compiling safe contracts..."
   solc --bin --abi contracts/*_safe.sol 2>&1
   echo "All contracts compiled successfully."
   ```
2. Run `solc` on all `.sol` files (vulnerable and safe variants).
3. Fix any compilation errors:
   - Missing imports, wrong pragma, type errors
   - Re-run until all contracts compile
4. Write `project-manifest.yaml`:
   ```yaml
   name: "hostile-lending-v1"
   generated: "2026-02-12T00:00:00Z"
   generator: "corpus-generator v1"
   theme: "lending"
   tier: 2
   adversarial_categories: ["A", "B"]
   pattern_count: 7
   safe_pattern_count: 2
   solidity_version: "0.8.20"
   compilation_verified: true
   contracts:
     vulnerable: ["LendingPool.sol", "CollateralManager.sol", "PriceOracle.sol"]
     safe: ["LendingPool_safe.sol", "CollateralManager_safe.sol", "PriceOracle_safe.sol"]
   files:
     ground_truth: "ground-truth.yaml"
     manifest: "project-manifest.yaml"
     build_script: "build-verification.sh"
   contamination_check:
     ethernaut: false
     dvdefi: false
     swc: false
     ctf: false
   ```
5. Initialize Jujutsu repository: `jj git init && jj commit -m "initial"`

### Quality Checklist

- [ ] `solc` succeeds on ALL `.sol` files (vulnerable and safe)
- [ ] Zero compilation errors or warnings (or warnings documented)
- [ ] `project-manifest.yaml` accurately reflects project contents
- [ ] `build-verification.sh` is executable and passes
- [ ] Project initialized as Jujutsu repository
- [ ] No known test suite contracts present (contamination check)

---

## Pipeline Summary

| Step | Input | Output | Key Validation |
|------|-------|--------|----------------|
| 1. Select Patterns | Parameters | Pattern list | 5-10 compatible patterns |
| 2. Extract Behavior | Pattern list | Behavioral specs | Operations + ordering |
| 3. Design Structure | Specs + theme | Project architecture | Multi-file, realistic |
| 4. Generate Code | Architecture | Solidity contracts | Novel, not CTF copies |
| 5. Apply Obfuscation | Contracts + category | Obfuscated contracts | Techniques documented |
| 6. Create Ground Truth | Obfuscated code | ground-truth.yaml | Reasoning chains |
| 7. Generate Safe Variant | Vulnerable code | *_safe.sol files | Fixes verified |
| 8. Compile & Validate | All contracts | Manifest + build script | solc passes |

**Total estimated time per project:** 3-5 minutes with Opus model.

**Contamination Protocol:** Generated projects MUST NOT contain code from Ethernaut,
Damn Vulnerable DeFi, SWC registry test cases, Paradigm CTF, Secureum quizzes, or any
other publicly available vulnerable contract datasets. Every contract must contain
ORIGINAL business logic that looks like a real protocol.
