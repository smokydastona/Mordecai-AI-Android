package ai.mordecai.shell

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer

class SpeechCommandProcessor(
    private val context: Context,
    private val onCommandHeard: (String) -> Unit,
    private val onFailure: (String) -> Unit,
    private val onTranscript: (String) -> Unit = {},
) : RecognitionListener {
    private var speechRecognizer: SpeechRecognizer? = null
    private var active = false

    fun startListening() {
        if (!SpeechRecognizer.isRecognitionAvailable(context) || active) {
            onFailure("Speech recognition is unavailable on this device.")
            return
        }
        speechRecognizer = SpeechRecognizer.createSpeechRecognizer(context).also {
            it.setRecognitionListener(this)
        }
        active = true
        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
            putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE, false)
            putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
        }
        speechRecognizer?.startListening(intent)
    }

    fun stop() {
        active = false
        speechRecognizer?.stopListening()
        speechRecognizer?.cancel()
        speechRecognizer?.destroy()
        speechRecognizer = null
    }

    override fun onResults(results: Bundle) {
        val match = results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION).orEmpty().firstOrNull()?.trim()
        active = false
        if (match.isNullOrBlank()) {
            onFailure("No command was heard.")
        } else {
            onCommandHeard(match)
        }
        stop()
    }

    override fun onError(error: Int) {
        active = false
        onFailure("Speech recognition error: $error")
        stop()
    }

    override fun onReadyForSpeech(params: Bundle) = Unit

    override fun onBeginningOfSpeech() = Unit

    override fun onRmsChanged(rmsdB: Float) = Unit

    override fun onBufferReceived(buffer: ByteArray) = Unit

    override fun onEndOfSpeech() = Unit

    override fun onPartialResults(partialResults: Bundle) {
        val match = partialResults.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION).orEmpty().firstOrNull()?.trim()
        if (!match.isNullOrBlank()) {
            onTranscript(match)
        }
    }

    override fun onEvent(eventType: Int, params: Bundle) = Unit
}