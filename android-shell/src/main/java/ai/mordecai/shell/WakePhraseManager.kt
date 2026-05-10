package ai.mordecai.shell

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer

class WakePhraseManager(
    private val context: Context,
    private val phrase: String,
    private val onWakePhraseHeard: () -> Unit,
    private val onWakeTranscript: (String) -> Unit = {},
) : RecognitionListener {
    private var speechRecognizer: SpeechRecognizer? = null
    private var active = false

    fun start() {
        if (!SpeechRecognizer.isRecognitionAvailable(context) || active) {
            return
        }
        speechRecognizer = SpeechRecognizer.createSpeechRecognizer(context).also {
            it.setRecognitionListener(this)
        }
        active = true
        beginListening()
    }

    fun stop() {
        active = false
        speechRecognizer?.stopListening()
        speechRecognizer?.cancel()
        speechRecognizer?.destroy()
        speechRecognizer = null
    }

    private fun beginListening() {
        if (!active) {
            return
        }
        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
            putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE, false)
        }
        speechRecognizer?.startListening(intent)
    }

    override fun onPartialResults(partialResults: Bundle) {
        val matches = partialResults.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION).orEmpty()
        val wakeMatch = matches.firstOrNull { it.contains(phrase, ignoreCase = true) }
        if (wakeMatch != null) {
            onWakeTranscript(wakeMatch)
            onWakePhraseHeard()
        }
    }

    override fun onResults(results: Bundle) {
        val matches = results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION).orEmpty()
        val wakeMatch = matches.firstOrNull { it.contains(phrase, ignoreCase = true) }
        if (wakeMatch != null) {
            onWakeTranscript(wakeMatch)
            onWakePhraseHeard()
        }
        beginListening()
    }

    override fun onError(error: Int) {
        beginListening()
    }

    override fun onReadyForSpeech(params: Bundle) = Unit

    override fun onBeginningOfSpeech() = Unit

    override fun onRmsChanged(rmsdB: Float) = Unit

    override fun onBufferReceived(buffer: ByteArray) = Unit

    override fun onEndOfSpeech() = Unit

    override fun onEvent(eventType: Int, params: Bundle) = Unit
}