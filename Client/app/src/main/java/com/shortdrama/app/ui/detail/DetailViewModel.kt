package com.shortdrama.app.ui.detail

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.shortdrama.app.data.model.Drama
import com.shortdrama.app.data.model.Episode
import com.shortdrama.app.data.repository.DramaRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class DetailUiState(
    val isLoading: Boolean = true,
    val drama: Drama? = null,
    val episodes: List<Episode> = emptyList(),
    val errorMessage: String? = null
)

class DetailViewModel(
    private val repository: DramaRepository,
    private val dramaId: Long
) : ViewModel() {

    private val _uiState = MutableStateFlow(DetailUiState())
    val uiState: StateFlow<DetailUiState> = _uiState.asStateFlow()

    init {
        loadDrama()
    }

    fun loadDrama() {
        viewModelScope.launch {
            _uiState.value = DetailUiState(isLoading = true)
            repository.getDramaDetail(dramaId)
                .onSuccess { drama ->
                    _uiState.value = DetailUiState(
                        isLoading = false,
                        drama = drama,
                        episodes = drama.episodes ?: emptyList()
                    )
                }
                .onFailure { e ->
                    _uiState.value = DetailUiState(
                        isLoading = false,
                        errorMessage = e.message ?: "加载失败"
                    )
                }
        }
    }

    companion object {
        fun create(dramaId: Long): ViewModelProvider.Factory = object : ViewModelProvider.Factory {
            @Suppress("UNCHECKED_CAST")
            override fun <T : ViewModel> create(modelClass: Class<T>): T {
                return DetailViewModel(DramaRepository(), dramaId) as T
            }
        }
    }
}
