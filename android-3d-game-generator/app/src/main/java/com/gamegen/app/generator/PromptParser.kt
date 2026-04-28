package com.gamegen.app.generator

object PromptParser {

    data class ParseResult(
        val config: GameConfig,
        val detectedType: String,
        val detectedTheme: String,
        val detectedDifficulty: String,
        val notes: List<String>
    )

    fun parseWithDetails(prompt: String): ParseResult {
        val p = prompt.lowercase()
        val notes = mutableListOf<String>()

        val gameType = extractGameType(p)
        val theme = extractTheme(p, gameType, notes)
        val difficulty = extractDifficulty(p, notes)
        val worldSize = extractWorldSize(p)
        val gameName = generateName(prompt, gameType, theme)

        if (p.containsAny("gun", "guns", "weapon", "armed", "shoot", "bullet"))
            notes.add("Armed enemies detected")
        if (p.containsAny("baby", "babies", "tiny", "small", "mini", "little"))
            notes.add("Tiny scale world")
        if (p.containsAny("scary", "horror", "creepy", "spooky", "haunted"))
            notes.add("Horror atmosphere")
        if (p.containsAny("rainbow", "colorful", "colour", "bright", "vibrant"))
            notes.add("Colorful world")
        if (p.containsAny("fast", "speed", "quick", "rush", "sprint"))
            notes.add("High speed")

        val config = GameConfig(
            gameType = gameType,
            theme = theme,
            difficulty = difficulty,
            worldSize = worldSize,
            enableFog = !p.containsAny("no fog", "clear sky", "bright") ,
            enableParticles = !p.contains("no particle"),
            gameName = gameName,
            seed = System.currentTimeMillis(),
            playerSpeed = extractSpeed(p)
        )

        return ParseResult(
            config = config,
            detectedType = gameType.displayName,
            detectedTheme = theme.displayName,
            detectedDifficulty = difficulty.displayName,
            notes = notes
        )
    }

    fun parse(prompt: String): GameConfig = parseWithDetails(prompt).config

    fun extractGameType(p: String): GameType = when {
        p.containsAny("maze", "labyrinth", "corridor", "lost", "navigate") -> GameType.MAZE_RUNNER
        p.containsAny("platform", "jump", "hop", "leap", "floating", "bounce") -> GameType.PLATFORM_JUMP
        p.containsAny("dungeon", "cave", "crypt", "underground", "RPG", "loot") -> GameType.DUNGEON_CRAWLER
        p.containsAny("space", "asteroid", "galaxy", "alien", "spaceship", "cosmos") -> GameType.SPACE_SHOOTER
        p.containsAny("tower", "climb", "spiral", "ascend", "top", "summit", "rise") -> GameType.TOWER_CLIMB
        p.containsAny("gun", "shoot", "bullet", "weapon", "blast") -> GameType.SPACE_SHOOTER
        else -> GameType.MAZE_RUNNER
    }

    fun extractTheme(p: String, gameType: GameType? = null, notes: MutableList<String>? = null): WorldTheme = when {
        p.containsAny("neon", "cyber", "futuristic", "city", "urban", "tech") -> WorldTheme.NEON
        p.containsAny("fantasy", "forest", "magic", "enchanted", "fairy", "dragon", "baby", "babies", "cute", "fun") -> WorldTheme.FANTASY
        p.containsAny("space", "cosmic", "galaxy", "star", "void", "dark", "alien") -> WorldTheme.SPACE
        p.containsAny("lava", "fire", "volcano", "hot", "magma", "hell", "inferno", "burn") -> WorldTheme.LAVA
        p.containsAny("ice", "snow", "frozen", "arctic", "cold", "winter", "freeze", "blizzard") -> WorldTheme.ICE
        else -> when (gameType) {
            GameType.SPACE_SHOOTER -> WorldTheme.SPACE
            GameType.DUNGEON_CRAWLER -> WorldTheme.FANTASY
            GameType.TOWER_CLIMB -> WorldTheme.NEON
            else -> WorldTheme.NEON
        }
    }

    fun extractDifficulty(p: String, notes: MutableList<String>? = null): Difficulty = when {
        p.containsAny("easy", "simple", "beginner", "casual", "baby", "babies", "relaxed", "chill") -> Difficulty.EASY
        p.containsAny("extreme", "impossible", "insane", "nightmare", "brutal", "death", "godlike") -> Difficulty.EXTREME
        p.containsAny("hard", "difficult", "challenging", "tough", "gun", "guns", "armed", "dangerous") -> Difficulty.HARD
        else -> Difficulty.NORMAL
    }

    fun extractWorldSize(p: String): Int {
        val sizeWords = mapOf(
            "tiny" to 10, "mini" to 11, "small" to 12, "medium" to 20,
            "large" to 28, "big" to 28, "huge" to 35, "massive" to 40,
            "giant" to 40, "epic" to 35, "enormous" to 40
        )
        for ((word, size) in sizeWords) if (p.contains(word)) return size
        val numMatch = Regex("\\b(\\d+)\\b").findAll(p)
            .map { it.value.toIntOrNull() ?: 0 }
            .firstOrNull { it in 10..40 }
        return numMatch ?: 20
    }

    private fun extractSpeed(p: String): Float = when {
        p.containsAny("fast", "speed", "quick", "rush", "sprint", "zoom") -> 8f
        p.containsAny("slow", "careful", "sneak", "stealth") -> 3f
        else -> 5f
    }

    private fun generateName(original: String, type: GameType, theme: WorldTheme): String {
        val p = original.lowercase()
        val adjectives = buildList {
            if (p.containsAny("baby", "babies")) add("Baby")
            if (p.containsAny("gun", "guns", "armed")) add("Armed")
            if (p.containsAny("scary", "horror", "spooky")) add("Haunted")
            if (p.containsAny("fast", "speed", "quick")) add("Turbo")
            if (p.containsAny("big", "huge", "massive", "giant")) add("Mega")
            if (p.containsAny("tiny", "mini", "small")) add("Micro")
            if (p.containsAny("dark", "night", "shadow")) add("Shadow")
            if (p.containsAny("fire", "lava", "burn")) add("Inferno")
        }
        val base = "${theme.displayName} ${type.displayName}"
        return if (adjectives.isNotEmpty()) "${adjectives.first()} $base" else base
    }

    private fun String.containsAny(vararg keywords: String) = keywords.any { contains(it) }
}
