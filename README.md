# Short Drama Real Time Interaction
基于短剧剧情的即时互动激发
# Interactive Drama Platform
基于剧情高光事件流的实时互动短剧平台。

## 项目简介

本项目旨在探索短剧场景中的实时互动能力，通过剧情高光识别、事件驱动下发、实时互动同步等机制，为用户提供低输入成本、高沉浸感的情绪表达体验。

项目整体采用：

- Android + Kotlin 客户端
- Golang 后端服务
- Python AI 内容分析服务

构建完整闭环。

---

# 核心功能

## 1. 短剧播放能力

- 剧集列表展示
- 视频播放
- 进度控制
- 高光事件同步

## 2. 高光互动系统

支持：

- 剧情高光互动
- 实时情绪表达
- 全服热度同步
- 动态特效展示

## 3. 实时互动能力

基于 WebSocket：

- 实时在线互动
- 情绪值同步
- 热度聚合广播

## 4. AI高光识别（可选）

基于字幕和情绪分析：

- 剧情高潮检测
- 情绪分类
- 高光点候选生成

---

# 项目架构

```text
Android Client 
        │
 HTTP / WebSocket
        │
Golang Backend
        │
Redis / MySQL
        │
Python AI highlight-engine

```

# 项目目录结构总览

```
Short-Drama-Real-Time-Interaction-main/
│
├── README.md, Structure.md           # 项目文档
│
├── Backend/                          # Go 后端服务
│   ├── main.go                       # 应用入口
│   ├── internal/
│   │   ├── config/                   # 配置加载（端口、MySQL DSN、MinIO）
│   │   ├── database/                 # GORM 连接 + 自动迁移
│   │   ├── model/                    # 数据模型（Drama, Episode, HighlightEvent）
│   │   ├── server/                   # Gin 路由 + CORS
│   │   ├── handler/                  # CRUD 处理器（drama, episode, highlight, upload）
│   │   └── storage/                  # MinIO 客户端
│   └── deploy/                       # 一键部署脚本（one_step.sh）
│
├── Client/                           # Android 客户端（Kotlin + Jetpack Compose）
│   ├── app/src/main/java/com/shortdrama/app/
│   │   ├── MainActivity.kt           # 单 Activity 入口
│   │   ├── navigation/               # 路由定义 + NavGraph（3 屏）
│   │   ├── data/model/               # API 响应、Drama、Episode、Highlight 数据类
│   │   ├── data/network/             # Retrofit API 客户端
│   │   ├── data/repository/          # 数据仓库
│   │   └── ui/                       # 3 屏：drama（列表）/ detail（详情）/ player（播放器+互动）
│   └── build.gradle.kts              # Compose + ExoPlayer + Retrofit + Coil
│
├── highlight-engine/                 # 基于 Highlight-7B 的高光检测模型项目（独立，未集成）
│   ├── highlight/
│   │   ├── model/                    # 多模态模型（Mistral-7B + CLIP + 4 输出头）
│   │   ├── prompts/                  # 高光检测/密集描述等任务 Prompt 模板
│   │   ├── eval/ + metrics/          # DVC/TVG/VHD 评测 + 指标
│   │   └── train_mt.py               # 训练入口
│   └── scripts/
│       ├── train/                    # 预训练/SFT/微调脚本
│       └── inference/                # 推理（含两阶段 + Qwen2.5-VL 流水线）
│
└── docs/
    └── api.md                        # 后端 REST API 文档
```
