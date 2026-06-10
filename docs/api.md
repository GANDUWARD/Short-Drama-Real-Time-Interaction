# Backend API

基于当前后端实现整理，按业务操作顺序组织。

## 1. 基础信息

- Base URL: `http://<server>:8080`
- Health Check: `GET /health`
- API Prefix: `/api`
- 返回格式:

成功:

```json
{
  "success": true,
  "data": {}
}
```

失败:

```json
{
  "success": false,
  "error": "error message"
}
```

## 2. 业务接入顺序

推荐按下面顺序调用:

1. 创建剧目 `Drama`
2. 上传封面 / 视频 / 特效资源到 MinIO
3. 创建剧集 `Episode`，写入视频 URL
4. 创建高光事件 `Highlight`
5. 播放前按需拉取剧目、剧集和高光数据

## 3. 健康检查

### `GET /health`

用于确认后端服务是否正常。

响应示例:

```json
{
  "status": "ok",
  "storage_enabled": true
}
```

`storage_enabled=true` 表示当前环境已启用 MinIO 上传能力。

## 4. 剧目管理

### 4.1 创建剧目

`POST /api/dramas`

请求体:

```json
{
  "title": "重生之我在豪门当保姆",
  "description": "短剧简介",
  "cover_url": "http://8.140.212.121:9000/short-drama/covers/2026/06/02/cover.jpg"
}
```

字段说明:

- `title`: 必填，剧目标题
- `description`: 选填，剧目简介
- `cover_url`: 选填，封面 URL，通常来自上传接口

### 4.2 获取剧目列表

`GET /api/dramas`

### 4.3 获取单个剧目详情

`GET /api/dramas/:id`

返回该剧目及其剧集列表。

### 4.4 更新剧目

`PUT /api/dramas/:id`

请求体与创建剧目一致。

### 4.5 删除剧目

`DELETE /api/dramas/:id`

删除剧目。当前实现下会级联影响关联数据。

## 5. 资源上传

资源上传到 MinIO，数据库只保存 URL。

### 5.1 上传接口

`POST /api/uploads/:folder`

支持的 `folder`:

- `videos`
- `covers`
- `effects`

请求要求:

- `Content-Type: multipart/form-data`
- 文件字段名必须为 `file`

### 5.2 上传视频

`POST /api/uploads/videos`

示例:

```bash
curl -X POST "http://<server>:8080/api/uploads/videos" \
  -F "file=@/path/to/episode-01.mp4"
```

### 5.3 上传封面

`POST /api/uploads/covers`

示例:

```bash
curl -X POST "http://<server>:8080/api/uploads/covers" \
  -F "file=@/path/to/cover.jpg"
```

### 5.4 上传特效资源

`POST /api/uploads/effects`

示例:

```bash
curl -X POST "http://<server>:8080/api/uploads/effects" \
  -F "file=@/path/to/effect.json"
```

上传成功响应示例:

```json
{
  "success": true,
  "data": {
    "folder": "videos",
    "object_key": "videos/2026/06/02/1717300000000_episode-01.mp4",
    "url": "http://8.140.212.121:9000/short-drama/videos/2026/06/02/1717300000000_episode-01.mp4"
  }
}
```

说明:

- `object_key`: MinIO 对象路径
- `url`: 可存入业务表的访问地址

如果当前环境未启用 MinIO，接口会返回 `503 Service Unavailable`。

## 6. 剧集管理

剧集依赖剧目先存在，视频地址通常来自上传接口。

### 6.1 创建剧集

`POST /api/episodes`

请求体:

```json
{
  "drama_id": 1,
  "episode_no": 1,
  "video_url": "http://8.140.212.121:9000/short-drama/videos/2026/06/02/1717300000000_episode-01.mp4",
  "duration": 95
}
```

字段说明:

- `drama_id`: 必填，所属剧目 ID
- `episode_no`: 必填，集数，必须大于 0
- `video_url`: 必填，视频 URL
- `duration`: 必填，视频时长，单位秒，必须大于 0

约束:

- `drama_id` 必须存在
- 同一剧目下 `episode_no` 唯一

### 6.2 获取剧集列表

`GET /api/episodes`

### 6.3 按剧目查询剧集

`GET /api/episodes?drama_id=1`

### 6.4 获取单个剧集详情

`GET /api/episodes/:id`

返回该剧集及其高光事件列表。

### 6.5 更新剧集

`PUT /api/episodes/:id`

请求体与创建剧集一致。

### 6.6 删除剧集

`DELETE /api/episodes/:id`

## 7. 高光事件管理

高光事件依赖剧集先存在。

### 7.1 创建高光事件

`POST /api/highlights`

请求体:

```json
{
  "episode_id": 101,
  "trigger_time": 32,
  "duration": 5,
  "event_type": "REVERSAL",
  "heat_level": 9,
  "payload": {
    "effect": "shock",
    "emoji_pool": [
      "卧槽",
      "反转了",
      "没想到"
    ]
  }
}
```

字段说明:

- `episode_id`: 必填，所属剧集 ID
- `trigger_time`: 必填，触发时间点，单位秒，必须大于等于 0
- `duration`: 必填，持续时间，单位秒，必须大于 0
- `event_type`: 必填，事件类型，如 `REVERSAL`
- `heat_level`: 必填，热度值，必须大于等于 0
- `payload`: 必填，JSON 格式的扩展信息

### 7.2 获取高光列表

`GET /api/highlights`

### 7.3 按剧集查询高光

`GET /api/highlights?episode_id=101`

### 7.4 按事件类型查询高光

`GET /api/highlights?event_type=REVERSAL`

### 7.5 获取单个高光详情

`GET /api/highlights/:id`

### 7.6 更新高光事件

`PUT /api/highlights/:id`

请求体与创建高光一致。

### 7.7 删除高光事件

`DELETE /api/highlights/:id`

## 8. 推荐业务流程示例

### 8.1 创建新剧并发布第一集

1. 上传封面:

```bash
POST /api/uploads/covers
```

2. 创建剧目:

```bash
POST /api/dramas
```

3. 上传视频:

```bash
POST /api/uploads/videos
```

4. 创建剧集:

```bash
POST /api/episodes
```

5. 配置高光:

```bash
POST /api/highlights
```

### 8.2 客户端播放页加载

推荐请求顺序:

1. 拉剧目详情:

```bash
GET /api/dramas/:id
```

2. 拉某一集详情:

```bash
GET /api/episodes/:id
```

3. 若需要单独刷新高光:

```bash
GET /api/highlights?episode_id=:episodeId
```

## 9. 当前版本限制

当前后端已支持:

- 剧目 CRUD
- 剧集 CRUD
- 高光事件 CRUD
- MinIO 文件上传

当前后端尚未支持:

- 用户鉴权
- 播放鉴权
- 分片上传
- 断点续传
- 视频转码 / HLS
- WebSocket 实时互动
- 后台登录权限管理
