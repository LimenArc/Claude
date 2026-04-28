package com.gamegen.app.generator

import java.io.Serializable

enum class GameType(val displayName: String, val description: String) {
    MAZE_RUNNER("Maze Runner", "Navigate through a procedural 3D maze"),
    PLATFORM_JUMP("Platform Jump", "Jump across floating 3D platforms"),
    DUNGEON_CRAWLER("Dungeon Crawler", "Explore a dark procedural dungeon"),
    SPACE_SHOOTER("Space Shooter", "Dodge asteroids in 3D space"),
    TOWER_CLIMB("Tower Climb", "Spiral up a procedurally generated tower")
}

enum class WorldTheme(val displayName: String) {
    NEON("Neon City"),
    FANTASY("Fantasy Forest"),
    SPACE("Deep Space"),
    LAVA("Volcanic"),
    ICE("Arctic")
}

enum class Difficulty(val displayName: String, val multiplier: Float) {
    EASY("Easy", 0.6f),
    NORMAL("Normal", 1.0f),
    HARD("Hard", 1.5f),
    EXTREME("Extreme", 2.2f)
}

data class GameConfig(
    val gameType: GameType = GameType.MAZE_RUNNER,
    val theme: WorldTheme = WorldTheme.NEON,
    val difficulty: Difficulty = Difficulty.NORMAL,
    val worldSize: Int = 20,
    val seed: Long = System.currentTimeMillis(),
    val playerSpeed: Float = 5f,
    val enableFog: Boolean = true,
    val enableParticles: Boolean = true,
    val gameName: String = ""
) : Serializable {

    fun describe(): String = buildString {
        append("${gameType.displayName} • ${theme.displayName} • ")
        append("${difficulty.displayName} • Size $worldSize")
    }
}

data class GeneratedGame(
    val id: String = java.util.UUID.randomUUID().toString(),
    val config: GameConfig,
    val worldData: WorldData,
    val createdAt: Long = System.currentTimeMillis()
) : Serializable

data class WorldData(
    val width: Int,
    val height: Int,
    val tiles: Array<IntArray>,
    val spawnX: Float,
    val spawnZ: Float,
    val exitX: Float,
    val exitZ: Float,
    val platformPositions: List<Triple<Float, Float, Float>>,
    val enemyPositions: List<Triple<Float, Float, Float>>,
    val collectiblePositions: List<Triple<Float, Float, Float>>,
    val seed: Long
) : Serializable {
    override fun equals(other: Any?) = other is WorldData && seed == other.seed
    override fun hashCode() = seed.hashCode()
}
