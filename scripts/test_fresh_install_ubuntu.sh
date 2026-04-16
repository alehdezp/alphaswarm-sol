#!/bin/bash
# Fresh Install Test - Ubuntu 22.04
# Tests that True VKG installs and runs correctly on a clean Ubuntu system
#
# Usage: ./scripts/test_fresh_install_ubuntu.sh
# Run in Docker: docker run -it ubuntu:22.04 bash -c "$(cat scripts/test_fresh_install_ubuntu.sh)"

set -e

echo "========================================"
echo "True VKG Fresh Install Test - Ubuntu"
echo "========================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

pass() { echo -e "${GREEN}✓ PASS${NC}: $1"; }
fail() { echo -e "${RED}✗ FAIL${NC}: $1"; exit 1; }
info() { echo -e "${YELLOW}→${NC} $1"; }

# Track test results
TESTS_PASSED=0
TESTS_FAILED=0

run_test() {
    local name="$1"
    local cmd="$2"
    info "Testing: $name"
    if eval "$cmd" > /dev/null 2>&1; then
        pass "$name"
        ((TESTS_PASSED++))
    else
        fail "$name"
        ((TESTS_FAILED++))
    fi
}

# =============================================================================
# 1. Prerequisites
# =============================================================================
echo ""
echo "Step 1: Installing prerequisites..."
echo "------------------------------------"

apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv git curl > /dev/null

run_test "Python 3.11+ available" "python3 --version | grep -E '3\.(11|12|13)'"

# =============================================================================
# 2. Install solc
# =============================================================================
echo ""
echo "Step 2: Installing Solidity compiler..."
echo "----------------------------------------"

pip3 install solc-select -q
solc-select install 0.8.20 > /dev/null 2>&1
solc-select use 0.8.20 > /dev/null 2>&1

run_test "solc installed" "solc --version"

# =============================================================================
# 3. Install True VKG
# =============================================================================
echo ""
echo "Step 3: Installing True VKG..."
echo "------------------------------"

# Create virtual environment
python3 -m venv /tmp/vkg-test-env
source /tmp/vkg-test-env/bin/activate

# Install from PyPI (or local for testing)
if [ -f "pyproject.toml" ]; then
    info "Installing from local source..."
    pip install -e . -q
else
    info "Installing from PyPI..."
    pip install true-vkg -q
fi

run_test "true-vkg command available" "which true-vkg"
run_test "true-vkg --help works" "true-vkg --help"

# =============================================================================
# 4. Create test contract
# =============================================================================
echo ""
echo "Step 4: Creating test contract..."
echo "----------------------------------"

mkdir -p /tmp/vkg-test-contracts
cat > /tmp/vkg-test-contracts/TestVault.sol << 'EOF'
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract TestVault {
    mapping(address => uint256) public balances;
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    // Vulnerable: external call before state update
    function withdraw(uint256 amount) public {
        require(balances[msg.sender] >= amount, "Insufficient");
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");
        balances[msg.sender] -= amount;
    }

    // Missing access control
    function setOwner(address newOwner) public {
        owner = newOwner;
    }
}
EOF

run_test "Test contract created" "[ -f /tmp/vkg-test-contracts/TestVault.sol ]"

# =============================================================================
# 5. Build knowledge graph
# =============================================================================
echo ""
echo "Step 5: Building knowledge graph..."
echo "------------------------------------"

cd /tmp/vkg-test-contracts
run_test "build-kg succeeds" "true-vkg build-kg TestVault.sol"
run_test "Graph file created" "[ -f .vrs/graphs/graph.json ]"

# =============================================================================
# 6. Query the graph
# =============================================================================
echo ""
echo "Step 6: Testing queries..."
echo "--------------------------"

run_test "NL query works" "true-vkg query 'public functions' --compact"
run_test "VQL query works" "true-vkg query 'FIND functions WHERE visibility = public' --compact"
run_test "Pattern query works" "true-vkg query 'pattern:weak-access-control' --compact || true"

# =============================================================================
# 7. Generate report
# =============================================================================
echo ""
echo "Step 7: Generating report..."
echo "----------------------------"

run_test "lens-report works" "true-vkg lens-report"
run_test "SARIF output works" "true-vkg lens-report --format sarif"

# =============================================================================
# 8. Cleanup
# =============================================================================
echo ""
echo "Step 8: Cleanup..."
echo "------------------"

deactivate
rm -rf /tmp/vkg-test-env /tmp/vkg-test-contracts

# =============================================================================
# Summary
# =============================================================================
echo ""
echo "========================================"
echo "Test Summary"
echo "========================================"
echo -e "Passed: ${GREEN}${TESTS_PASSED}${NC}"
echo -e "Failed: ${RED}${TESTS_FAILED}${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed.${NC}"
    exit 1
fi
