package main

import (
	"log"

	"shortdrama/backend/internal/config"
	"shortdrama/backend/internal/database"
	"shortdrama/backend/internal/server"
	"shortdrama/backend/internal/storage"
)

func main() {
	cfg, err := config.Load()
	if err != nil {
		log.Fatalf("load config: %v", err)
	}

	db, err := database.NewMySQL(cfg.MySQLDSN)
	if err != nil {
		log.Fatalf("connect mysql: %v", err)
	}

	if err := database.AutoMigrate(db); err != nil {
		log.Fatalf("auto migrate: %v", err)
	}

	var minioClient *storage.MinIOClient
	if cfg.MinIO.Enabled {
		minioClient, err = storage.NewMinIOClient(cfg.MinIO)
		if err != nil {
			log.Fatalf("init minio: %v", err)
		}
		log.Printf("minio storage enabled, bucket=%s", cfg.MinIO.Bucket)
	} else {
		log.Printf("minio storage disabled; upload API will return 503 until MinIO is configured")
	}

	engine := server.NewRouter(server.Dependencies{
		DB:      db,
		Storage: minioClient,
	})

	log.Printf("backend server listening on :%s", cfg.Port)
	if err := engine.Run(":" + cfg.Port); err != nil {
		log.Fatalf("run gin server: %v", err)
	}
}
