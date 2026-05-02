package com.example.ytplayer

import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.media3.common.MediaItem
import androidx.media3.datasource.DefaultHttpDataSource
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.exoplayer.dash.DashMediaSource
import androidx.media3.exoplayer.hls.HlsMediaSource
import androidx.media3.exoplayer.source.MediaSource
import androidx.media3.exoplayer.source.MergingMediaSource
import androidx.media3.exoplayer.source.ProgressiveMediaSource
import com.example.ytplayer.databinding.ActivityPlayerBinding
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.schabi.newpipe.extractor.ServiceList
import org.schabi.newpipe.extractor.stream.AudioStream
import org.schabi.newpipe.extractor.stream.DeliveryMethod
import org.schabi.newpipe.extractor.stream.VideoStream

class PlayerActivity : AppCompatActivity() {

    private lateinit var binding: ActivityPlayerBinding
    private var player: ExoPlayer? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityPlayerBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val url = intent.getStringExtra(EXTRA_URL) ?: run { finish(); return }

        player = ExoPlayer.Builder(this).build().also {
            binding.playerView.player = it
            binding.playerView.keepScreenOn = true
        }

        binding.progressBar.visibility = View.VISIBLE

        lifecycleScope.launch {
            runCatching {
                withContext(Dispatchers.IO) { extractStreams(url) }
            }.onSuccess { result ->
                binding.progressBar.visibility = View.GONE
                playStreams(result)
            }.onFailure { e ->
                binding.progressBar.visibility = View.GONE
                Toast.makeText(
                    this@PlayerActivity,
                    "Could not load video: ${e.message}",
                    Toast.LENGTH_LONG
                ).show()
                finish()
            }
        }
    }

    // ---------- extraction (runs on IO thread) ----------

    private data class StreamResult(val videoUrl: String, val videoDelivery: DeliveryMethod,
                                    val audioUrl: String?, val audioDelivery: DeliveryMethod?)

    private fun extractStreams(url: String): StreamResult {
        val extractor = ServiceList.YouTube.getStreamExtractor(url)
        extractor.fetchPage()

        // 1. Prefer combined video+audio progressive streams (no merging needed)
        val combined: VideoStream? = extractor.videoStreams
            .filter { it.deliveryMethod == DeliveryMethod.PROGRESSIVE_HTTP }
            .maxByOrNull { it.height }

        if (combined != null) {
            return StreamResult(combined.content, DeliveryMethod.PROGRESSIVE_HTTP, null, null)
        }

        // 2. Fall back to separate video + audio (higher quality, DASH/progressive)
        val video: VideoStream = extractor.videoOnlyStreams
            .maxByOrNull { it.height }
            ?: throw IllegalStateException("No video stream available")

        val audio: AudioStream? = extractor.audioStreams
            .maxByOrNull { it.averageBitrate }

        return StreamResult(
            video.content, video.deliveryMethod,
            audio?.content, audio?.deliveryMethod
        )
    }

    // ---------- playback ----------

    private fun playStreams(result: StreamResult) {
        val dsFactory = DefaultHttpDataSource.Factory()
            .setUserAgent("Mozilla/5.0 (Windows NT 10.0; rv:120.0) Gecko/20100101 Firefox/120.0")
            .setAllowCrossProtocolRedirects(true)

        val videoSource = buildMediaSource(result.videoUrl, result.videoDelivery, dsFactory)

        val source = if (result.audioUrl != null) {
            MergingMediaSource(
                videoSource,
                buildMediaSource(result.audioUrl, result.audioDelivery
                    ?: DeliveryMethod.PROGRESSIVE_HTTP, dsFactory)
            )
        } else {
            videoSource
        }

        player?.run {
            setMediaSource(source)
            prepare()
            playWhenReady = true
        }
    }

    private fun buildMediaSource(
        url: String,
        delivery: DeliveryMethod,
        dsFactory: DefaultHttpDataSource.Factory
    ): MediaSource = when (delivery) {
        DeliveryMethod.DASH ->
            DashMediaSource.Factory(dsFactory).createMediaSource(MediaItem.fromUri(url))
        DeliveryMethod.HLS ->
            HlsMediaSource.Factory(dsFactory).createMediaSource(MediaItem.fromUri(url))
        else ->
            ProgressiveMediaSource.Factory(dsFactory).createMediaSource(MediaItem.fromUri(url))
    }

    // ---------- lifecycle ----------

    override fun onStop() {
        super.onStop()
        player?.pause()
    }

    override fun onDestroy() {
        super.onDestroy()
        player?.release()
        player = null
    }

    companion object {
        const val EXTRA_URL = "extra_url"
    }
}
