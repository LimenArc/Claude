package com.gamegen.app.ui

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.AdapterView
import android.widget.ArrayAdapter
import androidx.appcompat.app.AppCompatActivity
import com.gamegen.app.databinding.ActivityGameConfigBinding
import com.gamegen.app.generator.*

class GameConfigActivity : AppCompatActivity() {

    private lateinit var binding: ActivityGameConfigBinding
    private var selectedType = GameType.MAZE_RUNNER
    private var selectedTheme = WorldTheme.NEON
    private var selectedDifficulty = Difficulty.NORMAL

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityGameConfigBinding.inflate(layoutInflater)
        setContentView(binding.root)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        title = "Configure Game"

        setupGameTypeSpinner()
        setupThemeSpinner()
        setupDifficultySpinner()
        updateDescription()

        binding.sliderWorldSize.addOnChangeListener { _, _, _ -> updateDescription() }

        binding.btnGenerate.setOnClickListener {
            val config = GameConfig(
                gameType = selectedType,
                theme = selectedTheme,
                difficulty = selectedDifficulty,
                worldSize = binding.sliderWorldSize.value.toInt(),
                seed = System.currentTimeMillis(),
                playerSpeed = 5f,
                enableFog = binding.switchFog.isChecked,
                enableParticles = binding.switchParticles.isChecked,
                gameName = binding.etGameName.text.toString().ifBlank {
                    "${selectedType.displayName} #${(System.currentTimeMillis() % 1000)}"
                }
            )
            val intent = Intent(this, GameActivity::class.java)
            intent.putExtra(GameActivity.EXTRA_CONFIG, config)
            startActivity(intent)
        }
    }

    private fun setupGameTypeSpinner() {
        val types = GameType.values()
        val names = types.map { it.displayName }
        binding.spinnerGameType.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, names)
        binding.spinnerGameType.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(p: AdapterView<*>, v: View?, pos: Int, id: Long) {
                selectedType = types[pos]
                binding.tvGameTypeDesc.text = types[pos].description
                updateDescription()
            }
            override fun onNothingSelected(p: AdapterView<*>) {}
        }
    }

    private fun setupThemeSpinner() {
        val themes = WorldTheme.values()
        binding.spinnerTheme.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, themes.map { it.displayName })
        binding.spinnerTheme.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(p: AdapterView<*>, v: View?, pos: Int, id: Long) {
                selectedTheme = themes[pos]
                updateDescription()
            }
            override fun onNothingSelected(p: AdapterView<*>) {}
        }
    }

    private fun setupDifficultySpinner() {
        val diffs = Difficulty.values()
        binding.spinnerDifficulty.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, diffs.map { it.displayName })
        binding.spinnerDifficulty.setSelection(1)
        binding.spinnerDifficulty.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(p: AdapterView<*>, v: View?, pos: Int, id: Long) {
                selectedDifficulty = diffs[pos]
                updateDescription()
            }
            override fun onNothingSelected(p: AdapterView<*>) {}
        }
    }

    private fun updateDescription() {
        val size = binding.sliderWorldSize.value.toInt()
        binding.tvSizeLabel.text = "World Size: $size"
        binding.tvConfigSummary.text =
            "${selectedType.displayName} • ${selectedTheme.displayName} • ${selectedDifficulty.displayName} • Size $size"
    }

    override fun onSupportNavigateUp(): Boolean { onBackPressed(); return true }
}
