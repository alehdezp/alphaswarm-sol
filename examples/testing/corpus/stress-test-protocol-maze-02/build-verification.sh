#!/bin/bash
set -e
echo "=== Build Verification: stress-test-protocol-maze-02 ==="
solc --bin --abi contracts/libraries/CipherLib.sol contracts/periphery/DataRegistry.sol contracts/core/NexusController.sol 2>&1
solc --bin --abi contracts/libraries/CipherLib.sol contracts/periphery/DataRegistry_safe.sol contracts/core/NexusController_safe.sol 2>&1
echo "All contracts compiled successfully."
