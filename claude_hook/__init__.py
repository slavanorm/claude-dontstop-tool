#!/usr/bin/env python3
import json
import re
import subprocess
import sys
import traceback
from pathlib import Path

from claude_hook import sound, todo

LOG_FILE = Path.home() / ".claude" / "hook.log"

PATTERNS = [
    r'\byes\b', r'\bno\b', r'\by/n\b', r'\bconfirm\b',
    r'\bproceed\b', r'\bcontinue\b', r'\bshould i\b',
    r'\bdo you want\b', r'\bwould you like\b', r'\bsure\b',
    r'\bnext\b', r'\banother\b', r'\bmore\b',
    r'\bready\b', r'\bapprove\b', r'\bgo ahead\b'
]

DENY = """This appears to be a yes/no question.
Recall the user's original intent/task. Make the reasonable choice yourself and proceed."""


def log(msg: str):
    with LOG_FILE.open("a") as f:
        f.write(msg + "\n")


def logged(fn):
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception:
            log(traceback.format_exc())
            return {}
    return wrapper


def is_binary(questions: list) -> bool:
    for q in questions:
        opts = q.get('options', [])
        if len(opts) == 2:
            return True
        text = q.get('question', '').lower()
        for p in PATTERNS:
            if re.search(p, text):
                return True
    return False


def handle_ask(payload: dict) -> dict:
    params = payload.get('tool_input', {})
    questions = params.get('questions', [])
    if is_binary(questions):
        return dict(
            hookSpecificOutput=dict(
                hookEventName="PreToolUse",
                permissionDecision="deny",
                permissionDecisionReason=DENY,
            )
        )
    return {}


def handle_bash(payload: dict) -> dict:
    sound.play("pop")
    return dict(
        hookSpecificOutput=dict(
            hookEventName="PreToolUse",
            permissionDecision="allow",
            permissionDecisionReason="auto-approved by hook",
        )
    )


def handle_stop(payload: dict) -> dict:
    path = sound.SOUNDS["done"]
    if not Path(path).exists():
        subprocess.run(
            ["say", "-o", path, "done"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    v = sound.volume()
    if v == 0:
        return {}
    subprocess.Popen(
        ["afplay", "-v", str(v / 20), path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return {}


def handle_prompt(payload: dict) -> dict:
    prompt = payload.get('prompt', '').strip()
    m = re.match(r'/volume\s+(\d)', prompt.lower())
    if m:
        sound.VOLUME_FILE.write_text(m.group(1))
        return {}
    result = todo.handle(payload)
    if result is not None:
        return result
    return {}


@logged
def main():
    raw = sys.stdin.read()
    payload = json.loads(raw) if raw.strip() else {}
    tool = payload.get('tool_name', '')
    log(f"tool={tool} keys={list(payload.keys())}")
    if tool == 'AskUserQuestion':
        result = handle_ask(payload)
        if result:
            json.dump(result, sys.stdout)
    elif tool == 'Bash':
        result = handle_bash(payload)
        json.dump(result, sys.stdout)
    elif tool == 'Stop':
        handle_stop(payload)
    elif 'prompt' in payload:
        result = handle_prompt(payload)
        if result:
            json.dump(result, sys.stdout)


main()
