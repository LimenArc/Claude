package com.gamegen.app

import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import com.gamegen.app.databinding.ActivityMainBinding
import com.gamegen.app.ui.GameConfigActivity
import com.gamegen.app.ui.GamesLibraryActivity

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.btnGenerate.setOnClickListener {
            startActivity(Intent(this, GameConfigActivity::class.java))
        }

        binding.btnLibrary.setOnClickListener {
            startActivity(Intent(this, GamesLibraryActivity::class.java))
        }
    }
}
