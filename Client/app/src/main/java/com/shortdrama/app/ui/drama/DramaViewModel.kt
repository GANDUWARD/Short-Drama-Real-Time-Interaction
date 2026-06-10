package com.shortdrama.app.ui.drama

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.shortdrama.app.data.model.Drama
import com.shortdrama.app.data.repository.DramaRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class DramaViewModel : ViewModel() {

    private val repository = DramaRepository()

    private val _uiState = MutableStateFlow(DramaUiState())
    val uiState: StateFlow<DramaUiState> = _uiState.asStateFlow()

    init {
        loadDramas()
    }

    fun loadDramas() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, errorMessage = null)

            repository.getDramas()
                .onSuccess { dramas ->
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        dramas = dramas,
                        errorMessage = null
                    )
                }
                .onFailure { e ->
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        errorMessage = e.message ?: "加载失败"
                    )
                }
        }
    }
}

data class DramaUiState(
    val isLoading: Boolean = true,
    val dramas: List<Drama> = emptyList(),
    val errorMessage: String? = null
)
