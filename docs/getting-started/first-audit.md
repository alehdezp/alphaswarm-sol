# First Audit

Run your first security audit with AlphaSwarm.sol.

## Prerequisites

- AlphaSwarm.sol installed ([Installation Guide](installation.md))
- Claude Code installed and configured
- A Solidity project to analyze

## The Primary Workflow: /vrs-audit

> **v6.0 Status:** The 9-stage pipeline is the TARGET design. Currently, Stages 1-3 work reliably. The full E2E pipeline (through Stage 9) is the goal of Phase 3. See `.planning/STATE.md` for current status.

AlphaSwarm.sol runs through Claude Code as a 9-stage orchestrated pipeline:

```bash
# In your project directory, start Claude Code
claude

# Run the full audit pipeline (Phase 3 target)
/vrs-audit contracts/
```

This executes:

| Stage | What Happens |
|-------|--------------|
| 1. Preflight | Validate settings, check tools, load state |
| 2. Build Graph | Claude Code invokes `alphaswarm build-kg` → BSKG with 200+ properties/function |
| 3. Protocol Context | Exa MCP research for economic context |
| 4. Tool Init | Run static analyzers (Slither, Aderyn) |
| 5. Pattern Detection | 466 active patterns (Tier A/B/C) against graph |
| 6. Task Creation | TaskCreate per candidate finding |
| 7. Verification | Attacker → Defender → Verifier debate |
| 8. Report Generation | Evidence-linked findings |
| 9. Progress Update | Store state, emit resume hints |

---

## Optional: Manual Tool Steps (Development/Debug)

If you want to inspect individual stages outside the orchestrated workflow, use direct tool commands:

### Step 1: Create a Test Contract

Create `Vault.sol`:

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Vault {
    mapping(address => uint256) public balances;
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    // VULNERABLE: external call before state update (reentrancy)
    function withdraw(uint256 amount) public {
        require(balances[msg.sender] >= amount, "Insufficient");
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");
        balances[msg.sender] -= amount;  // State update AFTER call
    }

    // VULNERABLE: no access control on privileged function
    function setOwner(address newOwner) public {
        owner = newOwner;
    }
}
```

### Step 2: Build the Knowledge Graph

```bash
uv run alphaswarm build-kg Vault.sol
```

Output:
```
Building BSKG for: Vault.sol
Analyzing with Slither...
Deriving security properties...
Graph saved: .vrs/graphs/graph.toon
Nodes: 8 | Edges: 12 | Properties: 156
```

### Step 3: Query for Vulnerabilities

**Natural Language:**
```bash
uv run alphaswarm query "functions with external calls before state writes"
```

**VQL:**
```bash
uv run alphaswarm query "FIND functions WHERE state_write_after_external_call = true"
```

**Pattern:**
```bash
uv run alphaswarm query "pattern:reentrancy-classic"
```

### Step 4: Check Tool Status

```bash
uv run alphaswarm tools status
```

Shows which security tools are available (Slither, Aderyn, Mythril, etc.).

---

## Understanding the Output

### Finding Structure

```yaml
id: reen-001-Vault.withdraw
pattern: reentrancy-classic
severity: critical
confidence: 0.92
location:
  file: Vault.sol
  contract: Vault
  function: withdraw
  lines: [15, 21]
behavioral_signature: R:bal -> X:out -> W:bal
evidence:
  - state_write_after_external_call: true
  - has_reentrancy_guard: false
  - external_call_line: 18
  - state_write_line: 20
```

### Behavioral Signatures

AlphaSwarm.sol detects **behavior**, not function names:

```
R:bal -> X:out -> W:bal   # VULNERABLE: external call before state update
R:bal -> W:bal -> X:out   # SAFE: CEI pattern (Checks-Effects-Interactions)
```

| Code | Meaning |
|------|---------|
| `R:bal` | Read user balance |
| `W:bal` | Write user balance |
| `X:out` | Transfer value out |
| `C:auth` | Permission check |
| `M:crit` | Modify critical state |

---

## The Full Audit (Recommended)

For real audits, always use the full pipeline:

```bash
# Start Claude Code in your project
claude

# Run full audit with multi-agent verification
/vrs-audit contracts/
```

This gives you:
- Protocol context research (economic risks, similar exploits)
- Multi-agent debate (attacker finds exploit, defender finds guards)
- Evidence-linked findings with proof tokens
- Confidence buckets (confirmed/likely/uncertain/rejected)

---

## CI/CD Integration

### GitHub Actions

These are headless tool examples for CI pipelines (not the primary user workflow).

```yaml
- name: Run AlphaSwarm.sol
  run: |
    uv run alphaswarm build-kg contracts/
    uv run alphaswarm query "pattern:*" --format sarif > results.sarif

- name: Upload SARIF
  uses: github/codeql-action/upload-sarif@v2
  with:
    sarif_file: results.sarif
```

### Exit Code

```bash
uv run alphaswarm query "pattern:*" --exit-code --min-severity high
# Exit 1 if high/critical findings exist
```

---

## Troubleshooting

### "Slither not found"

```bash
pip install slither-analyzer
```

### "Solc version mismatch"

```bash
# Install solc-select
pip install solc-select

# Install and use correct version
solc-select install 0.8.20
solc-select use 0.8.20
```

### "No findings" on vulnerable code

1. Check the graph was built: `ls .vrs/graphs/`
2. Query all functions: `uv run alphaswarm query "FIND functions"`
3. Check specific properties: `uv run alphaswarm query "FIND functions WHERE has_external_call = true"`

---

## Next Steps

| Goal | Resource |
|------|----------|
| Learn query syntax | [Query Guide](../guides/queries.md) |
| Write custom patterns | [Pattern Guide](../guides/patterns.md) |
| Configure agents | [Agent Reference](../reference/agents.md) |
| Understand the system | [Architecture](../architecture.md) |
| Know the limits | [Honest Limitations](../LIMITATIONS.md) |
