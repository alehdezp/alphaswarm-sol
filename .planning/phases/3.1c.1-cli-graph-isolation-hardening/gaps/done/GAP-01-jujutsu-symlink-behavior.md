# GAP-01: Jujutsu workspace symlink vs copy behavior for Python package files

**Created by:** improve-phase
**Source:** P1-IMP-05
**Priority:** HIGH
**Status:** active
**depends_on:** []

## Question

Does Jujutsu (`jj workspace add`) create copies or symlinks for Python package source files? Specifically, when a Jujutsu workspace is created from a Python project with an editable install, does `__file__` for modules in the workspace point to the workspace directory (copy) or back to the main worktree (symlink)?

## Context

Plan 01 proposes `__file__`-relative resolution to fix vulndocs path resolution from any working directory. If Jujutsu workspaces use symlinks for source files, `__file__` would point to the symlink location (workspace) while the actual vulndocs directory lives only in the real source tree. This would cause `Path(__file__).parent / "vulndocs"` to resolve to a non-existent path.

The decision between `__file__`-relative and `importlib.resources.files()` depends on this answer:
- If Jujutsu copies files: `__file__`-relative is safe (but vulndocs must also be copied)
- If Jujutsu symlinks files: `__file__`-relative may work IF symlinks are to the source tree where vulndocs lives
- If neither reliably: `importlib.resources.files()` is the safer choice

Plan 01 confidence drops from HIGH to MEDIUM if this is unverified.

## Research Approach

- Search for Jujutsu workspace documentation on file handling (copy vs symlink vs hardlink)
- Check Jujutsu source code or GitHub issues about workspace file strategy
- Test with `jj workspace add` if possible (verify with `readlink` or `ls -la`)
- Check how this interacts with Python's `__file__` attribute for editable installs
- Authoritative sources: Jujutsu official docs, GitHub repo, martinvonz/jj issues

## Findings

**Confidence: HIGH** (empirically verified + official documentation)

### 1. Jujutsu workspaces create REAL FILE COPIES, not symlinks

**Source:** Official Jujutsu documentation (https://docs.jj-vcs.dev/latest/working-copy/) + empirical verification on this project.

The Jujutsu working copy documentation states: "The working copy is where the current working-copy commit's files are **written** so you can interact with them." The `.jj/` directory contains a `repo` file that **links back** to the main repository's `.jj/repo`, but all source files are **full copies** written to the workspace directory.

**Empirical verification on this project:**
- Created workspace: `jj workspace add /tmp/test-jj-workspace-verify`
- Result: "Added 6406 files, modified 0 files, removed 0 files"
- `readlink /tmp/.../core.py` -> "NOT A SYMLINK" (confirmed real file)
- `file /tmp/.../core.py` -> "Python script text executable, ASCII text" (real file)
- `ls -la /tmp/.../core.py` -> regular file owned by user (not symlink)

### 2. vulndocs/ IS copied to the workspace

The vulndocs directory is present at `/tmp/test-jj-workspace-verify/vulndocs/` because it is tracked by jj (part of the commit tree). All tracked files are written as real copies.

### 3. BUT: editable install `__file__` does NOT point to the workspace

**Critical finding:** This project uses `uv tool install -e .` (editable install). With an editable install:
- `__file__` for `alphaswarm_sol.queries.patterns` resolves to: `./src/alphaswarm_sol/queries/patterns.py`
- This is the **original source tree**, NOT any workspace copy
- Even when running Python from a workspace directory, imported modules resolve to the editable install location (the main project root)

**Implication:** With editable install, `__file__`-relative resolution ALWAYS resolves to the main project's source tree. This means:
- `Path(__file__).parent / "../../vulndocs"` would resolve to the main tree's vulndocs, which EXISTS
- The workspace's vulndocs copy is IRRELEVANT for editable installs
- The `__file__`-relative fix works correctly for the editable install case

### 4. Non-editable install behavior

For `pip install alphaswarm-sol` (non-editable), `__file__` would point into `site-packages/`. In this case:
- vulndocs must be declared as `package_data` in `pyproject.toml` (P1-IMP-02 addresses this)
- `importlib.resources.files()` is the correct solution for this case

### Sources
- Jujutsu official docs: https://docs.jj-vcs.dev/latest/working-copy/ (HIGH confidence)
- Jujutsu man page: https://man.archlinux.org/man/jj-workspace-add.1.en (HIGH confidence)
- Empirical test on this project with jj 0.38.0 (VERIFIED)
- Python editable install behavior: Python packaging standard (HIGH confidence)

## Recommendation

**Plan 01 confidence remains HIGH.** The `__file__`-relative fix is safe for the project's use case.

Specifically:
1. **Keep `__file__`-relative resolution as the primary approach** for editable installs (development, Jujutsu workspaces, Agent Teams testing). This works because editable install `__file__` always points to the source tree where vulndocs lives.
2. **Add `importlib.resources` as the fallback** for non-editable installs (production `pip install`), as recommended by P1-IMP-02. The resolution function should try `__file__`-relative first, fall back to `importlib.resources.files()`.
3. **Add to Plan 01 assumptions in CONTEXT.md:** "Jujutsu workspaces create real file copies (not symlinks). With editable install, `__file__` resolves to the main source tree regardless of workspace cwd. The `__file__`-relative fix is verified safe for this project's development and testing workflow."
4. **Drop symlink concern entirely:** Jujutsu does NOT use symlinks for tracked files. The symlink edge case in IMP-05 does not apply.

**Plans affected:** Plan 01 (vulndocs resolution) -- confidence stays HIGH. No changes needed to Plan 02 or 03.
