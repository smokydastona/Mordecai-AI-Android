package ai.mordecai.shell

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.view.View
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import ai.mordecai.shell.accessibility.MordecaiAccessibilityService
import ai.mordecai.shell.databinding.ActivitySettingsBinding
import kotlinx.coroutines.launch

class SettingsActivity : AppCompatActivity() {
    private data class PermissionStep(
        val title: String,
        val message: String,
        val actionLabel: String,
        val waitForReturn: Boolean = false,
        val action: () -> Unit,
    )

    companion object {
        const val EXTRA_START_PERMISSION_ONBOARDING = "start_permission_onboarding"
        private const val PROFILE_RULE_BASED = "rule-based"
        private const val PROFILE_CLOUD = "cloud"
        private const val PROFILE_LOCAL = "local"

        private const val MESSAGE_PERMISSIONS_STILL_NEEDED = "Some permissions are still denied. You can review them again from this settings screen."
        private const val TITLE_MICROPHONE = "Allow microphone access"
        private const val MESSAGE_MICROPHONE = "Microphone access is required for wake-phrase listening and voice command capture. Mordecai only uses it for explicit shell voice features."
        private const val TITLE_NOTIFICATIONS = "Allow notification access"
        private const val MESSAGE_NOTIFICATIONS = "Notification permission keeps foreground service status visible and lets the shell surface backend and voice-state updates clearly."
        private const val TITLE_ACCESSIBILITY = "Enable accessibility service"
        private const val MESSAGE_ACCESSIBILITY = "Accessibility access is required for the lock-screen overlay, safe local actions, and continuous perception updates into the backend. Android will take you to the system accessibility screen."
        private const val LABEL_ALLOW = "Allow"
        private const val LABEL_NOT_NOW = "Not now"
        private const val MESSAGE_PERMISSIONS_READY = "Core permissions already look good."
        private const val MESSAGE_AI_PROVIDER_INCOMPLETE = "The selected AI profile needs a base URL, API key or token, and model name before it can be applied."
        private const val SUMMARY_TERMUX_READY = "Termux ready"
        private const val SUMMARY_TERMUX_MISSING = "Termux missing"
        private const val SUMMARY_ROOT_READY = "Root available"
        private const val SUMMARY_ROOT_UNAVAILABLE = "Root unavailable"
        private const val SUMMARY_ACCESSIBILITY_READY = "Accessibility enabled"
        private const val SUMMARY_ACCESSIBILITY_MISSING = "Accessibility disabled"
        private const val SUMMARY_MICROPHONE_READY = "Microphone permission granted"
        private const val SUMMARY_MICROPHONE_MISSING = "Microphone permission missing"
        private const val SUMMARY_NOTIFICATIONS_READY = "Notification permission granted"
        private const val SUMMARY_NOTIFICATIONS_MISSING = "Notification permission missing"
        private const val SUMMARY_SERVICE_ENABLED = "Shell service enabled"
        private const val SUMMARY_SERVICE_DISABLED = "Shell service disabled"
        private const val SUMMARY_MODEL_RULE_BASED = "Active model profile: rule-based"
        private const val SUMMARY_UNKNOWN_PROVIDER = "unknown"
        private const val SUMMARY_BACKEND_UNAVAILABLE = "Backend unavailable"
    }

    private lateinit var binding: ActivitySettingsBinding
    private lateinit var commandClient: TermuxCommandClient
    private lateinit var backendSupervisor: BackendSupervisor
    private lateinit var prefs: android.content.SharedPreferences
    private val rootDetector = RootDetector()
    private val pendingPermissionSteps = ArrayDeque<PermissionStep>()
    private var permissionDialogVisible = false
    private var awaitingPermissionContinuation = false
    private var updatingUi = false

    private val permissionLauncher = registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { result ->
        val denied = result.filterValues { granted -> !granted }.keys
        if (denied.isNotEmpty()) {
            toast(MESSAGE_PERMISSIONS_STILL_NEEDED)
        }
        awaitingPermissionContinuation = false
        refreshStatus()
        showNextPermissionStep()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivitySettingsBinding.inflate(layoutInflater)
        setContentView(binding.root)

        commandClient = TermuxCommandClient(this)
        prefs = getSharedPreferences("mordecai-shell-prefs", Context.MODE_PRIVATE)
        backendSupervisor = BackendSupervisor(commandClient) {
            prefs.getString(MordecaiShellService.PREF_BACKEND_URL, BackendSupervisor.DEFAULT_BASE_URL) ?: BackendSupervisor.DEFAULT_BASE_URL
        }

        bindUi()
        refreshStatus()

        if (intent.getBooleanExtra(EXTRA_START_PERMISSION_ONBOARDING, false)) {
            binding.root.post {
                launchPermissionOnboarding(includeAccessibility = true, forceReview = true)
            }
        }
    }

    override fun onResume() {
        super.onResume()
        refreshStatus()
        if (awaitingPermissionContinuation) {
            awaitingPermissionContinuation = false
            showNextPermissionStep()
        }
    }

    private fun bindUi() {
        binding.buttonBackFromSettings.setOnClickListener {
            finish()
        }
        binding.buttonSaveSettings.setOnClickListener {
            persistTextSettings()
            refreshStatus()
            toast(getString(R.string.settings_saved))
        }
        binding.buttonAccessibilitySettings.setOnClickListener {
            openAccessibilitySettings()
        }
        binding.buttonNotificationSettings.setOnClickListener {
            openNotificationSettings()
        }
        binding.buttonReviewPermissions.setOnClickListener {
            launchPermissionOnboarding(includeAccessibility = true, forceReview = true)
        }
        binding.buttonApplyAiSettings.setOnClickListener {
            persistAiSettings()
        }

        binding.radioProviderRuleBased.setOnCheckedChangeListener { _, isChecked ->
            if (!updatingUi && isChecked) {
                updateAiProfileVisibility()
            }
        }
        binding.radioProviderCloud.setOnCheckedChangeListener { _, isChecked ->
            if (!updatingUi && isChecked) {
                updateAiProfileVisibility()
            }
        }
        binding.radioProviderLocal.setOnCheckedChangeListener { _, isChecked ->
            if (!updatingUi && isChecked) {
                updateAiProfileVisibility()
            }
        }

        binding.switchService.setOnCheckedChangeListener { _, checked ->
            if (updatingUi) {
                return@setOnCheckedChangeListener
            }
            if (checked) {
                requestRuntimePermissions()
                MordecaiShellService.start(this)
            } else {
                stopService(Intent(this, MordecaiShellService::class.java).setAction(MordecaiShellService.ACTION_STOP))
            }
            prefs.edit().putBoolean(MordecaiShellService.PREF_SERVICE_ENABLED, checked).apply()
        }

        binding.switchWake.setOnCheckedChangeListener { _, checked ->
            if (updatingUi) {
                return@setOnCheckedChangeListener
            }
            requestRuntimePermissions()
            prefs.edit().putBoolean(MordecaiShellService.PREF_WAKE_ENABLED, checked).apply()
            if (binding.switchService.isChecked) {
                MordecaiShellService.start(this)
            }
        }

        binding.switchAdvanced.setOnCheckedChangeListener { _, checked ->
            if (updatingUi) {
                return@setOnCheckedChangeListener
            }
            if (!rootDetector.isRootAvailable()) {
                binding.switchAdvanced.isChecked = false
                toast(getString(R.string.advanced_mode_requires_root))
                return@setOnCheckedChangeListener
            }
            prefs.edit().putBoolean(MordecaiShellService.PREF_ADVANCED_ENABLED, checked).apply()
            handleCommand(backendSupervisor.setAdvancedMode(checked))
        }

        binding.switchAutoStart.setOnCheckedChangeListener { _, checked ->
            if (updatingUi) {
                return@setOnCheckedChangeListener
            }
            prefs.edit().putBoolean(MordecaiShellService.PREF_AUTO_START, checked).apply()
        }

        binding.switchOverlay.setOnCheckedChangeListener { _, checked ->
            if (updatingUi) {
                return@setOnCheckedChangeListener
            }
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
        updatingUi = true
        binding.inputBackendUrl.setText(prefs.getString(MordecaiShellService.PREF_BACKEND_URL, BackendSupervisor.DEFAULT_BASE_URL))
        binding.inputWakePhrase.setText(prefs.getString(MordecaiShellService.PREF_WAKE_PHRASE, MordecaiShellService.DEFAULT_WAKE_PHRASE))
        binding.inputCloudBaseUrl.setText(prefs.getString(PREF_CLOUD_BASE_URL, "https://api.openai.com/v1"))
        binding.inputCloudApiKey.setText(prefs.getString(PREF_CLOUD_API_KEY, ""))
        binding.inputCloudModel.setText(prefs.getString(PREF_CLOUD_MODEL, "gpt-4.1-mini"))
        binding.inputLocalBaseUrl.setText(prefs.getString(PREF_LOCAL_BASE_URL, "http://127.0.0.1:11434/v1"))
        binding.inputLocalApiKey.setText(prefs.getString(PREF_LOCAL_API_KEY, "local-token"))
        binding.inputLocalModel.setText(prefs.getString(PREF_LOCAL_MODEL, "llama3.1"))
        binding.textAccessibilityStatus.text = if (MordecaiAccessibilityService.isEnabled(this)) {
            getString(R.string.accessibility_enabled)
        } else {
            getString(R.string.accessibility_disabled)
        }
        binding.switchService.isChecked = prefs.getBoolean(MordecaiShellService.PREF_SERVICE_ENABLED, false)
        binding.switchWake.isChecked = prefs.getBoolean(MordecaiShellService.PREF_WAKE_ENABLED, false)
        binding.switchAutoStart.isChecked = prefs.getBoolean(MordecaiShellService.PREF_AUTO_START, true)
        binding.switchOverlay.isChecked = prefs.getBoolean(MordecaiShellService.PREF_LOCKSCREEN_OVERLAY, true)
        val rooted = rootDetector.isRootAvailable()
        binding.switchAdvanced.isEnabled = rooted
        binding.switchAdvanced.isChecked = prefs.getBoolean(MordecaiShellService.PREF_ADVANCED_ENABLED, false) && rooted
        when (prefs.getString(PREF_MODEL_PROFILE_MODE, PROFILE_RULE_BASED)) {
            PROFILE_CLOUD -> binding.radioProviderCloud.isChecked = true
            PROFILE_LOCAL -> binding.radioProviderLocal.isChecked = true
            else -> binding.radioProviderRuleBased.isChecked = true
        }
        updateAiProfileVisibility()
        updateStatusSummary()
        updatingUi = false
    }

    private fun persistTextSettings() {
        prefs.edit()
            .putString(MordecaiShellService.PREF_BACKEND_URL, currentBackendUrl())
            .putString(MordecaiShellService.PREF_WAKE_PHRASE, currentWakePhrase())
            .apply()
    }

    private fun persistAiSettings() {
        val mode = selectedProfileMode()
        val editor = prefs.edit()
            .putString(PREF_MODEL_PROFILE_MODE, mode)
            .putString(PREF_CLOUD_BASE_URL, currentCloudBaseUrl())
            .putString(PREF_CLOUD_API_KEY, currentCloudApiKey())
            .putString(PREF_CLOUD_MODEL, currentCloudModel())
            .putString(PREF_LOCAL_BASE_URL, currentLocalBaseUrl())
            .putString(PREF_LOCAL_API_KEY, currentLocalApiKey())
            .putString(PREF_LOCAL_MODEL, currentLocalModel())
        editor.apply()

        if (mode != PROFILE_RULE_BASED) {
            val baseUrl = if (mode == PROFILE_CLOUD) currentCloudBaseUrl() else currentLocalBaseUrl()
            val apiKey = if (mode == PROFILE_CLOUD) currentCloudApiKey() else currentLocalApiKey()
            val model = if (mode == PROFILE_CLOUD) currentCloudModel() else currentLocalModel()
            if (baseUrl.isBlank() || apiKey.isBlank() || model.isBlank()) {
                toast(MESSAGE_AI_PROVIDER_INCOMPLETE)
                return
            }
        }

        val result = if (mode == PROFILE_RULE_BASED) {
            backendSupervisor.configureAiProvider(PROFILE_RULE_BASED, "", "", "")
        } else if (mode == PROFILE_CLOUD) {
            backendSupervisor.configureAiProvider(PROFILE_CLOUD, currentCloudBaseUrl(), currentCloudApiKey(), currentCloudModel())
        } else {
            backendSupervisor.configureAiProvider(PROFILE_LOCAL, currentLocalBaseUrl(), currentLocalApiKey(), currentLocalModel())
        }
        handleCommand(result)
        binding.textAiConfigStatus.text = result.message
        refreshStatus()
    }

    private fun currentBackendUrl(): String {
        val raw = binding.inputBackendUrl.text?.toString()?.trim().orEmpty()
        return if (raw.isBlank()) BackendSupervisor.DEFAULT_BASE_URL else raw.removeSuffix("/")
    }

    private fun currentWakePhrase(): String {
        val raw = binding.inputWakePhrase.text?.toString()?.trim().orEmpty()
        return if (raw.isBlank()) MordecaiShellService.DEFAULT_WAKE_PHRASE else raw
    }

    private fun currentCloudBaseUrl(): String = binding.inputCloudBaseUrl.text?.toString()?.trim().orEmpty()

    private fun currentCloudApiKey(): String = binding.inputCloudApiKey.text?.toString()?.trim().orEmpty()

    private fun currentCloudModel(): String = binding.inputCloudModel.text?.toString()?.trim().orEmpty()

    private fun currentLocalBaseUrl(): String = binding.inputLocalBaseUrl.text?.toString()?.trim().orEmpty()

    private fun currentLocalApiKey(): String = binding.inputLocalApiKey.text?.toString()?.trim().orEmpty()

    private fun currentLocalModel(): String = binding.inputLocalModel.text?.toString()?.trim().orEmpty()

    private fun selectedProfileMode(): String = when {
        binding.radioProviderCloud.isChecked -> PROFILE_CLOUD
        binding.radioProviderLocal.isChecked -> PROFILE_LOCAL
        else -> PROFILE_RULE_BASED
    }

    private fun updateAiProfileVisibility() {
        val mode = selectedProfileMode()
        binding.cloudProfileFields.visibility = if (mode == PROFILE_CLOUD) View.VISIBLE else View.GONE
        binding.localProfileFields.visibility = if (mode == PROFILE_LOCAL) View.VISIBLE else View.GONE
    }

    private fun updateStatusSummary() {
        val termuxInstalled = commandClient.isTermuxInstalled()
        val rooted = rootDetector.isRootAvailable()
        val microphoneGranted = ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED
        val notificationsGranted = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED
        } else {
            true
        }
        binding.textSummaryTermux.text = if (termuxInstalled) SUMMARY_TERMUX_READY else SUMMARY_TERMUX_MISSING
        binding.textSummaryRoot.text = if (rooted) SUMMARY_ROOT_READY else SUMMARY_ROOT_UNAVAILABLE
        binding.textSummaryAccessibility.text = if (MordecaiAccessibilityService.isEnabled(this)) SUMMARY_ACCESSIBILITY_READY else SUMMARY_ACCESSIBILITY_MISSING
        binding.textSummaryMicrophone.text = if (microphoneGranted) SUMMARY_MICROPHONE_READY else SUMMARY_MICROPHONE_MISSING
        binding.textSummaryNotifications.text = if (notificationsGranted) SUMMARY_NOTIFICATIONS_READY else SUMMARY_NOTIFICATIONS_MISSING
        binding.textSummaryService.text = if (prefs.getBoolean(MordecaiShellService.PREF_SERVICE_ENABLED, false)) SUMMARY_SERVICE_ENABLED else SUMMARY_SERVICE_DISABLED

        val mode = prefs.getString(PREF_MODEL_PROFILE_MODE, PROFILE_RULE_BASED) ?: PROFILE_RULE_BASED
        val modelSummary = when (mode) {
            PROFILE_CLOUD -> "Active model profile: cloud (${prefs.getString(PREF_CLOUD_MODEL, "gpt-4.1-mini")})"
            PROFILE_LOCAL -> "Active model profile: local (${prefs.getString(PREF_LOCAL_MODEL, "llama3.1")})"
            else -> SUMMARY_MODEL_RULE_BASED
        }
        binding.textSummaryModel.text = modelSummary

        lifecycleScope.launch {
            val status = backendSupervisor.runtimeStatus()
            binding.textSummaryBackend.text = if (status.ok) {
                "Backend online: provider=${status.provider ?: SUMMARY_UNKNOWN_PROVIDER}"
            } else {
                "Backend offline: ${status.error ?: SUMMARY_BACKEND_UNAVAILABLE}"
            }
        }
    }

    private fun requestRuntimePermissions() {
        launchPermissionOnboarding(includeAccessibility = false, forceReview = false)
    }

    private fun launchPermissionOnboarding(includeAccessibility: Boolean, forceReview: Boolean) {
        pendingPermissionSteps.clear()

        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            pendingPermissionSteps += PermissionStep(
                title = TITLE_MICROPHONE,
                message = MESSAGE_MICROPHONE,
                actionLabel = LABEL_ALLOW,
                waitForReturn = true,
            ) {
                permissionLauncher.launch(arrayOf(Manifest.permission.RECORD_AUDIO))
            }
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU && ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            pendingPermissionSteps += PermissionStep(
                title = TITLE_NOTIFICATIONS,
                message = MESSAGE_NOTIFICATIONS,
                actionLabel = LABEL_ALLOW,
                waitForReturn = true,
            ) {
                permissionLauncher.launch(arrayOf(Manifest.permission.POST_NOTIFICATIONS))
            }
        }
        if (includeAccessibility && !MordecaiAccessibilityService.isEnabled(this)) {
            pendingPermissionSteps += PermissionStep(
                title = TITLE_ACCESSIBILITY,
                message = MESSAGE_ACCESSIBILITY,
                actionLabel = getString(R.string.action_open_accessibility_settings),
                waitForReturn = true,
            ) {
                openAccessibilitySettings()
            }
        }

        if (pendingPermissionSteps.isEmpty()) {
            if (forceReview) {
                toast(MESSAGE_PERMISSIONS_READY)
            }
            refreshStatus()
            return
        }

        awaitingPermissionContinuation = false
        showNextPermissionStep()
    }

    private fun showNextPermissionStep() {
        if (permissionDialogVisible || pendingPermissionSteps.isEmpty()) {
            return
        }
        val step = pendingPermissionSteps.removeFirst()
        permissionDialogVisible = true
        AlertDialog.Builder(this)
            .setTitle(step.title)
            .setMessage(step.message)
            .setPositiveButton(step.actionLabel) { dialog, _ ->
                if (step.waitForReturn) {
                    awaitingPermissionContinuation = true
                }
                step.action()
                dialog.dismiss()
            }
            .setNegativeButton(LABEL_NOT_NOW) { dialog, _ ->
                dialog.dismiss()
            }
            .setOnDismissListener {
                permissionDialogVisible = false
                if (!awaitingPermissionContinuation) {
                    showNextPermissionStep()
                }
            }
            .show()
    }

    private fun handleCommand(result: TermuxCommandClient.CommandResult) {
        toast(result.message)
        refreshStatus()
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
                data = android.net.Uri.parse("package:$packageName")
            }
        }
        startActivity(intent)
    }

    private fun toast(message: String) {
        Toast.makeText(this, message, Toast.LENGTH_SHORT).show()
    }

    companion object {
        private const val PREF_MODEL_PROFILE_MODE = "model_profile_mode"
        private const val PREF_CLOUD_BASE_URL = "cloud_openai_base_url"
        private const val PREF_CLOUD_API_KEY = "cloud_openai_api_key"
        private const val PREF_CLOUD_MODEL = "cloud_openai_model"
        private const val PREF_LOCAL_BASE_URL = "local_openai_base_url"
        private const val PREF_LOCAL_API_KEY = "local_openai_api_key"
        private const val PREF_LOCAL_MODEL = "local_openai_model"
    }
}