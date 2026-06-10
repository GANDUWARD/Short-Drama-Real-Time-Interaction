package com.shortdrama.app.data.model

/**
 *
 * 后端路由: GET /api/dramas（列表） / GET /api/dramas/:id（详情）
 *
 * 列表接口返回的 episodes = []（后端 omitempty，Gson 使用默认值）
 * 详情接口返回的 episodes = 该剧所有剧集
 */
data class Drama(
    val id: Long,
    val title: String,
    val description: String? = null,
    val cover_url: String? = null,
    val created_at: String? = null,
    val episodes: List<Episode> = emptyList()
)
