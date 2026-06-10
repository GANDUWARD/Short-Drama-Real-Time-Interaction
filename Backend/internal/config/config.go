package config

import (
	"errors"
	"os"
	"strings"
)

type Config struct {
	Port     string
	MySQLDSN string
	MinIO    MinIOConfig
}

type MinIOConfig struct {
	Enabled       bool
	Endpoint      string
	AccessKey     string
	SecretKey     string
	Bucket        string
	UseSSL        bool
	PublicBaseURL string
}

func Load() (Config, error) {
	minio := MinIOConfig{
		Endpoint:      os.Getenv("MINIO_ENDPOINT"),
		AccessKey:     os.Getenv("MINIO_ACCESS_KEY"),
		SecretKey:     os.Getenv("MINIO_SECRET_KEY"),
		Bucket:        getEnv("MINIO_BUCKET", "short-drama"),
		UseSSL:        strings.EqualFold(getEnv("MINIO_USE_SSL", "false"), "true"),
		PublicBaseURL: strings.TrimRight(os.Getenv("MINIO_PUBLIC_BASE_URL"), "/"),
	}
	minio.Enabled = resolveMinIOEnabled(minio)

	cfg := Config{
		Port:     getEnv("APP_PORT", "8080"),
		MySQLDSN: os.Getenv("MYSQL_DSN"),
		MinIO:    minio,
	}

	if cfg.MySQLDSN == "" {
		return Config{}, errors.New("MYSQL_DSN is required")
	}
	if cfg.MinIO.Enabled {
		if cfg.MinIO.Endpoint == "" {
			return Config{}, errors.New("MINIO_ENDPOINT is required when MinIO is enabled")
		}
		if cfg.MinIO.AccessKey == "" {
			return Config{}, errors.New("MINIO_ACCESS_KEY is required when MinIO is enabled")
		}
		if cfg.MinIO.SecretKey == "" {
			return Config{}, errors.New("MINIO_SECRET_KEY is required when MinIO is enabled")
		}
	}

	return cfg, nil
}

func getEnv(key, fallback string) string {
	value := strings.TrimSpace(os.Getenv(key))
	if value == "" {
		return fallback
	}
	return value
}

func resolveMinIOEnabled(cfg MinIOConfig) bool {
	raw := strings.TrimSpace(os.Getenv("MINIO_ENABLED"))
	if raw != "" {
		return strings.EqualFold(raw, "true")
	}

	return cfg.Endpoint != "" || cfg.AccessKey != "" || cfg.SecretKey != "" || cfg.PublicBaseURL != ""
}
