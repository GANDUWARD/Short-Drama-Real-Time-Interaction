package handler

import (
	"net/http"

	"shortdrama/backend/internal/model"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

type EpisodeHandler struct {
	db *gorm.DB
}

type episodeRequest struct {
	DramaID   uint64 `json:"drama_id" binding:"required"`
	EpisodeNo int    `json:"episode_no"`
	VideoURL  string `json:"video_url" binding:"required"`
	Duration  int    `json:"duration"`
}

func NewEpisodeHandler(db *gorm.DB) *EpisodeHandler {
	return &EpisodeHandler{db: db}
}

func (h *EpisodeHandler) Register(rg *gin.RouterGroup) {
	rg.GET("/episodes", h.List)
	rg.GET("/episodes/:id", h.Get)
	rg.POST("/episodes", h.Create)
	rg.PUT("/episodes/:id", h.Update)
	rg.DELETE("/episodes/:id", h.Delete)
}

func (h *EpisodeHandler) List(c *gin.Context) {
	var episodes []model.Episode

	query := h.db.Order("drama_id asc").Order("episode_no asc")
	if dramaID := c.Query("drama_id"); dramaID != "" {
		query = query.Where("drama_id = ?", dramaID)
	}

	if err := query.Find(&episodes).Error; err != nil {
		failure(c, http.StatusInternalServerError, err.Error())
		return
	}

	success(c, http.StatusOK, episodes)
}

func (h *EpisodeHandler) Get(c *gin.Context) {
	id, ok := parseID(c)
	if !ok {
		return
	}

	var episode model.Episode
	err := h.db.Preload("Highlights", func(db *gorm.DB) *gorm.DB {
		return db.Order("trigger_time asc")
	}).First(&episode, id).Error
	if err != nil {
		handleDBError(c, err)
		return
	}

	success(c, http.StatusOK, episode)
}

func (h *EpisodeHandler) Create(c *gin.Context) {
	var req episodeRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		failure(c, http.StatusBadRequest, err.Error())
		return
	}
	if req.EpisodeNo <= 0 || req.Duration <= 0 {
		failure(c, http.StatusBadRequest, "episode_no and duration must be positive")
		return
	}

	if !h.dramaExists(req.DramaID) {
		failure(c, http.StatusBadRequest, "drama_id does not exist")
		return
	}

	episode := model.Episode{
		DramaID:   req.DramaID,
		EpisodeNo: req.EpisodeNo,
		VideoURL:  req.VideoURL,
		Duration:  req.Duration,
	}
	if err := h.db.Create(&episode).Error; err != nil {
		failure(c, http.StatusInternalServerError, err.Error())
		return
	}

	success(c, http.StatusCreated, episode)
}

func (h *EpisodeHandler) Update(c *gin.Context) {
	id, ok := parseID(c)
	if !ok {
		return
	}

	var req episodeRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		failure(c, http.StatusBadRequest, err.Error())
		return
	}
	if req.EpisodeNo <= 0 || req.Duration <= 0 {
		failure(c, http.StatusBadRequest, "episode_no and duration must be positive")
		return
	}
	if !h.dramaExists(req.DramaID) {
		failure(c, http.StatusBadRequest, "drama_id does not exist")
		return
	}

	var episode model.Episode
	if err := h.db.First(&episode, id).Error; err != nil {
		handleDBError(c, err)
		return
	}

	episode.DramaID = req.DramaID
	episode.EpisodeNo = req.EpisodeNo
	episode.VideoURL = req.VideoURL
	episode.Duration = req.Duration

	if err := h.db.Save(&episode).Error; err != nil {
		failure(c, http.StatusInternalServerError, err.Error())
		return
	}

	success(c, http.StatusOK, episode)
}

func (h *EpisodeHandler) Delete(c *gin.Context) {
	id, ok := parseID(c)
	if !ok {
		return
	}

	if err := h.db.Delete(&model.Episode{}, id).Error; err != nil {
		failure(c, http.StatusInternalServerError, err.Error())
		return
	}

	success(c, http.StatusOK, gin.H{"id": id})
}

func (h *EpisodeHandler) dramaExists(dramaID uint64) bool {
	var count int64
	h.db.Model(&model.Drama{}).Where("id = ?", dramaID).Count(&count)
	return count > 0
}
