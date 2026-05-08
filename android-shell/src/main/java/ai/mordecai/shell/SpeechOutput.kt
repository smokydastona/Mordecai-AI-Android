package ai.mordecai.shell

import android.content.Context
import android.speech.tts.TextToSpeech
import java.util.Locale

class SpeechOutput(context: Context) : TextToSpeech.OnInitListener {
    private val appContext = context.applicationContext
    private var tts: TextToSpeech? = TextToSpeech(appContext, this)
    private var ready = false
    private var queuedText: String? = null

    override fun onInit(status: Int) {
        ready = status == TextToSpeech.SUCCESS
        if (ready) {
            tts?.language = Locale.US
            tts?.setPitch(0.88f)
            tts?.setSpeechRate(0.92f)
            queuedText?.let {
                speak(it)
                queuedText = null
            }
        }
    }

    fun speak(text: String) {
        val sanitized = text.trim()
        if (sanitized.isBlank()) {
            return
        }
        if (!ready) {
            queuedText = sanitized
            return
        }
        tts?.speak(sanitized, TextToSpeech.QUEUE_FLUSH, null, "mordecai-reply")
    }

    fun shutdown() {
        tts?.stop()
        tts?.shutdown()
        tts = null
        ready = false
        queuedText = null
    }
}