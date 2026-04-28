package com.gamegen.app.generator

import kotlin.math.*
import kotlin.random.Random

object GameGenerator {

    fun generate(config: GameConfig): GeneratedGame {
        val worldData = when (config.gameType) {
            GameType.MAZE_RUNNER -> generateMaze(config)
            GameType.PLATFORM_JUMP -> generatePlatforms(config)
            GameType.DUNGEON_CRAWLER -> generateDungeon(config)
            GameType.SPACE_SHOOTER -> generateSpace(config)
            GameType.TOWER_CLIMB -> generateTower(config)
        }
        return GeneratedGame(config = config, worldData = worldData)
    }

    private fun generateMaze(config: GameConfig): WorldData {
        val size = config.worldSize.coerceIn(10, 40)
        val rng = Random(config.seed)
        val tiles = Array(size) { IntArray(size) { 1 } }

        // Recursive backtracking maze
        fun carve(x: Int, z: Int) {
            tiles[x][z] = 0
            val dirs = listOf(
                intArrayOf(0, 2), intArrayOf(0, -2),
                intArrayOf(2, 0), intArrayOf(-2, 0)
            ).shuffled(rng)
            for (d in dirs) {
                val nx = x + d[0]; val nz = z + d[1]
                if (nx in 1 until size - 1 && nz in 1 until size - 1 && tiles[nx][nz] == 1) {
                    tiles[x + d[0] / 2][z + d[1] / 2] = 0
                    carve(nx, nz)
                }
            }
        }
        carve(1, 1)

        // Place collectibles in open cells
        val collectibles = mutableListOf<Triple<Float, Float, Float>>()
        val enemies = mutableListOf<Triple<Float, Float, Float>>()
        for (x in 1 until size - 1) {
            for (z in 1 until size - 1) {
                if (tiles[x][z] == 0 && rng.nextFloat() < 0.08f)
                    collectibles.add(Triple(x.toFloat(), 0.5f, z.toFloat()))
                if (tiles[x][z] == 0 && rng.nextFloat() < 0.04f)
                    enemies.add(Triple(x.toFloat(), 0f, z.toFloat()))
            }
        }

        return WorldData(
            width = size, height = size, tiles = tiles,
            spawnX = 1f, spawnZ = 1f,
            exitX = (size - 2).toFloat(), exitZ = (size - 2).toFloat(),
            platformPositions = emptyList(),
            enemyPositions = enemies,
            collectiblePositions = collectibles,
            seed = config.seed
        )
    }

    private fun generatePlatforms(config: GameConfig): WorldData {
        val rng = Random(config.seed)
        val count = (config.worldSize * 1.5f * config.difficulty.multiplier).toInt().coerceIn(8, 60)
        val platforms = mutableListOf<Triple<Float, Float, Float>>()
        val collectibles = mutableListOf<Triple<Float, Float, Float>>()
        val enemies = mutableListOf<Triple<Float, Float, Float>>()

        var x = 0f; var y = 0f; var z = 0f
        platforms.add(Triple(x, y, z))

        for (i in 1 until count) {
            val angle = rng.nextFloat() * PI.toFloat() * 2f
            val dist = 2.5f + rng.nextFloat() * 2f
            x += cos(angle) * dist
            y += 0.5f + rng.nextFloat() * 1.5f
            z += sin(angle) * dist
            platforms.add(Triple(x, y, z))
            if (rng.nextFloat() < 0.3f) collectibles.add(Triple(x, y + 0.8f, z))
            if (i > 3 && rng.nextFloat() < 0.15f) enemies.add(Triple(x, y + 0.5f, z))
        }

        val size = config.worldSize
        val tiles = Array(size) { IntArray(size) { 0 } }
        return WorldData(
            width = size, height = size, tiles = tiles,
            spawnX = 0f, spawnZ = 0f,
            exitX = x, exitZ = z,
            platformPositions = platforms,
            enemyPositions = enemies,
            collectiblePositions = collectibles,
            seed = config.seed
        )
    }

    private fun generateDungeon(config: GameConfig): WorldData {
        val size = config.worldSize.coerceIn(16, 50)
        val rng = Random(config.seed)
        val tiles = Array(size) { IntArray(size) { 1 } }
        val rooms = mutableListOf<IntArray>()

        fun tryPlaceRoom(w: Int, h: Int): Boolean {
            val rx = rng.nextInt(size - w - 2) + 1
            val rz = rng.nextInt(size - h - 2) + 1
            for (x in rx - 1..rx + w) {
                for (z in rz - 1..rz + h) {
                    if (x < 0 || x >= size || z < 0 || z >= size) return false
                    if (tiles[x][z] == 0) return false
                }
            }
            for (x in rx until rx + w) for (z in rz until rz + h) tiles[x][z] = 0
            rooms.add(intArrayOf(rx + w / 2, rz + h / 2))
            return true
        }

        repeat(30) { tryPlaceRoom(rng.nextInt(4) + 3, rng.nextInt(4) + 3) }

        // Connect rooms with corridors
        for (i in 0 until rooms.size - 1) {
            val (ax, az) = rooms[i][0] to rooms[i][1]
            val (bx, bz) = rooms[i + 1][0] to rooms[i + 1][1]
            var cx = ax
            while (cx != bx) { tiles[cx][az] = 0; if (cx < bx) cx++ else cx-- }
            var cz = az
            while (cz != bz) { tiles[bx][cz] = 0; if (cz < bz) cz++ else cz-- }
        }

        val collectibles = mutableListOf<Triple<Float, Float, Float>>()
        val enemies = mutableListOf<Triple<Float, Float, Float>>()
        for (room in rooms.drop(1)) {
            if (rng.nextFloat() < 0.4f) collectibles.add(Triple(room[0].toFloat(), 0.5f, room[1].toFloat()))
            if (rng.nextFloat() < 0.3f) enemies.add(Triple(room[0].toFloat(), 0f, room[1].toFloat()))
        }

        val spawn = rooms.firstOrNull() ?: intArrayOf(1, 1)
        val exit = rooms.lastOrNull() ?: intArrayOf(size - 2, size - 2)
        return WorldData(
            width = size, height = size, tiles = tiles,
            spawnX = spawn[0].toFloat(), spawnZ = spawn[1].toFloat(),
            exitX = exit[0].toFloat(), exitZ = exit[1].toFloat(),
            platformPositions = emptyList(),
            enemyPositions = enemies,
            collectiblePositions = collectibles,
            seed = config.seed
        )
    }

    private fun generateSpace(config: GameConfig): WorldData {
        val rng = Random(config.seed)
        val size = config.worldSize
        val count = (size * 3 * config.difficulty.multiplier).toInt().coerceIn(10, 100)
        val enemies = (0 until count).map {
            Triple(
                (rng.nextFloat() - 0.5f) * size * 2f,
                (rng.nextFloat() - 0.5f) * size.toFloat(),
                (rng.nextFloat() * size * 3f) + 5f
            )
        }
        val collectibles = (0 until count / 3).map {
            Triple(
                (rng.nextFloat() - 0.5f) * size * 1.5f,
                (rng.nextFloat() - 0.5f) * size * 0.8f,
                (rng.nextFloat() * size * 3f) + 5f
            )
        }
        val tiles = Array(size) { IntArray(size) { 0 } }
        return WorldData(
            width = size, height = size, tiles = tiles,
            spawnX = 0f, spawnZ = 0f,
            exitX = 0f, exitZ = size * 3f,
            platformPositions = emptyList(),
            enemyPositions = enemies,
            collectiblePositions = collectibles,
            seed = config.seed
        )
    }

    private fun generateTower(config: GameConfig): WorldData {
        val rng = Random(config.seed)
        val floors = (config.worldSize * config.difficulty.multiplier).toInt().coerceIn(5, 30)
        val platforms = mutableListOf<Triple<Float, Float, Float>>()
        val collectibles = mutableListOf<Triple<Float, Float, Float>>()
        val enemies = mutableListOf<Triple<Float, Float, Float>>()

        for (floor in 0 until floors) {
            val angle = floor * 0.4f
            val radius = 3f + sin(floor * 0.3f) * 1.5f
            val y = floor * 2.5f
            val px = cos(angle) * radius
            val pz = sin(angle) * radius
            platforms.add(Triple(px, y, pz))

            if (floor % 3 == 0) collectibles.add(Triple(px, y + 0.8f, pz))
            if (floor > 2 && rng.nextFloat() < 0.25f) enemies.add(Triple(px, y + 0.5f, pz))
        }

        val size = config.worldSize
        val tiles = Array(size) { IntArray(size) { 0 } }
        return WorldData(
            width = size, height = size, tiles = tiles,
            spawnX = 0f, spawnZ = 0f,
            exitX = platforms.last().first, exitZ = platforms.last().third,
            platformPositions = platforms,
            enemyPositions = enemies,
            collectiblePositions = collectibles,
            seed = config.seed
        )
    }
}
