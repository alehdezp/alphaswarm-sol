# Workflow Expectations (Product Behavior)

**Status:** Legacy reference only. Canonical workflow contracts now live in ` docs/workflows/ `.
Use ` docs/workflows/README.md ` and ` docs/workflows/workflow-*.md ` for current behavior.

**Purpose:** Define expected behavior for each workflow, skill, and subagent.

This file is the product‑level reference. Testing details live in:
- `.planning/testing/`

## Naming Contract

- Skills and commands use `vrs-*` naming.
- `/vrs-` naming is deprecated and should not appear in new docs.

## Orchestrator Workflow (Audit Entrypoint)

**Inputs:** contract scope, settings, tools available  
**Outputs:** evidence‑linked report, task history, state updates  
**Success:** staged execution with TaskCreate/Task/TaskUpdate and progress guidance  
**Failure:** skips stages, no tasks created, or no state updates

Stages:
1. Health check
2. Init (install skills)
3. Graph build
4. Context generation (protocol + economic)
5. Tool initialization (status + run)
6. Pattern detection (Tier A/B/C)
7. Task orchestration (specialists + attacker/defender/verifier)
8. Verification + false‑positive handling
9. Final report

### Legacy Addendum (Hooks + Tasks)

This legacy reference assumes orchestration enforcement. Current contract adds:
- Hook‑based preflight gates and completion gates.
- TaskCreate/TaskUpdate markers required before findings.

Canonical reference: `docs/reference/claude-code-orchestration.md`.

## Graph Build Workflow

**Inputs:** contracts path  
**Outputs:** `.vrs/graphs/*.toon`, query outputs  
**Success:** evidence refs + valid graph contract  
**Failure:** query outputs without evidence or invalid schema

## Context Generation Workflow

**Inputs:** contracts + docs  
**Outputs:** `.vrs/context/protocol-pack.yaml`, economic context artifacts  
**Success:** context exists before Tier C execution  
**Failure:** Tier C runs without context

## Tool Integration Workflow

**Inputs:** tool availability  
**Outputs:** tool results and markers in transcript  
**Success:** tools run before findings are finalized  
**Failure:** no tool markers in audit flow

## Task Orchestration Workflow

**Inputs:** pattern candidates  
**Outputs:** TaskCreate/Task/TaskUpdate records  
**Success:** tasks scoped to single patterns, subagents do not drift  
**Failure:** findings produced without tasks or verification

## Verification Workflow

**Inputs:** candidate findings  
**Outputs:** verified or discarded findings  
**Success:** false positives explicitly discarded  
**Failure:** all findings reported without verification

## State And Settings Contracts

**Settings (user‑configured):** `.vrs/settings.yaml`  
**State (auto‑updated):** `.vrs/state/current.yaml`

Settings must control:
- tools enabled/disabled
- Tier A/B/C gating
- context generation

State must expose:
- current stage
- completed stages
- pending tasks/beads
- available tools

## Subagent Expectations

- `vrs-attacker`: exploit path only
- `vrs-defender`: guard/mitigation only
- `vrs-verifier`: evidence arbitration only
- specialists: confined to assigned pattern scope

Each subagent must:
- use graph‑first queries
- produce evidence refs
- avoid out‑of‑scope findings
