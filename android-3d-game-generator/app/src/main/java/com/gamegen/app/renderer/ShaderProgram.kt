package com.gamegen.app.renderer

import android.opengl.GLES20

object ShaderProgram {

    val VERTEX_SHADER = """
        uniform mat4 uMVPMatrix;
        uniform mat4 uModelMatrix;
        attribute vec4 aPosition;
        attribute vec3 aNormal;
        attribute vec2 aTexCoord;
        varying vec3 vNormal;
        varying vec3 vFragPos;
        varying vec2 vTexCoord;
        void main() {
            gl_Position = uMVPMatrix * aPosition;
            vFragPos = vec3(uModelMatrix * aPosition);
            vNormal = mat3(uModelMatrix) * aNormal;
            vTexCoord = aTexCoord;
        }
    """.trimIndent()

    val FRAGMENT_SHADER = """
        precision mediump float;
        uniform vec3 uColor;
        uniform vec3 uLightPos;
        uniform vec3 uLightColor;
        uniform vec3 uViewPos;
        uniform float uFogDensity;
        uniform vec3 uFogColor;
        uniform float uEmissive;
        varying vec3 vNormal;
        varying vec3 vFragPos;
        varying vec2 vTexCoord;
        void main() {
            vec3 norm = normalize(vNormal);
            vec3 lightDir = normalize(uLightPos - vFragPos);
            float diff = max(dot(norm, lightDir), 0.0);
            vec3 ambient = 0.25 * uLightColor;
            vec3 diffuse = diff * uLightColor;
            vec3 viewDir = normalize(uViewPos - vFragPos);
            vec3 reflectDir = reflect(-lightDir, norm);
            float spec = pow(max(dot(viewDir, reflectDir), 0.0), 32.0);
            vec3 specular = 0.3 * spec * uLightColor;
            vec3 result = (ambient + diffuse + specular) * uColor + uColor * uEmissive;
            float dist = length(uViewPos - vFragPos);
            float fog = exp(-uFogDensity * dist * dist);
            fog = clamp(fog, 0.0, 1.0);
            gl_FragColor = vec4(mix(uFogColor, result, fog), 1.0);
        }
    """.trimIndent()

    val PARTICLE_VERTEX_SHADER = """
        uniform mat4 uMVPMatrix;
        attribute vec4 aPosition;
        attribute float aSize;
        attribute float aAlpha;
        varying float vAlpha;
        void main() {
            gl_Position = uMVPMatrix * aPosition;
            gl_PointSize = aSize;
            vAlpha = aAlpha;
        }
    """.trimIndent()

    val PARTICLE_FRAGMENT_SHADER = """
        precision mediump float;
        uniform vec3 uColor;
        varying float vAlpha;
        void main() {
            vec2 coord = gl_PointCoord - vec2(0.5);
            float dist = length(coord);
            if (dist > 0.5) discard;
            float alpha = (1.0 - dist * 2.0) * vAlpha;
            gl_FragColor = vec4(uColor, alpha);
        }
    """.trimIndent()

    fun compile(vertSrc: String, fragSrc: String): Int {
        val vert = compileShader(GLES20.GL_VERTEX_SHADER, vertSrc)
        val frag = compileShader(GLES20.GL_FRAGMENT_SHADER, fragSrc)
        val program = GLES20.glCreateProgram()
        GLES20.glAttachShader(program, vert)
        GLES20.glAttachShader(program, frag)
        GLES20.glLinkProgram(program)
        GLES20.glDeleteShader(vert)
        GLES20.glDeleteShader(frag)
        return program
    }

    private fun compileShader(type: Int, src: String): Int {
        val shader = GLES20.glCreateShader(type)
        GLES20.glShaderSource(shader, src)
        GLES20.glCompileShader(shader)
        return shader
    }
}
