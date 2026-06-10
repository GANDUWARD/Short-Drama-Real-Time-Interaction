package handler

import (
	"net/http"

	"shortdrama/backend/internal/storage"

	"github.com/gin-gonic/gin"
)

type UploadHandler struct {
	storage *storage.MinIOClient
}

func NewUploadHandler(storage *storage.MinIOClient) *UploadHandler {
	return &UploadHandler{storage: storage}
}

func (h *UploadHandler) Register(rg *gin.RouterGroup) {
	rg.POST("/uploads/:folder", h.Upload)
}

func (h *UploadHandler) Upload(c *gin.Context) {
	if h.storage == nil {
		failure(c, http.StatusServiceUnavailable, "minio storage is disabled in current environment")
		return
	}

	file, err := c.FormFile("file")
	if err != nil {
		failure(c, http.StatusBadRequest, "file is required")
		return
	}

	folder := c.Param("folder")
	objectKey, url, err := h.storage.UploadFile(c.Request.Context(), folder, file)
	if err != nil {
		failure(c, http.StatusBadRequest, err.Error())
		return
	}

	success(c, http.StatusCreated, gin.H{
		"folder":     folder,
		"object_key": objectKey,
		"url":        url,
	})
}
