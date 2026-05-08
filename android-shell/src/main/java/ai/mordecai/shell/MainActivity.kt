package ai.mordecai.shell

import android.Manifest
import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.webkit.WebChromeClient
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import ai.mordecai.shell.accessibility.MordecaiAccessibilityService
import ai.mordecai.shell.databinding.ActivityMainBinding
import kotlinx.coroutines.launch

class MainActivity : AppCompatActivity() {
    private lateinit var binding: ActivityMainBinding
    private lateinit var commandClient: TermuxCommandClient
    private lateinit var backendSupervisor: BackendSupervisor
    private lateinit var prefs: android.content.SharedPreferences
    private val rootDetector = RootDetector()

    private val permissionLauncher = registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { }

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
        binding.inputBackendUrl.setText(prefs.getString(MordecaiShellService.PREF_BACKEND_URL, BackendSupervisor.DEFAULT_BASE_URL))
        binding.inputWakePhrase.setText(prefs.getString(MordecaiShellService.PREF_WAKE_PHRASE, MordecaiShellService.DEFAULT_WAKE_PHRASE))
        refreshStatus()
        binding.dashboardView.loadUrl(currentBackendUrl())
    }

    override fun onResume() {
        super.onResume()
        refreshStatus()
    }

    private fun bindUi() {
        binding.buttonInstall.setOnClickListener {
            handleCommand(commandClient.installRuntime())
        }
        binding.buttonStart.setOnClickListener {
            persistTextSettings()
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
            persistTextSettings()
            binding.dashboardView.reload()
            refreshStatus()
        }
        binding.buttonSaveSettings.setOnClickListener {
            persistTextSettings()
            binding.dashboardView.loadUrl(currentBackendUrl())
            refreshStatus()
            toast(getString(R.string.settings_saved))
        }
        binding.buttonOpenTermux.setOnClickListener {
            openTermux()
        }
        binding.buttonAccessibilitySettings.setOnClickListener {
            openAccessibilitySettings()
        }
        binding.buttonNotificationSettings.setOnClickListener {
            openNotificationSettings()
        }

        binding.switchService.setOnCheckedChangeListener { _, checked ->
            if (checked) {
                requestRuntimePermissions()
                MordecaiShellService.start(this)
            } else {
                stopService(Intent(this, MordecaiShellService::class.java).setAction(MordecaiShellService.ACTION_STOP))
            }
            prefs.edit().putBoolean(MordecaiShellService.PREF_SERVICE_ENABLED, checked).apply()
        }

        binding.switchWake.setOnCheckedChangeListener { _, checked ->
            requestRuntimePermissions()
            prefs.edit().putBoolean(MordecaiShellService.PREF_WAKE_ENABLED, checked).apply()
            if (binding.switchService.isChecked) {
                MordecaiShellService.start(this)
            }
        }

        binding.switchAdvanced.setOnCheckedChangeListener { _, checked ->
            if (!rootDetector.isRootAvailable()) {
                binding.switchAdvanced.isChecked = false
                toast(getString(R.string.advanced_mode_requires_root))
                return@setOnCheckedChangeListener
            }
            prefs.edit().putBoolean(MordecaiShellService.PREF_ADVANCED_ENABLED, checked).apply()
            handleCommand(backendSupervisor.setAdvancedMode(checked))
        }

        binding.switchAutoStart.setOnCheckedChangeListener { _, checked ->
            prefs.edit().putBoolean(MordecaiShellService.PREF_AUTO_START, checked).apply()
        }

        binding.switchOverlay.setOnCheckedChangeListener { _, checked ->
            prefs.edit().putBoolean(MordecaiShellService.PREF_LOCKSCREEN_OVERLAY, checked).apply()
            val connected = MordecaiAccessibilityService.refreshOverlay(this)
            if (checked && !MordecaiAccessibilityService.isEnabled(this)) {
                toast(getString(R.string.accessibility_required_message))
                openAccessibilitySettings()
                return@setOnCheckedChangeListener
            }
            if (connected) {
                toast(getString(R.string.overlay_sync_complete))
            }
        }
    }

    private fun refreshStatus() {
        val termuxInstalled = commandClient.isTermuxInstalled()
        val rooted = rootDetector.isRootAvailable()
        binding.textTermuxStatus.text = if (termuxInstalled) getString(R.string.termux_detected) else getString(R.string.termux_missing)
        binding.textRootStatus.text = if (rooted) getString(R.string.root_available) else getString(R.string.root_unavailable)
        binding.textAccessibilityStatus.text = if (MordecaiAccessibilityService.isEnabled(this)) {
            getString(R.string.accessibility_enabled)
        } else {
            getString(R.string.accessibility_disabled)
        }
        binding.switchAdvanced.isEnabled = rooted
        binding.switchService.isChecked = prefs.getBoolean(MordecaiShellService.PREF_SERVICE_ENABLED, false)
        binding.switchWake.isChecked = prefs.getBoolean(MordecaiShellService.PREF_WAKE_ENABLED, false)
        binding.switchAutoStart.isChecked = prefs.getBoolean(MordecaiShellService.PREF_AUTO_START, true)
        binding.switchOverlay.isChecked = prefs.getBoolean(MordecaiShellService.PREF_LOCKSCREEN_OVERLAY, true)
        binding.switchAdvanced.isChecked = prefs.getBoolean(MordecaiShellService.PREF_ADVANCED_ENABLED, false) && rooted

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

    private fun persistTextSettings() {
        prefs.edit()
            .putString(MordecaiShellService.PREF_BACKEND_URL, currentBackendUrl())
            .putString(MordecaiShellService.PREF_WAKE_PHRASE, currentWakePhrase())
            .apply()
    }

    private fun currentBackendUrl(): String {
        val raw = binding.inputBackendUrl.text?.toString()?.trim().orEmpty()
        return if (raw.isBlank()) BackendSupervisor.DEFAULT_BASE_URL else raw.removeSuffix("/")
    }

    private fun currentWakePhrase(): String {
        val raw = binding.inputWakePhrase.text?.toString()?.trim().orEmpty()
        return if (raw.isBlank()) MordecaiShellService.DEFAULT_WAKE_PHRASE else raw
    }

    private fun requestRuntimePermissions() {
        val permissions = mutableListOf<String>()
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            permissions += Manifest.permission.RECORD_AUDIO
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU && ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            permissions += Manifest.permission.POST_NOTIFICATIONS
        }
        if (permissions.isNotEmpty()) {
            permissionLauncher.launch(permissions.toTypedArray())
        }
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

    private fun openAccessibilitySettings() {
        startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))
    }

    private fun openNotificationSettings() {
        val intent = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS).apply {
                putExtra(Settings.EXTRA_APP_PACKAGE, packageName)
            }
        } else {
            Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
                data = Uri.parse("package:$packageName")
            }
        }
        startActivity(intent)
    }

    private fun toast(message: String) {
        Toast.makeText(this, message, Toast.LENGTH_SHORT).show()
    }

}