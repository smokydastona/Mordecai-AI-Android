package ai.mordecai.shell

import ai.mordecai.shell.backend.RuntimeCommandGateway
import ai.mordecai.shell.backend.ShellBackendClient
import org.json.JSONObject

class BackendSupervisor(
    val backendClient: ShellBackendClient,
    val runtimeGateway: RuntimeCommandGateway,
) {
    constructor(
        commandClient: TermuxCommandClient,
        baseUrlProvider: () -> String = { DEFAULT_BASE_URL },
    ) : this(
        backendClient = ShellBackendClient(baseUrlProvider),
        runtimeGateway = RuntimeCommandGateway(commandClient),
    )

    suspend fun checkHealth(): ShellBackendClient.HealthSnapshot = backendClient.checkHealth()

    suspend fun chat(message: String): ShellBackendClient.ChatSnapshot = backendClient.chat(message)

    suspend fun runtimeStatus(): ShellBackendClient.RuntimeStatusSnapshot = backendClient.runtimeStatus()

    suspend fun avatar(): ShellBackendClient.AvatarSnapshot = backendClient.avatar()

    suspend fun startVoiceSession(label: String, background: Boolean): ShellBackendClient.VoiceSessionSnapshot =
        backendClient.startVoiceSession(label, background)

    suspend fun postVoiceSessionEvent(
        sessionId: String,
        transcript: String,
        isFinal: Boolean,
        interrupt: Boolean = false,
        playbackFinished: Boolean = false,
        autoExecute: Boolean = true,
    ): ShellBackendClient.VoiceEventSnapshot =
        backendClient.postVoiceSessionEvent(sessionId, transcript, isFinal, interrupt, playbackFinished, autoExecute)

    suspend fun ingestPerception(payload: JSONObject): Boolean = backendClient.ingestPerception(payload)

    fun installRuntime() = runtimeGateway.installRuntime()

    fun startRuntime() = runtimeGateway.startRuntime()

    fun stopRuntime() = runtimeGateway.stopRuntime()

    fun updateRuntime() = runtimeGateway.updateRuntime()

    fun configureAiProvider(providerMode: String, baseUrl: String, apiKey: String, model: String) =
        runtimeGateway.configureAiProvider(providerMode, baseUrl, apiKey, model)

    fun setAdvancedMode(enabled: Boolean) = runtimeGateway.setAdvancedMode(enabled)

    companion object {
        const val DEFAULT_BASE_URL = ShellBackendClient.DEFAULT_BASE_URL
    }
}