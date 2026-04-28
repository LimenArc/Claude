package com.gamegen.app.generator

import android.content.Context
import android.content.SharedPreferences
import com.google.gson.Gson
import com.google.gson.GsonBuilder
import com.google.gson.reflect.TypeToken

object GameStorage {

    private const val PREFS_NAME = "game_library"
    private const val KEY_GAMES = "saved_games"
    private val gson: Gson = GsonBuilder().create()

    private fun prefs(context: Context): SharedPreferences =
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    fun saveGame(context: Context, game: GeneratedGame) {
        val games = loadAll(context).toMutableList()
        games.removeAll { it.id == game.id }
        games.add(0, game)
        val json = gson.toJson(games.take(20))
        prefs(context).edit().putString(KEY_GAMES, json).apply()
    }

    fun loadAll(context: Context): List<GeneratedGame> {
        val json = prefs(context).getString(KEY_GAMES, null) ?: return emptyList()
        return try {
            val type = object : TypeToken<List<GeneratedGame>>() {}.type
            gson.fromJson(json, type) ?: emptyList()
        } catch (e: Exception) {
            emptyList()
        }
    }

    fun delete(context: Context, id: String) {
        val games = loadAll(context).filter { it.id != id }
        prefs(context).edit().putString(KEY_GAMES, gson.toJson(games)).apply()
    }
}
