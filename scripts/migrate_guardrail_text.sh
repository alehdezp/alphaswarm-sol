#!/bin/bash
# scripts/migrate_guardrail_text.sh
# Migration script for Plan 07.3.1.9-08
# Updates "Worktree isolation" boilerplate to "Workspace isolation" in phase plans

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Change to repo root
cd "$(dirname "$0")/.."

# Counters
UPDATED=0
SKIPPED=0
ERRORS=0

# Old and new text patterns
OLD_PATTERN="Worktree isolation: run any commands or experiments that mutate state in a fresh git worktree; do not use the main worktree and do not reuse worktrees for reruns"
NEW_PATTERN="Workspace isolation: run any commands or experiments that mutate state in a fresh jj workspace; do not use the main workspace and do not reuse workspaces for reruns"

echo "=== Phase Plan Guardrail Migration ==="
echo "Migrating: 'Worktree isolation' -> 'Workspace isolation'"
echo ""

# Find all PLAN.md files with the old pattern
FILES=$(grep -rl "Worktree isolation: run any commands" .planning/phases/ --include="*-PLAN.md" 2>/dev/null || true)

if [ -z "$FILES" ]; then
    echo -e "${YELLOW}No files found with 'Worktree isolation' pattern.${NC}"
    exit 0
fi

echo "Found files to update:"
echo "$FILES" | wc -l | xargs echo "  Total:"
echo ""

# Process each file
for file in $FILES; do
    # Skip if file doesn't exist
    if [ ! -f "$file" ]; then
        echo -e "${RED}SKIP (not found): $file${NC}"
        ((SKIPPED++))
        continue
    fi

    # Skip if already has the new pattern (avoid double migration)
    if grep -q "Workspace isolation: run any commands" "$file"; then
        echo -e "${YELLOW}SKIP (already migrated): $file${NC}"
        ((SKIPPED++))
        continue
    fi

    # Perform the replacement using sed
    # Using | as delimiter since the text contains /
    if sed -i.bak "s|Worktree isolation: run any commands or experiments that mutate state in a fresh git worktree; do not use the main worktree and do not reuse worktrees for reruns|Workspace isolation: run any commands or experiments that mutate state in a fresh jj workspace; do not use the main workspace and do not reuse workspaces for reruns|g" "$file" 2>/dev/null; then
        # Verify the change was made
        if grep -q "Workspace isolation: run any commands" "$file"; then
            echo -e "${GREEN}UPDATED: $file${NC}"
            ((UPDATED++))
            # Remove backup file
            rm -f "$file.bak"
        else
            echo -e "${RED}ERROR (change not verified): $file${NC}"
            # Restore from backup
            mv "$file.bak" "$file"
            ((ERRORS++))
        fi
    else
        echo -e "${RED}ERROR (sed failed): $file${NC}"
        ((ERRORS++))
    fi
done

echo ""
echo "=== Migration Summary ==="
echo -e "  Updated: ${GREEN}$UPDATED${NC}"
echo -e "  Skipped: ${YELLOW}$SKIPPED${NC}"
echo -e "  Errors:  ${RED}$ERRORS${NC}"
echo ""

# Verification
echo "=== Verification ==="
REMAINING=$(grep -rl "Worktree isolation: run any commands" .planning/phases/ --include="*-PLAN.md" 2>/dev/null | wc -l || echo "0")
MIGRATED=$(grep -rl "Workspace isolation: run any commands" .planning/phases/ --include="*-PLAN.md" 2>/dev/null | wc -l || echo "0")

echo "  Files with 'Worktree isolation' (remaining): $REMAINING"
echo "  Files with 'Workspace isolation' (migrated): $MIGRATED"

if [ "$REMAINING" -gt 0 ]; then
    echo ""
    echo -e "${YELLOW}Warning: Some files still have old pattern:${NC}"
    grep -rl "Worktree isolation: run any commands" .planning/phases/ --include="*-PLAN.md" 2>/dev/null || true
fi

exit 0
