package ai.mordecai.shell.backend

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL

class ShellBackendClient(
    private val baseUrlProvider: () -> String = { DEFAULT_BASE_URL },
) {
    data class HealthSnapshot(val reachable: Boolean, val status: String)
    data class ChatSnapshot(val ok: Boolean, val reply: String, val provider: String, val error: String? = null)
    data class RuntimeStatusSnapshot(val ok: Boolean, val provider: String?, val appName: String?, val error: String? = null)
    data class AvatarSnapshot(val ok: Boolean, val emotion: String, val svg: String?, val error: String? = null)
    data class VoiceSessionSnapshot(val ok: Boolean, val sessionId: String?, val status: String?, val lastResponse: String?, val error: String? = null)
    data class VoiceEventSnapshot(val ok: Boolean, val sessionId: String?, val status: String?, val lastResponse: String?, val planResponse: String?, val error: String? = null)

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

    suspend fun runtimeStatus(): RuntimeStatusSnapshot = withContext(Dispatchers.IO) {
        try {
            val connection = URL("${baseUrlProvider()}/api/status").openConnection() as HttpURLConnection
            connection.requestMethod = "GET"
            connection.connectTimeout = 2_000
            connection.readTimeout = 4_000
            val body = (if (connection.responseCode in 200..299) connection.inputStream else connection.errorStream)
                ?.bufferedReader()
                ?.use { it.readText() }
                .orEmpty()
            if (connection.responseCode !in 200..299) {
                return@withContext RuntimeStatusSnapshot(false, null, null, body.ifBlank { "Runtime status request failed." })
            }
            val payload = JSONObject(body)
            RuntimeStatusSnapshot(
                ok = true,
                provider = payload.optString("provider").ifBlank { null },
                appName = payload.optString("app_name").ifBlank { null },
            )
        } catch (error: Exception) {
            RuntimeStatusSnapshot(false, null, null, error.message ?: "Backend unavailable")
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

    suspend fun startVoiceSession(label: String, background: Boolean): VoiceSessionSnapshot = withContext(Dispatchers.IO) {
        val payload = JSONObject().apply {
            put("label", label)
            put("background", background)
        }
        try {
            val body = postJson("/api/voice/sessions", payload)
            val json = JSONObject(body)
            VoiceSessionSnapshot(
                ok = true,
                sessionId = json.optString("session_id"),
                status = json.optString("status"),
                lastResponse = json.optString("last_response").ifBlank { null },
            )
        } catch (error: Exception) {
            VoiceSessionSnapshot(false, null, null, null, error.message ?: "Voice session start failed")
        }
    }

    suspend fun postVoiceSessionEvent(
        sessionId: String,
        transcript: String,
        isFinal: Boolean,
        interrupt: Boolean = false,
        playbackFinished: Boolean = false,
        autoExecute: Boolean = true,
    ): VoiceEventSnapshot = withContext(Dispatchers.IO) {
        val payload = JSONObject().apply {
            put("transcript", transcript)
            put("is_final", isFinal)
            put("interrupt", interrupt)
            put("playback_finished", playbackFinished)
            put("auto_execute", autoExecute)
        }
        try {
            val body = postJson("/api/voice/sessions/$sessionId/events", payload)
            val json = JSONObject(body)
            val session = json.optJSONObject("session")
            val plan = json.optJSONObject("plan")
            VoiceEventSnapshot(
                ok = true,
                sessionId = session?.optString("session_id"),
                status = session?.optString("status"),
                lastResponse = session?.optString("last_response")?.ifBlank { null },
                planResponse = plan?.optString("final_response")?.ifBlank { null },
            )
        } catch (error: Exception) {
            VoiceEventSnapshot(false, sessionId, null, null, null, error.message ?: "Voice session event failed")
        }
    }

    suspend fun ingestPerception(payload: JSONObject): Boolean = withContext(Dispatchers.IO) {
        try {
            postJson("/api/android/perception", payload)
            true
        } catch (_: Exception) {
            false
        }
    }

    private fun postJson(path: String, payload: JSONObject): String {
        val connection = URL("${baseUrlProvider()}$path").openConnection() as HttpURLConnection
        connection.requestMethod = "POST"
        connection.connectTimeout = 4_000
        connection.readTimeout = 12_000
        connection.doOutput = true
        connection.setRequestProperty("Content-Type", "application/json")
        OutputStreamWriter(connection.outputStream, Charsets.UTF_8).use { writer ->
            writer.write(payload.toString())
        }
        val body = (if (connection.responseCode in 200..299) connection.inputStream else connection.errorStream)
            ?.bufferedReader()
            ?.use { it.readText() }
            .orEmpty()
        if (connection.responseCode !in 200..299) {
            throw IllegalStateException(body.ifBlank { "Backend request failed for $path" })
        }
        return body
    }

    companion object {
        const val DEFAULT_BASE_URL = "http://127.0.0.1:8000"
    }
}