package com.example.ytplayer

import okhttp3.OkHttpClient
import okhttp3.RequestBody.Companion.toRequestBody
import org.schabi.newpipe.extractor.downloader.Downloader
import org.schabi.newpipe.extractor.downloader.Request
import org.schabi.newpipe.extractor.downloader.Response
import org.schabi.newpipe.extractor.exceptions.ReCaptchaException
import java.util.concurrent.TimeUnit

class YTDownloader private constructor() : Downloader() {

    private val client = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .build()

    override fun execute(request: Request): Response {
        val reqBuilder = okhttp3.Request.Builder()
            .url(request.url())
            .addHeader("User-Agent", USER_AGENT)

        request.headers().forEach { (key, values) ->
            values.forEach { value -> reqBuilder.addHeader(key, value) }
        }

        request.dataToSend()?.let { body ->
            reqBuilder.post(body.toRequestBody())
        }

        val response = client.newCall(reqBuilder.build()).execute()

        if (response.code == 429) {
            throw ReCaptchaException("reCAPTCHA requested", request.url())
        }

        val headers = response.headers.names().associateWith { response.headers(it) }

        return Response(
            response.code,
            response.message,
            headers,
            response.body?.string() ?: "",
            response.request.url.toString()
        )
    }

    companion object {
        private const val USER_AGENT =
            "Mozilla/5.0 (Windows NT 10.0; rv:120.0) Gecko/20100101 Firefox/120.0"

        @Volatile private var instance: YTDownloader? = null

        fun getInstance() = instance ?: synchronized(this) {
            instance ?: YTDownloader().also { instance = it }
        }
    }
}
