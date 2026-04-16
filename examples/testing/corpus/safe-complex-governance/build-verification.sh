#!/bin/bash
set -e
echo "=== Build Verification: safe-complex-governance ==="
solc --bin --abi contracts/core/SecureGovernor.sol 2>&1
echo "All contracts compiled successfully."
