package storage

import (
	"context"
	"fmt"
	"mime/multipart"
	"path"
	"path/filepath"
	"strings"
	"time"

	"shortdrama/backend/internal/config"

	"github.com/minio/minio-go/v7"
	"github.com/minio/minio-go/v7/pkg/credentials"
)

var allowedFolders = map[string]struct{}{
	"videos":  {},
	"covers":  {},
	"effects": {},
}

type MinIOClient struct {
	client *minio.Client
	config config.MinIOConfig
}

func NewMinIOClient(cfg config.MinIOConfig) (*MinIOClient, error) {
	client, err := minio.New(cfg.Endpoint, &minio.Options{
		Creds:  credentials.NewStaticV4(cfg.AccessKey, cfg.SecretKey, ""),
		Secure: cfg.UseSSL,
	})
	if err != nil {
		return nil, err
	}

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	exists, err := client.BucketExists(ctx, cfg.Bucket)
	if err != nil {
		return nil, err
	}
	if !exists {
		if err := client.MakeBucket(ctx, cfg.Bucket, minio.MakeBucketOptions{}); err != nil {
			return nil, err
		}
	}

	return &MinIOClient{
		client: client,
		config: cfg,
	}, nil
}

func (m *MinIOClient) UploadFile(ctx context.Context, folder string, fileHeader *multipart.FileHeader) (string, string, error) {
	if _, ok := allowedFolders[folder]; !ok {
		return "", "", fmt.Errorf("unsupported folder: %s", folder)
	}

	src, err := fileHeader.Open()
	if err != nil {
		return "", "", err
	}
	defer src.Close()

	objectName := buildObjectName(folder, fileHeader.Filename)
	contentType := fileHeader.Header.Get("Content-Type")

	_, err = m.client.PutObject(ctx, m.config.Bucket, objectName, src, fileHeader.Size, minio.PutObjectOptions{
		ContentType: contentType,
	})
	if err != nil {
		return "", "", err
	}

	return objectName, m.objectURL(objectName), nil
}

func buildObjectName(folder, filename string) string {
	safeName := strings.ReplaceAll(filepath.Base(filename), " ", "_")
	return path.Join(folder, time.Now().Format("2006/01/02"), fmt.Sprintf("%d_%s", time.Now().UnixNano(), safeName))
}

func (m *MinIOClient) objectURL(objectName string) string {
	if m.config.PublicBaseURL != "" {
		return m.config.PublicBaseURL + "/" + objectName
	}

	scheme := "http"
	if m.config.UseSSL {
		scheme = "https"
	}

	return fmt.Sprintf("%s://%s/%s/%s", scheme, m.config.Endpoint, m.config.Bucket, objectName)
}
