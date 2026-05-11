package ai.mordecai.shell.coordinator

import ai.mordecai.shell.BackendSupervisor
import ai.mordecai.shell.MordecaiShellService
import ai.mordecai.shell.RootDetector
import ai.mordecai.shell.TermuxCommandClient
import ai.mordecai.shell.accessibility.MordecaiAccessibilityService
import ai.mordecai.shell.state.ShellState
import ai.mordecai.shell.voice.VoiceSessionController
import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.content.ContextCompat
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock

class ShellCoordinator private constructor(
    private val appContext: Context,
) {
    private val prefs = appContext.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
    private val rootDetector = RootDetector()
    private val refreshMutex = Mutex()
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
    private val _state = MutableStateFlow(ShellState())

    val state: StateFlow<ShellState> = _state.asStateFlow()
    val backendSupervisor = BackendSupervisor(TermuxCommandClient(appContext)) {
        currentBackendUrl()
    }

    private val startupOrchestrator = StartupOrchestrator(prefs, backendSupervisor)

    init {
        scope.launch {
            refreshState()
        }
    }

    fun createVoiceSessionController(): VoiceSessionController =
        VoiceSessionController(backendSupervisor.backendClient, prefs)

    fun currentBackendUrl(): String {
        val raw = prefs.getString(MordecaiShellService.PREF_BACKEND_URL, BackendSupervisor.DEFAULT_BASE_URL).orEmpty().trim()
        return if (raw.isBlank()) BackendSupervisor.DEFAULT_BASE_URL else raw.removeSuffix("/")
    }

    fun currentWakePhrase(): String {
        val raw = prefs.getString(MordecaiShellService.PREF_WAKE_PHRASE, MordecaiShellService.DEFAULT_WAKE_PHRASE).orEmpty().trim()
        return if (raw.isBlank()) MordecaiShellService.DEFAULT_WAKE_PHRASE else raw
    }

    fun isServiceEnabled(): Boolean = prefs.getBoolean(MordecaiShellService.PREF_SERVICE_ENABLED, false)

    suspend fun refreshState(startupPhase: ShellState.StartupPhase = state.value.startupPhase): ShellState = refreshMutex.withLock {
        val snapshot = buildSnapshot(startupPhase)
        _state.value = snapshot
        snapshot
    }

    suspend fun performStartup(): ShellState = refreshMutex.withLock {
        _state.value = buildSnapshot(ShellState.StartupPhase.CHECKING_ENVIRONMENT)
        val finalPhase = startupOrchestrator.run { phase ->
            _state.value = buildSnapshot(phase)
        }
        val snapshot = buildSnapshot(finalPhase)
        _state.value = snapshot
        snapshot
    }

    fun setServiceEnabled(enabled: Boolean) {
        prefs.edit().putBoolean(MordecaiShellService.PREF_SERVICE_ENABLED, enabled).apply()
        _state.value = _state.value.copy(shellServiceEnabled = enabled)
        scope.launch { refreshState() }
    }

    fun setWakeEnabled(enabled: Boolean) {
        prefs.edit().putBoolean(MordecaiShellService.PREF_WAKE_ENABLED, enabled).apply()
        _state.value = _state.value.copy(wakeEnabled = enabled)
        scope.launch { refreshState() }
    }

    fun setAutoStartEnabled(enabled: Boolean) {
        prefs.edit().putBoolean(MordecaiShellService.PREF_AUTO_START, enabled).apply()
        scope.launch { refreshState() }
    }

    fun setOverlayEnabled(enabled: Boolean) {
        prefs.edit().putBoolean(MordecaiShellService.PREF_LOCKSCREEN_OVERLAY, enabled).apply()
        _state.value = _state.value.copy(overlayEnabled = enabled)
        scope.launch { refreshState() }
    }

    fun saveBackendUrl(url: String) {
        val normalized = url.trim().ifBlank { BackendSupervisor.DEFAULT_BASE_URL }.removeSuffix("/")
        prefs.edit().putString(MordecaiShellService.PREF_BACKEND_URL, normalized).apply()
        scope.launch { refreshState() }
    }

    fun saveWakePhrase(phrase: String) {
        val normalized = phrase.trim().ifBlank { MordecaiShellService.DEFAULT_WAKE_PHRASE }
        prefs.edit().putString(MordecaiShellService.PREF_WAKE_PHRASE, normalized).apply()
        scope.launch { refreshState() }
    }

    fun setActiveVoiceSurface(surface: ShellState.ActiveVoiceSurface) {
        _state.value = _state.value.copy(activeVoiceSurface = surface)
    }

    fun clearActiveVoiceSurface(surface: ShellState.ActiveVoiceSurface) {
        if (_state.value.activeVoiceSurface == surface) {
            _state.value = _state.value.copy(activeVoiceSurface = ShellState.ActiveVoiceSurface.NONE)
        }
    }

    fun installRuntime() = backendSupervisor.installRuntime().also {
        scope.launch { refreshState() }
    }

    fun startRuntime() = backendSupervisor.startRuntime().also {
        scope.launch { performStartup() }
    }

    fun stopRuntime() = backendSupervisor.stopRuntime().also {
        scope.launch { refreshState(ShellState.StartupPhase.DEGRADED) }
    }

    fun updateRuntime() = backendSupervisor.updateRuntime().also {
        scope.launch { refreshState() }
    }

    fun configureAiProvider(providerMode: String, baseUrl: String, apiKey: String, model: String) =
        backendSupervisor.configureAiProvider(providerMode, baseUrl, apiKey, model).also {
            scope.launch { refreshState() }
        }

    fun setAdvancedMode(enabled: Boolean) = backendSupervisor.setAdvancedMode(enabled).also {
        if (it.ok) {
            prefs.edit().putBoolean(MordecaiShellService.PREF_ADVANCED_ENABLED, enabled).apply()
            _state.value = _state.value.copy(advancedModeEnabled = enabled)
        }
        scope.launch { refreshState() }
    }

    private suspend fun buildSnapshot(startupPhase: ShellState.StartupPhase): ShellState {
        val health = backendSupervisor.checkHealth()
        val runtimeStatus = if (health.reachable) backendSupervisor.runtimeStatus() else null
        val backendProvider = runtimeStatus?.takeIf { it.ok }?.provider
        val backendStatusText = when {
            health.reachable -> runtimeStatus?.error?.ifBlank { null } ?: health.status.ifBlank { "Backend reachable" }
            else -> health.status.ifBlank { "Backend unavailable" }
        }
        val advancedModeAllowed = rootDetector.isRootAvailable()
        val microphonePermissionGranted = ContextCompat.checkSelfPermission(appContext, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED
        val notificationPermissionGranted = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            ContextCompat.checkSelfPermission(appContext, Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED
        } else {
            true
        }
        return ShellState(
            termuxInstalled = backendSupervisor.runtimeGateway.isTermuxInstalled(),
            backendReachable = health.reachable,
            backendStatusText = backendStatusText,
            backendProvider = backendProvider,
            shellServiceEnabled = prefs.getBoolean(MordecaiShellService.PREF_SERVICE_ENABLED, false),
            wakeEnabled = prefs.getBoolean(MordecaiShellService.PREF_WAKE_ENABLED, false),
            accessibilityEnabled = MordecaiAccessibilityService.isEnabled(appContext),
            overlayEnabled = prefs.getBoolean(MordecaiShellService.PREF_LOCKSCREEN_OVERLAY, true),
            advancedModeAllowed = advancedModeAllowed,
            advancedModeEnabled = prefs.getBoolean(MordecaiShellService.PREF_ADVANCED_ENABLED, false) && advancedModeAllowed,
            microphonePermissionGranted = microphonePermissionGranted,
            notificationPermissionGranted = notificationPermissionGranted,
            activeVoiceSurface = state.value.activeVoiceSurface,
            startupPhase = startupPhase,
        )
    }

    companion object {
        private const val PREFS_NAME = "mordecai-shell-prefs"

        @Volatile
        private var instance: ShellCoordinator? = null

        fun get(context: Context): ShellCoordinator {
            return instance ?: synchronized(this) {
                instance ?: ShellCoordinator(context.applicationContext).also { instance = it }
            }
        }
    }
}