from pathlib import Path

from mordecai.store import ConversationEntry, StateStore, StateStoreError


def test_state_store_raises_on_corrupt_state_file(tmp_path):
    store = StateStore(tmp_path / ".mordecai", 10)
    conversation_path = store._conversation_path
    conversation_path.write_text("{not-json", encoding="utf-8")

    try:
        store.read_conversation()
    except StateStoreError as exc:
        assert "corrupt" in str(exc)
        assert conversation_path.name in str(exc)
    else:
        raise AssertionError("Expected corrupt state file to raise StateStoreError")


def test_state_store_raises_when_save_fails(tmp_path, monkeypatch):
    store = StateStore(tmp_path / ".mordecai", 10)

    def fail_replace(self: Path, target: Path) -> Path:
        raise PermissionError("denied")

    monkeypatch.setattr(Path, "replace", fail_replace)

    try:
        store.append_conversation(ConversationEntry(role="user", content="hello"))
    except StateStoreError as exc:
        assert "Failed to save" in str(exc)
        assert "conversation.json" in str(exc)
    else:
        raise AssertionError("Expected save failure to raise StateStoreError")