package server

import (
	"net/http"

	"shortdrama/backend/internal/handler"
	"shortdrama/backend/internal/storage"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

type Dependencies struct {
	DB      *gorm.DB
	Storage *storage.MinIOClient
}

func NewRouter(deps Dependencies) *gin.Engine {
	engine := gin.Default()
	engine.Use(cors())

	engine.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"status":          "ok",
			"storage_enabled": deps.Storage != nil,
		})
	})

	api := engine.Group("/api")
	handler.NewDramaHandler(deps.DB).Register(api)
	handler.NewEpisodeHandler(deps.DB).Register(api)
	handler.NewHighlightHandler(deps.DB).Register(api)
	handler.NewUploadHandler(deps.Storage).Register(api)

	return engine
}

func cors() gin.HandlerFunc {
	return func(c *gin.Context) {
		c.Writer.Header().Set("Access-Control-Allow-Origin", "*")
		c.Writer.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")
		c.Writer.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")

		if c.Request.Method == http.MethodOptions {
			c.AbortWithStatus(http.StatusNoContent)
			return
		}

		c.Next()
	}
}
