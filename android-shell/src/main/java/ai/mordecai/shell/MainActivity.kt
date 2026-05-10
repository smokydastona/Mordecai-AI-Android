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
import androidx.lifecycle.lifecycleScope
import ai.mordecai.shell.databinding.ActivityMainBinding
import kotlinx.coroutines.launch

class MainActivity : AppCompatActivity() {
    companion object {
        private const val PREF_WELCOME_COMPLETED = "welcome_completed"
        private const val MESSAGE_WELCOME_SKIPPED = "Welcome setup skipped. Open the settings menu to review permissions later."
    }

    private lateinit var binding: ActivityMainBinding
    private lateinit var commandClient: TermuxCommandClient
    private lateinit var backendSupervisor: BackendSupervisor
    private lateinit var prefs: android.content.SharedPreferences
    private val rootDetector = RootDetector()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        commandClient = TermuxCommandClient(this)
        prefs = getSharedPreferences("mordecai-shell-prefs", Context.MODE_PRIVATE)
        backendSupervisor = BackendSupervisor(commandClient) {
            prefs.getString(MordecaiShellService.PREF_BACKEND_URL, BackendSupervisor.DEFAULT_BASE_URL) ?: BackendSupervisor.DEFAULT_BASE_URL
        }

        configureWebView(binding.dashboardView)
        bindUi()
        refreshStatus()
        updateWelcomeState()
        binding.dashboardView.loadUrl(currentBackendUrl())
    }

    override fun onResume() {
        super.onResume()
        refreshStatus()
        binding.dashboardView.loadUrl(currentBackendUrl())
    }

    private fun bindUi() {
        binding.buttonSettings.setOnClickListener {
            openSettings()
        }
        binding.buttonInstall.setOnClickListener {
            handleCommand(commandClient.installRuntime())
        }
        binding.buttonStart.setOnClickListener {
            handleCommand(backendSupervisor.startRuntime())
            binding.dashboardView.loadUrl(currentBackendUrl())
        }
        binding.buttonStop.setOnClickListener {
            handleCommand(backendSupervisor.stopRuntime())
        }
        binding.buttonUpdate.setOnClickListener {
            handleCommand(backendSupervisor.updateRuntime())
        }
        binding.buttonRefresh.setOnClickListener {
            binding.dashboardView.reload()
            refreshStatus()
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

    private fun refreshStatus() {
        val termuxInstalled = commandClient.isTermuxInstalled()
        val rooted = rootDetector.isRootAvailable()
        binding.textTermuxStatus.text = if (termuxInstalled) getString(R.string.termux_detected) else getString(R.string.termux_missing)
        binding.textRootStatus.text = if (rooted) getString(R.string.root_available) else getString(R.string.root_unavailable)

        lifecycleScope.launch {
            val snapshot = backendSupervisor.checkHealth()
            binding.textBackendStatus.text = if (snapshot.reachable) {
                getString(R.string.backend_online)
            } else {
                getString(R.string.backend_offline, snapshot.status)
            }
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

    private fun currentBackendUrl(): String {
        val raw = prefs.getString(MordecaiShellService.PREF_BACKEND_URL, BackendSupervisor.DEFAULT_BASE_URL).orEmpty().trim()
        return if (raw.isBlank()) BackendSupervisor.DEFAULT_BASE_URL else raw.removeSuffix("/")
    }

    private fun handleCommand(result: TermuxCommandClient.CommandResult) {
        toast(result.message)
        refreshStatus()
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