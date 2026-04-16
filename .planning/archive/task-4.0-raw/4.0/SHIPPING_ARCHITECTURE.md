# BSKG Shipping Architecture

**Goal:** One-command setup, zero manual configuration, works with ANY AI agent immediately.

**Last Updated:** 2026-01-07

---

## Installation Flow

```bash
# Step 1: Install
pip install alphaswarm    # or: uv add alphaswarm

# Step 2: Setup (everything configured automatically)
vkg setup

# Step 3: Done - any AI agent can use BSKG immediately
```

---

## Core Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         BSKG SHIPPING PACKAGE                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                    CLI + AGENTS.md (Primary Integration)                │ │
│  │                                                                         │ │
│  │  CLI COMMANDS:                                                          │ │
│  │  ├── vkg build <path>       Build knowledge graph from contracts       │ │
│  │  ├── vkg analyze <path>     Full security analysis                     │ │
│  │  ├── vkg query "<query>"    Natural language query                     │ │
│  │  ├── vkg findings list      List all findings                          │ │
│  │  ├── vkg findings get <id>  Get finding details                        │ │
│  │  ├── vkg bead get <id>      Get investigation context (TOON)           │ │
│  │  ├── vkg grimoire <name>    Execute testing playbook                   │ │
│  │  ├── vkg test <test>        Run Foundry test                           │ │
│  │  ├── vkg fuzz <contract>    Run Medusa/Echidna fuzzing                 │ │
│  │  ├── vkg fork <rpc>         Create mainnet fork (anvil)                │ │
│  │  ├── vkg deploy <testnet>   Deploy to testnet                          │ │
│  │  ├── vkg patterns list      List available patterns                    │ │
│  │  ├── vkg report             Generate audit report                      │ │
│  │  └── vkg doctor             Health check                               │ │
│  │                                                                         │ │
│  │  STRUCTURED OUTPUT:                                                     │ │
│  │  ├── --output json          JSON format for parsing                    │ │
│  │  ├── --output sarif         SARIF for CI/CD integration                │ │
│  │  ├── --output toon          TOON format (LLM-optimized)                │ │
│  │  └── --compact              Minimal output                             │ │
│  │                                                                         │ │
│  │  AGENTS.md:                                                             │ │
│  │  └── Universal tool discovery file for all AI agents                   │ │
│  │                                                                         │ │
│  │  NOTE: MCP-VKG server planned for future release                       │ │
│  │                                                                         │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                    AGENT-SPECIFIC CONFIGS (Auto-Generated)              │ │
│  │                                                                         │ │
│  │  PRIORITY: SKILLS > MCPs                                                │ │
│  │  ═══════════════════════════════════════                               │ │
│  │  Skills are preferred - smaller context, faster execution.             │ │
│  │  MCPs load on-demand only when stateful operations needed.             │ │
│  │                                                                         │ │
│  │  CLAUDE CODE:                                                           │ │
│  │  ├── .claude/skills/              ★ PRIMARY: 36 grimoire skills       │ │
│  │  │   ├── test-reentrancy.md       Skill for reentrancy testing        │ │
│  │  │   ├── test-access.md           Skill for access control testing    │ │
│  │  │   ├── test-oracle.md           Skill for oracle testing            │ │
│  │  │   ├── full-audit.md            Skill for complete audit            │ │
│  │  │   └── ...                                                           │ │
│  │  ├── .claude/settings.json        MCPs registered (on-demand load)    │ │
│  │  │   └── autoload: false for all MCPs                                 │ │
│  │  └── CLAUDE.md                    BSKG section appended                 │ │
│  │                                                                         │ │
│  │  CODEX:                                                                 │ │
│  │  ├── codex.yaml                   Tool + skill definitions             │ │
│  │  ├── .codex/skills/               ★ PRIMARY: Grimoire skills          │ │
│  │  └── .codex/tools/vkg.yaml        CLI tool config                      │ │
│  │                                                                         │ │
│  │  OPENCODE:                                                              │ │
│  │  ├── opencode.yaml                Config file                          │ │
│  │  ├── .opencode/skills/            ★ PRIMARY: Grimoire skills          │ │
│  │  └── .opencode/mcp.json           MCPs (on-demand)                     │ │
│  │                                                                         │ │
│  │  CURSOR:                                                                │ │
│  │  ├── .cursorrules                 Context + BSKG rules + skills        │ │
│  │  └── .cursor/mcp.json             MCPs (on-demand)                     │ │
│  │                                                                         │ │
│  │  WINDSURF:                                                              │ │
│  │  ├── .windsurfrules               Context + BSKG rules + skills        │ │
│  │  └── .windsurf/mcp.json           MCPs (on-demand)                     │ │
│  │                                                                         │ │
│  │  MCP SERVERS (registered, load ON-DEMAND):                             │ │
│  │  ├── mcp-foundry                  When: Forge test needs live anvil   │ │
│  │  ├── mcp-ethereum                 When: RPC calls, tx simulation      │ │
│  │  ├── mcp-slither                  When: Deep static analysis          │ │
│  │  └── mcp-tenderly                 When: Fork simulation needed        │ │
│  │                                                                         │ │
│  │  UNIVERSAL (always created):                                            │ │
│  │  └── AGENTS.md                    Universal tool discovery             │ │
│  │                                                                         │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                    TESTING TOOLS (Auto-Installed)                       │ │
│  │                                                                         │ │
│  │  FRAMEWORKS:                                                            │ │
│  │  ├── Foundry (forge, cast, anvil, chisel)                              │ │
│  │  │   └── Latest features: --gas-report, --ffi, fork caching            │ │
│  │  ├── Hardhat + plugins                                                  │ │
│  │  │   └── hardhat-deploy, hardhat-tracer, console.log                   │ │
│  │  ├── Medusa (Consensys fuzzer)                                          │ │
│  │  │   └── Parallel fuzzing, property-based testing                      │ │
│  │  ├── Echidna (Trail of Bits)                                            │ │
│  │  │   └── Coverage-guided mutation testing                              │ │
│  │  └── Slither (static analysis)                                          │ │
│  │      └── Detector integration, custom queries                          │ │
│  │                                                                         │ │
│  │  SIMULATION:                                                            │ │
│  │  ├── Tenderly (fork simulation, tx tracing)                            │ │
│  │  ├── Anvil (local fork with state)                                     │ │
│  │  └── Hardhat Network (JS-based simulation)                             │ │
│  │                                                                         │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                    TESTNETS (Pre-Configured, Free Tier)                 │ │
│  │                                                                         │ │
│  │  ETHEREUM:                                                              │ │
│  │  ├── Sepolia       Primary testnet (public RPC bundled)                │ │
│  │  └── Holesky       Staking testnet (public RPC bundled)                │ │
│  │                                                                         │ │
│  │  LAYER 2:                                                               │ │
│  │  ├── Base Sepolia      Base L2 testnet                                 │ │
│  │  ├── Arbitrum Sepolia  Arbitrum L2 testnet                             │ │
│  │  ├── OP Sepolia        Optimism L2 testnet                             │ │
│  │  └── Polygon Amoy      Polygon L2 testnet                              │ │
│  │                                                                         │ │
│  │  FALLBACK:                                                              │ │
│  │  └── Infura/Alchemy free tier auto-configured                          │ │
│  │                                                                         │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Grimoire Catalog (34+ Testing Playbooks)

Each grimoire is a complete testing playbook invocable as a skill:

### Reentrancy (3 grimoires)
| Skill | Variant | Tools | Key Tests |
|-------|---------|-------|-----------|
| `/test-reentrancy-classic` | CEI violation | Foundry, fork | State write after call |
| `/test-reentrancy-cross-fn` | Cross-function | Foundry, fork | Multi-function attack |
| `/test-reentrancy-readonly` | View reentrancy | Foundry | Read-only manipulation |

### Access Control (4 grimoires)
| Skill | Variant | Tools | Key Tests |
|-------|---------|-------|-----------|
| `/test-access-missing` | No modifier | Foundry | Direct state write |
| `/test-access-bypass` | Logic bypass | Foundry, fuzz | Conditional bypass |
| `/test-access-role` | Role escalation | Foundry | Privilege escalation |
| `/test-access-origin` | tx.origin | Foundry | Phishing attack |

### Oracle (4 grimoires)
| Skill | Variant | Tools | Key Tests |
|-------|---------|-------|-----------|
| `/test-oracle-stale` | Staleness | Fork, Chainlink | Outdated price |
| `/test-oracle-manipulation` | Price manipulation | Fork | Flash loan attack |
| `/test-oracle-twap` | TWAP window | Fork | Window manipulation |
| `/test-oracle-sequencer` | L2 sequencer | Fork | Sequencer down |

### DoS (3 grimoires)
| Skill | Variant | Tools | Key Tests |
|-------|---------|-------|-----------|
| `/test-dos-unbounded` | Unbounded loop | Medusa, gas | Gas exhaustion |
| `/test-dos-external-loop` | External in loop | Foundry | Revert cascade |
| `/test-dos-gas` | Gas griefing | Foundry | Deliberate revert |

### MEV (3 grimoires)
| Skill | Variant | Tools | Key Tests |
|-------|---------|-------|-----------|
| `/test-mev-sandwich` | Sandwich | Fork, simulate | Price extraction |
| `/test-mev-frontrun` | Frontrunning | Fork | Transaction ordering |
| `/test-mev-backrun` | Backrunning | Fork | Post-tx extraction |

### Token (5 grimoires)
| Skill | Variant | Tools | Key Tests |
|-------|---------|-------|-----------|
| `/test-token-return` | Unchecked return | Foundry | Silent failure |
| `/test-token-fee` | Fee-on-transfer | Foundry, fuzz | Balance mismatch |
| `/test-token-approval` | Approval race | Foundry | Double spend |
| `/test-token-erc777` | ERC777 hooks | Foundry | Callback attack |
| `/test-token-infinite` | Infinite approval | Foundry | Unlimited drain |

### Upgrade (4 grimoires)
| Skill | Variant | Tools | Key Tests |
|-------|---------|-------|-----------|
| `/test-upgrade-gap` | Storage gap | Foundry | Collision |
| `/test-upgrade-init` | Initializer | Foundry | Re-initialization |
| `/test-upgrade-destruct` | Selfdestruct | Foundry | Logic destruction |
| `/test-upgrade-delegate` | Delegatecall | Foundry | Untrusted target |

### Cryptography (3 grimoires)
| Skill | Variant | Tools | Key Tests |
|-------|---------|-------|-----------|
| `/test-crypto-sig` | Signature malleability | Foundry | s-value flip |
| `/test-crypto-ecrecover` | Zero address | Foundry | Invalid signature |
| `/test-crypto-replay` | Replay attack | Foundry, fork | Cross-chain replay |

### Flash Loan (2 grimoires)
| Skill | Variant | Tools | Key Tests |
|-------|---------|-------|-----------|
| `/test-flashloan-attack` | General attack | Fork | Arbitrage exploit |
| `/test-flashloan-oracle` | Oracle via flash | Fork | Price manipulation |

### Governance (3 grimoires)
| Skill | Variant | Tools | Key Tests |
|-------|---------|-------|-----------|
| `/test-gov-flashloan` | Flash loan voting | Fork | Vote manipulation |
| `/test-gov-timelock` | Timelock bypass | Foundry | Execution skip |
| `/test-gov-central` | Centralization | Foundry | Single point |

### Meta (2 grimoires)
| Skill | Variant | Tools | Key Tests |
|-------|---------|-------|-----------|
| `/full-audit` | Complete audit | All | All patterns |
| `/quick-scan` | Fast scan | Foundry | Critical only |

**Total: 36 grimoires**

---

## SDK Feature Matrix

Use the most performant features from each SDK:

| Feature | Claude Code | Codex | OpenCode |
|---------|-------------|-------|----------|
| **MCP Support** | Native | TBD | Native |
| **Skills Location** | `.claude/skills/` | `codex.yaml` | `.opencode/skills/` |
| **Subagent Spawn** | Agent SDK | Codex SDK | OpenCode SDK |
| **Thread Resume** | Automatic | `codex exec resume` | Automatic |
| **Structured Output** | `tool_use` | `--output-schema` | Native |
| **Background Tasks** | `Task` tool | `--full-auto` | Background mode |
| **Noninteractive** | `--print` | `codex exec` | `--headless` |
| **Best For** | Complex reasoning | Code generation | Multi-provider |

### Claude Code Optimization
```json
// .claude/settings.json
{
  "mcpServers": {
    // MCPs registered but loaded ON-DEMAND (not at startup)
    "mcp-foundry": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-foundry"],
      "env": {},
      "autoload": false  // Load when needed
    },
    "mcp-ethereum": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-ethereum"],
      "env": {},
      "autoload": false  // Load when needed
    }
  }
}
```

**Note:** Skills are PREFERRED over MCPs for all grimoire operations. MCPs only activate when stateful operations (forks, live RPC) are needed.

### Codex Optimization
```yaml
# codex.yaml
tools:
  vkg:
    command: vkg
    description: Security analysis for Solidity smart contracts

noninteractive:
  output_schema: true
  full_auto: false  # Require approval for dangerous operations
```

### OpenCode Optimization
```yaml
# opencode.yaml
mcp:
  servers:
    vkg:
      command: vkg mcp serve

providers:
  default: anthropic  # Or whatever the user has configured
  zen_mode: true      # Curated models only
```

---

## vkg setup Command

```python
# Pseudocode for vkg setup
def setup():
    # 1. Detect installed agents
    agents = detect_agents()  # Claude Code, Codex, OpenCode, Cursor...

    # 2. Install testing tools (CLI-based, no MCPs needed)
    install_foundry()   # forge, cast, anvil, chisel
    install_medusa()    # Consensys fuzzer
    install_echidna()   # Trail of Bits fuzzer
    install_slither()   # Static analysis

    # 3. Configure testnets (just RPC config, no MCP)
    configure_testnets()  # Creates ~/.vrs/testnets.yaml

    # 4. Install SKILLS (PRIMARY - 36 grimoires)
    install_grimoires_as_skills()  # Skills invoke CLI commands directly

    # 5. Register MCPs (on-demand, NOT auto-loaded)
    register_mcps_lazy()  # autoload: false for all

    # 6. Generate agent-specific configs
    for agent in agents:
        generate_config(agent)  # Skills first, MCPs as fallback

    # 7. Create AGENTS.md (universal discovery)
    create_agents_md()

    # 8. Run doctor
    run_doctor()

    print("VKG is ready! Run: vkg analyze ./contracts/")
    print("Use /test-reentrancy, /full-audit, etc. for security testing")
```

### Skills vs MCPs Decision Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  AGENT NEEDS TO TEST FOR REENTRANCY                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  STEP 1: Check if skill available                               │
│          /test-reentrancy → FOUND → USE SKILL                   │
│          ├── Skill invokes: vkg bead get <id> --format toon    │
│          ├── Skill invokes: forge test --match-contract        │
│          └── Result: Fast, minimal context                      │
│                                                                  │
│  STEP 2: Only if skill needs live blockchain data               │
│          Agent detects: needs fork simulation                   │
│          → Activate mcp-tenderly (on-demand)                    │
│          → Use MCP for stateful fork operations                 │
│          → Deactivate when done                                 │
│                                                                  │
│  RESULT: Skills handle 90% of cases, MCPs only when necessary   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## vkg doctor Output

```
$ vkg doctor

VKG Health Check
════════════════════════════════════════════════════════════════

Core:
  ✅ BSKG version 4.0.0
  ✅ Knowledge graph engine operational
  ✅ Pattern engine loaded (200+ patterns)

Tools:
  ✅ Foundry (forge 0.2.0, cast 0.2.0, anvil 0.2.0)
  ✅ Medusa (0.1.0)
  ✅ Echidna (2.2.0)
  ✅ Slither (0.10.0)

Testnets:
  ✅ Sepolia (connected, 12ms latency)
  ✅ Holesky (connected, 15ms latency)
  ✅ Base Sepolia (connected, 20ms latency)
  ✅ Arbitrum Sepolia (connected, 18ms latency)
  ✅ OP Sepolia (connected, 22ms latency)

MCP Servers (On-Demand):
  ⏸️ mcp-foundry (registered, loads when needed)
  ⏸️ mcp-ethereum (registered, loads when needed)
  ⏸️ mcp-slither (registered, loads when needed)
  ⏸️ mcp-tenderly (registered, loads when needed)
  ℹ️  MCPs load on-demand to minimize context bloat

Agent Configs:
  ✅ Claude Code (.claude/settings.json + 36 skills)
  ✅ Codex (codex.yaml)
  ⚠️  OpenCode (not detected - install for support)
  ✅ Cursor (.cursorrules + .cursor/mcp.json)
  ✅ AGENTS.md (universal discovery)

Grimoires:
  ✅ 36 grimoires installed
  ✅ All skills invocable

Beads:
  ✅ BeadCreator operational
  ✅ TOON encoder working (30-50% reduction verified)

════════════════════════════════════════════════════════════════
Status: READY
Run `vkg analyze <path>` to start security analysis.
```

---

## Key Principles

1. **Zero Manual Configuration**
   - `vkg setup` handles everything
   - No config files to edit manually
   - Auto-detect and configure for installed agents

2. **Skills > MCPs (Context Efficiency)**
   - **Prefer skills over MCPs whenever possible**
   - Skills are lightweight, focused, and don't bloat context
   - MCPs add overhead (capability listing, protocol messages)
   - Skills execute faster with less token cost

   **When to use skills:**
   - Testing playbooks (grimoires) → Skills
   - Common workflows → Skills
   - Single-purpose commands → Skills

   **When MCPs make sense:**
   - Complex stateful operations (fork management)
   - Real-time data feeds (RPC calls)
   - Operations needing bidirectional communication

3. **On-Demand MCP Loading**
   - **MCPs are NOT all enabled by default**
   - Register MCPs but load lazily when needed
   - Agent requests capability → MCP activates
   - Reduces context bloat and startup time

   ```
   ┌─────────────────────────────────────────────────────┐
   │  MCP LOADING STRATEGY                               │
   ├─────────────────────────────────────────────────────┤
   │                                                      │
   │  DEFAULT STATE:                                      │
   │  ├── mcp-foundry       REGISTERED (not loaded)      │
   │  ├── mcp-ethereum      REGISTERED (not loaded)      │
   │  ├── mcp-slither       REGISTERED (not loaded)      │
   │  └── mcp-tenderly      REGISTERED (not loaded)      │
   │                                                      │
   │  WHEN AGENT NEEDS FORK:                             │
   │  └── mcp-tenderly      LOADED (on-demand)           │
   │                                                      │
   │  RESULT:                                             │
   │  ├── Smaller initial context                        │
   │  ├── Faster startup                                 │
   │  └── Only pay for what you use                      │
   │                                                      │
   └─────────────────────────────────────────────────────┘
   ```

4. **CLI + AGENTS.md Primary Integration**
   - BSKG accessed via CLI commands (not MCP server)
   - AGENTS.md for universal tool discovery
   - Skills invoke CLI commands directly

5. **Agent-Specific Optimization**
   - Each agent gets its native config format
   - Use most performant features per SDK
   - Fallback to AGENTS.md always works

6. **Complete Testing Toolkit**
   - All security testing tools pre-installed
   - All testnets pre-configured with free RPCs
   - All grimoires (36) ready to invoke as skills

7. **Context Efficiency**
   - Beads provide complete context per finding
   - TOON format for 30-50% token savings
   - Graph slicing removes irrelevant properties (75% reduction)
   - Skills minimize protocol overhead

8. **Verification Built-In**
   - `vkg doctor` confirms everything works
   - Clear error messages if something is missing
   - Guided remediation for issues

---

## File Structure After Setup

```
project/
├── .claude/                      # Claude Code config
│   ├── settings.json             # MCP registration
│   └── skills/                   # 36 grimoire skills
│       ├── test-reentrancy.md
│       ├── test-access.md
│       ├── ...
│       └── full-audit.md
├── .cursor/                      # Cursor config
│   └── mcp.json                  # MCP registration
├── .cursorrules                  # Cursor context
├── codex.yaml                    # Codex config
├── AGENTS.md                     # Universal discovery
├── .vrs/                         # BSKG local config
│   ├── config.yaml               # Project config
│   ├── testnets.yaml             # Testnet RPCs
│   └── cache/                    # Graph cache
└── contracts/                    # User's contracts
    └── *.sol
```

---

*SHIPPING_ARCHITECTURE.md | BSKG 4.0 | 2026-01-07*
