package ai.mordecai.shell

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.net.HttpURLConnection
import java.net.URL

class BackendSupervisor(
    private val commandClient: TermuxCommandClient,
    private val baseUrlProvider: () -> String = { DEFAULT_BASE_URL },
) {
    data class HealthSnapshot(val reachable: Boolean, val status: String)

    suspend fun checkHealth(): HealthSnapshot = withContext(Dispatchers.IO) {
        try {
            val connection = URL("${baseUrlProvider()}/health").openConnection() as HttpURLConnection
            connection.requestMethod = "GET"
            connection.connectTimeout = 1500
            connection.readTimeout = 1500
            connection.inputStream.bufferedReader().use { reader ->
                val body = reader.readText()
                HealthSnapshot(connection.responseCode in 200..299, body)
            }
        } catch (error: Exception) {
            HealthSnapshot(false, error.message ?: "Backend unavailable")
        }
    }

    fun installRuntime() = commandClient.installRuntime()

    fun startRuntime() = commandClient.startRuntime()

    fun stopRuntime() = commandClient.stopRuntime()

    fun updateRuntime() = commandClient.updateRuntime()

    fun setAdvancedMode(enabled: Boolean) = commandClient.setAdvancedMode(enabled)

    companion object {
        const val DEFAULT_BASE_URL = "http://127.0.0.1:8000"
    }
}