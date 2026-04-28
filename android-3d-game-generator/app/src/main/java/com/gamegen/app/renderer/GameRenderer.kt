package com.gamegen.app.renderer

import android.opengl.GLES20
import android.opengl.GLSurfaceView
import android.opengl.Matrix
import com.gamegen.app.generator.*
import javax.microedition.khronos.egl.EGLConfig
import javax.microedition.khronos.opengles.GL10
import kotlin.math.*

class GameRenderer(private val game: GeneratedGame) : GLSurfaceView.Renderer {

    private var program = 0
    private lateinit var wallMesh: Mesh
    private lateinit var floorMesh: Mesh
    private lateinit var collectibleMesh: Mesh
    private lateinit var enemyMesh: Mesh
    private lateinit var exitMesh: Mesh

    val camera = Camera()
    private val colors = themeColorsFor(game.config.theme)
    private val world = game.worldData

    var score = 0
    var lives = 3
    var gameOver = false
    var gameWon = false
    var onScoreChanged: ((Int) -> Unit)? = null
    var onLivesChanged: ((Int) -> Unit)? = null
    var onGameOver: (() -> Unit)? = null
    var onGameWon: (() -> Unit)? = null

    private val collectibleAlive = BooleanArray(world.collectiblePositions.size) { true }
    private var lightAngle = 0f
    private var time = 0f

    private val modelMatrix = FloatArray(16)
    private val mvpMatrix = FloatArray(16)
    private val tmpMatrix = FloatArray(16)

    private var posLoc = 0
    private var normalLoc = 0
    private var texLoc = 0
    private var mvpLoc = 0
    private var modelLoc = 0
    private var colorLoc = 0
    private var lightPosLoc = 0
    private var lightColorLoc = 0
    private var viewPosLoc = 0
    private var fogDensityLoc = 0
    private var fogColorLoc = 0
    private var emissiveLoc = 0

    private var moveForward = false
    private var moveBack = false
    private var moveLeft = false
    private var moveRight = false
    private var velocityY = 0f
    private var isGrounded = true

    override fun onSurfaceCreated(gl: GL10, config: EGLConfig) {
        val sky = colors.skyColor
        GLES20.glClearColor(sky[0], sky[1], sky[2], 1f)
        GLES20.glEnable(GLES20.GL_DEPTH_TEST)
        GLES20.glEnable(GLES20.GL_CULL_FACE)

        program = ShaderProgram.compile(ShaderProgram.VERTEX_SHADER, ShaderProgram.FRAGMENT_SHADER)
        wallMesh = Mesh.cube(1f)
        floorMesh = Mesh.platform(1f, 0.1f, 1f)
        collectibleMesh = Mesh.sphere(0.25f, 8, 8)
        enemyMesh = Mesh.cube(0.6f)
        exitMesh = Mesh.cube(0.8f)

        posLoc = GLES20.glGetAttribLocation(program, "aPosition")
        normalLoc = GLES20.glGetAttribLocation(program, "aNormal")
        texLoc = GLES20.glGetAttribLocation(program, "aTexCoord")
        mvpLoc = GLES20.glGetUniformLocation(program, "uMVPMatrix")
        modelLoc = GLES20.glGetUniformLocation(program, "uModelMatrix")
        colorLoc = GLES20.glGetUniformLocation(program, "uColor")
        lightPosLoc = GLES20.glGetUniformLocation(program, "uLightPos")
        lightColorLoc = GLES20.glGetUniformLocation(program, "uLightColor")
        viewPosLoc = GLES20.glGetUniformLocation(program, "uViewPos")
        fogDensityLoc = GLES20.glGetUniformLocation(program, "uFogDensity")
        fogColorLoc = GLES20.glGetUniformLocation(program, "uFogColor")
        emissiveLoc = GLES20.glGetUniformLocation(program, "uEmissive")

        camera.position[0] = world.spawnX
        camera.position[1] = 1.7f
        camera.position[2] = world.spawnZ
    }

    override fun onSurfaceChanged(gl: GL10, width: Int, height: Int) {
        GLES20.glViewport(0, 0, width, height)
        camera.setProjection(width, height)
    }

    override fun onDrawFrame(gl: GL10) {
        if (gameOver || gameWon) return
        val dt = 0.016f
        time += dt
        lightAngle += dt * 0.3f

        update(dt)

        val sky = colors.skyColor
        GLES20.glClearColor(sky[0], sky[1], sky[2], 1f)
        GLES20.glClear(GLES20.GL_COLOR_BUFFER_BIT or GLES20.GL_DEPTH_BUFFER_BIT)

        GLES20.glUseProgram(program)
        camera.update()

        val lx = camera.position[0] + cos(lightAngle) * 10f
        val ly = 15f
        val lz = camera.position[2] + sin(lightAngle) * 10f
        GLES20.glUniform3f(lightPosLoc, lx, ly, lz)
        GLES20.glUniform3fv(lightColorLoc, 1, colors.lightColor, 0)
        GLES20.glUniform3fv(viewPosLoc, 1, camera.position, 0)
        GLES20.glUniform1f(fogDensityLoc, if (game.config.enableFog) colors.fogDensity else 0f)
        GLES20.glUniform3fv(fogColorLoc, 1, colors.fogColor, 0)

        when (game.config.gameType) {
            GameType.MAZE_RUNNER, GameType.DUNGEON_CRAWLER -> drawTileWorld()
            GameType.PLATFORM_JUMP, GameType.TOWER_CLIMB -> drawPlatformWorld()
            GameType.SPACE_SHOOTER -> drawSpaceWorld()
        }

        drawCollectibles()
        drawEnemies()
        drawExit()
        checkCollisions()
    }

    private fun update(dt: Float) {
        val speed = game.config.playerSpeed * dt
        if (moveForward) camera.move(0f, speed)
        if (moveBack) camera.move(0f, -speed)
        if (moveLeft) camera.move(-speed, 0f)
        if (moveRight) camera.move(speed, 0f)

        // Gravity for platform games
        if (game.config.gameType == GameType.PLATFORM_JUMP || game.config.gameType == GameType.TOWER_CLIMB) {
            velocityY -= 20f * dt
            camera.position[1] += velocityY * dt
            val groundY = findGroundY()
            if (camera.position[1] < groundY + 1.7f) {
                camera.position[1] = groundY + 1.7f
                velocityY = 0f
                isGrounded = true
            } else {
                isGrounded = false
            }
        } else {
            val tileX = camera.position[0].toInt()
            val tileZ = camera.position[2].toInt()
            if (!isTileWalkable(tileX, tileZ)) {
                camera.position[0] = world.spawnX
                camera.position[2] = world.spawnZ
            }
            camera.position[1] = 1.7f
        }

        // Fall death
        if (camera.position[1] < -10f) {
            loseLife()
        }
    }

    private fun findGroundY(): Float {
        var best = -5f
        for (p in world.platformPositions) {
            val dx = abs(camera.position[0] - p.first)
            val dz = abs(camera.position[2] - p.third)
            if (dx < 1.2f && dz < 1.2f) {
                val top = p.second + 0.15f
                if (top > best && top < camera.position[1]) best = top
            }
        }
        return best
    }

    private fun isTileWalkable(x: Int, z: Int): Boolean {
        if (x < 0 || z < 0 || x >= world.width || z >= world.height) return false
        return world.tiles[x][z] == 0
    }

    fun jump() {
        if (isGrounded) {
            velocityY = 7f
            isGrounded = false
        }
    }

    fun setMovement(forward: Boolean, back: Boolean, left: Boolean, right: Boolean) {
        moveForward = forward; moveBack = back; moveLeft = left; moveRight = right
    }

    private fun drawTileWorld() {
        // Draw floor
        for (x in 0 until world.width) {
            for (z in 0 until world.height) {
                if (world.tiles[x][z] == 0) {
                    drawMesh(floorMesh, x.toFloat(), -0.05f, z.toFloat(), colors.floorColor, 0f)
                } else {
                    drawMesh(wallMesh, x.toFloat(), 0.5f, z.toFloat(), colors.wallColor, colors.lightEmissive * 0.5f)
                }
            }
        }
    }

    private fun drawPlatformWorld() {
        for (p in world.platformPositions) {
            drawMeshScale(floorMesh, p.first, p.second, p.third, 2f, 0.3f, 2f, colors.platformColor, colors.lightEmissive * 0.3f)
        }
    }

    private fun drawSpaceWorld() {
        // Draw background asteroids (enemies act as asteroids in space mode)
    }

    private fun drawCollectibles() {
        val bob = sin(time * 3f) * 0.1f
        for (i in world.collectiblePositions.indices) {
            if (!collectibleAlive[i]) continue
            val p = world.collectiblePositions[i]
            drawMesh(collectibleMesh, p.first, p.second + bob, p.third, colors.collectibleColor, 0.8f)
        }
    }

    private fun drawEnemies() {
        val bob = sin(time * 2f) * 0.05f
        for (p in world.enemyPositions) {
            drawMesh(enemyMesh, p.first, p.second + 0.3f + bob, p.third, colors.enemyColor, 0.2f)
        }
    }

    private fun drawExit() {
        val pulse = 0.5f + 0.5f * sin(time * 4f)
        val c = floatArrayOf(1.0f * pulse, 0.8f, 0.0f)
        drawMesh(exitMesh, world.exitX, 0.4f, world.exitZ, c, 0.9f)
    }

    private fun checkCollisions() {
        val px = camera.position[0]
        val py = camera.position[1]
        val pz = camera.position[2]

        // Collectibles
        for (i in world.collectiblePositions.indices) {
            if (!collectibleAlive[i]) continue
            val c = world.collectiblePositions[i]
            val d = sqrt((px - c.first).pow(2f) + (py - 1f - c.second).pow(2f) + (pz - c.third).pow(2f))
            if (d < 0.8f) {
                collectibleAlive[i] = false
                score += 10
                onScoreChanged?.invoke(score)
            }
        }

        // Enemies
        for (e in world.enemyPositions) {
            val d = sqrt((px - e.first).pow(2f) + (pz - e.third).pow(2f))
            if (d < 0.7f) loseLife()
        }

        // Exit
        val de = sqrt((px - world.exitX).pow(2f) + (pz - world.exitZ).pow(2f))
        if (de < 1.2f) {
            gameWon = true
            onGameWon?.invoke()
        }
    }

    private fun loseLife() {
        lives--
        onLivesChanged?.invoke(lives)
        if (lives <= 0) {
            gameOver = true
            onGameOver?.invoke()
        } else {
            camera.position[0] = world.spawnX
            camera.position[1] = 1.7f
            camera.position[2] = world.spawnZ
            velocityY = 0f
        }
    }

    private fun drawMesh(mesh: Mesh, x: Float, y: Float, z: Float, color: FloatArray, emissive: Float) {
        Matrix.setIdentityM(modelMatrix, 0)
        Matrix.translateM(modelMatrix, 0, x, y, z)
        Matrix.multiplyMM(mvpMatrix, 0, camera.vpMatrix, 0, modelMatrix, 0)
        GLES20.glUniformMatrix4fv(mvpLoc, 1, false, mvpMatrix, 0)
        GLES20.glUniformMatrix4fv(modelLoc, 1, false, modelMatrix, 0)
        GLES20.glUniform3fv(colorLoc, 1, color, 0)
        GLES20.glUniform1f(emissiveLoc, emissive)
        mesh.bind(posLoc, normalLoc, texLoc)
        mesh.draw()
    }

    private fun drawMeshScale(mesh: Mesh, x: Float, y: Float, z: Float, sx: Float, sy: Float, sz: Float, color: FloatArray, emissive: Float) {
        Matrix.setIdentityM(modelMatrix, 0)
        Matrix.translateM(modelMatrix, 0, x, y, z)
        Matrix.scaleM(modelMatrix, 0, sx, sy, sz)
        Matrix.multiplyMM(mvpMatrix, 0, camera.vpMatrix, 0, modelMatrix, 0)
        GLES20.glUniformMatrix4fv(mvpLoc, 1, false, mvpMatrix, 0)
        GLES20.glUniformMatrix4fv(modelLoc, 1, false, modelMatrix, 0)
        GLES20.glUniform3fv(colorLoc, 1, color, 0)
        GLES20.glUniform1f(emissiveLoc, emissive)
        mesh.bind(posLoc, normalLoc, texLoc)
        mesh.draw()
    }
}
