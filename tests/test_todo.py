import json
import shutil
from pathlib import Path

import pytest

from claude_hook import todo


@pytest.fixture
def session(tmp_path, monkeypatch):
    monkeypatch.setattr(todo, "TASKS_DIR", tmp_path / "tasks")
    monkeypatch.setattr(todo, "TODOS_DIR", tmp_path / "todos")
    monkeypatch.setattr(todo, "EDIT_FILE", tmp_path / "todo.edit")
    return "test-session"


# --- parse ---

class TestParse:
    def test_list(self):
        assert todo.parse("todo") == dict(action="list")
        assert todo.parse("Todo") == dict(action="list")

    def test_add(self):
        assert todo.parse("todo buy milk") == dict(action="add", priority=0, subject="buy milk")

    def test_add_priority(self):
        assert todo.parse("todo 3 fix auth") == dict(action="add", priority=3, subject="fix auth")

    def test_done(self):
        assert todo.parse("todo 2") == dict(action="done", id=2)

    def test_done_all(self):
        assert todo.parse("todo all") == dict(action="done_all")

    def test_undo(self):
        assert todo.parse("todo u3") == dict(action="undo", id=3)
        assert todo.parse("todo u 3") == dict(action="undo", id=3)

    def test_reword(self):
        assert todo.parse("todo r2 new text") == dict(action="reword", id=2, subject="new text")
        assert todo.parse("todo r 2 new text") == dict(action="reword", id=2, subject="new text")

    def test_edit(self):
        assert todo.parse("todo vi") == dict(action="edit")
        assert todo.parse("todo e") == dict(action="edit")

    def test_sync(self):
        assert todo.parse("todo sync") == dict(action="sync")

    def test_no_match(self):
        assert todo.parse("hello") is None
        assert todo.parse("my todo list") is None


# --- storage ---

class TestStorage:
    def test_add_and_read(self, session):
        todo.add(session, "buy milk", 0)
        tasks = todo.read(session)
        assert len(tasks) == 1
        assert tasks[0]["subject"] == "buy milk"
        assert tasks[0]["status"] == "pending"

    def test_complete(self, session):
        todo.add(session, "task one", 0)
        result = todo.complete(session, 1)
        assert result == "task one"
        assert todo.read(session)[0]["status"] == "completed"

    def test_complete_missing(self, session):
        assert todo.complete(session, 99) is None

    def test_undo(self, session):
        todo.add(session, "task one", 0)
        todo.complete(session, 1)
        todo.undo(session, 1)
        assert todo.read(session)[0]["status"] == "pending"

    def test_reword(self, session):
        todo.add(session, "old text", 0)
        todo.reword(session, 1, "new text")
        assert todo.read(session)[0]["subject"] == "new text"

    def test_next_id(self, session):
        assert todo.next_id(session) == 1
        todo.add(session, "a", 0)
        assert todo.next_id(session) == 2
        todo.add(session, "b", 0)
        assert todo.next_id(session) == 3


# --- text roundtrip ---

class TestText:
    def test_roundtrip_flat(self, session):
        todo.add(session, "one", 0)
        todo.add(session, "two", 0)
        todo.complete(session, 1)
        tasks = todo.read(session)
        text = todo.to_text(tasks)
        assert "[x] #1 one" in text
        assert "[ ] #2 two" in text
        existing = {t["id"]: t for t in tasks}
        back = todo.from_text(text, existing)
        assert len(back) == 2
        assert back[0]["status"] == "completed"
        assert back[1]["status"] == "pending"

    def test_roundtrip_nested(self):
        text = "[ ] #1 parent\n  [ ] #2 child\n    [ ] #3 grandchild\n"
        tasks = todo.from_text(text, {})
        assert tasks[0]["blockedBy"] == []
        assert tasks[1]["blockedBy"] == ["1"]
        assert tasks[2]["blockedBy"] == ["2"]
        rendered = todo.to_text(tasks)
        assert "  [ ] #2 child" in rendered
        assert "    [ ] #3 grandchild" in rendered

    def test_siblings(self):
        text = "[ ] #1 parent\n  [ ] #2 a\n  [ ] #3 b\n"
        tasks = todo.from_text(text, {})
        assert tasks[1]["blockedBy"] == ["1"]
        assert tasks[2]["blockedBy"] == ["1"]

    def test_comments_skipped(self):
        text = "# comment\n[ ] #1 task\n# another\n"
        tasks = todo.from_text(text, {})
        assert len(tasks) == 1


# --- edit / sync ---

class TestEditSync:
    def test_edit_creates_file(self, session):
        todo.add(session, "task", 0)
        msg = todo.edit(session)
        assert todo.EDIT_FILE.exists()
        content = todo.EDIT_FILE.read_text()
        assert "[ ] #1 task" in content

    def test_sync_reads_back(self, session):
        todo.add(session, "old", 0)
        todo.edit(session)
        todo.EDIT_FILE.write_text("[x] #1 renamed\n[ ] #2 new task\n")
        msg = todo.sync_edit(session)
        assert "synced 2" in msg
        tasks = todo.read(session)
        assert tasks[0]["subject"] == "renamed"
        assert tasks[0]["status"] == "completed"
        assert tasks[1]["subject"] == "new task"
        assert not todo.EDIT_FILE.exists()

    def test_sync_no_file(self, session):
        msg = todo.sync_edit(session)
        assert "no edit file" in msg


# --- handle (integration) ---

class TestHandle:
    def test_add(self, session):
        r = todo.handle(dict(prompt="todo buy milk", session_id=session))
        assert r["decision"] == "block"
        assert "buy milk" in r["reason"]
        assert len(todo.read(session)) == 1

    def test_done(self, session):
        todo.add(session, "task", 0)
        r = todo.handle(dict(prompt="todo 1", session_id=session))
        assert "done #1" in r["reason"]

    def test_done_all(self, session):
        todo.add(session, "a", 0)
        todo.add(session, "b", 0)
        r = todo.handle(dict(prompt="todo all", session_id=session))
        assert "done all (2" in r["reason"]

    def test_undo(self, session):
        todo.add(session, "task", 0)
        todo.complete(session, 1)
        r = todo.handle(dict(prompt="todo u1", session_id=session))
        assert "undone #1" in r["reason"]

    def test_reword(self, session):
        todo.add(session, "old", 0)
        r = todo.handle(dict(prompt="todo r1 new", session_id=session))
        assert "→ new" in r["reason"]

    def test_list(self, session):
        r = todo.handle(dict(prompt="todo", session_id=session))
        assert r["decision"] == "block"

    def test_no_match(self, session):
        r = todo.handle(dict(prompt="hello", session_id=session))
        assert r is None

    def test_syncs_todos_file(self, session):
        todo.handle(dict(prompt="todo milk", session_id=session))
        path = todo.TODOS_DIR / f"{session}-agent-{session}.json"
        assert path.exists()
        data = json.loads(path.read_text())
        assert data[0]["content"] == "milk"
