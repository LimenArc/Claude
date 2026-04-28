package com.gamegen.app.renderer

import android.opengl.Matrix
import kotlin.math.*

class Camera {

    val position = floatArrayOf(0f, 2f, 0f)
    var yaw = 0f
    var pitch = -20f

    val viewMatrix = FloatArray(16)
    val projMatrix = FloatArray(16)
    val vpMatrix = FloatArray(16)

    fun setProjection(width: Int, height: Int, fov: Float = 70f, near: Float = 0.1f, far: Float = 200f) {
        val ratio = width.toFloat() / height
        Matrix.perspectiveM(projMatrix, 0, fov, ratio, near, far)
    }

    fun update() {
        val yawRad = Math.toRadians(yaw.toDouble()).toFloat()
        val pitchRad = Math.toRadians(pitch.toDouble()).toFloat()
        val frontX = cos(pitchRad) * sin(yawRad)
        val frontY = sin(pitchRad)
        val frontZ = cos(pitchRad) * (-cos(yawRad))
        Matrix.setLookAtM(
            viewMatrix, 0,
            position[0], position[1], position[2],
            position[0] + frontX, position[1] + frontY, position[2] + frontZ,
            0f, 1f, 0f
        )
        Matrix.multiplyMM(vpMatrix, 0, projMatrix, 0, viewMatrix, 0)
    }

    fun move(dx: Float, dz: Float) {
        val yawRad = Math.toRadians(yaw.toDouble()).toFloat()
        position[0] += (cos(yawRad) * dz + sin(yawRad) * dx)
        position[2] += (sin(yawRad) * dz - cos(yawRad) * dx) * -1f
    }

    fun look(dYaw: Float, dPitch: Float) {
        yaw = (yaw + dYaw) % 360f
        pitch = (pitch + dPitch).coerceIn(-85f, 85f)
    }

    fun frontDirection(): FloatArray {
        val yr = Math.toRadians(yaw.toDouble()).toFloat()
        return floatArrayOf(sin(yr), 0f, -cos(yr))
    }
}
