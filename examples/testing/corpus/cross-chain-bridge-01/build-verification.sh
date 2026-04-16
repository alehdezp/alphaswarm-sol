#!/bin/bash
set -e
echo "=== Build Verification: cross-chain-bridge-01 ==="
solc --bin --abi contracts/periphery/MessageVerifier.sol contracts/core/BridgeGateway.sol 2>&1
solc --bin --abi contracts/periphery/MessageVerifier_safe.sol contracts/core/BridgeGateway_safe.sol 2>&1
echo "All contracts compiled successfully."
