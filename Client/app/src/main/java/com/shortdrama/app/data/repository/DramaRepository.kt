package com.shortdrama.app.data.repository

import com.shortdrama.app.data.model.Drama
import com.shortdrama.app.data.model.Episode
import com.shortdrama.app.data.model.Highlight
import com.shortdrama.app.data.network.ApiClient
import com.shortdrama.app.data.network.DramaApi

/**
 * 数据仓库层。
 *
 * 封装 [DramaApi] 的调用逻辑，将 [ApiResponse] 映射为 Kotlin 标准的 [Result]，
 * ViewModel 通过本类获取数据，不直接依赖 Retrofit。
 */
class DramaRepository {

    private val api = ApiClient.retrofit.create(DramaApi::class.java)

    /** 获取所有剧目列表 */
    suspend fun getDramas(): Result<List<Drama>> {
        return try {
            val response = api.getDramas()
            if (response.success && response.data != null) {
                Result.success(response.data)
            } else {
                Result.failure(Exception(response.error ?: "Unknown error"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    /** 获取剧目详情（含剧集列表） */
    suspend fun getDramaDetail(id: Long): Result<Drama> {
        return try {
            val response = api.getDrama(id)
            if (response.success && response.data != null) {
                Result.success(response.data)
            } else {
                Result.failure(Exception(response.error ?: "Unknown error"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    /** 获取剧集详情（含高光事件列表） */
    suspend fun getEpisodeDetail(id: Long): Result<Episode> {
        return try {
            val response = api.getEpisode(id)
            if (response.success && response.data != null) {
                Result.success(response.data)
            } else {
                Result.failure(Exception(response.error ?: "Unknown error"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    /** 按剧集 ID 获取高光事件列表 */
    suspend fun getHighlightsByEpisode(episodeId: Long): Result<List<Highlight>> {
        return try {
            val response = api.getHighlights(episodeId)
            if (response.success && response.data != null) {
                Result.success(response.data)
            } else {
                Result.failure(Exception(response.error ?: "Unknown error"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
