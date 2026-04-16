# Guide Agent And LLM Prompting For Testing

**Purpose:** Remove guesswork when prompting an LLM or agent to run real-world tests.

## When To Use

- Every time a new workflow, skill, or sub-agent is created.
- Whenever a phase requires validation or E2E evidence.

## Non-Negotiables

- Use claude-code-controller for all interactive tests.
- Use LIVE mode for validation.
- Produce evidence packs for every run.
- Follow the progressive disclosure path.
- Use `vrs-*` skill names (Claude Code does not accept `vrs:*`).
- Run agent-related skills inside a dedicated demo claude-code-agent-teams session.
- Follow the testing skill hierarchy in `.planning/testing/rules/canonical/TESTING-FRAMEWORK.md`.

## Progressive Disclosure Prompting

Start with minimal context, then load only the workflow you need.

**Step 1**
Load the index and pick the workflow:

- ` .planning/testing/DOC-INDEX.md `

**Step 2**
Load only one workflow doc and one guide if needed.

**Step 3**
Execute the workflow using claude-code-controller.

## Meta-Prompting (Use Selectively)

Use meta-prompts only when a workflow requires guaranteed structure (plan/report/evidence). Pair with hook validation.

Reference: `docs/reference/claude-code-orchestration.md`.

## Prompt Template For A Controller Agent

```text
You are the test controller.

1. Load .planning/testing/DOC-INDEX.md and select the correct workflow doc.
2. Load only that workflow doc and .planning/testing/guides/guide-claude-code-controller.md.
3. Use claude-code-controller to execute the workflow exactly as written.
4. Capture the transcript and save evidence pack to .vrs/testing/runs/<run_id>/.
5. Produce a report with mode=live, duration_ms, tokens_used, and limitations.
6. If any rule is violated, stop and report why, when, and which rule.
```

## Prompt Template For Audit Entry Point

```text
You are the audit controller.

1. Load .planning/testing/workflows/workflow-audit-entrypoint.md only.
2. Use claude-code-controller to run /vrs-workflow-test /vrs-audit contracts/ --criteria audit-entrypoint.
3. Verify health-check, init, graph build, tool initialization, and task lifecycle markers.
4. Capture transcript and evidence pack.
5. If missing TaskCreate/TaskUpdate or progress guidance, report a failure.
```

## Prompt Template For A Subject Agent

```text
You are the subject under test.
Follow the exact workflow command provided by the controller.
Do not invent steps or skip instructions.
Emit tool markers and evidence as required.
```

## Scope-Limited Prompting For Pattern Tests

If a test is focused on a single pattern, enforce scope.

```text
You are testing only pattern <pattern_id>.
Do not report unrelated vulnerabilities.
If unrelated issues appear, log them as out-of-scope and continue.
```

## Subagent Delegation Prompting

Before delegating to subagents, run instruction verification:

- ` .planning/testing/workflows/workflow-instruction-verification.md `

Then delegate with a bounded instruction:

```text
Execute only the provided workflow command.
Do not deviate or explore unrelated tasks.
Report failures with timestamps and rule references.
```

## Failure Reporting Template

```text
Failure Summary:
- What failed:
- When it failed:
- Rule violated:
- Evidence location:
- Recommended fix:
```
