package ai.mordecai.shell.accessibility

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.GestureDescription
import android.content.ComponentName
import android.content.Context
import android.graphics.Path
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
    private enum class RestrictedAction {
        BACK,
        HOME,
        RECENTS,
        NOTIFICATIONS,
        QUICK_SETTINGS,
        TAP_CENTER,
    }

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
        overlay = MordecaiOverlay(this, onListenRequested = {
            listenForVoiceCommand(manualTrigger = true)
        }, onActionRequested = { action ->
            performRestrictedAction(action)
        })
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
                    val localAction = parseRestrictedAction(command)
                    if (localAction != null) {
                        val result = performRestrictedAction(localAction)
                        speechOutput.speak(result)
                        prefs.edit().putString(MordecaiShellService.PREF_LAST_REPLY, result).apply()
                        overlay.showStatus(
                            title = getString(R.string.overlay_action_title),
                            message = result,
                        )
                        return@launch
                    }
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

    private fun parseRestrictedAction(command: String): RestrictedAction? {
        val normalized = command.trim().lowercase()
        return when {
            normalized.contains("go back") || normalized == "back" -> RestrictedAction.BACK
            normalized.contains("go home") || normalized == "home" -> RestrictedAction.HOME
            normalized.contains("recent") || normalized.contains("app switcher") -> RestrictedAction.RECENTS
            normalized.contains("notifications") || normalized.contains("show notifications") -> RestrictedAction.NOTIFICATIONS
            normalized.contains("quick settings") || normalized.contains("show quick settings") -> RestrictedAction.QUICK_SETTINGS
            normalized.contains("tap center") || normalized.contains("press center") -> RestrictedAction.TAP_CENTER
            else -> null
        }
    }

    private fun performRestrictedAction(action: String): String {
        val restrictedAction = runCatching { RestrictedAction.valueOf(action) }.getOrNull()
            ?: return getString(R.string.overlay_action_unknown)
        return performRestrictedAction(restrictedAction)
    }

    private fun performRestrictedAction(action: RestrictedAction): String {
        val success = when (action) {
            RestrictedAction.BACK -> performGlobalAction(GLOBAL_ACTION_BACK)
            RestrictedAction.HOME -> performGlobalAction(GLOBAL_ACTION_HOME)
            RestrictedAction.RECENTS -> performGlobalAction(GLOBAL_ACTION_RECENTS)
            RestrictedAction.NOTIFICATIONS -> performGlobalAction(GLOBAL_ACTION_NOTIFICATIONS)
            RestrictedAction.QUICK_SETTINGS -> performGlobalAction(GLOBAL_ACTION_QUICK_SETTINGS)
            RestrictedAction.TAP_CENTER -> dispatchCenterTap()
        }
        return if (success) {
            getString(
                when (action) {
                    RestrictedAction.BACK -> R.string.overlay_action_back_done
                    RestrictedAction.HOME -> R.string.overlay_action_home_done
                    RestrictedAction.RECENTS -> R.string.overlay_action_recents_done
                    RestrictedAction.NOTIFICATIONS -> R.string.overlay_action_notifications_done
                    RestrictedAction.QUICK_SETTINGS -> R.string.overlay_action_quick_settings_done
                    RestrictedAction.TAP_CENTER -> R.string.overlay_action_tap_center_done
                }
            )
        } else {
            getString(R.string.overlay_action_failed)
        }
    }

    private fun dispatchCenterTap(): Boolean {
        val metrics = resources.displayMetrics
        val centerX = metrics.widthPixels / 2f
        val centerY = metrics.heightPixels / 2f
        val path = Path().apply {
            moveTo(centerX, centerY)
        }
        val gesture = GestureDescription.Builder()
            .addStroke(GestureDescription.StrokeDescription(path, 0, 60))
            .build()
        return dispatchGesture(gesture, null, null)
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