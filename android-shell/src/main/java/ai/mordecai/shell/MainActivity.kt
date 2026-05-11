package ai.mordecai.shell

import android.Manifest
import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.view.View
import android.webkit.WebChromeClient
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import ai.mordecai.shell.coordinator.ShellCoordinator
import ai.mordecai.shell.state.ShellState
import ai.mordecai.shell.databinding.ActivityMainBinding
import kotlinx.coroutines.launch

class MainActivity : AppCompatActivity() {
    companion object {
        private const val PREF_WELCOME_COMPLETED = "welcome_completed"
        private const val MESSAGE_WELCOME_SKIPPED = "Welcome setup skipped. Open the settings menu to review permissions later."
    }

    private lateinit var binding: ActivityMainBinding
    private lateinit var shellCoordinator: ShellCoordinator
    private lateinit var prefs: android.content.SharedPreferences

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        shellCoordinator = ShellCoordinator.get(this)
        prefs = getSharedPreferences("mordecai-shell-prefs", Context.MODE_PRIVATE)

        configureWebView(binding.dashboardView)
        bindUi()
        observeShellState()
        updateWelcomeState()
        binding.dashboardView.loadUrl(shellCoordinator.currentBackendUrl())
        lifecycleScope.launch {
            shellCoordinator.performStartup()
        }
    }

    override fun onResume() {
        super.onResume()
        binding.dashboardView.loadUrl(shellCoordinator.currentBackendUrl())
        lifecycleScope.launch {
            shellCoordinator.performStartup()
        }
    }

    private fun bindUi() {
        binding.buttonSettings.setOnClickListener {
            openSettings()
        }
        binding.buttonInstall.setOnClickListener {
            handleCommand(shellCoordinator.installRuntime())
        }
        binding.buttonStart.setOnClickListener {
            handleCommand(shellCoordinator.startRuntime())
            binding.dashboardView.loadUrl(shellCoordinator.currentBackendUrl())
        }
        binding.buttonStop.setOnClickListener {
            handleCommand(shellCoordinator.stopRuntime())
        }
        binding.buttonUpdate.setOnClickListener {
            handleCommand(shellCoordinator.updateRuntime())
        }
        binding.buttonRefresh.setOnClickListener {
            binding.dashboardView.reload()
            lifecycleScope.launch {
                shellCoordinator.performStartup()
            }
        }
        binding.buttonOpenTermux.setOnClickListener {
            openTermux()
        }
        binding.buttonWelcomeStart.setOnClickListener {
            completeWelcome()
            openSettings(startPermissionOnboarding = true)
        }
        binding.buttonWelcomeSkip.setOnClickListener {
            completeWelcome()
            toast(MESSAGE_WELCOME_SKIPPED)
        }
    }

    private fun observeShellState() {
        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                shellCoordinator.state.collect { renderShellState(it) }
            }
        }
    }

    private fun renderShellState(state: ShellState) {
        binding.textTermuxStatus.text = if (state.termuxInstalled) getString(R.string.termux_detected) else getString(R.string.termux_missing)
        binding.textRootStatus.text = if (state.advancedModeAllowed) getString(R.string.root_available) else getString(R.string.root_unavailable)
        binding.textBackendStatus.text = if (state.backendReachable) {
            getString(R.string.backend_online)
        } else {
            getString(R.string.backend_offline, state.backendStatusText)
        }
        binding.textAccessibilityStatus.text = if (state.accessibilityEnabled) {
            getString(R.string.accessibility_enabled)
        } else {
            getString(R.string.accessibility_disabled)
        }
    }

    private fun configureWebView(webView: WebView) {
        webView.settings.javaScriptEnabled = true
        webView.settings.domStorageEnabled = true
        webView.webViewClient = WebViewClient()
        webView.webChromeClient = WebChromeClient()
    }

    private fun updateWelcomeState() {
        binding.welcomeOverlay.visibility = if (prefs.getBoolean(PREF_WELCOME_COMPLETED, false)) {
            View.GONE
        } else {
            View.VISIBLE
        }
    }

    private fun completeWelcome() {
        prefs.edit().putBoolean(PREF_WELCOME_COMPLETED, true).apply()
        updateWelcomeState()
    }

    private fun openSettings(startPermissionOnboarding: Boolean = false) {
        startActivity(Intent(this, SettingsActivity::class.java).apply {
            putExtra(SettingsActivity.EXTRA_START_PERMISSION_ONBOARDING, startPermissionOnboarding)
        })
    }

    private fun handleCommand(result: TermuxCommandClient.CommandResult) {
        toast(result.message)
        lifecycleScope.launch {
            shellCoordinator.performStartup()
        }
    }

    private fun openTermux() {
        val launchIntent = packageManager.getLaunchIntentForPackage(TermuxCommandClient.TERMUX_PACKAGE)
        if (launchIntent != null) {
            startActivity(launchIntent)
            return
        }
        val uri = Uri.parse("https://f-droid.org/packages/com.termux/")
        try {
            startActivity(Intent(Intent.ACTION_VIEW, uri))
        } catch (_: ActivityNotFoundException) {
            toast(getString(R.string.termux_missing))
        }
    }

    private fun toast(message: String) {
        Toast.makeText(this, message, Toast.LENGTH_SHORT).show()
    }

}