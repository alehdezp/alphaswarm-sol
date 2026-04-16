#!/bin/bash
set -e
echo "=== Build Verification: proxy-delegate-system-01 ==="
solc --bin --abi contracts/core/StorageProxy.sol contracts/core/VaultLogicV1.sol 2>&1
solc --bin --abi contracts/core/StorageProxy_safe.sol contracts/core/VaultLogicV1_safe.sol 2>&1
echo "All contracts compiled successfully."
