from mordecai.config import Settings


def test_settings_derive_phase1_layout_from_backend_workspace(tmp_path):
    backend_dir = tmp_path / "backend"
    backend_dir.mkdir()

    settings = Settings(workspace_dir=backend_dir)

    assert settings.install_root == tmp_path.resolve()
    assert settings.data_dir == (tmp_path / "data").resolve()
    assert settings.state_dir == (tmp_path / "data" / "state").resolve()
    assert settings.log_dir == (tmp_path / "data" / "logs").resolve()
    assert settings.cache_dir == (tmp_path / "data" / "cache").resolve()
    assert settings.models_dir == (tmp_path / "data" / "models").resolve()


def test_settings_preserve_custom_state_dir_when_provided(tmp_path):
    custom_state = tmp_path / "custom-state"

    settings = Settings(workspace_dir=tmp_path, state_dir=custom_state)

    assert settings.state_dir == custom_state.resolve()
    assert settings.data_dir == custom_state.resolve()