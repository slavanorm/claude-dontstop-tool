#!/usr/bin/env python3
import sys
import json
import re

PATTERNS = [
    r'\byes\b', r'\bno\b', r'\by/n\b', r'\bconfirm\b',
    r'\bproceed\b', r'\bcontinue\b', r'\bshould i\b',
    r'\bdo you want\b', r'\bwould you like\b', r'\bsure\b',
    r'\bnext\b', r'\banother\b', r'\bmore\b',
    r'\bready\b', r'\bapprove\b', r'\bgo ahead\b'
]

REASON = """This appears to be a yes/no question.
Recall the user's original intent/task. Make the reasonable choice yourself and proceed."""


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


def main():
    payload = json.load(sys.stdin)
    params = payload.get('tool_input', {})
    questions = params.get('questions', [])
    
    if is_binary(questions):
        result = dict(
            hookSpecificOutput=dict(
                hookEventName="PreToolUse",
                permissionDecision="deny",
                permissionDecisionReason=REASON
            )
        )
        print(json.dumps(result))


main()
