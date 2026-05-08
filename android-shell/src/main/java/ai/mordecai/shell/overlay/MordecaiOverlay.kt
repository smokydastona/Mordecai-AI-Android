package ai.mordecai.shell.overlay

import android.content.Context
import android.graphics.PixelFormat
import android.graphics.Typeface
import android.view.Gravity
import android.view.WindowManager
import android.webkit.WebView
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import ai.mordecai.shell.R

class MordecaiOverlay(
    private val context: Context,
    private val onListenRequested: () -> Unit,
) {
    private val windowManager = context.getSystemService(Context.WINDOW_SERVICE) as WindowManager
    private val rootView: LinearLayout = LinearLayout(context)
    private val avatarView: WebView = WebView(context)
    private val statusTitle: TextView = TextView(context)
    private val statusBody: TextView = TextView(context)
    private val actionButton: Button = Button(context)
    private var attached = false

    private val layoutParams = WindowManager.LayoutParams(
        WindowManager.LayoutParams.MATCH_PARENT,
        WindowManager.LayoutParams.WRAP_CONTENT,
        WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
        WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
            WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN or
            WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED,
        PixelFormat.TRANSLUCENT,
    ).apply {
        gravity = Gravity.TOP or Gravity.CENTER_HORIZONTAL
        y = dp(32)
    }

    init {
        rootView.orientation = LinearLayout.VERTICAL
        rootView.setBackgroundColor(0xE61A1E24.toInt())
        rootView.setPadding(dp(16), dp(16), dp(16), dp(16))

        avatarView.setBackgroundColor(0x00000000)
        avatarView.layoutParams = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(180))

        statusTitle.setTextColor(0xFFFFFFFF.toInt())
        statusTitle.textSize = 20f
        statusTitle.setTypeface(Typeface.DEFAULT_BOLD)

        statusBody.setTextColor(0xFFD2D7E0.toInt())
        statusBody.textSize = 15f
        statusBody.setLineSpacing(0f, 1.1f)

        actionButton.text = context.getString(R.string.action_voice_command)
        actionButton.setOnClickListener { onListenRequested() }

        rootView.addView(avatarView)
        rootView.addView(statusTitle)
        rootView.addView(statusBody)
        rootView.addView(actionButton)
    }

    fun show() {
        if (attached) {
            return
        }
        windowManager.addView(rootView, layoutParams)
        attached = true
    }

    fun hide() {
        if (!attached) {
            return
        }
        windowManager.removeView(rootView)
        attached = false
    }

    fun showStatus(title: String, message: String) {
        show()
        statusTitle.text = title
        statusBody.text = message
    }

    fun showReply(reply: String, emotion: String, svg: String?) {
        show()
        statusTitle.text = context.getString(R.string.overlay_reply_title, emotion.replace('-', ' '))
        statusBody.text = reply
        renderAvatar(svg)
    }

    private fun renderAvatar(svg: String?) {
        val body = if (svg.isNullOrBlank()) {
            "<html><body style='margin:0;background:transparent;color:white;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100%;'>Mordecai</body></html>"
        } else {
            "<html><body style='margin:0;background:transparent;display:flex;align-items:center;justify-content:center;height:100%;'>$svg</body></html>"
        }
        avatarView.loadDataWithBaseURL(null, body, "text/html", "utf-8", null)
    }

    private fun dp(value: Int): Int = (value * context.resources.displayMetrics.density).toInt()
}