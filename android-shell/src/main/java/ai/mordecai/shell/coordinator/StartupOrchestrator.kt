package ai.mordecai.shell.coordinator

import ai.mordecai.shell.BackendSupervisor
import ai.mordecai.shell.MordecaiShellService
import ai.mordecai.shell.state.ShellState
import android.content.SharedPreferences
import kotlinx.coroutines.delay

class StartupOrchestrator(
    private val prefs: SharedPreferences,
    private val backendSupervisor: BackendSupervisor,
) {
    suspend fun run(onPhaseChanged: suspend (ShellState.StartupPhase) -> Unit): ShellState.StartupPhase {
        onPhaseChanged(ShellState.StartupPhase.CHECKING_ENVIRONMENT)

        val initialHealth = backendSupervisor.checkHealth()
        if (initialHealth.reachable) {
            return ShellState.StartupPhase.READY
        }

        val canAutoStart = prefs.getBoolean(MordecaiShellService.PREF_AUTO_START, true)
        if (!canAutoStart || !backendSupervisor.runtimeGateway.isTermuxInstalled()) {
            return ShellState.StartupPhase.DEGRADED
        }

        onPhaseChanged(ShellState.StartupPhase.STARTING_RUNTIME)
        backendSupervisor.startRuntime()

        onPhaseChanged(ShellState.StartupPhase.VERIFYING_BACKEND)
        repeat(VERIFY_ATTEMPTS) {
            delay(VERIFY_DELAY_MS)
            if (backendSupervisor.checkHealth().reachable) {
                return ShellState.StartupPhase.READY
            }
        }

        return ShellState.StartupPhase.DEGRADED
    }

    companion object {
        private const val VERIFY_ATTEMPTS = 4
        private const val VERIFY_DELAY_MS = 1_500L
    }
}