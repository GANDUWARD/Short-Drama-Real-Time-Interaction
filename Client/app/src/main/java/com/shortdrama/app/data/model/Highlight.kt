package com.shortdrama.app.data.model

/**
 *
 * 后端路由: GET /api/highlights（列表） / GET /api/highlights?episode_id=xxx
 *
 * 播放器在视频播放到 trigger_time 秒时弹出互动浮层，
 * 浮层展示 event_type、heat_level，以及 payload 中的情绪选项。
 *
 * event_type 枚举值（来自后端）：
 *   REVERSAL   — 剧情反转
 *   CLIMAX     — 剧情高潮
 *   EMOTIONAL  — 情感爆发
 *   SUSPENSE   — 悬念揭晓
 */
data class Highlight(
    val id: Long,
    val episode_id: Long,
    val trigger_time: Long,
    val duration: Long,
    val event_type: String,
    val heat_level: Int,
    val payload: HighlightPayload
)

/**
 * 高光事件的 payload 扩展信息。
 *
 * 后端以 MySQL JSON 类型存储，Gson 自动解析为嵌套对象。
 *
 * @property effect     特效类型，如 "shock" / "heartbreak" / "surprise"
 * @property text       互动浮层上显示的文案，如 "惊天反转！"
 * @property emoji_pool 提供给用户的情绪表达选项池
 */
data class HighlightPayload(
    val effect: String? = null,
    val text: String? = null,
    val emoji_pool: List<String> = emptyList()
)
