package ai.mordecai.shell

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val action = intent.action ?: return
        if (action != Intent.ACTION_BOOT_COMPLETED && action != Intent.ACTION_MY_PACKAGE_REPLACED) {
            return
        }
        val prefs = context.getSharedPreferences("mordecai-shell-prefs", Context.MODE_PRIVATE)
        if (prefs.getBoolean(MordecaiShellService.PREF_SERVICE_ENABLED, false)) {
            MordecaiShellService.start(context)
        }
    }
}