from pathlib import Path
import subprocess
import tarfile

import httpx
from fastapi.testclient import TestClient

from mordecai.config import get_settings
from mordecai.main import build_runtime, create_app
from mordecai.avatar import list_avatar_emotions
from mordecai.local_models import LocalModelService
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


def test_dashboard_alias_endpoint(tmp_path, monkeypatch):
    client = build_test_client(tmp_path, monkeypatch)

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "Mordecai Console" in response.text


def test_dashboard_renders_bundle_details_and_approval_toggle(tmp_path, monkeypatch):
    client = build_test_client(tmp_path, monkeypatch)

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert 'id="model-bundle-details"' in response.text
    assert 'id="model-acknowledge-approval"' in response.text
    assert "selectedBundle.requires_operator_approval" in response.text
    assert "approvalSelect.disabled = true;" in response.text
    assert 'id="voice-transcribe-provider"' in response.text
    assert "fetch('/api/voice/transcribe'" in response.text
    assert 'id="perception-latest"' in response.text
    assert 'id="planner-goal"' in response.text
    assert 'id="planner-history"' in response.text
    assert 'id="planner-history-select"' in response.text
    assert 'id="planner-history-detail"' in response.text
    assert "fetch(`/api/agent/plans/${selectedPlanId}`)" in response.text
    assert 'id="voice-session-select"' in response.text
    assert 'id="avatar-frame"' in response.text
    assert 'id="avatar-meta"' in response.text


def test_chat_and_status_endpoints(tmp_path, monkeypatch):
    client = build_test_client(tmp_path, monkeypatch)

    chat_response = client.post("/api/chat", json={"message": "Status report, Mordecai."})
    status_response = client.get("/api/status")

    assert chat_response.status_code == 200
    assert "Mordecai" in chat_response.json()["reply"] or "stable" in chat_response.json()["reply"]
    assert status_response.status_code == 200
    assert status_response.json()["app_name"] == "Mordecai"
    assert "avatar_emotion" in status_response.json()
    assert "active_goals" in status_response.json()
    assert "active_routines" in status_response.json()


def test_goals_and_routines_endpoints_persist_records(tmp_path, monkeypatch):
    client = build_test_client(tmp_path, monkeypatch)

    goal_response = client.post(
        "/api/goals",
        json={"title": "Protect the runtime", "description": "Keep safety boundaries intact.", "priority": "high"},
    )
    routine_response = client.post(
        "/api/routines",
        json={"title": "Morning status", "description": "Check local backend each morning.", "trigger": "time:08:00", "enabled": True},
    )
    goals_response = client.get("/api/goals")
    routines_response = client.get("/api/routines")

    assert goal_response.status_code == 200
    assert routine_response.status_code == 200
    assert goals_response.status_code == 200
    assert routines_response.status_code == 200
    assert goals_response.json()[0]["title"] == "Protect the runtime"
    assert routines_response.json()[0]["trigger"] == "time:08:00"


def test_memory_record_endpoints_persist_and_search_context(tmp_path, monkeypatch):
    client = build_test_client(tmp_path, monkeypatch)

    create_response = client.post(
        "/api/memory/records",
        json={
            "category": "preference",
            "content": "Prefer anti-cheat-safe solutions when discussing controller tooling.",
            "tags": ["anti-cheat", "controller"],
            "importance": 5,
            "pinned": True,
        },
    )
    list_response = client.get("/api/memory/records")
    search_response = client.post(
        "/api/memory/search",
        json={"query": "controller anti-cheat guidance", "limit": 3},
    )

    assert create_response.status_code == 200
    assert list_response.status_code == 200
    assert search_response.status_code == 200
    assert list_response.json()[0]["category"] == "preference"
    assert search_response.json()[0]["record"]["pinned"] is True
    assert "anti-cheat-safe" in search_response.json()[0]["record"]["content"]


def test_chat_persists_project_memory_for_future_retrieval(tmp_path, monkeypatch):
    client = build_test_client(tmp_path, monkeypatch)

    response = client.post("/api/chat", json={"message": "I am working on ESP32 joycon mappings and debugging firmware flashing issues."})
    search_response = client.post("/api/memory/search", json={"query": "esp32 firmware", "limit": 5})

    assert response.status_code == 200
    assert search_response.status_code == 200
    assert any(item["record"]["category"] == "project" for item in search_response.json())


def test_android_perception_ingest_parses_ui_dump_and_exposes_latest_snapshot(tmp_path, monkeypatch):
    client = build_test_client(tmp_path, monkeypatch)
    xml = """
    <hierarchy>
      <node package="com.termux" class="android.widget.TextView" text="Mordecai Console" clickable="false" enabled="true" />
      <node package="com.termux" class="android.widget.Button" text="Run" clickable="true" enabled="true" resource-id="com.termux:id/run" />
    </hierarchy>
    """

    ingest_response = client.post(
        "/api/android/perception",
        json={"activity": "TermuxActivity", "ui_dump_xml": xml, "notification_summaries": ["Build finished"]},
    )
    latest_response = client.get("/api/android/perception/latest")

    assert ingest_response.status_code == 200
    assert latest_response.status_code == 200
    payload = latest_response.json()
    assert payload["app_package"] == "com.termux"
    assert "Mordecai Console" in payload["visible_text"]
    assert "Run" in payload["action_labels"]


def test_android_perception_ingest_accepts_notification_actions_and_focused_node(tmp_path, monkeypatch):
    client = build_test_client(tmp_path, monkeypatch)

    response = client.post(
        "/api/android/perception",
        json={
            "app_package": "com.android.systemui",
            "focused_text": "Reply",
            "focused_node": {
                "text": "Reply",
                "resource_id": "android:id/reply",
                "class_name": "android.widget.Button",
                "clickable": True,
                "enabled": True,
                "bounds": "[0,0][100,40]"
            },
            "notification_actions": [
                {"title": "Reply", "action_type": "notification-action"},
                {"title": "Archive", "action_type": "notification-action"}
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["focused_node"]["resource_id"] == "android:id/reply"
    assert payload["notification_actions"][0]["title"] == "Reply"


def test_agent_plan_uses_perception_to_retrieve_relevant_memory_and_execute_git_status(tmp_path, monkeypatch):
    client = build_test_client(tmp_path, monkeypatch)

    memory_response = client.post(
        "/api/memory/records",
        json={
            "category": "project",
            "content": "Termux is used for backend control and local runtime debugging.",
            "tags": ["termux", "debugging"],
            "importance": 4,
        },
    )
    assert memory_response.status_code == 200

    perception_response = client.post(
        "/api/android/perception",
        json={"app_package": "com.termux", "screen_title": "Mordecai Console", "visible_text": ["Terminal", "Mordecai Console"]},
    )
    assert perception_response.status_code == 200

    plan_response = client.post(
        "/api/agent/plan",
        json={"goal": "Check git status for the current screen workflow", "auto_execute": True, "granted_permissions": ["git"], "safe_mode": True},
    )

    assert plan_response.status_code == 200
    payload = plan_response.json()
    assert payload["perception"]["app_package"] == "com.termux"
    assert any("Termux" in item["record"]["content"] for item in payload["memory_hits"])
    assert any(step["tool_name"] == "git.status" and step["status"] == "completed" for step in payload["steps"])


def test_agent_plan_includes_android_notification_workflow_when_android_control_is_enabled(tmp_path, monkeypatch):
    monkeypatch.setenv("MORDECAI_ENABLE_ANDROID_CONTROL", "true")
    client = build_test_client(tmp_path, monkeypatch)

    response = client.post(
        "/api/agent/plan",
        json={"goal": "Open notifications for the current app", "auto_execute": False},
    )

    assert response.status_code == 200
    payload = response.json()
    assert any(step["tool_name"] == "android.control" for step in payload["steps"])
    assert any(step["arguments"]["action"] == "show_notifications" for step in payload["steps"] if step["tool_name"] == "android.control")


def test_agent_plan_can_select_allowlisted_app_launch_action(tmp_path, monkeypatch):
    monkeypatch.setenv("MORDECAI_ENABLE_ANDROID_CONTROL", "true")
    client = build_test_client(tmp_path, monkeypatch)

    response = client.post(
        "/api/agent/plan",
        json={"goal": "Launch Termux so I can inspect the shell", "auto_execute": False},
    )

    assert response.status_code == 200
    payload = response.json()
    android_steps = [step for step in payload["steps"] if step["tool_name"] == "android.control"]
    assert any(step["arguments"]["action"] == "open_app" for step in android_steps)
    assert any(step["arguments"]["arguments"] == ["com.termux"] for step in android_steps)


def test_agent_plan_history_endpoint_returns_saved_plans(tmp_path, monkeypatch):
    client = build_test_client(tmp_path, monkeypatch)

    create_response = client.post(
        "/api/agent/plan",
        json={"goal": "Check git status", "auto_execute": False},
    )
    history_response = client.get("/api/agent/plans")

    assert create_response.status_code == 200
    assert history_response.status_code == 200
    assert any(item["goal"] == "Check git status" for item in history_response.json())


def test_voice_session_orchestration_handles_wake_word_command_and_interruptions(tmp_path, monkeypatch):
    client = build_test_client(tmp_path, monkeypatch)

    start_response = client.post("/api/voice/sessions", json={"label": "hands-free", "background": True})
    assert start_response.status_code == 200
    session_id = start_response.json()["session_id"]

    partial_response = client.post(
        f"/api/voice/sessions/{session_id}/events",
        json={"transcript": "Mordecai", "is_final": False},
    )
    assert partial_response.status_code == 200
    assert partial_response.json()["session"]["status"] == "listening-command"

    command_response = client.post(
        f"/api/voice/sessions/{session_id}/events",
        json={"transcript": "Mordecai show git status", "is_final": True, "granted_permissions": ["git"], "auto_execute": True},
    )

    assert command_response.status_code == 200
    command_payload = command_response.json()
    assert command_payload["wake_word_detected"] is True
    assert command_payload["session"]["status"] == "speaking"
    assert command_payload["plan"]["goal"] == "show git status"

    interrupt_response = client.post(
        f"/api/voice/sessions/{session_id}/events",
        json={"transcript": "Mordecai stop", "is_final": False, "interrupt": True},
    )

    assert interrupt_response.status_code == 200
    assert interrupt_response.json()["session"]["interrupted_count"] == 1


def test_avatar_endpoint_returns_immutable_frames(tmp_path, monkeypatch):
    client = build_test_client(tmp_path, monkeypatch)

    response = client.get("/api/avatar")

    assert response.status_code == 200
    payload = response.json()
    settings = get_settings()
    assert payload["immutable_assets"] is True
    assert payload["immutable_behavior"] is True
    assert payload["immutable_style"] is True
    assert len(payload["frames"]) == len(list_avatar_emotions(settings.avatar_assets_dir))
    assert any(frame["emotion"] == "wise-smirk" for frame in payload["frames"])
    assert any(frame["emotion"] == "unimpressed" for frame in payload["frames"])


def test_local_models_endpoint_returns_catalog(tmp_path, monkeypatch):
    client = build_test_client(tmp_path, monkeypatch)

    response = client.get("/api/local-models")

    assert response.status_code == 200
    payload = response.json()
    assert payload["configured_profiles"] >= 4
    assert any(profile["name"] == "whisper-cli" for profile in payload["profiles"])
    assert any(bundle["bundle_id"] == "phone-starter" for bundle in payload["bundles"])
    assert any(profile["name"] == "whisper.cpp-base-en" for profile in payload["profiles"])
    assert any(bundle["bundle_id"] == "voice-asr-whispercpp-phone" for bundle in payload["bundles"])


def test_runtime_contract_endpoints_return_provider_and_tool_manifests(tmp_path, monkeypatch):
    client = build_test_client(tmp_path, monkeypatch)

    provider_response = client.get("/api/runtime/provider-registry")
    tool_response = client.get("/api/runtime/tool-manifest")

    assert provider_response.status_code == 200
    assert tool_response.status_code == 200

    provider_payload = provider_response.json()
    tool_payload = tool_response.json()

    assert provider_payload["contract"] == "provider-registry"
    assert any(provider["name"] == "rule-based" for provider in provider_payload["providers"])
    assert tool_payload["contract"] == "tool-manifest"
    assert any(tool["tool"] == "git.status" and tool["provider"] == "core.git" for tool in tool_payload["tools"])
    assert any(tool["tool"] == "filesystem.read" and tool["default_timeout_seconds"] == 10.0 for tool in tool_payload["tools"])


def test_local_model_install_endpoint_downloads_bundle_assets(tmp_path, monkeypatch):
    client = build_test_client(tmp_path, monkeypatch)
    settings = get_settings()
    components = get_runtime_components()

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("qwen2.5-3b-instruct-q4_k_m.gguf"):
            return httpx.Response(200, content=b"qwen-bytes", request=request)
        if path.endswith("en_US-lessac-medium.onnx"):
            return httpx.Response(200, content=b"voice-bytes", request=request)
        if path.endswith("en_US-lessac-medium.onnx.json"):
            return httpx.Response(200, content=b'{"voice": true}', request=request)
        raise AssertionError(f"Unexpected request to {request.url}")

    client.app.state.local_models = LocalModelService(
        settings,
        proxy=type(components.proxy)(
            settings,
            components.policy,
            components.store,
            client_factory=lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False),
        ),
        store=components.store,
    )

    response = client.post("/api/local-models/install", json={"bundle_id": "phone-starter"})

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["installed_assets"]) == 3
    assert (settings.models_dir / "Qwen2.5-3B-Instruct-Q4_K_M.gguf").exists()
    assert (settings.models_dir / "en_US-lessac-medium.onnx").exists()
    assert (settings.models_dir / "en_US-lessac-medium.onnx.json").exists()


def test_phone_starter_qwen_asset_uses_public_official_repo():
    asset = next(asset for asset in LocalModelService.default_assets() if asset.asset_id == "qwen2.5-3b-instruct-q4km")

    assert asset.source_url == "https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf?download=true"


def test_local_model_install_endpoint_supports_whispercpp_voice_bundle(tmp_path, monkeypatch):
    client = build_test_client(tmp_path, monkeypatch)
    settings = get_settings()
    components = get_runtime_components()

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("ggml-base.en.bin"):
            return httpx.Response(200, content=b"whispercpp-model", request=request)
        if path.endswith("ggml-silero-v6.2.0.bin"):
            return httpx.Response(200, content=b"vad-model", request=request)
        raise AssertionError(f"Unexpected request to {request.url}")

    client.app.state.local_models = LocalModelService(
        settings,
        proxy=type(components.proxy)(
            settings,
            components.policy,
            components.store,
            client_factory=lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False),
        ),
        store=components.store,
    )

    response = client.post("/api/local-models/install", json={"bundle_id": "voice-asr-whispercpp-phone"})

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["installed_assets"]) == 2
    assert any(path.endswith("ggml-base.en.bin") for path in payload["extracted_paths"]) is False
    assert (settings.models_dir / "ggml-base.en.bin").exists()
    assert (settings.models_dir / "ggml-silero-v6.2.0.bin").exists()


def test_local_model_install_endpoint_requires_acknowledgement_for_gated_bundle(tmp_path, monkeypatch):
    client = build_test_client(tmp_path, monkeypatch)

    response = client.post("/api/local-models/install", json={"bundle_id": "voice-asr-sherpa-phone"})

    assert response.status_code == 403
    assert response.json()["detail"]["error"]["code"] == "PermissionDenied"


def test_local_model_install_endpoint_extracts_sherpa_archive(tmp_path, monkeypatch):
    client = build_test_client(tmp_path, monkeypatch)
    settings = get_settings()
    components = get_runtime_components()

    def build_archive_bytes() -> bytes:
        import io

        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:bz2") as archive:
            files = {
                "sherpa-onnx-whisper-tiny.en/tiny.en-encoder.int8.onnx": b"fake-encoder",
                "sherpa-onnx-whisper-tiny.en/tiny.en-decoder.int8.onnx": b"fake-decoder",
                "sherpa-onnx-whisper-tiny.en/tiny.en-tokens.txt": b"one\ntwo\n",
            }
            for name, content in files.items():
                info = tarfile.TarInfo(name=name)
                info.size = len(content)
                archive.addfile(info, io.BytesIO(content))
        return buffer.getvalue()

    archive_bytes = build_archive_bytes()

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("sherpa-onnx-whisper-tiny.en.tar.bz2"):
            return httpx.Response(200, content=archive_bytes, request=request)
        if path.endswith("silero_vad.onnx"):
            return httpx.Response(200, content=b"vad-onnx", request=request)
        raise AssertionError(f"Unexpected request to {request.url}")

    client.app.state.local_models = LocalModelService(
        settings,
        proxy=type(components.proxy)(
            settings,
            components.policy,
            components.store,
            client_factory=lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False),
        ),
        store=components.store,
    )

    response = client.post(
        "/api/local-models/install",
        json={"bundle_id": "voice-asr-sherpa-phone", "acknowledge_operator_approval": True},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["approval_acknowledged"] is True
    assert any(path.endswith("tiny.en-encoder.int8.onnx") for path in payload["extracted_paths"])
    assert any(path.endswith("mordecai-sherpa-manifest.json") for path in payload["extracted_paths"])
    assert any(path.endswith("mordecai-sherpa-setup.txt") for path in payload["extracted_paths"])


def test_voice_transcribe_endpoint_supports_whisper_cpp_provider(tmp_path, monkeypatch):
    client = build_test_client(tmp_path, monkeypatch)
    settings = get_settings()
    audio_path = settings.data_dir / "voice" / "sample.wav"
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    audio_path.write_bytes(b"WAVE")
    (settings.models_dir).mkdir(parents=True, exist_ok=True)
    (settings.models_dir / "ggml-base.en.bin").write_bytes(b"model")
    (settings.models_dir / "ggml-silero-v6.2.0.bin").write_bytes(b"vad")

    def fake_which(binary: str) -> str | None:
        if binary == "whisper-cli":
            return "C:/tools/whisper-cli.exe"
        return None

    def fake_run(command, *args, **kwargs):
        prefix = Path(command[command.index("-of") + 1])
        transcript = prefix.with_suffix(".txt")
        transcript.parent.mkdir(parents=True, exist_ok=True)
        transcript.write_text("whisper cpp text", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr("mordecai.voice.shutil.which", fake_which)
    monkeypatch.setattr("mordecai.voice.subprocess.run", fake_run)

    response = client.post(
        "/api/voice/transcribe",
        json={"audio_path": audio_path.as_posix(), "provider": "whisper.cpp"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["engine"] == "whisper.cpp"
    assert payload["provider"] == "whisper.cpp"
    assert payload["text"] == "whisper cpp text"


def test_voice_transcribe_endpoint_supports_sherpa_onnx_provider(tmp_path, monkeypatch):
    client = build_test_client(tmp_path, monkeypatch)
    settings = get_settings()
    audio_path = settings.data_dir / "voice" / "sample.wav"
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    audio_path.write_bytes(b"WAVE")
    sherpa_root = settings.models_dir / "sherpa-onnx-whisper-tiny.en"
    sherpa_root.mkdir(parents=True, exist_ok=True)
    encoder = sherpa_root / "tiny.en-encoder.int8.onnx"
    decoder = sherpa_root / "tiny.en-decoder.int8.onnx"
    tokens = sherpa_root / "tiny.en-tokens.txt"
    encoder.write_bytes(b"encoder")
    decoder.write_bytes(b"decoder")
    tokens.write_text("one\ntwo\n", encoding="utf-8")
    (sherpa_root / "mordecai-sherpa-manifest.json").write_text(
        """{
  "whisper_encoder": "%s",
  "whisper_decoder": "%s",
  "tokens": "%s"
}""" % (encoder.as_posix(), decoder.as_posix(), tokens.as_posix()),
        encoding="utf-8",
    )

    def fake_which(binary: str) -> str | None:
        if binary == "sherpa-onnx-offline":
            return "C:/tools/sherpa-onnx-offline.exe"
        return None

    def fake_run(command, *args, **kwargs):
        stdout = '{"text":"sherpa text"}\nElapsed seconds: 0.01\n'
        return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")

    monkeypatch.setattr("mordecai.voice.shutil.which", fake_which)
    monkeypatch.setattr("mordecai.voice.subprocess.run", fake_run)

    response = client.post(
        "/api/voice/transcribe",
        json={"audio_path": audio_path.as_posix(), "provider": "sherpa-onnx"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["engine"] == "sherpa-onnx"
    assert payload["provider"] == "sherpa-onnx"
    assert payload["text"] == "sherpa text"
    assert payload["transcript_path"].endswith("sample.sherpa-onnx.txt")


def test_voice_engines_endpoint_reports_binary_availability(tmp_path, monkeypatch):
    client = build_test_client(tmp_path, monkeypatch)

    def fake_which(binary: str) -> str | None:
        if binary == "piper":
            return "C:/tools/piper.exe"
        if binary == "whisper":
            return None
        return None

    monkeypatch.setattr("mordecai.voice.shutil.which", fake_which)
    response = client.get("/api/voice/engines")

    assert response.status_code == 200
    payload = response.json()
    assert payload["piper"]["available"] is True
    assert payload["whisper"]["available"] is False
    assert payload["catalog_summary"]["unique_repositories"] >= 100
    assert payload["recommended_stack"]["baseline_tts"] == "piper"


def test_voice_catalog_endpoint_returns_categorized_repository_index(tmp_path, monkeypatch):
    client = build_test_client(tmp_path, monkeypatch)

    response = client.get("/api/voice/catalog")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["unique_repositories"] >= 100
    assert payload["summary"]["runtime_supported"] >= 2
    assert payload["summary"]["approval_required"] >= 10
    assert any(category["id"] == "text-to-speech" for category in payload["categories"])
    assert any(repo["slug"] == "piper" and repo["supported_by_runtime"] for repo in payload["repos"])
    assert any(repo["slug"] == "whisper" and repo["supported_by_runtime"] for repo in payload["repos"])


def test_voice_catalog_endpoint_supports_filtering(tmp_path, monkeypatch):
    client = build_test_client(tmp_path, monkeypatch)

    response = client.get("/api/voice/catalog", params={"query": "whisper", "runtime_fit": "phone", "limit": 10})

    assert response.status_code == 200
    payload = response.json()
    assert payload["filters"]["query"] == "whisper"
    assert payload["summary"]["unique_repositories"] <= 10
    assert payload["repos"]
    assert all(repo["runtime_fit"] == "phone" for repo in payload["repos"])
    assert all("whisper" in " ".join([repo["slug"], repo["name"], repo["notes"]]).lower() for repo in payload["repos"])


def test_voice_synthesize_endpoint_generates_wav(tmp_path, monkeypatch):
    client = build_test_client(tmp_path, monkeypatch)
    settings = get_settings()
    model_path = settings.models_dir / "en_US-lessac-medium.onnx"
    config_path = settings.models_dir / "en_US-lessac-medium.onnx.json"
    model_path.parent.mkdir(parents=True, exist_ok=True)
    model_path.write_bytes(b"model")
    config_path.write_text("{}", encoding="utf-8")

    def fake_which(binary: str) -> str | None:
        if binary == "piper":
            return "C:/tools/piper.exe"
        return None

    def fake_run(command, *args, **kwargs):
        output_idx = command.index("--output_file") + 1
        output_path = Path(command[output_idx])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"RIFF....WAVE")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr("mordecai.voice.shutil.which", fake_which)
    monkeypatch.setattr("mordecai.voice.subprocess.run", fake_run)

    response = client.post("/api/voice/synthesize", json={"text": "Hello from Mordecai", "output_filename": "test-voice.wav"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["engine"] == "piper"
    assert payload["output_path"].endswith("test-voice.wav")
    assert Path(payload["output_path"]).exists()


def test_voice_transcribe_endpoint_reads_transcript(tmp_path, monkeypatch):
    client = build_test_client(tmp_path, monkeypatch)
    settings = get_settings()
    audio_path = settings.data_dir / "voice" / "sample.wav"
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    audio_path.write_bytes(b"WAVE")

    def fake_which(binary: str) -> str | None:
        if binary == "whisper":
            return "C:/tools/whisper.exe"
        return None

    def fake_run(command, *args, **kwargs):
        source = Path(command[1])
        output_dir = Path(command[command.index("--output_dir") + 1])
        transcript = output_dir / f"{source.stem}.txt"
        transcript.parent.mkdir(parents=True, exist_ok=True)
        transcript.write_text("transcribed text", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr("mordecai.voice.shutil.which", fake_which)
    monkeypatch.setattr("mordecai.voice.subprocess.run", fake_run)

    response = client.post("/api/voice/transcribe", json={"audio_path": audio_path.as_posix(), "model": "base"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["engine"] == "whisper"
    assert payload["text"] == "transcribed text"


def test_voice_synthesize_endpoint_returns_validation_failure_when_piper_missing(tmp_path, monkeypatch):
    client = build_test_client(tmp_path, monkeypatch)

    monkeypatch.setattr("mordecai.voice.shutil.which", lambda binary: None)
    response = client.post("/api/voice/synthesize", json={"text": "Hello"})

    assert response.status_code == 400
    assert response.json()["detail"]["error"]["code"] == "ExecutionFailed"


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


def test_improvement_apply_rejects_untested_candidate(tmp_path, monkeypatch):
    client = build_test_client(tmp_path, monkeypatch)

    propose_response = client.post(
        "/api/improvement/propose",
        json={
            "description": "Untested candidate",
            "changes": [{"path": "src/demo.py", "content": "VALUE = 2\n"}],
            "run_tests": False,
        },
    )

    candidate_id = propose_response.json()["candidate_id"]
    apply_response = client.post(f"/api/improvement/apply/{candidate_id}")

    assert propose_response.status_code == 200
    assert apply_response.status_code == 400
    error = apply_response.json()["detail"]["error"]
    assert error["code"] == "ExecutionFailed"
    assert "must pass before apply" in error["message"]


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
    assert any(profile["name"] == "ollama-local" for profile in capabilities_payload["local_models"])


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

    assert response.status_code == 404
    error = response.json()["detail"]["error"]
    assert error["code"] == "NotFound"
    assert "not available" in error["message"]


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
