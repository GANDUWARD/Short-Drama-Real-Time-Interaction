package com.shortdrama.app.ui.player

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import androidx.media3.common.MediaItem
import androidx.media3.common.Player
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.exoplayer.SeekParameters
import com.shortdrama.app.data.model.Episode
import com.shortdrama.app.data.model.Highlight
import com.shortdrama.app.data.repository.DramaRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class PlayerUiState(
    val isLoading: Boolean = true,
    val episode: Episode? = null,
    val highlights: List<Highlight> = emptyList(),
    val errorMessage: String? = null,
    val player: ExoPlayer? = null
)

class PlayerViewModel(
    private val repository: DramaRepository,
    private val episodeId: Long
) : ViewModel() {

    private val _uiState = MutableStateFlow(PlayerUiState())
    val uiState: StateFlow<PlayerUiState> = _uiState.asStateFlow()

    init {
        loadEpisode()
    }

    private fun loadEpisode() {
        viewModelScope.launch {
            _uiState.value = PlayerUiState(isLoading = true)

            val episodeResult = repository.getEpisodeDetail(episodeId)
            val highlightsResult = repository.getHighlightsByEpisode(episodeId)

            episodeResult.onSuccess { episode ->
                val highlights = highlightsResult.getOrDefault(emptyList())
                _uiState.value = PlayerUiState(
                    isLoading = false,
                    episode = episode,
                    highlights = highlights
                )
            }.onFailure { e ->
                _uiState.value = PlayerUiState(
                    isLoading = false,
                    errorMessage = e.message ?: "加载失败"
                )
            }
        }
    }

    fun createPlayer(context: android.content.Context): ExoPlayer {
        val player = ExoPlayer.Builder(context)
            .setSeekParameters(SeekParameters.EXACT)
            .build()
        val videoUrl = _uiState.value.episode?.video_url ?: return player

        player.setMediaItem(MediaItem.fromUri(videoUrl))
        player.prepare()
        player.playWhenReady = true

        _uiState.value = _uiState.value.copy(player = player)
        return player
    }

    fun releasePlayer() {
        _uiState.value.player?.release()
        _uiState.value = _uiState.value.copy(player = null)
    }

    override fun onCleared() {
        super.onCleared()
        releasePlayer()
    }

    companion object {
        fun create(episodeId: Long): ViewModelProvider.Factory = object : ViewModelProvider.Factory {
            @Suppress("UNCHECKED_CAST")
            override fun <T : ViewModel> create(modelClass: Class<T>): T {
                return PlayerViewModel(DramaRepository(), episodeId) as T
            }
        }
    }
}
