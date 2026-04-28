package com.gamegen.app.generator

import kotlin.math.*

class NoiseGenerator(seed: Long) {

    private val permutation = IntArray(512)

    init {
        val rng = java.util.Random(seed)
        val p = IntArray(256) { it }
        for (i in 255 downTo 1) {
            val j = rng.nextInt(i + 1)
            val tmp = p[i]; p[i] = p[j]; p[j] = tmp
        }
        for (i in 0 until 512) permutation[i] = p[i and 255]
    }

    private fun fade(t: Double) = t * t * t * (t * (t * 6 - 15) + 10)
    private fun lerp(t: Double, a: Double, b: Double) = a + t * (b - a)

    private fun grad(hash: Int, x: Double, y: Double): Double {
        return when (hash and 3) {
            0 -> x + y; 1 -> -x + y; 2 -> x - y; else -> -x - y
        }
    }

    fun noise(x: Double, y: Double): Double {
        val xi = floor(x).toInt() and 255
        val yi = floor(y).toInt() and 255
        val xf = x - floor(x)
        val yf = y - floor(y)
        val u = fade(xf)
        val v = fade(yf)
        val aa = permutation[permutation[xi] + yi]
        val ab = permutation[permutation[xi] + yi + 1]
        val ba = permutation[permutation[xi + 1] + yi]
        val bb = permutation[permutation[xi + 1] + yi + 1]
        return lerp(v,
            lerp(u, grad(aa, xf, yf), grad(ba, xf - 1, yf)),
            lerp(u, grad(ab, xf, yf - 1), grad(bb, xf - 1, yf - 1))
        )
    }

    fun octaveNoise(x: Double, y: Double, octaves: Int, persistence: Double): Double {
        var value = 0.0
        var amplitude = 1.0
        var frequency = 1.0
        var maxValue = 0.0
        repeat(octaves) {
            value += noise(x * frequency, y * frequency) * amplitude
            maxValue += amplitude
            amplitude *= persistence
            frequency *= 2.0
        }
        return value / maxValue
    }
}
