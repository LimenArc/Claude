package com.gamegen.app.ui

import android.content.Intent
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.gamegen.app.R
import com.gamegen.app.databinding.ActivityGamesLibraryBinding
import com.gamegen.app.generator.GeneratedGame
import com.gamegen.app.generator.GameStorage
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class GamesLibraryActivity : AppCompatActivity() {

    private lateinit var binding: ActivityGamesLibraryBinding
    private val games = mutableListOf<GeneratedGame>()
    private lateinit var adapter: GameAdapter

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityGamesLibraryBinding.inflate(layoutInflater)
        setContentView(binding.root)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        title = "My Games"

        adapter = GameAdapter(games) { game, action ->
            when (action) {
                "play" -> playGame(game)
                "delete" -> confirmDelete(game)
            }
        }
        binding.recyclerGames.layoutManager = LinearLayoutManager(this)
        binding.recyclerGames.adapter = adapter
    }

    override fun onResume() {
        super.onResume()
        games.clear()
        games.addAll(GameStorage.loadAll(this))
        adapter.notifyDataSetChanged()
        binding.tvEmpty.visibility = if (games.isEmpty()) View.VISIBLE else View.GONE
    }

    private fun playGame(game: GeneratedGame) {
        val intent = Intent(this, GameActivity::class.java)
        intent.putExtra(GameActivity.EXTRA_CONFIG, game.config)
        startActivity(intent)
    }

    private fun confirmDelete(game: GeneratedGame) {
        AlertDialog.Builder(this)
            .setTitle("Delete Game")
            .setMessage("Delete \"${game.config.gameName}\"?")
            .setPositiveButton("Delete") { _, _ ->
                GameStorage.delete(this, game.id)
                onResume()
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    override fun onSupportNavigateUp(): Boolean { onBackPressed(); return true }

    inner class GameAdapter(
        private val items: List<GeneratedGame>,
        private val onClick: (GeneratedGame, String) -> Unit
    ) : RecyclerView.Adapter<GameAdapter.VH>() {

        inner class VH(view: View) : RecyclerView.ViewHolder(view) {
            val name: TextView = view.findViewById(R.id.tv_game_name)
            val desc: TextView = view.findViewById(R.id.tv_game_desc)
            val date: TextView = view.findViewById(R.id.tv_game_date)
        }

        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): VH {
            val v = LayoutInflater.from(parent.context).inflate(R.layout.item_game, parent, false)
            return VH(v)
        }

        override fun getItemCount() = items.size

        override fun onBindViewHolder(holder: VH, pos: Int) {
            val game = items[pos]
            holder.name.text = game.config.gameName
            holder.desc.text = game.config.describe()
            val fmt = SimpleDateFormat("MMM d, yyyy HH:mm", Locale.getDefault())
            holder.date.text = fmt.format(Date(game.createdAt))
            holder.itemView.setOnClickListener { onClick(game, "play") }
            holder.itemView.setOnLongClickListener { onClick(game, "delete"); true }
        }
    }
}
