#!/bin/bash
set -e
echo "=== Build Verification: governance-timelock-02 ==="
solc --bin --abi contracts/core/ProposalRegistry.sol contracts/core/TimelockController.sol 2>&1
solc --bin --abi contracts/core/ProposalRegistry_safe.sol contracts/core/TimelockController_safe.sol 2>&1
echo "All contracts compiled successfully."
