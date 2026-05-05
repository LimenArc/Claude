package com.example.onedrivestreamer.data

import com.google.gson.annotations.SerializedName

data class DriveItemsResponse(
    @SerializedName("value") val items: List<DriveItem>,
    @SerializedName("@odata.nextLink") val nextLink: String?
)

data class DriveItem(
    val id: String,
    val name: String,
    val size: Long?,
    @SerializedName("@microsoft.graph.downloadUrl") val downloadUrl: String?,
    val video: VideoFacet?,
    val thumbnails: List<ThumbnailSet>?
)

data class VideoFacet(
    val duration: Long?,
    val width: Int?,
    val height: Int?
)

data class ThumbnailSet(
    val medium: Thumbnail?
)

data class Thumbnail(
    val url: String?
)
