package com.example.onedrivestreamer.ui

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat
import androidx.fragment.app.Fragment
import androidx.navigation.fragment.navArgs
import androidx.window.layout.WindowMetricsCalculator
import com.example.onedrivestreamer.databinding.FragmentVideoPlayerBinding
import androidx.media3.common.MediaItem
import androidx.media3.common.Player
import androidx.media3.exoplayer.ExoPlayer

class VideoPlayerFragment : Fragment() {

    private var _binding: FragmentVideoPlayerBinding? = null
    private val binding get() = _binding!!
    private val args: VideoPlayerFragmentArgs by navArgs()
    private var player: ExoPlayer? = null

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View {
        _binding = FragmentVideoPlayerBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        binding.videoTitle.text = args.video.name
        adjustAspectRatioForWindow()
    }

    override fun onStart() {
        super.onStart()
        initPlayer()
    }

    override fun onStop() {
        releasePlayer()
        super.onStop()
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }

    private fun initPlayer() {
        player = ExoPlayer.Builder(requireContext()).build().also { exo ->
            binding.playerView.player = exo
            exo.setMediaItem(MediaItem.fromUri(args.video.downloadUrl))
            exo.repeatMode = Player.REPEAT_MODE_ONE
            exo.playWhenReady = true
            exo.prepare()
        }
    }

    private fun releasePlayer() {
        player?.let {
            it.stop()
            it.release()
        }
        player = null
    }

    // Adjust player aspect ratio for foldables / wide displays
    private fun adjustAspectRatioForWindow() {
        val metrics = WindowMetricsCalculator.getOrCreate()
            .computeCurrentWindowMetrics(requireActivity())
        val bounds = metrics.bounds
        val windowRatio = bounds.width().toFloat() / bounds.height()

        val videoW = args.video.width?.toFloat() ?: 16f
        val videoH = args.video.height?.toFloat() ?: 9f
        val videoRatio = videoW / videoH

        // On wide/foldable screens, constrain width so the player doesn't stretch
        binding.playerView.apply {
            if (windowRatio > 1.5f && videoRatio < windowRatio) {
                val targetWidth = (bounds.height() * videoRatio).toInt()
                layoutParams = layoutParams.also {
                    it.width = targetWidth
                }
            }
        }
    }
}
