package expo.modules.shareintent

import android.content.Intent
import android.net.Uri
import android.os.Build
import android.webkit.MimeTypeMap
import expo.modules.kotlin.modules.Module
import expo.modules.kotlin.modules.ModuleDefinition
import java.io.File

private const val SHARE_EVENT = "onShare"
private const val MAX_IMAGE_BYTES = 30L * 1024 * 1024

/**
 * Turns Android ACTION_SEND (text, image) and ACTION_PROCESS_TEXT (text-selection menu) intents into
 * plain payloads for JS. Shared images are copied into the cache so JS can read them after the
 * temporary URI grant expires.
 */
class ShareIntentModule : Module() {
  override fun definition() = ModuleDefinition {
    Name("ShareIntent")

    Events(SHARE_EVENT)

    AsyncFunction("getInitialShare") {
      val activity = appContext.currentActivity ?: return@AsyncFunction null
      val payload = getSharePayload(activity.intent) ?: return@AsyncFunction null
      activity.intent = Intent(Intent.ACTION_MAIN)
      payload
    }

    OnNewIntent { intent ->
      val payload = getSharePayload(intent) ?: return@OnNewIntent
      appContext.currentActivity?.intent = Intent(Intent.ACTION_MAIN)
      sendEvent(SHARE_EVENT, payload)
    }
  }

  private fun getSharePayload(intent: Intent?): Map<String, Any?>? {
    if (intent == null) return null
    return when (intent.action) {
      Intent.ACTION_PROCESS_TEXT -> getTextPayload(intent.getCharSequenceExtra(Intent.EXTRA_PROCESS_TEXT), null, "process_text")
      Intent.ACTION_SEND -> getSendPayload(intent)
      else -> null
    }
  }

  private fun getSendPayload(intent: Intent): Map<String, Any?>? {
    if (intent.type?.startsWith("image/") == true) {
      val uri = getStreamUri(intent) ?: return null
      val file = copyToCache(uri, intent.type) ?: return null
      return mapOf("kind" to "image", "uri" to Uri.fromFile(file).toString(), "source" to "share")
    }
    return getTextPayload(intent.getCharSequenceExtra(Intent.EXTRA_TEXT), intent.getStringExtra(Intent.EXTRA_SUBJECT), "share")
  }

  private fun getTextPayload(text: CharSequence?, subject: String?, source: String): Map<String, Any?>? {
    val value = text?.toString()?.trim().orEmpty()
    if (value.isEmpty()) return null
    return mapOf("kind" to "text", "text" to value, "subject" to subject, "source" to source)
  }

  @Suppress("DEPRECATION")
  private fun getStreamUri(intent: Intent): Uri? =
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
      intent.getParcelableExtra(Intent.EXTRA_STREAM, Uri::class.java)
    } else {
      intent.getParcelableExtra(Intent.EXTRA_STREAM) as? Uri
    }

  private fun copyToCache(uri: Uri, mimeType: String?): File? {
    val context = appContext.reactContext ?: return null
    val extension = MimeTypeMap.getSingleton().getExtensionFromMimeType(mimeType) ?: "img"
    val directory = File(context.cacheDir, "shared").apply { mkdirs() }
    directory.listFiles()?.forEach { it.delete() }
    val target = File(directory, "shared-${System.currentTimeMillis()}.$extension")
    return try {
      context.contentResolver.openInputStream(uri)?.use { input ->
        target.outputStream().use { output -> copyLimited(input, output) }
      } ?: return null
      target
    } catch (error: Exception) {
      target.delete()
      null
    }
  }

  private fun copyLimited(input: java.io.InputStream, output: java.io.OutputStream) {
    val buffer = ByteArray(64 * 1024)
    var total = 0L
    while (true) {
      val read = input.read(buffer)
      if (read < 0) return
      total += read
      if (total > MAX_IMAGE_BYTES) throw IllegalStateException("Shared image is too large")
      output.write(buffer, 0, read)
    }
  }
}
