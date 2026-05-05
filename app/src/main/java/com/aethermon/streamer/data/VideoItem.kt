package com.aethermon.streamer.data

import android.os.Parcelable
import kotlinx.parcelize.Parcelize

@Parcelize
data class VideoItem(
    val id: String,
    val name: String,
    val size: Long,
    val downloadUrl: String,
    val thumbnailUrl: String?,
    val durationMs: Long?,
    val width: Int?,
    val height: Int?
) : Parcelable
