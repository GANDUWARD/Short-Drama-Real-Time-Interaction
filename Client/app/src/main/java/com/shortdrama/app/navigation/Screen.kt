package com.shortdrama.app.navigation

sealed class Screen(val route: String) {
    data object DramaList : Screen("drama_list")
    data object Detail : Screen("detail/{dramaId}") {
        fun createRoute(dramaId: Long) = "detail/$dramaId"
    }
    data object Player : Screen("player/{episodeId}/{dramaTitle}") {
        fun createRoute(episodeId: Long, dramaTitle: String) = "player/$episodeId/$dramaTitle"
    }
}
