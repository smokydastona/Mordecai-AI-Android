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
        if path.endswith("Qwen2.5-3B-Instruct-Q4_K_M.gguf"):
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
