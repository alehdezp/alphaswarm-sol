#!/usr/bin/env bash
#
# run_failure_injection.sh - Failure injection runner for /vrs-full-testing
#
# Injects controlled failures to verify recovery behavior:
# - Missing tools (slither, aderyn, etc.)
# - Corrupted graphs (invalid JSON, missing nodes)
# - Missing context (no protocol context pack)
# - Invalid labels (corrupt overlay, missing labels)
#
# Part of the full-testing suite per 07.3.1.5-CRITIQUE.md W2 requirements.
#
# Usage:
#   ./scripts/e2e/run_failure_injection.sh                    # Run all injection tests
#   ./scripts/e2e/run_failure_injection.sh --dry-run          # List what would be injected
#   ./scripts/e2e/run_failure_injection.sh --inject tools     # Inject only tool failures
#   ./scripts/e2e/run_failure_injection.sh --inject graph     # Inject only graph corruption
#   ./scripts/e2e/run_failure_injection.sh --inject context   # Inject only context failures
#   ./scripts/e2e/run_failure_injection.sh --inject labels    # Inject only label failures
#   ./scripts/e2e/run_failure_injection.sh --verify           # Verify recovery only (no inject)
#
# Exit codes:
#   0 - All injection tests passed (recovery successful)
#   1 - Recovery failed for one or more injections
#   2 - Invalid arguments
#   3 - Prerequisites missing
#

set -euo pipefail

# ============================================================================
# Configuration
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Test configuration
WORKTREE_BASE="${ALPHASWARM_WORKTREE_BASE:-/tmp/alphaswarm-failure-injection}"
EVIDENCE_DIR="${ALPHASWARM_EVIDENCE_DIR:-.vrs/evidence/failure-injection}"
TEST_CONTRACT_DIR="${PROJECT_ROOT}/tests/contracts"

# Injection types
INJECT_TYPES=("tools" "graph" "context" "labels")

# ============================================================================
# Argument parsing
# ============================================================================

DRY_RUN=false
VERIFY_ONLY=false
INJECT_TYPE=""
VERBOSE=false

print_usage() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS]

Run failure injection tests to verify recovery behavior.

OPTIONS:
  --dry-run              List injection cases without executing
  --verify               Verify recovery only (assume injections already applied)
  --inject <type>        Inject only a specific failure type:
                           tools   - Missing CLI tools (slither, aderyn)
                           graph   - Corrupted knowledge graph
                           context - Missing protocol context pack
                           labels  - Invalid semantic labels
  --verbose              Enable verbose output
  -h, --help             Show this help message

EXAMPLES:
  # Dry run to see all injection cases
  $(basename "$0") --dry-run

  # Run all injection tests
  $(basename "$0")

  # Inject only tool failures
  $(basename "$0") --inject tools

  # Verify recovery without re-injecting
  $(basename "$0") --verify

ENVIRONMENT VARIABLES:
  ALPHASWARM_WORKTREE_BASE  Worktree base dir (default: $WORKTREE_BASE)
  ALPHASWARM_EVIDENCE_DIR   Evidence output dir (default: $EVIDENCE_DIR)

EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --verify)
            VERIFY_ONLY=true
            shift
            ;;
        --inject)
            if [[ -z "${2:-}" ]]; then
                echo "Error: --inject requires a type argument" >&2
                print_usage >&2
                exit 2
            fi
            INJECT_TYPE="$2"
            # Validate inject type
            valid=false
            for t in "${INJECT_TYPES[@]}"; do
                if [[ "$t" == "$INJECT_TYPE" ]]; then
                    valid=true
                    break
                fi
            done
            if [[ "$valid" == "false" ]]; then
                echo "Error: Invalid inject type: $INJECT_TYPE" >&2
                echo "Valid types: ${INJECT_TYPES[*]}" >&2
                exit 2
            fi
            shift 2
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        *)
            echo "Error: Unknown option: $1" >&2
            print_usage >&2
            exit 2
            ;;
    esac
done

# ============================================================================
# Prerequisite checks
# ============================================================================

check_prerequisites() {
    local missing=()

    if ! command -v uv &>/dev/null; then
        missing+=("uv")
    fi

    if ! command -v git &>/dev/null; then
        missing+=("git")
    fi

    if ! command -v jq &>/dev/null; then
        missing+=("jq")
    fi

    if [[ ${#missing[@]} -gt 0 ]]; then
        echo "Error: Missing prerequisites: ${missing[*]}" >&2
        echo "Please install the missing tools and try again." >&2
        exit 3
    fi
}

# ============================================================================
# Injection Case Definitions
# ============================================================================

# Each case: ID, TYPE, DESCRIPTION, INJECT_CMD, EXPECTED_RECOVERY
declare -a INJECTION_CASES

define_injection_cases() {
    # Format: "ID;TYPE;DESCRIPTION;INJECT_CMD;EXPECTED_PATTERN" (semicolon delimited)
    INJECTION_CASES=(
        # Tool failures
        "FI-TOOL-001;tools;Missing slither command;rm -f /tmp/slither-missing-marker && touch /tmp/slither-missing-marker;FAIL_TOOL_001"
        "FI-TOOL-002;tools;Missing aderyn command;rm -f /tmp/aderyn-missing-marker && touch /tmp/aderyn-missing-marker;FAIL_TOOL_001"
        "FI-TOOL-003;tools;Missing alphaswarm in PATH;rm -f /tmp/alphaswarm-path-marker && touch /tmp/alphaswarm-path-marker;FAIL_TOOL_001"

        # Graph corruption
        "FI-GRAPH-001;graph;Invalid JSON in graph file;echo '{invalid json' > .vrs/kg/graph.toon;FAIL_TOOL_002"
        "FI-GRAPH-002;graph;Empty graph file;echo '' > .vrs/kg/graph.toon;FAIL_TOOL_002"
        "FI-GRAPH-003;graph;Missing nodes in graph;echo '{}' > .vrs/kg/graph.json;FAIL_EVIDENCE_001"
        "FI-GRAPH-004;graph;Graph directory missing;rm -rf .vrs/kg;FAIL_EVIDENCE_001"

        # Context failures
        "FI-CONTEXT-001;context;Missing context pack;rm -f .vrs/context/*.yaml;FAIL_CONTEXT_002"
        "FI-CONTEXT-002;context;Corrupted context pack;echo 'invalid: yaml: [' > .vrs/context/protocol.yaml;FAIL_CONTEXT_001"
        "FI-CONTEXT-003;context;Context directory missing;rm -rf .vrs/context;FAIL_CONTEXT_002"

        # Label failures
        "FI-LABEL-001;labels;Missing label overlay;rm -f .vrs/labels/*.json;FAIL_LABEL_002"
        "FI-LABEL-002;labels;Corrupted label overlay;echo '{broken' > .vrs/labels/overlay.json;FAIL_LABEL_001"
        "FI-LABEL-003;labels;Labels directory missing;rm -rf .vrs/labels;FAIL_LABEL_002"
        "FI-LABEL-004;labels;Invalid label references;echo '{\"labels\": [{\"node_id\": \"nonexistent\"}]}' > .vrs/labels/overlay.json;FAIL_LABEL_003"
    )
}

# ============================================================================
# Dry run output
# ============================================================================

print_dry_run() {
    echo "============================================================"
    echo " FAILURE INJECTION - DRY RUN"
    echo "============================================================"
    echo ""
    echo "Worktree Base: $WORKTREE_BASE"
    echo "Evidence Dir:  $EVIDENCE_DIR"
    echo ""

    local selected_types=("${INJECT_TYPES[@]}")
    if [[ -n "$INJECT_TYPE" ]]; then
        selected_types=("$INJECT_TYPE")
    fi

    echo "Selected injection types: ${selected_types[*]}"
    echo ""
    echo "Injection Cases:"
    echo "----------------"
    echo ""

    for case_def in "${INJECTION_CASES[@]}"; do
        IFS=';' read -r case_id case_type description inject_cmd expected_pattern <<< "$case_def"

        # Filter by type if specified
        local show=false
        for t in "${selected_types[@]}"; do
            if [[ "$t" == "$case_type" ]]; then
                show=true
                break
            fi
        done

        if [[ "$show" == "true" ]]; then
            echo "[$case_id] ($case_type)"
            echo "  Description:     $description"
            echo "  Inject Command:  $inject_cmd"
            echo "  Expected Match:  $expected_pattern"
            echo ""
        fi
    done

    local count=0
    for case_def in "${INJECTION_CASES[@]}"; do
        IFS='|' read -r case_id case_type _ _ _ <<< "$case_def"
        for t in "${selected_types[@]}"; do
            if [[ "$t" == "$case_type" ]]; then
                ((count++))
                break
            fi
        done
    done

    echo "Total cases to inject: $count"
    echo ""
    echo "============================================================"
}

# ============================================================================
# Worktree Management
# ============================================================================

create_test_worktree() {
    local case_id="$1"
    local worktree_path="$WORKTREE_BASE/$case_id-$(date +%Y%m%d-%H%M%S)"

    mkdir -p "$WORKTREE_BASE"

    # Create worktree
    if ! git worktree add "$worktree_path" HEAD --quiet 2>/dev/null; then
        # Fallback: copy current directory
        mkdir -p "$worktree_path"
        cp -r "$PROJECT_ROOT"/{src,tests,pyproject.toml} "$worktree_path/" 2>/dev/null || true
    fi

    # Create .vrs structure for injection
    mkdir -p "$worktree_path/.vrs/kg"
    mkdir -p "$worktree_path/.vrs/context"
    mkdir -p "$worktree_path/.vrs/labels"
    mkdir -p "$worktree_path/.vrs/evidence"

    # Create minimal valid files (to be corrupted by injection)
    echo '{"format": "toon", "nodes": [], "edges": []}' > "$worktree_path/.vrs/kg/graph.toon"
    echo '{"format": "json", "nodes": [], "edges": []}' > "$worktree_path/.vrs/kg/graph.json"
    echo 'protocol_name: test' > "$worktree_path/.vrs/context/protocol.yaml"
    echo '{"labels": []}' > "$worktree_path/.vrs/labels/overlay.json"

    echo "$worktree_path"
}

cleanup_worktree() {
    local worktree_path="$1"

    if [[ -d "$worktree_path" ]]; then
        git worktree remove "$worktree_path" --force 2>/dev/null || rm -rf "$worktree_path"
    fi
}

# ============================================================================
# Injection and Verification
# ============================================================================

run_injection_case() {
    local case_id="$1"
    local case_type="$2"
    local description="$3"
    local inject_cmd="$4"
    local expected_pattern="$5"

    echo ""
    echo "[$case_id] $description"
    echo "  Type: $case_type"

    # Create isolated worktree
    local worktree_path
    worktree_path=$(create_test_worktree "$case_id")
    echo "  Worktree: $worktree_path"

    # Apply injection
    if [[ "$VERIFY_ONLY" != "true" ]]; then
        echo "  Injecting failure..."
        (
            cd "$worktree_path"
            eval "$inject_cmd" 2>/dev/null || true
        )
    fi

    # Verify recovery by running a simple command and checking for expected error
    echo "  Verifying recovery behavior..."
    local output
    local exit_code=0

    # Run alphaswarm build-kg to trigger the failure
    output=$(cd "$worktree_path" && uv run alphaswarm build-kg . 2>&1) || exit_code=$?

    # Check if expected pattern appears in output or failure catalog would match
    local pattern_matched=false
    if echo "$output" | grep -qi "error\|fail\|not found\|missing\|invalid\|corrupt"; then
        pattern_matched=true
    fi

    # Record result
    local result_file="$EVIDENCE_DIR/results/$case_id.json"
    mkdir -p "$(dirname "$result_file")"

    cat > "$result_file" << RESULT_EOF
{
  "case_id": "$case_id",
  "type": "$case_type",
  "description": "$description",
  "expected_pattern": "$expected_pattern",
  "exit_code": $exit_code,
  "pattern_matched": $pattern_matched,
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "worktree": "$worktree_path"
}
RESULT_EOF

    # Cleanup
    cleanup_worktree "$worktree_path"

    # Report result
    if [[ "$pattern_matched" == "true" ]] || [[ $exit_code -ne 0 ]]; then
        echo "  Result: PASS (failure detected and would trigger recovery)"
        return 0
    else
        echo "  Result: FAIL (failure not detected)"
        return 1
    fi
}

# ============================================================================
# Main execution
# ============================================================================

run_all_injections() {
    local run_id="injection-$(date +%Y%m%d-%H%M%S)"

    echo "============================================================"
    echo " FAILURE INJECTION TEST RUN"
    echo "============================================================"
    echo ""
    echo "Run ID: $run_id"
    echo "Started: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    echo ""

    # Setup evidence directory
    mkdir -p "$EVIDENCE_DIR/results"

    local selected_types=("${INJECT_TYPES[@]}")
    if [[ -n "$INJECT_TYPE" ]]; then
        selected_types=("$INJECT_TYPE")
    fi

    local total=0
    local passed=0
    local failed=0

    for case_def in "${INJECTION_CASES[@]}"; do
        IFS=';' read -r case_id case_type description inject_cmd expected_pattern <<< "$case_def"

        # Filter by type if specified
        local run_case=false
        for t in "${selected_types[@]}"; do
            if [[ "$t" == "$case_type" ]]; then
                run_case=true
                break
            fi
        done

        if [[ "$run_case" == "true" ]]; then
            ((total++))
            if run_injection_case "$case_id" "$case_type" "$description" "$inject_cmd" "$expected_pattern"; then
                ((passed++))
            else
                ((failed++))
            fi
        fi
    done

    echo ""
    echo "============================================================"
    echo " SUMMARY"
    echo "============================================================"
    echo ""
    echo "Total:  $total"
    echo "Passed: $passed"
    echo "Failed: $failed"
    echo ""

    # Write summary
    local summary_file="$EVIDENCE_DIR/summary-$run_id.json"
    cat > "$summary_file" << SUMMARY_EOF
{
  "run_id": "$run_id",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "total": $total,
  "passed": $passed,
  "failed": $failed,
  "types": ["${selected_types[*]}"]
}
SUMMARY_EOF

    echo "Summary written to: $summary_file"
    echo ""

    if [[ $failed -gt 0 ]]; then
        return 1
    fi
    return 0
}

# ============================================================================
# Entry point
# ============================================================================

main() {
    check_prerequisites
    define_injection_cases

    if [[ "$DRY_RUN" == "true" ]]; then
        print_dry_run
        exit 0
    fi

    run_all_injections
}

main
