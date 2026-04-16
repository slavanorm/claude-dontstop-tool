import json

from claude_hook import is_binary, handle_ask, handle_prompt


class TestBinary:
    def test_two_options(self):
        q = [dict(question="pick", options=[dict(label="a"), dict(label="b")])]
        assert is_binary(q)

    def test_three_options(self):
        q = [dict(question="pick", options=[dict(label="a"), dict(label="b"), dict(label="c")])]
        assert not is_binary(q)

    def test_pattern_match(self):
        q = [dict(question="Should I proceed?", options=[dict(label="a"), dict(label="b"), dict(label="c")])]
        assert is_binary(q)

    def test_no_pattern(self):
        q = [dict(question="Which color?", options=[dict(label="a"), dict(label="b"), dict(label="c")])]
        assert not is_binary(q)


class TestHandleAsk:
    def test_denies_binary(self):
        payload = dict(tool_input=dict(questions=[
            dict(question="yes or no?", options=[dict(label="yes"), dict(label="no")])
        ]))
        r = handle_ask(payload)
        assert r["hookSpecificOutput"]["permissionDecision"] == "deny"

    def test_allows_non_binary(self):
        payload = dict(tool_input=dict(questions=[
            dict(question="Which color?", options=[dict(label="a"), dict(label="b"), dict(label="c")])
        ]))
        r = handle_ask(payload)
        assert r == {}


class TestHandlePrompt:
    def test_volume(self, tmp_path, monkeypatch):
        from claude_hook import sound
        vol = tmp_path / "vol"
        monkeypatch.setattr(sound, "VOLUME_FILE", vol)
        handle_prompt(dict(prompt="/volume 5"))
        assert vol.read_text() == "5"

    def test_todo_passthrough(self, tmp_path, monkeypatch):
        from claude_hook import todo
        monkeypatch.setattr(todo, "TASKS_DIR", tmp_path / "tasks")
        monkeypatch.setattr(todo, "TODOS_DIR", tmp_path / "todos")
        r = handle_prompt(dict(prompt="todo milk", session_id="s"))
        assert r["decision"] == "block"

    def test_normal_passthrough(self):
        r = handle_prompt(dict(prompt="hello world"))
        assert r == {}
