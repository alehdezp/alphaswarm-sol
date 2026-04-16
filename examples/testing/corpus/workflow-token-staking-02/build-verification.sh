#!/bin/bash
set -e
echo "=== Build Verification: workflow-token-staking-02 ==="
echo "Compiling vulnerable contracts..."
solc --bin --abi contracts/interfaces/IStakeEngine.sol contracts/libraries/RewardCalc.sol contracts/core/StakeEngine.sol contracts/periphery/StakeRouter.sol 2>&1
echo ""
echo "Compiling safe contracts..."
solc --bin --abi contracts/interfaces/IStakeEngine.sol contracts/libraries/RewardCalc.sol contracts/core/StakeEngine_safe.sol contracts/periphery/StakeRouter_safe.sol 2>&1
echo ""
echo "All contracts compiled successfully."
