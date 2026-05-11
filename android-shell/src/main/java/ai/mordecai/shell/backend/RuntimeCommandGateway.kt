package ai.mordecai.shell.backend

import ai.mordecai.shell.TermuxCommandClient

class RuntimeCommandGateway(
    private val commandClient: TermuxCommandClient,
) {
    fun isTermuxInstalled(): Boolean = commandClient.isTermuxInstalled()

    fun installRuntime() = commandClient.installRuntime()

    fun startRuntime() = commandClient.startRuntime()

    fun stopRuntime() = commandClient.stopRuntime()

    fun updateRuntime() = commandClient.updateRuntime()

    fun configureAiProvider(providerMode: String, baseUrl: String, apiKey: String, model: String) =
        commandClient.configureAiProvider(providerMode, baseUrl, apiKey, model)

    fun setAdvancedMode(enabled: Boolean) = commandClient.setAdvancedMode(enabled)
}