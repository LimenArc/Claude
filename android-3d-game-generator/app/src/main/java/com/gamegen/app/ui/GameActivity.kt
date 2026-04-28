package com.gamegen.app.ui

import android.annotation.SuppressLint
import android.app.AlertDialog
import android.opengl.GLSurfaceView
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.MotionEvent
import android.view.View
import android.view.WindowManager
import androidx.appcompat.app.AppCompatActivity
import com.gamegen.app.databinding.ActivityGameBinding
import com.gamegen.app.generator.GameConfig
import com.gamegen.app.generator.GameGenerator
import com.gamegen.app.generator.GameStorage
import com.gamegen.app.generator.GameType
import com.gamegen.app.renderer.GameRenderer

class GameActivity : AppCompatActivity() {

    companion object {
        const val EXTRA_CONFIG = "extra_config"
        const val EXTRA_GAME_ID = "extra_game_id"
    }

    private lateinit var binding: ActivityGameBinding
    private lateinit var renderer: GameRenderer
    private lateinit var glView: GLSurfaceView
    private val handler = Handler(Looper.getMainLooper())

    private var lookStartX = 0f
    private var lookStartY = 0f

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        binding = ActivityGameBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val config = intent.getSerializableExtra(EXTRA_CONFIG) as? GameConfig
            ?: run { finish(); return }

        showGeneratingOverlay()
        Thread {
            val game = GameGenerator.generate(config)
            GameStorage.saveGame(this, game)
            renderer = GameRenderer(game)

            runOnUiThread {
                hideGeneratingOverlay()
                setupGL()
                setupHUD(config)
                setupControls()
                setupRendererCallbacks()
            }
        }.start()
    }

    private fun showGeneratingOverlay() {
        binding.layoutGenerating.visibility = View.VISIBLE
    }

    private fun hideGeneratingOverlay() {
        binding.layoutGenerating.visibility = View.GONE
    }

    private fun setupGL() {
        glView = GLSurfaceView(this)
        glView.setEGLContextClientVersion(2)
        glView.setRenderer(renderer)
        glView.renderMode = GLSurfaceView.RENDERMODE_CONTINUOUSLY
        binding.glContainer.addView(glView)
    }

    private fun setupHUD(config: GameConfig) {
        binding.tvGameTitle.text = config.gameName
        binding.tvScore.text = "Score: 0"
        binding.tvLives.text = "Lives: 3"

        val type = config.gameType
        binding.btnJump.visibility = if (type == GameType.PLATFORM_JUMP || type == GameType.TOWER_CLIMB)
            View.VISIBLE else View.GONE
    }

    @SuppressLint("ClickableViewAccessibility")
    private fun setupControls() {
        // DPAD movement
        binding.btnForward.setOnTouchListener { _, e -> handleDpad(e, true, false, false, false); true }
        binding.btnBack.setOnTouchListener { _, e -> handleDpad(e, false, true, false, false); true }
        binding.btnLeft.setOnTouchListener { _, e -> handleDpad(e, false, false, true, false); true }
        binding.btnRight.setOnTouchListener { _, e -> handleDpad(e, false, false, false, true); true }

        // Look (right side of screen)
        binding.lookArea.setOnTouchListener { _, e ->
            when (e.action) {
                MotionEvent.ACTION_DOWN -> { lookStartX = e.x; lookStartY = e.y }
                MotionEvent.ACTION_MOVE -> {
                    val dx = (e.x - lookStartX) * 0.3f
                    val dy = (e.y - lookStartY) * 0.3f
                    renderer.camera.look(dx, -dy)
                    lookStartX = e.x; lookStartY = e.y
                }
            }
            true
        }

        binding.btnJump.setOnClickListener { renderer.jump() }
        binding.btnMenu.setOnClickListener { showPauseMenu() }
    }

    private fun handleDpad(e: MotionEvent, f: Boolean, b: Boolean, l: Boolean, r: Boolean) {
        val down = e.action == MotionEvent.ACTION_DOWN || e.action == MotionEvent.ACTION_MOVE
        renderer.setMovement(
            if (f) down else false,
            if (b) down else false,
            if (l) down else false,
            if (r) down else false
        )
    }

    private fun setupRendererCallbacks() {
        renderer.onScoreChanged = { s ->
            handler.post { binding.tvScore.text = "Score: $s" }
        }
        renderer.onLivesChanged = { l ->
            handler.post { binding.tvLives.text = "Lives: $l" }
        }
        renderer.onGameOver = {
            handler.post { showGameOver() }
        }
        renderer.onGameWon = {
            handler.post { showVictory() }
        }
    }

    private fun showGameOver() {
        AlertDialog.Builder(this)
            .setTitle("Game Over")
            .setMessage("Score: ${renderer.score}")
            .setPositiveButton("Try Again") { _, _ -> recreate() }
            .setNegativeButton("Menu") { _, _ -> finish() }
            .setCancelable(false)
            .show()
    }

    private fun showVictory() {
        AlertDialog.Builder(this)
            .setTitle("Victory!")
            .setMessage("You escaped!\nFinal Score: ${renderer.score}")
            .setPositiveButton("Play Again") { _, _ -> recreate() }
            .setNegativeButton("Menu") { _, _ -> finish() }
            .setCancelable(false)
            .show()
    }

    private fun showPauseMenu() {
        glView.onPause()
        AlertDialog.Builder(this)
            .setTitle("Paused")
            .setItems(arrayOf("Resume", "Quit to Menu")) { _, which ->
                if (which == 0) glView.onResume()
                else finish()
            }
            .setOnCancelListener { glView.onResume() }
            .show()
    }

    override fun onResume() {
        super.onResume()
        if (::glView.isInitialized) glView.onResume()
    }

    override fun onPause() {
        super.onPause()
        if (::glView.isInitialized) glView.onPause()
    }
}
