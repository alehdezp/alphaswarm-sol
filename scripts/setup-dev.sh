#!/usr/bin/env bash
# Recreates symlinks from .claude/ to shipping/ for development.
# Run from project root after cloning or if symlinks break.
set -euo pipefail

SHIPPING_SKILLS="src/alphaswarm_sol/shipping/skills"
SHIPPING_AGENTS="src/alphaswarm_sol/shipping/agents"

echo "=== AlphaSwarm.sol Dev Setup ==="
echo "Creating symlinks from .claude/ to shipping/"

# Skill symlinks: .claude/skills/<name>/SKILL.md -> shipping/skills/<file>.md
declare -A SKILL_MAP=(
  ["vrs-audit"]="audit.md"
  ["vrs-verify"]="verify.md"
  ["vrs-investigate"]="investigate.md"
  ["vrs-debate"]="debate.md"
  ["vrs-slither"]="tool-slither.md"
  ["vrs-aderyn"]="tool-aderyn.md"
  ["vrs-tool-slither"]="tool-slither.md"
  ["vrs-tool-aderyn"]="tool-aderyn.md"
  ["vrs-bead-create"]="bead-create.md"
  ["vrs-bead-update"]="bead-update.md"
  ["vrs-bead-list"]="bead-list.md"
  ["vrs-orch-spawn"]="orch-spawn.md"
  ["vrs-orch-resume"]="orch-resume.md"
  ["vrs-health-check"]="health-check.md"
  ["vrs-mythril"]="tool-mythril.md"
  ["vrs-tool-mythril"]="tool-mythril.md"
  ["vrs-tool-coordinator"]="tool-coordinator.md"
)

for skill_dir in "${!SKILL_MAP[@]}"; do
  target_file="${SKILL_MAP[$skill_dir]}"
  skill_path=".claude/skills/${skill_dir}/SKILL.md"
  shipping_path="../../../${SHIPPING_SKILLS}/${target_file}"

  if [ ! -f "${SHIPPING_SKILLS}/${target_file}" ]; then
    echo "  SKIP ${skill_dir} (${target_file} not in shipping)"
    continue
  fi

  mkdir -p ".claude/skills/${skill_dir}"
  rm -f "${skill_path}"
  ln -s "${shipping_path}" "${skill_path}"
  echo "  OK ${skill_path} -> ${shipping_path}"
done

# Agent symlinks: .claude/agents/<name>.md -> shipping/agents/<name>.md
PRODUCT_AGENTS=(
  "vrs-attacker"
  "vrs-defender"
  "vrs-verifier"
  "vrs-integrator"
  "vrs-supervisor"
)

for agent in "${PRODUCT_AGENTS[@]}"; do
  agent_path=".claude/agents/${agent}.md"
  shipping_path="../../${SHIPPING_AGENTS}/${agent}.md"

  if [ ! -f "${SHIPPING_AGENTS}/${agent}.md" ]; then
    echo "  SKIP ${agent}.md (not in shipping)"
    continue
  fi

  rm -f "${agent_path}"
  ln -s "${shipping_path}" "${agent_path}"
  echo "  OK ${agent_path} -> ${shipping_path}"
done

echo ""
echo "Done. Verify with: ls -la .claude/skills/vrs-audit/SKILL.md .claude/agents/vrs-attacker.md"
