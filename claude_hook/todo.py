import json
import re
from pathlib import Path

TASKS_DIR = Path.home() / ".claude" / "tasks"
TODOS_DIR = Path.home() / ".claude" / "todos"
EDIT_FILE = Path.home() / ".claude" / "todo.edit"

FOOTER = """\




#
# [x] done  [ ] pending  delete line = remove
#
# nesting (indent = child of above):
# [ ] #10 build auth
#   [ ] #11 login page
#   [ ] #12 signup page
#     [ ] #13 email validation
#   [ ] #14 deploy
"""


def parse(text: str) -> dict | None:
    m = re.match(r'todo(?:\s+(.*))?$', text.strip(), re.DOTALL | re.IGNORECASE)
    if not m:
        return None
    body = (m.group(1) or '').strip()
    if not body:
        return dict(action="list")
    if body.lower() == 'all':
        return dict(action="done_all")
    dm = re.match(r'^(\d+)$', body)
    if dm:
        return dict(action="done", id=int(dm.group(1)))
    um = re.match(r'^u\s*(\d+)$', body, re.IGNORECASE)
    if um:
        return dict(action="undo", id=int(um.group(1)))
    rm = re.match(r'^r\s*(\d+)\s+(.+)$', body, re.DOTALL | re.IGNORECASE)
    if rm:
        return dict(action="reword", id=int(rm.group(1)), subject=rm.group(2).strip())
    if body.lower() in ('vi', 'vim', 'edit', 'e'):
        return dict(action="edit")
    if body.lower() == 'sync':
        return dict(action="sync")
    pm = re.match(r'^(\d+)\s+(.+)$', body, re.DOTALL)
    if pm:
        return dict(action="add", priority=int(pm.group(1)), subject=pm.group(2).strip())
    return dict(action="add", priority=0, subject=body)


# --- storage ---

def tasks_dir(session: str) -> Path:
    return TASKS_DIR / session


def read(session: str) -> list:
    d = tasks_dir(session)
    if not d.exists():
        return []
    tasks = []
    for f in sorted(d.glob("*.json"), key=lambda p: int(p.stem)):
        tasks.append(json.loads(f.read_text()))
    return tasks


def next_id(session: str) -> int:
    d = tasks_dir(session)
    if not d.exists():
        return 1
    ids = [int(f.stem) for f in d.glob("*.json")]
    return max(ids, default=0) + 1


def add(session: str, subject: str, priority: int):
    d = tasks_dir(session)
    d.mkdir(parents=True, exist_ok=True)
    tid = next_id(session)
    word = subject.split()[0]
    rest = " ".join(subject.split()[1:])
    active = word.capitalize() + "ing"
    if rest:
        active += " " + rest
    task = dict(
        id=str(tid),
        subject=subject,
        description="",
        activeForm=active,
        status="pending",
        blocks=[],
        blockedBy=[],
    )
    (d / f"{tid}.json").write_text(json.dumps(task, indent=2))


def set_status(session: str, tid: int, status: str) -> str | None:
    f = tasks_dir(session) / f"{tid}.json"
    if not f.exists():
        return None
    task = json.loads(f.read_text())
    task["status"] = status
    f.write_text(json.dumps(task, indent=2))
    return task["subject"]


def complete(session: str, tid: int) -> str | None:
    return set_status(session, tid, "completed")


def undo(session: str, tid: int) -> str | None:
    return set_status(session, tid, "pending")


def reword(session: str, tid: int, subject: str) -> str | None:
    f = tasks_dir(session) / f"{tid}.json"
    if not f.exists():
        return None
    task = json.loads(f.read_text())
    task["subject"] = subject
    f.write_text(json.dumps(task, indent=2))
    return subject


def sync_todos(session: str):
    """Mirror tasks/ → todos/ so /todos command sees them."""
    tasks = read(session)
    TODOS_DIR.mkdir(parents=True, exist_ok=True)
    path = TODOS_DIR / f"{session}-agent-{session}.json"
    todos = [dict(content=t["subject"], status=t["status"], activeForm=t.get("activeForm", "")) for t in tasks]
    path.write_text(json.dumps(todos, indent=2))


# --- text format for vi editing ---

def to_text(tasks: list) -> str:
    parents = {}
    for t in tasks:
        if t.get("blockedBy"):
            parents[t["id"]] = t["blockedBy"][0]

    def depth(tid: str) -> int:
        if tid not in parents:
            return 0
        return 1 + depth(parents[tid])

    lines = []
    for t in tasks:
        mark = "x" if t["status"] == "completed" else " "
        indent = "  " * depth(t["id"])
        lines.append(f"{indent}[{mark}] #{t['id']} {t['subject']}")
    lines.append(FOOTER)
    return "\n".join(lines) + "\n"


def from_text(text: str, existing: dict) -> list:
    tasks = []
    stack = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        m = re.match(r'^(\s*)\[([x ])\]\s*#?(\d+)\s+(.+?)$', line)
        if not m:
            continue
        indent = len(m.group(1))
        done = m.group(2) == 'x'
        tid = m.group(3)
        subject = m.group(4).strip()
        while stack and stack[-1][0] >= indent:
            stack.pop()
        blocked = [stack[-1][1]] if stack else []
        stack.append((indent, tid))
        old = existing.get(tid, {})
        tasks.append(dict(
            id=tid,
            subject=subject,
            description=old.get("description", ""),
            activeForm=old.get("activeForm", ""),
            status="completed" if done else "pending",
            blocks=old.get("blocks", []),
            blockedBy=blocked,
        ))
    return tasks


def edit(session: str) -> str:
    d = tasks_dir(session)
    d.mkdir(parents=True, exist_ok=True)
    tasks = read(session)
    text = to_text(tasks) if tasks else "[ ] #1 example task\n"
    EDIT_FILE.write_text(text)
    return f"Ctrl+Z → nvim {EDIT_FILE} → fg → todo sync"


def sync_edit(session: str) -> str:
    if not EDIT_FILE.exists():
        return "no edit file. run todo vi first"
    tasks = read(session)
    existing = {t["id"]: t for t in tasks}
    edited = EDIT_FILE.read_text()
    updated = from_text(edited, existing)
    d = tasks_dir(session)
    for f in d.glob("*.json"):
        f.unlink()
    for t in updated:
        (d / f"{t['id']}.json").write_text(json.dumps(t, indent=2))
    EDIT_FILE.unlink()
    return f"synced {len(updated)} tasks"


# --- handler ---

def handle(payload: dict) -> dict | None:
    prompt = payload.get('prompt', '').strip()
    parsed = parse(prompt)
    if not parsed:
        return None
    session = payload.get('session_id', '')

    def done(reason: str) -> dict:
        sync_todos(session)
        return dict(decision="block", reason=reason)

    if parsed["action"] == "edit":
        return done(edit(session))
    if parsed["action"] == "sync":
        return done(sync_edit(session))
    if parsed["action"] == "done_all":
        tasks = read(session)
        n = 0
        for t in tasks:
            if t["status"] != "completed":
                complete(session, int(t["id"]))
                n += 1
        return done(f"✓ done all ({n} tasks)")
    if parsed["action"] == "done":
        subject = complete(session, parsed["id"])
        if not subject:
            return done(f"No task #{parsed['id']}")
        return done(f"✓ done #{parsed['id']} {subject}")
    if parsed["action"] == "undo":
        subject = undo(session, parsed["id"])
        if not subject:
            return done(f"No task #{parsed['id']}")
        return done(f"○ undone #{parsed['id']} {subject}")
    if parsed["action"] == "reword":
        subject = reword(session, parsed["id"], parsed["subject"])
        if not subject:
            return done(f"No task #{parsed['id']}")
        return done(f"✎ #{parsed['id']} → {parsed['subject']}")
    if parsed["action"] == "list":
        return done("")
    add(session, parsed["subject"], parsed["priority"])
    return done(f"✓ [P{parsed['priority']}] {parsed['subject']}")
