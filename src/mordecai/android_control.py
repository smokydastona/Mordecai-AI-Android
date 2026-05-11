from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote
from uuid import uuid4

from mordecai.config import Settings
from mordecai.models import AndroidDiagnosticRecord
from mordecai.policy import PolicyEngine
from mordecai.store import StateStore

logger = logging.getLogger(__name__)


class AndroidController:
    """
    Android control layer for Mode A (accessibility overlay, voice commands)
    and Mode B (rooted shell automation, recovery state queries).
    
    All operations are gated behind explicit policy enforcement and operator approval.
    """

    def __init__(self, settings: Settings, policy: PolicyEngine, store: StateStore | None = None) -> None:
        self.settings = settings
        self.policy = policy
        self.store = store

    def perform(self, action: str, arguments: list[str]) -> dict[str, str]:
        """
        Execute a Mode A or Mode B action.
        
        Mode A actions (always available):
        - tap: input tap X Y
        - swipe: input swipe X1 Y1 X2 Y2 [duration]
        - type: input text STRING
        - open_app: monkey -p PACKAGE
        
        Mode B actions (requires enable_mode_b=True and root access):
        - get_property: getprop PROPERTY
        - get_setting: settings get NAMESPACE KEY
        - query_battery: dumpsys battery
        - query_display: dumpsys display
        - query_processes: ps | grep PATTERN
        - get_mode_b_state: read recovery-layer state from /metadata/mordecai/
        
        Raises:
        - PermissionError: Android control disabled or action not allowed by policy
        - RuntimeError: adb not available, command failed, or invalid mode B state
        - ValueError: Unsupported action or invalid argument count
        """
        if not self.settings.enable_android_control:
            raise PermissionError("Android control is disabled")
        if shutil.which("adb") is None:
            raise RuntimeError("adb is not available on PATH")
        
        # Mode B actions require explicit enablement
        if action.startswith("mode_b_") and not self.settings.enable_mode_b:
            raise PermissionError("Mode B is disabled; set enable_mode_b=True to use rooted shell automation")

        action_decision = self.policy.validate_android_action(action, arguments)
        if not action_decision.allowed:
            raise PermissionError(action_decision.reason)
        
        command = self._build_command(action, arguments)
        decision = self.policy.validate_command(" ".join(command))
        if not decision.allowed:
            raise PermissionError(decision.reason)
        
        result = subprocess.run(command, text=True, capture_output=True, check=False)
        if result.returncode != 0:
            error_msg = result.stderr.strip() or "adb command failed"
            logger.error(f"Android action '{action}' failed: {error_msg}")
            raise RuntimeError(error_msg)
        
        return {"stdout": result.stdout.strip(), "stderr": result.stderr.strip()}

    def _build_command(self, action: str, arguments: list[str]) -> list[str]:
        """Build adb command for the requested action."""
        
        # ============ Mode A: Basic Input Injection ============
        if action == "tap" and len(arguments) == 2:
            # Validate coordinate bounds (rough sanity check)
            try:
                x, y = int(arguments[0]), int(arguments[1])
                if not (0 <= x <= 2000 and 0 <= y <= 2000):
                    raise ValueError("Coordinates out of expected bounds (0-2000)")
            except ValueError as e:
                raise ValueError(f"Invalid tap coordinates: {e}")
            return ["adb", "shell", "input", "tap", str(x), str(y)]
        
        if action == "swipe" and len(arguments) in (4, 5):
            # swipe X1 Y1 X2 Y2 [DURATION_MS]
            try:
                x1, y1, x2, y2 = map(int, arguments[:4])
                if not all(0 <= c <= 2000 for c in [x1, y1, x2, y2]):
                    raise ValueError("Coordinates out of expected bounds (0-2000)")
                
                # Optional duration (default: 500ms, max: 5000ms)
                duration = 500
                if len(arguments) == 5:
                    duration = int(arguments[4])
                    if not (100 <= duration <= 5000):
                        raise ValueError("Duration must be 100-5000ms")
            except ValueError as e:
                raise ValueError(f"Invalid swipe arguments: {e}")
            
            cmd = ["adb", "shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration)]
            return cmd
        
        if action == "type" and len(arguments) == 1:
            # Escape special characters for shell
            text = arguments[0]
            # Allow alphanumeric, space, and common punctuation
            if not re.match(r"^[a-zA-Z0-9\s\-_.,!?@#\$%&()]+$", text):
                raise ValueError("Text contains unsupported characters; use alphanumeric and basic punctuation")
            return ["adb", "shell", "input", "text", text]
        
        if action == "open_app" and len(arguments) == 1:
            package = arguments[0]
            if package not in self.settings.allowed_android_packages:
                raise PermissionError(f"Package '{package}' is not allowlisted; add to allowed_android_packages in config")
            return ["adb", "shell", "monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1"]

        if action == "back" and len(arguments) == 0:
            return ["adb", "shell", "input", "keyevent", "KEYCODE_BACK"]

        if action == "home" and len(arguments) == 0:
            return ["adb", "shell", "input", "keyevent", "KEYCODE_HOME"]

        if action == "recents" and len(arguments) == 0:
            return ["adb", "shell", "input", "keyevent", "KEYCODE_APP_SWITCH"]

        if action == "show_notifications" and len(arguments) == 0:
            return ["adb", "shell", "cmd", "statusbar", "expand-notifications"]

        if action == "show_quick_settings" and len(arguments) == 0:
            return ["adb", "shell", "cmd", "statusbar", "expand-settings"]
        
        # ============ Mode B: Rooted Shell Actions ============
        
        if action == "mode_b_get_property" and len(arguments) == 1:
            prop = arguments[0]
            # Only allow ro.* properties and safe device properties
            if not re.match(r"^ro\.[a-z0-9._]+$", prop):
                raise ValueError(f"Property '{prop}' not allowed; only ro.* properties are readable")
            return ["adb", "shell", "getprop", prop]
        
        if action == "mode_b_get_setting" and len(arguments) == 2:
            namespace, key = arguments
            # Allow only system/secure/global namespaces, no modification
            if namespace not in ("system", "secure", "global"):
                raise ValueError(f"Namespace '{namespace}' not allowed; use 'system', 'secure', or 'global'")
            if not re.match(r"^[a-z0-9_]+$", key):
                raise ValueError(f"Setting key '{key}' contains invalid characters")
            return ["adb", "shell", "settings", "get", namespace, key]
        
        if action == "mode_b_query_battery" and len(arguments) == 0:
            return ["adb", "shell", "dumpsys", "battery"]
        
        if action == "mode_b_query_display" and len(arguments) == 0:
            return ["adb", "shell", "dumpsys", "display"]
        
        if action == "mode_b_query_processes" and len(arguments) == 1:
            pattern = arguments[0]
            # Prevent command injection via grep pattern
            if not re.match(r"^[a-zA-Z0-9._-]+$", pattern):
                raise ValueError(f"Process pattern '{pattern}' contains invalid characters")
            return ["adb", "shell", "sh", "-c", f"ps | grep '{pattern}'"]
        
        if action == "mode_b_get_state" and len(arguments) == 0:
            # This will be handled specially by the caller; return placeholder
            return ["adb", "shell", "cat", "/metadata/mordecai/bootstate.txt"]
        
        raise ValueError(f"Unsupported Android action '{action}' or invalid argument count")

    def get_mode_b_state(self) -> dict[str, Any]:
        """
        Query recovery-layer Mode B initialization state.
        
        Reads state files written by the custom recovery tree during boot.
        Returns a dict with keys: bootloader, ro_secure, build_fingerprint, 
        system_as_root, magisk_detected.
        
        All values are strings or None if the file could not be read.
        
        Requires Mode B to be enabled and adb available.
        """
        if not self.settings.enable_mode_b:
            raise PermissionError("Mode B is disabled")
        
        state_dir = "/metadata/mordecai"
        state_files = {
            "bootloader": "bootloader.txt",
            "ro_secure": "ro_secure.txt",
            "build_fingerprint": "build_fingerprint.txt",
            "system_as_root": "system_as_root.txt",
            "magisk_detected": "magisk_detected.txt",
        }
        
        result = {}
        for key, filename in state_files.items():
            try:
                cmd = ["adb", "shell", "cat", f"{state_dir}/{filename}"]
                proc = subprocess.run(cmd, text=True, capture_output=True, check=False, timeout=5)
                if proc.returncode == 0:
                    result[key] = proc.stdout.strip()
                else:
                    result[key] = None
                    logger.warning(f"Could not read Mode B state file {key}: {proc.stderr.strip()}")
            except subprocess.TimeoutExpired:
                result[key] = None
                logger.warning(f"Timeout reading Mode B state file {key}")
            except Exception as e:
                result[key] = None
                logger.error(f"Error reading Mode B state file {key}: {e}")
        
        return result

    def list_diagnostics(self, *, category: str | None = None, limit: int = 25) -> list[AndroidDiagnosticRecord]:
        if self.store is None:
            return []
        return self.store.filter_android_diagnostics(category=category, limit=limit)

    def collect_diagnostic(
        self,
        category: str,
        *,
        filter_text: str | None = None,
        package: str | None = None,
        limit: int = 200,
    ) -> AndroidDiagnosticRecord:
        if not self.settings.enable_android_control:
            raise PermissionError("Android control is disabled")
        if shutil.which("adb") is None:
            raise RuntimeError("adb is not available on PATH")
        normalized = category.strip().lower()
        if normalized in {"logcat", "process-memory", "battery", "thermal"} and not self.settings.enable_mode_b:
            raise PermissionError("Mode B is disabled; these diagnostics require enable_mode_b=True")

        if normalized == "logcat":
            capped_limit = max(10, min(limit, 400))
            command = ["adb", "shell", "logcat", "-d", "-t", str(capped_limit)]
            payload = self._run_diagnostic_command(command)
            lines = [line for line in payload.splitlines() if line.strip()]
            if filter_text:
                if not re.fullmatch(r"[a-zA-Z0-9._:/ @#-]{1,80}", filter_text):
                    raise ValueError("Filter text contains unsupported characters")
                lowered = filter_text.lower()
                lines = [line for line in lines if lowered in line.lower()]
            details = {
                "line_count": len(lines),
                "filter_text": filter_text,
                "preview": lines[:50],
            }
            return self._record_diagnostic("logcat", f"Logcat capture returned {len(lines)} lines", details)

        if normalized == "process-memory":
            if not package:
                raise ValueError("Package is required for process-memory diagnostics")
            if package not in self.settings.allowed_android_packages:
                raise PermissionError(f"Package '{package}' is not allowlisted")
            command = ["adb", "shell", "dumpsys", "meminfo", package]
            payload = self._run_diagnostic_command(command)
            summary_line = next((line.strip() for line in payload.splitlines() if "TOTAL PSS" in line.upper() or "TOTAL" in line.upper()), "No TOTAL line found")
            details = {
                "package": package,
                "summary_line": summary_line,
                "preview": payload.splitlines()[:80],
            }
            return self._record_diagnostic("process-memory", f"Memory stats captured for {package}", details)

        if normalized == "battery":
            command = ["adb", "shell", "dumpsys", "battery"]
            payload = self._run_diagnostic_command(command)
            parsed: dict[str, str] = {}
            for line in payload.splitlines():
                if ":" not in line:
                    continue
                key, value = line.split(":", 1)
                parsed[key.strip().lower().replace(" ", "_")] = value.strip()
            level = parsed.get("level", "unknown")
            status = parsed.get("status", "unknown")
            return self._record_diagnostic(
                "battery",
                f"Battery snapshot level={level} status={status}",
                {"parsed": parsed, "preview": payload.splitlines()[:80]},
            )

        if normalized == "thermal":
            command = ["adb", "shell", "dumpsys", "thermalservice"]
            payload = self._run_diagnostic_command(command)
            preview = [line for line in payload.splitlines() if line.strip()][:80]
            return self._record_diagnostic(
                "thermal",
                f"Thermal service snapshot returned {len(preview)} non-empty lines",
                {"preview": preview},
            )

        raise ValueError(f"Unsupported Android diagnostic category '{category}'")

    def _run_diagnostic_command(self, command: list[str]) -> str:
        decision = self.policy.validate_command(" ".join(command))
        if not decision.allowed:
            raise PermissionError(decision.reason)
        result = subprocess.run(command, text=True, capture_output=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "adb diagnostic command failed")
        return result.stdout.strip()

    def _record_diagnostic(self, category: str, summary: str, details: dict[str, Any]) -> AndroidDiagnosticRecord:
        record = AndroidDiagnosticRecord(
            diagnostic_id=uuid4().hex[:12],
            category=category,
            source="android-control",
            summary=summary,
            details=details,
            created_at=datetime.now(UTC),
        )
        if self.store is not None:
            self.store.append_android_diagnostic(record)
        return record