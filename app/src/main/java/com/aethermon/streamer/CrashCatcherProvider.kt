package com.aethermon.streamer

import android.content.ContentProvider
import android.content.ContentValues
import android.database.Cursor
import android.net.Uri

class CrashCatcherProvider : ContentProvider() {

    override fun onCreate(): Boolean {
        val ctx = context ?: return false
        val default = Thread.getDefaultUncaughtExceptionHandler()
        Thread.setDefaultUncaughtExceptionHandler { thread, throwable ->
            try {
                ctx.getSharedPreferences("crash_log", android.content.Context.MODE_PRIVATE)
                    .edit()
                    .putString("crash", throwable.stackTraceToString().take(4000))
                    .commit()
            } catch (_: Exception) {}
            default?.uncaughtException(thread, throwable)
        }
        return true
    }

    override fun query(uri: Uri, p: Array<String>?, s: String?, sA: Array<String>?, so: String?): Cursor? = null
    override fun getType(uri: Uri): String? = null
    override fun insert(uri: Uri, values: ContentValues?): Uri? = null
    override fun delete(uri: Uri, s: String?, sA: Array<String>?): Int = 0
    override fun update(uri: Uri, values: ContentValues?, s: String?, sA: Array<String>?): Int = 0
}
