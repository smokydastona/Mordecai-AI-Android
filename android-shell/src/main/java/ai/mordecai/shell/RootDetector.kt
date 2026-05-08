package ai.mordecai.shell

import java.io.File

class RootDetector {
    fun isRootAvailable(): Boolean {
        val commonPaths = listOf(
            "/system/bin/su",
            "/system/xbin/su",
            "/sbin/su",
            "/vendor/bin/su",
        )
        if (commonPaths.any { File(it).exists() }) {
            return true
        }
        return try {
            val process = ProcessBuilder("which", "su").redirectErrorStream(true).start()
            process.inputStream.bufferedReader().use { it.readText().trim().isNotEmpty() }
        } catch (_: Exception) {
            false
        }
    }
}