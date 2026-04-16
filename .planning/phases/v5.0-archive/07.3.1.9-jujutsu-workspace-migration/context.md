# Phase 07.3.1.9: Jujutsu Workspace Migration

## Overview

**Goal:** Replace all git worktree implementations and references with Jujutsu (jj) workspace equivalents across the entire AlphaSwarm.sol codebase.

**Rationale:**
- Jujutsu workspaces provide simpler, commit-centric isolation (vs. git's branch-centric model)
- Multiple workspaces can point to the same revision (impossible with git worktrees)
- Built-in conflict tolerance and operation logging
- Lighter workspace creation overhead
- Better fit for parallel agent execution model

**Scope:**
- 2 production WorktreeManager implementations (~900 LOC)
- 1000+ lines of test code
- 212+ documentation files
- Phase 07.3.1.7 harness redesign

---

## Prerequisites

- [x] Jujutsu v0.37.0 installed (`/opt/homebrew/bin/jj`)
- [x] Repository colocated with jj (`.jj/` exists)
- [x] Migration inventory complete (MIGRATION-INVENTORY.md)
- [x] Jujutsu guide created (`.planning/testing/guides/guide-jujutsu-vcs.md`)

---

## Key Decisions

### D1: Naming Convention
- **Decision:** Rename `WorktreeManager` → `WorkspaceManager`
- **Rationale:** Aligns terminology with Jujutsu's workspace concept
- **Impact:** Breaking change for imports; requires update in all integration points

### D2: File Naming
- **Decision:** Rename `worktree.py` → `workspace.py`
- **Rationale:** Consistency with class naming
- **Impact:** Import path changes throughout codebase

### D3: Metadata Schema
- **Decision:** Replace `branch_name` field with `workspace_name`
- **Rationale:** Jujutsu workspaces don't require branches; workspace name is the identifier
- **Impact:** Schema migration for any persisted metadata

### D4: Cleanup Strategy
- **Decision:** Use two-step cleanup: `jj workspace forget` + `rm -rf`
- **Rationale:** Jujutsu's `forget` only removes tracking; disk cleanup is separate
- **Impact:** Slightly more verbose cleanup code but explicit behavior

### D5: Phase 07.3.1.7 Approach
- **Decision:** Rename phase to `07.3.1.7-synthetic-test-environments-workspace-harness`
- **Rationale:** Reflects new implementation technology
- **Impact:** All cross-references need updating

---

## Architecture

### Before (Git Worktrees)
```
Main Repository
├── .git/
│   └── worktrees/        # Git tracks worktrees here
│       ├── wt-agent-1/
│       └── wt-agent-2/
├── .vrs/
│   └── worktrees/
│       └── metadata.json  # Our tracking
└── src/

Worktree 1 (separate directory)
├── .git → ../main-repo/.git/worktrees/wt-agent-1
├── .vrs/                  # Isolated state
└── (working files)

Worktree 2 (separate directory)
├── .git → ../main-repo/.git/worktrees/wt-agent-2
├── .vrs/                  # Isolated state
└── (working files)
```

### After (Jujutsu Workspaces)
```
Main Repository
├── .jj/                   # Jujutsu repository data
│   ├── repo/             # Shared commit storage
│   └── working_copy/     # Main workspace state
├── .vrs/
│   └── workspaces/
│       └── metadata.json  # Our tracking (updated schema)
└── src/

Workspace 1 (separate directory)
├── .jj/                   # Links to main repo's .jj/repo
│   └── working_copy/     # This workspace's state
├── .vrs/                  # Isolated state
└── (working files)

Workspace 2 (separate directory)
├── .jj/                   # Links to main repo's .jj/repo
│   └── working_copy/     # This workspace's state
├── .vrs/                  # Isolated state
└── (working files)
```

---

## Migration Waves

### Wave 1: Core Implementation (Plans 01-03)
- Rename and update `orchestration/worktree.py` → `workspace.py`
- Rename and update `testing/flexible/worktree_manager.py` → `workspace_manager.py`
- Update test files with new mocks

### Wave 2: Integration Points (Plan 04)
- Update imports in PropulsionEngine
- Update imports in EnvironmentManager
- Update orchestration `__init__.py` exports

### Wave 3: Phase 07.3.1.7 Redesign (Plans 05-06)
- Rename phase directory
- Rewrite context.md
- Rewrite implementation plans

### Wave 4: Documentation Batch Updates (Plans 07-09)
- Testing guides rewrite
- Phase plan boilerplate updates (152 files)
- Public docs updates

### Wave 5: Verification (Plan 10)
- End-to-end workspace isolation test
- Parallel agent execution test
- Evidence pack capture test

---

## Success Criteria

1. **All git worktree commands removed** from production code
2. **All tests pass** with jj workspace commands (mocked or real)
3. **PropulsionEngine** successfully allocates/releases workspaces for parallel agents
4. **Phase 07.3.1.7** harness works with jj workspaces
5. **Documentation** consistently uses "workspace" terminology
6. **No regressions** in existing test coverage

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| jj workspace command differences break tests | HIGH | Comprehensive mocking; test on real jj repo |
| Cross-workspace state contamination | HIGH | Validate `.vrs/` isolation explicitly |
| 152-file batch update introduces errors | MEDIUM | Automated find/replace with review |
| Phase 07.3.1.7 depends on git-specific features | MEDIUM | Research jj equivalents before redesign |
| External documentation links to git worktree | LOW | Search/update external references |

---

## References

- [Jujutsu Documentation](https://martinvonz.github.io/jj/)
- [Migration Inventory](./MIGRATION-INVENTORY.md)
- [Jujutsu Guide](/.planning/testing/guides/guide-jujutsu-vcs.md)
- [Phase 07.3.1.7 Context](/.planning/phases/07.3.1.7-synthetic-test-environments-workspace-harness/context.md)
