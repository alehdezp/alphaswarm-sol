# claude-code-controller Instructions

A command-line tool for controlling CLI applications running in claude-code-agent-teams panes/windows.
Automatically detects whether you're inside or outside claude-code-agent-teams and uses the appropriate mode.

## Auto-Detection
- **Inside claude-code-agent-teams (Local Mode)**: Manages panes in your current claude-code-agent-teams window
- **Outside claude-code-agent-teams (Remote Mode)**: Creates and manages a separate claude-code-agent-teams session with windows

## Prerequisites
- claude-code-agent-teams must be installed
- The `claude-code-controller` command must be available (installed via `uv tool install`)

## Pane Identification

Panes can be specified in two simple ways:
- Just the pane number (e.g., `2`) - refers to pane 2 in the current window
- Full format: `session:window.pane` (e.g., `myapp:1.2`) - for any pane in any session

## ⚠️ IMPORTANT: Always Launch a Shell First!

**Always launch zsh first** to prevent losing output when commands fail:
```bash
claude-code-controller launch "zsh"  # Do this FIRST
claude-code-controller send "your-command" --pane=2  # Then run commands
```

If you launch a command directly and it errors, the pane closes immediately and you lose all output!

## Core Commands

### Launch a CLI application
```bash
claude-code-controller launch "command"
# Example: claude-code-controller launch "python3"
# Returns: pane identifier (e.g., session:window.pane format like myapp:1.2)
```

### Send input to a pane
```bash
claude-code-controller send "text" --pane=PANE_ID
# Example: claude-code-controller send "print('hello')" --pane=3

# By default, there's a 1.5-second delay between text and Enter,
# plus automatic Enter key verification with retry (up to 3 attempts).
# This ensures reliability with various CLI applications.

# To send without Enter:
claude-code-controller send "text" --pane=PANE_ID --enter=False

# To send immediately without delay:
claude-code-controller send "text" --pane=PANE_ID --delay-enter=False

# To use a custom delay (in seconds):
claude-code-controller send "text" --pane=PANE_ID --delay-enter=0.5
```

### Capture output from a pane
```bash
claude-code-controller capture --pane=PANE_ID --output=.vrs/testing/runs/<run_id>/transcript.txt
# Example: claude-code-controller capture --pane=2 --output=.vrs/testing/runs/vrs-2026-02-03-120000/transcript.txt
```

**Local mode note:** If claude-code-controller reports `MODE: LOCAL`, use shell redirection:

```bash
claude-code-controller capture --pane=PANE_ID > .vrs/testing/runs/<run_id>/transcript.txt
```

### List all panes
```bash
claude-code-controller list_panes
# Returns: JSON with pane IDs, indices, and status
```

### Show current claude-code-agent-teams status
```bash
claude-code-controller status
# Shows current location and all panes in current window
# Example output:
#   Current location: myapp:1.2
#   Panes in current window:
#    * myapp:1.0       zsh                  zsh
#      myapp:1.1       python3              python3
#      myapp:1.2       vim                  main.py
```

### Kill a pane
```bash
claude-code-controller kill --pane=PANE_ID
# Example: claude-code-controller kill --pane=2

# SAFETY: You cannot kill your own pane - this will give an error
# to prevent accidentally terminating your session
```

### Send interrupt (Ctrl+C)
```bash
claude-code-controller interrupt --pane=PANE_ID
# Example: claude-code-controller interrupt --pane=2
```

### Send escape key
```bash
claude-code-controller escape --pane=PANE_ID
# Example: claude-code-controller escape --pane=3
# Useful for exiting Claude or vim-like applications
```

### Wait for pane to become idle
```bash
claude-code-controller wait_idle --pane=PANE_ID
# Example: claude-code-controller wait_idle --pane=2
# Waits until no output changes for 2 seconds (default)

# Custom idle time and timeout:
claude-code-controller wait_idle --pane=2 --idle-time=3.0 --timeout=60
```

### Execute command and get exit code

Run a shell command and get both the output and exit code. Ideal for build/test
automation where you need to know if a command succeeded or failed.

```bash
claude-code-controller execute "pytest tests/" --pane=2
# Returns JSON: {"output": "...", "exit_code": 0}

# With custom timeout (default is 30 seconds)
claude-code-controller execute "long_running_script.sh" --pane=2 --timeout=120

# Timeout returns exit_code=-1
```

**Python API:**

```python
from claude_code_tools.claude-code-agent-teams_cli_controller import claude-code-agent-teamsCLIController

ctrl = claude-code-agent-teamsCLIController()
result = ctrl.execute("make test", pane_id="ops:1.2")
# Returns: {"output": "...", "exit_code": 0}
```

**Why use `execute()` instead of `send_keys()` + `capture_pane()`?**

- **Reliable exit codes**: Know definitively if a command succeeded or failed
- **No output parsing**: Don't guess success by looking for "error" in text
- **Proper automation**: Build pipelines that abort on failure, retry on transient
  errors, or continue on success

**When NOT to use `execute()`:**

- Agent-to-agent communication (Claude Code doesn't return exit codes)
- Interactive REPL sessions (use `send_keys()` + `wait_for_idle()` instead)
- Long-running processes you want to monitor incrementally

### Get help
```bash
claude-code-controller help
# Displays this documentation
```

## Typical Workflow

1. **ALWAYS launch a shell first** (prefer zsh) - this prevents losing output on errors:
   ```bash
   claude-code-controller launch "zsh"  # Returns pane identifier - DO THIS FIRST!
   ```

2. Run your command in the shell:
   ```bash
   claude-code-controller send "python script.py" --pane=2
   ```

3. Interact with the program:
   ```bash
   claude-code-controller send "user input" --pane=2
   claude-code-controller capture --pane=2  # Check output
   ```

4. Clean up when done:
   ```bash
   claude-code-controller kill --pane=2
   ```

## Remote Mode Specific Commands

These commands are only available when running outside claude-code-agent-teams:

### Attach to session
```bash
claude-code-controller attach
# Opens the managed claude-code-agent-teams session to view live
```

### Clean up session
```bash
claude-code-controller cleanup
# Kills the entire managed session and all its windows
```

### List windows
```bash
claude-code-controller list_windows
# Shows all windows in the managed session
```

## Tips
- Always save the pane/window identifier returned by `launch`
- Use `capture` to check the current state before sending input
- Use `status` to see all available panes and their current state
- In local mode: Pane identifiers can be session:window.pane format (like `myapp:1.2`) or just pane indices like `1`, `2`
- In remote mode: Window IDs can be indices like `0`, `1` or full form like `session:0.0`
- If you launch a command directly (not via shell), the pane/window closes when
  the command exits
- **IMPORTANT**: The tool prevents you from killing your own pane/window to avoid
  accidentally terminating your session

## Avoiding Polling
Instead of repeatedly checking with `capture`, use `wait_idle`:
```bash
# Send command to a CLI application
claude-code-controller send "analyze this code" --pane=2

# Wait for it to finish (no output for 3 seconds)
claude-code-controller wait_idle --pane=2 --idle-time=3.0

# Now capture the result
claude-code-controller capture --pane=2
```
