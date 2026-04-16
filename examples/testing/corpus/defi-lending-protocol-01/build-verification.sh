#!/bin/bash
set -e
echo "=== Build Verification: defi-lending-protocol-01 ==="
echo "Compiling vulnerable contracts..."
solc --bin --abi contracts/interfaces/IAssetOracle.sol contracts/libraries/PositionMath.sol contracts/core/CreditFacility.sol contracts/periphery/RiskEngine.sol 2>&1
echo ""
echo "Compiling safe contracts..."
solc --bin --abi contracts/interfaces/IAssetOracle.sol contracts/libraries/PositionMath.sol contracts/core/CreditFacility_safe.sol contracts/periphery/RiskEngine_safe.sol 2>&1
echo ""
echo "All contracts compiled successfully."
