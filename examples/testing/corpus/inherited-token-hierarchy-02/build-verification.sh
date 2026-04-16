#!/bin/bash
set -e
echo "=== Build Verification: inherited-token-hierarchy-02 ==="
solc --bin --abi contracts/core/BaseToken.sol contracts/core/MintableToken.sol contracts/core/RewardToken.sol 2>&1
solc --bin --abi contracts/core/BaseToken.sol contracts/core/RewardToken_safe.sol 2>&1
echo "All contracts compiled successfully."
