package com.gamegen.app.generator

object PromptParser {

    fun parse(prompt: String): GameConfig {
        val p = prompt.lowercase()
        return GameConfig(
            gameType = extractGameType(p),
            theme = extractTheme(p),
            difficulty = extractDifficulty(p),
            worldSize = extractWorldSize(p),
            enableFog = !p.contains("no fog") && !p.contains("clear"),
            enableParticles = !p.contains("no particle"),
            gameName = prompt.take(40).replaceFirstChar { it.uppercase() },
            seed = System.currentTimeMillis()
        )
    }

    fun extractGameType(p: String): GameType = when {
        p.containsAny("maze", "labyrinth", "corridor") -> GameType.MAZE_RUNNER
        p.containsAny("platform", "jump", "hop", "leap") -> GameType.PLATFORM_JUMP
        p.containsAny("dungeon", "cave", "crypt", "underground") -> GameType.DUNGEON_CRAWLER
        p.containsAny("space", "star", "asteroid", "shoot", "galaxy") -> GameType.SPACE_SHOOTER
        p.containsAny("tower", "climb", "spiral", "ascend") -> GameType.TOWER_CLIMB
        else -> GameType.MAZE_RUNNER
    }

    fun extractTheme(p: String): WorldTheme = when {
        p.containsAny("neon", "cyber", "futuristic", "city", "urban") -> WorldTheme.NEON
        p.containsAny("fantasy", "forest", "magic", "enchanted", "green") -> WorldTheme.FANTASY
        p.containsAny("space", "cosmic", "galaxy", "star", "dark") -> WorldTheme.SPACE
        p.containsAny("lava", "fire", "volcano", "hot", "magma", "hell") -> WorldTheme.LAVA
        p.containsAny("ice", "snow", "frozen", "arctic", "cold", "winter") -> WorldTheme.ICE
        else -> WorldTheme.NEON
    }

    fun extractDifficulty(p: String): Difficulty = when {
        p.containsAny("easy", "simple", "beginner", "casual", "relaxed") -> Difficulty.EASY
        p.containsAny("extreme", "impossible", "insane", "nightmare") -> Difficulty.EXTREME
        p.containsAny("hard", "difficult", "challenging", "tough") -> Difficulty.HARD
        else -> Difficulty.NORMAL
    }

    fun extractWorldSize(p: String): Int {
        val sizeWords = mapOf(
            "tiny" to 10, "small" to 12, "medium" to 20,
            "large" to 28, "big" to 28, "huge" to 35, "massive" to 40, "giant" to 40
        )
        for ((word, size) in sizeWords) if (p.contains(word)) return size
        val numMatch = Regex("\\b(\\d+)\\b").findAll(p)
            .map { it.value.toIntOrNull() ?: 0 }
            .firstOrNull { it in 10..40 }
        return numMatch ?: 20
    }

    private fun String.containsAny(vararg keywords: String) = keywords.any { contains(it) }
}
