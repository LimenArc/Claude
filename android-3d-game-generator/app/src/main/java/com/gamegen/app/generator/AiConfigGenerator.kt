package com.gamegen.app.generator

import android.content.Context
import android.content.SharedPreferences
import org.json.JSONObject
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL

object AiConfigGenerator {

    private const val PREFS = "ai_settings"
    private const val KEY_URL = "api_url"
    private const val KEY_MODEL = "model"
    private const val KEY_APIKEY = "api_key"

    private val SYSTEM_PROMPT = """
        You are a game configuration assistant for a 3D game generator app.
        Based on the user's description, output a JSON object with these exact fields:
        - gameType: one of "MAZE_RUNNER", "PLATFORM_JUMP", "DUNGEON_CRAWLER", "SPACE_SHOOTER", "TOWER_CLIMB"
        - theme: one of "NEON", "FANTASY", "SPACE", "LAVA", "ICE"
        - difficulty: one of "EASY", "NORMAL", "HARD", "EXTREME"
        - worldSize: integer 10-40
        - enableFog: boolean
        - enableParticles: boolean
        - gameName: creative short name for this game (max 30 chars)
        Respond with ONLY the JSON object, no markdown, no explanation.
        Example: {"gameType":"MAZE_RUNNER","theme":"NEON","difficulty":"HARD","worldSize":25,"enableFog":true,"enableParticles":true,"gameName":"Neon Labyrinth"}
    """.trimIndent()

    fun getSettings(context: Context): Triple<String, String, String> {
        val p = prefs(context)
        return Triple(
            p.getString(KEY_URL, "http://localhost:11434/v1/chat/completions") ?: "",
            p.getString(KEY_MODEL, "llama3.2") ?: "",
            p.getString(KEY_APIKEY, "") ?: ""
        )
    }

    fun saveSettings(context: Context, url: String, model: String, apiKey: String) {
        prefs(context).edit()
            .putString(KEY_URL, url)
            .putString(KEY_MODEL, model)
            .putString(KEY_APIKEY, apiKey)
            .apply()
    }

    fun isConfigured(context: Context): Boolean {
        val (url, _, _) = getSettings(context)
        return url.isNotBlank()
    }

    fun generate(context: Context, userPrompt: String): GameConfig {
        val (url, model, apiKey) = getSettings(context)
        if (url.isBlank()) return PromptParser.parse(userPrompt)

        return try {
            val json = callApi(url, model, apiKey, userPrompt)
            parseResponse(json, userPrompt)
        } catch (e: Exception) {
            PromptParser.parse(userPrompt)
        }
    }

    private fun callApi(url: String, model: String, apiKey: String, prompt: String): String {
        val body = JSONObject().apply {
            put("model", model.ifBlank { "llama3.2" })
            put("messages", org.json.JSONArray().apply {
                put(JSONObject().apply {
                    put("role", "system")
                    put("content", SYSTEM_PROMPT)
                })
                put(JSONObject().apply {
                    put("role", "user")
                    put("content", prompt)
                })
            })
            put("temperature", 0.3)
            put("max_tokens", 200)
            put("stream", false)
        }.toString()

        val conn = URL(url).openConnection() as HttpURLConnection
        conn.requestMethod = "POST"
        conn.setRequestProperty("Content-Type", "application/json")
        conn.setRequestProperty("Accept", "application/json")
        if (apiKey.isNotBlank()) conn.setRequestProperty("Authorization", "Bearer $apiKey")
        conn.connectTimeout = 15_000
        conn.readTimeout = 30_000
        conn.doOutput = true

        OutputStreamWriter(conn.outputStream).use { it.write(body) }

        val response = conn.inputStream.bufferedReader().readText()
        val root = JSONObject(response)
        return root.getJSONArray("choices")
            .getJSONObject(0)
            .getJSONObject("message")
            .getString("content")
            .trim()
    }

    private fun parseResponse(content: String, originalPrompt: String): GameConfig {
        val jsonStr = content
            .removePrefix("```json").removePrefix("```").removeSuffix("```").trim()
        val obj = JSONObject(jsonStr)

        val gameType = runCatching {
            GameType.valueOf(obj.getString("gameType"))
        }.getOrDefault(PromptParser.extractGameType(originalPrompt))

        val theme = runCatching {
            WorldTheme.valueOf(obj.getString("theme"))
        }.getOrDefault(PromptParser.extractTheme(originalPrompt))

        val difficulty = runCatching {
            Difficulty.valueOf(obj.getString("difficulty"))
        }.getOrDefault(Difficulty.NORMAL)

        return GameConfig(
            gameType = gameType,
            theme = theme,
            difficulty = difficulty,
            worldSize = obj.optInt("worldSize", 20).coerceIn(10, 40),
            enableFog = obj.optBoolean("enableFog", true),
            enableParticles = obj.optBoolean("enableParticles", true),
            gameName = obj.optString("gameName", originalPrompt.take(30)),
            seed = System.currentTimeMillis()
        )
    }

    private fun prefs(context: Context): SharedPreferences =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
}
