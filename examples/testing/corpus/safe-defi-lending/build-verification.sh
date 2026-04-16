#!/bin/bash
set -e
echo "=== Build Verification: safe-defi-lending ==="
solc --bin --abi contracts/core/FortifiedLender.sol 2>&1
echo "All contracts compiled successfully."
