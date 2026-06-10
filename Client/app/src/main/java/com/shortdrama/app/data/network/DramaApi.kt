package com.shortdrama.app.data.network

import com.shortdrama.app.data.model.ApiResponse
import com.shortdrama.app.data.model.Drama
import com.shortdrama.app.data.model.Episode
import com.shortdrama.app.data.model.Highlight
import retrofit2.http.GET
import retrofit2.http.Path
import retrofit2.http.Query

/**
 * 后端 REST API 接口定义。
 *
 * 所有方法均为 suspend 挂起函数，配合 Retrofit 协程适配器使用。
 * 返回值统一为 ApiResponse<T>，data 的泛型由 Gson 自定义适配器解析。
 */
interface DramaApi {

    /** GET /api/dramas — 获取所有剧目列表（首页用） */
    @GET("api/dramas")
    suspend fun getDramas(): ApiResponse<List<Drama>>

    /** GET /api/dramas/{id} — 获取单个剧目详情（含剧集列表） */
    @GET("api/dramas/{id}")
    suspend fun getDrama(@Path("id") dramaId: Long): ApiResponse<Drama>

    /** GET /api/episodes/{id} — 获取单个剧集详情（含高光事件列表） */
    @GET("api/episodes/{id}")
    suspend fun getEpisode(@Path("id") episodeId: Long): ApiResponse<Episode>

    /** GET /api/highlights?episode_id=xxx — 按剧集查询高光事件 */
    @GET("api/highlights")
    suspend fun getHighlights(@Query("episode_id") episodeId: Long): ApiResponse<List<Highlight>>
}
