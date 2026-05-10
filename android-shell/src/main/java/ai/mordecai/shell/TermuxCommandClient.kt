package ai.mordecai.shell

import android.content.Context
import android.content.Intent
import android.os.Build
import android.content.pm.PackageManager

class TermuxCommandClient(private val context: Context) {
    data class CommandResult(val ok: Boolean, val message: String)

    fun isTermuxInstalled(): Boolean = try {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            context.packageManager.getPackageInfo(TERMUX_PACKAGE, PackageManager.PackageInfoFlags.of(0))
        } else {
            @Suppress("DEPRECATION")
            context.packageManager.getPackageInfo(TERMUX_PACKAGE, 0)
        }
        true
    } catch (_: Exception) {
        false
    }

    fun installRuntime(): CommandResult = runBash(
        "bash <(curl -fsSL https://raw.githubusercontent.com/smokydastona/Mordecai-AI-Android/main/scripts/proot-setup.sh)",
        "Install Mordecai runtime",
    )

    fun startRuntime(): CommandResult = runBash("$INSTALL_ROOT/scripts/start.sh", "Start Mordecai runtime")

    fun stopRuntime(): CommandResult = runBash("$INSTALL_ROOT/scripts/stop.sh", "Stop Mordecai runtime")

    fun updateRuntime(): CommandResult = runBash("$INSTALL_ROOT/scripts/update.sh", "Update Mordecai runtime")

    fun configureAiProvider(
        providerMode: String,
        baseUrl: String,
        apiKey: String,
        model: String,
    ): CommandResult {
        val normalizedMode = providerMode.trim().lowercase()
        val defaultProvider = if (normalizedMode == "rule-based") "rule-based" else "openai-compatible"
        val normalizedBaseUrl = baseUrl.trim()
        val normalizedApiKey = apiKey.trim()
        val normalizedModel = model.trim()
        val script = """
python - <<'PY'
from pathlib import Path

env_path = Path.home() / "mordecai" / ".env"
if not env_path.exists():
    raise SystemExit("Missing runtime environment file. Install the runtime first.")

entries = {}
for line in env_path.read_text(encoding="utf-8").splitlines():
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    entries[key] = value

entries["MORDECAI_DEFAULT_PROVIDER"] = "$defaultProvider"
entries["MORDECAI_OPENAI_BASE_URL"] = "$normalizedBaseUrl"
entries["MORDECAI_OPENAI_API_KEY"] = "$normalizedApiKey"
entries["MORDECAI_OPENAI_MODEL"] = "$normalizedModel"

env_path.write_text("\n".join(f"{key}={value}" for key, value in entries.items()) + "\n", encoding="utf-8")
PY
$INSTALL_ROOT/scripts/stop.sh || true
$INSTALL_ROOT/scripts/start.sh
""".trimIndent()
        return runBash(script, "Apply AI provider settings")
    }

    fun setAdvancedMode(enabled: Boolean): CommandResult {
        val mode = if (enabled) "mode-b" else "mode-a"
        val androidControl = enabled.toString().lowercase()
        val daemonMode = enabled.toString().lowercase()
        val advancedSelfImprovement = enabled.toString().lowercase()
        val script = """
python - <<'PY'
from pathlib import Path

env_path = Path.home() / "mordecai" / ".env"
if not env_path.exists():
    raise SystemExit("Missing runtime environment file. Install the runtime first.")

entries = {}
for line in env_path.read_text(encoding="utf-8").splitlines():
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    entries[key] = value

entries["MORDECAI_MODE"] = "$mode"
entries["MORDECAI_ENABLE_ANDROID_CONTROL"] = "$androidControl"
entries["MORDECAI_ENABLE_DAEMON_MODE"] = "$daemonMode"
entries["MORDECAI_ENABLE_ADVANCED_SELF_IMPROVEMENT"] = "$advancedSelfImprovement"

env_path.write_text("\n".join(f"{key}={value}" for key, value in entries.items()) + "\n", encoding="utf-8")
PY
$INSTALL_ROOT/scripts/stop.sh || true
$INSTALL_ROOT/scripts/start.sh
""".trimIndent()
        return runBash(script, if (enabled) "Enable advanced mode" else "Disable advanced mode")
    }

    private fun runBash(command: String, description: String): CommandResult {
        if (!isTermuxInstalled()) {
            return CommandResult(false, "Termux is not installed.")
        }
        val intent = Intent(ACTION_RUN_COMMAND).apply {
            setClassName(TERMUX_PACKAGE, RUN_COMMAND_SERVICE)
            putExtra(EXTRA_COMMAND_PATH, BASH_PATH)
            putExtra(EXTRA_ARGUMENTS, arrayOf("-lc", command))
            putExtra(EXTRA_BACKGROUND, true)
            putExtra(EXTRA_WORKDIR, INSTALL_ROOT)
        }
        return try {
            context.startService(intent)
            CommandResult(true, description)
        } catch (error: Exception) {
            CommandResult(false, error.message ?: "Unable to contact Termux.")
        }
    }

    companion object {
        const val TERMUX_PACKAGE = "com.termux"
        private const val RUN_COMMAND_SERVICE = "com.termux.app.RunCommandService"
        private const val ACTION_RUN_COMMAND = "com.termux.RUN_COMMAND"
        private const val EXTRA_COMMAND_PATH = "com.termux.RUN_COMMAND_PATH"
        private const val EXTRA_ARGUMENTS = "com.termux.RUN_COMMAND_ARGUMENTS"
        private const val EXTRA_WORKDIR = "com.termux.RUN_COMMAND_WORKDIR"
        private const val EXTRA_BACKGROUND = "com.termux.RUN_COMMAND_BACKGROUND"
        private const val BASH_PATH = "/data/data/com.termux/files/usr/bin/bash"
        private const val INSTALL_ROOT = "/data/data/com.termux/files/home/mordecai"
    }
}