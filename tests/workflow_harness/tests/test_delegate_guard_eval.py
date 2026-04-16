"""Canary tests for evaluation delegate_guard config enforcement (3.1c.2-01).

These tests verify that the eval config (delegate_guard_config_eval.yaml) correctly:
- Blocks Python interpreter invocations (python, python3.12, from alphaswarm import)
- Allows alphaswarm CLI commands via prefix match on allowed_bash_commands
- Blocks reading project context (CLAUDE.md) while allowing contract file reads
- Fails fast when config path is invalid
- Closes the CRITICAL Gap 2.7 bypass (python -c "import alphaswarm")

All tests call delegate_guard.main() directly (not via subprocess) for speed.
Environment variables are set via monkeypatch and restored after each test.
"""

import io
import json
import os
import sys
from pathlib import Path

import pytest

# Resolve the hooks directory for delegate_guard import
_HOOKS_DIR = str(Path(__file__).resolve().parent.parent / "hooks")
if _HOOKS_DIR not in sys.path:
    sys.path.insert(0, _HOOKS_DIR)

import delegate_guard  # noqa: E402

_EVAL_CONFIG_PATH = str(
    Path(__file__).resolve().parent.parent
    / "hooks"
    / "delegate_guard_config_eval.yaml"
)


def _run_guard(monkeypatch, tool_name: str, tool_input: dict) -> int:
    """Run delegate_guard.main() with synthetic stdin and return the exit code.

    Sets _GUARD_PROFILE=strict and DELEGATE_GUARD_CONFIG to the eval config.
    Returns the SystemExit code (0=allowed, 2=blocked).
    """
    monkeypatch.setenv("_GUARD_PROFILE", "strict")
    monkeypatch.setenv("DELEGATE_GUARD_CONFIG", _EVAL_CONFIG_PATH)

    input_data = {"tool_name": tool_name, "tool_input": tool_input}
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))

    with pytest.raises(SystemExit) as exc_info:
        delegate_guard.main()

    return exc_info.value.code


class TestBlockPythonImports:
    """Tests 1-3: Python interpreter invocations are blocked."""

    def test_block_python_import_via_bash(self, monkeypatch):
        """Test 1: Bash(python -c 'import os') -> exit 2 (blocked)."""
        code = _run_guard(
            monkeypatch,
            "Bash",
            {"command": "python -c 'import os'"},
        )
        assert code == 2, f"Expected exit 2 (blocked), got {code}"

    def test_block_python3_without_trailing_space(self, monkeypatch):
        """Test 2: python3.12 (no trailing space) -> exit 2 (blocked).

        This specifically tests that 'python3' (no trailing space) catches python3.12.
        """
        code = _run_guard(
            monkeypatch,
            "Bash",
            {"command": "python3.12 -c 'import os'"},
        )
        assert code == 2, f"Expected exit 2 (blocked), got {code}"

    def test_block_from_alphaswarm_import(self, monkeypatch):
        """Test 3: from alphaswarm.kg import Graph -> exit 2 (blocked)."""
        code = _run_guard(
            monkeypatch,
            "Bash",
            {"command": "python -c 'from alphaswarm.kg import Graph'"},
        )
        assert code == 2, f"Expected exit 2 (blocked), got {code}"


class TestAllowAlphaswarmCLI:
    """Tests 4-5: alphaswarm CLI commands are allowed via prefix match."""

    def test_allow_uv_run_alphaswarm_build_kg(self, monkeypatch):
        """Test 4: uv run alphaswarm build-kg -> exit 0 (allowed).

        Command starts with 'uv run alphaswarm' in allowed_bash_commands.
        """
        code = _run_guard(
            monkeypatch,
            "Bash",
            {"command": "uv run alphaswarm build-kg contracts/Reentrancy.sol"},
        )
        assert code == 0, f"Expected exit 0 (allowed), got {code}"

    def test_allow_uv_run_alphaswarm_query(self, monkeypatch):
        """Test 5: uv run alphaswarm query -> exit 0 (allowed)."""
        code = _run_guard(
            monkeypatch,
            "Bash",
            {
                "command": "uv run alphaswarm query 'functions' --graph /tmp/g.toon"
            },
        )
        assert code == 0, f"Expected exit 0 (allowed), got {code}"


class TestFileAccessControl:
    """Tests 6-7: Context files blocked, contract files allowed."""

    def test_block_read_claude_md(self, monkeypatch):
        """Test 6: Read CLAUDE.md -> exit 2 (blocked).

        Read is in blocked_tools; path does not match allowed_file_reads.
        """
        code = _run_guard(
            monkeypatch,
            "Read",
            {"file_path": "/project/CLAUDE.md"},
        )
        assert code == 2, f"Expected exit 2 (blocked), got {code}"

    def test_allow_read_contract_files(self, monkeypatch):
        """Test 7: Read contracts/ReentrancyClassic.sol -> exit 0 (allowed).

        Read is in blocked_tools, but 'contracts/' is in allowed_file_reads.
        """
        code = _run_guard(
            monkeypatch,
            "Read",
            {"file_path": "contracts/ReentrancyClassic.sol"},
        )
        assert code == 0, f"Expected exit 0 (allowed), got {code}"


class TestFailFast:
    """Test 8: Fail-fast on invalid config path."""

    def test_failfast_invalid_config_path(self, monkeypatch):
        """Test 8: DELEGATE_GUARD_CONFIG=/nonexistent/path.yaml -> exit 2.

        When _GUARD_PROFILE=strict and config file is missing, the guard
        must fail-fast (exit 2) instead of falling through to dev config.
        """
        monkeypatch.setenv("_GUARD_PROFILE", "strict")
        monkeypatch.setenv("DELEGATE_GUARD_CONFIG", "/nonexistent/path.yaml")

        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "echo hello"},
        }
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))

        with pytest.raises(SystemExit) as exc_info:
            delegate_guard.main()

        assert (
            exc_info.value.code == 2
        ), f"Expected exit 2 (fail-fast), got {exc_info.value.code}"


class TestBypassRegression:
    """Test 9: THE CRITICAL Gap 2.7 bypass regression test."""

    def test_bypass_python_import_alphaswarm_blocked(self, monkeypatch):
        """Test 9 (CRITICAL): python -c 'import alphaswarm' -> exit 2 (BLOCKED).

        This is the CRITICAL test. With the old allowed_reads: ["alphaswarm"]
        config, this command would have been ALLOWED because "alphaswarm"
        appeared as a substring in the tool_input JSON, matching the
        allowed_reads escape hatch.

        With the new design:
        - allowed_bash_commands: ["uv run alphaswarm"] uses PREFIX match
          on the command string
        - "python -c 'import alphaswarm'" does NOT start with
          "uv run alphaswarm"
        - Therefore it is BLOCKED by the "python " pattern with no
          escape hatch match

        This test MUST be present and passing. It proves Gap 2.7 is closed.
        """
        code = _run_guard(
            monkeypatch,
            "Bash",
            {"command": "python -c 'import alphaswarm'"},
        )
        assert code == 2, (
            f"BYPASS DETECTED: Expected exit 2 (blocked), got {code}. "
            "Gap 2.7 is NOT closed -- 'python -c import alphaswarm' "
            "passed through the guard."
        )


class TestBlockedCallLogging:
    """Supplementary: verify _log_blocked writes JSON records."""

    def test_log_blocked_writes_json_record(self, monkeypatch, tmp_path):
        """Verify blocked calls produce JSON log entries at DELEGATE_GUARD_LOG."""
        log_file = tmp_path / "guard.log"
        monkeypatch.setenv("_GUARD_PROFILE", "strict")
        monkeypatch.setenv("DELEGATE_GUARD_CONFIG", _EVAL_CONFIG_PATH)
        monkeypatch.setenv("DELEGATE_GUARD_LOG", str(log_file))

        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "python -c 'import os'"},
        }
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))

        with pytest.raises(SystemExit) as exc_info:
            delegate_guard.main()

        assert exc_info.value.code == 2

        # Verify log file was written
        assert log_file.exists(), "DELEGATE_GUARD_LOG file was not created"
        content = log_file.read_text().strip()
        record = json.loads(content)
        assert record["action"] == "blocked"
        assert record["tool_name"] == "Bash"
        assert "blocked_pattern" in record
        assert "tool_input_preview" in record
        assert "timestamp" in record
