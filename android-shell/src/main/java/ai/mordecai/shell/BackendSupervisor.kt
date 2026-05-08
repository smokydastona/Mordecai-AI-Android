package ai.mordecai.shell

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.net.HttpURLConnection
import java.net.URL
import java.io.OutputStreamWriter
import org.json.JSONArray
import org.json.JSONObject

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

    data class ChatSnapshot(val ok: Boolean, val reply: String, val provider: String, val error: String? = null)
    data class AvatarSnapshot(val ok: Boolean, val emotion: String, val svg: String?, val error: String? = null)

    suspend fun chat(message: String): ChatSnapshot = withContext(Dispatchers.IO) {
        try {
            val connection = URL("${baseUrlProvider()}/api/chat").openConnection() as HttpURLConnection
            connection.requestMethod = "POST"
            connection.connectTimeout = 4_000
            connection.readTimeout = 12_000
            connection.doOutput = true
            connection.setRequestProperty("Content-Type", "application/json")
            OutputStreamWriter(connection.outputStream, Charsets.UTF_8).use { writer ->
                writer.write(JSONObject(mapOf("message" to message)).toString())
            }
            val body = (if (connection.responseCode in 200..299) connection.inputStream else connection.errorStream)
                ?.bufferedReader()
                ?.use { it.readText() }
                .orEmpty()
            if (connection.responseCode !in 200..299) {
                return@withContext ChatSnapshot(false, "", "", body.ifBlank { "Backend chat failed." })
            }
            val payload = JSONObject(body)
            ChatSnapshot(
                ok = true,
                reply = payload.optString("reply"),
                provider = payload.optString("provider"),
            )
        } catch (error: Exception) {
            ChatSnapshot(false, "", "", error.message ?: "Backend unavailable")
        }
    }

    suspend fun avatar(): AvatarSnapshot = withContext(Dispatchers.IO) {
        try {
            val connection = URL("${baseUrlProvider()}/api/avatar").openConnection() as HttpURLConnection
            connection.requestMethod = "GET"
            connection.connectTimeout = 2_000
            connection.readTimeout = 4_000
            val body = (if (connection.responseCode in 200..299) connection.inputStream else connection.errorStream)
                ?.bufferedReader()
                ?.use { it.readText() }
                .orEmpty()
            if (connection.responseCode !in 200..299) {
                return@withContext AvatarSnapshot(false, "neutral", null, body.ifBlank { "Avatar request failed." })
            }
            val payload = JSONObject(body)
            val emotion = payload.optString("current_emotion", "neutral")
            val frames = payload.optJSONArray("frames") ?: JSONArray()
            var svg: String? = null
            for (index in 0 until frames.length()) {
                val frame = frames.optJSONObject(index) ?: continue
                if (frame.optString("emotion") == emotion) {
                    svg = frame.optString("svg")
                    break
                }
            }
            AvatarSnapshot(true, emotion, svg)
        } catch (error: Exception) {
            AvatarSnapshot(false, "neutral", null, error.message ?: "Backend unavailable")
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