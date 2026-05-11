package ai.mordecai.shell.state

data class ShellState(
    val termuxInstalled: Boolean = false,
    val backendReachable: Boolean = false,
    val backendStatusText: String = "Backend unavailable",
    val backendProvider: String? = null,
    val shellServiceEnabled: Boolean = false,
    val wakeEnabled: Boolean = false,
    val accessibilityEnabled: Boolean = false,
    val overlayEnabled: Boolean = false,
    val advancedModeAllowed: Boolean = false,
    val advancedModeEnabled: Boolean = false,
    val microphonePermissionGranted: Boolean = false,
    val notificationPermissionGranted: Boolean = false,
    val activeVoiceSurface: ActiveVoiceSurface = ActiveVoiceSurface.NONE,
    val startupPhase: StartupPhase = StartupPhase.NOT_STARTED,
) {
    enum class ActiveVoiceSurface {
        NONE,
        SHELL_SERVICE,
        ACCESSIBILITY_OVERLAY,
    }

    enum class StartupPhase {
        NOT_STARTED,
        CHECKING_ENVIRONMENT,
        STARTING_RUNTIME,
        VERIFYING_BACKEND,
        READY,
        DEGRADED,
    }
}