# Git Worktree → Jujutsu Workspace Migration Inventory

**Phase:** 07.3.1.9 - Jujutsu Workspace Migration
**Created:** 2026-02-04
**Status:** PLANNING

---

## Executive Summary

This document provides a complete inventory of all git worktree references and implementations across the AlphaSwarm.sol codebase that must be migrated to Jujutsu (jj) workspaces.

**Scope:**
- 212+ documentation files with worktree references
- 2 production WorktreeManager implementations (~900 lines)
- 1000+ lines of test code
- Integration points in PropulsionEngine, EnvironmentManager

**Migration Complexity:** MEDIUM
- Most changes are terminology updates (documentation)
- Core implementation requires subprocess command changes
- Existing abstraction layers minimize integration impact

---

## Part 1: Production Code Implementations

### 1.1 Orchestration WorktreeManager (PRIMARY)

**File:** `src/alphaswarm_sol/orchestration/worktree.py`
**Lines:** 1-577
**Purpose:** Phase 07.1.1-05 agent isolation for parallel safe execution

| Component | Current | Jujutsu Equivalent | Migration Notes |
|-----------|---------|-------------------|-----------------|
| `WorktreeManager` class | Git-based | JJ-based | Rename to `WorkspaceManager` |
| `WorktreeMetadata` dataclass | `branch_name` field | `workspace_name` field | Schema change |
| `WorktreeError` exception | Keep | Keep | No change |

**Methods to Update:**

| Method | Git Commands Used | Jujutsu Replacement |
|--------|-------------------|---------------------|
| `_find_repo_root()` | `git rev-parse --show-toplevel` | `jj root` |
| `allocate()` | `git worktree add -b {branch} {path} {ref}` | `jj workspace add {path} --name {name} -r {rev}` |
| `release()` | Status update only | No change |
| `_remove_worktree()` | `git worktree remove --force` + `git branch -D` | `jj workspace forget` + `rm -rf` |
| `cleanup_pool()` | Iterates `_remove_worktree()` | Same pattern |
| `cleanup_stale()` | Time-based removal | Same pattern |
| `_prune_worktrees()` | `git worktree prune` | Remove (implicit in jj) |
| `_get_current_ref()` | `git rev-parse HEAD` | `jj log -r @ -T commit_id` |

**Key Code Changes (line numbers):**

| Lines | Current Code | Required Change |
|-------|-------------|-----------------|
| 163-183 | `["git", "rev-parse", "--show-toplevel"]` | `["jj", "root"]` |
| 228-244 | `["git", "rev-parse", "HEAD"]` | `["jj", "log", "-r", "@", ...]` |
| 292 | `branch_name = f"vrs-{pool_id[:8]}-..."` | `workspace_name = f"vrs-{pool_id[:8]}-..."` |
| 294-313 | `["git", "worktree", "add", "-b", ...]` | `["jj", "workspace", "add", "--name", ...]` |
| 398-410 | `["git", "worktree", "remove", "--force", ...]` | `["jj", "workspace", "forget", ...]` |
| 420-431 | `["git", "branch", "-D", branch_name]` | Remove (not needed in jj) |
| 529-540 | `["git", "worktree", "prune"]` | Remove or stub |

---

### 1.2 Testing WorktreeManager (SECONDARY)

**File:** `src/alphaswarm_sol/testing/flexible/worktree_manager.py`
**Lines:** 1-317
**Purpose:** Lightweight worktree management for test environments

| Component | Current | Jujutsu Equivalent | Migration Notes |
|-----------|---------|-------------------|-----------------|
| `WorktreeManager` class | Git-based | JJ-based | Rename to `WorkspaceManager` |
| `Worktree` dataclass | `name`, `path`, `ref` | Same fields | No change |
| `WorktreeError` exception | Keep | Keep | No change |
| `MAX_WORKTREES = 5` | Keep | Keep | Rename to `MAX_WORKSPACES` |

**Methods to Update:**

| Method | Git Commands Used | Jujutsu Replacement |
|--------|-------------------|---------------------|
| `create()` | `git worktree add --detach {path} {ref}` | `jj workspace add {path} -r {rev}` |
| `remove()` | `git worktree remove --force` | `jj workspace forget` + `rm -rf` |
| `list_worktrees()` | Directory walk | `jj workspace list` + parse |
| `cleanup_all()` | Iterative removal | Same pattern |
| `cleanup_stale()` | Time-based removal | Same pattern |
| `managed_worktree()` | Context manager | No change (wraps create/remove) |

**Key Code Changes (line numbers):**

| Lines | Current Code | Required Change |
|-------|-------------|-----------------|
| 151-157 | `["git", "worktree", "add", "--detach", ...]` | `["jj", "workspace", "add", ...]` |
| 219-225 | `["git", "worktree", "remove", "--force", ...]` | `["jj", "workspace", "forget", ...]` |

---

### 1.3 Integration Points (No Direct Git Commands)

These files call WorktreeManager but don't use git directly:

| File | Integration | Migration Impact |
|------|-------------|------------------|
| `src/alphaswarm_sol/agents/propulsion/engine.py` | Calls `WorktreeManager.allocate/release` | Update imports only |
| `src/alphaswarm_sol/testing/flexible/environment.py` | Calls `WorktreeManager.create/remove` | Update imports only |
| `src/alphaswarm_sol/agents/runtime/base.py` | Uses `workdir` config field | No change |
| `src/alphaswarm_sol/orchestration/__init__.py` | Exports `WorktreeManager` | Update export name |

---

### 1.4 Test Files

| File | Lines | Migration Notes |
|------|-------|-----------------|
| `tests/agents/test_worktree_isolation.py` | 677 | Mock `jj` commands instead of `git` |
| `tests/test_worktree_manager.py` | 348 | Mock `jj` commands instead of `git` |

**Test Classes to Update:**

| Class | Tests | Changes |
|-------|-------|---------|
| `TestAgentConfigWorkdir` | 4 | No change (abstraction-agnostic) |
| `TestWorktreeManager` | 14 | Update mocks for jj commands |
| `TestWorktreeMetadata` | 2 | Update field name `branch_name` → `workspace_name` |
| `TestPropulsionEngineWorktreeIntegration` | 7 | Update mocks for jj commands |
| `TestParallelAgentWorktrees` | 2 | Update mocks for jj commands |
| `TestCodexCLIRuntimeWorkdir` | 6 | No change (abstraction-agnostic) |
| `TestWorktreeCleanup` | 3 | Update mocks for jj commands |
| `TestEnvironment` | 2 | No change |
| `TestEnvironmentManager` | 7 | Update mocks for jj commands |

---

## Part 2: Documentation - Phase Plans (212 Files)

### 2.1 Boilerplate Guardrail Pattern (152 Files)

**Pattern Found In:** Phases 05.0 through 07.1.4

**Current Text:**
```
- Worktree isolation: run any commands or experiments that mutate state in a fresh git worktree;
  do not use the main worktree and do not reuse worktrees for reruns.
```

**Replacement Text:**
```
- Workspace isolation: run any commands or experiments that mutate state in a fresh jj workspace;
  do not use the main workspace and do not reuse workspaces for reruns.
```

**Phases Affected:**
| Phase | Plan Count |
|-------|------------|
| 05-semantic-labeling | 8 |
| 05.1-static-analysis-tool-integration | 10 |
| 05.2-multi-agent-sdk-integration | 10 |
| 05.3-opencode-sdk-refactor | 10 |
| 05.4-vulndocs-patterns-unification | 10 |
| 05.5-agent-execution-context-enhancement | 8 |
| 05.6-orchestration-skill-separation | 9 |
| 05.6.1-toon-format-adoption | 4 |
| 05.7-vulndocs-knowledge-consolidation | 10 |
| 05.8-repository-cleanup-hygiene | 5 |
| 05.9-llm-graph-interface-improvements | 13 |
| 05.10-pattern-context-batch-discovery-orchestration | 14 |
| 05.11-economic-context-agentic-workflow-integrity | 10 |
| 06-release-preparation | 7 |
| 06.1-rebrand-completion | 2 |
| 07.1.1-production-orchestration-hardening | 4 |
| 07.1.3-cost-token-efficiency-context-engineering | 1 |
| 07.1.4-interop-orchestrator-adapters | 6 |

---

### 2.2 Dedicated Worktree Harness Phase (CRITICAL)

**Phase:** 07.3.1.7-synthetic-test-environments-workspace-harness (RENAMED)

**Status:** Directory renamed and context.md updated in Plan 07.3.1.9-05.

**Files:**
| File | Workspace References | Migration Status |
|------|---------------------|------------------|
| `context.md` | 6+ | DONE - updated in Plan 05 |
| `07.3.1.7-00-PLAN.md` | 10+ | PENDING - Plan 06 |
| `07.3.1.7-02-PLAN.md` | 20+ | PENDING - Plan 06 |
| `07.3.1.7-03-PLAN.md` | 5+ | PENDING - Plan 06 |

**Completed Updates (Plan 05):**
- Phase directory renamed from `worktree-harness` to `workspace-harness`
- context.md rewritten with jj workspace terminology:
  - Strategy section: jj workspace per scenario
  - Locked decisions: jj revision history
  - Required sources: manage_workspaces.sh, workspace_snapshot_policy.yaml
  - Success definition: jj workspace add/forget commands

**Remaining (Plan 06):**
- Rewrite implementation plans (07.3.1.7-0x-PLAN.md files)

---

### 2.3 Validation & Testing Phases

| Phase | Files | Key References |
|-------|-------|----------------|
| 07.3-validation-program | 1 | Line 92: "new worktree, new evidence pack" |
| 07.3.1.5-full-testing-orchestrator | 12+ | WORKTREE-SNAPSHOT-MATRIX.md |
| 07.3.1.6-full-testing-hardening | 6 | Worktree stress testing |
| 07.3.1.8-synthetic-expansion-stress-testing | 3 | Multi-worktree matrix |
| 07.3.2-execution-evidence-protocol | 2 | Evidence capture in worktrees |

**File: 07.3.1.5-WORKTREE-SNAPSHOT-MATRIX.md**

Defines 7 canonical snapshot stages - needs complete rewrite for jj operations:
1. `pre-graph` → Use jj revision
2. `post-graph` → Use jj revision
3. `post-context` → Use jj revision
4. `post-patterns` → Use jj revision
5. `post-agents` → Use jj revision
6. `post-debate` → Use jj revision
7. `post-report` → Use jj revision

---

### 2.4 GA Validation Plans (35+ Files)

**Pattern:** Each validation gate requires isolated worktree evidence

**Phases:**
- 07.3-00-v6-PLAN.md through 07.3-12-v6-PLAN.md
- Multiple SUMMARY files

**Replacement Strategy:** Batch find/replace "worktree" → "workspace"

---

## Part 3: Testing Documentation & Guides

### 3.1 Primary Guide Requiring Rewrite

**File:** `.planning/testing/guides/guide-worktree-scenarios.md`

**Current Purpose:** Use GitHub worktrees to create isolated, reusable, real-world test scenarios

**Migration Options:**
1. **Option A:** Rename to `guide-jujutsu-workspaces.md` and rewrite
2. **Option B:** Update in-place with jj workspace commands

**Commands to Replace:**

| Line | Current | Replacement |
|------|---------|-------------|
| 22-29 | `git worktree add ../vrs-wt-audit-001 -b wt-audit-001` | `jj workspace add ../vrs-wt-audit-001 -r @` |
| 22-29 | `git worktree remove ../vrs-wt-audit-001` | `jj workspace forget vrs-wt-audit-001` + `rm -rf ../vrs-wt-audit-001` |

---

### 3.2 Secondary Guides (Minor Updates)

| File | Lines | Change |
|------|-------|--------|
| `.planning/testing/guides/guide-claude-code-controller.md` | 37 | "worktree" → "workspace" |
| `.planning/testing/guides/guide-iteration.md` | 73 | "worktree" → "workspace" |
| `.planning/testing/rules/canonical/TESTING-FRAMEWORK.md` | 215 | "worktrees" → "workspaces" |
| `.planning/testing/rules/canonical/TESTING-PHILOSOPHY.md` | 22 | "worktrees" → "workspaces" |

---

### 3.3 Index & Cross-Reference Files

| File | Lines | Reference Updates |
|------|-------|-------------------|
| `.planning/testing/DOC-INDEX.md` | 60, 125, 189 | Guide name if renamed |
| `.planning/testing/README.md` | 70-71, 157 | "worktree" → "workspace" |
| `.planning/testing/CONTEXT-OVERVIEW.md` | 79 | Guide reference |
| `.planning/testing/DOCS-VALIDATION-STATUS.md` | 32 | Guide reference |
| `.planning/TESTING-INDEX.md` | 17 | Guide reference |

---

## Part 4: Public Documentation (docs/)

### 4.1 Architecture Diagram

**File:** `docs/workflows/diagrams/05-testing-architecture.md`

**Lines 356-360:**
```mermaid
subgraph Worktrees["Isolated Worktrees"]
    W1["worktree-1<br/>/test-001"]
    W2["worktree-2<br/>/test-002"]
    W3["worktree-3<br/>/test-003"]
end
```

**Replacement:**
```mermaid
subgraph Workspaces["Isolated JJ Workspaces"]
    W1["workspace-1<br/>/test-001"]
    W2["workspace-2<br/>/test-002"]
    W3["workspace-3<br/>/test-003"]
end
```

**Lines 373-377 (Parallel Testing Rules):**
```
Current: "- Each test in separate worktree"
Update:  "- Each test in separate jj workspace"
```

---

## Part 5: Scripts & Configuration

### 5.1 Scripts to Create/Update

| File | Status | Action |
|------|--------|--------|
| `scripts/manage_worktrees.sh` | Planned in 07.3.1.7 | Create as `scripts/manage_workspaces.sh` |
| `scripts/test_real_workflow.py` | May exist | Update to use jj workspace commands |

### 5.2 Configuration Files

| File | Change |
|------|--------|
| `configs/worktree_snapshot_policy.yaml` | Planned - create as `workspace_snapshot_policy.yaml` |
| `configs/claude_code_controller_markers.yaml` | Check for worktree path references |

---

## Part 6: Migration Execution Plan

### Priority 1: Core Implementation (BLOCKING)

1. **Update `src/alphaswarm_sol/orchestration/worktree.py`**
   - Rename to `workspace.py`
   - Replace all `git worktree` → `jj workspace` commands
   - Update class name `WorktreeManager` → `WorkspaceManager`
   - Update dataclass `WorktreeMetadata` → `WorkspaceMetadata`
   - Update field `branch_name` → `workspace_name`

2. **Update `src/alphaswarm_sol/testing/flexible/worktree_manager.py`**
   - Same changes as above

3. **Update test files**
   - `tests/agents/test_worktree_isolation.py`
   - `tests/test_worktree_manager.py`

4. **Update imports in integration points**
   - `src/alphaswarm_sol/agents/propulsion/engine.py`
   - `src/alphaswarm_sol/testing/flexible/environment.py`
   - `src/alphaswarm_sol/orchestration/__init__.py`

### Priority 2: Phase 07.3.1.7 Harness (BLOCKING)

1. **Rename phase directory** (optional but recommended)
2. **Rewrite context.md** with jj workspace architecture
3. **Rewrite 07.3.1.7-02-PLAN.md** with jj workspace tasks
4. **Create jj workspace scripts**

### Priority 3: Testing Guides (HIGH)

1. **Rewrite guide-worktree-scenarios.md** or create guide-jujutsu-workspaces.md
2. **Update secondary guides** (find/replace)
3. **Update index files** with new guide references

### Priority 4: Documentation Batch Updates (MEDIUM)

1. **Boilerplate guardrail** - Batch replace in 152 phase plan files
2. **GA validation plans** - Batch replace in 35+ files
3. **Public docs** - Update architecture diagram

### Priority 5: Configuration & Scripts (LOW)

1. Create workspace management scripts
2. Update any configuration files

---

## Verification Checklist

After migration, verify:

- [ ] `jj workspace add` creates isolated test environment
- [ ] `jj workspace forget` + `rm -rf` cleans up completely
- [ ] `jj workspace list` shows all active workspaces
- [ ] PropulsionEngine can allocate/release workspaces for agents
- [ ] EnvironmentManager can switch between environments
- [ ] All tests pass with jj commands mocked
- [ ] Parallel workspace creation works without conflicts
- [ ] `.vrs/` directories are isolated per workspace
- [ ] Evidence packs capture workspace state correctly

---

## Command Reference (Quick Lookup)

### Git Worktree → JJ Workspace

| Git Worktree | JJ Workspace | Notes |
|--------------|--------------|-------|
| `git worktree add <path> <branch>` | `jj workspace add <path> -r <rev>` | No branch required |
| `git worktree add -b <branch> <path> <ref>` | `jj workspace add <path> --name <name> -r <rev>` | Name optional |
| `git worktree remove <path>` | `jj workspace forget <name>` + `rm -rf <path>` | Two-step cleanup |
| `git worktree list` | `jj workspace list` | Similar output |
| `git worktree prune` | N/A (automatic) | Not needed in jj |
| `git rev-parse --show-toplevel` | `jj root` | Repository root |
| `git rev-parse HEAD` | `jj log -r @ -T commit_id --no-graph` | Current revision |

### JJ-Only Commands (New Capabilities)

| Command | Purpose |
|---------|---------|
| `jj workspace update-stale` | Recover workspace after external changes |
| `jj workspace rename <old> <new>` | Rename workspace |
| `jj op log` | View operation history |
| `jj undo` | Undo last operation |

---

## Appendix: Jujutsu Reference

See: `.planning/testing/guides/guide-jujutsu-vcs.md` for complete jj command reference and testing workflow patterns.
