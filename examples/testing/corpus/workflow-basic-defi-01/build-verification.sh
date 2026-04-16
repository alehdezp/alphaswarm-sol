#!/bin/bash
set -e
echo "=== Build Verification: workflow-basic-defi-01 ==="
echo "Compiling vulnerable contracts..."
solc --bin --abi contracts/interfaces/IVaultCore.sol contracts/interfaces/IPriceFeed.sol contracts/libraries/ShareMath.sol contracts/core/SimpleVault.sol contracts/periphery/RewardDistributor.sol 2>&1
echo ""
echo "Compiling safe contracts..."
solc --bin --abi contracts/interfaces/IVaultCore.sol contracts/interfaces/IPriceFeed.sol contracts/libraries/ShareMath.sol contracts/core/SimpleVault_safe.sol contracts/periphery/RewardDistributor_safe.sol 2>&1
echo ""
echo "All contracts compiled successfully."
