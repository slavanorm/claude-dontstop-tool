# claude-dontstop-tool

Claude Code hook that intercepts yes/no questions and tells Claude to decide and proceed autonomously.

## Why

When Claude asks "Should I proceed?" or gives you 2 options - often it can infer the answer from your original intent. This hook blocks such questions and prompts Claude to recall your intent and make the reasonable choice itself.

Result: less interruptions, more flow.

## How it works

1. Hooks into `AskUserQuestion` tool
2. Detects binary questions (exactly 2 options, or contains yes/no/confirm/proceed patterns)
3. Denies with message: "Recall user's original intent. Make the reasonable choice yourself and proceed."
4. Claude receives denial, reconsiders, and continues working

## Setup

```bash
git clone https://github.com/slavanorm/claude-dontstop-tool ~/.claude/tools/claude-dontstop-tool
pip install -e ~/.claude/tools/claude-dontstop-tool
```

Add to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "AskUserQuestion",
        "hooks": [
          {
            "type": "command",
            "command": "claude-dontstop"
          }
        ]
      }
    ]
  }
}
```
