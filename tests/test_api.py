from pathlib import Path

from fastapi.testclient import TestClient

from mordecai.config import get_settings
from mordecai.main import build_runtime, create_app
from mordecai_core.runtime import get_runtime_components


def build_test_client(tmp_path, monkeypatch):
    monkeypatch.setenv("MORDECAI_WORKSPACE_DIR", str(tmp_path))
    monkeypatch.setenv("MORDECAI_STATE_DIR", str(tmp_path / ".mordecai-test"))
    monkeypatch.setenv("MORDECAI_SYSTEM_PROMPT_PATH", str(tmp_path / "prompt.txt"))
    (tmp_path / "prompt.txt").write_text("Test prompt", encoding="utf-8")
    get_settings.cache_clear()
    build_runtime.cache_clear()
    get_runtime_components.cache_clear()
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
    get_runtime_components.cache_clear()
    client = TestClient(create_app())

    response = client.post("/api/chat", json={"message": "Hello"})

    assert response.status_code == 403
    assert response.json()["detail"]["error"]["code"] == "PermissionDenied"
    assert "allowlist" in response.json()["detail"]["error"]["message"]


def test_events_and_proxy_logs_endpoints(tmp_path, monkeypatch):
    client = build_test_client(tmp_path, monkeypatch)

    client.post("/api/chat", json={"message": "github search fastapi"})
    events_response = client.get("/api/events")
    proxy_response = client.get("/api/proxy/logs")

    assert events_response.status_code == 200
    assert proxy_response.status_code == 200
    assert any(event["category"] == "proxy" for event in events_response.json())
    assert proxy_response.json()


def test_runtime_trace_and_capabilities_endpoints(tmp_path, monkeypatch):
    client = build_test_client(tmp_path, monkeypatch)

    client.post("/api/chat", json={"message": "Status report, Mordecai."})
    trace_response = client.get("/api/runtime/trace")
    capabilities_response = client.get("/api/runtime/capabilities")

    assert trace_response.status_code == 200
    assert capabilities_response.status_code == 200
    trace_payload = trace_response.json()
    capabilities_payload = capabilities_response.json()
    assert "events" in trace_payload
    assert any(event["name"].startswith("provider.") for event in trace_payload["events"])
    assert "providers" in capabilities_payload
    assert "openai-compatible" in capabilities_payload["providers"]
    assert any(tool["tool"] == "filesystem.write" for tool in capabilities_payload["tools"])


def test_tool_execution_endpoint_runs_registered_tool(tmp_path, monkeypatch):
    client = build_test_client(tmp_path, monkeypatch)

    response = client.post(
        "/api/tools/execute",
        json={
            "tool": "git.status",
            "granted_permissions": ["git"],
            "arguments": {},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["tool_name"] == "git.status"
    assert isinstance(payload["output"], dict)


def test_tool_execution_endpoint_returns_structured_failure(tmp_path, monkeypatch):
    client = build_test_client(tmp_path, monkeypatch)

    response = client.post(
        "/api/tools/execute",
        json={
            "tool": "android.control",
            "granted_permissions": ["android-control"],
            "arguments": {"action": "tap", "arguments": ["1", "2"]},
        },
    )

    assert response.status_code == 403
    error = response.json()["detail"]["error"]
    assert error["code"] == "PermissionDenied"
    assert "execution_id" in error["details"]


def test_runtime_trace_includes_persisted_tool_execution_history(tmp_path, monkeypatch):
    client = build_test_client(tmp_path, monkeypatch)

    execute_response = client.post(
        "/api/tools/execute",
        json={
            "tool": "git.status",
            "granted_permissions": ["git"],
            "arguments": {},
        },
    )
    trace_response = client.get("/api/runtime/trace")

    assert execute_response.status_code == 200
    assert trace_response.status_code == 200
    executions = trace_response.json()["executions"]
    assert executions
    assert executions[-1]["tool_name"] == "git.status"
    assert executions[-1]["status"] == "completed"
