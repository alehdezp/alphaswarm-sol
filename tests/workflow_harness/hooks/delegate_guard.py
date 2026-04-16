#!/usr/bin/env python3
"""Delegation guard hook: PreToolUse — blocks prohibited tool calls.

Event: PreToolUse (type: "command")
Behavior:
  - Read config from delegate_guard_config.yaml (or eval override via env vars)
  - Exit 2 on match (BLOCK the tool call)
  - Exit 0 on allow

P15-IMP-22: Config-driven delegation enforcement.
3.1c.2-01: Eval config + env-var gating + separated allow-lists + blocked-call logging.
"""

import datetime
import json
import os
import sys
from pathlib import Path


def _log_blocked(tool_name: str, matched_pattern: str, input_str: str) -> None:
    """Log a blocked tool call to DELEGATE_GUARD_LOG path (if set).

    Best-effort: OSError does not affect the block/allow decision.
    """
    log_path = os.environ.get("DELEGATE_GUARD_LOG")
    if not log_path:
        return
    record = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "action": "blocked",
        "tool_name": tool_name,
        "blocked_pattern": matched_pattern,
        "tool_input_preview": input_str[:200],
    }
    try:
        with open(log_path, "a") as f:
            f.write(json.dumps(record) + "\n")
    except OSError:
        pass


def _log_allowed(tool_name: str, matched_pattern: str, input_str: str) -> None:
    """Log an allowed exception-path hit to DELEGATE_GUARD_LOG path (if set).

    Best-effort: OSError does not affect the block/allow decision.
    """
    log_path = os.environ.get("DELEGATE_GUARD_LOG")
    if not log_path:
        return
    record = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "action": "allowed",
        "tool_name": tool_name,
        "matched_pattern": matched_pattern,
        "tool_input_preview": input_str[:200],
    }
    try:
        with open(log_path, "a") as f:
            f.write(json.dumps(record) + "\n")
    except OSError:
        pass


def _load_config() -> dict:
    """Load guard config from delegate_guard_config.yaml.

    Priority:
    0. Eval mode: _GUARD_PROFILE=strict + DELEGATE_GUARD_CONFIG env var (D-6)
    1. Same directory as this hook script
    2. .claude/hooks/ in the working directory
    3. Workspace root (.vrs/config/)
    """
    # Eval mode: env-var config path override (D-6 from CONTEXT.md)
    if os.environ.get("_GUARD_PROFILE") == "strict":
        config_override = os.environ.get("DELEGATE_GUARD_CONFIG", "")
        if config_override:
            override_path = Path(config_override)
            if override_path.is_file():
                try:
                    return _parse_simple_yaml(override_path)
                except (OSError, ValueError):
                    pass
            # Config path set but file missing or unreadable = fail-fast
            print(
                f"EVAL MODE: DELEGATE_GUARD_CONFIG not found or unreadable: {config_override}",
                file=sys.stderr,
            )
            sys.exit(2)

    config_name = "delegate_guard_config.yaml"
    search_paths = [
        Path(__file__).parent / config_name,
        Path(os.getcwd()) / ".claude" / "hooks" / config_name,
        Path(os.getcwd()) / ".vrs" / "config" / config_name,
    ]

    for config_path in search_paths:
        if config_path.is_file():
            try:
                # Use stdlib-compatible YAML parsing (simple key: [value] format)
                return _parse_simple_yaml(config_path)
            except (OSError, ValueError):
                continue

    return {"blocked_tools": [], "blocked_patterns": [], "allowed_reads": []}


def _parse_simple_yaml(path: Path) -> dict:
    """Parse a simple YAML config with list values.

    Supports format:
        blocked_tools:
          - Read
          - Write
        blocked_patterns:
          - "*.sol"
        allowed_reads:
          - ".vrs/"
        allowed_file_reads:
          - "contracts/"
        allowed_bash_commands:
          - "uv run alphaswarm"
    """
    config: dict = {}
    current_key: str | None = None

    with open(path) as f:
        for line in f:
            stripped = line.rstrip()
            if not stripped or stripped.startswith("#"):
                continue

            # Top-level key (no leading whitespace, ends with colon)
            if not stripped.startswith(" ") and stripped.endswith(":"):
                current_key = stripped[:-1].strip()
                config[current_key] = []
            # List item (leading whitespace, starts with -)
            elif stripped.lstrip().startswith("- ") and current_key is not None:
                value = stripped.lstrip()[2:].strip().strip("'\"")
                config[current_key].append(value)

    return config


def main() -> None:
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    config = _load_config()

    blocked_tools = config.get("blocked_tools", [])
    blocked_patterns = config.get("blocked_patterns", [])
    # New separated allow-lists (3.1c.2-01 bypass fix)
    # Fall back to allowed_reads for backward compatibility with dev config
    allowed_file_reads = config.get("allowed_file_reads", config.get("allowed_reads", []))
    allowed_bash_commands = config.get("allowed_bash_commands", [])

    input_str = json.dumps(tool_input)

    # Check if tool is explicitly blocked
    if tool_name in blocked_tools:
        # Check allowed_file_reads exceptions for Read tool
        if tool_name == "Read":
            file_path = tool_input.get("file_path", "") or tool_input.get("path", "")
            for allowed in allowed_file_reads:
                if allowed in file_path:
                    _log_allowed(tool_name, f"blocked_tool:{tool_name}", input_str)
                    sys.exit(0)  # Allowed exception
        # Check allowed_file_reads for Grep tool
        elif tool_name == "Grep":
            search_path = tool_input.get("path", "")
            for allowed in allowed_file_reads:
                if allowed in search_path:
                    _log_allowed(tool_name, f"blocked_tool:{tool_name}", input_str)
                    sys.exit(0)  # Allowed exception

        # Blocked by tool name (no exception matched)
        _log_blocked(tool_name, f"blocked_tool:{tool_name}", input_str)
        sys.exit(2)

    # Check blocked patterns against tool input
    for pattern in blocked_patterns:
        if pattern in input_str:
            # Tool-specific exception handling
            if tool_name == "Bash":
                # For Bash: check allowed_bash_commands (PREFIX match on command string)
                command = tool_input.get("command", "")
                for allowed_cmd in allowed_bash_commands:
                    if command.startswith(allowed_cmd):
                        _log_allowed(tool_name, pattern, input_str)
                        sys.exit(0)
            elif tool_name in ("Read", "Grep"):
                # For Read/Grep: check allowed_file_reads (substring match on file path)
                file_path = tool_input.get("file_path", tool_input.get("path", ""))
                for allowed_path in allowed_file_reads:
                    if allowed_path in file_path:
                        _log_allowed(tool_name, pattern, input_str)
                        sys.exit(0)
            else:
                # For other tools: check allowed_file_reads on input_str (backward compat)
                for allowed in allowed_file_reads:
                    if allowed in input_str:
                        _log_allowed(tool_name, pattern, input_str)
                        sys.exit(0)

            _log_blocked(tool_name, pattern, input_str)
            sys.exit(2)  # Blocked by pattern

    # Allow
    sys.exit(0)


if __name__ == "__main__":
    main()
