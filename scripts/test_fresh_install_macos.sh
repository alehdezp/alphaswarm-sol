#!/bin/bash
# Fresh Install Test - macOS
# Tests that True VKG installs and runs correctly on a clean macOS system
#
# Usage: ./scripts/test_fresh_install_macos.sh

set -e

echo "========================================"
echo "True VKG Fresh Install Test - macOS"
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
# 1. Prerequisites Check
# =============================================================================
echo ""
echo "Step 1: Checking prerequisites..."
echo "----------------------------------"

# Check Python
if ! command -v python3 &> /dev/null; then
    fail "Python 3 not found. Install with: brew install python@3.11"
fi
run_test "Python 3.11+ available" "python3 --version | grep -E '3\.(11|12|13)'"

# Check Homebrew (optional but common)
if command -v brew &> /dev/null; then
    info "Homebrew detected"
fi

# =============================================================================
# 2. Install solc
# =============================================================================
echo ""
echo "Step 2: Installing Solidity compiler..."
echo "----------------------------------------"

if ! command -v solc &> /dev/null; then
    info "Installing solc-select..."
    pip3 install solc-select -q
    solc-select install 0.8.20 > /dev/null 2>&1
    solc-select use 0.8.20 > /dev/null 2>&1
fi

run_test "solc installed" "solc --version"

# =============================================================================
# 3. Create test environment
# =============================================================================
echo ""
echo "Step 3: Creating test environment..."
echo "-------------------------------------"

TEST_DIR=$(mktemp -d)
cd "$TEST_DIR"
info "Test directory: $TEST_DIR"

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# =============================================================================
# 4. Install True VKG
# =============================================================================
echo ""
echo "Step 4: Installing True VKG..."
echo "------------------------------"

# Install from PyPI (or local for testing)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -f "$SCRIPT_DIR/pyproject.toml" ]; then
    info "Installing from local source..."
    pip install -e "$SCRIPT_DIR" -q
else
    info "Installing from PyPI..."
    pip install true-vkg -q
fi

run_test "true-vkg command available" "which true-vkg"
run_test "true-vkg --help works" "true-vkg --help"

# =============================================================================
# 5. Create test contract
# =============================================================================
echo ""
echo "Step 5: Creating test contract..."
echo "----------------------------------"

mkdir -p contracts
cat > contracts/TestVault.sol << 'EOF'
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

run_test "Test contract created" "[ -f contracts/TestVault.sol ]"

# =============================================================================
# 6. Build knowledge graph
# =============================================================================
echo ""
echo "Step 6: Building knowledge graph..."
echo "------------------------------------"

run_test "build-kg succeeds" "true-vkg build-kg contracts/"
run_test "Graph file created" "[ -f .vrs/graphs/graph.json ]"

# =============================================================================
# 7. Query the graph
# =============================================================================
echo ""
echo "Step 7: Testing queries..."
echo "--------------------------"

run_test "NL query works" "true-vkg query 'public functions' --compact"
run_test "VQL query works" "true-vkg query 'FIND functions WHERE visibility = public' --compact"

# =============================================================================
# 8. Generate report
# =============================================================================
echo ""
echo "Step 8: Generating report..."
echo "----------------------------"

run_test "lens-report works" "true-vkg lens-report"
run_test "Schema export works" "true-vkg schema"

# =============================================================================
# 9. Cleanup
# =============================================================================
echo ""
echo "Step 9: Cleanup..."
echo "------------------"

deactivate
cd /
rm -rf "$TEST_DIR"
info "Test directory cleaned up"

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
