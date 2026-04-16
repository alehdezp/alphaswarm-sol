# Installation

This guide covers installing AlphaSwarm.sol and its dependencies.

## Requirements

- **Python 3.11+** - Check with `python --version`
- **Solc** - Solidity compiler for contract parsing
- **Git** - For source installation (optional)

## Installation Methods

> **Note:** AlphaSwarm.sol is not yet published to PyPI. Install from source.
>
> **Primary workflow:** AlphaSwarm.sol is Claude Code workflow-first. End users invoke `/vrs-*` skills; CLI commands are subordinate tool calls for development, CI, or deep diagnostics.

### Using uv (Recommended)

```bash
# Clone the repository (internal — not yet public)
git clone <repo-url>
cd alphaswarm

# Install as a tool (available globally)
uv tool install -e .

# Optional tool-level verification
uv run alphaswarm --version
```

To install from an existing local clone:

```bash
# Install from absolute path (run from anywhere)
uv tool install -e /path/to/alphaswarm
```

### Using pip

```bash
git clone <repo-url>
cd alphaswarm
pip install -e .
```

### Development Mode (without global install)

If you don't want to install globally, you can run directly with uv:

```bash
cd /path/to/alphaswarm
uv run alphaswarm --help
```

## Installing Dependencies

### Solidity Compiler (solc)

AlphaSwarm.sol uses Slither for parsing, which requires a Solidity compiler.

=== "Using solc-select (Recommended)"

    ```bash
    pip install solc-select
    solc-select install 0.8.20
    solc-select use 0.8.20
    ```

=== "macOS"

    ```bash
    brew install solidity
    ```

=== "Ubuntu/Debian"

    ```bash
    sudo add-apt-repository ppa:ethereum/ethereum
    sudo apt update
    sudo apt install solc
    ```

=== "Windows (WSL)"

    ```bash
    # Use WSL with Ubuntu
    sudo add-apt-repository ppa:ethereum/ethereum
    sudo apt update
    sudo apt install solc
    ```

### Verify Solc Installation

```bash
solc --version
# Expected: solc, the solidity compiler commandline interface
```

## Verifying Installation

After installation, verify the workflow surface first:

1. Start Claude Code in your target project.
2. Run `/vrs-health-check`.
3. Confirm tool checks and environment checks pass.

Optional tool-level checks:

```bash
uv run alphaswarm --help
uv run alphaswarm --version
```

## VRS Directory Structure

AlphaSwarm.sol uses a `.vrs/` directory to store configuration and artifacts:

```
project/
  .vrs/
    graphs/          # Knowledge graphs
    beads/           # Investigation beads
    tools.yaml       # Tool configuration
    AGENTS.md        # Agent interface documentation
```

## Optional: External Tools

AlphaSwarm.sol can integrate with external security tools for enhanced detection:

| Tool | Purpose | Installation |
|------|---------|--------------|
| Slither | Static analysis (required) | `pip install slither-analyzer` |
| Aderyn | Additional detectors | `cargo install aderyn` |
| Mythril | Symbolic execution | `pip install mythril` |
| Echidna | Property fuzzing | [Binary download](https://github.com/crytic/echidna) |
| Foundry | Testing framework | `curl -L https://foundry.paradigm.xyz \| bash` |

Check tool status:

```bash
uv run alphaswarm tools status
```

## Claude Code Integration

For workflow-first auditing with Claude Code:

1. Ensure Claude Code is installed
2. Initialize VRS in your project:

```bash
uv run alphaswarm init
```

This creates the `.vrs/` directory with:

- Agent interface documentation (`.vrs/AGENTS.md`)
- Default tool configuration (`.vrs/tools.yaml`)
- Skills integration for Claude Code

## Troubleshooting

### "Command not found: alphaswarm"

The CLI entry point may not be in your PATH. Try:

```bash
# If installed with pip
python -m alphaswarm_sol.cli --help

# If using uv
uv run alphaswarm --help
```

### "Slither not found"

Install Slither explicitly:

```bash
pip install slither-analyzer
```

### "Solc version mismatch"

Check the pragma in your contracts and install the matching version:

```bash
grep "pragma solidity" contracts/*.sol
solc-select install <version>
solc-select use <version>
```

### Windows Issues

AlphaSwarm.sol requires WSL on Windows. Native Windows is not supported due to Slither dependencies.

## Next Steps

- [First Audit](first-audit.md) - Run your first security analysis
- [Claude Code Workflow Architecture](../claude-code-architecture.md) - Workflow-first model, APIs, and lifecycle
- [CLI Reference](../reference/cli.md) - Tool-level command reference (subagent/dev)
