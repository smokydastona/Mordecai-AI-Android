from pathlib import Path

from mordecai.store import ConversationEntry, StateStore, StateStoreError
from mordecai.models import AgentPlanRecord, AndroidPerceptionSnapshot, MemoryRecord, VoiceSessionRecord


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


def test_state_store_searches_structured_memory(tmp_path):
    store = StateStore(tmp_path / ".mordecai", 10)
    store.save_memory(
        MemoryRecord(
            memory_id="pref-1",
            category="preference",
            content="User prefers anti-cheat-safe solutions for controller tooling.",
            tags=["anti-cheat", "controller", "tooling"],
            importance=5,
            pinned=True,
        )
    )
    store.save_memory(
        MemoryRecord(
            memory_id="proj-1",
            category="project",
            content="User was debugging ESP32 firmware flashing failures yesterday.",
            tags=["esp32", "firmware", "debugging"],
            importance=3,
        )
    )

    results = store.search_memories("Need anti-cheat-safe help for controller debugging", limit=2)

    assert len(results) == 2
    assert results[0].record.memory_id == "pref-1"
    assert results[0].score > results[1].score


def test_state_store_persists_perception_and_voice_sessions(tmp_path):
    store = StateStore(tmp_path / ".mordecai", 10)
    snapshot = AndroidPerceptionSnapshot(snapshot_id="snap-1", source="test", app_package="com.termux", visible_text=["Mordecai Console"])
    session = VoiceSessionRecord(session_id="voice-1", status="speaking", last_response="ready")

    store.save_perception_snapshot(snapshot)
    store.save_voice_session(session)

    assert store.latest_perception() is not None
    assert store.latest_perception().app_package == "com.termux"
    assert store.get_voice_session("voice-1") is not None
    assert store.get_voice_session("voice-1").status == "speaking"


def test_state_store_persists_plan_history(tmp_path):
    store = StateStore(tmp_path / ".mordecai", 10)
    record = AgentPlanRecord(plan_id="plan-1", session_id="sess-1", goal="Open notifications", executed=True, final_response="done")

    store.save_plan(record)

    assert store.get_plan("plan-1") is not None
    assert store.get_plan("plan-1").goal == "Open notifications"