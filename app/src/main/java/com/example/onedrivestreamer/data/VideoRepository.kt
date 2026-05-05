package com.example.onedrivestreamer.data

import com.example.onedrivestreamer.network.RetrofitClient

class VideoRepository {

    private val api = RetrofitClient.graphApiService

    suspend fun fetchAllVideos(accessToken: String): List<VideoItem> {
        val bearer = "Bearer $accessToken"
        val result = mutableListOf<VideoItem>()
        var response = api.searchVideos(bearer)
        result += response.items.mapNotNull { it.toVideoItem() }

        var nextLink = response.nextLink
        while (nextLink != null) {
            response = api.getNextPage(nextLink, bearer)
            result += response.items.mapNotNull { it.toVideoItem() }
            nextLink = response.nextLink
        }
        return result
    }

    private fun DriveItem.toVideoItem(): VideoItem? {
        val url = downloadUrl ?: return null
        return VideoItem(
            id = id,
            name = name,
            size = size ?: 0L,
            downloadUrl = url,
            thumbnailUrl = thumbnails?.firstOrNull()?.medium?.url,
            durationMs = video?.duration,
            width = video?.width,
            height = video?.height
        )
    }
}
