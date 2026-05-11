package ai.mordecai.shell

import android.Manifest
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import androidx.lifecycle.LifecycleService
import androidx.lifecycle.lifecycleScope
import ai.mordecai.shell.accessibility.MordecaiAccessibilityService
import ai.mordecai.shell.coordinator.ShellCoordinator
import ai.mordecai.shell.state.ShellState
import ai.mordecai.shell.voice.VoiceSessionController
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

class MordecaiShellService : LifecycleService() {
    private lateinit var shellCoordinator: ShellCoordinator
    private lateinit var prefs: android.content.SharedPreferences
    private lateinit var backendSupervisor: BackendSupervisor
    private lateinit var voiceSessionController: VoiceSessionController
    private lateinit var speechOutput: SpeechOutput
    private var wakePhraseManager: WakePhraseManager? = null
    private var commandProcessor: SpeechCommandProcessor? = null
    private var pollingJob: Job? = null

    override fun onCreate() {
        super.onCreate()
        shellCoordinator = ShellCoordinator.get(this)
        prefs = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        backendSupervisor = shellCoordinator.backendSupervisor
        voiceSessionController = shellCoordinator.createVoiceSessionController()
        speechOutput = SpeechOutput(this) {
            lifecycleScope.launch {
                voiceSessionController.onPlaybackFinished("shell-service")
                shellCoordinator.clearActiveVoiceSurface(ShellState.ActiveVoiceSurface.SHELL_SERVICE)
            }
        }
        createChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_STOP -> {
                shellCoordinator.setServiceEnabled(false)
                stopForeground(STOP_FOREGROUND_REMOVE)
                stopSelf()
                return Service.START_NOT_STICKY
            }
            ACTION_VOICE_COMMAND -> listenForVoiceCommand(manualTrigger = true)
            ACTION_WAKE_ONLY -> startWakePhraseIfEnabled()
            else -> Unit
        }

        startForeground(NOTIFICATION_ID, buildNotification(getString(R.string.notification_starting)))
        startWakePhraseIfEnabled()
        startPolling()
        shellCoordinator.setServiceEnabled(true)
        return Service.START_STICKY
    }

    override fun onDestroy() {
        pollingJob?.cancel()
        wakePhraseManager?.stop()
        commandProcessor?.stop()
        speechOutput.shutdown()
        shellCoordinator.clearActiveVoiceSurface(ShellState.ActiveVoiceSurface.SHELL_SERVICE)
        shellCoordinator.setServiceEnabled(false)
        super.onDestroy()
    }

    override fun onBind(intent: Intent): IBinder? = super.onBind(intent)

    private fun startPolling() {
        pollingJob?.cancel()
        pollingJob = lifecycleScope.launch {
            while (true) {
                val snapshot = shellCoordinator.performStartup()
                val content = if (snapshot.backendReachable) {
                    getString(R.string.notification_backend_online)
                } else {
                    getString(R.string.notification_backend_offline)
                }
                val manager = getSystemService(NotificationManager::class.java)
                manager.notify(NOTIFICATION_ID, buildNotification(content))
                delay(15_000)
            }
        }
    }

    private fun startWakePhraseIfEnabled() {
        if (!prefs.getBoolean(PREF_WAKE_ENABLED, false)) {
            wakePhraseManager?.stop()
            wakePhraseManager = null
            return
        }
        val phrase = prefs.getString(PREF_WAKE_PHRASE, DEFAULT_WAKE_PHRASE) ?: DEFAULT_WAKE_PHRASE
        wakePhraseManager?.stop()
        wakePhraseManager = WakePhraseManager(
            context = this,
            phrase = phrase,
            onWakePhraseHeard = {
                shellCoordinator.startRuntime()
                val manager = getSystemService(NotificationManager::class.java)
                manager.notify(NOTIFICATION_ID, buildNotification(getString(R.string.notification_wake_phrase_heard)))
                listenForVoiceCommand(manualTrigger = false)
            },
            onWakeTranscript = { transcript ->
                lifecycleScope.launch {
                    voiceSessionController.postPartialTranscript("shell-service", transcript)
                }
            },
        )
        wakePhraseManager?.start()
    }

    private fun listenForVoiceCommand(manualTrigger: Boolean) {
        if (MordecaiAccessibilityService.requestVoiceCommand(manualTrigger)) {
            val manager = getSystemService(NotificationManager::class.java)
            manager.notify(NOTIFICATION_ID, buildNotification(getString(R.string.notification_overlay_active)))
            return
        }
        shellCoordinator.setActiveVoiceSurface(ShellState.ActiveVoiceSurface.SHELL_SERVICE)
        lifecycleScope.launch {
            speechOutput.interrupt()
            voiceSessionController.prepareForCommand("shell-service", currentWakePhrase())
        }
        commandProcessor?.stop()
        val manager = getSystemService(NotificationManager::class.java)
        manager.notify(NOTIFICATION_ID, buildNotification(getString(R.string.notification_listening_for_command)))
        commandProcessor = SpeechCommandProcessor(
            context = this,
            onCommandHeard = { command ->
                lifecycleScope.launch {
                    val result = voiceSessionController.submitFinalCommand("shell-service", command)
                    val spokenReply = result?.lastResponse ?: result?.planResponse
                    if (result?.ok == true && !spokenReply.isNullOrBlank()) {
                        speechOutput.speak(spokenReply)
                        manager.notify(NOTIFICATION_ID, buildNotification(spokenReply))
                    } else {
                        shellCoordinator.clearActiveVoiceSurface(ShellState.ActiveVoiceSurface.SHELL_SERVICE)
                        val errorMessage = result?.error ?: getString(R.string.notification_command_failed)
                        manager.notify(NOTIFICATION_ID, buildNotification(errorMessage))
                    }
                }
            },
            onFailure = { error ->
                shellCoordinator.clearActiveVoiceSurface(ShellState.ActiveVoiceSurface.SHELL_SERVICE)
                val message = if (manualTrigger) error else getString(R.string.notification_command_timeout)
                manager.notify(NOTIFICATION_ID, buildNotification(message))
            },
            onTranscript = { transcript ->
                lifecycleScope.launch {
                    voiceSessionController.postPartialTranscript("shell-service", transcript)
                }
            },
        )
        commandProcessor?.startListening()
    }

    private fun currentWakePhrase(): String {
        return prefs.getString(PREF_WAKE_PHRASE, DEFAULT_WAKE_PHRASE) ?: DEFAULT_WAKE_PHRASE
    }

    private fun buildNotification(content: String): Notification {
        val openIntent = PendingIntent.getActivity(
            this,
            100,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        val stopIntent = PendingIntent.getService(
            this,
            101,
            Intent(this, MordecaiShellService::class.java).setAction(ACTION_STOP),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        val voiceIntent = PendingIntent.getService(
            this,
            102,
            Intent(this, MordecaiShellService::class.java).setAction(ACTION_VOICE_COMMAND),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle(getString(R.string.app_name))
            .setContentText(content)
            .setSmallIcon(R.drawable.ic_mordecai_foreground)
            .setOngoing(true)
            .setContentIntent(openIntent)
            .addAction(0, getString(R.string.action_voice_command), voiceIntent)
            .addAction(0, getString(R.string.action_stop_service), stopIntent)
            .setStyle(NotificationCompat.BigTextStyle().bigText(content))
            .build()
    }

    private fun createChannel() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) {
            return
        }
        val manager = getSystemService(NotificationManager::class.java)
        val channel = NotificationChannel(CHANNEL_ID, getString(R.string.channel_name), NotificationManager.IMPORTANCE_LOW)
        channel.description = getString(R.string.channel_description)
        manager.createNotificationChannel(channel)
    }

    companion object {
        private const val CHANNEL_ID = "mordecai-shell"
        private const val NOTIFICATION_ID = 40
        private const val PREFS_NAME = "mordecai-shell-prefs"
        const val PREF_AUTO_START = "auto_start_backend"
        const val PREF_BACKEND_URL = "backend_url"
        const val PREF_WAKE_ENABLED = "wake_enabled"
        const val PREF_WAKE_PHRASE = "wake_phrase"
        const val PREF_ADVANCED_ENABLED = "advanced_enabled"
        const val PREF_SERVICE_ENABLED = "service_enabled"
        const val PREF_LAST_REPLY = "last_reply"
        const val PREF_LOCKSCREEN_OVERLAY = "lockscreen_overlay_enabled"
        const val DEFAULT_WAKE_PHRASE = "mordecai"
        const val ACTION_STOP = "ai.mordecai.shell.action.STOP"
        const val ACTION_WAKE_ONLY = "ai.mordecai.shell.action.WAKE_ONLY"
        const val ACTION_VOICE_COMMAND = "ai.mordecai.shell.action.VOICE_COMMAND"

        fun start(context: Context, action: String? = null) {
            val intent = Intent(context, MordecaiShellService::class.java).apply {
                if (action != null) {
                    setAction(action)
                }
            }
            ContextCompat.startForegroundService(context, intent)
        }
    }
}