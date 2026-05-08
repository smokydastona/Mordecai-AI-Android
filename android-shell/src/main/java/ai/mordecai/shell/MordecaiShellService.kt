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
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

class MordecaiShellService : LifecycleService() {
    private lateinit var prefs: android.content.SharedPreferences
    private lateinit var backendSupervisor: BackendSupervisor
    private var wakePhraseManager: WakePhraseManager? = null
    private var pollingJob: Job? = null

    override fun onCreate() {
        super.onCreate()
        prefs = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        backendSupervisor = BackendSupervisor(TermuxCommandClient(this)) {
            prefs.getString(PREF_BACKEND_URL, BackendSupervisor.DEFAULT_BASE_URL) ?: BackendSupervisor.DEFAULT_BASE_URL
        }
        createChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_STOP -> {
                stopForeground(STOP_FOREGROUND_REMOVE)
                stopSelf()
                return Service.START_NOT_STICKY
            }
            ACTION_WAKE_ONLY -> startWakePhraseIfEnabled()
            else -> Unit
        }

        startForeground(NOTIFICATION_ID, buildNotification(getString(R.string.notification_starting)))
        startWakePhraseIfEnabled()
        startPolling()
        prefs.edit().putBoolean(PREF_SERVICE_ENABLED, true).apply()
        return Service.START_STICKY
    }

    override fun onDestroy() {
        pollingJob?.cancel()
        wakePhraseManager?.stop()
        prefs.edit().putBoolean(PREF_SERVICE_ENABLED, false).apply()
        super.onDestroy()
    }

    override fun onBind(intent: Intent): IBinder? = super.onBind(intent)

    private fun startPolling() {
        pollingJob?.cancel()
        pollingJob = lifecycleScope.launch {
            while (true) {
                val snapshot = backendSupervisor.checkHealth()
                val content = if (snapshot.reachable) {
                    getString(R.string.notification_backend_online)
                } else {
                    getString(R.string.notification_backend_offline)
                }
                val manager = getSystemService(NotificationManager::class.java)
                manager.notify(NOTIFICATION_ID, buildNotification(content))
                if (!snapshot.reachable && prefs.getBoolean(PREF_AUTO_START, true)) {
                    backendSupervisor.startRuntime()
                }
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
        wakePhraseManager = WakePhraseManager(this, phrase) {
            backendSupervisor.startRuntime()
            val manager = getSystemService(NotificationManager::class.java)
            manager.notify(NOTIFICATION_ID, buildNotification(getString(R.string.notification_wake_phrase_heard)))
        }
        wakePhraseManager?.start()
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
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle(getString(R.string.app_name))
            .setContentText(content)
            .setSmallIcon(R.drawable.ic_mordecai_foreground)
            .setOngoing(true)
            .setContentIntent(openIntent)
            .addAction(0, getString(R.string.action_stop_service), stopIntent)
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
        const val DEFAULT_WAKE_PHRASE = "mordecai"
        const val ACTION_STOP = "ai.mordecai.shell.action.STOP"
        const val ACTION_WAKE_ONLY = "ai.mordecai.shell.action.WAKE_ONLY"

        fun start(context: Context) {
            val intent = Intent(context, MordecaiShellService::class.java)
            ContextCompat.startForegroundService(context, intent)
        }
    }
}