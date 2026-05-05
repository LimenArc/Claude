package com.aethermon.streamer.network

import com.aethermon.streamer.data.DriveItemsResponse
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.Query
import retrofit2.http.Url

interface GraphApiService {

    @GET("v1.0/me/drive/root/search(q='')")
    suspend fun searchVideos(
        @Header("Authorization") bearer: String,
        @Query("\$filter") filter: String = "video ne null",
        @Query("\$select") select: String = "id,name,size,video,thumbnails,@microsoft.graph.downloadUrl",
        @Query("\$expand") expand: String = "thumbnails",
        @Query("\$top") top: Int = 50
    ): DriveItemsResponse

    @GET
    suspend fun getNextPage(
        @Url url: String,
        @Header("Authorization") bearer: String
    ): DriveItemsResponse
}
