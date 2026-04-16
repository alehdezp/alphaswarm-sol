#!/bin/bash
# Pre-Release Checklist
# Validates that VKG is ready for release
#
# Usage: ./scripts/pre_release_check.sh

set -e

echo "========================================"
echo "True VKG Pre-Release Checklist"
echo "========================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

pass() { echo -e "${GREEN}✓ PASS${NC}: $1"; }
fail() { echo -e "${RED}✗ FAIL${NC}: $1"; }
warn() { echo -e "${YELLOW}⚠ WARN${NC}: $1"; }
info() { echo -e "${YELLOW}→${NC} $1"; }

CHECKS_PASSED=0
CHECKS_FAILED=0
CHECKS_WARNED=0

check_pass() {
    pass "$1"
    ((CHECKS_PASSED++))
}

check_fail() {
    fail "$1"
    ((CHECKS_FAILED++))
}

check_warn() {
    warn "$1"
    ((CHECKS_WARNED++))
}

# =============================================================================
# 1. Version Check
# =============================================================================
echo ""
echo "1. Version Configuration"
echo "------------------------"

VERSION=$(grep 'version = ' pyproject.toml | head -1 | cut -d'"' -f2)
info "Version in pyproject.toml: $VERSION"

if [[ "$VERSION" == "4.0.0" ]]; then
    check_pass "Version is 4.0.0"
else
    check_fail "Version should be 4.0.0, got: $VERSION"
fi

# =============================================================================
# 2. Tests
# =============================================================================
echo ""
echo "2. Test Suite"
echo "-------------"

info "Running tests..."
if uv run pytest tests/ -q --tb=no > /dev/null 2>&1; then
    TEST_COUNT=$(uv run pytest tests/ --collect-only -q 2>/dev/null | tail -1 | grep -oE '[0-9]+' | head -1)
    check_pass "All tests pass ($TEST_COUNT tests)"
else
    check_fail "Some tests failed"
fi

# =============================================================================
# 3. CLI Help
# =============================================================================
echo ""
echo "3. CLI Functionality"
echo "--------------------"

if uv run true-vkg --help > /dev/null 2>&1; then
    check_pass "CLI help works"
else
    check_fail "CLI help failed"
fi

# Check major commands
for cmd in build-kg query lens-report beads findings learn metrics novel; do
    if uv run true-vkg $cmd --help > /dev/null 2>&1; then
        check_pass "Command '$cmd' works"
    else
        check_fail "Command '$cmd' failed"
    fi
done

# =============================================================================
# 4. Documentation
# =============================================================================
echo ""
echo "4. Documentation"
echo "----------------"

DOCS_REQUIRED=(
    "README.md"
    "docs/getting-started.md"
    "docs/cli-reference.md"
    "docs/LIMITATIONS.md"
    "docs/PHILOSOPHY.md"
)

for doc in "${DOCS_REQUIRED[@]}"; do
    if [ -f "$doc" ]; then
        check_pass "Doc exists: $doc"
    else
        check_fail "Missing doc: $doc"
    fi
done

# =============================================================================
# 5. Docker
# =============================================================================
echo ""
echo "5. Docker Configuration"
echo "-----------------------"

if [ -f "Dockerfile" ]; then
    check_pass "Dockerfile exists"
else
    check_fail "Dockerfile missing"
fi

if [ -f "docker-compose.yml" ]; then
    check_pass "docker-compose.yml exists"
else
    check_fail "docker-compose.yml missing"
fi

# Validate Dockerfile syntax (if docker available)
if command -v docker &> /dev/null; then
    if docker build --check . > /dev/null 2>&1 || docker build -f Dockerfile --target runtime . > /dev/null 2>&1; then
        check_pass "Dockerfile syntax valid"
    else
        check_warn "Dockerfile not validated (build check failed)"
    fi
else
    check_warn "Docker not available for validation"
fi

# =============================================================================
# 6. Package Files
# =============================================================================
echo ""
echo "6. Package Files"
echo "----------------"

PACKAGE_FILES=(
    "pyproject.toml"
    "LICENSE"
    "src/true_vkg/__init__.py"
    "patterns/"
)

for file in "${PACKAGE_FILES[@]}"; do
    if [ -e "$file" ]; then
        check_pass "Package file exists: $file"
    else
        check_fail "Missing package file: $file"
    fi
done

# =============================================================================
# 7. Type Hints (spot check)
# =============================================================================
echo ""
echo "7. Code Quality"
echo "---------------"

# Check if mypy would pass on key files (if mypy available)
if command -v mypy &> /dev/null; then
    if mypy src/true_vkg/cli/main.py --ignore-missing-imports > /dev/null 2>&1; then
        check_pass "Type hints in CLI (mypy passes)"
    else
        check_warn "Type hint issues in CLI"
    fi
else
    check_warn "mypy not available for type checking"
fi

# =============================================================================
# 8. Dependencies
# =============================================================================
echo ""
echo "8. Dependencies"
echo "---------------"

# Check for pinned versions
if grep -q "slither-analyzer" pyproject.toml; then
    check_pass "Slither dependency declared"
else
    check_fail "Slither dependency missing"
fi

if grep -q "typer" pyproject.toml; then
    check_pass "Typer dependency declared"
else
    check_fail "Typer dependency missing"
fi

# =============================================================================
# 9. Security
# =============================================================================
echo ""
echo "9. Security Checks"
echo "------------------"

# Check for common security issues
if grep -rE "(api_key|password|secret)\s*=" src/ --include="*.py" | grep -v "environ\|getenv\|config\|example" > /dev/null 2>&1; then
    check_warn "Possible hardcoded credentials (review manually)"
else
    check_pass "No obvious hardcoded credentials"
fi

# =============================================================================
# Summary
# =============================================================================
echo ""
echo "========================================"
echo "Pre-Release Summary"
echo "========================================"
echo -e "Passed:  ${GREEN}${CHECKS_PASSED}${NC}"
echo -e "Failed:  ${RED}${CHECKS_FAILED}${NC}"
echo -e "Warned:  ${YELLOW}${CHECKS_WARNED}${NC}"
echo ""

if [ $CHECKS_FAILED -eq 0 ]; then
    echo -e "${GREEN}Ready for release!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Update CHANGELOG.md"
    echo "2. Tag release: git tag v4.0.0"
    echo "3. Push to PyPI: ./scripts/publish_pypi.sh"
    echo "4. Build Docker: docker build -t truevkg/true-vkg:4.0.0 ."
    echo "5. Create GitHub release"
    exit 0
else
    echo -e "${RED}Not ready for release. Fix the above issues first.${NC}"
    exit 1
fi
