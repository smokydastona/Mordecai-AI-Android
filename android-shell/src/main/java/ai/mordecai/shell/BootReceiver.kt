package ai.mordecai.shell

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import ai.mordecai.shell.coordinator.ShellCoordinator

class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val action = intent.action ?: return
        if (action != Intent.ACTION_BOOT_COMPLETED && action != Intent.ACTION_MY_PACKAGE_REPLACED) {
            return
        }
        if (ShellCoordinator.get(context).isServiceEnabled()) {
            MordecaiShellService.start(context)
        }
    }
}