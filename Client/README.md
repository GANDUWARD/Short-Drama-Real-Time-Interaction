# Short Drama Client — Android

短剧高光实时互动系统 · Android 客户端

## 环境要求

| 工具 | 版本 |
|------|------|
| Android Studio | Hedgehog (2023.1.1) 或更高 |
| Gradle | 8.7 |
| Android Gradle Plugin | 8.2.0 |
| Kotlin | 1.9.22 |
| compileSdk | 34 |
| minSdk | 26 |
| targetSdk | 34 |
| Java | 17 |

## 项目结构

```
Client/
├── app/
│   ├── src/main/
│   │   ├── java/com/shortdrama/app/
│   │   │   ├── MainActivity.kt
│   │   │   ├── navigation/
│   │   │   │   ├── Screen.kt        # 路由定义
│   │   │   │   └── NavGraph.kt      # 导航图
│   │   │   ├── data/
│   │   │   │   ├── model/           # 数据模型 (Drama, Episode, Highlight)
│   │   │   │   ├── network/         # Retrofit API 客户端
│   │   │   │   └── repository/      # 数据仓库
│   │   │   └── ui/
│   │   │       ├── drama/           # 首页列表
│   │   │       ├── detail/          # 剧集详情
│   │   │       └── player/          # 视频播放 + 高光浮层 + 互动动画
│   │   └── AndroidManifest.xml
│   └── build.gradle.kts
├── build.gradle.kts
├── settings.gradle.kts
├── gradle/wrapper/gradle-wrapper.properties
└── .gitignore
```

## 快速开始

### 1. 用 Android Studio 打开

打开 Android Studio → **File** → **Open** → 选择 `Client/` 目录

### 2. 等待 Gradle 同步

首次打开会自动下载依赖，如未自动同步可手动点击 **File → Sync Project with Gradle Files**。

### 3. 运行

- 连上安卓手机（开启 USB 调试），或启动模拟器
- 点击 **Run** ▶ 按钮
- 或者 **Build → Build APK(s)** 生成安装包

## 构建 APK

```bash
# Windows
gradlew.bat assembleDebug

# macOS / Linux
./gradlew assembleDebug
```

APK 位置: `app/build/outputs/apk/debug/app-debug.apk`

## 后端 API

客户端连接的是已部署的后端服务：

- **API 地址**: `http://8.140.212.121:8080/`
- **文件存储**: MinIO `http://8.140.212.121:9000/`
- 接口路径: `/api/dramas`、`/api/episodes`、`/api/highlights`

如需修改后端地址，编辑 `app/src/main/java/com/shortdrama/app/data/network/ApiClient.kt` 中的 `BASE_URL`。

## 主要依赖

| 库 | 用途 |
|----|------|
| Jetpack Compose + Material3 | UI 框架 |
| Navigation Compose 2.8.0 | 页面导航 |
| ViewModel + StateFlow | 状态管理 |
| Retrofit 2.9.0 + Gson | 网络请求 |
| OkHttp 4.12.0 | HTTP 日志拦截 |
| Coil 2.6.0 | 封面图片加载 |
| Media3 ExoPlayer 1.3.1 | 视频播放 |

## 功能

- **剧集列表页** — 深色渐变背景，封面+简介卡片，高光互动标签
- **剧集详情页** — 大尺寸封面、展开/收起式剧情简介、剧集列表入口
- **视频播放页** — ExoPlayer 播放 + 顶部高光事件提示 / 中间扫入动画浮层，一键开关切换
- **互动工具栏** — 播放页面底部 5 个互动图标（💣 🌹 😄 🎉 💢），点击后图标从底部飞到屏幕中间绽放 + 粒子散射动画
- **AI 高光事件** — 自动检测剧情高潮 / 反转 / 情感爆发 / 悬念揭晓，播放时实时触发浮层

## 权限

仅需 `INTERNET` 权限，已在 `AndroidManifest.xml` 中声明。
