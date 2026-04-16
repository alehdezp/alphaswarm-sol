#!/bin/bash
# AlphaSwarm.sol Smoke Test Script
# Validates fresh installation works correctly
#
# Usage: ./scripts/smoke_test.sh
# Exit codes: 0 = all tests passed, 1 = one or more tests failed

set -e

EXPECTED_VERSION="0.5.0"
PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

pass() {
    echo -e "${GREEN}PASS${NC}: $1"
    PASS_COUNT=$((PASS_COUNT + 1))
}

fail() {
    echo -e "${RED}FAIL${NC}: $1"
    FAIL_COUNT=$((FAIL_COUNT + 1))
}

warn() {
    echo -e "${YELLOW}WARN${NC}: $1"
    WARN_COUNT=$((WARN_COUNT + 1))
}

echo "============================================"
echo "AlphaSwarm.sol Smoke Test Suite"
echo "Expected Version: $EXPECTED_VERSION"
echo "============================================"
echo ""

# ============================================
# Test 1: Version Check
# ============================================
echo -n "Test 1: Version check... "
VERSION_OUTPUT=$(uv run alphaswarm --version 2>&1 || true)
if [[ "$VERSION_OUTPUT" == *"$EXPECTED_VERSION"* ]]; then
    pass "alphaswarm --version returns $EXPECTED_VERSION"
else
    fail "Expected $EXPECTED_VERSION, got: $VERSION_OUTPUT"
fi

# ============================================
# Test 2: Short Alias
# ============================================
echo -n "Test 2: Short alias (aswarm)... "
if uv run aswarm --version >/dev/null 2>&1; then
    pass "aswarm alias works"
else
    fail "aswarm alias not available"
fi

# ============================================
# Test 3: Help Command
# ============================================
echo -n "Test 3: Help command... "
if uv run alphaswarm --help | grep -q "build-kg"; then
    pass "Help shows build-kg command"
else
    fail "Help missing expected commands"
fi

# ============================================
# Test 4: Build Knowledge Graph
# ============================================
echo -n "Test 4: Build knowledge graph... "
TEMP_DIR=$(mktemp -d)
cat > "$TEMP_DIR/Test.sol" << 'EOF'
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Test {
    mapping(address => uint256) public balances;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient");
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");
        balances[msg.sender] -= amount;
    }
}
EOF

BUILD_OUTPUT=$(uv run alphaswarm build-kg "$TEMP_DIR/Test.sol" --out "$TEMP_DIR/vkg_out" 2>&1 || true)
GRAPH_FILE="$TEMP_DIR/vkg_out/graph.json"
if [[ "$BUILD_OUTPUT" == *"Built"* ]] || [[ "$BUILD_OUTPUT" == *"graph"* ]] || [ -f "$GRAPH_FILE" ]; then
    pass "build-kg succeeded"
else
    fail "build-kg failed: $BUILD_OUTPUT"
fi

# ============================================
# Test 5: Query Graph
# ============================================
echo -n "Test 5: Query graph... "
if [ -f "$GRAPH_FILE" ]; then
    QUERY_OUTPUT=$(uv run alphaswarm query "FIND functions" --graph "$GRAPH_FILE" 2>&1 || true)
    if [[ "$QUERY_OUTPUT" == *"function"* ]] || [[ "$QUERY_OUTPUT" == *"withdraw"* ]] || [[ "$QUERY_OUTPUT" == *"deposit"* ]] || [[ "$QUERY_OUTPUT" == *"found"* ]]; then
        pass "Query returned results"
    else
        warn "Query ran but returned no results (may be expected)"
    fi
else
    fail "Graph file not created"
fi

# ============================================
# Test 6: Python Import
# ============================================
echo -n "Test 6: Python import... "
IMPORT_OUTPUT=$(uv run python -c "from alphaswarm_sol import __version__; print(__version__)" 2>&1 || true)
if [[ "$IMPORT_OUTPUT" == *"$EXPECTED_VERSION"* ]]; then
    pass "Python import works"
else
    fail "Python import failed: $IMPORT_OUTPUT"
fi

# ============================================
# Test 7: Agent Discovery File
# ============================================
echo -n "Test 7: Agent discovery file... "
if [ -f ".vrs/AGENTS.md" ]; then
    if grep -q "vrs-" ".vrs/AGENTS.md"; then
        pass ".vrs/AGENTS.md exists with vrs-* agents"
    else
        fail ".vrs/AGENTS.md missing vrs-* agents"
    fi
else
    fail ".vrs/AGENTS.md not found"
fi

# ============================================
# Test 8: Docker Image (if available)
# ============================================
echo -n "Test 8: Docker image... "
if command -v docker &> /dev/null; then
    if docker images alphaswarm-sol:test --format "{{.Repository}}" 2>/dev/null | grep -q "alphaswarm"; then
        DOCKER_OUTPUT=$(docker run --rm alphaswarm-sol:test --version 2>&1 || true)
        if [[ "$DOCKER_OUTPUT" == *"$EXPECTED_VERSION"* ]]; then
            pass "Docker image works"
        else
            fail "Docker image version mismatch: $DOCKER_OUTPUT"
        fi
    else
        warn "Docker image not found locally (skipping)"
    fi
else
    warn "Docker not installed (skipping)"
fi

# ============================================
# Cleanup
# ============================================
rm -rf "$TEMP_DIR"

# ============================================
# Summary
# ============================================
echo ""
echo "============================================"
echo "Smoke Test Summary"
echo "============================================"
echo -e "Passed: ${GREEN}$PASS_COUNT${NC}"
echo -e "Failed: ${RED}$FAIL_COUNT${NC}"
echo -e "Warnings: ${YELLOW}$WARN_COUNT${NC}"
echo ""

if [ $FAIL_COUNT -gt 0 ]; then
    echo -e "${RED}SMOKE TEST FAILED${NC}"
    exit 1
else
    echo -e "${GREEN}ALL SMOKE TESTS PASSED${NC}"
    exit 0
fi
