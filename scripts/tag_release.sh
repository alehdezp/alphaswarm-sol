#!/bin/bash
# Tag repository for GA release
#
# Usage:
#   ./scripts/tag_release.sh [--push]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAIN_REPO="$(dirname "$SCRIPT_DIR")"

# Get version
VERSION=$(grep '^version' "$MAIN_REPO/pyproject.toml" | head -1 | cut -d'"' -f2)

echo "========================================"
echo " TAG GA RELEASE"
echo "========================================"
echo "Version: v$VERSION"
echo "========================================"

# Check if GA gate passed
if [ ! -f "$MAIN_REPO/.vrs/ga-gate/gate-report.json" ]; then
    echo "WARNING: GA gate report not found."
    echo "Run ./scripts/run_ga_gate.sh first for full validation."
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    GATE_PASSED=$(python3 -c "import json; print(json.load(open('$MAIN_REPO/.vrs/ga-gate/gate-report.json'))['required_passed'])")
    if [ "$GATE_PASSED" != "True" ]; then
        echo "WARNING: GA gate did not pass. Review gate-report.json for issues."
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
fi

# Check for uncommitted changes
if ! git diff --quiet; then
    echo "WARNING: Uncommitted changes detected!"
    git status --short
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if tag already exists
if git tag -l "v$VERSION" | grep -q "v$VERSION"; then
    echo "ERROR: Tag v$VERSION already exists!"
    exit 1
fi

# Build tag message
TAG_MSG="AlphaSwarm GA Release v$VERSION"

# Add metrics if available
if [ -f "$MAIN_REPO/.vrs/ga-metrics/aggregated-metrics.json" ]; then
    PRECISION=$(python3 -c "import json; print(f\"{json.load(open('$MAIN_REPO/.vrs/ga-metrics/aggregated-metrics.json')).get('overall_precision', 0):.1%}\")" 2>/dev/null || echo "N/A")
    RECALL=$(python3 -c "import json; print(f\"{json.load(open('$MAIN_REPO/.vrs/ga-metrics/aggregated-metrics.json')).get('overall_recall', 0):.1%}\")" 2>/dev/null || echo "N/A")
    F1=$(python3 -c "import json; print(f\"{json.load(open('$MAIN_REPO/.vrs/ga-metrics/aggregated-metrics.json')).get('overall_f1', 0):.1%}\")" 2>/dev/null || echo "N/A")
    TAG_MSG="$TAG_MSG

Validated metrics:
- Precision: $PRECISION
- Recall: $RECALL
- F1 Score: $F1"
fi

TAG_MSG="$TAG_MSG

See RELEASE_NOTES.md for details."

# Create tag
echo ""
echo "Creating tag v$VERSION..."
git tag -a "v$VERSION" -m "$TAG_MSG"

echo "Tag created: v$VERSION"

# Push if requested
if [ "$1" == "--push" ]; then
    echo ""
    echo "Pushing tag to origin..."
    git push origin "v$VERSION"
    echo "Tag pushed!"
else
    echo ""
    echo "To push the tag:"
    echo "  git push origin v$VERSION"
fi

echo ""
echo "========================================"
echo " TAG COMPLETE"
echo "========================================"
