package com.shortdrama.app.data.model

/**
 *
 * 后端路由: GET /api/episodes（列表） / GET /api/episodes/:id（详情）
 *
 * 列表接口返回的 highlights = []（后端 omitempty）
 * 详情接口返回的 highlights = 该集所有高光事件
 *
 * duration 单位秒；video_url 可直接传给 ExoPlayer/Media3 播放。
 */
data class Episode(
    val id: Long,
    val drama_id: Long,
    val episode_no: Int,
    val video_url: String,
    val duration: Long,
    val highlights: List<Highlight> = emptyList()
)
