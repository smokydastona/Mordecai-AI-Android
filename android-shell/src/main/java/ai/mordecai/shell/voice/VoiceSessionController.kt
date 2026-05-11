package ai.mordecai.shell.voice

import ai.mordecai.shell.MordecaiShellService
import ai.mordecai.shell.backend.ShellBackendClient

class VoiceSessionController(
    private val backendClient: ShellBackendClient,
    private val prefs: android.content.SharedPreferences,
) {
    private var voiceSessionId: String? = null

    suspend fun onPlaybackFinished(label: String) {
        val sessionId = ensureVoiceSessionId(label) ?: return
        backendClient.postVoiceSessionEvent(
            sessionId = sessionId,
            transcript = "",
            isFinal = false,
            playbackFinished = true,
            autoExecute = false,
        )
    }

    suspend fun prepareForCommand(label: String, wakePhrase: String) {
        val sessionId = ensureVoiceSessionId(label) ?: return
        backendClient.postVoiceSessionEvent(
            sessionId = sessionId,
            transcript = "",
            isFinal = false,
            interrupt = true,
            autoExecute = false,
        )
        backendClient.postVoiceSessionEvent(
            sessionId = sessionId,
            transcript = wakePhrase,
            isFinal = false,
            autoExecute = false,
        )
    }

    suspend fun postPartialTranscript(label: String, transcript: String) {
        if (transcript.isBlank()) {
            return
        }
        val sessionId = ensureVoiceSessionId(label) ?: return
        backendClient.postVoiceSessionEvent(
            sessionId = sessionId,
            transcript = transcript,
            isFinal = false,
            autoExecute = false,
        )
    }

    suspend fun submitFinalCommand(label: String, command: String): ShellBackendClient.VoiceEventSnapshot? {
        if (command.isBlank()) {
            return null
        }
        val sessionId = ensureVoiceSessionId(label) ?: return null
        val result = backendClient.postVoiceSessionEvent(
            sessionId = sessionId,
            transcript = command,
            isFinal = true,
            autoExecute = true,
        )
        if (result.ok) {
            (result.lastResponse ?: result.planResponse)?.takeIf { it.isNotBlank() }?.let { persistLastReply(it) }
        }
        return result
    }

    fun persistLastReply(reply: String) {
        if (reply.isBlank()) {
            return
        }
        prefs.edit().putString(MordecaiShellService.PREF_LAST_REPLY, reply).apply()
    }

    private suspend fun ensureVoiceSessionId(label: String): String? {
        if (!voiceSessionId.isNullOrBlank()) {
            return voiceSessionId
        }
        val snapshot = backendClient.startVoiceSession(label, background = true)
        if (snapshot.ok) {
            voiceSessionId = snapshot.sessionId
        }
        return voiceSessionId
    }
}