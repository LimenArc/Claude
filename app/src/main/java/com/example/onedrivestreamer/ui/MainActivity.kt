package com.example.onedrivestreamer.ui

import android.os.Bundle
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.navigation.NavController
import androidx.navigation.fragment.NavHostFragment
import androidx.navigation.ui.AppBarConfiguration
import androidx.navigation.ui.setupActionBarWithNavController
import androidx.navigation.ui.setupWithNavController
import com.example.onedrivestreamer.R
import com.example.onedrivestreamer.databinding.ActivityMainBinding

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    val viewModel: VideoViewModel by viewModels()
    private var navController: NavController? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)
        setSupportActionBar(binding.toolbar)

        // Show previous crash so we can diagnose remotely
        val prefs = getSharedPreferences("crash_log", android.content.Context.MODE_PRIVATE)
        val crash = prefs.getString("crash", null)
        if (crash != null) {
            prefs.edit().remove("crash").apply()
            android.app.AlertDialog.Builder(this)
                .setTitle("Crash Log (send to developer)")
                .setMessage(crash)
                .setPositiveButton("OK", null)
                .show()
        }

        viewModel.initAuth()
    }

    override fun onStart() {
        super.onStart()
        val navHostFragment = supportFragmentManager
            .findFragmentById(R.id.nav_host_fragment) as? NavHostFragment ?: return
        navController = navHostFragment.navController
        val appBarConfig = AppBarConfiguration(setOf(R.id.videoListFragment))
        setupActionBarWithNavController(navHostFragment.navController, appBarConfig)
        binding.toolbar.setupWithNavController(navHostFragment.navController, appBarConfig)
    }

    override fun onSupportNavigateUp(): Boolean {
        return navController?.navigateUp() ?: false || super.onSupportNavigateUp()
    }
}
