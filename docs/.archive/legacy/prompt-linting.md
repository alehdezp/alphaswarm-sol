# Prompt Linting Guide

This guide covers the prompt linting and tool description compression features added in Phase 7.1.3-05 for reducing LLM context size and detecting wasteful prompts.

## Overview

Prompt linting helps detect:
- **Oversized sections** - Code blocks, metadata, or source sections that waste tokens
- **Duplicate context** - Repeated evidence IDs, file paths, or code snippets
- **Missing constraints** - Prompts lacking output schemas or evidence requirements
- **Unused tools** - Tool references that aren't in the allowed list
- **Prompt size** - Prompts exceeding or approaching token budgets

Tool description compression reduces tool context by:
- Abbreviating common verbose phrases
- Truncating long descriptions and examples
- Removing non-essential fields in aggressive mode
- Creating minimal context strings for tight budgets

## Quick Start

### Lint a Prompt

```python
from alphaswarm_sol.llm.prompt_lint import lint_prompt

report = lint_prompt(prompt_text, context={"max_tokens": 6000})

if report.has_warnings:
    print(report.summary())
    # Prompt lint: 0 errors, 2 warnings, 1 info
    #   Tokens: 5200 total, ~300 wasteful
    #   [W] oversized-section (code_block_1): Code block 1 is 2500 chars...
```

### Compress Tool Descriptions

```python
from alphaswarm_sol.tools.description_compress import compress_tool_description

tool = {
    "name": "slither",
    "description": "Static analyzer for Solidity - primary VKG data source",
    "install_hint": "pip install slither-analyzer",
}
compressed = compress_tool_description(tool)
# description -> "Solidity static analyzer - VKG core"
```

### Get Tools for LLM Context

```python
from alphaswarm_sol.tools.registry import ToolRegistry

registry = ToolRegistry()

# Get compressed tool list (for structured context)
tools = registry.get_tools_for_context(max_tokens=500)

# Get minimal context string (for inline prompts)
context = registry.get_tools_context_string(max_chars=200)
# "Tools: slither(pip), aderyn(cargo), mythril(pip)"
```

## Lint Rules

### oversized-section

Detects sections that exceed size thresholds:

| Section Type | Threshold |
|-------------|-----------|
| Code blocks (``` ... ```) | 2000 chars (~500 tokens) |
| Metadata (## Metadata) | 1000 chars (~250 tokens) |
| Raw source (## Source, ## Raw Code) | 3000 chars (~750 tokens) |
| Full context (## Full Context) | 3000 chars (~750 tokens) |

**Severity:** WARN

**Example violation:**
```
[W] oversized-section (code_block_1): Code block 1 is 2500 chars (500 over threshold)
```

**Suggestion:** Trim code to essential lines or use evidence IDs instead of full code.

### duplicate-context

Detects duplicated content that wastes tokens:

- Duplicate evidence IDs (e.g., E-ABC123 appearing multiple times)
- Repeated file paths (same file mentioned more than twice)
- Duplicate code definitions (same function/modifier declarations)

**Severity:** WARN (evidence), INFO (file paths, code)

**Example violation:**
```
[W] duplicate-context (evidence_ids): Found 3 duplicate evidence IDs
```

**Suggestion:** Deduplicate evidence references before building prompt.

### missing-constraint

Detects prompts missing important constraints:

- No output schema specified (INFO)
- No evidence requirement stated (WARN)
- Verification task without confidence constraint (INFO)

**Severity:** WARN or INFO depending on constraint

**Example violation:**
```
[W] missing-constraint: No evidence requirement stated
```

**Suggestion:** Add "cite evidence IDs" or similar constraint.

### unused-tool

Detects tool references that may be unused or invalid:

- Tool names mentioned but not in allowed list
- Tool descriptions included but tool not actually needed

**Severity:** WARN

**Requires:** `allowed_tools` in lint context

**Example violation:**
```
[W] unused-tool (tool_reference): Tool 'unknown_tool' referenced but not in allowed list
```

### prompt-size

Checks overall prompt size against budget:

- Error if exceeds `max_tokens`
- Warning if > 80% of budget

**Severity:** ERROR (over budget), WARN (approaching budget)

**Example violation:**
```
[E] prompt-size: Prompt exceeds budget: ~7500 tokens (limit: 6000)
```

## Integration with Subagent Manager

Prompt linting is automatically integrated into `LLMSubagentManager._build_prompt()`. When dispatching tasks:

```python
from alphaswarm_sol.llm.subagents import LLMSubagentManager, SubagentTask, TaskType

manager = LLMSubagentManager()
task = SubagentTask(
    type=TaskType.TIER_B_VERIFICATION,
    prompt="Verify this finding",
    context={"evidence": [...], "code": ...},
)

result = await manager.dispatch(task)

# Lint report available in result
if result.prompt_lint_report:
    report = result.prompt_lint_report
    print(f"Wasteful tokens: {report['wasteful_tokens']}")
```

Lint warnings are logged but don't block execution by default.

## Tool Description Compression

### Phrase Abbreviations

Common verbose phrases are automatically shortened:

| Original | Compressed |
|----------|------------|
| Static analyzer for Solidity | Solidity static analyzer |
| primary VKG data source | VKG core |
| Rust-based Solidity analyzer with custom detectors | Rust analyzer |
| Symbolic execution for vulnerability detection | Symbolic exec |
| Property-based fuzzer for smart contracts | Fuzzer |
| Fast testing framework and toolkit | Testing toolkit |

### Aggressive Mode

For tight token budgets, aggressive mode:
- Limits descriptions to 50 chars
- Removes homepage URLs
- Truncates lists to 3 items
- Shortens URLs to domain/path

```python
compressed = compress_tool_description(tool, aggressive=True)
```

### Batch Compression with Budget

```python
from alphaswarm_sol.tools.description_compress import compress_tool_descriptions

# Compress tools to fit within token budget
compressed = compress_tool_descriptions(tools, max_tokens=200)
```

The function automatically escalates to aggressive mode if needed, and falls back to minimal fields (name, binary, install_hint) for extreme budgets.

## Custom Linter Configuration

### Include/Exclude Rules

```python
from alphaswarm_sol.llm.prompt_lint import create_linter

# Only check prompt size
linter = create_linter(include_rules=["prompt-size"])

# Exclude verbose rules
linter = create_linter(exclude_rules=["duplicate-context", "missing-constraint"])

report = linter.lint(prompt)
```

### Custom Rules

```python
from alphaswarm_sol.llm.prompt_lint import LintRule, LintViolation, LintSeverity

class CustomRule(LintRule):
    @property
    def rule_id(self) -> str:
        return "custom-rule"

    def check(self, prompt: str, context: dict) -> list:
        violations = []
        if "forbidden_keyword" in prompt:
            violations.append(LintViolation(
                rule_id=self.rule_id,
                severity=LintSeverity.ERROR,
                message="Forbidden keyword found",
            ))
        return violations

linter = PromptLinter(rules=[CustomRule()])
```

## Best Practices

1. **Always lint before expensive calls** - Catch wasteful context early
2. **Use evidence IDs over full code** - Reference evidence by ID, not inline code
3. **Compress tool descriptions for context** - Use `get_tools_context_string()` for minimal overhead
4. **Set appropriate token budgets** - Default is 6000, use 8000 as absolute max
5. **Monitor wasteful_tokens metric** - Track this over time to identify patterns
6. **Address WARN violations** - They indicate improvable patterns

## Related Documentation

- [Context Budget Policy](./context-budget.md) - Token budgeting and progressive disclosure
- [Model Routing](./model-routing.md) - Tier-based model selection
- [Subagent Manager](./subagents.md) - LLM dispatch and routing
