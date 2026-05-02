package com.example.ytplayer

import android.content.Intent
import android.os.Bundle
import android.view.inputmethod.EditorInfo
import androidx.appcompat.app.AppCompatActivity
import com.example.ytplayer.databinding.ActivityMainBinding

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // Auto-play if app was opened via a YouTube share/link
        intent?.data?.toString()?.let { url ->
            binding.urlInput.setText(url)
            openPlayer(url)
        }

        binding.playButton.setOnClickListener {
            val input = binding.urlInput.text?.toString()?.trim().orEmpty()
            if (input.isNotEmpty()) openPlayer(input)
        }

        binding.urlInput.setOnEditorActionListener { _, actionId, _ ->
            if (actionId == EditorInfo.IME_ACTION_GO) {
                val input = binding.urlInput.text?.toString()?.trim().orEmpty()
                if (input.isNotEmpty()) openPlayer(input)
                true
            } else false
        }
    }

    private fun openPlayer(input: String) {
        val url = when {
            input.startsWith("http") -> input
            // bare 11-char video ID
            input.matches(Regex("[A-Za-z0-9_-]{11}")) ->
                "https://www.youtube.com/watch?v=$input"
            else -> input
        }
        startActivity(
            Intent(this, PlayerActivity::class.java)
                .putExtra(PlayerActivity.EXTRA_URL, url)
        )
    }
}
