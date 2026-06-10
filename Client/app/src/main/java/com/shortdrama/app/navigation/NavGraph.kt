package com.shortdrama.app.navigation

import androidx.compose.runtime.Composable
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavHostController
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.navArgument
import com.shortdrama.app.ui.detail.DetailScreen
import com.shortdrama.app.ui.detail.DetailViewModel
import com.shortdrama.app.ui.drama.DramaScreen
import com.shortdrama.app.ui.player.PlayerScreen
import com.shortdrama.app.ui.player.PlayerViewModel

@Composable
fun NavGraph(navController: NavHostController) {
    NavHost(navController = navController, startDestination = Screen.DramaList.route) {
        // 首页 - 剧目列表
        composable(Screen.DramaList.route) {
            DramaScreen(
                onDramaClick = { dramaId ->
                    navController.navigate(Screen.Detail.createRoute(dramaId))
                }
            )
        }

        // 详情页 - 剧集列表
        composable(
            route = Screen.Detail.route,
            arguments = listOf(navArgument("dramaId") { type = NavType.LongType })
        ) { backStackEntry ->
            val dramaId = backStackEntry.arguments?.getLong("dramaId") ?: return@composable
            val viewModel: DetailViewModel = viewModel(factory = DetailViewModel.create(dramaId))
            val dramaTitle = viewModel.uiState.value.drama?.title ?: ""

            DetailScreen(
                viewModel = viewModel,
                onBack = { navController.popBackStack() },
                onEpisodeClick = { episodeId ->
                    navController.navigate(Screen.Player.createRoute(episodeId, dramaTitle))
                }
            )
        }

        // 播放页
        composable(
            route = Screen.Player.route,
            arguments = listOf(
                navArgument("episodeId") { type = NavType.LongType },
                navArgument("dramaTitle") { type = NavType.StringType }
            )
        ) { backStackEntry ->
            val episodeId = backStackEntry.arguments?.getLong("episodeId") ?: return@composable
            val dramaTitle = backStackEntry.arguments?.getString("dramaTitle") ?: ""
            val viewModel: PlayerViewModel = viewModel(factory = PlayerViewModel.create(episodeId))

            PlayerScreen(
                viewModel = viewModel,
                dramaTitle = dramaTitle,
                onBack = { navController.popBackStack() }
            )
        }
    }
}
