package com.aethermon.streamer.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.viewModelScope
import com.aethermon.streamer.auth.AuthManager
import com.aethermon.streamer.data.VideoItem
import com.aethermon.streamer.data.VideoRepository
import kotlinx.coroutines.launch

sealed class UiState<out T> {
    object Loading : UiState<Nothing>()
    data class Success<T>(val data: T) : UiState<T>()
    data class Error(val message: String) : UiState<Nothing>()
}

class VideoViewModel(application: Application) : AndroidViewModel(application) {

    val authManager = AuthManager(application)
    private val repository = VideoRepository()

    private val _videos = MutableLiveData<UiState<List<VideoItem>>>(UiState.Loading)
    val videos: LiveData<UiState<List<VideoItem>>> = _videos

    private val _authReady = MutableLiveData(false)
    val authReady: LiveData<Boolean> = _authReady

    fun initAuth() {
        viewModelScope.launch {
            runCatching { authManager.initialize(getApplication()) }
            _authReady.value = true
        }
    }

    fun loadVideos(accessToken: String) {
        _videos.value = UiState.Loading
        viewModelScope.launch {
            runCatching { repository.fetchAllVideos(accessToken) }
                .onSuccess { _videos.value = UiState.Success(it) }
                .onFailure { _videos.value = UiState.Error(it.message ?: "Unknown error") }
        }
    }
}
