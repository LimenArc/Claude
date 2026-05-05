package com.aethermon.streamer.ui

import android.os.Bundle
import android.widget.ScrollView
import android.widget.TextView
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.navigation.NavController
import androidx.navigation.fragment.NavHostFragment
import androidx.navigation.ui.AppBarConfiguration
import androidx.navigation.ui.setupActionBarWithNavController
import androidx.navigation.ui.setupWithNavController
import com.aethermon.streamer.R
import com.aethermon.streamer.databinding.ActivityMainBinding

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    val viewModel: VideoViewModel by viewModels()
    private var navController: NavController? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Show crash from PREVIOUS run before anything else can crash
        val prefs = getSharedPreferences("crash_log", MODE_PRIVATE)
        val prevCrash = prefs.getString("crash", null)
        if (prevCrash != null) {
            prefs.edit().remove("crash").apply()
            showCrash(prevCrash)
            return
        }

        try {
            binding = ActivityMainBinding.inflate(layoutInflater)
        } catch (e: Exception) {
            showCrash("INFLATE ERROR:\n${e.stackTraceToString()}")
            return
        }

        try {
            setContentView(binding.root)
        } catch (e: Exception) {
            showCrash("SET_CONTENT ERROR:\n${e.stackTraceToString()}")
            return
        }

        try {
            setSupportActionBar(binding.toolbar)
            viewModel.initAuth()
        } catch (e: Exception) {
            showCrash("INIT ERROR:\n${e.stackTraceToString()}")
        }
    }

    private fun showCrash(msg: String) {
        val tv = TextView(this).apply {
            text = msg
            setPadding(24, 24, 24, 24)
            textSize = 10f
            setTextIsSelectable(true)
        }
        val sv = ScrollView(this)
        sv.addView(tv)
        setContentView(sv)
    }

    override fun onStart() {
        super.onStart()
        if (!::binding.isInitialized) return
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
