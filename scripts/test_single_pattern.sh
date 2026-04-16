#!/bin/bash
# Test Single Pattern Execution
#
# Purpose: Verify that specific patterns can be queried against the graph
#
# Expected behavior:
#   - pattern:reentrancy-classic query returns only that pattern
#   - No extraneous patterns in result
#
# Usage:
#   ./scripts/test_single_pattern.sh [--timeout 300] [--skip-cleanup]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKTREES_BASE="/tmp/vrs-worktrees"
FIXTURE="foundry-vault"
WORKTREE="wt-pattern-test"
TIMEOUT=300

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --skip-cleanup)
            SKIP_CLEANUP=true
            shift
            ;;
        --help)
            echo "Usage: $0 [--timeout 300] [--skip-cleanup]"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

WORKTREE_PATH="$WORKTREES_BASE/$WORKTREE"
SKIP_CLEANUP=${SKIP_CLEANUP:-false}

echo "========================================"
echo " SINGLE PATTERN EXECUTION TEST"
echo "========================================"
echo "Fixture:  $FIXTURE"
echo "Worktree: $WORKTREE"
echo "Pattern:  reentrancy-classic"
echo "Timeout:  ${TIMEOUT}s"
echo "========================================"

# Cleanup function
cleanup() {
    if [ "$SKIP_CLEANUP" = false ]; then
        "$SCRIPT_DIR/manage_worktrees.sh" cleanup "$WORKTREE" 2>/dev/null || true
    fi
}
trap cleanup EXIT

# Setup
echo ""
echo "[1/4] Creating worktree from fixture..."
"$SCRIPT_DIR/manage_worktrees.sh" create-from-fixture "$WORKTREE" "$FIXTURE"

# Build graph first
echo ""
echo "[2/4] Building knowledge graph..."
cd "$WORKTREE_PATH"
mkdir -p .vrs/graphs

if command -v alphaswarm &> /dev/null; then
    alphaswarm build-kg contracts/ --with-labels --output .vrs/graphs/ 2>&1 || {
        echo "WARNING: alphaswarm build-kg failed, trying with uv run..."
        uv run alphaswarm build-kg contracts/ --with-labels --output .vrs/graphs/ 2>&1 || {
            echo "ERROR: Failed to build knowledge graph"
            exit 1
        }
    }
else
    uv run alphaswarm build-kg contracts/ --with-labels --output .vrs/graphs/ 2>&1 || {
        echo "ERROR: Failed to build knowledge graph"
        exit 1
    }
fi

# Find the graph file
GRAPH_FILE=$(ls .vrs/graphs/*.toon 2>/dev/null | head -1 || ls .vrs/graphs/*.json 2>/dev/null | head -1 || echo "")
if [ -z "$GRAPH_FILE" ]; then
    echo "ERROR: No graph file found after build"
    exit 1
fi
echo "Graph file: $GRAPH_FILE"

# Query single pattern
echo ""
echo "[3/4] Querying single pattern: reentrancy-classic..."
mkdir -p .vrs

if command -v alphaswarm &> /dev/null; then
    alphaswarm query "pattern:reentrancy-classic" \
        --graph "$GRAPH_FILE" \
        --output .vrs/single-pattern-result.json 2>&1 || true
else
    uv run alphaswarm query "pattern:reentrancy-classic" \
        --graph "$GRAPH_FILE" \
        --output .vrs/single-pattern-result.json 2>&1 || true
fi

# Validate
echo ""
echo "[4/4] Validating single pattern result..."
cd "$SCRIPT_DIR/.."

if uv run python "$SCRIPT_DIR/validate_single_pattern.py" "$WORKTREE_PATH"; then
    echo ""
    echo "========================================"
    echo " SINGLE PATTERN TEST: PASSED"
    echo "========================================"
    exit 0
else
    echo ""
    echo "========================================"
    echo " SINGLE PATTERN TEST: FAILED"
    echo "========================================"
    echo "Worktree preserved for inspection: $WORKTREE_PATH"
    SKIP_CLEANUP=true
    exit 1
fi
