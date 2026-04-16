# VulnDocs Template: Minimal Pattern-Focused Documentation

## Purpose

Extract **core vulnerability patterns** for LLM detection, NOT exhaustive exploit documentation.

## Structure

Each vulnerability subcategory needs:
1. **`index.yaml`** - Metadata (category, severity, CWE)
2. **`core-pattern.md`** - MINIMAL pattern + code (THIS FILE REPLACES exploits.md, patterns.md, fixes.md)

**DO NOT CREATE:**
- ❌ `exploits.md` - Too verbose, includes unnecessary exploit details
- ❌ `detection.md` - Redundant with core-pattern.md
- ❌ `patterns.md` - Redundant with core-pattern.md
- ❌ `fixes.md` - Remediation included in core-pattern.md

## `core-pattern.md` Template

```markdown
# [Vulnerability Name]

## Vulnerability Pattern

**Core Issue:** [One sentence describing the vulnerability]

**Vulnerable Pattern:**
```solidity
// 5-10 lines showing WHAT is vulnerable
function vulnerable() {
    // BAD CODE HERE
}
```

**Why Vulnerable:**
- Bullet point 1
- Bullet point 2
- Bullet point 3

**Safe Pattern:**
```solidity
// 5-10 lines showing the FIX
function safe() {
    // FIXED CODE HERE
}
```

## Detection Signals

**Tier A (Deterministic):**
- `property_name: value`
- `another_property: value`

**Behavioral Signature:**
```
R:state -> OPERATION -> W:corrupted_state
```

## Fix

1. First fix step
2. Second fix step
3. Third fix step

**Real-world:** [Protocol name (year)] - OPTIONAL, one line only
```

## Content Rules

### ✅ DO INCLUDE:
- Core vulnerable pattern (5-10 lines)
- Safe pattern (5-10 lines)
- BSKG properties for detection (Tier A)
- Behavioral signature (operation sequence)
- 3-5 bullet fix steps
- One-line real-world reference (optional)

### ❌ DO NOT INCLUDE:
- Financial losses ($X million)
- Detailed attack steps (Step 1, Step 2...)
- Flash loan amplification details
- Cross-chain extraction details
- Recovery efforts
- Audit firm names
- Chain counts
- "Lessons learned" sections
- Multiple code examples per pattern
- Test code
- Deployment checklists
- Monitoring details

## Pattern Extraction

When processing multiple vulnerabilities:

1. **Group by root cause** - If 5 exploits have same root cause, create ONE pattern
2. **Extract commonality** - What's the shared vulnerable pattern?
3. **Minimal diff** - Show vulnerable vs safe (smallest possible diff)
4. **Focus on detection** - What helps LLM identify this bug?

### Example: Multiple Reentrancy Exploits

If you find:
- DAO Hack (2016)
- Lendf.me (2020)
- Cream Finance (2021)
- Fei Protocol (2022)

**Create ONE pattern:**
```markdown
# Classic Reentrancy

**Vulnerable:**
```solidity
function withdraw() external {
    msg.sender.call{value: balance}(""); // External call first
    balance[msg.sender] = 0; // State update after
}
```

**Safe:**
```solidity
function withdraw() external {
    uint256 amount = balance[msg.sender];
    balance[msg.sender] = 0; // State update first
    msg.sender.call{value: amount}(""); // External call after
}
```

**Real-world:** DAO (2016), Lendf.me (2020), Cream (2021), Fei (2022)
```

Do NOT create 4 separate documents.

## Dynamic Weights (Future)

Patterns may include dynamic weights based on:
- Frequency in current codebase
- Protocol type (DeFi, NFT, DAO)
- Solidity version

Example:
```yaml
weight_factors:
  - condition: "has_external_calls > 5"
    multiplier: 1.5
  - condition: "protocol_type = AMM"
    multiplier: 2.0
```

## Validation

Before committing VulnDocs:

1. ✅ core-pattern.md < 100 lines?
2. ✅ Code examples < 15 lines each?
3. ✅ No financial loss details?
4. ✅ No detailed attack sequences?
5. ✅ Pattern covers multiple vulnerabilities if applicable?
6. ✅ Detection signals are VKG-compatible?

If any answer is NO, revise.

## Agent Instructions

For `knowledge-aggregation-worker`:

```
When processing vulnerability sources:

1. EXTRACT patterns, not exploits
2. GROUP similar vulnerabilities under one pattern
3. CREATE minimal core-pattern.md (< 100 lines)
4. SHOW vulnerable vs safe (5-10 lines each)
5. OMIT financial losses, attack details, recovery info
6. FOCUS on what helps LLM detect the bug

If you find 10 vulnerabilities with same root cause:
- Create ONE pattern
- Mention all 10 in one line: "Real-world: ProtocolA (2020), ProtocolB (2021), ..."
- Do NOT create 10 separate documents
```

---

**This template supersedes previous verbose documentation approach.**
**Goal: Minimal, pattern-focused, LLM-optimized vulnerability knowledge.**
