package com.shortdrama.app.ui.player

import android.view.ViewGroup
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.Spring
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.spring
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.key
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.media3.ui.PlayerView
import com.shortdrama.app.data.model.Highlight
import kotlin.math.cos
import kotlin.math.sin
import kotlin.math.PI
import kotlin.random.Random
import kotlinx.coroutines.delay

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PlayerScreen(
    viewModel: PlayerViewModel,
    dramaTitle: String,
    onBack: () -> Unit
) {
    val uiState by viewModel.uiState.collectAsState()
    val context = LocalContext.current

    DisposableEffect(Unit) {
        onDispose {
            viewModel.releasePlayer()
        }
    }

    Scaffold(
        containerColor = Color(0xFF0E0E14),
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        text = dramaTitle,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "返回")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = Color(0xFF0E0E14),
                    titleContentColor = Color.White,
                    navigationIconContentColor = Color.White
                )
            )
        }
    ) { padding ->
        when {
            uiState.isLoading -> {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(padding),
                    contentAlignment = Alignment.Center
                ) {
                    CircularProgressIndicator(color = Color.White)
                }
            }

            uiState.errorMessage != null -> {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(padding),
                    contentAlignment = Alignment.Center
                ) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text(
                            text = uiState.errorMessage ?: "",
                            style = MaterialTheme.typography.bodyLarge,
                            color = Color(0xFFFFB4AB)
                        )
                    }
                }
            }

            uiState.episode != null -> {
                val exoPlayer = remember(uiState.episode?.id) {
                    viewModel.createPlayer(context)
                }

                var currentPosition by remember { mutableLongStateOf(0L) }

                LaunchedEffect(exoPlayer) {
                    while (true) {
                        currentPosition = exoPlayer.currentPosition
                        kotlinx.coroutines.delay(500)
                    }
                }

                // false：只在顶部显示一行高光提示；true：在屏幕中间播放划过式高光浮层
                var showCenterHighlight by remember { mutableStateOf(false) }

                var burstId by remember { mutableLongStateOf(0L) }
                var burstEffects by remember { mutableStateOf(listOf<BurstEffect>()) }

                val activeHighlight = findActiveHighlight(
                    highlights = uiState.highlights,
                    positionMs = currentPosition
                )

                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(padding)
                ) {
                    Box(modifier = Modifier.weight(1f)) {
                        AndroidView(
                            factory = { context ->
                                PlayerView(context).apply {
                                    player = exoPlayer
                                    useController = true
                                    layoutParams = ViewGroup.LayoutParams(
                                        ViewGroup.LayoutParams.MATCH_PARENT,
                                        ViewGroup.LayoutParams.MATCH_PARENT
                                    )
                                }
                            },
                            modifier = Modifier.fillMaxSize()
                        )

                        Box(
                            modifier = Modifier
                                .fillMaxWidth()
                                .align(Alignment.TopCenter)
                                .background(
                                    Brush.verticalGradient(
                                        colors = listOf(
                                            Color.Black.copy(alpha = 0.72f),
                                            Color.Transparent
                                        )
                                    )
                                )
                                .padding(horizontal = 14.dp, vertical = 12.dp)
                        ) {
                            activeHighlight?.let { highlight ->
                                if (showCenterHighlight) {
                                    SmallTopStatus(text = "高光弹幕已开启 · ${eventLabel(highlight.event_type)}")
                                } else {
                                    TopHighlightLine(highlight = highlight)
                                }
                            } ?: SmallTopStatus(text = "等待剧情高光触发")
                        }

                        CenterHighlightArea(
                            visible = showCenterHighlight && activeHighlight != null,
                            highlight = activeHighlight,
                            modifier = Modifier.align(Alignment.Center)
                        )

                        HighlightSwitchButton(
                            enabled = showCenterHighlight,
                            onClick = { showCenterHighlight = !showCenterHighlight },
                            modifier = Modifier
                                .align(Alignment.BottomEnd)
                                .padding(14.dp)
                        )

                        BoxWithConstraints(modifier = Modifier.fillMaxSize()) {
                            val parentW = maxWidth
                            val parentH = maxHeight
                            burstEffects.forEach { effect ->
                                key(effect.id) {
                                    BurstExplosion(
                                        effect = effect,
                                        parentWidth = parentW,
                                        parentHeight = parentH,
                                        onFinished = {
                                            burstEffects = burstEffects.filter { it.id != effect.id }
                                        }
                                    )
                                }
                            }
                        }
                    }

                    InteractionBar(
                        onEmojiTap = { emoji ->
                            val id = burstId++
                            burstEffects = burstEffects + BurstEffect(
                                id = id,
                                emoji = emoji,
                                offsetX = 0.15f + Random.nextFloat() * 0.7f,
                                offsetY = 0.15f + Random.nextFloat() * 0.5f
                            )
                        }
                    )

                    EpisodeInfoBar(
                        episodeNo = uiState.episode!!.episode_no,
                        duration = uiState.episode!!.duration,
                        highlightCount = uiState.highlights.size
                    )
                }
            }
        }
    }
}

@Composable
private fun TopHighlightLine(highlight: Highlight) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(50.dp))
            .background(Color.White.copy(alpha = 0.12f))
            .padding(horizontal = 14.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(
            text = "${eventLabel(highlight.event_type)}：${payloadText(highlight)}",
            style = MaterialTheme.typography.bodyMedium,
            fontWeight = FontWeight.SemiBold,
            color = Color.White,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            modifier = Modifier.weight(1f)
        )
        Spacer(modifier = Modifier.width(8.dp))
        Text(
            text = "点右下角放大",
            style = MaterialTheme.typography.labelSmall,
            color = Color(0xFFFFD6E7)
        )
    }
}

@Composable
private fun SmallTopStatus(text: String) {
    Text(
        text = text,
        style = MaterialTheme.typography.bodySmall,
        color = Color.White.copy(alpha = 0.76f),
        maxLines = 1,
        overflow = TextOverflow.Ellipsis,
        modifier = Modifier
            .clip(RoundedCornerShape(50.dp))
            .background(Color.Black.copy(alpha = 0.34f))
            .padding(horizontal = 14.dp, vertical = 8.dp)
    )
}

@Composable
private fun CenterSweepHighlight(highlight: Highlight) {
    val offsetAnim = remember { Animatable(360f) }
    val alphaAnim = remember { Animatable(0f) }

    LaunchedEffect(highlight.id) {
        offsetAnim.snapTo(360f)
        alphaAnim.snapTo(0f)
        alphaAnim.animateTo(1f, animationSpec = tween(durationMillis = 180))
        offsetAnim.animateTo(
            targetValue = 0f,
            animationSpec = tween(durationMillis = 520, easing = FastOutSlowInEasing)
        )
    }

    val scale by animateFloatAsState(
        targetValue = 1f,
        animationSpec = spring(dampingRatio = 0.55f, stiffness = Spring.StiffnessLow),
        label = "highlightScale"
    )

    Box(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 24.dp)
            .offset(x = offsetAnim.value.dp)
            .graphicsLayer(
                alpha = alphaAnim.value,
                scaleX = scale,
                scaleY = scale
            ),
        contentAlignment = Alignment.Center
    ) {
        Box(
            modifier = Modifier
                .matchParentSize()
                .background(
                    brush = Brush.radialGradient(
                        colors = listOf(
                            Color(0x55FF4F9A),
                            Color(0x22FF8A3D),
                            Color.Transparent
                        )
                    ),
                    shape = RoundedCornerShape(28.dp)
                )
        )

        Row(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(28.dp))
                .background(Color(0xEE171321))
                .padding(horizontal = 22.dp, vertical = 18.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Spacer(modifier = Modifier.width(14.dp))

            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = payloadText(highlight),
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.ExtraBold,
                    color = Color.White,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = eventLabel(highlight.event_type),
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = FontWeight.SemiBold,
                    color = Color(0xFFFFD6E7),
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
            }
        }
    }
}

@Composable
private fun CenterHighlightArea(
    visible: Boolean,
    highlight: Highlight?,
    modifier: Modifier = Modifier
) {
    Box(modifier = modifier) {
        AnimatedVisibility(visible = visible) {
            highlight?.let { h ->
                CenterSweepHighlight(highlight = h)
            }
        }
    }
}

@Composable
private fun HighlightSwitchButton(
    enabled: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    Row(
        modifier = modifier
            .clip(RoundedCornerShape(50.dp))
            .background(
                if (enabled) Color(0xFFFF4F9A) else Color.White.copy(alpha = 0.16f)
            )
            .clickable(onClick = onClick)
            .padding(horizontal = 14.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(
            text = if (enabled) "高光开" else "高光关",
            style = MaterialTheme.typography.labelLarge,
            fontWeight = FontWeight.Bold,
            color = Color.White
        )
    }
}

@Composable
private fun EpisodeInfoBar(
    episodeNo: Any,
    duration: Long,
    highlightCount: Int
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(Color(0xFF151520))
            .padding(horizontal = 16.dp, vertical = 14.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = "第 $episodeNo 集",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
                color = Color.White
            )
            Spacer(modifier = Modifier.height(3.dp))
            Text(
                text = "${formatDuration(duration)} · $highlightCount 个高光点",
                style = MaterialTheme.typography.bodySmall,
                color = Color.White.copy(alpha = 0.62f)
            )
        }
        Text(
            text = "实时互动",
            style = MaterialTheme.typography.labelLarge,
            fontWeight = FontWeight.SemiBold,
            color = Color(0xFFFFD6E7),
            modifier = Modifier
                .clip(RoundedCornerShape(50.dp))
                .background(Color(0xFFFF4F9A).copy(alpha = 0.20f))
                .padding(horizontal = 12.dp, vertical = 7.dp)
        )
    }
}

private fun payloadText(highlight: Highlight): String {
    return highlight.payload?.text ?: "精彩时刻"
}

private fun eventLabel(eventType: String): String {
    return when (eventType) {
        "CLIMAX" -> "剧情高潮"
        "REVERSAL" -> "惊天反转"
        "EMOTIONAL" -> "情感爆发"
        "SUSPENSE" -> "悬念揭晓"
        else -> eventType
    }
}

private fun findActiveHighlight(
    highlights: List<Highlight>,
    positionMs: Long
): Highlight? {
    val positionSec = positionMs / 1000
    return highlights.firstOrNull { h ->
        positionSec >= h.trigger_time &&
            positionSec < h.trigger_time + h.duration
    }
}

private fun formatDuration(seconds: Long): String {
    val min = seconds / 60
    val sec = seconds % 60
    return "${min}分${sec}秒"
}

private data class BurstEffect(
    val id: Long,
    val emoji: String,
    val offsetX: Float,
    val offsetY: Float
)

@Composable
private fun InteractionBar(
    onEmojiTap: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    val icons = listOf(
        "💣" to "炸弹",
        "🌹" to "玫瑰",
        "😄" to "开心",
        "🎉" to "祝贺",
        "💢" to "愤怒"
    )

    Row(
        modifier = modifier
            .fillMaxWidth()
            .background(Color(0xFF1A1A2E))
            .padding(horizontal = 20.dp, vertical = 10.dp),
        horizontalArrangement = Arrangement.SpaceEvenly,
        verticalAlignment = Alignment.CenterVertically
    ) {
        icons.forEach { (emoji, label) ->
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                modifier = Modifier
                    .clip(RoundedCornerShape(50.dp))
                    .clickable { onEmojiTap(emoji) }
                    .padding(horizontal = 10.dp, vertical = 6.dp)
            ) {
                Text(text = emoji, style = MaterialTheme.typography.titleLarge)
                Spacer(modifier = Modifier.height(2.dp))
                Text(
                    text = label,
                    style = MaterialTheme.typography.labelSmall,
                    color = Color.White.copy(alpha = 0.7f)
                )
            }
        }
    }
}

@Composable
private fun BurstExplosion(
    effect: BurstEffect,
    parentWidth: Dp,
    parentHeight: Dp,
    onFinished: () -> Unit
) {
    val flightProgress = remember { Animatable(0f) }
    val burstProgress = remember { Animatable(0f) }
    val mainAlpha = remember { Animatable(1f) }

    val startX = 0.5f
    val startY = 0.92f
    val endX = effect.offsetX
    val endY = effect.offsetY

    LaunchedEffect(effect.id) {
        // Phase 1: fly from bottom to target, growing
        flightProgress.animateTo(1f, tween(400, easing = FastOutSlowInEasing))
        // Phase 2: burst particles
        burstProgress.animateTo(1f, tween(400, easing = FastOutSlowInEasing))
        // Phase 3: fade out
        mainAlpha.animateTo(0f, tween(200))
        onFinished()
    }

    val flight = flightProgress.value
    val curX = parentWidth * (startX + (endX - startX) * flight) - 30.dp
    val curY = parentHeight * (startY + (endY - startY) * flight) - 30.dp
    val scale = 0.3f + 1.2f * flight

    Box(
        modifier = Modifier
            .offset(x = curX, y = curY)
            .size(60.dp)
            .graphicsLayer(
                scaleX = scale,
                scaleY = scale,
                alpha = mainAlpha.value
            ),
        contentAlignment = Alignment.Center
    ) {
        Text(text = effect.emoji, fontSize = 28.sp)

        if (burstProgress.value > 0f) {
            for (i in 0 until 8) {
                val angle = i * 45f + Random.nextFloat() * 15f - 7.5f
                val dist = 50.dp + 40.dp * Random.nextFloat()
                BurstParticle(
                    emoji = effect.emoji,
                    angleDeg = angle,
                    distance = dist,
                    burst = burstProgress.value,
                    delay = i * 20L
                )
            }
        }
    }
}

@Composable
private fun BurstParticle(
    emoji: String,
    angleDeg: Float,
    distance: Dp,
    burst: Float,
    delay: Long
) {
    val p = ((burst * 500 - delay) / 500f).coerceIn(0f, 1f)

    val rad = angleDeg * (PI / 180).toFloat()
    val dx = distance * p * cos(rad)
    val dy = distance * p * sin(rad)
    val particleAlpha = 1f - p
    val particleScale = 1f - p * 0.6f

    if (p > 0f) {
        Text(
            text = emoji,
            fontSize = 14.sp,
            modifier = Modifier
                .offset(x = dx, y = dy)
                .graphicsLayer(
                    alpha = particleAlpha,
                    scaleX = particleScale,
                    scaleY = particleScale
                )
        )
    }
}
