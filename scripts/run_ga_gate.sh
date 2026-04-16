#!/bin/bash
# Run complete GA release gate validation
#
# Usage:
#   ./scripts/run_ga_gate.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAIN_REPO="$(dirname "$SCRIPT_DIR")"

echo "========================================"
echo " ALPHASWARM GA RELEASE GATE"
echo "========================================"
echo "Repository: $MAIN_REPO"
echo "Date:       $(date)"
echo "========================================"

# Step 1: Check prerequisites
echo ""
echo "[Step 1/6] Checking prerequisites..."

# Check metrics exist
if [ ! -f "$MAIN_REPO/.vrs/ga-metrics/aggregated-metrics.json" ]; then
    echo "WARNING: Metrics not found at .vrs/ga-metrics/aggregated-metrics.json"
    echo "Run plan 07.3-13-v6 to generate metrics."
    echo "Continuing without metrics..."
fi

# Check baseline exists
if [ ! -f "$MAIN_REPO/.vrs/baselines/ga-baseline.json" ]; then
    echo "WARNING: Baseline not found at .vrs/baselines/ga-baseline.json"
    echo "Run plan 07.3-14-v6 to capture baseline."
    echo "Continuing without baseline..."
fi

echo "  Prerequisites check complete"

# Step 2: Run GA gate checks
echo ""
echo "[Step 2/6] Running GA gate checks..."
mkdir -p "$MAIN_REPO/.vrs/ga-gate"

cd "$MAIN_REPO"
uv run python "$SCRIPT_DIR/ga_gate_check.py" \
    --output "$MAIN_REPO/.vrs/ga-gate/gate-report.json" || true

# Check if gate passed
if [ -f "$MAIN_REPO/.vrs/ga-gate/gate-report.json" ]; then
    GATE_PASSED=$(python3 -c "import json; print(json.load(open('$MAIN_REPO/.vrs/ga-gate/gate-report.json'))['required_passed'])")
else
    GATE_PASSED="False"
fi

# Step 3: Generate release notes
echo ""
echo "[Step 3/6] Generating release notes..."
uv run python "$SCRIPT_DIR/generate_release_notes.py" \
    --output "$MAIN_REPO/RELEASE_NOTES.md"

# Step 4: Update CHANGELOG
echo ""
echo "[Step 4/6] Checking CHANGELOG..."
if [ ! -f "$MAIN_REPO/CHANGELOG.md" ]; then
    echo "WARNING: CHANGELOG.md not found. Creating placeholder."
    cat > "$MAIN_REPO/CHANGELOG.md" << 'EOF'
# Changelog

All notable changes to AlphaSwarm will be documented in this file.

## [Unreleased]

## [0.5.0] - GA Release

See RELEASE_NOTES.md for details.

### Added
- Complete BSKG with 50+ security properties
- 556+ vulnerability patterns
- Multi-agent debate protocol
- External tool integration (7 tools)
- Protocol context pack generation
- Evidence-linked findings

### Changed
- N/A (first GA release)

### Fixed
- N/A (first GA release)
EOF
fi

# Step 5: Verify version
echo ""
echo "[Step 5/6] Verifying version..."
VERSION=$(grep '^version' "$MAIN_REPO/pyproject.toml" | head -1 | cut -d'"' -f2)
echo "  Current version: $VERSION"

# Check if version looks like GA
if [[ "$VERSION" == *"alpha"* ]] || [[ "$VERSION" == *"beta"* ]] || [[ "$VERSION" == *"dev"* ]]; then
    echo "WARNING: Version contains pre-release suffix!"
    echo "Update pyproject.toml version before release."
fi

# Step 6: Summary
echo ""
echo "[Step 6/6] Final summary..."
echo ""
echo "========================================"
if [ "$GATE_PASSED" == "True" ]; then
    echo " GA GATE: PASSED"
else
    echo " GA GATE: NOT YET PASSED"
    echo ""
    echo " Some checks may have failed. Review gate-report.json for details."
fi
echo "========================================"
echo ""
echo "Generated artifacts:"
echo "  - Gate report:    .vrs/ga-gate/gate-report.json"
echo "  - Release notes:  RELEASE_NOTES.md"
if [ -f "$MAIN_REPO/.vrs/ga-metrics/aggregated-metrics.json" ]; then
    echo "  - Metrics:        .vrs/ga-metrics/aggregated-metrics.json"
fi
if [ -f "$MAIN_REPO/.vrs/baselines/ga-baseline.json" ]; then
    echo "  - Baseline:       .vrs/baselines/ga-baseline.json"
fi
echo ""
echo "Next steps:"
echo "  1. Review RELEASE_NOTES.md"
echo "  2. Update version in pyproject.toml if needed"
echo "  3. Commit all changes"
echo "  4. Create git tag: git tag -a v$VERSION -m 'GA Release'"
echo "  5. Push: git push origin v$VERSION"
echo ""
echo "To tag for release:"
echo "  ./scripts/tag_release.sh"
echo "  ./scripts/tag_release.sh --push  # To push tag"
