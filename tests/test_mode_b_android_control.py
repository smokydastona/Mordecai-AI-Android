"""Tests for Mode B rooted shell automation and recovery state integration."""

import pytest
from unittest.mock import MagicMock, patch

from mordecai.android_control import AndroidController
from mordecai.config import Settings
from mordecai.policy import PolicyEngine, PolicyDecision


class TestModeBAandroidController:
    """Validate Mode B rooted shell action support and recovery state queries."""

    @pytest.fixture
    def mock_adb_available(self):
        """Mock adb availability globally for all tests in this class."""
        with patch("shutil.which", return_value="/usr/bin/adb"):
            yield

    @pytest.fixture(autouse=True)
    def auto_mock_adb(self, mock_adb_available):
        """Auto-use adb mock for all tests."""
        pass

    @pytest.fixture
    def settings_mode_b_enabled(self):
        """Settings with Mode B enabled."""
        settings = Settings(enable_android_control=True, enable_mode_b=True)
        return settings

    @pytest.fixture
    def settings_mode_b_disabled(self):
        """Settings with Mode B disabled."""
        settings = Settings(enable_android_control=True, enable_mode_b=False)
        return settings

    @pytest.fixture
    def policy(self):
        """Mock policy engine that allows all Mode B commands."""
        policy = MagicMock(spec=PolicyEngine)
        policy.validate_command.return_value = PolicyDecision(allowed=True, reason="")
        return policy

    def test_mode_b_get_property(self, settings_mode_b_enabled, policy):
        """Mode B: Read ro.* properties via getprop."""
        controller = AndroidController(settings_mode_b_enabled, policy)
        
        with patch("mordecai.android_control.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="G970FXXS1AXGA", stderr="")
            result = controller.perform("mode_b_get_property", ["ro.build.version.incremental"])
            
            assert result["stdout"] == "G970FXXS1AXGA"
            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            assert call_args == ["adb", "shell", "getprop", "ro.build.version.incremental"]

    def test_mode_b_get_property_invalid(self, settings_mode_b_enabled, policy):
        """Mode B: Reject non-ro.* properties."""
        controller = AndroidController(settings_mode_b_enabled, policy)
        
        with pytest.raises(ValueError, match="Property .* not allowed"):
            controller.perform("mode_b_get_property", ["system.usb.debug"])

    def test_mode_b_get_setting_system(self, settings_mode_b_enabled, policy):
        """Mode B: Read system namespace settings."""
        controller = AndroidController(settings_mode_b_enabled, policy)
        
        with patch("mordecai.android_control.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="500", stderr="")
            result = controller.perform("mode_b_get_setting", ["system", "screen_brightness"])
            
            assert result["stdout"] == "500"
            call_args = mock_run.call_args[0][0]
            assert call_args == ["adb", "shell", "settings", "get", "system", "screen_brightness"]

    def test_mode_b_get_setting_secure(self, settings_mode_b_enabled, policy):
        """Mode B: Read secure namespace settings."""
        controller = AndroidController(settings_mode_b_enabled, policy)
        
        with patch("mordecai.android_control.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="1", stderr="")
            result = controller.perform("mode_b_get_setting", ["secure", "location_mode"])
            
            assert result["stdout"] == "1"

    def test_mode_b_get_setting_invalid_namespace(self, settings_mode_b_enabled, policy):
        """Mode B: Reject invalid settings namespaces."""
        controller = AndroidController(settings_mode_b_enabled, policy)
        
        with pytest.raises(ValueError, match="Namespace .* not allowed"):
            controller.perform("mode_b_get_setting", ["custom", "key"])

    def test_mode_b_get_setting_invalid_key(self, settings_mode_b_enabled, policy):
        """Mode B: Reject settings keys with invalid characters."""
        controller = AndroidController(settings_mode_b_enabled, policy)
        
        with pytest.raises(ValueError, match="Setting key .* contains invalid characters"):
            controller.perform("mode_b_get_setting", ["system", "key; rm -rf /"])

    def test_mode_b_query_battery(self, settings_mode_b_enabled, policy):
        """Mode B: Query battery status via dumpsys."""
        controller = AndroidController(settings_mode_b_enabled, policy)
        
        battery_output = "Current Battery Service state:\n  AC powered: false\n  USB powered: true"
        with patch("mordecai.android_control.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=battery_output, stderr="")
            result = controller.perform("mode_b_query_battery", [])
            
            assert "USB powered: true" in result["stdout"]
            call_args = mock_run.call_args[0][0]
            assert call_args == ["adb", "shell", "dumpsys", "battery"]

    def test_mode_b_query_display(self, settings_mode_b_enabled, policy):
        """Mode B: Query display state via dumpsys."""
        controller = AndroidController(settings_mode_b_enabled, policy)
        
        with patch("mordecai.android_control.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="Display Power: state=ON", stderr="")
            result = controller.perform("mode_b_query_display", [])
            
            assert "Display Power" in result["stdout"]

    def test_mode_b_query_processes(self, settings_mode_b_enabled, policy):
        """Mode B: Query running processes."""
        controller = AndroidController(settings_mode_b_enabled, policy)
        
        ps_output = "u0_a100  1234  567 100 systemd app.mordecai"
        with patch("mordecai.android_control.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=ps_output, stderr="")
            result = controller.perform("mode_b_query_processes", ["mordecai"])
            
            assert "app.mordecai" in result["stdout"]
            call_args = mock_run.call_args[0][0]
            assert "ps | grep 'mordecai'" in " ".join(call_args)

    def test_mode_b_query_processes_invalid_pattern(self, settings_mode_b_enabled, policy):
        """Mode B: Reject process patterns with special characters."""
        controller = AndroidController(settings_mode_b_enabled, policy)
        
        with pytest.raises(ValueError, match="Process pattern .* contains invalid characters"):
            controller.perform("mode_b_query_processes", ["mordecai; rm -rf"])

    def test_mode_b_disabled_raises_permission_error(self, settings_mode_b_disabled, policy):
        """Mode B actions fail when enable_mode_b=False."""
        controller = AndroidController(settings_mode_b_disabled, policy)
        
        with pytest.raises(PermissionError, match="Mode B is disabled"):
            controller.perform("mode_b_get_property", ["ro.build.version"])

    def test_mode_b_get_state_queries_recovery_files(self, settings_mode_b_enabled, policy):
        """Mode B: Query recovery-layer state from /metadata/mordecai/."""
        controller = AndroidController(settings_mode_b_enabled, policy)
        
        def mock_run_side_effect(cmd, *args, **kwargs):
            """Return mock state file contents based on requested file."""
            cmd_str = " ".join(cmd) if isinstance(cmd, list) else cmd
            if "bootloader.txt" in cmd_str:
                return MagicMock(returncode=0, stdout="G970FXXS1AXGA", stderr="")
            elif "ro_secure.txt" in cmd_str:
                return MagicMock(returncode=0, stdout="0", stderr="")
            elif "build_fingerprint.txt" in cmd_str:
                return MagicMock(returncode=0, stdout="samsung/beyond0lte/beyond0lte:12/...", stderr="")
            elif "system_as_root.txt" in cmd_str:
                return MagicMock(returncode=0, stdout="1", stderr="")
            elif "magisk_detected.txt" in cmd_str:
                return MagicMock(returncode=0, stdout="1", stderr="")
            return MagicMock(returncode=1, stdout="", stderr="Not found")
        
        with patch("mordecai.android_control.subprocess.run", side_effect=mock_run_side_effect):
            state = controller.get_mode_b_state()
            
            assert state["bootloader"] == "G970FXXS1AXGA"
            assert state["ro_secure"] == "0"
            assert state["system_as_root"] == "1"
            assert state["magisk_detected"] == "1"

    def test_mode_b_get_state_handles_missing_files(self, settings_mode_b_enabled, policy):
        """Mode B: Recovery state gracefully handles missing files."""
        controller = AndroidController(settings_mode_b_enabled, policy)
        
        with patch("mordecai.android_control.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=2, stdout="", stderr="No such file or directory")
            state = controller.get_mode_b_state()
            
            # All values should be None when files are missing
            assert all(v is None for v in state.values())

    def test_mode_b_get_state_disabled(self, settings_mode_b_disabled, policy):
        """Mode B: get_mode_b_state raises PermissionError when disabled."""
        controller = AndroidController(settings_mode_b_disabled, policy)
        
        with pytest.raises(PermissionError, match="Mode B is disabled"):
            controller.get_mode_b_state()

    def test_tap_with_coordinate_validation(self, settings_mode_b_enabled, policy):
        """Mode A: Tap validates coordinate bounds."""
        controller = AndroidController(settings_mode_b_enabled, policy)
        
        # Valid coordinates
        with patch("mordecai.android_control.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            controller.perform("tap", ["100", "200"])
            assert mock_run.called
        
        # Out of bounds
        with pytest.raises(ValueError, match="Coordinates out of expected bounds"):
            controller.perform("tap", ["3000", "100"])

    def test_swipe_with_duration_validation(self, settings_mode_b_enabled, policy):
        """Mode A: Swipe validates duration limits."""
        controller = AndroidController(settings_mode_b_enabled, policy)
        
        # Valid swipe with duration
        with patch("mordecai.android_control.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            controller.perform("swipe", ["100", "200", "300", "400", "500"])
            call_args = mock_run.call_args[0][0]
            assert "500" in call_args
        
        # Duration too low
        with pytest.raises(ValueError, match="Duration must be 100-5000ms"):
            controller.perform("swipe", ["100", "200", "300", "400", "50"])
        
        # Duration too high
        with pytest.raises(ValueError, match="Duration must be 100-5000ms"):
            controller.perform("swipe", ["100", "200", "300", "400", "6000"])

    def test_type_with_character_validation(self, settings_mode_b_enabled, policy):
        """Mode A: Type validates input characters."""
        controller = AndroidController(settings_mode_b_enabled, policy)
        
        # Valid text
        with patch("mordecai.android_control.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            controller.perform("type", ["Hello World 123"])
            assert mock_run.called
        
        # Invalid characters
        with pytest.raises(ValueError, match="Text contains unsupported characters"):
            controller.perform("type", ["test; rm -rf /"])

    def test_policy_enforcement(self, settings_mode_b_enabled):
        """Mode B: Policy engine decision is enforced."""
        policy = MagicMock(spec=PolicyEngine)
        policy.validate_command.return_value = PolicyDecision(allowed=False, reason="Command blocked by policy")
        
        controller = AndroidController(settings_mode_b_enabled, policy)
        
        with pytest.raises(PermissionError, match="Command blocked by policy"):
            controller.perform("mode_b_get_property", ["ro.test"])

    def test_mode_a_statusbar_and_navigation_actions(self, settings_mode_b_enabled, policy):
        controller = AndroidController(settings_mode_b_enabled, policy)

        with patch("mordecai.android_control.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            controller.perform("show_notifications", [])
            assert mock_run.call_args[0][0] == ["adb", "shell", "cmd", "statusbar", "expand-notifications"]

            controller.perform("show_quick_settings", [])
            assert mock_run.call_args[0][0] == ["adb", "shell", "cmd", "statusbar", "expand-settings"]

            controller.perform("back", [])
            assert mock_run.call_args[0][0] == ["adb", "shell", "input", "keyevent", "KEYCODE_BACK"]

            controller.perform("home", [])
            assert mock_run.call_args[0][0] == ["adb", "shell", "input", "keyevent", "KEYCODE_HOME"]

            controller.perform("recents", [])
            assert mock_run.call_args[0][0] == ["adb", "shell", "input", "keyevent", "KEYCODE_APP_SWITCH"]
