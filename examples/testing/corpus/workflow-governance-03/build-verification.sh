#!/bin/bash
set -e
echo "=== Build Verification: workflow-governance-03 ==="
echo "Compiling vulnerable contracts..."
solc --bin --abi contracts/core/GovernorAlpha.sol contracts/periphery/VoteAggregator.sol 2>&1
echo ""
echo "Compiling safe contracts..."
solc --bin --abi contracts/core/GovernorAlpha_safe.sol contracts/periphery/VoteAggregator_safe.sol 2>&1
echo ""
echo "All contracts compiled successfully."
