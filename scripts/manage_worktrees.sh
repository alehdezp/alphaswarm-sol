#!/bin/bash
# Worktree management for Phase 7.3 GA Validation
#
# Usage:
#   ./scripts/manage_worktrees.sh create <name>     # Create new worktree
#   ./scripts/manage_worktrees.sh cleanup <name>    # Remove worktree
#   ./scripts/manage_worktrees.sh list              # List all worktrees
#   ./scripts/manage_worktrees.sh reset <name>      # Reset worktree to clean state
#   ./scripts/manage_worktrees.sh setup <name>      # Setup worktree for testing

set -e

MAIN_REPO="/Volumes/ex_ssd/home/projects/python/vkg-solidity/true-vkg"
WORKTREES_BASE="/tmp/vrs-worktrees"
FIXTURES_DIR="$MAIN_REPO/tests/fixtures"

function create_worktree() {
    local name=$1
    local path="$WORKTREES_BASE/$name"

    echo "Creating worktree: $name at $path"

    # Create worktrees directory
    mkdir -p "$WORKTREES_BASE"

    # Check if already exists
    if [ -d "$path" ]; then
        echo "ERROR: Worktree already exists: $path"
        exit 1
    fi

    # Create worktree from current branch
    cd "$MAIN_REPO"
    git worktree add "$path" HEAD

    echo "Worktree created: $path"
}

function setup_worktree() {
    local name=$1
    local path="$WORKTREES_BASE/$name"

    echo "Setting up worktree: $name"

    if [ ! -d "$path" ]; then
        echo "ERROR: Worktree does not exist: $path"
        exit 1
    fi

    cd "$path"

    # Install alphaswarm tool (editable from this worktree)
    echo "Installing alphaswarm..."
    uv tool install -e . --force

    # Verify installation
    if command -v alphaswarm &> /dev/null; then
        echo "✓ alphaswarm installed: $(alphaswarm --version 2>/dev/null || echo 'version check failed')"
    else
        echo "WARNING: alphaswarm not in PATH, checking with uv run..."
        uv run alphaswarm --version
    fi

    # Copy skills to worktree's .claude directory
    echo "Copying skills..."
    mkdir -p .claude/skills
    cp -r "$MAIN_REPO/.claude/skills/"* .claude/skills/ 2>/dev/null || echo "No skills to copy"

    # Create contracts directory
    mkdir -p contracts

    # Create .vrs directory structure
    mkdir -p .vrs/{graphs,context,findings,reports,transcripts}

    echo "✓ Worktree setup complete: $path"
    echo ""
    echo "To use:"
    echo "  cd $path"
    echo "  claude"
    echo "  > /solidity-audit contracts/"
}

function cleanup_worktree() {
    local name=$1
    local path="$WORKTREES_BASE/$name"

    echo "Cleaning up worktree: $name"

    cd "$MAIN_REPO"

    if git worktree list | grep -q "$path"; then
        git worktree remove "$path" --force
        echo "✓ Worktree removed: $path"
    else
        echo "Worktree not found in git, removing directory..."
        rm -rf "$path"
        echo "✓ Directory removed: $path"
    fi
}

function list_worktrees() {
    echo "Git worktrees:"
    cd "$MAIN_REPO"
    git worktree list

    echo ""
    echo "Test worktrees in $WORKTREES_BASE:"
    if [ -d "$WORKTREES_BASE" ]; then
        ls -la "$WORKTREES_BASE" 2>/dev/null || echo "No worktrees found"
    else
        echo "No worktrees directory"
    fi
}

function reset_worktree() {
    local name=$1
    local path="$WORKTREES_BASE/$name"

    echo "Resetting worktree: $name"

    if [ ! -d "$path" ]; then
        echo "ERROR: Worktree does not exist: $path"
        exit 1
    fi

    cd "$path"

    # Discard all local changes
    git checkout .

    # Remove generated files
    rm -rf .vrs/

    # Recreate .vrs structure
    mkdir -p .vrs/{graphs,context,findings,reports,transcripts}

    echo "✓ Worktree reset: $path"
}

function create_and_setup() {
    local name=$1
    create_worktree "$name"
    setup_worktree "$name"
}

function create_from_fixture() {
    local name=$1
    local fixture=$2
    local path="$WORKTREES_BASE/$name"
    local fixture_path="$FIXTURES_DIR/$fixture"

    echo "Creating worktree from fixture: $fixture"

    if [ ! -d "$fixture_path" ]; then
        echo "ERROR: Fixture not found: $fixture_path"
        exit 1
    fi

    # Create base worktree
    create_worktree "$name"
    setup_worktree "$name"

    # Copy fixture files
    echo "Copying fixture files..."
    if [ -d "$fixture_path/src" ]; then
        mkdir -p "$path/contracts"
        cp -r "$fixture_path/src/"* "$path/contracts/"
    fi

    # Copy expected outputs
    if [ -d "$fixture_path/expected" ]; then
        mkdir -p "$path/expected"
        cp -r "$fixture_path/expected/"* "$path/expected/"
    fi

    # Copy ground truth
    if [ -f "$fixture_path/ground-truth.yaml" ]; then
        cp "$fixture_path/ground-truth.yaml" "$path/"
    fi

    # Copy foundry.toml if exists
    if [ -f "$fixture_path/foundry.toml" ]; then
        cp "$fixture_path/foundry.toml" "$path/"
    fi

    echo "Worktree created from fixture: $path"
    echo ""
    echo "Contents:"
    ls -la "$path/contracts/" 2>/dev/null || echo "No contracts"
    ls -la "$path/expected/" 2>/dev/null || echo "No expected files"
}

function validate_stage() {
    local name=$1
    local stage=$2
    local path="$WORKTREES_BASE/$name"

    echo "Validating stage: $stage"

    case "$stage" in
        graph)
            if ls "$path/.vrs/graphs/"*.toon 1>/dev/null 2>&1 || ls "$path/.vrs/graphs/"*.json 1>/dev/null 2>&1; then
                echo "  Graph file exists"
                return 0
            else
                echo "  No graph file found"
                return 1
            fi
            ;;

        context)
            if [ -f "$path/.vrs/context/protocol-pack.yaml" ]; then
                echo "  Context pack exists"
                return 0
            else
                echo "  No context pack found"
                return 1
            fi
            ;;

        patterns)
            if [ -f "$path/.vrs/findings/pattern-matches.json" ]; then
                echo "  Pattern matches file exists"
                return 0
            else
                echo "  No pattern matches found"
                return 1
            fi
            ;;

        agents)
            if [ -f "$path/.vrs/findings/agent-investigations.json" ]; then
                echo "  Agent investigations file exists"
                return 0
            else
                echo "  No agent investigations found"
                return 1
            fi
            ;;

        debate)
            if [ -f "$path/.vrs/findings/verdicts.json" ]; then
                echo "  Verdicts file exists"
                return 0
            else
                echo "  No verdicts found"
                return 1
            fi
            ;;

        report)
            if [ -f "$path/.vrs/reports/audit-report.md" ]; then
                echo "  Audit report exists"
                return 0
            else
                echo "  No audit report found"
                return 1
            fi
            ;;

        all)
            local all_passed=true
            for s in graph context patterns agents debate report; do
                if ! validate_stage "$name" "$s"; then
                    all_passed=false
                fi
            done
            if $all_passed; then
                echo "All stages validated"
                return 0
            else
                echo "Some stages failed"
                return 1
            fi
            ;;

        *)
            echo "Unknown stage: $stage"
            echo "Valid stages: graph, context, patterns, agents, debate, report, all"
            return 1
            ;;
    esac
}

function list_fixtures() {
    echo "Available fixtures:"
    if [ -d "$FIXTURES_DIR" ]; then
        for f in "$FIXTURES_DIR"/*/; do
            if [ -d "$f" ]; then
                fixture_name=$(basename "$f")
                # Skip non-fixture directories
                if [ -f "$f/ground-truth.yaml" ] || [ -d "$f/src" ]; then
                    echo "  - $fixture_name"
                    if [ -f "$f/ground-truth.yaml" ]; then
                        echo "      ground-truth: yes"
                    fi
                    if [ -d "$f/src" ]; then
                        echo "      contracts: $(ls "$f/src"/*.sol 2>/dev/null | wc -l | tr -d ' ') .sol files"
                    fi
                fi
            fi
        done
    else
        echo "No fixtures directory found at $FIXTURES_DIR"
    fi
}

# Main command dispatcher
case "$1" in
    create)
        if [ -z "$2" ]; then
            echo "Usage: $0 create <name>"
            exit 1
        fi
        create_worktree "$2"
        ;;

    setup)
        if [ -z "$2" ]; then
            echo "Usage: $0 setup <name>"
            exit 1
        fi
        setup_worktree "$2"
        ;;

    init)
        # Create and setup in one step
        if [ -z "$2" ]; then
            echo "Usage: $0 init <name>"
            exit 1
        fi
        create_and_setup "$2"
        ;;

    cleanup)
        if [ -z "$2" ]; then
            echo "Usage: $0 cleanup <name>"
            exit 1
        fi
        cleanup_worktree "$2"
        ;;

    list)
        list_worktrees
        ;;

    reset)
        if [ -z "$2" ]; then
            echo "Usage: $0 reset <name>"
            exit 1
        fi
        reset_worktree "$2"
        ;;

    cleanup-all)
        echo "Cleaning up ALL worktrees..."
        cd "$MAIN_REPO"
        for wt in $(ls "$WORKTREES_BASE" 2>/dev/null); do
            cleanup_worktree "$wt"
        done
        echo "All worktrees cleaned up"
        ;;

    create-from-fixture)
        if [ -z "$2" ] || [ -z "$3" ]; then
            echo "Usage: $0 create-from-fixture <name> <fixture>"
            echo ""
            list_fixtures
            exit 1
        fi
        create_from_fixture "$2" "$3"
        ;;

    validate)
        if [ -z "$2" ] || [ -z "$3" ]; then
            echo "Usage: $0 validate <name> <stage>"
            echo ""
            echo "Stages: graph, context, patterns, agents, debate, report, all"
            exit 1
        fi
        validate_stage "$2" "$3"
        ;;

    list-fixtures)
        list_fixtures
        ;;

    *)
        echo "Usage: $0 {create|setup|init|cleanup|list|reset|cleanup-all|create-from-fixture|validate|list-fixtures} [args]"
        echo ""
        echo "Commands:"
        echo "  create <name>                      Create a new git worktree"
        echo "  setup <name>                       Setup worktree for testing (install alphaswarm, copy skills)"
        echo "  init <name>                        Create and setup in one step"
        echo "  cleanup <name>                     Remove a worktree"
        echo "  list                               List all worktrees"
        echo "  reset <name>                       Reset worktree to clean state"
        echo "  cleanup-all                        Remove all test worktrees"
        echo "  create-from-fixture <name> <fix>   Create worktree from test fixture"
        echo "  validate <name> <stage>            Validate a specific stage output"
        echo "  list-fixtures                      List available test fixtures"
        exit 1
        ;;
esac
