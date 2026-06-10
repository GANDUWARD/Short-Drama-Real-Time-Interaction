# Backend

Gin + GORM + MySQL + optional MinIO backend for the short-drama real-time interaction platform.

## Features

- `Drama API`: CRUD for drama metadata
- `Episode API`: CRUD for episodes and video URL storage
- `Highlight API`: CRUD for highlight events with JSON payload
- `Video Upload API`: upload files to MinIO folders `videos/`, `covers/`, `effects/`
- Local development mode: run with MySQL only and enable MinIO later on the server

## Project Structure

```text
Backend/
├── main.go
├── .env.example
├── go.mod
└── internal/
    ├── config/
    ├── database/
    ├── handler/
    ├── model/
    ├── server/
    └── storage/
```

## Environment Variables

Copy `.env.example` into your local environment:

```powershell
$env:APP_PORT="8080"
$env:MYSQL_DSN="root:password@tcp(127.0.0.1:3306)/short_drama?charset=utf8mb4&parseTime=True&loc=Local"
$env:MINIO_ENABLED="false"
$env:MINIO_ENDPOINT="127.0.0.1:9000"
$env:MINIO_ACCESS_KEY="minioadmin"
$env:MINIO_SECRET_KEY="minioadmin"
$env:MINIO_BUCKET="short-drama"
$env:MINIO_USE_SSL="false"
$env:MINIO_PUBLIC_BASE_URL="http://127.0.0.1:9000/short-drama"
```

If `MINIO_ENABLED=false`, the service can start without MinIO and `POST /api/uploads/:folder` returns `503 Service Unavailable`.

## Run

```powershell
go mod tidy
go run -buildvcs=false .
```

## API Summary

- `GET /health`
- `GET|POST /api/dramas`
- `GET|PUT|DELETE /api/dramas/:id`
- `GET|POST /api/episodes`
- `GET|PUT|DELETE /api/episodes/:id`
- `GET|POST /api/highlights`
- `GET|PUT|DELETE /api/highlights/:id`
- `POST /api/uploads/:folder`

`folder` supports `videos`, `covers`, `effects`. Upload with `multipart/form-data` and field name `file`.

## Deployment Assets

Cloud deployment notes and MinIO scripts are in:

- `deploy/README.md`
- `deploy/minio/docker-compose.yml`
- `deploy/minio/start.sh`
- `deploy/minio/init-buckets.sh`
