package ai.mordecai.shell.accessibility

import android.accessibilityservice.AccessibilityService
import android.content.ComponentName
import android.content.Context
import android.provider.Settings
import android.view.accessibility.AccessibilityEvent
import ai.mordecai.shell.BackendSupervisor
import ai.mordecai.shell.MordecaiShellService
import ai.mordecai.shell.R
import ai.mordecai.shell.SpeechCommandProcessor
import ai.mordecai.shell.SpeechOutput
import ai.mordecai.shell.TermuxCommandClient
import ai.mordecai.shell.overlay.MordecaiOverlay
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch

class MordecaiAccessibilityService : AccessibilityService() {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
    private lateinit var prefs: android.content.SharedPreferences
    private lateinit var backendSupervisor: BackendSupervisor
    private lateinit var speechOutput: SpeechOutput
    private lateinit var overlay: MordecaiOverlay
    private var commandProcessor: SpeechCommandProcessor? = null

    override fun onCreate() {
        super.onCreate()
        prefs = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        backendSupervisor = BackendSupervisor(TermuxCommandClient(this)) {
            prefs.getString(MordecaiShellService.PREF_BACKEND_URL, BackendSupervisor.DEFAULT_BASE_URL)
                ?: BackendSupervisor.DEFAULT_BASE_URL
        }
        speechOutput = SpeechOutput(this)
        overlay = MordecaiOverlay(this) {
            listenForVoiceCommand(manualTrigger = true)
        }
    }

    override fun onServiceConnected() {
        super.onServiceConnected()
        instance = this
        syncOverlayVisibility()
        overlay.showStatus(
            title = getString(R.string.overlay_title),
            message = getString(R.string.accessibility_ready),
        )
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        if (event?.eventType == AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED && prefs.getBoolean(MordecaiShellService.PREF_LOCKSCREEN_OVERLAY, true)) {
            syncOverlayVisibility()
        }
    }

    override fun onInterrupt() {
        commandProcessor?.stop()
        overlay.showStatus(
            title = getString(R.string.overlay_title),
            message = getString(R.string.accessibility_interrupted),
        )
    }

    override fun onDestroy() {
        instance = null
        commandProcessor?.stop()
        overlay.hide()
        speechOutput.shutdown()
        scope.cancel()
        super.onDestroy()
    }

    fun syncOverlayVisibility() {
        if (prefs.getBoolean(MordecaiShellService.PREF_LOCKSCREEN_OVERLAY, true)) {
            overlay.show()
        } else {
            overlay.hide()
        }
    }

    private fun listenForVoiceCommand(manualTrigger: Boolean) {
        syncOverlayVisibility()
        commandProcessor?.stop()
        overlay.showStatus(
            title = getString(R.string.overlay_listening_title),
            message = getString(R.string.notification_listening_for_command),
        )
        commandProcessor = SpeechCommandProcessor(
            context = this,
            onCommandHeard = { command ->
                scope.launch {
                    overlay.showStatus(
                        title = getString(R.string.overlay_processing_title),
                        message = command,
                    )
                    val result = backendSupervisor.chat(command)
                    if (!result.ok) {
                        overlay.showStatus(
                            title = getString(R.string.overlay_error_title),
                            message = result.error ?: getString(R.string.notification_command_failed),
                        )
                        return@launch
                    }
                    val avatar = backendSupervisor.avatar()
                    val spokenReply = result.reply.ifBlank { getString(R.string.notification_empty_reply) }
                    speechOutput.speak(spokenReply)
                    prefs.edit().putString(MordecaiShellService.PREF_LAST_REPLY, spokenReply).apply()
                    overlay.showReply(
                        reply = spokenReply,
                        emotion = avatar.emotion,
                        svg = avatar.svg,
                    )
                }
            },
            onFailure = { error ->
                val message = if (manualTrigger) error else getString(R.string.notification_command_timeout)
                overlay.showStatus(
                    title = getString(R.string.overlay_error_title),
                    message = message,
                )
            },
        )
        commandProcessor?.startListening()
    }

    companion object {
        @Volatile
        private var instance: MordecaiAccessibilityService? = null
        private const val PREFS_NAME = "mordecai-shell-prefs"

        fun isEnabled(context: Context): Boolean {
            val current = instance
            if (current != null) {
                return true
            }
            val enabled = Settings.Secure.getString(context.contentResolver, Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES).orEmpty()
            val target = ComponentName(context, MordecaiAccessibilityService::class.java).flattenToString()
            return enabled.split(':').any { it.equals(target, ignoreCase = true) }
        }

        fun requestVoiceCommand(manualTrigger: Boolean = true): Boolean {
            val service = instance ?: return false
            service.listenForVoiceCommand(manualTrigger)
            return true
        }

        fun refreshOverlay(context: Context): Boolean {
            val service = instance ?: return false
            service.syncOverlayVisibility()
            return isEnabled(context)
        }
    }
}