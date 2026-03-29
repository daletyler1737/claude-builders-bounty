#!/usr/bin/env python3
"""
Claude Code Pre-Tool-Use Hook
Blocks dangerous commands before execution.

Install: Place in ~/.claude/hooks/ and add to settings.json:
  "hooks": {
    "pre-tool-use": [{"hook": "path/to/pre_tool_use_hook.py"}]
  }
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

HOOKS_DIR = Path.home() / ".claude" / "hooks"
BLOCKED_LOG = HOOKS_DIR / "blocked.log"

DANGEROUS_PATTERNS = [
    (r'rm\s+-rf\s+/(?:\S+)*',              "rm -rf / — attempts to delete root filesystem"),
    (r'rm\s+-rf\s+/\S+',                    "rm -rf on system directory — destructive"),
    (r'DROP\s+(?:TABLE|DATABASE)',           "DROP TABLE/DATABASE — destructive database operation"),
    (r'TRUNCATE\s+TABLE',                   "TRUNCATE TABLE — destructive database operation"),
    (r'DELETE\s+FROM\s+(?!.*\bWHERE\b)',    "DELETE FROM without WHERE clause — data loss risk"),
    (r'git\s+push\s+--force(?=\s|--|$)',  "git push --force — rewrites remote history"),
    (r'git\s+push\s+-f',                    "git push -f — rewrites remote history"),
    (r':!\s*rm\s+-rf',                     "vim/neovim :!rm -rf — destructive shell escape"),
    (r'%\s*rm\s+-rf',                      "IPython/Perl !rm -rf — destructive shell escape"),
]

DANGEROUS_PATTERNS = [(re.compile(p, re.IGNORECASE), m) for p, m in DANGEROUS_PATTERNS]

def get_tool_name(tool_use):
    if isinstance(tool_use, dict):
        return tool_use.get("name", "unknown")
    return str(tool_use)

def check_command(command_str):
    """Return (blocked: bool, reason: str)"""
    for pattern, reason in DANGEROUS_PATTERNS:
        if pattern.search(command_str):
            return True, reason
    return False, None

def log_blocked(tool_name, command, reason, project_path):
    HOOKS_DIR.mkdir(parents=True, exist_ok=True)
    with open(BLOCKED_LOG, "a") as f:
        f.write(
            f"[{datetime.now().isoformat()}] "
            f"BLOCKED {tool_name} in {project_path}\n"
            f"  Reason: {reason}\n"
            f"  Command: {command}\n\n"
        )

def build_blocked_message(tool_name, command, reason):
    return (
        f"\n{'='*60}\n"
        f"⚠️  HOOK BLOCKED — {tool_name}\n"
        f"{'='*60}\n"
        f"Reason: {reason}\n\n"
        f"Command:\n  {command}\n\n"
        f"This command was blocked by your Claude Code pre-tool-use hook.\n"
        f"It is considered dangerous and could cause irreversible damage.\n\n"
        f"If you believe this is a false positive, you can:\n"
        f"  1. Modify the command to be safer\n"
        f"  2. Temporarily disable the hook: remove from settings.json\n"
        f"  3. Ask your human for confirmation before proceeding\n\n"
        f"Full log: {BLOCKED_LOG}\n"
        f"{'='*60}\n"
    )

def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        print("pre_tool_use_hook: no input received")
        sys.exit(0)

    tool_name = payload.get("tool", "unknown")
    tool_input = payload.get("toolInput", {})

    # Only check bash commands
    if tool_name != "Bash":
        sys.exit(0)

    command = tool_input.get("command", "")
    if not command:
        sys.exit(0)

    project_path = os.environ.get("CLAUDE_PROJECT_PATH", ".")

    blocked, reason = check_command(command)

    if blocked:
        log_blocked(tool_name, command, reason, project_path)
        msg = build_blocked_message(tool_name, command, reason)
        # Print to stderr — Claude will show this to the user
        print(msg, file=sys.stderr)
        # Exit with non-zero to block
        sys.exit(1)

    sys.exit(0)

if __name__ == "__main__":
    main()
