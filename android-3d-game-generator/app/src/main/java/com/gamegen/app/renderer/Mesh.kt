package com.gamegen.app.renderer

import android.opengl.GLES20
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.FloatBuffer
import java.nio.ShortBuffer

class Mesh(vertices: FloatArray, indices: ShortArray, val stride: Int = 8) {

    private val vbo = IntArray(1)
    private val ibo = IntArray(1)
    val indexCount = indices.size

    private val vertexBuffer: FloatBuffer = ByteBuffer
        .allocateDirect(vertices.size * 4)
        .order(ByteOrder.nativeOrder())
        .asFloatBuffer().apply { put(vertices); position(0) }

    private val indexBuffer: ShortBuffer = ByteBuffer
        .allocateDirect(indices.size * 2)
        .order(ByteOrder.nativeOrder())
        .asShortBuffer().apply { put(indices); position(0) }

    init {
        GLES20.glGenBuffers(1, vbo, 0)
        GLES20.glBindBuffer(GLES20.GL_ARRAY_BUFFER, vbo[0])
        GLES20.glBufferData(GLES20.GL_ARRAY_BUFFER, vertices.size * 4, vertexBuffer, GLES20.GL_STATIC_DRAW)

        GLES20.glGenBuffers(1, ibo, 0)
        GLES20.glBindBuffer(GLES20.GL_ELEMENT_ARRAY_BUFFER, ibo[0])
        GLES20.glBufferData(GLES20.GL_ELEMENT_ARRAY_BUFFER, indices.size * 2, indexBuffer, GLES20.GL_STATIC_DRAW)
    }

    fun bind(posLoc: Int, normalLoc: Int, texLoc: Int) {
        val byteStride = stride * 4
        GLES20.glBindBuffer(GLES20.GL_ARRAY_BUFFER, vbo[0])
        GLES20.glBindBuffer(GLES20.GL_ELEMENT_ARRAY_BUFFER, ibo[0])
        if (posLoc >= 0) {
            GLES20.glEnableVertexAttribArray(posLoc)
            GLES20.glVertexAttribPointer(posLoc, 3, GLES20.GL_FLOAT, false, byteStride, 0)
        }
        if (normalLoc >= 0 && stride >= 6) {
            GLES20.glEnableVertexAttribArray(normalLoc)
            GLES20.glVertexAttribPointer(normalLoc, 3, GLES20.GL_FLOAT, false, byteStride, 12)
        }
        if (texLoc >= 0 && stride >= 8) {
            GLES20.glEnableVertexAttribArray(texLoc)
            GLES20.glVertexAttribPointer(texLoc, 2, GLES20.GL_FLOAT, false, byteStride, 24)
        }
    }

    fun draw() {
        GLES20.glDrawElements(GLES20.GL_TRIANGLES, indexCount, GLES20.GL_UNSIGNED_SHORT, 0)
    }

    fun release() {
        GLES20.glDeleteBuffers(1, vbo, 0)
        GLES20.glDeleteBuffers(1, ibo, 0)
    }

    companion object {
        fun cube(size: Float = 1f): Mesh {
            val h = size / 2f
            val v = floatArrayOf(
                // pos (3), normal (3), uv (2)  — 6 faces × 4 verts
                // Front
                -h,-h, h,  0f, 0f, 1f,  0f,0f,
                 h,-h, h,  0f, 0f, 1f,  1f,0f,
                 h, h, h,  0f, 0f, 1f,  1f,1f,
                -h, h, h,  0f, 0f, 1f,  0f,1f,
                // Back
                 h,-h,-h,  0f, 0f,-1f,  0f,0f,
                -h,-h,-h,  0f, 0f,-1f,  1f,0f,
                -h, h,-h,  0f, 0f,-1f,  1f,1f,
                 h, h,-h,  0f, 0f,-1f,  0f,1f,
                // Left
                -h,-h,-h, -1f, 0f, 0f,  0f,0f,
                -h,-h, h, -1f, 0f, 0f,  1f,0f,
                -h, h, h, -1f, 0f, 0f,  1f,1f,
                -h, h,-h, -1f, 0f, 0f,  0f,1f,
                // Right
                 h,-h, h,  1f, 0f, 0f,  0f,0f,
                 h,-h,-h,  1f, 0f, 0f,  1f,0f,
                 h, h,-h,  1f, 0f, 0f,  1f,1f,
                 h, h, h,  1f, 0f, 0f,  0f,1f,
                // Top
                -h, h, h,  0f, 1f, 0f,  0f,0f,
                 h, h, h,  0f, 1f, 0f,  1f,0f,
                 h, h,-h,  0f, 1f, 0f,  1f,1f,
                -h, h,-h,  0f, 1f, 0f,  0f,1f,
                // Bottom
                -h,-h,-h,  0f,-1f, 0f,  0f,0f,
                 h,-h,-h,  0f,-1f, 0f,  1f,0f,
                 h,-h, h,  0f,-1f, 0f,  1f,1f,
                -h,-h, h,  0f,-1f, 0f,  0f,1f
            )
            val idx = ShortArray(36)
            for (i in 0 until 6) {
                val b = (i * 4).toShort()
                idx[i * 6 + 0] = b; idx[i * 6 + 1] = (b + 1).toShort()
                idx[i * 6 + 2] = (b + 2).toShort(); idx[i * 6 + 3] = b
                idx[i * 6 + 4] = (b + 2).toShort(); idx[i * 6 + 5] = (b + 3).toShort()
            }
            return Mesh(v, idx)
        }

        fun platform(w: Float = 2f, h: Float = 0.3f, d: Float = 2f): Mesh {
            val hw = w / 2; val hh = h / 2; val hd = d / 2
            val v = floatArrayOf(
                -hw,-hh, hd,  0f,0f,1f,  0f,0f,
                 hw,-hh, hd,  0f,0f,1f,  1f,0f,
                 hw, hh, hd,  0f,0f,1f,  1f,1f,
                -hw, hh, hd,  0f,0f,1f,  0f,1f,
                 hw,-hh,-hd,  0f,0f,-1f, 0f,0f,
                -hw,-hh,-hd,  0f,0f,-1f, 1f,0f,
                -hw, hh,-hd,  0f,0f,-1f, 1f,1f,
                 hw, hh,-hd,  0f,0f,-1f, 0f,1f,
                -hw,-hh,-hd, -1f,0f,0f,  0f,0f,
                -hw,-hh, hd, -1f,0f,0f,  1f,0f,
                -hw, hh, hd, -1f,0f,0f,  1f,1f,
                -hw, hh,-hd, -1f,0f,0f,  0f,1f,
                 hw,-hh, hd,  1f,0f,0f,  0f,0f,
                 hw,-hh,-hd,  1f,0f,0f,  1f,0f,
                 hw, hh,-hd,  1f,0f,0f,  1f,1f,
                 hw, hh, hd,  1f,0f,0f,  0f,1f,
                -hw, hh, hd,  0f,1f,0f,  0f,0f,
                 hw, hh, hd,  0f,1f,0f,  1f,0f,
                 hw, hh,-hd,  0f,1f,0f,  1f,1f,
                -hw, hh,-hd,  0f,1f,0f,  0f,1f,
                -hw,-hh,-hd,  0f,-1f,0f, 0f,0f,
                 hw,-hh,-hd,  0f,-1f,0f, 1f,0f,
                 hw,-hh, hd,  0f,-1f,0f, 1f,1f,
                -hw,-hh, hd,  0f,-1f,0f, 0f,1f
            )
            val idx = ShortArray(36)
            for (i in 0 until 6) {
                val b = (i * 4).toShort()
                idx[i*6+0]=b; idx[i*6+1]=(b+1).toShort()
                idx[i*6+2]=(b+2).toShort(); idx[i*6+3]=b
                idx[i*6+4]=(b+2).toShort(); idx[i*6+5]=(b+3).toShort()
            }
            return Mesh(v, idx)
        }

        fun sphere(radius: Float = 0.5f, stacks: Int = 10, slices: Int = 10): Mesh {
            val verts = mutableListOf<Float>()
            val idxList = mutableListOf<Short>()
            val pi = Math.PI.toFloat()
            for (i in 0..stacks) {
                val phi = pi * i / stacks - pi / 2
                for (j in 0..slices) {
                    val theta = 2 * pi * j / slices
                    val x = kotlin.math.cos(phi) * kotlin.math.cos(theta)
                    val y = kotlin.math.sin(phi)
                    val z = kotlin.math.cos(phi) * kotlin.math.sin(theta)
                    verts += x * radius; verts += y * radius; verts += z * radius
                    verts += x; verts += y; verts += z
                    verts += j.toFloat() / slices; verts += i.toFloat() / stacks
                }
            }
            for (i in 0 until stacks) {
                for (j in 0 until slices) {
                    val a = i * (slices + 1) + j
                    val b = a + slices + 1
                    idxList += a.toShort(); idxList += b.toShort(); idxList += (a + 1).toShort()
                    idxList += b.toShort(); idxList += (b + 1).toShort(); idxList += (a + 1).toShort()
                }
            }
            return Mesh(verts.toFloatArray(), idxList.toShortArray())
        }
    }
}
