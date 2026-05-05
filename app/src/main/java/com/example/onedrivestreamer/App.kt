package com.example.onedrivestreamer

import android.app.Application
import android.content.Context

class App : Application() {

    override fun onCreate() {
        super.onCreate()
        val default = Thread.getDefaultUncaughtExceptionHandler()
        Thread.setDefaultUncaughtExceptionHandler { thread, throwable ->
            getSharedPreferences("crash_log", Context.MODE_PRIVATE)
                .edit()
                .putString("crash", throwable.stackTraceToString().take(3000))
                .apply()
            default?.uncaughtException(thread, throwable)
        }
    }
}
