package com.shortdrama.app.data.model

/**
 *
 * 所有接口返回格式：
 *   成功 → { "success": true,  "data": { ... } }
 *   失败 → { "success": false, "error": "错误信息" }
 *
 * Retrofit 使用示例：
 *   interface DramaApi {
 *       @GET("api/dramas")
 *       suspend fun getDramas(): ApiResponse<List<Drama>>
 *   }
 *
 * 【Gson 说明】由于泛型 T 运行时会被擦除，Retrofit + Gson 默认无法直接解析 List<T>。
 * 解决方案有两种：
 *   方案 A：在 ApiClient 中注册自定义 Gson TypeAdapterFactory 处理 ApiResponse 泛型
 *   方案 B：将返回值改为 Response<ApiResponse<List<Drama>>> 手动解析 data 的 TypeToken
 * 推荐方案 A，网上搜索 "Gson ApiResponse<T> TypeAdapter" 即可找到现成实现。
 */
data class ApiResponse<T>(
    val success: Boolean,
    val data: T?,
    val error: String?
)
