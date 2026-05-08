from pathlib import Path

from fastapi.testclient import TestClient

from mordecai.config import get_settings
from mordecai.main import build_runtime, create_app


def build_test_client(tmp_path, monkeypatch):
    monkeypatch.setenv("MORDECAI_WORKSPACE_DIR", str(tmp_path))
    monkeypatch.setenv("MORDECAI_STATE_DIR", str(tmp_path / ".mordecai-test"))
    monkeypatch.setenv("MORDECAI_SYSTEM_PROMPT_PATH", str(tmp_path / "prompt.txt"))
    (tmp_path / "prompt.txt").write_text("Test prompt", encoding="utf-8")
    get_settings.cache_clear()
    build_runtime.cache_clear()
    return TestClient(create_app())


def test_health_endpoint(tmp_path, monkeypatch):
    client = build_test_client(tmp_path, monkeypatch)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_chat_and_status_endpoints(tmp_path, monkeypatch):
    client = build_test_client(tmp_path, monkeypatch)

    chat_response = client.post("/api/chat", json={"message": "Status report, Mordecai."})
    status_response = client.get("/api/status")

    assert chat_response.status_code == 200
    assert "Mordecai" in chat_response.json()["reply"] or "stable" in chat_response.json()["reply"]
    assert status_response.status_code == 200
    assert status_response.json()["app_name"] == "Mordecai"


def test_improvement_candidate_blocks_protected_paths(tmp_path, monkeypatch):
    client = build_test_client(tmp_path, monkeypatch)
    protected = Path("src/mordecai/policy.py").as_posix()

    response = client.post(
        "/api/improvement/propose",
        json={
            "description": "Attempt forbidden change",
            "changes": [{"path": protected, "content": "print('forbidden')"}],
            "run_tests": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert protected in payload["protected_paths_blocked"]


def test_openai_compatible_provider_requires_allowlisted_host(tmp_path, monkeypatch):
    client = build_test_client(tmp_path, monkeypatch)
    monkeypatch.setenv("MORDECAI_OPENAI_BASE_URL", "https://example.com/v1")
    monkeypatch.setenv("MORDECAI_OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("MORDECAI_OPENAI_MODEL", "gpt-test")
    get_settings.cache_clear()
    build_runtime.cache_clear()
    client = TestClient(create_app())

    response = client.post("/api/chat", json={"message": "Hello"})

    assert response.status_code == 400
    assert "allowlist" in response.json()["detail"]


def test_events_and_proxy_logs_endpoints(tmp_path, monkeypatch):
    client = build_test_client(tmp_path, monkeypatch)

    client.post("/api/chat", json={"message": "github search fastapi"})
    events_response = client.get("/api/events")
    proxy_response = client.get("/api/proxy/logs")

    assert events_response.status_code == 200
    assert proxy_response.status_code == 200
    assert any(event["category"] == "proxy" for event in events_response.json())
    assert proxy_response.json()
