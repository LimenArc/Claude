package com.gamegen.app.renderer

import com.gamegen.app.generator.WorldTheme

data class ThemeColors(
    val wallColor: FloatArray,
    val floorColor: FloatArray,
    val skyColor: FloatArray,
    val lightColor: FloatArray,
    val fogColor: FloatArray,
    val collectibleColor: FloatArray,
    val enemyColor: FloatArray,
    val playerColor: FloatArray,
    val platformColor: FloatArray,
    val fogDensity: Float,
    val lightEmissive: Float
)

fun themeColorsFor(theme: WorldTheme): ThemeColors = when (theme) {
    WorldTheme.NEON -> ThemeColors(
        wallColor = floatArrayOf(0.05f, 0.05f, 0.2f),
        floorColor = floatArrayOf(0.02f, 0.02f, 0.15f),
        skyColor = floatArrayOf(0.0f, 0.0f, 0.05f),
        lightColor = floatArrayOf(0.2f, 0.8f, 1.0f),
        fogColor = floatArrayOf(0.0f, 0.0f, 0.1f),
        collectibleColor = floatArrayOf(0.0f, 1.0f, 0.8f),
        enemyColor = floatArrayOf(1.0f, 0.1f, 0.4f),
        playerColor = floatArrayOf(0.3f, 0.6f, 1.0f),
        platformColor = floatArrayOf(0.1f, 0.1f, 0.5f),
        fogDensity = 0.012f,
        lightEmissive = 0.3f
    )
    WorldTheme.FANTASY -> ThemeColors(
        wallColor = floatArrayOf(0.2f, 0.4f, 0.15f),
        floorColor = floatArrayOf(0.15f, 0.3f, 0.1f),
        skyColor = floatArrayOf(0.4f, 0.6f, 0.9f),
        lightColor = floatArrayOf(1.0f, 0.95f, 0.7f),
        fogColor = floatArrayOf(0.6f, 0.75f, 0.5f),
        collectibleColor = floatArrayOf(1.0f, 0.85f, 0.0f),
        enemyColor = floatArrayOf(0.6f, 0.1f, 0.1f),
        playerColor = floatArrayOf(0.5f, 0.8f, 0.3f),
        platformColor = floatArrayOf(0.3f, 0.5f, 0.2f),
        fogDensity = 0.008f,
        lightEmissive = 0.1f
    )
    WorldTheme.SPACE -> ThemeColors(
        wallColor = floatArrayOf(0.05f, 0.05f, 0.08f),
        floorColor = floatArrayOf(0.02f, 0.02f, 0.05f),
        skyColor = floatArrayOf(0.0f, 0.0f, 0.02f),
        lightColor = floatArrayOf(0.8f, 0.8f, 1.0f),
        fogColor = floatArrayOf(0.0f, 0.0f, 0.02f),
        collectibleColor = floatArrayOf(1.0f, 0.9f, 0.0f),
        enemyColor = floatArrayOf(0.8f, 0.3f, 0.0f),
        playerColor = floatArrayOf(0.7f, 0.7f, 0.9f),
        platformColor = floatArrayOf(0.1f, 0.1f, 0.2f),
        fogDensity = 0.002f,
        lightEmissive = 0.5f
    )
    WorldTheme.LAVA -> ThemeColors(
        wallColor = floatArrayOf(0.25f, 0.08f, 0.02f),
        floorColor = floatArrayOf(0.4f, 0.1f, 0.0f),
        skyColor = floatArrayOf(0.15f, 0.05f, 0.0f),
        lightColor = floatArrayOf(1.0f, 0.5f, 0.1f),
        fogColor = floatArrayOf(0.3f, 0.05f, 0.0f),
        collectibleColor = floatArrayOf(1.0f, 0.8f, 0.0f),
        enemyColor = floatArrayOf(0.9f, 0.2f, 0.0f),
        playerColor = floatArrayOf(0.8f, 0.4f, 0.1f),
        platformColor = floatArrayOf(0.3f, 0.1f, 0.0f),
        fogDensity = 0.018f,
        lightEmissive = 0.4f
    )
    WorldTheme.ICE -> ThemeColors(
        wallColor = floatArrayOf(0.7f, 0.85f, 1.0f),
        floorColor = floatArrayOf(0.75f, 0.9f, 1.0f),
        skyColor = floatArrayOf(0.6f, 0.8f, 1.0f),
        lightColor = floatArrayOf(0.9f, 0.95f, 1.0f),
        fogColor = floatArrayOf(0.7f, 0.85f, 1.0f),
        collectibleColor = floatArrayOf(0.0f, 0.9f, 1.0f),
        enemyColor = floatArrayOf(0.2f, 0.4f, 0.9f),
        playerColor = floatArrayOf(0.9f, 0.95f, 1.0f),
        platformColor = floatArrayOf(0.6f, 0.8f, 1.0f),
        fogDensity = 0.015f,
        lightEmissive = 0.0f
    )
}
