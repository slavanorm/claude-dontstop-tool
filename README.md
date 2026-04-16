# claude-custom-hook

Claude Code hooks: auto-deny binary questions, sounds, and todo management.

## Features

- **Auto-deny binary questions** — when Claude asks "Should I proceed?" or gives 2 options, hook blocks it and tells Claude to decide itself
- **Sounds** — pop on bash, chime on done
- **Volume** — `/volume N` (0-9, 0=mute)
- **Todo** — manage tasks directly, no AI processing

## Todo commands

| Command | Action |
|---|---|
| `todo buy milk` | add task |
| `todo 3 fix auth` | add with priority 3 |
| `todo 2` | mark #2 done |
| `todo u2` | undo #2 |
| `todo all` | mark all done |
| `todo r2 new text` | reword #2 |
| `todo vi` | export to file for editing |
| `todo sync` | import edited file back |
| `todo` | list tasks |

All todo commands are instant (hook blocks prompt, zero AI processing). Tasks are stored in `~/.claude/tasks/{session}/` and mirrored to `~/.claude/todos/` for `/todos` compatibility.

### Nesting via `todo vi`

```
[ ] #1 build auth
  [ ] #2 login page
  [ ] #3 signup page
    [ ] #4 email validation
  [ ] #5 deploy
```

Indent = child of parent above. Children get `blockedBy` parent automatically.

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
        "hooks": [{ "type": "command", "command": "claude-custom-hook" }]
      },
      {
        "matcher": "Bash",
        "hooks": [{ "type": "command", "command": "claude-custom-hook" }]
      }
    ],
    "Stop": [
      {
        "matcher": "*",
        "hooks": [{ "type": "command", "command": "echo '{\"tool_name\":\"Stop\"}' | claude-custom-hook" }]
      }
    ],
    "UserPromptSubmit": [
      {
        "matcher": "*",
        "hooks": [{ "type": "command", "command": "claude-custom-hook" }]
      }
    ]
  }
}
```

## Structure

```
claude_hook/
  __init__.py    # routing, binary detection, main entry point
  sound.py       # volume control, sound playback
  todo.py        # todo parser, storage, text format, handler
tests/
  test_hook.py   # binary detection, routing tests
  test_todo.py   # todo parser, storage, text roundtrip, handler tests
```

## Tests

```bash
pytest
```
