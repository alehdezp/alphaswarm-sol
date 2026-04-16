#!/usr/bin/env bash
# Guard against unintentional full test suite runs.
# Blocks broad pytest invocations (exit 2) so Claude gets the error
# and must decide whether the full suite is truly needed.
#
# If Claude decides it IS needed, it can re-run with --full-suite flag to bypass.

set -euo pipefail

input=$(cat /dev/stdin)
command=$(echo "$input" | jq -r '.tool_input.command // ""')

# Normalize: strip leading whitespace and "uv run " prefix (macOS-compatible)
normalized=$(echo "$command" | sed -E 's/^[[:space:]]*(uv run[[:space:]]+)?//')

# Not a pytest command — allow
if ! echo "$normalized" | grep -qE '^pytest[[:space:]]|^pytest$'; then
  exit 0
fi

# Explicit bypass: --full-suite flag means Claude already decided it's needed
if echo "$normalized" | grep -qE -- '--full-suite'; then
  exit 0
fi

# Allow: specific .py file, :: function target
if echo "$normalized" | grep -qE '\.(py|sol)|::'; then
  exit 0
fi

# Allow: -k filter, -m marker
if echo "$normalized" | grep -qE '(^|[[:space:]])-k[[:space:]]|(^|[[:space:]])-m[[:space:]]'; then
  exit 0
fi

# Allow: subdirectory targeting (tests/something/ where something != just flags)
if echo "$normalized" | grep -qE 'tests/[a-zA-Z_][a-zA-Z0-9_]+'; then
  exit 0
fi

# Block: this looks like a full suite run
echo "HOOK BLOCKED: Full test suite detected (1700+ tests). Is this truly needed for your current change, or should you target specific test files? If the full suite is genuinely required, re-run with --full-suite flag." >&2
exit 2
