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
