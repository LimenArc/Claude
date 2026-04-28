package com.gamegen.app.ui

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import com.gamegen.app.databinding.ActivityPromptBinding
import com.gamegen.app.generator.AiConfigGenerator
import com.gamegen.app.generator.GameGenerator

class PromptActivity : AppCompatActivity() {

    private lateinit var binding: ActivityPromptBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityPromptBinding.inflate(layoutInflater)
        setContentView(binding.root)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        title = "AI Game Generator"

        updateModelLabel()

        binding.btnSettings.setOnClickListener { showSettingsDialog() }

        binding.btnGenerate.setOnClickListener {
            val prompt = binding.etPrompt.text.toString().trim()
            if (prompt.isBlank()) {
                Toast.makeText(this, "Describe the game you want!", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            generateFromPrompt(prompt)
        }

        binding.chipMaze.setOnClickListener { appendChip("procedural maze") }
        binding.chipPlatform.setOnClickListener { appendChip("platform jump game") }
        binding.chipDungeon.setOnClickListener { appendChip("dark dungeon crawler") }
        binding.chipSpace.setOnClickListener { appendChip("space shooter") }
        binding.chipTower.setOnClickListener { appendChip("spiral tower climb") }
    }

    private fun appendChip(text: String) {
        val current = binding.etPrompt.text.toString().trim()
        binding.etPrompt.setText(if (current.isEmpty()) text else "$current, $text")
        binding.etPrompt.setSelection(binding.etPrompt.text?.length ?: 0)
    }

    private fun generateFromPrompt(prompt: String) {
        binding.progressBar.visibility = View.VISIBLE
        binding.btnGenerate.isEnabled = false
        binding.tvStatus.text = if (AiConfigGenerator.isConfigured(this))
            "Asking AI model..." else "Parsing prompt locally..."
        binding.tvStatus.visibility = View.VISIBLE

        Thread {
            val config = AiConfigGenerator.generate(this, prompt)
            val game = GameGenerator.generate(config)

            runOnUiThread {
                binding.progressBar.visibility = View.GONE
                binding.btnGenerate.isEnabled = true
                binding.tvStatus.visibility = View.GONE
                val intent = Intent(this, GameActivity::class.java)
                intent.putExtra(GameActivity.EXTRA_CONFIG, config)
                startActivity(intent)
            }
        }.start()
    }

    private fun showSettingsDialog() {
        val (url, model, apiKey) = AiConfigGenerator.getSettings(this)
        val view = layoutInflater.inflate(com.gamegen.app.R.layout.dialog_ai_settings, null)
        val etUrl = view.findViewById<com.google.android.material.textfield.TextInputEditText>(com.gamegen.app.R.id.et_api_url)
        val etModel = view.findViewById<com.google.android.material.textfield.TextInputEditText>(com.gamegen.app.R.id.et_model)
        val etKey = view.findViewById<com.google.android.material.textfield.TextInputEditText>(com.gamegen.app.R.id.et_api_key)
        etUrl.setText(url)
        etModel.setText(model)
        etKey.setText(apiKey)

        AlertDialog.Builder(this)
            .setTitle("AI Model Settings")
            .setView(view)
            .setPositiveButton("Save") { _, _ ->
                AiConfigGenerator.saveSettings(
                    this,
                    etUrl.text.toString().trim(),
                    etModel.text.toString().trim(),
                    etKey.text.toString().trim()
                )
                updateModelLabel()
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun updateModelLabel() {
        val (url, model, _) = AiConfigGenerator.getSettings(this)
        binding.tvModelInfo.text = if (url.isBlank())
            "Mode: Local keyword parsing (no AI configured)"
        else
            "Model: ${model.ifBlank { "llama3.2" }}  •  ${url.substringBefore("/v1")}"
    }

    override fun onSupportNavigateUp(): Boolean { onBackPressed(); return true }
}
